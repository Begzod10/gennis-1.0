import datetime

from app import app, db, jsonify, request, desc
from backend.models.models import Users, Students, or_, DeletedStudents, CalendarDay, CalendarMonth, CalendarYear, \
    TaskStudents, TasksStatistics, StudentExcuses, Tasks, TaskDailyStatistics, BlackStudents, BlackStudentsStatistics, \
    StudentCallingInfo, LeadInfos, Lead
from backend.functions.utils import api, find_calendar_date, iterate_models, refreshdatas
from sqlalchemy import asc

from backend.tasks.utils import update_debt_progress, update_all_ratings, black_students_count
from flask_jwt_extended import jwt_required, get_jwt_identity


@app.route(f'{api}/student_debts_progress/<int:location_id>/', defaults={"date": None})
@app.route(f'{api}/student_debts_progress/<int:location_id>/<date>')
@jwt_required()
def student_debts_progress(location_id, date):
    date = datetime.datetime.strptime(date, "%Y-%m-%d")
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    table = False
    task = Tasks.query.filter(Tasks.role == "admin", Tasks.name == "excuses").first()
    if date == calendar_day.date:
        students, task_statistics = update_debt_progress(location_id)
        task_daily_statistics = update_all_ratings(location_id)

    elif date < calendar_day.date:
        calendar_day = CalendarDay.query.filter(CalendarDay.date == date).first()

        students = db.session.query(Students).join(Students.user).join(Students.students_tasks).filter(
            Users.location_id == location_id, TaskStudents.status == False,
            TaskStudents.calendar_day == calendar_day.id).order_by(desc(Students.id)).all() if calendar_day else None
        # students = Students.query.join(Users).filter(Users.location_id == location_id).join(Students.excuses).filter(
        #     StudentExcuses.added_date == date).distinct().order_by(Students.id).all()
        task_statistics = TasksStatistics.query.filter(TasksStatistics.location_id == location_id,
                                                       TasksStatistics.task_id == task.id,
                                                       TasksStatistics.calendar_day == calendar_day.id).first() if calendar_day else None

        task_daily_statistics = TaskDailyStatistics.query.filter(TaskDailyStatistics.location_id == location_id,

                                                                 TaskDailyStatistics.calendar_day == calendar_day.id).first() if calendar_day else None
        table = True

    else:

        return jsonify({"students": [], "task_statistics": None, "task_daily_statistics": None, "message": "No data"})
    return jsonify({
        "students": iterate_models(students),
        "task_statistics": task_statistics.convert_json() if task_statistics else None,
        "task_daily_statistics": task_daily_statistics.convert_json() if task_daily_statistics else None,
        "table": table

    })


@app.route(f'{api}/student_debts_completed/<int:location_id>', defaults={"date": None})
@app.route(f'{api}/student_debts_completed/<int:location_id>/<date>')
@jwt_required()
def student_debts_completed(location_id, date):
    date = datetime.datetime.strptime(date, "%Y-%m-%d")
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    table = False
    task = Tasks.query.filter(Tasks.role == "admin", Tasks.name == "excuses").first()
    if date == calendar_day.date:
        _, task_statistics = update_debt_progress(location_id)
        task_daily_statistics = update_all_ratings(location_id)
        students = db.session.query(Students).join(Students.user).join(Students.students_tasks).filter(
            Users.location_id == location_id, TaskStudents.status == True,
            TaskStudents.calendar_day == calendar_day.id, Students.debtor != 4).order_by(desc(Students.id)).all()

    elif date > calendar_day.date:
        table = True
        calendar_day = CalendarDay.query.filter(CalendarDay.date == date).first()
        # students = db.session.query(Students).join(Students.students_tasks).filter(
        #     TaskStudents.location_id == location_id, TaskStudents.status == True).order_by(desc(Students.id)).all()

        students = db.session.query(Students).join(Students.excuses).filter(
            StudentExcuses.to_date == date).distinct().order_by(Students.id).all()

        # task_statistics = TasksStatistics.query.filter(TasksStatistics.location_id == location_id,
        #                                                TasksStatistics.calendar_day == calendar_day.id).first() if calendar_day else None
        # task_daily_statistics = TaskDailyStatistics.query.filter(TaskDailyStatistics.location_id == location_id,
        #                                                          TaskDailyStatistics.calendar_day == calendar_day.id).first() if calendar_day else None
        task_statistics = None
        task_daily_statistics = None
    elif date < calendar_day.date:
        table = True
        calendar_day = CalendarDay.query.filter(CalendarDay.date == date).first()
        students = db.session.query(Students).join(Students.excuses).filter(
            StudentExcuses.added_date == date).distinct().order_by(Students.id).all()

        task_statistics = TasksStatistics.query.filter(TasksStatistics.location_id == location_id,
                                                       TasksStatistics.calendar_day == calendar_day.id,
                                                       TasksStatistics.task_id == task.id).first() if calendar_day else None
        task_daily_statistics = TaskDailyStatistics.query.filter(TaskDailyStatistics.location_id == location_id,
                                                                 TaskDailyStatistics.calendar_day == calendar_day.id).first() if calendar_day else None

    else:
        return jsonify({"students": [], "task_statistics": None, "task_daily_statistics": None, "message": "No data"})

    return jsonify({
        "students": iterate_models(students),
        "task_statistics": task_statistics.convert_json() if task_statistics else None,
        "task_daily_statistics": task_daily_statistics.convert_json() if task_daily_statistics else None,
        "table": table
    })


