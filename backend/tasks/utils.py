from sqlalchemy import asc, desc
from sqlalchemy.orm import aliased, joinedload
from sqlalchemy.sql import func, and_, or_

from datetime import datetime
import pytz
from backend.functions.utils import find_calendar_date
from backend.models.models import (
    Users, Students, BlackStudentsStatistics, BlackStudents, StudentExcuses,
    TaskStudents, TasksStatistics, Tasks, TaskDailyStatistics, StudentCallingInfo,
    Lead, LeadInfos, TaskRatingsMonthly, TaskRatings, db
)


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


_calendar_cache = None
_cache_date = None


def get_cached_calendar_ids():
    """
    Cache calendar IDs but auto-clear when date changes.
    Returns IDs instead of objects to avoid DetachedInstanceError.
    """
    global _calendar_cache, _cache_date

    # Get current date in Tashkent timezone
    tz = pytz.timezone('Asia/Tashkent')
    today = datetime.now(tz).date()

    # If cache is empty OR date has changed, refresh
    if _calendar_cache is None or _cache_date != today:
        calendar_year, calendar_month, calendar_day = find_calendar_date()

        _calendar_cache = {
            'year_id': calendar_year.id,
            'month_id': calendar_month.id,
            'day_id': calendar_day.id,
            'date': calendar_day.date,
            'year_obj': calendar_year,
            'month_obj': calendar_month,
            'day_obj': calendar_day
        }
        _cache_date = today

    return _calendar_cache


def clear_calendar_cache():
    """Manually clear cache if needed"""
    global _calendar_cache, _cache_date
    _calendar_cache = None
    _cache_date = None


# ==================== FIXED: Update Debt Progress ====================
def update_debt_progress(location_id):
    """
    FIXED VERSION with proper session handling
    - Uses IDs instead of detached objects
    - All session operations are safe
    """

    # Get calendar IDs (not objects that can detach)
    calendar_year, calendar_month, calendar_day = find_calendar_date()

    # Get task
    task = Tasks.query.filter_by(role="admin", name="excuses").first()
    if not task:
        raise ValueError("Task 'excuses' not found")

    # Get or create task statistics
    task_statistics = TasksStatistics.query.filter_by(
        location_id=location_id,
        calendar_day=calendar_day.id,  # Use ID, not object
        calendar_month=calendar_month.id,
        calendar_year=calendar_year.id,
        task_id=task.id
    ).first()

    # Get students based on whether stats exist
    if task_statistics:
        # Query in-progress tasks with eager loading
        in_progress_tasks = (
            TaskStudents.query
            .options(joinedload(TaskStudents.student))
            .filter(
                TaskStudents.task_id == task.id,
                TaskStudents.tasksstatistics_id == task_statistics.id,
                TaskStudents.status == False,
                TaskStudents.calendar_day == calendar_day.id  # Use ID
            )
            .join(TaskStudents.student)
            .filter(
                Students.debtor.notin_([0, 4])
            )
            .distinct(TaskStudents.student_id)
            .all()
        )
        students = [ts.student for ts in in_progress_tasks]
    else:
        # Get debt students
        students = filter_debts(location_id)

        # Create new task statistics
        task_statistics = TasksStatistics(
            task_id=task.id,
            calendar_year=calendar_year.id,  # Use ID
            calendar_month=calendar_month.id,
            calendar_day=calendar_day.id,
            location_id=location_id,
            in_progress_tasks=0,
            total_tasks=0
        )
        db.session.add(task_statistics)
        db.session.flush()  # Get ID without full commit

        # Bulk check existing tasks (single query)
        existing_student_ids = {
            ts.student_id
            for ts in TaskStudents.query.filter_by(
                task_id=task.id,
                tasksstatistics_id=task_statistics.id,
                calendar_day=calendar_day.id  # Use ID
            ).with_entities(TaskStudents.student_id).all()
        }

        # Bulk insert new task students
        new_task_students = [
            TaskStudents(
                task_id=task.id,
                tasksstatistics_id=task_statistics.id,
                status=False,
                student_id=st.id,
                calendar_day=calendar_day.id  # Use ID
            )
            for st in students
            if st.id not in existing_student_ids
        ]

        if new_task_students:
            db.session.bulk_save_objects(new_task_students)

    # Count completed in single query
    completed_students_count = (
            db.session.query(func.count(func.distinct(TaskStudents.student_id)))
            .filter(
                TaskStudents.task_id == task.id,
                TaskStudents.tasksstatistics_id == task_statistics.id,
                TaskStudents.status == True,
                TaskStudents.calendar_day == calendar_day.id  # Use ID
            )
            .join(TaskStudents.student)
            .filter(Students.debtor != 4)
            .scalar() or 0
    )

    # Update statistics
    task_statistics.completed_tasks = completed_students_count
    task_statistics.in_progress_tasks = len(students)
    task_statistics.total_tasks = completed_students_count + len(students)

    # Safe percentage calculation
    if task_statistics.total_tasks > 0:
        task_statistics.completed_tasks_percentage = round(
            (completed_students_count / task_statistics.total_tasks) * 100
        )
    else:
        task_statistics.completed_tasks_percentage = 0

    # Single commit for all operations
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise

    # Update monthly stats
    update_task_statistics_monthly_fixed(task, location_id)

    return students, task_statistics


