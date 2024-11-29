import datetime

from app import app, db, jsonify, request
from backend.models.models import Users, Students, or_, DeletedStudents, CalendarDay, CalendarMonth, CalendarYear, \
    TaskStudents, TasksStatistics, StudentExcuses, Tasks
from backend.functions.utils import api, find_calendar_date
from sqlalchemy import asc
from backend.student.functions import update_tasks_in_progress, update_all_ratings
from backend.tasks.utils import filter_debts


@app.route(f'{api}/student_debts/<int:location_id>/<date>', methods=["POST", "GET"])
def student_debts(location_id, date):
    month = datetime.datetime.strptime(f"{date}", "%Y-%m")  # "2024-08"
    task_type = Tasks.query.filter(Tasks.name == 'excuses').first()
    calendar_year, calendar_month, calendar_day = find_calendar_date()

    # calendar_year, calendar_month, calendar_day = find_calendar_date(date_day=day, date_month=month, date_year=year)
    update_tasks_in_progress(location_id, month)
    update_all_ratings(location_id)
    print(location_id)
    task_statistics = TasksStatistics.query.filter(
        TasksStatistics.task_id == task_type.id,
        TasksStatistics.calendar_day == calendar_day.id,
        TasksStatistics.location_id == location_id
    ).first()
    print(task_statistics)
    task_students = TaskStudents.query.filter(TaskStudents.task_id == task_type.id,
                                              TaskStudents.status == False,
                                              TaskStudents.tasksstatistics_id == task_statistics.id,
                                              ).all()
    task_student = TaskStudents.query.filter(TaskStudents.task_id == task_type.id,
                                             TaskStudents.tasksstatistics_id == task_statistics.id,
                                             TasksStatistics.location_id == location_id).first()
    if task_student:
        students = Students.query.filter(Students.id.in_([st.student_id for st in task_students]))
    else:

        students, deleted_student_ids = filter_debts(location_id, month)

    if not task_student:
        for student in students:
            add_task_student = TaskStudents(task_id=task_type.id, tasksstatistics_id=task_statistics.id,
                                            student_id=student.id)
            add_task_student.add()

    return jsonify({
        "status": "true",
        # "deleted_students": len(deleted_student_ids),
        # "students": len(students)
    })


@app.route(f'{api}/call_to_debts', methods=["POST"])
def call_to_debts():
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    data = request.get_json()
    reason = data.get('comment')
    select = data.get('select')
    to_date = data.get('date')
    user_id = data.get('id')
    task_type = Tasks.query.filter(Tasks.name == 'excuses').first()
    task_statistics = TasksStatistics.query.filter_by(task_id=task_type.id).first()
    print("select", select)
    print("reason", reason)
    print(select == "tel ko'tardi")
    if to_date:
        to_date = datetime.datetime.strptime(to_date, "%Y-%m-%d")
    else:
        to_date = calendar_day.date

    student = Students.query.filter(Students.id == user_id).first()
    if to_date > calendar_day.date:
        exist_excuse = StudentExcuses.query.filter(StudentExcuses.added_date == calendar_day.date,
                                                   StudentExcuses.student_id == student.id).first()
        if not exist_excuse:
            if select == "tel ko'tardi":

                new_excuse = StudentExcuses(reason=reason,
                                            to_date=to_date,
                                            added_date=calendar_day.date,
                                            student_id=student.id)
                print(True)
            else:
                new_excuse = StudentExcuses(reason="tel ko'tarmadi",
                                            to_date=to_date,
                                            added_date=calendar_day.date,
                                            student_id=student.id)
                print(False)
            db.session.add(new_excuse)
            db.session.commit()

        task_student = TaskStudents.query.filter(TaskStudents.task_id == task_type.id,
                                                 TaskStudents.tasksstatistics_id == task_statistics.id,
                                                 TaskStudents.student_id == student.id).first()
        task_student.status = True
        db.session.commit()
    return jsonify({
        "status": "true",
        "message": "ma'lumot kiritildi"
    })
