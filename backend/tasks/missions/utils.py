from backend.tasks.models.models import Mission, Notification, MissionAttachment, MissionComment, MissionProof, Tag, db
from datetime import date, timedelta
from flask import current_app
import os
from werkzeug.utils import secure_filename

ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'pdf', 'docx', 'xlsx', 'xls', 'mp4', 'mov'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT


def recurring_check():
    """Check recurring missions, create new ones if needed."""
    today = date.today()
    # keep it small: query only recurring True
    tasks = Mission.query.filter(Mission.is_recurring == True).all()
    for t in tasks:
        if t.last_generated == today:
            continue
        interval = t.repeat_every or 1
        next_generate_day = t.deadline + timedelta(days=interval)
        if today >= next_generate_day:
            # create copy
            new = Mission(
                title=t.title,
                description=t.description,
                category=t.category,
                creator_id=t.creator_id,
                executor_id=t.executor_id,
                reviewer_id=t.reviewer_id,
                branch_id=t.branch_id,
                deadline=next_generate_day,
                is_recurring=True,
                repeat_every=t.repeat_every,
                kpi_weight=t.kpi_weight,
                penalty_per_day=t.penalty_per_day
            )
            db.session.add(new)
            t.last_generated = today
            db.session.commit()
            # create notification for executor
            create_notification(user_id=new.executor_id, mission_id=new.id,
                                message=f"Yangi recurring task yaratildi: {new.title}", role="executor")


def create_notification(user_id, mission_id=None, message="", role="executor", deadline=None):
    n = Notification(user_id=user_id, mission_id=mission_id, message=message, role=role, deadline=deadline)
    db.session.add(n)
    db.session.commit()


def notify_deadlines():
    today = date.today()
    soon = today
    # upcoming: tasks with deadline == today+1
    upcoming = Mission.query.filter(Mission.deadline == today + timedelta(days=1)).all()
    for m in upcoming:
        create_notification(user_id=m.executor_id, mission_id=m.id,
                            message=f"Task deadline yaqin: {m.title} (ertaga)", role="executor", deadline=m.deadline)
    overdue = Mission.query.filter(Mission.deadline < today, Mission.finish_date == None).all()
    for m in overdue:
        create_notification(user_id=m.executor_id, mission_id=m.id,
                            message=f"Task overdue: {m.title}", role="executor", deadline=m.deadline)



def create_deadline_notifications(mission):
    days = mission.remaining_days()
    if days is None:
        return

    # 1) O‘tgan bo‘lsa (deadline < today)
    if days < 0:
        exists = Notification.query.filter_by(
            mission_id=mission.id,
            role="executor",
            message="Deadline o'tib ketdi!"
        ).first()

        if not exists:
            notif = Notification(
                user_id=mission.executor_id,
                mission_id=mission.id,
                message="Deadline o'tib ketdi!",
                role="executor",
                deadline=mission.deadline_datetime.date()
            )
            db.session.add(notif)
            db.session.commit()
        return

    # 2) 1 kun qolganda
    if days == 1:
        exists = Notification.query.filter_by(
            mission_id=mission.id,
            role="executor",
            message="Deadline 1 kun qoldi!"
        ).first()

        if not exists:
            notif = Notification(
                user_id=mission.executor_id,
                mission_id=mission.id,
                message="Deadline 1 kun qoldi!",
                role="executor",
                deadline=mission.deadline_datetime.date()
            )
            db.session.add(notif)
            db.session.commit()