@app.route(f'{api}/call_to_debts', methods=["POST"])
@jwt_required()
def call_to_debts():
    refreshdatas()
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    data = request.get_json()
    reason = data.get('comment')
    select = data.get('select')
    to_date = data.get('date')
    user_id = data.get('id')
    task_type = Tasks.query.filter(Tasks.name == 'excuses').first()
    student = Students.query.filter(Students.user_id == user_id).first()
    task_statistics = TasksStatistics.query.filter(TasksStatistics.calendar_day == calendar_day.id,
                                                   TasksStatistics.task_id == task_type.id,
                                                   TasksStatistics.location_id == student.user.location_id).first()
    month = datetime.datetime.strptime("2024-08", "%Y-%m")
    if to_date:
        to_date = datetime.datetime.strptime(to_date, "%Y-%m-%d")
    else:
        to_date = calendar_day.date + datetime.timedelta(days=1)

    if to_date > calendar_day.date:
        exist_excuse = StudentExcuses.query.filter(StudentExcuses.added_date == calendar_day.date,
                                                   StudentExcuses.student_id == student.id).first()
        if not exist_excuse:
            if select == "tel ko'tardi":

                new_excuse = StudentExcuses(reason=reason,
                                            to_date=to_date,
                                            added_date=calendar_day.date,
                                            student_id=student.id)

            else:
                new_excuse = StudentExcuses(reason="tel ko'tarmadi",
                                            to_date=to_date,
                                            added_date=calendar_day.date,
                                            student_id=student.id)

            db.session.add(new_excuse)
            db.session.commit()

        task_student = TaskStudents.query.filter(TaskStudents.task_id == task_type.id,
                                                 TaskStudents.tasksstatistics_id == task_statistics.id,
                                                 TaskStudents.student_id == student.id).first()

        task_student.status = True
        db.session.commit()
    students, task_statistics = update_debt_progress(student.user.location_id)
    task_daily_statistics = update_all_ratings(student.user.location_id)
    return jsonify({
        "status": "true",
        "message": "ma'lumot kiritildi",
        "student_id": student.id,
        "task_statistics": task_statistics.convert_json(),
        "task_daily_statistics": task_daily_statistics.convert_json()
    })


@app.route(f'{api}/add_blacklist/<int:user_id>', methods=["GET", "POST"])
@jwt_required()
def add_blacklist2(user_id):
    refreshdatas()
    user_get = Users.query.filter(Users.user_id == get_jwt_identity()).first()
    user = Users.query.filter(Users.id == user_id).first()
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    student = Students.query.filter(Students.user_id == user_id).first()
    data = request.get_json()
    if student.debtor != 4:
        student.debtor = 4
        db.session.commit()
        black_student = BlackStudents.query.filter(BlackStudents.student_id == student.id).first()
        if not black_student:
            new_blacklist = BlackStudents(student_id=student.id, calendar_year=calendar_year.id,
                                          user_id=user_get.id, location_id=student.user.location_id,
                                          calendar_month=calendar_month.id, calendar_day=calendar_day.id,
                                          comment=data.get('comment'))
            db.session.add(new_blacklist)
            db.session.commit()
        else:
            black_student.deleted = False
            black_student.comment = data.get('comment')
            db.session.commit()
        black_students_count(calendar_month=calendar_month.id, calendar_year=calendar_year.id,
                             location_id=student.user.location_id)
        return jsonify({
            "success": True,
            "msg": "Student qora ro'yxatga qo'shildi"
        })

    else:
        black_student = BlackStudents.query.filter(BlackStudents.student_id == student.id).first()
        calendar_year, calendar_month = black_student.calendar_year, black_student.calendar_month
        black_student.deleted = True
        db.session.commit()
        black_students_count(calendar_month=calendar_month, calendar_year=calendar_year,
                             location_id=student.user.location_id)
        student_excuse = StudentExcuses.query.filter(StudentExcuses.student_id == student.id,
                                                     StudentExcuses.to_date > calendar_day.date).order_by(
            desc(StudentExcuses.id)).first()

        if not student_excuse:
            if user.balance >= 0:
                Students.query.filter_by(id=student.id).update({"debtor": 0})
            elif user.balance < 0:
                Students.query.filter_by(id=student.id).update({"debtor": 1})
            elif user.balance >= -student.combined_debt:
                Students.query.filter_by(id=student.id).update({"debtor": 2})
        else:
            Students.query.filter_by(id=student.id).update({"debtor": 3})
        db.session.commit()
        return jsonify({
            "success": True,
            "msg": "Student qora ro'yxatdan olib tashlandi"
        })


@app.route(f'{api}/get_comment/<int:user_id>/<type_comment>', methods=["GET", "POST"])
@jwt_required()
def get_comment(user_id, type_comment):
    student = Students.query.filter(Students.user_id == user_id).first()
    if type_comment == "debtors":
        return jsonify({
            "comments": iterate_models(StudentExcuses.query.filter(StudentExcuses.student_id == student.id).order_by(
                desc(StudentExcuses.id)).all()),
            "info": Students.query.filter(Students.user_id == user_id).first().convert_json()
        })
    elif type_comment == "newStudents":
        return jsonify({
            "comments": iterate_models(
                StudentCallingInfo.query.filter(StudentCallingInfo.student_id == student.id).order_by(
                    desc(StudentCallingInfo.id)).all()),
            "info": Students.query.filter(Students.user_id == user_id).first().convert_json()
        })
    else:

        return jsonify({
            "comments": iterate_models(
                LeadInfos.query.filter(LeadInfos.lead_id == user_id).order_by(desc(LeadInfos.id)).all()),
            "info": Lead.query.filter(Lead.id == user_id).first().convert_json()
        })
