import json

import os
from app import app, api, request, db, jsonify, contains_eager, classroom_server, or_, migrate

import pprint

from app import app, api, request, db, jsonify, contains_eager, classroom_server, or_

from backend.functions.filters import old_current_dates
import requests
from backend.functions.debt_salary_update import salary_debt
from flask_jwt_extended import jwt_required
from backend.student.class_model import Student_Functions
from backend.group.class_model import Group_Functions
from datetime import datetime
from .utils import get_students_info, prepare_scores
from backend.functions.utils import find_calendar_date, update_salary, iterate_models, get_json_field, \
    update_school_salary
from backend.models.models import Users, Attendance, Students, AttendanceDays, Teachers, Groups, Locations, Subjects, \
    StudentCharity, Roles, TeacherBlackSalary, GroupReason, TeacherObservationDay, DeletedStudents, \
    TeacherGroupStatistics, Group_Room_Week, LessonPlan
from backend.school.models import SchoolUser, SchoolUserSalary, SchoolUserSalaryDay, SchoolUserSalaryAttendance
from datetime import timedelta
from backend.models.models import CalendarDay, CalendarMonth, CalendarYear
from sqlalchemy import func
from backend.functions.functions import update_user_time_table, get_dates_for_weekdays
from backend.teacher.utils import send_telegram_message


def analyze(attendances, teacher, type_rating=None):
    ball = 0
    teacher_list = []
    info = {
        "name": teacher.user.name,
        "surname": teacher.user.surname,
        "percentage": 0
    }
    if type_rating == "attendance":
        for att in attendances:
            if att.ball_percentage:
                ball += att.ball_percentage
        info["percentage"] = round(ball / len(attendances)) if ball != 0 else 0

        teacher_list.append(info)
    elif type_rating == "observation":
        for att in attendances:
            ball += att.average
        info["percentage"] = round(ball / len(attendances)) if ball != 0 else 0
        info['observation_len'] = len(attendances)
        teacher_list.append(info)
    elif type_rating == "deleted_students":
        for att in attendances:
            ball += att.percentage
        info["percentage"] = round(ball / len(attendances)) if ball != 0 else 0
        teacher_list.append(info)
    return teacher_list


@app.route(f'{api}/statistics_dates', methods=['POST', 'GET'])
@jwt_required()
def statistics_dates():
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    calendar_years = CalendarYear.query.order_by(CalendarYear.date).all()
    if request.method == "GET":
        calendar_months = CalendarMonth.query.filter(CalendarMonth.year_id == calendar_year.id).order_by(
            CalendarMonth.date).distinct(CalendarMonth.date).all()
        return jsonify({
            "years_list": iterate_models(calendar_years),
            "month_list": iterate_models(calendar_months),
            "current_year": calendar_year.date.strftime("%Y"),
            "current_month": calendar_month.date.strftime("%Y-%m")
        })
    else:
        year = get_json_field('year') if 'year' in request.get_json() else calendar_year.date
        calendar_year = CalendarYear.query.filter(CalendarYear.date == datetime.strptime(year, "%Y")).first()
        calendar_months = CalendarMonth.query.filter(CalendarMonth.year_id == calendar_year.id).order_by(
            CalendarMonth.date).distinct(CalendarMonth.date).all()
        return jsonify({
            "month_list": iterate_models(calendar_months)
        })


