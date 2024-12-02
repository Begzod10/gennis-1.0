from datetime import datetime

from flask_jwt_extended import jwt_required
from sqlalchemy import func

from app import app, request, jsonify, db
from backend.functions.utils import api, find_calendar_date, iterate_models
from backend.models.models import Students, StudentCallingInfo, Users
from backend.models.models import desc
from backend.student.functions import change_statistics
from backend.tasks.models.models import Tasks, TasksStatistics
from backend.tasks.utils import update_all_ratings, filter_new_students


@app.route(f'{api}/task_new_students/<int:location_id>', methods=["POST", "GET"])
@jwt_required()
def task_new_students(location_id):
    students, task_statistics = filter_new_students(location_id)
    task_daily_statistics = update_all_ratings(location_id)

    return jsonify({
        "students": students,
        "task_statistics": task_statistics.convert_json(),
        "task_daily_statistics": task_daily_statistics.convert_json()
    })


@app.route(f'{api}/call_to_new_students', methods=["POST"])
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
                day=datetime.today().now(),
                date=date
            )
            db.session.add(add_info)
            db.session.commit()
        students, task_statistics = filter_new_students(student.user.location_id)
        task_daily_statistics = update_all_ratings((student.user.location_id))
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
