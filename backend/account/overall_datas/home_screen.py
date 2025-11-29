import pprint

from backend.models.models import Staff, Users, EducationLanguage, Professions
from backend.models.models import Teachers, TeacherSalary, StaffSalary, PaymentTypes, DeletedStaffSalaries, UserBooks, \
    StaffSalaries, TeacherSalaries, DeletedTeacherSalaries, AccountingPeriod, CalendarMonth, StudentPayments, \
    CalendarYear, Locations, TeacherBlackSalary, db, AttendanceHistoryStudent, Students, Groups, Subjects

from flask import Blueprint
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import desc
from sqlalchemy import or_
from sqlalchemy.orm import contains_eager
from datetime import datetime

home_screen_bp = Blueprint('home_screen_bp', __name__)


@home_screen_bp.route('/debtors/', methods=['GET'])
# @jwt_required()
def home_screen_debtors():
    location_id = request.args.get('location_id')
    month = request.args.get('month')
    year = request.args.get('year')
    month_date = year + '-' + month
    year_obj = datetime.strptime(year, '%Y')
    month_date_obj = datetime.strptime(month_date, '%Y-%m')

    year_id = CalendarYear.query.filter(CalendarYear.date == year_obj).first().id
    month_id = CalendarMonth.query.filter(
        CalendarMonth.date == month_date_obj,
        CalendarMonth.year_id == year_id
    ).first().id

    # Get all attendance history with related data in one query
    attendance_records = (
        db.session.query(
            AttendanceHistoryStudent,
            Students,
            Users,
            Groups,
            Subjects
        )
        .join(Students, AttendanceHistoryStudent.student_id == Students.id)
        .join(Users, Students.user_id == Users.id)
        .join(Groups, AttendanceHistoryStudent.group_id == Groups.id)
        .join(Subjects, Groups.subject_id == Subjects.id)
        .filter(
            AttendanceHistoryStudent.calendar_month == month_id,
            AttendanceHistoryStudent.calendar_year == year_id,
            Users.location_id == location_id,
            Groups.status == True
        )
        .order_by(Students.id)
        .all()
    )

    # Group by student
    students_dict = {}
    total_debt = 0
    remaining_debt = 0
    payment = 0
    for attendance, student, user, group, subject in attendance_records:
        if student.id not in students_dict:
            students_dict[student.id] = {
                'id': student.id,
                'student_name': f"{user.name} {user.surname}",
                "month": month_date_obj.strftime("%Y-%m"),
                "groups": []
            }
        total_debt += attendance.total_debt if attendance.total_debt else 0
        remaining_debt += attendance.remaining_debt if attendance.remaining_debt else 0
        payment += attendance.payment if attendance.payment else 0
        students_dict[student.id]['groups'].append({
            'group_name': group.name,
            "subject_name": subject.name,
            "remaining_debt": attendance.remaining_debt,
            "total_debt": attendance.total_debt,
            "payment": attendance.payment
        })

    attendance_history_list = list(students_dict.values())

    return jsonify({
        "student_list": attendance_history_list,
        "total_debt": total_debt,
        "remaining_debt": remaining_debt,
        "payment": payment

    })
