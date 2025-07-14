from app import app, api, contains_eager, db, request
from flask import jsonify
from flask_jwt_extended import jwt_required
from backend.functions.utils import find_calendar_date, get_json_field, update_salary
from backend.models.models import AttendanceHistoryStudent, Students, Groups, Roles, Week, Group_Room_Week, Rooms, \
    Users, Attendance, AttendanceDays, Teachers, TeacherBlackSalary
from datetime import datetime
from backend.functions.filters import update_lesson_plan, old_current_dates
from backend.group.class_model import Group_Functions
from backend.student.class_model import Student_Functions
from backend.functions.debt_salary_update import salary_debt


@app.route(f'{api}/group_dates2_classroom/<int:group_id>')
def group_dates2_classroom(group_id):
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    year_list = []
    month_list = []
    attendance_month = AttendanceHistoryStudent.query.filter(
        AttendanceHistoryStudent.group_id == group_id,
    ).order_by(AttendanceHistoryStudent.id).all()
    for attendance in attendance_month:
        year = AttendanceHistoryStudent.query.filter(AttendanceHistoryStudent.group_id == group_id,
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
        #
        # if info['year'] != calendar_year.date.strftime("%Y"):
        #     info['year'] = calendar_year.date.strftime("%Y")
        # if calendar_month.date.strftime("%m") not in info['months']:
        #     print(calendar_year.date.strftime("%Y"))
        #     info['months'].append(calendar_month.date.strftime("%m"))
        month_list.append(info)
    year_list = list(dict.fromkeys(year_list))
    if calendar_year.date.strftime("%Y") not in year_list:
        year_list.append(calendar_year.date.strftime("%Y"))
    filtered_list = []
    for student in month_list:
        added_to_existing = False
        for merged in filtered_list:
            if merged['year'] == student['year']:
                added_to_existing = True
            if added_to_existing:
                break
        if not added_to_existing:
            filtered_list.append(student)
    return jsonify({
        "data": {
            "months": filtered_list,
            "years": year_list,
            "current_year": calendar_year.date.strftime("%Y"),
            "current_month": calendar_month.date.strftime("%m"),
        }
    })


@app.route(f'{api}/attendances_classroom/<int:group_id>', methods=['GET', "POST"])
def attendances_classroom(group_id):
    update_lesson_plan(group_id)
    students = db.session.query(Students).join(Students.group).options(contains_eager(Students.group)).filter(
        Groups.id == group_id).order_by(Students.id).all()
    student_list = [{
        "id": st.user.id,
        "img": None,
        "name": st.user.name.title(),
        "surname": st.user.surname.title(),
        "money": st.user.balance,
        "moneyType": ["green", "yellow", "red", "navy", "black"][st.debtor] if st.debtor else 0,
        "comment": st.user.comment,
        "reg_date": st.user.day.date.strftime("%Y-%m-%d"),
        "phone": st.user.phone[0].phone,
        "username": st.user.username,
        "age": st.user.age,
        "photo_profile": st.user.photo_profile,
        "role": Roles.query.filter(Roles.id == st.user.role_id).first().role
    } for st in students]

    gr_functions = Group_Functions(group_id=group_id)
    if request.method == "GET":
        current_month = datetime.now().month
        if len(str(current_month)) == 1:
            current_month = "0" + str(current_month)
        current_year = datetime.now().year

        return jsonify({

            "data": {
                "attendance_filter": gr_functions.attendance_filter(month=current_month, year=current_year),
                "students": student_list,
                "date": old_current_dates(group_id),
            }
        })
    else:
        year = get_json_field('year')

        month = get_json_field('month')
        return jsonify({

            "data": {
                "attendance_filter": gr_functions.attendance_filter(month=month, year=year),
                "students": student_list,
                "date": old_current_dates(group_id),
            }
        })


@app.route(f'{api}/group_time_table_classroom/<int:group_id>')
def group_time_table_classroom(group_id):
    group = Groups.query.filter(Groups.id == group_id).first()
    week_days = Week.query.filter(Week.location_id == group.location_id).order_by(Week.order).all()
    table_list = []
    weeks = []
    for week in week_days:
        weeks.append(week.name)
    rooms = db.session.query(Rooms).join(Rooms.time_table).options(contains_eager(Rooms.time_table)).filter(
        Group_Room_Week.group_id == group_id, Rooms.location_id == group.location_id).all()
    for room in rooms:
        room_info = {
            "room": room.name,
            "id": room.id,
            "lesson": []
        }
        week_list = []
        for week in week_days:
            info = {
                "from": "",
                "to": ""
            }
            time_table = Group_Room_Week.query.filter(Group_Room_Week.group_id == group_id,
                                                      Group_Room_Week.week_id == week.id,
                                                      Group_Room_Week.room_id == room.id).order_by(
                Group_Room_Week.group_id).first()
            if time_table:
                info["from"] = time_table.start_time.strftime("%H:%M")
                info["to"] = time_table.end_time.strftime("%H:%M")

            week_list.append(info)
            room_info['lesson'] = week_list
        table_list.append(room_info)
    return jsonify({
        "success": True,
        "data": table_list,
        "days": weeks
    })


@app.route(f'{api}/combined_attendances_classroom/<int:student_id>/', methods=["POST", "GET"])
def combined_attendances_classroom(student_id):
    student = Students.query.filter(Students.user_id == student_id).first()
    st_functions = Student_Functions(student_id=student.id)
    if request.method == "GET":
        current_month = datetime.now().month
        if len(str(current_month)) == 1:
            current_month = "0" + str(current_month)
        current_year = datetime.now().year
        return jsonify({
            "data": st_functions.attendance_filter_student(month=current_month, year=current_year)
        })
    else:
        year = get_json_field('year')

        month = get_json_field('month')

        return jsonify({
            "data": st_functions.attendance_filter_student(month=month, year=year)
        })


@app.route(f'{api}/student_group_dates2_classroom/<int:student_id>/')
def student_group_dates2_classroom(student_id):
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    year_list = []
    month_list = []
    student = Students.query.filter(Students.user_id == student_id).first()
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
    return jsonify({
        "data": {
            "months": filtered_list,
            "years": year_list,
            "current_year": calendar_year.date.strftime("%Y"),
            "current_month": calendar_month.date.strftime("%m"),
        }
    })


@app.route(
    f'{api}/delete_attendance_classroom/<int:attendance_id>/<int:student_id>/<int:group_id>', methods=["GET"])
def delete_attendance_classroom(attendance_id, student_id, group_id):
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
