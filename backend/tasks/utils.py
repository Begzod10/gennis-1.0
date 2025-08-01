from app import app, db, jsonify, request
from backend.models.models import Users, Students, or_, BlackStudentsStatistics, BlackStudents, CalendarDay, \
    CalendarMonth, CalendarYear, \
    StudentExcuses, TaskStudents, TasksStatistics, Tasks, TaskDailyStatistics, StudentCallingInfo, Lead, LeadInfos, \
    AccountPayableHistory, TaskRatingsMonthly, TaskRatings
from sqlalchemy import asc, desc
from backend.functions.utils import find_calendar_date, refreshdatas

from sqlalchemy.orm import aliased
from sqlalchemy.sql import func, and_, or_


def black_students_count(calendar_month, calendar_year, location_id):
    black_student_statistics = BlackStudentsStatistics.query.filter(
        BlackStudentsStatistics.calendar_month == calendar_month,
        BlackStudentsStatistics.calendar_year == calendar_year,
        BlackStudentsStatistics.location_id == location_id).first()
    if not black_student_statistics:
        black_student_statistics = BlackStudentsStatistics(total_black_students=1,
                                                           calendar_month=calendar_month,
                                                           calendar_year=calendar_year,
                                                           location_id=location_id)
        db.session.add(black_student_statistics)
        db.session.commit()
    black_students = BlackStudents.query.filter(BlackStudents.calendar_year == calendar_year,
                                                BlackStudents.calendar_month == calendar_month,
                                                BlackStudents.location_id == location_id,
                                                BlackStudents.deleted == False
                                                ).all()
    black_student_statistics.total_black_students = len(black_students)
    db.session.commit()


def filter_new_leads(location_id):
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    task_type = Tasks.query.filter(Tasks.name == 'leads').first()

    task_statistics = TasksStatistics.query.filter(
        TasksStatistics.task_id == task_type.id,
        TasksStatistics.calendar_day == calendar_day.id,
        TasksStatistics.location_id == location_id
    ).first()
    if not task_statistics:
        task_statistics = TasksStatistics(task_id=task_type.id, calendar_year=calendar_year.id,
                                          calendar_month=calendar_month.id, calendar_day=calendar_day.id,
                                          location_id=location_id, in_progress_tasks=0,
                                          total_tasks=0)
        db.session.add(task_statistics)
        db.session.commit()
    completed = db.session.query(Lead).join(Lead.infos).filter(Lead.deleted == False,
                                                               Lead.location_id == location_id,
                                                               LeadInfos.added_date == calendar_day.date).all()
    latest_excuses_subquery = (
        db.session.query(
            LeadInfos.lead_id.label("lead_id"),
            func.max(LeadInfos.day).label("latest_to_date"),
        )
        .group_by(LeadInfos.lead_id)
        .subquery()  # Use `.subquery()` to make it a valid SQL table
    )

    # Alias the subquery
    latest_excuses_alias = aliased(latest_excuses_subquery)

    leads = db.session.query(Lead).filter(Lead.deleted == False,
                                          Lead.location_id == location_id).outerjoin(
        latest_excuses_alias,
        latest_excuses_alias.c.lead_id == Lead.id,  # Match subquery results with Students table
    ).outerjoin(
        LeadInfos,
        and_(
            LeadInfos.lead_id == Lead.id,
            LeadInfos.day == latest_excuses_alias.c.latest_to_date,  # Match the latest excuse
        ),
    ).filter(or_(LeadInfos.day <= calendar_day.date, LeadInfos.id == None)).order_by(
        desc(Lead.id)).all()
    task_statistics.completed_tasks = len(completed)
    task_statistics.in_progress_tasks = len(leads)
    task_statistics.total_tasks = len(leads) + len(completed)
    if len(completed) != 0:
        task_statistics.completed_tasks_percentage = (len(completed) / task_statistics.total_tasks) * 100
    db.session.commit()
    update_task_statistics_monthly(task_type, location_id)
    return leads, task_statistics, completed