# ==================== FIXED: Filter Debts ====================
def filter_debts(location_id):
    """FIXED: Uses calendar IDs properly"""
    calendar_year, calendar_month, calendar_day = find_calendar_date()

    # Subquery for latest excuse
    latest_excuses_subquery = (
        db.session.query(
            StudentExcuses.student_id.label("student_id"),
            func.max(StudentExcuses.to_date).label("latest_to_date"),
        )
        .group_by(StudentExcuses.student_id)
        .subquery()
    )

    latest_excuses_alias = aliased(latest_excuses_subquery)

    # Main query with eager loading
    students = (
        db.session.query(Students)
        .join(Users, Students.user_id == Users.id)
        .options(joinedload(Students.user))
        .filter(
            Users.balance < 0,
            Users.location_id == location_id,
            Students.debtor != 4,
            Students.deleted_from_register == None
        )
        .outerjoin(
            latest_excuses_alias,
            latest_excuses_alias.c.student_id == Students.id
        )
        .outerjoin(
            StudentExcuses,
            and_(
                StudentExcuses.student_id == Students.id,
                StudentExcuses.to_date == latest_excuses_alias.c.latest_to_date
            )
        )
        .filter(
            or_(
                StudentExcuses.to_date.is_(None),
                StudentExcuses.to_date <= calendar_day.date  # Use date, not object
            )
        )
        .order_by(asc(Users.balance))
        .limit(100)
        .all()
    )

    return students


# ==================== FIXED: Filter New Leads ====================
def filter_new_leads(location_id):
    """FIXED: Uses calendar IDs properly"""
    calendar_year, calendar_month, calendar_day = find_calendar_date()

    # Get task type
    task_type = Tasks.query.filter(Tasks.name == 'leads').first()
    if not task_type:
        raise ValueError("Task type 'leads' not found")

    # Get or create task statistics
    task_statistics = TasksStatistics.query.filter(
        TasksStatistics.task_id == task_type.id,
        TasksStatistics.calendar_day == calendar_day.id,  # Use ID
        TasksStatistics.location_id == location_id
    ).first()

    if not task_statistics:
        task_statistics = TasksStatistics(
            task_id=task_type.id,
            calendar_year=calendar_year.id,
            calendar_month=calendar_month.id,
            calendar_day=calendar_day.id,
            location_id=location_id,
            in_progress_tasks=0,
            total_tasks=0
        )
        db.session.add(task_statistics)
        db.session.flush()

    # Query completed leads with eager loading
    completed = (
        db.session.query(Lead)
        .join(Lead.infos)
        .options(joinedload(Lead.infos))
        .filter(
            Lead.deleted == False,
            Lead.location_id == location_id,
            LeadInfos.added_date == calendar_day.date  # Use date
        )
        .all()
    )

    # Subquery for latest lead info
    latest_infos_subquery = (
        db.session.query(
            LeadInfos.lead_id.label("lead_id"),
            func.max(LeadInfos.day).label("latest_day"),
        )
        .group_by(LeadInfos.lead_id)
        .subquery()
    )

    latest_infos_alias = aliased(latest_infos_subquery)

    # Query in-progress leads
    leads = (
        db.session.query(Lead)
        .filter(
            Lead.deleted == False,
            Lead.location_id == location_id
        )
        .outerjoin(
            latest_infos_alias,
            latest_infos_alias.c.lead_id == Lead.id
        )
        .outerjoin(
            LeadInfos,
            and_(
                LeadInfos.lead_id == Lead.id,
                LeadInfos.day == latest_infos_alias.c.latest_day
            )
        )
        .filter(
            or_(
                LeadInfos.day <= calendar_day.date,  # Use date
                LeadInfos.id == None
            )
        )
        .order_by(desc(Lead.id))
        .all()
    )

    # Update statistics
    completed_count = len(completed)
    in_progress_count = len(leads)
    total_count = completed_count + in_progress_count

    task_statistics.completed_tasks = completed_count
    task_statistics.in_progress_tasks = in_progress_count
    task_statistics.total_tasks = total_count

    if total_count > 0:
        task_statistics.completed_tasks_percentage = round(
            (completed_count / total_count) * 100, 2
        )
    else:
        task_statistics.completed_tasks_percentage = 0

    db.session.commit()

    update_task_statistics_monthly_fixed(task_type, location_id)

    return leads, task_statistics, completed


