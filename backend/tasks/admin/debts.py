import datetime

import pytz
from flask_jwt_extended import jwt_required, get_jwt_identity

from flask import Blueprint
from sqlalchemy.orm import joinedload
from sqlalchemy import desc
from flask import jsonify, request
from backend.celery.debt_calls import process_student_call
from backend.functions.utils import api, find_calendar_date, iterate_models, refreshdatas
from backend.models.models import Users, Students, CalendarDay, TaskStudents, TasksStatistics, StudentExcuses, Tasks, \
    TaskDailyStatistics, BlackStudents, StudentCallingInfo, LeadInfos, Lead, db, PhoneList
from backend.student.models import StudentExcusesAudio
from backend.tasks.utils import update_debt_progress, update_all_ratings, black_students_count
from sqlalchemy import func, and_

task_debts = Blueprint('task_debts', __name__)


@task_debts.route(f'/student_debts_progress/<int:location_id>/', defaults={"date": None})
@task_debts.route(f'/student_debts_progress/<int:location_id>/<date>')
@jwt_required()
def student_debts_progress(location_id, date):
    # try:
    #     # Parse and validate date
    if not date:
        return jsonify({
            "error": "Date is required",
            "students": [],
            "task_statistics": None,
            "task_daily_statistics": None,
            "table": False
        }), 400

    date_obj = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    current_date = calendar_day.date.date() if isinstance(calendar_day.date,
                                                          datetime.datetime) else calendar_day.date

    # Get task (consider caching this)
    task = Tasks.query.filter(Tasks.role == "admin", Tasks.name == "excuses").first()
    if not task:
        return jsonify({
            "error": "Excuses task not found",
            "students": [],
            "task_statistics": None,
            "task_daily_statistics": None,
            "table": False
        }), 404

    # Check date type
    is_current = date_obj == current_date
    is_past = date_obj < current_date
    is_future = date_obj > current_date

    # Future dates are not allowed
    if is_future:
        return jsonify({
            "students": [],
            "task_statistics": None,
            "task_daily_statistics": None,
            "table": False,
            "message": "Future date not allowed"
        }), 200

    # Current day - use live data
    if is_current:
        students, task_statistics = update_debt_progress(location_id)
        task_daily_statistics = update_all_ratings(location_id)

        return jsonify({
            "students": iterate_models(students) if students else [],
            "task_statistics": task_statistics.convert_json() if task_statistics else None,
            "task_daily_statistics": task_daily_statistics.convert_json() if task_daily_statistics else None,
            "table": False
        }), 200

    # Past day - query historical data
    past_calendar_day = CalendarDay.query.filter(
        func.date(CalendarDay.date) == date_obj
    ).first()

    if not past_calendar_day:
        return jsonify({
            "students": [],
            "task_statistics": None,
            "task_daily_statistics": None,
            "table": True,
            "message": "No data for this date"
        }), 200

    # Query students with incomplete tasks
    students = db.session.query(Students).join(
        Students.user
    ).join(
        Students.students_tasks
    ).filter(
        Users.location_id == location_id,
        TaskStudents.status == False,
        TaskStudents.calendar_day == past_calendar_day.id
    ).order_by(desc(Students.id)).all()

    # Query statistics efficiently
    task_statistics = TasksStatistics.query.filter(
        TasksStatistics.location_id == location_id,
        TasksStatistics.task_id == task.id,
        TasksStatistics.calendar_day == past_calendar_day.id
    ).first()

    task_daily_statistics = TaskDailyStatistics.query.filter(
        TaskDailyStatistics.location_id == location_id,
        TaskDailyStatistics.calendar_day == past_calendar_day.id
    ).first()

    return jsonify({
        "students": iterate_models(students) if students else [],
        "task_statistics": task_statistics.convert_json() if task_statistics else None,
        "task_daily_statistics": task_daily_statistics.convert_json() if task_daily_statistics else None,
        "table": True
    }), 200


# except ValueError as e:
#     return jsonify({
#         "error": f"Invalid date format. Expected YYYY-MM-DD: {str(e)}",
#         "students": [],
#         "task_statistics": None,
#         "task_daily_statistics": None,
#         "table": False
#     }), 400
# except Exception as e:
#     db.session.rollback()
#     return jsonify({
#         "error": f"Server error: {str(e)}",
#         "students": [],
#         "task_statistics": None,
#         "task_daily_statistics": None,
#         "table": False
#     }), 500


