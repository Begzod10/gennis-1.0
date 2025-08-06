from sqlalchemy.orm import joinedload
from backend.teacher.utils import send_telegram_message
from app import app, db, request, jsonify, or_, contains_eager, classroom_server
from backend.account.models import StudentPayments, BookPayments
from backend.group.models import AttendanceHistoryStudent, GroupTest
from backend.models.models import Users, Roles, CalendarMonth, CalendarDay, CalendarYear, Attendance, AttendanceDays, \
    Students, Groups, Teachers, StudentCharity, Subjects, SubjectLevels, TeacherBlackSalary, StaffSalary, \
    DeletedTeachers, Locations, LessonPlan, Group_Room_Week, Parent
from werkzeug.security import check_password_hash
from backend.functions.utils import api, refresh_age, update_salary, iterate_models, get_json_field, check_exist_id, \
    find_calendar_date, update_school_salary
from datetime import datetime
from backend.functions.debt_salary_update import salary_debt
from flask_jwt_extended import jwt_required, create_refresh_token, create_access_token, get_jwt_identity
from backend.functions.filters import old_current_dates
from backend.group.class_model import Group_Functions
from backend.student.class_model import Student_Functions
from backend.student.models import StudentTest
from datetime import timedelta
from pprint import pprint
import requests
from werkzeug.security import generate_password_hash
from flask import Blueprint
from backend.functions.functions import update_user_time_table, get_dates_for_weekdays
from backend.models.models import Week

classroom_bp = Blueprint('classroom', __name__)


@app.route(f'{api}/login2', methods=['POST', 'GET'])
def login2():
    """
    login function
    create token
    :return: logged User datas
    """
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    if request.method == "POST":
        username = get_json_field('username')
        password = get_json_field('password')
        username_sign = Users.query.filter_by(username=username).first()

        if username_sign and check_password_hash(username_sign.password, password):
            role = Roles.query.filter(Roles.id == username_sign.role_id).first()
            access_token = create_access_token(identity=username_sign.user_id)
            refresh_age(username_sign.id)
            class_status = False
            # if role.type_role == "student" or role.type_role == "teacher" or role.type_role == "methodist":
            #     return jsonify({
            #         "success": False,
            #         "msg": "Username yoki parol noturg'i"
            #     })
            location = Locations.query.filter(Locations.id == username_sign.location_id).first()
            parent = Parent.query.filter(Parent.user_id == username_sign.id).first()
            return jsonify({
                'class': class_status,
                "type_platform": "gennis",
                "access_token": access_token,
                "user": username_sign.convert_json(),
                "refresh_token": create_refresh_token(identity=username_sign.user_id),
                "data": {
                    "username": username_sign.username,
                    "surname": username_sign.surname.title(),
                    "name": username_sign.name.title(),
                    "id": username_sign.id,
                    "role": role.role,
                    "location_id": username_sign.location_id,
                    "access_token": access_token,
                    "refresh_token": create_refresh_token(identity=username_sign.user_id),
                },
                "success": True,
                "type_user": role.type_role,
                "parent": parent.convert_json() if parent else {},
                "location": location.convert_json()

            })
        else:
            return jsonify({
                "success": False,
                "msg": "Username yoki parol noturg'i"
            })


@app.route(f'{api}/get_user')
@jwt_required()
def get_user():
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity)

    user = Users.query.filter_by(user_id=identity).first()
    subjects = Subjects.query.order_by(Subjects.id).all()

    return jsonify({
        "data": user.convert_json(),
        "access_token": access_token,
        "refresh_token": create_refresh_token(identity=user.user_id),
        "subject_list": iterate_models(subjects),
        # "users": iterate_models(users, entire=True)
    })


@app.route(f'{api}/get_group_datas/<int:group_id>')
@jwt_required()
def get_group_datas(group_id):
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity)
    students = Students.query.join(Students.group).filter(Groups.id == group_id).all()
    group = Groups.query.filter(Groups.id == group_id).first()
    users = Users.query.filter(Users.id.in_([user.user.id for user in students])).all()
    # for user in users:
    #     user_id = check_exist_id(user.user_id)
    #     user.user_id = user_id
    #     db.session.commit()
    return jsonify({
        "users": iterate_models(users),
        "access_token": access_token,
        "group": group.convert_json()
    })


@app.route(f'{api}/update_group_datas', methods=['POST'])
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


@app.route(f'{api}/update_user/<user_id>', methods=['POST'])
@jwt_required()
def update_user(user_id):
    Users.query.filter(Users.id == user_id).update({
        "user_id": get_json_field('user_id')
    })
    db.session.commit()
    return jsonify({
        "msg": "User id o'zgartirildi"
    })