@app.route(f'{api}/teacher_statistics/<location_id>', methods=['POST'])
@jwt_required()
def teacher_statistics(location_id):
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    teachers = db.session.query(Teachers).join(Teachers.locations).options(contains_eager(Teachers.locations)).filter(
        Teachers.deleted == None, Teachers.group != None, Locations.id == location_id).join(Teachers.group).filter(
        Groups.deleted != True).order_by(Teachers.id).all()
    group_reasons = GroupReason.query.order_by(GroupReason.id).all()
    teachers_list = []

    year = get_json_field('year') if 'year' in request.get_json() else calendar_year.date
    month = get_json_field('month') if 'month' in request.get_json() else None
    month = datetime.strptime(month, "%Y-%m") if month else None
    type_rating = get_json_field('type_rating') if 'type_rating' in request.get_json() else None
    if year != "all" and not month:
        calendar_year = CalendarYear.query.filter(CalendarYear.date == datetime.strptime(year, "%Y")).first()
        for teacher in teachers:
            if type_rating == "attendances":
                attendances = Attendance.query.filter(Attendance.calendar_year == calendar_year.id,
                                                      Attendance.teacher_id == teacher.id,
                                                      Attendance.ball_percentage != None
                                                      ).all()
                teachers_list += analyze(attendances, teacher, type_rating)
            elif type_rating == "observation":
                observations = TeacherObservationDay.query.filter(
                    TeacherObservationDay.calendar_year == calendar_year.id,
                    TeacherObservationDay.teacher_id == teacher.id).all()
                teachers_list += analyze(observations, teacher, type_rating)
        if type_rating == "deleted_students":
            del_st_statistics_num = TeacherGroupStatistics.query.filter(
                TeacherGroupStatistics.calendar_year == calendar_year.id,
                TeacherGroupStatistics.teacher_id.in_([teacher.id for teacher in teachers])
            ).order_by(
                TeacherGroupStatistics.calendar_year).all()
            all_percentage = 0
            for st in del_st_statistics_num:
                all_percentage += st.percentage
            for reason in group_reasons:
                del_st_statistics = TeacherGroupStatistics.query.filter(
                    TeacherGroupStatistics.calendar_year == calendar_year.id,
                    TeacherGroupStatistics.reason_id == reason.id,
                    TeacherGroupStatistics.teacher_id.in_([teacher.id for teacher in teachers])
                ).order_by(
                    TeacherGroupStatistics.calendar_year).all()
                percentage = 0
                for st in del_st_statistics:
                    percentage += st.percentage

                info = {
                    "name": reason.reason,
                    "percentage": round((percentage / all_percentage) * 100) if del_st_statistics_num else 0
                }
                teachers_list.append(info)

        teachers_list = sorted(teachers_list, key=lambda d: d['percentage'])
        teachers_list.reverse()

        return jsonify({
            "teachers_list": teachers_list
        })
    elif year != "all" and month:
        calendar_year = CalendarYear.query.filter(CalendarYear.date == datetime.strptime(year, "%Y")).first()
        # date = year + "-" + month
        calendar_month = CalendarMonth.query.filter(CalendarMonth.date == month).first()

        for teacher in teachers:

            if type_rating == "attendance":
                attendances = Attendance.query.filter(Attendance.calendar_year == calendar_year.id,
                                                      Attendance.teacher_id == teacher.id,
                                                      Attendance.calendar_month == calendar_month.id,
                                                      Attendance.ball_percentage != None
                                                      ).all()

                teachers_list += analyze(attendances, teacher, type_rating)
            elif type_rating == "observation":
                observations = TeacherObservationDay.query.filter(
                    TeacherObservationDay.calendar_year == calendar_year.id,
                    TeacherObservationDay.calendar_month == calendar_month.id,
                    TeacherObservationDay.teacher_id == teacher.id).all()
                teachers_list += analyze(observations, teacher, type_rating)
        if type_rating == "deleted_students":
            del_st_statistics_num = TeacherGroupStatistics.query.filter(
                TeacherGroupStatistics.calendar_year == calendar_year.id,
                TeacherGroupStatistics.calendar_month == calendar_month.id,
                TeacherGroupStatistics.teacher_id.in_([teacher.id for teacher in teachers])
            ).order_by(
                TeacherGroupStatistics.calendar_year).all()
            all_percentage = 0
            for st in del_st_statistics_num:
                all_percentage += st.percentage
            for reason in group_reasons:
                del_st_statistics = TeacherGroupStatistics.query.filter(
                    TeacherGroupStatistics.calendar_year == calendar_year.id,
                    TeacherGroupStatistics.calendar_month == calendar_month.id,
                    TeacherGroupStatistics.reason_id == reason.id,
                    TeacherGroupStatistics.teacher_id.in_([teacher.id for teacher in teachers])
                ).order_by(
                    TeacherGroupStatistics.calendar_year).all()
                percentage = 0
                for st in del_st_statistics:
                    percentage += st.percentage
                info = {
                    "name": reason.reason,
                    "percentage": round((percentage / all_percentage) * 100) if del_st_statistics_num else 0
                }
                teachers_list.append(info)
        teachers_list = sorted(teachers_list, key=lambda d: d['percentage'])
        teachers_list.reverse()
        return jsonify({
            "teachers_list": teachers_list
        })
    else:
        for teacher in teachers:
            if type_rating == "attendance":
                attendances = Attendance.query.filter(Attendance.teacher_id == teacher.id,
                                                      Attendance.ball_percentage != None
                                                      ).all()
                teachers_list += analyze(attendances, teacher, type_rating)
            elif type_rating == "observation":
                observations = TeacherObservationDay.query.filter(
                    TeacherObservationDay.teacher_id == teacher.id).all()
                teachers_list += analyze(observations, teacher, type_rating)
        if type_rating == "deleted_students":
            del_st_statistics_num = TeacherGroupStatistics.query.filter(
                TeacherGroupStatistics.teacher_id.in_([teacher.id for teacher in teachers])
            ).order_by(
                TeacherGroupStatistics.calendar_year).all()
            all_percentage = 0
            for st in del_st_statistics_num:
                all_percentage += st.percentage
            for reason in group_reasons:
                del_st_statistics = TeacherGroupStatistics.query.filter(
                    TeacherGroupStatistics.reason_id == reason.id,
                    TeacherGroupStatistics.teacher_id.in_([teacher.id for teacher in teachers])
                ).order_by(
                    TeacherGroupStatistics.calendar_year).all()
                percentage = 0
                for st in del_st_statistics:
                    percentage += st.percentage
                info = {
                    "name": reason.reason,
                    "percentage": round((percentage / all_percentage) * 100) if del_st_statistics_num else 0
                }
                teachers_list.append(info)
        teachers_list = sorted(teachers_list, key=lambda d: d['percentage'])
        teachers_list.reverse()
        return jsonify({
            "teachers_list": teachers_list
        })