@task_debts.route(f'/student_debts_completed/<int:location_id>', defaults={"date": None})
@task_debts.route(f'/student_debts_completed/<int:location_id>/<date>')
@jwt_required()
def student_debts_completed(location_id, date):
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    current_date = calendar_day.date.date() if isinstance(calendar_day.date, datetime.datetime) else calendar_day.date

    # Parse date - use current_date if date is None
    date_obj = datetime.datetime.strptime(date, "%Y-%m-%d").date() if date else current_date

    # Get task once
    task = Tasks.query.filter(Tasks.role == "admin", Tasks.name == "excuses").first()
    if not task:
        return jsonify({
            "students": [],
            "task_statistics": None,
            "task_daily_statistics": None,
            "table": True,
            "records": []
        }), 404

    # Base student query
    base_student_query = db.session.query(Students).join(Students.user).filter(
        Users.location_id == location_id
    )

    # Determine date relationship
    is_current = date_obj == current_date
    is_future = date_obj > current_date

    if is_current:
        # Current day logic
        _, task_statistics = update_debt_progress(location_id)
        task_daily_statistics = update_all_ratings(location_id)

        students = base_student_query.join(Students.students_tasks).filter(
            TaskStudents.status == True,
            TaskStudents.tasksstatistics_id == task_statistics.id,
            TaskStudents.calendar_day == calendar_day.id,
            Students.debtor != 4,
            TaskStudents.task_id == task.id
        ).order_by(desc(Students.id)).all()

        excuse_date_filter = func.date(StudentExcuses.added_date) == date_obj

    elif is_future:
        # Future date logic
        students = base_student_query.join(Students.excuses).filter(
            func.date(StudentExcuses.to_date) == date_obj
        ).distinct().order_by(Students.id).all()

        task_statistics = None
        task_daily_statistics = None
        excuse_date_filter = func.date(StudentExcuses.to_date) == date_obj

    else:
        # Past date logic
        target_calendar_day = CalendarDay.query.filter(
            func.date(CalendarDay.date) == date_obj
        ).first()

        students = base_student_query.join(Students.excuses).filter(
            func.date(StudentExcuses.added_date) == date_obj
        ).distinct().order_by(Students.id).all()

        if target_calendar_day:
            task_statistics = TasksStatistics.query.filter(
                TasksStatistics.location_id == location_id,
                TasksStatistics.calendar_day == target_calendar_day.id,
                TasksStatistics.task_id == task.id
            ).first()

            task_daily_statistics = TaskDailyStatistics.query.filter(
                TaskDailyStatistics.location_id == location_id,
                TaskDailyStatistics.calendar_day == target_calendar_day.id
            ).first()
        else:
            task_statistics = None
            task_daily_statistics = None

        excuse_date_filter = func.date(StudentExcuses.added_date) == date_obj

    # Get records efficiently
    records = []
    if students:
        student_ids = [s.id for s in students]
        records = db.session.query(StudentExcuses).filter(
            StudentExcuses.student_id.in_(student_ids),
            excuse_date_filter
        ).all()

    return jsonify({
        # "students": iterate_models(students),
        "task_statistics": task_statistics.convert_json() if task_statistics else None,
        "task_daily_statistics": task_daily_statistics.convert_json() if task_daily_statistics else None,
        "table": True,
        "records": iterate_models(records)
    }), 200



@task_debts.route('/get_phones/<int:student_id>/')
def get_phones(student_id):
    student = Students.query.filter(Students.id == student_id).first()
    phones = PhoneList.query.filter(PhoneList.user_id == student.user_id).all()
    if not student:
        return jsonify({"error": "Student not found"}), 404

    return jsonify({"phones": iterate_models(phones)}), 200


