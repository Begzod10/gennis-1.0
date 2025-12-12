from datetime import datetime, timedelta, date
from backend.tasks.models.models import Notification, db


def send_notification(user_id, mission, message, role):
    notif = Notification(
        user_id=user_id,
        mission_id=mission.id,
        message=message,
        role=role,
        deadline=mission.deadline_datetime.date() if mission.deadline_datetime else None
    )
    db.session.add(notif)
    db.session.commit()


def deadline_check_for_user(user_id, mission):
    today = datetime.now().date()

    if not mission.deadline_datetime:
        return

    # deadline_datetime -> date() format
    mission_deadline = mission.deadline_datetime.date()

    # 1 kun qolgan bo'lsa
    if mission_deadline == today + timedelta(days=1):

        exists = Notification.query.filter(
            Notification.user_id == user_id,
            Notification.mission_id == mission.id,
            Notification.message.contains("deadline yaqin"),
            Notification.role == "executor"
        ).first()

        if not exists:
            send_notification(
                user_id,
                mission,
                f"Vazifa '{mission.title}' deadline yaqin: {mission_deadline}",
                "executor"
            )

    # deadline o‘tib ketgan bo'lsa
    elif mission_deadline < today:

        exists = Notification.query.filter(
            Notification.user_id == user_id,
            Notification.mission_id == mission.id,
            Notification.message.contains("o‘tib ketdi"),
            Notification.role == "executor"
        ).first()

        if not exists:
            send_notification(
                user_id,
                mission,
                f"Vazifa '{mission.title}' deadline o‘tib ketdi!",
                "executor"
            )


def on_mission_status_change(old_status, new_status, mission):
    executor = mission.executor
    creator = mission.creator
    reviewer = mission.reviewer

    # 1) Executor started → creator’ga
    if new_status == "in_progress":
        send_notification(
            user_id=creator.id,
            mission=mission,
            message=f"{executor.name} vazifani boshladi: {mission.title}",
            role="creator"
        )

    # 2) Executor finished → reviewer’ga
    if new_status == "completed" and reviewer:
        send_notification(
            user_id=reviewer.id,
            mission=mission,
            message=f"{executor.name} '{mission.title}' vazifasini tugatdi. Ko‘rib chiqing.",
            role="reviewer"
        )

    # 3) Reviewer tasdiqladi → executor’ga
    if new_status == "approved":
        send_notification(
            user_id=executor.id,
            mission=mission,
            message=f"'{mission.title}' tasdiqlandi.",
            role="executor"
        )

        send_notification(
            user_id=creator.id,
            mission=mission,
            message=f"'{mission.title}' tugallandi.",
            role="creator"
        )

    # 4) Reviewer qaytardi → executor’ga
    if new_status == "recheck":
        send_notification(
            user_id=executor.id,
            mission=mission,
            message=f"'{mission.title}' qayta tekshirish uchun qaytarildi.",
            role="executor"
        )

    # 5) Reviewer rad qildi → executor’ga
    if new_status == "declined":
        send_notification(
            user_id=executor.id,
            mission=mission,
            message=f"'{mission.title}' rad qilindi.",
            role="executor"
        )
