import logging
from datetime import date, datetime
from sqlalchemy.orm import joinedload
from sqlalchemy import or_, and_
from flask import Blueprint, request, jsonify, send_from_directory
from marshmallow import ValidationError
from backend.tasks.missions.marshmallow import MissionCreateSchema, MissionDetailSchema, MissionHistorySchema
from backend.tasks.models.models import Mission, MissionHistory, db, Tag, MissionComment
from backend.models.models import Users
from backend.tasks.models.management import ManagementMission, ManagementSession, sync_history_to_management
from backend.tasks.missions.utils import create_notification
from backend.tasks.missions.signals import on_mission_status_change, send_notification

_logger = logging.getLogger(__name__)


def _get_management_mission(management_id: int):
    """Return (session, ManagementMission) or (None, None) if not found."""
    if ManagementSession is None or not management_id:
        return None, None
    sess = ManagementSession()
    try:
        mgmt = sess.query(ManagementMission).filter(
            ManagementMission.id == management_id,
            ManagementMission.deleted == False,
        ).first()
        return sess, mgmt
    except Exception:
        sess.close()
        return None, None


def _sync_update_to_management(mission):
    """Sync changed fields back to the management mission (direct DB write)."""
    if not mission.management_id:
        return
    sess, mgmt = _get_management_mission(mission.management_id)
    if mgmt is None:
        if sess:
            sess.close()
        return
    try:
        for attr, dst in [
            ("title",               "title"),
            ("description",         "description"),
            ("category",            "category"),
            ("status",              "status"),
            ("delay_days",          "delay_days"),
            ("final_sc",            "final_sc"),
            ("kpi_weight",          "kpi_weight"),
            ("penalty_per_day",     "penalty_per_day"),
            ("early_bonus_per_day", "early_bonus_per_day"),
            ("max_bonus",           "max_bonus"),
            ("max_penalty",         "max_penalty"),
        ]:
            val = getattr(mission, attr, None)
            if val is not None:
                setattr(mgmt, dst, val)
        if mission.deadline_datetime:
            mgmt.deadline = mission.deadline_datetime.date()
        if mission.finish_datetime:
            mgmt.finish_date = mission.finish_datetime.date()
        if mission.executor_id:
            mgmt.gennis_executor_id = mission.executor_id
        sess.commit()
    except Exception as exc:
        sess.rollback()
        _logger.warning("[management sync] Gennis update failed: %s", exc)
    finally:
        sess.close()


def _sync_delete_to_management(mission):
    """Soft-delete the management mission when it is deleted in Gennis."""
    if not mission.management_id:
        return
    sess, mgmt = _get_management_mission(mission.management_id)
    if mgmt is None:
        if sess:
            sess.close()
        return
    try:
        mgmt.deleted = True
        sess.commit()
    except Exception as exc:
        sess.rollback()
        _logger.warning("[management sync] Gennis delete failed: %s", exc)
    finally:
        sess.close()

missions_bp = Blueprint("missions", __name__)
up_bp = Blueprint("up_bp", __name__)



@missions_bp.route("/", methods=["GET"])
def list_missions():
    q = Mission.query.options(
        joinedload(Mission.creator),
        joinedload(Mission.executor),
        joinedload(Mission.reviewer),
        joinedload(Mission.redirected_by),
        joinedload(Mission.tags),
        joinedload(Mission.comments).joinedload(MissionComment.user),
        joinedload(Mission.subtasks),
        joinedload(Mission.proofs),
        joinedload(Mission.attachments)
    )

    status = request.args.get("status")
    category = request.args.get("category")
    creator = request.args.get("creator")
    executor = request.args.get("executor")
    reviewer = request.args.get("reviewer")
    d_after = request.args.get("deadline_after")
    d_before = request.args.get("deadline_before")

    if status:
        q = q.filter(Mission.status == status)

    if category:
        q = q.filter(Mission.category == category)

    if executor:
        executor_id = int(executor)
        q = q.filter(
            or_(
                Mission.executor_id == executor_id,
                and_(
                    Mission.is_redirected == True,
                    Mission.redirected_by_id == executor_id
                )
            )
        )

    if reviewer:
        q = q.filter(Mission.reviewer_id == int(reviewer))

    if d_after:
        q = q.filter(Mission.deadline_datetime >= datetime.fromisoformat(d_after))

    if d_before:
        q = q.filter(Mission.deadline_datetime <= datetime.fromisoformat(d_before))

    items = q.order_by(Mission.created_at.desc()).all()
    schema = MissionDetailSchema()

    # ⛔ executor/reviewer bo‘lsa — OLDINGIDEK
    if executor or reviewer or not creator:
        data = schema.dump(items, many=True)
        for d in data:
            d["is_grouped"] = False
        return jsonify(data), 200

    # ✅ CREATOR UCHUN GROUPING
    grouped = {}

    for m in items:
        key = (
            m.title,
            m.description,
            m.category,
            m.deadline_datetime,
            m.creator_id
        )

        dumped = schema.dump(m)

        if key not in grouped:
            base = dumped.copy()
            base["is_grouped"] = True
            base["children"] = []
            grouped[key] = base

        grouped[key]["children"].append(dumped)

    return jsonify(list(grouped.values())), 200


