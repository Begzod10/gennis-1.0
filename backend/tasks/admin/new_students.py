from datetime import datetime

from flask import request, jsonify
from flask_jwt_extended import jwt_required

from app import app, db
from backend.functions.utils import api, find_calendar_date, iterate_models
from backend.models.models import Students, StudentCallingInfo, CalendarDay, TaskDailyStatistics
from backend.tasks.models.models import Tasks, TasksStatistics
from backend.tasks.utils import update_all_ratings, filter_new_students

from flask import Blueprint

task_new_students_bp = Blueprint('task_new_students', __name__)


@task_new_students_bp.route(f'/task_new_students/<int:location_id>/<date>', methods=["POST", "GET"])
@jwt_required()
def task_new_students(location_id, date):
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    date = datetime.strptime(date, "%Y-%m-%d")
    task_type = Tasks.query.filter(Tasks.name == 'new_students').first()
    table = False
    if date == calendar_day.date:
        students, task_statistics, _ = filter_new_students(location_id)
        task_daily_statistics = update_all_ratings(location_id)
    else:
        table = True
        calendar_day = CalendarDay.query.filter(CalendarDay.date == date).first()
        students = db.session.query(Students).join(Students.student_calling_info).filter(
            StudentCallingInfo.day == date).distinct().order_by(Students.id).all()
        task_statistics = TasksStatistics.query.filter(TasksStatistics.location_id == location_id,
                                                       TasksStatistics.calendar_day == calendar_day.id,
                                                       TasksStatistics.task_id == task_type.id).first() if calendar_day else None
        task_daily_statistics = TaskDailyStatistics.query.filter(TaskDailyStatistics.location_id == location_id,
                                                                 TaskDailyStatistics.calendar_day == calendar_day.id).first() if calendar_day else None
    return jsonify({
        "students": iterate_models(students),
        "task_statistics": task_statistics.convert_json(),
        "task_daily_statistics": task_daily_statistics.convert_json(),
        "table": table
    })


@task_new_students_bp.route(f'/completed_new_students/<int:location_id>/<date>', methods=["POST", "GET"])
@jwt_required()
def completed_new_students(location_id, date):
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    date = datetime.strptime(date, "%Y-%m-%d")
    task_type = Tasks.query.filter(Tasks.name == 'new_students').first()
    table = True
    if date == calendar_day.date:
        _, task_statistics, students = filter_new_students(location_id)
        task_daily_statistics = update_all_ratings(location_id)
        table = False

    elif date > calendar_day.date:

        calendar_day = CalendarDay.query.filter(CalendarDay.date == date).first()
        students = db.session.query(Students).join(Students.student_calling_info).filter(
            StudentCallingInfo.date == date).distinct().order_by(Students.id).all()
        task_statistics = TasksStatistics.query.filter(TasksStatistics.location_id == location_id,
                                                       TasksStatistics.calendar_day == calendar_day.id,
                                                       TasksStatistics.task_id == task_type.id).first() if calendar_day else None
        task_daily_statistics = TaskDailyStatistics.query.filter(TaskDailyStatistics.location_id == location_id,
                                                                 TaskDailyStatistics.calendar_day == calendar_day.id).first() if calendar_day else None
    else:

        calendar_day = CalendarDay.query.filter(CalendarDay.date == date).first()
        students = db.session.query(Students).join(Students.student_calling_info).filter(
            StudentCallingInfo.day == date).distinct().order_by(Students.id).all()
        task_statistics = TasksStatistics.query.filter(TasksStatistics.location_id == location_id,
                                                       TasksStatistics.calendar_day == calendar_day.id,
                                                       TasksStatistics.task_id == task_type.id).first() if calendar_day else None
        task_daily_statistics = TaskDailyStatistics.query.filter(TaskDailyStatistics.location_id == location_id,
                                                                 TaskDailyStatistics.calendar_day == calendar_day.id).first() if calendar_day else None
    return jsonify({
        "students": iterate_models(students),
        "task_statistics": task_statistics.convert_json() if task_statistics else None,
        "task_daily_statistics": task_daily_statistics.convert_json() if task_daily_statistics else None,
        "table": table
    })


@task_new_students_bp.route(f'/call_to_new_students', methods=["POST"])
def call_to_new_students():
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    student_info = request.get_json()
    date = datetime.strptime(student_info['date'], "%Y-%m-%d")
    if date > calendar_day.date:
        student = Students.query.filter_by(user_id=student_info['id']).first()
        exist_info = StudentCallingInfo.query.filter_by(
            student_id=student.id,
            day=datetime.today().now()
        ).first()

        if not exist_info:
            add_info = StudentCallingInfo(
                student_id=student.id,
                comment=student_info['comment'],
                day=calendar_day.date,
                date=date
            )
            db.session.add(add_info)
            db.session.commit()
        students, task_statistics, _ = filter_new_students(student.user.location_id)
        task_daily_statistics = update_all_ratings(student.user.location_id)
        return jsonify({
            "student": {
                'msg': "Comment muvaffaqiyatli qo'shildi",
                "student_id": student.user.id,
                "task_statistics": task_statistics.convert_json(),
                "task_daily_statistics": task_daily_statistics.convert_json()
            }
        })
    else:
        return jsonify({'msg': "Eski sana kiritilgan"})
