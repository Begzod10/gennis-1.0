import pprint
from datetime import datetime
from app import app, api, desc, jsonify
from backend.models.models import StudentPayments, Students, Attendance, Users, Group_Room_Week, Week, AttendanceDays, \
    CalendarDay, \
    CalendarYear, CalendarMonth, AttendanceHistoryStudent, StudentTest, GroupTest, Teachers, Groups
from backend.functions.utils import iterate_models, find_calendar_date


@app.route(f'{api}/bot_student_payments/<student_id>')
def bot_student_payments(student_id):
    student_payments = StudentPayments.query.filter(StudentPayments.student_id == student_id).order_by(
        desc(StudentPayments.id)).all()
    return jsonify({"payments": iterate_models(student_payments)})


@app.route(f'{api}/bot_student_time_table/<pk>/<user_type>')
def bot_student_time_table(pk, user_type):
    student = Students.query.filter(Students.id == pk).first()
    teacher = Teachers.query.filter(Teachers.id == pk).first()

    table_list = []
    group = student.group if user_type == "student" else teacher.group

    group = Groups.query.filter(Groups.id.in_([gr.id for gr in group]), Groups.deleted == False,
                                Groups.status == True).order_by(Groups.id).all()
    for gr in group:
        info = {
            "id": gr.id,
            "name": gr.name,
            "teacher": f"{gr.teacher[0].user.name} {gr.teacher[0].user.surname}",
            "subject": gr.subject.name,
            "lessons": []
        }
        student_time_table = Group_Room_Week.query.filter(
            Group_Room_Week.group_id == gr.id).join(Week).order_by(Week.order).all()
        for time in student_time_table:
            info["lessons"].append({
                "day": time.week.name,
                "room": time.room.name,
                "from": time.start_time.strftime("%H:%M"),
                "to": time.end_time.strftime("%H:%M"),
                "order": time.week.order
            })
        table_list.append(info)
    return jsonify({"table_list": table_list})


@app.route(f'{api}/student_attendance_dates/<int:student_id>')
def student_attendance_dates(student_id):
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    year_list = []
    month_list = []
    student = Students.query.filter(Students.id == student_id).first()
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


@app.route(f'{api}/bot_student_attendances/<student_id>/<set_year>/<set_month>')
def bot_student_attendances(student_id, set_year, set_month):
    set_month = set_year + "-" + set_month
    set_year = datetime.strptime(set_year, "%Y")
    set_month = datetime.strptime(set_month, "%Y-%m")
    calendar_year = CalendarYear.query.filter(CalendarYear.date == set_year).first()
    calendar_month = CalendarMonth.query.filter(CalendarMonth.date == set_month).first()

    student = Students.query.filter(Students.id == student_id).first()
    attendance_list = []
    for gr in student.group:
        info = {
            "id": gr.id,
            "name": gr.name,
            "teacher": f"{gr.teacher[0].user.name} {gr.teacher[0].user.surname}",
            "subject": gr.subject.name,
            "attendances": [],
            "current_month": calendar_month.date.strftime("%Y-%m")
        }
        attendance = AttendanceDays.query.filter(AttendanceDays.student_id == student_id,
                                                 AttendanceDays.group_id == gr.id).join(
            AttendanceDays.attendance).filter(Attendance.calendar_year == calendar_year.id,
                                              Attendance.calendar_month == calendar_month.id).join(
            AttendanceDays.day).order_by(
            CalendarDay.date).all()
        info["attendances"] = iterate_models(attendance)
        attendance_list.append(info)
    return jsonify({"attendances": attendance_list})


@app.route(f'{api}/bot_student_test_results/<student_id>')
def bot_student_test_results(student_id):
    student = Students.query.filter(Students.id == student_id).first()
    tests = []
    for gr in student.group:
        student_tests = StudentTest.query.filter(StudentTest.group_id == gr.id,
                                                 StudentTest.student_id == student_id).order_by(
            desc(StudentTest.id)).all()
        info = {
            "id": gr.id,
            "name": gr.name,
            "teacher": f"{gr.teacher[0].user.name} {gr.teacher[0].user.surname}",
            "subject": gr.subject.name,
            "tests": iterate_models(student_tests)
        }
        tests.append(info)
    return jsonify({"test_results": tests})


@app.route(f'{api}/bot_student_balance/<student_id>/<user_type>')
def bot_student_balance(student_id, user_type):
    student = Students.query.filter(Students.id == student_id).first()
    teacher = Teachers.query.filter(Teachers.id == student_id).first()
    balance = student.user.balance if user_type == "student" else teacher.user.balance
    return jsonify({"balance": balance})