@missions_bp.route("/", methods=["POST"])
def create_mission():
    json_data = request.get_json() or {}

    try:
        data = MissionCreateSchema().load(json_data)
    except ValidationError as err:
        return jsonify(err.messages), 400

    # Authdan kelishi kerak (misol uchun jsondan olyapmiz)
    creator_id = json_data.get("creator_id")
    executor_ids = json_data.get("executor_ids", [])

    if not creator_id:
        return jsonify({"detail": "creator_id required"}), 400

    if not executor_ids or not isinstance(executor_ids, list):
        return jsonify({"detail": "executor_ids must be non-empty list"}), 400

    created_missions = []

    for executor_id in executor_ids:
        mission = Mission(
            title=data["title"],
            description=data.get("description"),
            category=data.get("category", "academic"),
            creator_id=creator_id,
            executor_id=executor_id,
            reviewer_id=data.get("reviewer_id"),
            location_id=data.get("location_id"),
            start_datetime=data.get("start_datetime") or datetime.utcnow(),
            deadline_datetime=data["deadline_datetime"],
            status=data.get("status", "not_started"),
            is_recurring=data.get("is_recurring", False),
            repeat_every=data.get("repeat_every", 1),
            kpi_weight=data.get("kpi_weight", 10),
            penalty_per_day=data.get("penalty_per_day", 2),
            early_bonus_per_day=data.get("early_bonus_per_day", 1),
            max_bonus=data.get("max_bonus", 3),
            max_penalty=data.get("max_penalty", 10),
        )

        db.session.add(mission)
        db.session.flush()  # mission.id olish uchun

        # TAGS
        tag_ids = json_data.get("tags", [])
        if tag_ids:
            tags = Tag.query.filter(Tag.id.in_(tag_ids)).all()
            mission.tags = tags

        # NOTIFICATION
        send_notification(
            user_id=executor_id,
            mission=mission,
            message=f"Sizga task berildi: {mission.title}",
            role="executor"
        )

        created_missions.append(mission)

    db.session.commit()

    schema = MissionDetailSchema(many=True)
    return jsonify(schema.dump(created_missions)), 201


@missions_bp.route("/<int:pk>/", methods=["GET"])
def retrieve_mission(pk):
    m = Mission.query.get_or_404(pk)
    schema = MissionDetailSchema()
    return jsonify(schema.dump(m)), 200


