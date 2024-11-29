from app import app, db, jsonify, request
from backend.models.models import Users, Students, or_, DeletedStudents, CalendarDay, CalendarMonth, CalendarYear, \
    StudentExcuses
from sqlalchemy import asc
from backend.functions.utils import find_calendar_date


def filter_debts(location_id, month):
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    deleted_student_ids = (
        db.session.query(DeletedStudents.student_id)
        .join(Students, DeletedStudents.student_id == Students.id)
        .join(Users, Students.user_id == Users.id)
        .join(CalendarDay, DeletedStudents.calendar_day == CalendarDay.id)
        .join(CalendarMonth, CalendarDay.month_id == CalendarMonth.id)
        .filter(
            Users.location_id == location_id,
            CalendarMonth.date >= month
        )
        .distinct()  # Ensure unique IDs
        .all()
    )

    # Extract IDs as a list

    deleted_student_ids = [row[0] for row in deleted_student_ids]  # Convert result tuples to a list of IDs

    # Second Query: Get students filtered by the first query

    students = (
        db.session.query(Students)
        .join(Users, Students.user_id == Users.id)
        .filter(
            Users.balance < 0,
            Users.location_id == location_id,
            or_(
                Students.id.in_(deleted_student_ids),  # Include students matching deleted IDs
                Students.deleted_from_register == None  # Include other students with `deleted_from_register` as None
            )
        )
        .outerjoin(Students.excuses)  # Use an outer join to include students without excuses
        .filter(
            or_(
                StudentExcuses.to_date > calendar_day.date,  # Excuses valid after the calendar day
                StudentExcuses.id == None  # Students with no excuses
            )
        )
        .order_by(asc(Users.balance))
        .limit(100)
        .all()
    )
    return students, deleted_student_ids
