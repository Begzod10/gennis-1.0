import datetime

from app import app, db, jsonify
from backend.models.models import Users, Students, or_, DeletedStudents, CalendarDay
from backend.functions.utils import api, find_calendar_date
from sqlalchemy import asc


@app.route(f'{api}/student_debts/<int:location_id>', methods=["POST", "GET"])
def student_debts(location_id):
    day = datetime.datetime.strptime("2024-08-01", "%Y-%m-%d")  # "2024-08-01"
    month = datetime.datetime.strptime("2024-08", "%Y-%m")  # "2024-08"
    year = datetime.datetime.strptime("2024", "%Y")  # "2024"
    calendar_year, calendar_month, calendar_day = find_calendar_date(date_day=day, date_month=month, date_year=year)

    deleted_students = (
        db.session.query(DeletedStudents)
        .join(Students, DeletedStudents.student_id == Students.id)  # Ensure proper join condition
        .join(Users, Students.user_id == Users.id)  # Ensure proper join condition
        .filter(
            Users.location_id == location_id,
            DeletedStudents.calendar_day == calendar_day.id
        )
        .all()
    )

    print(len(deleted_students))

    students = db.session.query(Students).join(Students.user).filter(Users.balance < 0,
                                                                     Users.location_id == location_id
                                                                     ).filter(

        Students.deleted_from_register == None,
        or_(Students.deleted_from_group != None, Students.group != None)).order_by(
        asc(Users.balance)).limit(100).all()

    return jsonify({
        "status": "true",
        "deleted_students": len(deleted_students),
        "students": len(students)
    })
