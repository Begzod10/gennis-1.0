from dotenv import load_dotenv

from backend.models.models import Students, Groups, AttendanceDays, Users, Subjects, db
from sqlalchemy import desc, or_
from sqlalchemy.orm import contains_eager

load_dotenv()


# for teachers.py

def send_telegram_message(student_id, attendance_id, group_id):
    import os
    import requests
    get_group = Groups.query.get(group_id)
    get_subject = Subjects.query.get(get_group.subject_id)
    bot_token = os.getenv("TOKEN")
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    attendance = AttendanceDays.query.filter(AttendanceDays.id == attendance_id).first()
    print("attendance", attendance)
    student = Students.query.filter(Students.id == student_id).first()

    if not attendance or not student:
        return {"error": "Invalid student or attendance"}

    # Get parent(s)
    parents = student.parent

    # Student full name
    full_name = f"{student.user.name.title()} {student.user.surname.title()}"

    # Attendance status interpretation
    if attendance.status == 0:
        status_text = "❌ Darsda yo‘q"
        scores_text = ""
    elif attendance.status == 2:
        status_text = "✅ Darsda qatnashdi"
        if get_subject.ball_number > 2:
            scores_text = (
                f"\n📚 <b>Lug'at:</b> {attendance.dictionary or 0}"
                f"\n📝 <b>Uy vazifa:</b> {attendance.homework or 0}"
                f"\n🎯 <b>Faollik:</b> {attendance.activeness or 0}"
                f"\n📊 <b>O'rtacha ball:</b> {attendance.average_ball or 0}"
            )
        else:
            scores_text = (
                f"\n📝 <b>Uy vazifa:</b> {attendance.homework or 0}"
                f"\n🎯 <b>Faollik:</b> {attendance.activeness or 0}"
                f"\n📊 <b>O'rtacha ball:</b> {attendance.average_ball or 0}"
            )
    else:
        status_text = "✅ Darsda qatnashdi"
        scores_text = "Baholanmadi"

    text = (
        f"<b>{full_name}</b>\n"
        f"<b>Sana:</b> {attendance.day.date.strftime('%Y-%m-%d')}\n"
        f"{status_text}"
        f"{scores_text}"
    )

    # Send to all parents

    for parent in parents:
        user = Users.query.get(parent.user_id)
        if user and user.telegram_id:
            payload = {
                "chat_id": user.telegram_id,
                "text": text,
                "parse_mode": "HTML"
            }
            response = requests.post(url, data=payload)
    if student.user.telegram_id:
        payload = {
            "chat_id": student.user.telegram_id,
            "text": text,
            "parse_mode": "HTML"
        }
        response = requests.post(url, data=payload)
    return {"status": "done"}


def prepare_scores(subject_ball_number):
    base_scores = [
        {"name": "homework", "id": 1, "title": "Uy ishi", "activeStars": 0, "stars": [{"active": False}] * 5},
        {"name": "active", "id": 1, "title": "Darsda qatnashishi", "activeStars": 0, "stars": [{"active": False}] * 5}
    ]

    if subject_ball_number > 2:
        base_scores.append(
            {"name": "dictionary", "id": 1, "title": "Lug'at", "activeStars": 0, "stars": [{"active": False}] * 5})

    return base_scores


def get_students_info(group_id, hour2):
    students = db.session.query(Students).join(Students.group).options(contains_eager(Students.group)).filter(
        Groups.id == group_id, or_(Students.ball_time <= hour2, Students.ball_time == None)
    ).order_by(Students.id).all()

    student_list = []
    for student in students:
        debtor_color = ["green", "yellow", "red", "navy", "black"][student.debtor]
        student_info = {
            "id": student.user.id,
            "name": student.user.name.title(),
            "surname": student.user.surname.title(),
            "money": student.user.balance,
            "active": False,
            "checked": False,
            "profile_photo": student.user.photo_profile,
            "typeChecked": "",
            "date": {},
            "scores": {},
            "money_type": debtor_color
        }
        student_list.append(student_info)
    return student_list