# ==================== FIXED: Filter New Students ====================
def filter_new_students(location_id):
    """FIXED: Uses calendar IDs properly"""
    calendar_year, calendar_month, calendar_day = find_calendar_date()

    # Subquery for latest calling info
    latest_calling_subquery = (
        db.session.query(
            StudentCallingInfo.student_id.label("student_id"),
            func.max(StudentCallingInfo.date).label("latest_date"),
        )
        .group_by(StudentCallingInfo.student_id)
        .subquery()
    )

    latest_calling_alias = aliased(latest_calling_subquery)

    # Query students with eager loading
    students = (
        db.session.query(Students)
        .join(Students.user)
        .options(joinedload(Students.user))
        .filter(
            Users.location_id == location_id,
            Users.student != None,
            Students.subject != None,
            Students.deleted_from_register == None
        )
        .outerjoin(
            latest_calling_alias,
            latest_calling_alias.c.student_id == Students.id
        )
        .outerjoin(
            StudentCallingInfo,
            and_(
                StudentCallingInfo.student_id == Students.id,
                StudentCallingInfo.date == latest_calling_alias.c.latest_date
            )
        )
        .filter(
            or_(
                StudentCallingInfo.date <= calendar_day.date,  # Use date
                StudentCallingInfo.id == None
            )
        )
        .order_by(desc(Students.id))
        .all()
    )

    # Get task type
    task_type = Tasks.query.filter(Tasks.name == 'new_students').first()
    if not task_type:
        raise ValueError("Task type 'new_students' not found")

    # Get or create task statistics
    task_statistics = TasksStatistics.query.filter(
        TasksStatistics.task_id == task_type.id,
        TasksStatistics.calendar_day == calendar_day.id,  # Use ID
        TasksStatistics.location_id == location_id
    ).first()

    if not task_statistics:
        task_statistics = TasksStatistics(
            task_id=task_type.id,
            calendar_year=calendar_year.id,
            calendar_month=calendar_month.id,
            calendar_day=calendar_day.id,
            location_id=location_id,
            in_progress_tasks=0,
            total_tasks=0
        )
        db.session.add(task_statistics)
        db.session.flush()

    # Query students who were called today
    students_calling = (
        db.session.query(Students)
        .join(Students.user)
        .join(Students.student_calling_info)
        .options(joinedload(Students.user))
        .filter(
            Users.location_id == location_id,
            StudentCallingInfo.day == calendar_day.date  # Use date
        )
        .distinct()
        .all()
    )

    # Update statistics
    completed_count = len(students_calling)
    in_progress_count = len(students)
    total_count = completed_count + in_progress_count

    task_statistics.completed_tasks = completed_count
    task_statistics.in_progress_tasks = in_progress_count
    task_statistics.total_tasks = total_count

    if total_count > 0:
        task_statistics.completed_tasks_percentage = round(
            (completed_count / total_count) * 100, 2
        )
    else:
        task_statistics.completed_tasks_percentage = 0

    db.session.commit()

    update_task_statistics_monthly_fixed(task_type, location_id)

    return students, task_statistics, students_calling