def filter_new_students(location_id):
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    latest_excuses_subquery = (
        db.session.query(
            StudentCallingInfo.student_id.label("student_id"),
            func.max(StudentCallingInfo.date).label("latest_to_date"),
        )
        .group_by(StudentCallingInfo.student_id)
        .subquery()  # Use `.subquery()` to make it a valid SQL table
    )

    # Alias the subquery
    latest_excuses_alias = aliased(latest_excuses_subquery)

    students = db.session.query(Students).join(Students.user).filter(Users.location_id == location_id,
                                                                     Users.student != None,
                                                                     Students.subject != None,
                                                                     Students.deleted_from_register == None).outerjoin(
        latest_excuses_alias,
        latest_excuses_alias.c.student_id == Students.id,  # Match subquery results with Students table
    ).outerjoin(
        StudentCallingInfo,
        and_(
            StudentCallingInfo.student_id == Students.id,
            StudentCallingInfo.date == latest_excuses_alias.c.latest_to_date,  # Match the latest excuse
        ),
    ).filter(or_(StudentCallingInfo.date <= calendar_day.date, StudentCallingInfo.id == None)).order_by(
        desc(Students.id)).all()

    # students = db.session.query(Students).join(Students.user).filter(Users.location_id == location_id,
    #                                                                  Users.student != None,
    #                                                                  Students.subject != None,
    #                                                                  Students.deleted_from_register == None).outerjoin(
    #     Students.student_calling_info).filter(
    #     or_(StudentCallingInfo.date <= calendar_day.date, StudentCallingInfo.id == None)).order_by(
    #     desc(Students.id)).all()
    task_type = Tasks.query.filter(Tasks.name == 'new_students').first()

    task_statistics = TasksStatistics.query.filter(
        TasksStatistics.task_id == task_type.id,
        TasksStatistics.calendar_day == calendar_day.id,
        TasksStatistics.location_id == location_id
    ).first()
    if not task_statistics:
        task_statistics = TasksStatistics(task_id=task_type.id, calendar_year=calendar_year.id,
                                          calendar_month=calendar_month.id, calendar_day=calendar_day.id,
                                          location_id=location_id, in_progress_tasks=0,
                                          total_tasks=0)
        db.session.add(task_statistics)
        db.session.commit()
    students_calling = db.session.query(Students).join(Students.user).join(Students.student_calling_info).filter(
        Users.location_id == location_id,
        StudentCallingInfo.day == calendar_day.date
    ).distinct().all()
    task_statistics.completed_tasks = len(students_calling)
    task_statistics.in_progress_tasks = len(students)
    task_statistics.total_tasks = len(students) + len(students_calling)
    if len(students_calling) != 0:
        task_statistics.completed_tasks_percentage = (len(students_calling) / task_statistics.total_tasks) * 100
        db.session.commit()
    update_task_statistics_monthly(task_type, location_id)
    return students, task_statistics, students_calling


def filter_debts(location_id):
    calendar_year, calendar_month, calendar_day = find_calendar_date()

    # Second Query: Get students filtered by the first query

    latest_excuses_subquery = (
        db.session.query(
            StudentExcuses.student_id.label("student_id"),
            func.max(StudentExcuses.to_date).label("latest_to_date"),
        )
        .group_by(StudentExcuses.student_id)
        .subquery()  # Use `.subquery()` to make it a valid SQL table
    )

    # Alias the subquery
    latest_excuses_alias = aliased(latest_excuses_subquery)

    # Main query
    students = (
        db.session.query(Students)
        .join(Users, Students.user_id == Users.id)
        .filter(
            Users.balance < 0,
            Users.location_id == location_id,
            Students.debtor != 4,
            Students.deleted_from_register == None,  # Include students with `deleted_from_register` as None
        )
        .outerjoin(
            latest_excuses_alias,
            latest_excuses_alias.c.student_id == Students.id,  # Match subquery results with Students table
        )
        .outerjoin(
            StudentExcuses,
            and_(
                StudentExcuses.student_id == Students.id,
                StudentExcuses.to_date == latest_excuses_alias.c.latest_to_date,  # Match the latest excuse
            ),
        )
        .filter(
            or_(
                StudentExcuses.to_date.is_(None),  # No `to_date` specified
                StudentExcuses.to_date <= calendar_day.date,  # Latest `to_date` is before the calendar day
            )
        )
        .order_by(asc(Users.balance))
        .limit(100)
        .all()
    )
    return students


