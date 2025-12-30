import pprint
from datetime import datetime

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from backend.functions.utils import api, find_calendar_date, iterate_models
from backend.models.models import Students, StudentCallingInfo, CalendarDay, TaskDailyStatistics, db, \
    StudentCallingInfoAudio, Users
from backend.tasks.models.models import Tasks, TasksStatistics
from backend.tasks.utils import update_all_ratings, filter_new_students
from backend.celery.new_students import process_new_student_call
from flask import Blueprint
from sqlalchemy import desc

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

    if date == calendar_day.date:
        _, task_statistics, students = filter_new_students(location_id)
        task_daily_statistics = update_all_ratings(location_id)

        records = StudentCallingInfo.query.filter(
            StudentCallingInfo.day == date,
            StudentCallingInfo.student_id.in_([student.id for student in students])
        ).order_by(StudentCallingInfo.id).all()
    elif date > calendar_day.date:

        calendar_day = CalendarDay.query.filter(CalendarDay.date == date).first()
        students = db.session.query(Students).join(Students.student_calling_info).filter(
            StudentCallingInfo.date == date).distinct().order_by(Students.id).all()
        task_statistics = TasksStatistics.query.filter(TasksStatistics.location_id == location_id,
                                                       TasksStatistics.calendar_day == calendar_day.id,
                                                       TasksStatistics.task_id == task_type.id).first() if calendar_day else None
        task_daily_statistics = TaskDailyStatistics.query.filter(TaskDailyStatistics.location_id == location_id,
                                                                 TaskDailyStatistics.calendar_day == calendar_day.id).first() if calendar_day else None

        records = StudentCallingInfo.query.filter(
            StudentCallingInfo.date == date,
            StudentCallingInfo.student_id.in_([student.id for student in students])
        ).order_by(StudentCallingInfo.id).all()
    else:

        calendar_day = CalendarDay.query.filter(CalendarDay.date == date).first()
        students = db.session.query(Students).join(Students.student_calling_info).filter(
            StudentCallingInfo.day == date).distinct().order_by(Students.id).all()
        task_statistics = TasksStatistics.query.filter(TasksStatistics.location_id == location_id,
                                                       TasksStatistics.calendar_day == calendar_day.id,
                                                       TasksStatistics.task_id == task_type.id).first() if calendar_day else None
        task_daily_statistics = TaskDailyStatistics.query.filter(TaskDailyStatistics.location_id == location_id,
                                                                 TaskDailyStatistics.calendar_day == calendar_day.id).first() if calendar_day else None

        records = StudentCallingInfo.query.filter(
            StudentCallingInfo.day == date,
            StudentCallingInfo.student_id.in_([student.id for student in students])
        ).order_by(StudentCallingInfo.id).all()
    return jsonify({
        "students": iterate_models(students),
        "task_statistics": task_statistics.convert_json() if task_statistics else None,
        "task_daily_statistics": task_daily_statistics.convert_json() if task_daily_statistics else None,
        "table": True,
        "records": iterate_models(records)
    })


@task_new_students_bp.route('/call_to_new_student', methods=["POST"])
@jwt_required()
def call_to_new_student():
    """
    Initiate a call to a new student

    Request body:
        {
            "id": 123,  // user_id
            "phone": "998901234567"
        }

    Returns:
        {
            "message": "Call processing started",
            "task_id": "task-uuid",
            "status": "processing",
            "user_id": 123
        }
    """
    data = request.get_json()

    # Get parameters
    student_id = data.get('student_id')  # This is user_id
    phone = data.get('phone')
    identity = get_jwt_identity()
    user = Users.query.filter(Users.user_id == identity).first()
    if not user.crm_username:
        return jsonify({"error": "Missing 'crm_username'"}), 400
    else:
        if user.crm_username not in ['gennis_center', 'gennis_chirchiq', 'gennis_chorvoq', 'gennis_gazalkent',
                                     'gennis_nurafshon','admin']:
            return jsonify({"error": "CRM username is invalid"}), 400
    # Validate input
    if not student_id:
        return jsonify({"error": "Student ID (user_id) is required"}), 400

    if not phone:
        return jsonify({"error": "Phone number is required"}), 400

    # Verify student exists
    student = Students.query.filter_by(id=student_id).first()
    if not student:
        return jsonify({"error": "Student not found"}), 404

    # Queue the call task
    task = process_new_student_call.delay(student_id, phone, user.crm_username)

    return jsonify({
        "message": "Call processing started",
        "task_id": task.id,
        "status": "processing",
        "user_id": student_id,
        "student_id": student.id
    }), 202


@task_new_students_bp.route('/call-status/<task_id>', methods=["GET"])
def check_new_student_call_status(task_id):
    """
    Check the status of a new student call task

    Args:
        task_id: Celery task ID

    Returns:
        {
            "state": "SUCCESS|PENDING|FAILURE",
            "result": {...}
        }
    """
    from backend.celery.new_students import process_new_student_call

    task = process_new_student_call.AsyncResult(task_id)
    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'status': 'Task is waiting...'
        }
    elif task.state == 'SUCCESS':
        response = {
            'state': task.state,
            'result': task.result
        }
    elif task.state == 'FAILURE':
        response = {
            'state': task.state,
            'error': str(task.info)
        }
    else:
        response = {
            'state': task.state,
            'status': str(task.info)
        }

    return jsonify(response)


@task_new_students_bp.route(f'/call_to_new_students', methods=["POST"])
def call_to_new_students():
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    student_info = request.get_json()
    date = datetime.strptime(student_info['date'], "%Y-%m-%d")
    if date > calendar_day.date:
        student_calling_audio = StudentCallingInfoAudio.query.filter_by(id=student_info['id']).first()
        student_calling_info = StudentCallingInfo.query.filter_by(
            id=student_calling_audio.student_calling_info_id).first()
        student = Students.query.filter_by(id=student_calling_info.student_id).first()
        student_calling_info.comment = student_info['comment']
        student_calling_info.date = date
        db.session.commit()
        students, task_statistics, _ = filter_new_students(student.user.location_id)
        task_daily_statistics = update_all_ratings(student.user.location_id)
        return jsonify({
            "student": {
                'msg': "Comment muvaffaqiyatli qo'shildi",
                "student_id": student.user.id,
            },
            "task_statistics": task_statistics.convert_json(),
            "task_daily_statistics": task_daily_statistics.convert_json()
        })
    else:
        return jsonify({'msg': "Eski sana kiritilgan"})


@task_new_students_bp.route(f'/new_students_records/<int:student_id>', methods=["GET", "POST"])
def debts_records(student_id):
    student = Students.query.filter(Students.id == student_id).first()
    return jsonify({
        "comments": iterate_models(
            StudentCallingInfo.query.filter(StudentCallingInfo.student_id == student.id).order_by(
                desc(StudentCallingInfo.id)).all(), entire=True),
        "info": Students.query.filter(Students.id == student_id).first().convert_json()
    })