@app.route(f'{api}/teacher_statistics_deleted_students/<location_id>', methods=['POST'])
@jwt_required()
def teacher_statistics_deleted_students(location_id):
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    reason_name = get_json_field('reason_name')
    year = get_json_field('year') if 'year' in request.get_json() else calendar_year.date
    month = get_json_field('month') if 'month' in request.get_json() else None
    month = datetime.strptime(month, "%Y-%m") if month else None
    reason = GroupReason.query.filter(GroupReason.reason == reason_name).first()
    teachers = db.session.query(Teachers).join(Teachers.locations).options(contains_eager(Teachers.locations)).filter(
        Teachers.deleted == None, Teachers.group != None, Locations.id == location_id).join(Teachers.group).filter(
        Groups.deleted != True).order_by(Teachers.id).all()
    teachers_list = []
    if year != "all" and not month:
        calendar_year = CalendarYear.query.filter(CalendarYear.date == datetime.strptime(year, "%Y")).first()

        for teacher in teachers:
            del_st_statistics = TeacherGroupStatistics.query.filter(
                TeacherGroupStatistics.calendar_year == calendar_year.id,
                TeacherGroupStatistics.reason_id == reason.id,
                TeacherGroupStatistics.teacher_id == teacher.id
            ).order_by(
                TeacherGroupStatistics.calendar_year).all()
            teachers_list += analyze(del_st_statistics, teacher, "deleted_students")
    elif year != "all" and month:
        calendar_year = CalendarYear.query.filter(CalendarYear.date == datetime.strptime(year, "%Y")).first()
        # date = year + "-" + month
        calendar_month = CalendarMonth.query.filter(CalendarMonth.date == month).first()
        for teacher in teachers:
            del_st_statistics = TeacherGroupStatistics.query.filter(
                TeacherGroupStatistics.calendar_year == calendar_year.id,
                TeacherGroupStatistics.calendar_month == calendar_month.id,
                TeacherGroupStatistics.reason_id == reason.id,
                TeacherGroupStatistics.teacher_id == teacher.id
            ).order_by(
                TeacherGroupStatistics.calendar_year).all()
            teachers_list += analyze(del_st_statistics, teacher, "deleted_students")
    else:
        for teacher in teachers:
            del_st_statistics = TeacherGroupStatistics.query.filter(
                TeacherGroupStatistics.reason_id == reason.id,
                TeacherGroupStatistics.teacher_id == teacher.id
            ).order_by(
                TeacherGroupStatistics.calendar_year).all()
            teachers_list += analyze(del_st_statistics, teacher, "deleted_students")
    teachers_list = sorted(teachers_list, key=lambda d: d['percentage'])
    teachers_list.reverse()
    return jsonify({
        "teachers_list": teachers_list
    })