def update_debt_progress(location_id):
    refreshdatas()
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    task = Tasks.query.filter(Tasks.role == "admin", Tasks.name == "excuses").first()

    task_statistics = TasksStatistics.query.filter(TasksStatistics.location_id == location_id,
                                                   TasksStatistics.calendar_day == calendar_day.id,
                                                   TasksStatistics.calendar_month == calendar_month.id,
                                                   TasksStatistics.calendar_year == calendar_year.id,
                                                   TasksStatistics.task_id == task.id).first()
    if not task_statistics:
        task_statistics = TasksStatistics(task_id=task.id, calendar_year=calendar_year.id,
                                          calendar_month=calendar_month.id, calendar_day=calendar_day.id,
                                          location_id=location_id, in_progress_tasks=0,
                                          total_tasks=0)
        db.session.add(task_statistics)
        db.session.commit()

    # task_students = TaskStudents.query.filter(TaskStudents.task_id == task.id,
    #                                           TaskStudents.tasksstatistics_id == task_statistics.id,
    #                                           TaskStudents.calendar_day == calendar_day.id,
    #                                           ).all()
    # for st in task_students:
    #     added_excuses = StudentExcuses.query.filter(
    #         StudentExcuses.added_date == calendar_day.date,
    #         StudentExcuses.student_id == st.student_id
    #     ).first()
    #     if added_excuses:
    #         db.session.delete(added_excuses)
    #         db.session.commit()
    #     db.session.delete(st)
    #     db.session.commit()

    task_student = TaskStudents.query.filter(TaskStudents.task_id == task.id,
                                             TaskStudents.tasksstatistics_id == task_statistics.id,
                                             TaskStudents.calendar_day == calendar_day.id,
                                             ).first()
    in_progress_tasks = TaskStudents.query.filter(TaskStudents.task_id == task.id,
                                                  TaskStudents.tasksstatistics_id == task_statistics.id,
                                                  TaskStudents.status == False,
                                                  TaskStudents.calendar_day == calendar_day.id).join(
        TaskStudents.student).filter(Students.debtor != 4, Students.debtor != 0).all()

    if task_student:
        students = Students.query.filter(Students.id.in_([st.student_id for st in in_progress_tasks])).join(
            Students.students_tasks).filter(TaskStudents.status == False).all()
    else:

        students = filter_debts(location_id)

    if not task_student:
        for st in students:
            exist_task = TaskStudents.query.filter(TaskStudents.task_id == task.id,
                                                   TaskStudents.tasksstatistics_id == task_statistics.id,
                                                   TaskStudents.student_id == st.id,
                                                   TaskStudents.calendar_day == calendar_day.id).first()
            if not exist_task:
                add_task_student = TaskStudents(task_id=task.id, tasksstatistics_id=task_statistics.id,
                                                student_id=st.id, calendar_day=calendar_day.id)
                add_task_student.add()

    completed_students = (
        db.session.query(func.count(func.distinct(TaskStudents.student_id)))
        .filter(
            TaskStudents.task_id == task.id,
            TaskStudents.tasksstatistics_id == task_statistics.id,
            TaskStudents.status == True,
            TaskStudents.calendar_day == calendar_day.id
        )
        .join(TaskStudents.student)
        .filter(Students.debtor != 4)
        .scalar()
    )

    task_statistics.completed_tasks = completed_students
    task_statistics.in_progress_tasks = len(students)
    task_statistics.total_tasks = task_statistics.in_progress_tasks + task_statistics.completed_tasks
    if task_statistics.total_tasks != 0:
        task_statistics.completed_tasks_percentage = round(
            (task_statistics.completed_tasks / task_statistics.total_tasks) * 100)
    db.session.commit()
    update_task_statistics_monthly(task, location_id)
    return students, task_statistics