@task_debts.route('/call_to_debt', methods=["POST"])
@jwt_required()
def call_to_debt():
    """
    Initiate a call to a student about their debt

    Request body:
        {
            "id": 123,
            "phone": "998901234567"
        }

    Returns:
        {
            "message": "Call processing started",
            "task_id": "task-uuid",
            "status": "processing",
            "student_id": 123
        }
    """
    data = request.get_json()
    student_id = data.get('student_id')
    phone = data.get('phone')
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    task_type = Tasks.query.filter(Tasks.name == 'excuses').first()
    identity = get_jwt_identity()
    user = Users.query.filter(Users.user_id == identity).first()
    # Validate input
    if not student_id:
        return jsonify({"error": "Student ID is required"}), 400

    if not phone:
        return jsonify({"error": "Phone number is required"}), 400

    # Verify student exists
    student = Students.query.filter(Students.id == student_id).first()
    if not student:
        return jsonify({"error": "Student not found"}), 404
    if not user.crm_username:
        return jsonify({"error": "CRM username is required"}), 400
    else:
        if user.crm_username not in ['gennis_center', 'gennis_chirchiq', 'gennis_chorvoq', 'gennis_gazalkent',
                                     'gennis_nurafshon', 'admin']:
            return jsonify({"error": "CRM username is invalid"}), 400
    task_statistics = TasksStatistics.query.filter(
        TasksStatistics.calendar_day == calendar_day.id,
        TasksStatistics.task_id == task_type.id,
        TasksStatistics.location_id == user.location_id
    ).first()
    # Queue the call task
    task = process_student_call.delay(student_id, phone, task_statistics.id, user.crm_username)

    return jsonify({
        "message": "Call processing started",
        "task_id": task.id,
        "status": "processing",
        "student_id": student_id
    }), 202


@task_debts.route('/call-status/<task_id>', methods=["GET"])
def check_student_call_status(task_id):
    """
    Check the status of a student call task

    Args:
        task_id: Celery task ID

    Returns:
        {
            "state": "SUCCESS|PENDING|FAILURE",
            "result": {...},
            "student_id": 123
        }
    """
    from backend.celery.debt_calls import process_student_call

    task = process_student_call.AsyncResult(task_id)

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


