from datetime import datetime

from app import app, request, jsonify, db
from backend.functions.utils import api, find_calendar_date
from backend.models.models import Students, StudentCallingInfo, Users
from backend.models.models import desc
from backend.student.functions import change_statistics, \
    update_all_ratings
from backend.tasks.models.models import Tasks, TasksStatistics


@app.route(f'{api}/task_new_students_calling/<int:location_id>', methods=["POST", "GET"])
# @jwt_required()
def new_students_calling(location_id):
    def get_student_info(student, date_strptime, today):
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
                    'day': f'{calling_info.day.year}-{calling_info.day.month}-{calling_info.day.day}'
                }
                info['history'].append(calling_date)

            last_call = student.student_calling_info[-1]
            if last_call.date <= date_strptime:
                index = 1 if last_call.date.month != today.month else min(max(0, today.day - last_call.date.day), 1)
                info['status'] = ['yellow', 'red'][index]

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
        task_statistics.completed_tasks_percentage = round(
            (completed_tasks_count / total_tasks) * 100
        )

        db.session.commit()

    today = datetime.today()
    date_strptime = today.replace(hour=0, minute=0, second=0, microsecond=0)

    students = Students.query.join(Users).filter(
        Users.location_id == location_id,
        Users.student != None,
        Students.subject != None,
        Students.deleted_from_register == None
    ).order_by(desc(Students.id)).all()

    students_info = []
    completed_tasks = []

    for student in students:
        info = get_student_info(student, date_strptime, today)
        students_info.append(info)
        if info['status'] == 'yellow':
            completed_tasks.append(info)

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
                add_info.add()

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
            return jsonify({
                'msg': "Eski sana kiritilgan",
            })
