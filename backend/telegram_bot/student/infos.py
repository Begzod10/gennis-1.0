import pprint
from datetime import datetime

from backend.models.models import StudentPayments, Students, Attendance, AttendanceDays, \
    CalendarDay, \
    CalendarYear, CalendarMonth, AttendanceHistoryStudent, StudentTest, GroupTest, Groups, \
    StudentHistoryGroups
from backend.functions.utils import iterate_models, find_calendar_date
from flask import Blueprint, jsonify
from sqlalchemy import desc

student_bp = Blueprint('student', __name__)


@student_bp.route(f'payments/<student_id>')
def bot_student_payments(student_id):
    student_payments = StudentPayments.query.filter(StudentPayments.student_id == student_id).order_by(
        desc(StudentPayments.id)).all()
    return jsonify({"payments": iterate_models(student_payments)})


@student_bp.route(f'test/results/<student_id>')
def bot_student_test_results(student_id):
    tests = []
    student_tests = StudentTest.query.filter(StudentTest.student_id == student_id).order_by(desc(StudentTest.id)).all()
    group_ids = [gr.group_id for gr in student_tests]
    group_ids = list(dict.fromkeys(group_ids))

    groups = Groups.query.filter(Groups.id.in_(group_ids)).join(Groups.test).order_by(GroupTest.calendar_day).all()
    for gr in groups:
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


@student_bp.route(f'attendance/dates/<int:student_id>')
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


@student_bp.route(f'attendances/<student_id>/<set_year>/<set_month>')
def bot_student_attendances(student_id, set_year, set_month):
    set_month = set_year + "-" + set_month
    set_year = datetime.strptime(set_year, "%Y")
    set_month = datetime.strptime(set_month, "%Y-%m")
    calendar_year = CalendarYear.query.filter(CalendarYear.date == set_year).first()
    calendar_month = CalendarMonth.query.filter(CalendarMonth.date == set_month).first()
    student_history_groups = StudentHistoryGroups.query.filter(StudentHistoryGroups.student_id == student_id).all()
    group_ids = [gr.group_id for gr in student_history_groups]
    group_ids = list(dict.fromkeys(group_ids))
    group = Groups.query.filter(Groups.id.in_(group_ids)).order_by(Groups.id).all()
    attendance_list = []
    for gr in group:
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
        if len(attendance) != 0:
            info["attendances"] = iterate_models(attendance)
            attendance_list.append(info)
    return jsonify({"attendances": attendance_list})


@student_bp.route(f'scores/<student_id>/<set_year>/<set_month>')
def scores(student_id, set_year, set_month):
    set_month = set_year + "-" + set_month
    set_year = datetime.strptime(set_year, "%Y")
    set_month = datetime.strptime(set_month, "%Y-%m")
    calendar_year = CalendarYear.query.filter(CalendarYear.date == set_year).first()
    calendar_month = CalendarMonth.query.filter(CalendarMonth.date == set_month).first()
    student_history_groups = StudentHistoryGroups.query.filter(StudentHistoryGroups.student_id == student_id).all()
    group_ids = [gr.group_id for gr in student_history_groups]
    group_ids = list(dict.fromkeys(group_ids))
    group = Groups.query.filter(Groups.id.in_(group_ids)).order_by(Groups.id).all()
    score_list = []
    for gr in group:
        got_scored = AttendanceDays.query.filter(AttendanceDays.student_id == student_id,
                                                 AttendanceDays.group_id == gr.id).join(
            AttendanceDays.attendance).filter(Attendance.calendar_year == calendar_year.id,
                                              AttendanceDays.average_ball != None,
                                              Attendance.calendar_month == calendar_month.id).join(
            AttendanceDays.day).order_by(
            CalendarDay.date).all()
        average = 0
        if len(got_scored) > 0:
            info = {
                "id": gr.id,
                "name": gr.name,
                "teacher": f"{gr.teacher[0].user.name} {gr.teacher[0].user.surname}",
                "subject": gr.subject.name,
                "score": [],
                "current_month": calendar_month.date.strftime("%Y-%m"),
                "average_ball": 0,
                "dictionary_status": True if gr.subject.ball_number and gr.subject.ball_number > 2 else False
            }
            for ball in got_scored:
                average += ball.average_ball
            average = round(average / len(got_scored))
            info['score'] = iterate_models(got_scored)
            info['average_ball'] = average
            score_list.append(info)
    return jsonify({
        "score_list": score_list
    })
