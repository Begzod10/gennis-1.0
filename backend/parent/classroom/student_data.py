from sqlalchemy.orm import joinedload
from backend.teacher.utils import send_telegram_message

from backend.account.models import StudentPayments, BookPayments
from backend.group.models import AttendanceHistoryStudent, GroupTest
from backend.models.models import Users, Roles, CalendarMonth, CalendarDay, CalendarYear, Attendance, AttendanceDays, \
    Students, Groups, Teachers, StudentCharity, Subjects, SubjectLevels, TeacherBlackSalary, StaffSalary, \
    DeletedTeachers, Locations, LessonPlan, Group_Room_Week, Parent, db
from werkzeug.security import check_password_hash
from backend.functions.utils import api, refresh_age, update_salary, iterate_models, get_json_field, check_exist_id, \
    find_calendar_date, update_school_salary
from datetime import datetime
from backend.functions.debt_salary_update import salary_debt
from flask_jwt_extended import jwt_required, create_refresh_token, create_access_token, get_jwt_identity

from backend.student.models import StudentTest
from datetime import timedelta

from flask import Blueprint, jsonify, request

classroom_bp = Blueprint('classroom', __name__)


@classroom_bp.route(f'/get_group_datas/<int:group_id>')
@jwt_required()
def get_group_datas(group_id):
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity)
    students = Students.query.join(Students.group).filter(Groups.id == group_id).all()
    group = Groups.query.filter(Groups.id == group_id).first()
    users = Users.query.filter(Users.id.in_([user.user.id for user in students])).all()
    return jsonify({
        "users": iterate_models(users),
        "access_token": access_token,
        "group": group.convert_json()
    })


@classroom_bp.route(f'/update_group_datas', methods=['POST'])
@jwt_required()
def update_group_datas():
    group = Groups.query.filter(Groups.id == request.get_json()['group']['platform_id']).first()
    if request.get_json()['group']['course']:
        level = SubjectLevels.query.filter(
            SubjectLevels.classroom_id == request.get_json()['group']['course']['id']).first()
        if not level:
            level = SubjectLevels.query.filter(
                SubjectLevels.name == request.get_json()['group']['course']['name']).first()
        group.level_id = level.id
    return jsonify({
        "msg": "O'zgarildi"
    })


@classroom_bp.route(f'/update_user/<user_id>', methods=['POST'])
@jwt_required()
def update_user(user_id):
    Users.query.filter(Users.id == user_id).update({
        "user_id": get_json_field('user_id')
    })
    db.session.commit()
    return jsonify({
        "msg": "User id o'zgartirildi"
    })


@classroom_bp.route(f'/student_attendance_dates_classroom/<platform_id>')
def student_attendance_dates_classroom(platform_id):
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    year_list = []
    month_list = []
    user = Users.query.filter(Users.id == platform_id).first()
    student = Students.query.filter(Students.id == user.student.id).first()
    attendance_month = AttendanceHistoryStudent.query.filter(
        AttendanceHistoryStudent.student_id == student.id,
    ).order_by(AttendanceHistoryStudent.id).all()
    for attendance in attendance_month:
        year = AttendanceHistoryStudent.query.filter(AttendanceHistoryStudent.student_id == student.id,

                                                     AttendanceHistoryStudent.calendar_year == attendance.calendar_year).all()
        info = {
            'year': '',
            'months': []
        }
        if info['year'] != attendance.year.date.strftime("%Y"):
            info['year'] = attendance.year.date.strftime("%Y")
        for month in year:
            if attendance.year.date.strftime("%Y") not in year_list:
                year_list.append(attendance.year.date.strftime("%Y"))
            if month.month.date.strftime("%m") not in info['months']:
                info['months'].append(month.month.date.strftime("%m"))
                info['months'].sort()
        month_list.append(info)

    day_dict = {gr['year']: gr for gr in month_list}
    filtered_list = list(day_dict.values())
    year_list = list(reversed(year_list))
    return jsonify({
        "data": {
            "months": filtered_list,
            "years": year_list,
            "current_year": calendar_year.date.strftime("%Y"),
            "current_month": calendar_month.date.strftime("%m"),
        }
    })


@classroom_bp.route(f"/get_student_group_list/<int:platform_id>/<int:year>/<int:month>", methods=['GET'])
def get_student_group_list(platform_id, year, month):
    user = Users.query.filter(Users.id == platform_id).first()

    student = user.student

    calendar_year = CalendarYear.query.filter(
        db.extract('year', CalendarYear.date) == year
    ).first()

    calendar_month = CalendarMonth.query.filter(
        db.extract('year', CalendarMonth.date) == year,
        db.extract('month', CalendarMonth.date) == month,
        CalendarMonth.year_id == calendar_year.id
    ).first()

    group_query = db.session.query(Groups).join(AttendanceHistoryStudent).filter(
        AttendanceHistoryStudent.student_id == student.id,
        AttendanceHistoryStudent.calendar_year == calendar_year.id,
        AttendanceHistoryStudent.calendar_month == calendar_month.id
    ).distinct().all()

    group_list = [{
        "id": group.id,
        "nameGroup": group.name.title(),
        "name": group.subject.name if group.subject else None
    } for group in group_query]

    return jsonify({
        "group_list": group_list
    })


@classroom_bp.route(f'/get_student_attendance_days_list/<platform_id>/',
                    defaults={"group_id": None, "year": None, "month": None})
