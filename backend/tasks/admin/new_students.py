from datetime import datetime

from flask_jwt_extended import jwt_required
from sqlalchemy import func

from app import app, request, jsonify, db
from backend.functions.utils import api, find_calendar_date
from backend.models.models import Students, StudentCallingInfo, Users
from backend.models.models import desc
from backend.student.functions import change_statistics, update_all_ratings
from backend.tasks.models.models import Tasks, TasksStatistics


@app.route(f'{api}/task_new_students_calling/<int:location_id>', methods=["POST", "GET"])
@jwt_required()
def task_new_students_calling(location_id):
    today = datetime.today()
    date_strptime = today.replace(hour=0, minute=0, second=0, microsecond=0)

    def get_student_info(student):
        phone = next((phones.phone for phones in student.user.phone if phones.personal), None)
        subjects = [subject.name for subject in student.subject]
        shift = '1-smen' if student.morning_shift else '2-smen' if student.night_shift else 'Hamma vaqt'

        info = {
            'id': student.id,
            'name': student.user.name,
            'surname': student.user.surname,
            'phone': phone,
            'subject': subjects,
            'registered_date': f'{student.user.year.date.year}-{student.user.month.date.month}-{student.user.day.date.day}',
            'shift': shift,
            'history': [],
            'status': 'red',
        }

        if student.student_calling_info:
            for calling_info in student.student_calling_info:
                calling_date = {
                    'id': calling_info.id,
                    'comment': calling_info.comment,
                    'day': f'{calling_info.day.year}-{calling_info.day.month}-{calling_info.day.day}',
                    "date": calling_info.date
                }
                info['history'].append(calling_date)

            last_call = student.student_calling_info[-1]

            if last_call.date <= date_strptime:
                days_since_last_call = (today - last_call.date).days
                info['status'] = 'yellow' if days_since_last_call == 0 else 'red'

            added_date_strptime = datetime.strptime(f'{last_call.day.year}-{last_call.day.month}-{last_call.day.day}',
                                                    "%Y-%m-%d")
            if added_date_strptime == date_strptime and last_call.date > date_strptime:
                info['status'] = 'yellow'

        return info

    def update_task_statistics(location_id, students_info, completed_tasks, calendar_day):
        task_type = Tasks.query.filter_by(name='new_students').first()
        task_statistics = TasksStatistics.query.filter_by(
            task_id=task_type.id,
            calendar_day=calendar_day.id,
            location_id=location_id
        ).first()

        total_tasks = len(students_info)
        completed_tasks_count = len(completed_tasks)

        task_statistics.completed_tasks = completed_tasks_count
        task_statistics.in_progress_tasks = total_tasks
        task_statistics.completed_tasks_percentage = round((completed_tasks_count / total_tasks) * 100)

        db.session.commit()

    students = Students.query.join(Users).filter(
        Users.location_id == location_id,
        Users.student != None,
        Students.subject != None,
        Students.deleted_from_register == None
    ).order_by(desc(Students.id)).all()

    students_info = []
    completed_tasks = []

    def is_past_day_exist(calling_dates):
        return any(day.date() < today.date() for day in calling_dates)

    for student in students:
        info = get_student_info(student)
        if info['status'] == 'yellow':
            calling_dates = [i['date'] for i in info['history']]
            if is_past_day_exist(calling_dates):
                students_info.append(info)
            else:
                completed_tasks.append(info)
        else:
            students_info.append(info)

    calendar_year, calendar_month, calendar_day = find_calendar_date()

    if request.method == "GET":
        change_statistics(location_id)
        update_task_statistics(location_id, students_info, completed_tasks, calendar_day)
        update_all_ratings()

        return jsonify({
            "students": students_info,
            'completed_tasks': completed_tasks
        })

    if request.method == "POST":
        student_info = request.get_json()
        date = datetime.strptime(student_info['date'], "%Y-%m-%d")

        if date > calendar_day.date:
            exist_info = StudentCallingInfo.query.filter_by(
                student_id=student_info['id'],
                day=datetime.today().now()
            ).first()

            if not exist_info:
                add_info = StudentCallingInfo(
                    student_id=student_info['id'],
                    comment=student_info['comment'],
                    day=datetime.today().now(),
                    date=date
                )
                db.session.add(add_info)
                db.session.commit()

            update_task_statistics(location_id, students_info, completed_tasks, calendar_day)
            update_all_ratings()

            return jsonify({
                "student": {
                    'msg': "Comment muvaffaqiyatli qo\'shildi",
                    'id': student_info['id'],
                    "students_num": len(students_info)
                }
            })
        else:
            return jsonify({'msg': "Eski sana kiritilgan"})


@app.route(f'{api}/task_new_students_filter/<int:location_id>', methods=["POST", "GET"])
@jwt_required()
def task_new_students_filter(location_id):
    if request.method == "POST":
        students = []
        today = datetime.today()
        date = datetime.strptime(request.get_json()['date'], "%Y-%m-%d")
        if date.date() <= today.date():
            query = StudentCallingInfo.query.filter(
                func.extract('year', StudentCallingInfo.day) == date.year,
                func.extract('month', StudentCallingInfo.day) == date.month,
                func.extract('day', StudentCallingInfo.day) == date.day
            ).all()
        else:
            query = StudentCallingInfo.query.filter(
                func.extract('year', StudentCallingInfo.date) == date.year,
                func.extract('month', StudentCallingInfo.date) == date.month,
                func.extract('day', StudentCallingInfo.date) == date.day
            ).all()

        for student in query:
            info = {
                'student': student.student_id,
                'name': student.student.user.name,
                'surname': student.student.user.surname,
                'phone': next((phones.phone for phones in student.student.user.phone if phones.personal), None),
                'subject': [subject.name for subject in student.student.subject],
                'registered_date': f'{student.student.user.year.date.year}-{student.student.user.month.date.month}-{student.student.user.day.date.day}',
                'shift': '1-smen' if student.student.morning_shift else '2-smen' if student.student.night_shift else 'Hamma vaqt',
                'day': student.day,
                'date': student.date,
                'comment': student.comment
            }
            students.append(info)
    return jsonify(students)