@app.route(f'{api}/subjects_add', methods=['POST'])
def subjects_add():
    subjects = request.get_json()['subjects']
    print('subjects', subjects)
    for sub in subjects:
        get_subject = Subjects.query.filter(Subjects.classroom_id == sub['id']).first()
        if not get_subject:
            get_subject = Subjects.query.filter(Subjects.name == sub['name']).first()
        if not get_subject:
            get_subject = Subjects(name=sub['name'], ball_number=2, classroom_id=sub['id'])
            get_subject.add()
        else:
            get_subject.disabled = sub['disabled']
            get_subject.classroom_id = sub['id']
            get_subject.name = sub['name']
            db.session.commit()
    return jsonify({"msg": "Fanlar o'zgartirildi"})


@app.route(f'/api/get_datas', methods=['POST'])
def get_datas():
    type_info = request.get_json()['type']
    if type_info == "subject":
        response = request.get_json()['subject']
        for res in response:
            get_subject = Subjects.query.filter(Subjects.classroom_id == res['id']).first()
            if not get_subject:
                get_subject = Subjects.query.filter(Subjects.name == res['name']).first()
            if not get_subject:
                get_subject = Subjects(name=res['name'], ball_number=2, classroom_id=res['id'])
                get_subject.add()
            else:

                get_subject.disabled = res['disabled']
                get_subject.classroom_id = res['id']
                get_subject.name = res['name']
                db.session.commit()
        # disabled_subjects = Subjects.query.filter(Subjects.disabled == True).all()
        # for level in disabled_subjects:
        #     for gr in level.groups:
        #         gr.subject_id = None
        #         db.session.commit()
    else:
        response = request.get_json()['levels']
        for level in response:
            get_subject = Subjects.query.filter(Subjects.classroom_id == level['subject']['id']).first()
            if not get_subject:

                get_subject = Subjects.query.filter(Subjects.name == level['subject']['name']).first()

            elif not get_subject:
                get_subject = Subjects(name=level['subject']['name'], ball_number=2,
                                       classroom_id=level['subject']['id'])
                get_subject.add()
            else:
                get_subject.disabled = level['subject']['disabled']
                get_subject.classroom_id = level['subject']['id']
                get_subject.name = level['subject']['name']
                db.session.commit()
            get_level = SubjectLevels.query.filter(SubjectLevels.classroom_id == level['id'],
                                                   SubjectLevels.subject_id == get_subject.id).first()
            if not get_level:
                get_level = SubjectLevels.query.filter(SubjectLevels.name == level['name'],
                                                       SubjectLevels.subject_id == get_subject.id).first()

            if not get_level:
                get_level = SubjectLevels(name=level['name'], subject_id=get_subject.id, classroom_id=level['id'])
                get_level.add()
            else:
                get_level.disabled = level['disabled']
                get_level.classroom_id = level['id']
                get_level.name = level['name']
                db.session.commit()
        # disabled_levels = SubjectLevels.query.filter(SubjectLevels.disabled == True).all()
        # for level in disabled_levels:
        #     for gr in level.groups:
        #         gr.level_id = None
        #         db.session.commit()
    return jsonify({
        "msg": "Zo'r"
    })


@app.route(f'{api}/student_attendance_dates_classroom/<platform_id>')
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


@app.route(f"{api}/get_student_group_list/<int:platform_id>/<int:year>/<int:month>", methods=['GET'])
def get_student_group_list(platform_id, year, month):
    user = Users.query.filter(Users.id == platform_id).first()

    student = user.student
    print(student)

    calendar_year = CalendarYear.query.filter(
        db.extract('year', CalendarYear.date) == year
    ).first()
    print(calendar_year)

    calendar_month = CalendarMonth.query.filter(
        db.extract('year', CalendarMonth.date) == year,
        db.extract('month', CalendarMonth.date) == month,
        CalendarMonth.year_id == calendar_year.id
    ).first()
    print(calendar_month)

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


@app.route(f'{api}/get_student_attendance_days_list/<platform_id>/',
           defaults={"group_id": None, "year": None, "month": None})
@app.route(f"{api}/get_student_attendance_days_list/<platform_id>/<group_id>/<year>/<month>", methods=['GET'])
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


@app.route(f"{api}/student_payments_list/<platform_id>")
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


@app.route(f'{api}/filter_test_classroom/<int:group_id>/<month>/<year>', methods=['GET'])
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