# ==================== FIXED: Update Task Statistics Monthly ====================
def update_task_statistics_monthly_fixed(task_type, location_id):
    """FIXED: Uses calendar IDs properly"""
    calendar_year, calendar_month, calendar_day = find_calendar_date()

    # Get or create task rating
    task_lead = TaskRatings.query.filter(
        TaskRatings.task_id == task_type.id,
        TaskRatings.calendar_year == calendar_year.id,  # Use ID
        TaskRatings.calendar_month == calendar_month.id,
        TaskRatings.location_id == location_id
    ).first()

    if not task_lead:
        task_lead = TaskRatings(
            task_id=task_type.id,
            calendar_year=calendar_year.id,
            calendar_month=calendar_month.id,
            location_id=location_id
        )
        db.session.add(task_lead)
        db.session.flush()

    # Aggregate in database
    monthly_totals = (
        db.session.query(
            func.sum(TasksStatistics.completed_tasks).label('completed'),
            func.sum(TasksStatistics.total_tasks).label('total')
        )
        .filter(
            TasksStatistics.task_id == task_type.id,
            TasksStatistics.calendar_year == calendar_year.id,  # Use ID
            TasksStatistics.calendar_month == calendar_month.id,
            TasksStatistics.location_id == location_id
        )
        .first()
    )

    completed_tasks = monthly_totals.completed or 0
    total_tasks = monthly_totals.total or 0

    # Update statistics
    task_lead.completed_tasks = completed_tasks
    task_lead.total_tasks = total_tasks
    task_lead.in_progress_tasks = total_tasks - completed_tasks

    if total_tasks > 0:
        task_lead.completed_tasks_percentage = round(
            (completed_tasks / total_tasks) * 100, 2
        )
    else:
        task_lead.completed_tasks_percentage = 0

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise


# ==================== FIXED: Update All Ratings ====================
def update_all_ratings(location_id):
    """FIXED: Uses calendar IDs properly"""
    calendar_year, calendar_month, calendar_day = find_calendar_date()

    # Aggregate in database using SQL
    daily_totals = (
        db.session.query(
            func.sum(TasksStatistics.completed_tasks).label('completed'),
            func.sum(TasksStatistics.total_tasks).label('total')
        )
        .filter(
            TasksStatistics.calendar_day == calendar_day.id,  # Use ID
            TasksStatistics.location_id == location_id
        )
        .first()
    )

    completed_tasks = daily_totals.completed or 0
    total_tasks = daily_totals.total or 0

    # Get or create daily statistics
    tasks_daily_statistics = TaskDailyStatistics.query.filter_by(
        location_id=location_id,
        calendar_day=calendar_day.id,  # Use ID
        calendar_month=calendar_month.id,
        calendar_year=calendar_year.id
    ).first()

    if not tasks_daily_statistics:
        tasks_daily_statistics = TaskDailyStatistics(
            calendar_day=calendar_day.id,
            location_id=location_id,
            calendar_month=calendar_month.id,
            calendar_year=calendar_year.id,
            total_tasks=total_tasks
        )
        db.session.add(tasks_daily_statistics)
    else:
        tasks_daily_statistics.total_tasks = total_tasks

    # Calculate percentage
    completed_tasks_percentage = round(
        (completed_tasks / total_tasks) * 100, 2
    ) if total_tasks > 0 else 0

    # Update statistics
    tasks_daily_statistics.completed_tasks = completed_tasks
    tasks_daily_statistics.completed_tasks_percentage = completed_tasks_percentage
    tasks_daily_statistics.in_progress_tasks = total_tasks - completed_tasks

    # Get or create monthly rating
    task_rating_monthly = TaskRatingsMonthly.query.filter(
        TaskRatingsMonthly.calendar_year == calendar_year.id,  # Use ID
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

    # Aggregate monthly data in database
    monthly_totals = (
        db.session.query(
            func.sum(TaskDailyStatistics.completed_tasks).label('completed'),
            func.sum(TaskDailyStatistics.total_tasks).label('total')
        )
        .filter(
            TaskDailyStatistics.location_id == location_id,
            TaskDailyStatistics.calendar_month == calendar_month.id,  # Use ID
            TaskDailyStatistics.calendar_year == calendar_year.id
        )
        .first()
    )

    monthly_completed = monthly_totals.completed or 0
    monthly_total = monthly_totals.total or 0

    # Update monthly statistics
    task_rating_monthly.completed_tasks = monthly_completed
    task_rating_monthly.total_tasks = monthly_total
    task_rating_monthly.in_progress_tasks = monthly_total - monthly_completed

    if monthly_total > 0:
        task_rating_monthly.completed_tasks_percentage = round(
            (monthly_completed / monthly_total) * 100, 2
        )
    else:
        task_rating_monthly.completed_tasks_percentage = 0

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise

    return tasks_daily_statistics
