from flask import Blueprint, request, jsonify
from datetime import date
from sqlalchemy import or_
from backend.tasks.models.models import Notification, Mission, db
from backend.tasks.missions.signals import deadline_check_for_user

notif_bp = Blueprint("notifications", __name__)


@notif_bp.route("/", methods=["GET"])
def get_notifications():
    user_id = request.args.get("user_id", type=int)
    role = request.args.get("role")

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

    if role:
        query = query.filter_by(role=role)

    query = query.filter(
        or_(
            # Notification.is_read == False,
            Notification.deadline >= today
        )
    )

    notifications = query.order_by(Notification.created_at.desc()).all()

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


@notif_bp.route("/<int:id>", methods=["PATCH"])
def update_notification(id):
    notif = Notification.query.get_or_404(id)

    notif.is_read = True
    db.session.commit()

    return jsonify({"message": "read"}), 200