def update_all_ratings(location_id):
    calendar_year, calendar_month, calendar_day = find_calendar_date()

    overall_location_statistics = TasksStatistics.query.filter_by(
        # user_id=user.id,
        calendar_day=calendar_day.id,
        location_id=location_id
    ).all()
    completed_tasks = sum(stat.completed_tasks for stat in overall_location_statistics)
    total_tasks = sum(stat.total_tasks for stat in overall_location_statistics)
    tasks_daily_statistics = TaskDailyStatistics.query.filter_by(
        # user_id=user.id,
        location_id=location_id,
        calendar_day=calendar_day.id,
        calendar_month=calendar_month.id,
        calendar_year=calendar_year.id
    ).first()
    if not tasks_daily_statistics:
        tasks_daily_statistics = TaskDailyStatistics(
            calendar_day=calendar_day.id,
            location_id=location_id,
            calendar_month=calendar_month.id,
            calendar_year=calendar_year.id
        )
        db.session.add(tasks_daily_statistics)
        db.session.commit()
    tasks_daily_statistics.total_tasks = total_tasks
    db.session.commit()
    completed_tasks_percentage = round(
        (completed_tasks / tasks_daily_statistics.total_tasks) * 100) if completed_tasks else 0

    TaskDailyStatistics.query.filter_by(
        # user_id=user.id,
        location_id=location_id,
        calendar_day=calendar_day.id
    ).update({
        'completed_tasks': completed_tasks,
        'completed_tasks_percentage': completed_tasks_percentage,
        "in_progress_tasks": tasks_daily_statistics.total_tasks - completed_tasks
    })
    db.session.commit()
    task_rating_monthly = TaskRatingsMonthly.query.filter(
        TaskRatingsMonthly.calendar_year == calendar_year.id,
        TaskRatingsMonthly.calendar_month == calendar_month.id,
        TaskRatingsMonthly.location_id == location_id
    ).first()
    if not task_rating_monthly:
        task_rating_monthly = TaskRatingsMonthly(
            calendar_year=calendar_year.id,
            calendar_month=calendar_month.id,
            location_id=location_id
        )
        db.session.add(task_rating_monthly)
        db.session.commit()
    tasks_monthly_statistics = TaskDailyStatistics.query.filter_by(
        # user_id=user.id,
        location_id=location_id,
        calendar_month=calendar_month.id,
        calendar_year=calendar_year.id
    ).all()
    completed_tasks = sum(stat.completed_tasks for stat in tasks_monthly_statistics)
    total_tasks = sum(stat.total_tasks for stat in tasks_monthly_statistics)

    task_rating_monthly.completed_tasks = completed_tasks
    task_rating_monthly.in_progress_tasks = total_tasks - completed_tasks
    task_rating_monthly.total_tasks = total_tasks
    db.session.commit()
    if completed_tasks != 0:
        task_rating_monthly.completed_tasks_percentage = round(
            (task_rating_monthly.completed_tasks / task_rating_monthly.total_tasks) * 100)
    db.session.commit()
    return tasks_daily_statistics


def update_task_statistics_monthly(task_type, location_id):
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    task_lead = TaskRatings.query.filter(
        TaskRatings.task_id == task_type.id,
        TaskRatings.calendar_year == calendar_year.id,
        TaskRatings.calendar_month == calendar_month.id,
        TaskRatings.location_id == location_id
    ).first()
    if not task_lead:
        task_lead = TaskRatings(task_id=task_type.id, calendar_year=calendar_year.id,
                                calendar_month=calendar_month.id, location_id=location_id,
                                )
        task_lead.add()
    task_statistics_month = TasksStatistics.query.filter(
        TasksStatistics.task_id == task_type.id,
        TasksStatistics.calendar_year == calendar_year.id,
        TasksStatistics.calendar_month == calendar_month.id,
        TasksStatistics.location_id == location_id
    ).all()
    completed_tasks = sum(stat.completed_tasks for stat in task_statistics_month)
    total_tasks = sum(stat.total_tasks for stat in task_statistics_month)
    task_lead.completed_tasks = completed_tasks
    task_lead.in_progress_tasks = total_tasks - completed_tasks
    task_lead.total_tasks = total_tasks
    db.session.commit()
    if completed_tasks != 0:
        task_lead.completed_tasks_percentage = (completed_tasks / total_tasks) * 100
    db.session.commit()