@app.route(f'{api}/attendance/<int:group_id>', methods=['GET'])
@jwt_required()
def attendance(group_id):
    # Assuming this is a necessary function call
    today = datetime.today()

    hour = datetime.strftime(today, "%Y/%m/%d/%H/%M")
    hour2 = datetime.strptime(hour, "%Y/%m/%d/%H/%M")

    student_list = get_students_info(group_id, hour2)
    group = Groups.query.get(group_id)
    subject = Subjects.query.get(group.subject_id)
    scores = prepare_scores(subject.ball_number)

    gr_functions = Group_Functions(group_id=group_id)
    gr_functions.update_list_balance()

    return jsonify({
        'students': student_list,
        "date": old_current_dates(group_id),  # davomat funksiya kunlari
        "scoresData": scores
    })


@app.route(f'{api}/make_attendance', methods=['POST'])
@jwt_required()
def make_attendance():
    data = request.get_json()
    student = data['student']
    student_id = int(student['id'])
    group_id = int(data['groupId'])

    current_year = datetime.now().year
    old_year = current_year - 1
    current_month = str(datetime.now().month).zfill(2)
    current_day = datetime.now().day

    reason = student.get('reason', '')
    student_obj = Students.query.filter_by(user_id=student_id).first()
    if student_obj.debtor == 4:
        return jsonify({"error": True, "msg": "Debtor status 4", "requestType": "error"})

    # Scores
    scores = {score['name']: int(score['activeStars']) for score in student['scores']}
    homework = scores.get('homework', 0)
    active = scores.get('active', 0)
    dictionary = scores.get('dictionary', 0)

    type_attendance = student['typeChecked'] == "yes"
    group = Groups.query.get(group_id)
    teacher = Teachers.query.get(group.teacher_id)
    subject = Subjects.query.get(group.subject_id)
    discount = StudentCharity.query.filter_by(group_id=group_id, student_id=student_obj.id).first()

    # Dates
    day = student['date']['day']
    month_date = student['date'].get('month', current_month)
    if month_date == "12" and current_month == "01":
        current_year = old_year

    full_date = f"{current_year}-{month_date}-{day}"
    date_day = datetime.strptime(full_date, "%Y-%m-%d")
    date_month = datetime.strptime(f"{current_year}-{month_date}", "%Y-%m")
    date_year = datetime.strptime(str(current_year), "%Y")
    calendar_year, calendar_month, calendar_day = find_calendar_date(date_day, date_month, date_year)

    # Time calculations
    hour = datetime.today().strftime("%Y/%m/%d/%H/%M")
    ball_time = datetime.strptime(hour, "%Y/%m/%d/%H/%M")
    balance_per_day = round(group.price / group.attendance_days)
    salary_per_day = round(group.teacher_salary / group.attendance_days)
    discount_per_day = discount.discount / group.attendance_days if discount else 0
    balance_with_discount = balance_per_day - discount_per_day
    discount_status = bool(discount_per_day)
    student_obj.ball_time = ball_time

    # Attendance record
    attendance = Attendance.query.filter_by(
        student_id=student_obj.id,
        calendar_year=calendar_year.id,
        location_id=group.location_id,
        calendar_month=calendar_month.id,
        teacher_id=group.teacher_id,
        group_id=group.id,
        subject_id=subject.id,
        course_id=group.course_type_id
    ).first()

    if not attendance:
        attendance = Attendance(
            student_id=student_obj.id,
            calendar_year=calendar_year.id,
            location_id=group.location_id,
            calendar_month=calendar_month.id,
            teacher_id=teacher.id,
            group_id=group_id,
            course_id=group.course_type_id,
            subject_id=subject.id
        )
        db.session.add(attendance)
        db.session.commit()

    # Check existing attendance
    existing = AttendanceDays.query.join(Attendance).filter(
        AttendanceDays.student_id == student_obj.id,
        AttendanceDays.calendar_day == calendar_day.id,
        AttendanceDays.group_id == group_id,
        Attendance.calendar_month == calendar_month.id,
        Attendance.calendar_year == calendar_year.id
    ).first()
    if existing:
        return jsonify(
            {"error": True, "msg": "Davomat allaqachon mavjud", "student_id": student['id'], "requestType": "error"})

    # Check limit per month
    attendance_count = AttendanceDays.query.filter_by(
        student_id=student_obj.id,
        group_id=group_id,
        location_id=group.location_id,
        attendance_id=attendance.id
    ).count()
    if attendance_count >= group.attendance_days:
        return jsonify({"error": True, "msg": "Davomatlar soni limitdan oshdi", "student_id": student['id'],
                        "requestType": "error"})

    # Ball calculation
    ball = max(0, 5 - max(0, current_day - int(day)))
    week_names = [t.week.eng_name for t in Group_Room_Week.query.filter_by(group_id=group_id).all()]
    target_dates = [d.date() for d in get_dates_for_weekdays(week_names)]
    lesson_plan_today = LessonPlan.query.filter_by(
        group_id=group.id,
        teacher_id=teacher.id,
        date=calendar_day.date
    ).first()
    fine = 0
    fine = round(salary_per_day / group.attendance_days) if lesson_plan_today or ball < 5 else 0

    # Add attendance day

    attendance_add = AttendanceDays(
        teacher_id=teacher.id,
        student_id=student_obj.id,
        calendar_day=calendar_day.id,
        attendance_id=attendance.id,
        reason=reason if not type_attendance else None,
        status=0 if not type_attendance else 1 if (homework == 0 and dictionary == 0 and active == 0) else 2,
        balance_per_day=balance_per_day,
        balance_with_discount=balance_with_discount,
        salary_per_day=salary_per_day,
        group_id=group_id,
        location_id=group.location_id,
        discount_per_day=discount_per_day,
        discount=discount_status,
        date=datetime.now(),
        teacher_ball=ball,
        fine=fine,
        calling_status=True if type_attendance else False,
        homework=homework,
        dictionary=dictionary,
        activeness=active,
        average_ball=round((homework + dictionary + active) / subject.ball_number) if subject.ball_number else 0
    )
    db.session.add(attendance_add)
    db.session.commit()

    # Update percentage
    attendance_days = AttendanceDays.query.filter_by(attendance_id=attendance.id).filter(
        AttendanceDays.teacher_ball != None).all()
    total_ball = sum([a.teacher_ball for a in attendance_days])
    attendance.ball_percentage = round(total_ball / len(attendance_days))
    db.session.commit()

    # Update balance and debt
    st_functions = Student_Functions(student_id=student_obj.id)
    st_functions.update_debt()
    st_functions.update_balance()

    salary_location = salary_debt(student_id=student_obj.id, group_id=group_id, attendance_id=attendance_add.id,
                                  status_attendance=False, type_attendance="add")
    update_salary(teacher_id=teacher.user_id)

    if student_obj.debtor == 2:
        black_salary = TeacherBlackSalary.query.filter_by(
            teacher_id=teacher.id,
            student_id=student_obj.id,
            calendar_month=calendar_month.id,
            calendar_year=calendar_year.id,
            location_id=student_obj.user.location_id,
            salary_id=salary_location.id,
            status=False
        ).first()
        if not black_salary:
            black_salary = TeacherBlackSalary(
                teacher_id=teacher.id,
                total_salary=salary_per_day,
                student_id=student_obj.id,
                salary_id=salary_location.id,
                calendar_month=calendar_month.id,
                calendar_year=calendar_year.id,
                location_id=student_obj.user.location_id
            )
            black_salary.add()
        else:
            black_salary.total_salary += salary_per_day
            db.session.commit()

    user = Users.query.get(student_id)
    send_telegram_message(student_obj.id, attendance_add.id, group_id)
    if user.school_user_id:
        update_school_salary(user, group, calendar_day, calendar_month, calendar_year, attendance_add)

    return jsonify({"msg": "Davomat qo'shildi", "success": True, "student_id": student['id'], "requestType": "success"})


