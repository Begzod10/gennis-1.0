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

    # Fetch all students with their related user, subjects, and phones
    students = Students.query.join(Users).filter(
        Users.location_id == location_id,
        Users.student != None,
        Students.subject != None,
        Students.deleted_from_register == None
    ).order_by(desc(Students.id)).all()

    # Query calling information for the students in one go
    calling_info = StudentCallingInfo.query.filter(
        StudentCallingInfo.student_id.in_([student.id for student in students])
    ).all()

    # Create a mapping of student_id to calling info
    calling_info_dict = {call.student_id: [] for call in calling_info}
    for call in calling_info:
        calling_info_dict[call.student_id].append(call)

    # Use list comprehensions to gather and process all data in bulk
    students_info = []
    completed_tasks = []

    # Query phone and subjects in bulk for better performance
    student_phone_dict = {student.id: next((phone.phone for phone in student.user.phone if phone.personal), None) for student in students}
    student_subject_dict = {student.id: [subject.name for subject in student.subject] for student in students}
    student_shift_dict = {student.id: '1-smen' if student.morning_shift else '2-smen' if student.night_shift else 'Hamma vaqt' for student in students}
    student_registered_date_dict = {student.id: f'{student.user.year.date.year}-{student.user.month.date.month}-{student.user.day.date.day}' for student in students}

    # Process students and categorize based on calling history and status
    students_info = [
        {
            'id': student.id,
            'name': student.user.name,
            'surname': student.user.surname,
            'phone': student_phone_dict[student.id],
            'subject': student_subject_dict[student.id],
            'registered_date': student_registered_date_dict[student.id],
            'shift': student_shift_dict[student.id],
            'history': [{
                'id': call.id,
                'comment': call.comment,
                'day': f'{call.day.year}-{call.day.month}-{call.day.day}',
                'date': call.date
            } for call in calling_info_dict.get(student.id, [])],
            'status': 'red' if not calling_info_dict.get(student.id) else 'yellow'
        }
        for student in students
    ]

    # Update status based on calling history
    for student_info in students_info:
        if student_info['history']:
            last_call = student_info['history'][-1]
            if last_call['date'] <= date_strptime:
                days_since_last_call = (today - last_call['date']).days
                student_info['status'] = 'yellow' if days_since_last_call == 0 else 'red'

            added_date_strptime = datetime.strptime(last_call['day'], "%Y-%m-%d")
            if added_date_strptime == date_strptime and last_call['date'] > date_strptime:
                student_info['status'] = 'yellow'

    # Split students into categories based on their calling history
    students_info_to_show = [
        student_info for student_info in students_info if student_info['status'] == 'yellow' or not student_info['history']
    ]
    completed_tasks = [
        student_info for student_info in students_info if student_info['status'] != 'yellow' and student_info['history'] and not any(call.date.date() < today.date() for call in student_info['history'])
    ]

    calendar_year, calendar_month, calendar_day = find_calendar_date()

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

    if request.method == "GET":
        change_statistics(location_id)
        update_task_statistics(location_id, students_info_to_show, completed_tasks, calendar_day)
        update_all_ratings(location_id)

        return jsonify({
            "students": students_info_to_show,
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
            update_all_ratings(location_id)

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


        date = datetime.strptime(request.get_json()['date'], "%Y-%m-%d")

        today = datetime.today()
        if date.date() == today.date():
            students = {
                'result': [],
                'is_selected': False
            }
        else:
            students = {
                'result': [],
                'is_selected': True
            }
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
                'day': student.day.strftime("%Y-%m-%d"),
                'date': student.date.strftime("%Y-%m-%d"),
                'comment': student.comment,
            }
            students['result'].append(info)
    return jsonify(students)
