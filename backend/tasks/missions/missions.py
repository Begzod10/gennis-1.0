from datetime import date, datetime
from sqlalchemy.orm import joinedload
from flask import Blueprint, request, jsonify, send_from_directory
from marshmallow import ValidationError
from backend.tasks.missions.marshmallow import MissionCreateSchema, MissionDetailSchema
from backend.tasks.models.models import Mission, db, Tag, MissionComment
from backend.tasks.missions.utils import create_notification
from backend.tasks.missions.signals import on_mission_status_change, send_notification

missions_bp = Blueprint("missions", __name__)
up_bp = Blueprint("up_bp", __name__)


@missions_bp.route("/", methods=["GET"])
def list_missions():
    q = Mission.query.options(
        joinedload(Mission.creator),
        joinedload(Mission.executor),
        joinedload(Mission.reviewer),
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
    if creator:
        q = q.filter(Mission.creator_id == int(creator))
    if executor:
        q = q.filter(Mission.executor_id == int(executor))
    if reviewer:
        q = q.filter(Mission.reviewer_id == int(reviewer))
    if d_after:
        q = q.filter(Mission.deadline >= date.fromisoformat(d_after))
    if d_before:
        q = q.filter(Mission.deadline <= date.fromisoformat(d_before))

    items = q.order_by(Mission.created_at.desc()).all()
    schema = MissionDetailSchema(many=True)
    return jsonify(schema.dump(items)), 200


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

    old_status = m.status  # status o‘zgarishini kuzatish

    # Executor o‘zgarganda → notification
    if "executor_id" in json_data:
        m.executor_id = json_data["executor_id"]
        send_notification(
            user_id=m.executor_id,
            mission=m,
            message=f"Sizga task berildi: {m.title}",
            role="executor"
        )

    if "reviewer_id" in json_data:
        m.reviewer_id = json_data["reviewer_id"]

    if "deadline" in json_data:
        m.deadline_datetime = datetime.fromisoformat(json_data["deadline"])

    if "title" in json_data:
        m.title = json_data["title"]

    if "description" in json_data:
        m.description = json_data["description"]

    if "category" in json_data:
        m.category = json_data["category"]

    # STATUS CHANGE
    if "status" in json_data:
        new_status = json_data["status"]

        # Agar status o‘zgargan bo‘lsa → Django signaliga o‘xshatamiz
        if new_status != old_status:
            # Agar completed bo‘lsa → finish_date qo‘yiladi
            if new_status == "completed" and not m.finish_datetime:
                m.finish_datetime = datetime.utcnow()
                m.calculate_delay()
                m.final_sc = m.compute_final_score()

            m.status = new_status
            db.session.commit()

            # Django signaliga to‘liq analog
            on_mission_status_change(old_status, new_status, m)

    # Tags
    if "tags" in json_data:
        tag_ids = json_data.get("tags", [])
        tags = Tag.query.filter(Tag.id.in_(tag_ids)).all()
        m.tags = tags

    # Recurring
    if "is_recurring" in json_data:
        m.is_recurring = bool(json_data["is_recurring"])

    if "repeat_every" in json_data:
        m.repeat_every = int(json_data["repeat_every"])

    db.session.commit()

    schema = MissionDetailSchema()
    return jsonify(schema.dump(m)), 200


@missions_bp.route("/<int:pk>/", methods=["DELETE"])
def delete_mission(pk):
    m = Mission.query.get_or_404(pk)
    db.session.delete(m)
    db.session.commit()
    return jsonify({"detail": "deleted"}), 200


@up_bp.route('/<path:filename>')
def uploaded_files(filename):
    from backend.models.config import UPLOAD_BASE
    return send_from_directory(UPLOAD_BASE, filename)