@app.route(f'{api}/attendance_delete/<int:attendance_id>/<int:student_id>/<int:group_id>/<int:main_attendance>')
@jwt_required()
def attendance_delete(attendance_id, student_id, group_id, main_attendance):
    student = Students.query.filter(Students.user_id == student_id).first()
    attendancedays = AttendanceDays.query.filter(AttendanceDays.id == attendance_id).first()
    attendace_get = Attendance.query.filter(Attendance.id == attendancedays.attendance_id).first()
    group = Groups.query.filter(Groups.id == group_id).first()
    teacher = Teachers.query.filter(Teachers.id == group.teacher_id).first()
    black_salary = TeacherBlackSalary.query.filter(TeacherBlackSalary.teacher_id == teacher.id,
                                                   TeacherBlackSalary.student_id == student.id,
                                                   TeacherBlackSalary.calendar_month == attendace_get.calendar_month,
                                                   TeacherBlackSalary.calendar_year == attendace_get.calendar_year,
                                                   TeacherBlackSalary.status == False,
                                                   TeacherBlackSalary.location_id == student.user.location_id,
                                                   ).first()
    salary_per_day = attendancedays.salary_per_day
    if black_salary:
        if black_salary.total_salary:
            black_salary.total_salary -= salary_per_day
            db.session.commit()
        else:
            db.session.delete(black_salary)
            db.session.commit()
    salary_debt(student_id=student.id, group_id=group_id, attendance_id=attendance_id, status_attendance=True,
                type_attendance=True)
    st_functions = Student_Functions(student_id=student.id)
    st_functions.update_debt()
    st_functions.update_balance()

    update_salary(teacher_id=teacher.user_id)

    return jsonify({
        "success": True,
        "msg": "Davomat o'chirildi"
    })