@task_debts.route(f'/call_to_debts', methods=["POST"])
@jwt_required()
def call_to_debts():
    try:
        calendar_year, calendar_month, calendar_day = find_calendar_date()

        # Setup timezone
        local_tz = pytz.timezone("Asia/Tashkent")
        calendar_dt = datetime.datetime.combine(calendar_day.date, datetime.time.min)
        calendar_dt = local_tz.localize(calendar_dt)

        # Get and validate request data
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        reason = data.get('comment')
        to_date_str = data.get('date')
        excuse_id = data.get('excuse_id')

        if not excuse_id:
            return jsonify({"error": "Excuse ID is required"}), 400

        # Fetch all required data in optimized queries
        task_type = Tasks.query.filter(Tasks.name == 'excuses').first()
        if not task_type:
            return jsonify({"error": "Excuses task not found"}), 404

        # Get student excuse with student and user in one query
        audio = StudentExcusesAudio.query.filter(
            StudentExcusesAudio.id == excuse_id
        ).first()
        student_excuse = db.session.query(StudentExcuses).options(
            joinedload(StudentExcuses.student).joinedload(Students.user)
        ).filter(StudentExcuses.id == audio.student_excuse_id).first()

        if not student_excuse:
            return jsonify({"error": "Student excuse not found"}), 404

        student = Students.query.filter(Students.id == student_excuse.student_id).first()
        location_id = student.user.location_id
        # Get task statistics
        task_statistics = TasksStatistics.query.filter(
            TasksStatistics.calendar_day == calendar_day.id,
            TasksStatistics.task_id == task_type.id,
            TasksStatistics.location_id == location_id
        ).first()

        if not task_statistics:
            return jsonify({"error": "Task statistics not found"}), 404

        # Parse to_date
        if to_date_str:
            to_date = datetime.datetime.strptime(to_date_str, "%Y-%m-%d")
            to_date = local_tz.localize(datetime.datetime.combine(to_date.date(), datetime.time.min))
        else:
            to_date = calendar_dt + datetime.timedelta(days=1)
        # Get all task students for this student (including duplicates)
        task_students = TaskStudents.query.filter(
            TaskStudents.task_id == task_type.id,
            TaskStudents.tasksstatistics_id == task_statistics.id,
            TaskStudents.student_id == student.id,
            TaskStudents.calendar_day == calendar_day.id
        ).order_by(TaskStudents.id).all()

        if not task_students:
            return jsonify({"error": "Task student not found"}), 404

        # Keep first, delete others (remove duplicates)
        task_student = task_students[0]
        if len(task_students) > 1:
            for duplicate in task_students[1:]:
                db.session.delete(duplicate)
        print("task_student", task_student.id)
        print("student_id", task_student.student_id)
        # Process excuse if future date
        if to_date > calendar_dt:
            # Check for existing excuse

            student_excuse.reason = reason
            student_excuse.to_date = to_date.date()

            # Mark task as completed
            task_student.status = True

        # Commit all changes at once
        db.session.commit()

        # Update statistics
        students, updated_task_statistics = update_debt_progress(location_id)
        task_daily_statistics = update_all_ratings(location_id)

        return jsonify({
            "status": "success",
            "message": "Ma'lumot muvaffaqiyatli kiritildi",
            "student_id": student.id,
            "task_student": task_student.convert_json(),
            "task_statistics": updated_task_statistics.convert_json(),
            "task_daily_statistics": task_daily_statistics.convert_json()
        }), 200

    except ValueError as e:
        db.session.rollback()
        return jsonify({"error": f"Invalid date format: {str(e)}"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@task_debts.route(f'/add_blacklist/<int:user_id>', methods=["GET", "POST"])
@jwt_required()
def add_blacklist2(user_id):
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


# @app.route(f'{api}/get_comment/<int:user_id>/<type_comment>', methods=["GET", "POST"])
@task_debts.route(f'/get_comment/<int:user_id>/<type_comment>', methods=["GET", "POST"])
@jwt_required()
def get_comment(user_id, type_comment):
    student = Students.query.filter(Students.user_id == user_id).first()
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    if type_comment == "debtors":
        task = Tasks.query.filter(Tasks.role == "admin", Tasks.name == "excuses").first()
        task_student = TaskStudents.query.filter(
            TaskStudents.task_id == task.id,
            TaskStudents.student_id == student.id,
            TaskStudents.calendar_day == calendar_day.id,
        ).first()
        task_students = TaskStudents.query.filter(
            TaskStudents.task_id == task.id,
            TaskStudents.student_id == student.id,
            TaskStudents.calendar_day == calendar_day.id,
        ).all()
        return jsonify({
            "comments": iterate_models(StudentExcuses.query.filter(StudentExcuses.student_id == student.id).order_by(
                desc(StudentExcuses.id)).all()),
            "info": Students.query.filter(Students.user_id == user_id).first().convert_json(),
            "task_student": task_student.convert_json(),
            "task_students": iterate_models(task_students)
        })
    elif type_comment == "newStudents":
        return jsonify({
            "comments": iterate_models(
                StudentCallingInfo.query.filter(StudentCallingInfo.student_id == student.id).order_by(
                    desc(StudentCallingInfo.id)).all()),
            "info": Students.query.filter(Students.user_id == user_id).first().convert_json()
        })
    else:
        from backend.lead.models import LeadRecomended

        lead_ids = db.session.query(LeadRecomended.recommended_id).join(Lead, LeadRecomended.lead_id == Lead.id).filter(
            LeadRecomended.lead_id == user_id,
            Lead.deleted == False
        ).all()
        lead_ids = [l[0] for l in lead_ids]
        leads = Lead.query.filter(Lead.id.in_(lead_ids), Lead.deleted == False).all()

        return jsonify({
            "comments": iterate_models(
                LeadInfos.query.filter(LeadInfos.lead_id == user_id).order_by(desc(LeadInfos.id)).all()),
            "info": Lead.query.filter(Lead.id == user_id).first().convert_json(),
            "invitations": [lead.convert_json() for lead in leads]

        })


@task_debts.route(f'/debts_records/<int:student_id>', methods=["GET", "POST"])
def debts_records(student_id):
    student = Students.query.filter(Students.id == student_id).first()
    return jsonify({
        "comments": iterate_models(
            StudentExcuses.query.filter(StudentExcuses.student_id == student.id).order_by(
                desc(StudentExcuses.id)).all(), entire=True),
        "info": Students.query.filter(Students.id == student_id).first().convert_json()
    })
