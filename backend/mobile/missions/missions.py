from datetime import datetime, date

from flask import Blueprint, request, jsonify
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from backend.mobile.missions.marshmallow import MobileMissionListSchema, MobileMissionDetailSchema, CommentSchema
from backend.tasks.missions.signals import deadline_check_for_user
from backend.tasks.missions.signals import on_mission_status_change, send_notification
from backend.tasks.models.models import Mission, db, MissionComment, Notification

missions_bp = Blueprint("mobile_missions", __name__)


@missions_bp.route("/missions/", methods=["GET"])
def mobile_list_missions():
    user_id = int(request.args.get("user_id"))

    q = Mission.query.filter(Mission.executor_id == user_id)

    # 🔹 query params
    status = request.args.get("status")

    if status:
        q = q.filter(Mission.status == status)

    missions = q.order_by(Mission.deadline_datetime.asc()).all()

    return jsonify(
        MobileMissionListSchema(many=True).dump(missions)
    ), 200


@missions_bp.route("/missions_detail/<int:mission_id>/", methods=["GET"])
def mobile_mission_detail(mission_id):
    mission = Mission.query.options(
        joinedload(Mission.comments),
        joinedload(Mission.proofs),
        joinedload(Mission.attachments)
    ).filter_by(
        id=mission_id
    ).first_or_404()

    return jsonify(MobileMissionDetailSchema().dump(mission)), 200


@missions_bp.route("/missions/<int:mission_id>/status/", methods=["PATCH"])
def mobile_update_status(mission_id):
    mission = Mission.query.filter_by(
        id=mission_id
    ).first_or_404()

    new_status = request.json.get("status")
    old_status = mission.status

    if new_status != old_status:
        mission.status = new_status

        if new_status == "completed" and not mission.finish_datetime:
            mission.finish_datetime = datetime.utcnow()
            mission.calculate_delay()
            mission.final_sc = mission.compute_final_score()

        db.session.commit()

        # 🔔 NOTIFICATION
        on_mission_status_change(old_status, new_status, mission)

    return jsonify({"status": mission.status}), 200


@missions_bp.route("/missions/<int:mission_id>/comments/", methods=["POST"])
def mobile_add_comment(mission_id):
    user_id = request.args.get("user_id")

    mission = Mission.query.filter_by(
        id=mission_id
    ).first_or_404()

    text = request.json.get("text")
    comment = MissionComment(
        mission_id=mission.id,
        user_id=user_id,
        text=text
    )
    db.session.add(comment)
    db.session.commit()
    print(mission.executor)

    # 🔔 NOTIFICATION (creator ga)
    send_notification(
        user_id=mission.creator_id,
        mission=mission,
        message=f"{mission.executor.name} {mission.executor.surname} comment qoldirdi",
        role="creator"
    )

    return jsonify(CommentSchema().dump(comment)), 201


@missions_bp.route("/notifications/", methods=["GET"])
def get_notifications():
    user_id = request.args.get("user_id", type=int)

    today = date.today()

    # deadline tekshirish
    if user_id:
        missions = Mission.query.filter(
            Mission.executor_id == user_id,
            Mission.status.in_(["not_started", "in_progress"])
        ).all()

        for m in missions:
            deadline_check_for_user(user_id, m)

    # asosiy queryset
    query = Notification.query

    if user_id:
        query = query.filter_by(user_id=user_id)

    query = query.filter_by(role="executer")

    query = query.filter(
        or_(
            # Notification.is_read == False,
            Notification.deadline >= today
        )
    )

    notifications = query.order_by(Notification.created_at.desc()).all()
    print(notifications)

    return jsonify([
        {
            "id": n.id,
            "message": n.message,
            "mission_id": n.mission_id,
            "role": n.role,
            "is_read": n.is_read,
            "deadline": str(n.deadline),
            "created_at": n.created_at.strftime("%Y-%m-%d %H:%M")
        }
        for n in notifications
    ])


@missions_bp.route("/notifications/<int:id>/", methods=["PATCH"])
def update_notification(id):
    notif = Notification.query.get_or_404(id)

    notif.is_read = True
    db.session.commit()

    return jsonify({"message": "read"}), 200