@app.route(f"{api}/get_teachers", methods=["GET"])
@jwt_required()
def get_teachers():
    list_teachers = []
    role = Roles.query.filter(Roles.type_role == "teacher").first().role
    teachers = Teachers.query.order_by('id').all()

    list_teachers = [
        {
            "id": teach.user.id,
            "name": teach.user.name.title(),
            "surname": teach.user.surname.title(),
            "username": teach.user.username,
            "language": teach.user.language.name,
            "age": teach.user.age,
            "role": role,
            "reg_date": teach.user.day.date.strftime("%Y-%m-%d"),
            "subjects": [subject.name for subject in teach.subject]
        } for teach in teachers
    ]
    return jsonify({
        "teachers": list_teachers
    })


@app.route(f"{api}/get_teachers_location/<int:location_id>", methods=["GET"])
# @jwt_required()
def get_teachers_location(location_id):
    list_teachers = []
    role = Roles.query.filter(Roles.type_role == "teacher").first().role
    teachers = Teachers.query.join(Users).filter(Users.location_id == location_id, Teachers.deleted == None).order_by(
        Users.location_id).all()
    location = Locations.query.filter(Locations.id == location_id).first()
    for teach in teachers:
        if location not in teach.locations:
            teach.locations.append(location)
            db.session.commit()
    teachers = Teachers.query.join(Teachers.locations).filter(Locations.id == location_id,
                                                              Teachers.deleted == None).order_by(
        Teachers.id).all()
    for teach in teachers:
        status = False
        del_group = 0
        for gr in teach.group:
            if gr.deleted:
                del_group += 1
        if del_group == len(teach.group):
            status = True
        if not teach.group:
            status = True
        info = {
            "id": teach.user.id,
            "name": teach.user.name.title(),
            "surname": teach.user.surname.title(),
            "username": teach.user.username,
            "language": teach.user.language.name,
            "age": teach.user.age,
            "role": role,
            # "phone": teach.user.phone[0].phone,
            "reg_date": teach.user.day.date.strftime("%Y-%m-%d"),
            "status": status,
            "photo_profile": teach.user.photo_profile,
            "subjects": [subject.name for subject in teach.subject]
        }
        list_teachers.append(info)

    return jsonify({
        "teachers": list_teachers
    })