@classroom_bp.route(f"/get_student_attendance_days_list/<platform_id>/<group_id>/<year>/<month>", methods=['GET'])
def get_student_attendance_days_list(platform_id, group_id, year, month):
    user = Users.query.filter_by(id=platform_id).first()
    student = Students.query.filter_by(user_id=user.id).first()
    uzbek_weekdays = ['Dushanba', 'Seshanba', 'Chorshanba', 'Payshanba', 'Juma', 'Shanba', 'Yakshanba']
    today = datetime.today().date()
    week_result = []

    if year and month:
        calendar_days = CalendarDay.query.filter(
            db.extract('year', CalendarDay.date) == int(year),
            db.extract('month', CalendarDay.date) == int(month)
        ).order_by(CalendarDay.date).all()
    else:
        start_of_week = today - timedelta(days=today.weekday())
        calendar_days = []
        for i in range(7):
            current_date = start_of_week + timedelta(days=i)
            day = CalendarDay.query.filter(db.func.date(CalendarDay.date) == current_date).first()
            calendar_days.append(day if day else CalendarDay(date=current_date))

    groups = [Groups.query.get(int(group_id))] if group_id and group_id != "None" else student.group

    for day in calendar_days:
        if not day: continue

        weekday_index = day.date.weekday()
        info = {
            "date": day.date.strftime("%d"),
            "weekday": uzbek_weekdays[weekday_index],
            "attendances": [],
            "is_today": day.date == today
        }

        for gr in groups:
            timetable = gr.time_table[0] if gr.time_table else None

            if day.id:
                attendance_day = AttendanceDays.query.filter_by(
                    student_id=student.id,
                    calendar_day=day.id,
                    group_id=gr.id
                ).first()
                if attendance_day:

                    attendance_info = {
                        "group": gr.subject.name,
                        "time": f"{timetable.start_time.strftime('%H:%M')} / {timetable.end_time.strftime('%H:%M')}" if timetable else "Noma'lum",
                        "day_status": bool(day.id),
                        "status": ""
                    }

                    attendance_info['status'] = "Keldi" if attendance_day.status in [1, 2] else "Kelmadi"
                    attendance_info["average_ball"] = attendance_day.average_ball
                    if attendance_day.average_ball in [4, 5]:
                        attendance_info["color"] = "green"
                    elif attendance_day.average_ball == 3:
                        attendance_info["color"] = "yellow"
                    elif attendance_day.average_ball == 2:
                        attendance_info["color"] = "red"
                    else:
                        attendance_info["color"] = "gray"

                    info['attendances'].append(attendance_info)
        if info["attendances"]:
            week_result.append(info)

    return jsonify({"msg": week_result})


@classroom_bp.route(f"/student_payments_list/<platform_id>")
def student_payments_list(platform_id):
    user = Users.query.filter(Users.id == platform_id).first()
    student = Students.query.filter(Students.user_id == user.id).first()
    attendance_histories = AttendanceHistoryStudent.query.filter(
        AttendanceHistoryStudent.student_id == student.id).order_by(AttendanceHistoryStudent.id).all()
    student_payments = StudentPayments.query.filter(StudentPayments.student_id == student.id,
                                                    StudentPayments.payment == True).order_by(
        StudentPayments.id).all()
    history_list = []
    book_payments = BookPayments.query.filter(BookPayments.student_id == student.id).order_by(
        BookPayments.id).all()

    book_payment_list = [
        {
            "id": bk_payment.id,
            "payment": bk_payment.payment_sum,
            "date": bk_payment.day.date.strftime("%Y-%m-%d")
        } for bk_payment in book_payments
    ]
    history_list = [
        {
            "group_name": att.group.subject.name if att.group else "Ma'lumot yo'q",
            "total_debt": att.total_debt,
            "payment": att.payment,
            "remaining_debt": att.remaining_debt,
            "discount": att.total_discount,
            "present": att.present_days + att.scored_days,
            "absent": att.absent_days,
            "days": att.present_days + att.absent_days,
            "month": att.month.date.strftime("%Y-%m")
        } for att in attendance_histories
    ]
    payment_list = [
        {
            "id": payment.id,
            "payment": payment.payment_sum,
            "date": payment.day.date.strftime("%Y-%m-%d"),
            "type_payment": payment.payment_type.name
        } for payment in student_payments
    ]

    student_payments = StudentPayments.query.filter(StudentPayments.student_id == student.id,
                                                    StudentPayments.payment == False).order_by(
        StudentPayments.id).all()
    discount_list = [
        {
            "id": payment.id,
            "payment": payment.payment_sum,
            "date": payment.day.date.strftime("%Y-%m-%d"),

        } for payment in student_payments
    ]
    return jsonify({
        "data": {
            "id": student.user.id,
            "name": student.user.name.title(),
            "surname": student.user.surname.title(),
            "debts": history_list,
            "payments": payment_list,
            "discounts": discount_list,
            "bookPayments": book_payment_list
        }
    })


@classroom_bp.route(f'/filter_test_classroom/<int:group_id>/<month>/<year>', methods=['GET'])
def filter_test_classroom(group_id, month, year):
    month = f"{year}-{month}"
    calendar_year = CalendarYear.query.filter(CalendarYear.date == datetime.strptime(year, "%Y")).first()
    calendar_month = CalendarMonth.query.filter(CalendarMonth.date == datetime.strptime(month, "%Y-%m"),
                                                CalendarMonth.year_id == calendar_year.id).first()

    student_tests = StudentTest.query \
        .join(GroupTest, StudentTest.group_test_id == GroupTest.id) \
        .filter(
        GroupTest.calendar_month == calendar_month.id,
        StudentTest.group_id == group_id
    ) \
        .options(joinedload(StudentTest.group_test)) \
        .all()

    return jsonify({"tests": iterate_models(student_tests)})