@missions_bp.route("/<int:pk>/", methods=["PATCH", "PUT"])
def update_mission(pk):
    m = Mission.query.get_or_404(pk)
    json_data = request.get_json() or {}

    old_status = m.status
    old_executor_id = m.executor_id

    # =========================
    # EXECUTOR CHANGE / REDIRECT
    # =========================
    raw_executor = json_data.get("executor_id") or (json_data.get("executor_ids") or [None])[0]
    if raw_executor is not None:
        new_executor_id = int(raw_executor)

        if new_executor_id != old_executor_id:
            m.executor_id = new_executor_id
            m.is_redirected = True
            m.redirected_at = datetime.utcnow()
            m.redirected_by_id = old_executor_id

            # Record history locally
            old_executor_user = Users.query.get(old_executor_id)
            new_executor_user = Users.query.get(new_executor_id)
            old_name = f"{old_executor_user.name} {old_executor_user.surname}".strip() if old_executor_user else None
            new_name = f"{new_executor_user.name} {new_executor_user.surname}".strip() if new_executor_user else None
            history = MissionHistory(
                mission_id=m.id,
                executor_id=new_executor_id,
                changed_by_name=old_name,
                note=f"Redirected to {new_name}",
            )
            db.session.add(history)

            # Sync history to management
            if m.management_id:
                sync_history_to_management(
                    mission_management_id=m.management_id,
                    gennis_executor_id=new_executor_id,
                    gennis_executor_name=new_name,
                    note=f"Redirected by {old_name}",
                )

            send_notification(
                user_id=new_executor_id,
                mission=m,
                message=f"Sizga task berildi: {m.title}",
                role="executor"
            )

    # =========================
    # BASIC FIELDS
    # =========================
    if "reviewer_id" in json_data:
        new_reviewer_id = json_data["reviewer_id"]
        old_reviewer_id = m.reviewer_id

        if new_reviewer_id != old_reviewer_id:
            m.reviewer_id = new_reviewer_id

            new_reviewer_user = Users.query.get(new_reviewer_id) if new_reviewer_id else None
            old_reviewer_user = Users.query.get(old_reviewer_id) if old_reviewer_id else None
            new_reviewer_name = f"{new_reviewer_user.name} {new_reviewer_user.surname}".strip() if new_reviewer_user else None
            old_reviewer_name = f"{old_reviewer_user.name} {old_reviewer_user.surname}".strip() if old_reviewer_user else None

            history = MissionHistory(
                mission_id=m.id,
                reviewer_id=new_reviewer_id,
                changed_by_name=old_reviewer_name,
                note=f"Reviewer changed to {new_reviewer_name}",
            )
            db.session.add(history)

            if m.management_id:
                sync_history_to_management(
                    mission_management_id=m.management_id,
                    gennis_reviewer_id=new_reviewer_id,
                    gennis_reviewer_name=new_reviewer_name,
                    note=f"Reviewer changed by {old_reviewer_name}",
                )
        else:
            m.reviewer_id = new_reviewer_id

    if "deadline_datetime" in json_data:
        m.deadline_datetime = datetime.fromisoformat(json_data["deadline_datetime"])

    if "title" in json_data:
        m.title = json_data["title"]

    if "description" in json_data:
        m.description = json_data["description"]

    if "category" in json_data:
        m.category = json_data["category"]

    # =========================
    # STATUS CHANGE (signal analog)
    # =========================
    if "status" in json_data:
        new_status = json_data["status"]

        if new_status != old_status:
            if new_status == "completed" and not m.finish_datetime:
                m.finish_datetime = datetime.utcnow()
                m.calculate_delay()
                m.final_sc = m.compute_final_score()

            m.status = new_status
            db.session.commit()

            on_mission_status_change(old_status, new_status, m)

    # =========================
    # TAGS
    # =========================
    if "tags" in json_data:
        tag_ids = json_data.get("tags", [])
        tags = Tag.query.filter(Tag.id.in_(tag_ids)).all()
        m.tags = tags

    # =========================
    # RECURRING
    # =========================
    if "is_recurring" in json_data:
        m.is_recurring = bool(json_data["is_recurring"])

    if "repeat_every" in json_data:
        m.repeat_every = int(json_data["repeat_every"])

    db.session.commit()
    _sync_update_to_management(m)

    return jsonify(MissionDetailSchema().dump(m)), 200


@missions_bp.route("/<int:pk>/history/", methods=["GET"])
def mission_history(pk):
    Mission.query.get_or_404(pk)
    history = (
        MissionHistory.query
        .filter_by(mission_id=pk)
        .order_by(MissionHistory.created_at.asc())
        .all()
    )
    return jsonify(MissionHistorySchema().dump(history, many=True)), 200


@missions_bp.route("/<int:pk>/", methods=["DELETE"])
def delete_mission(pk):
    m = Mission.query.get_or_404(pk)
    _sync_delete_to_management(m)
    db.session.delete(m)
    db.session.commit()
    return jsonify({"detail": "deleted"}), 200


@up_bp.route('/<path:filename>')
def uploaded_files(filename):
    from backend.models.config import UPLOAD_BASE
    return send_from_directory(UPLOAD_BASE, filename)