@app.route(f'{api}/add_teacher_to_branch/<int:user_id>/<int:location_id>')
@jwt_required()
def add_teacher_to_branch(user_id, location_id):
    teacher = Teachers.query.filter(Teachers.user_id == user_id).first()
    location = Locations.query.filter(Locations.id == location_id).first()
    msg_info = {
        "msg": f"O'quvchi {location.name} flialiga qo'shildi",
        "success": True
    }
    if location not in teacher.locations:
        teacher.locations.append(location)
        db.session.commit()
    else:
        teacher.locations.remove(location)
        db.session.commit()
        msg_info = {
            "msg": f"O'quvchi {location.name} flialidan olindi",
            "success": True
        }
    return jsonify(msg_info)


@app.route(f"{api}/get_deletedTeachers_location/<int:location_id>", methods=["GET"])
@jwt_required()
def get_deletedTeachers_location(location_id):
    # Fetch the role information for "teacher" just once, as it's the same for all entries.
    teacher_role = Roles.query.filter_by(type_role="teacher").first().role

    # Query to fetch deleted teachers at the given location, including necessary joins for user and language details.
    teachers = Teachers.query.join(Users).filter(
        Users.location_id == location_id,
        Teachers.deleted != None
    ).all()

    # Build the list of teachers with their details, including subjects.
    list_teachers = [{
        "id": teacher.user.id,
        "name": teacher.user.name.title(),
        "surname": teacher.user.surname.title(),
        "username": teacher.user.username,
        "language": teacher.user.language.name,
        "age": teacher.user.age,
        "role": teacher_role,
        "phone": teacher.user.phone[0].phone,  # Assumes at least one phone number is present
        "reg_date": teacher.user.day.date.strftime("%Y-%m-%d"),
        "subjects": [subject.name for subject in teacher.subject]
    } for teacher in teachers]

    return jsonify({"teachers": list_teachers})


class Test(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

    def __repr__(self):
        return '<User %r>' % self.username


@app.route('/test_model', methods=["GET", "POST"])
# @jwt_required()
def test_model():
    return jsonify({"teachers": "True"})


@app.route(f'{api}/get_teacher_balance/<user_id>', methods=["GET", "POST"])
def get_teacher_balance(user_id):
    user = Users.query.filter(Users.id == user_id).first()
    return jsonify({"balance": user.balance})
