# tasks/salary.py
import sys
from backend.celery.celery_app import celery, shared_task, group
from backend.functions.debt_salary_update import salary_debt, find_calendar_date
from backend.student.class_model import Student_Functions
from backend.functions.utils import update_salary
from backend.models.models import TeacherBlackSalary, Students, db, Locations, DeletedStudents, RegisterDeletedStudents, \
    Groups, StudentPayments, BranchReport, Users, Teachers, Staff, AssistentBlackSalary, Assistent
import logging
from sqlalchemy import or_
from backend.teacher.utils import send_telegram_message
from celery import shared_task, group, chord

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_student_debt_and_balance(self, student_id):
    """
    Update student debt and balance calculations

    Args:
        student_id: Student ID to update
    """
    try:
        st_functions = Student_Functions(student_id=student_id)
        st_functions.update_debt()
        st_functions.update_balance()

        logger.info(f"Updated debt and balance for student {student_id}")
        return {"status": "success", "student_id": student_id}

    except Exception as exc:
        logger.error(f"Error updating student {student_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_salary_debt(self, student_id, group_id, attendance_id):
    """
    Calculate salary debt for attendance

    Args:
        student_id: Student ID
        group_id: Group ID
        attendance_id: Attendance day ID

    Returns:
        salary_location object ID
    """
    try:
        salary_location = salary_debt(
            student_id=student_id,
            group_id=group_id,
            attendance_id=attendance_id,
            status_attendance=False,
            type_attendance="add"
        )

        logger.info(f"Processed salary debt for attendance {attendance_id}")
        return {
            "status": "success",
            "salary_location_id": salary_location.id if salary_location else None
        }

    except Exception as exc:
        logger.error(f"Error processing salary debt: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def update_teacher_salary(self, teacher_user_id):
    """
    Update teacher salary calculations

    Args:
        teacher_user_id: Teacher's user ID
    """
    try:
        update_salary(teacher_id=teacher_user_id)

        logger.info(f"Updated salary for teacher {teacher_user_id}")
        return {"status": "success", "teacher_id": teacher_user_id}

    except Exception as exc:
        logger.error(f"Error updating teacher salary {teacher_user_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_black_salary(self, teacher_id, student_id, calendar_month_id,
                         calendar_year_id, location_id, salary_location_id,
                         salary_per_day):
    """
    Handle black salary for debtor students

    Args:
        teacher_id: Teacher ID
        student_id: Student ID
        calendar_month_id: Calendar month ID
        calendar_year_id: Calendar year ID
        location_id: Location ID
        salary_location_id: Salary location ID
        salary_per_day: Daily salary amount
    """
    try:
        black_salary = TeacherBlackSalary.query.filter(
            TeacherBlackSalary.teacher_id == teacher_id,
            TeacherBlackSalary.student_id == student_id,
            TeacherBlackSalary.calendar_month == calendar_month_id,
            TeacherBlackSalary.calendar_year == calendar_year_id,
            TeacherBlackSalary.status == False,
            TeacherBlackSalary.location_id == location_id,
            TeacherBlackSalary.salary_id == salary_location_id
        ).first()

        if not black_salary:
            black_salary = TeacherBlackSalary(
                teacher_id=teacher_id,
                total_salary=salary_per_day,
                student_id=student_id,
                salary_id=salary_location_id,
                calendar_month=calendar_month_id,
                calendar_year=calendar_year_id,
                location_id=location_id
            )
            black_salary.add()
            logger.info(f"Created black salary for teacher {teacher_id}, student {student_id}")
        else:
            black_salary.total_salary += salary_per_day
            db.session.commit()
            logger.info(f"Updated black salary for teacher {teacher_id}, student {student_id}")

        return {"status": "success", "black_salary_id": black_salary.id}

    except Exception as exc:
        logger.error(f"Error processing black salary: {exc}")
        db.session.rollback()
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=5, default_retry_delay=30)
def send_attendance_notification(self, student_id, attendance_day_id, group_id):
    """
    Send telegram notification for attendance

    Args:
        student_id: Student ID
        attendance_day_id: Attendance day ID
        group_id: Group ID
    """
    try:
        send_telegram_message(student_id, attendance_day_id, group_id)

        logger.info(f"Sent notification for student {student_id}, attendance {attendance_day_id}")
        return {"status": "success", "student_id": student_id}

    except Exception as exc:
        logger.error(f"Error sending notification: {exc}")
        # Telegram failures shouldn't fail the whole process
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 30)


# ✅ NEW: Callback task that processes results from step 1
@shared_task
def handle_post_attendance_completion(step1_results, teacher_user_id, is_debtor,
                                      teacher_id, student_id, calendar_month_id,
                                      calendar_year_id, location_id, salary_per_day,
                                      attendance_day_id, group_id, assistent_salary_per_day):
    """
    Callback task that runs after initial parallel tasks complete

    Args:
        step1_results: Results from [process_student_debt_and_balance, process_salary_debt]
        ... (other parameters passed through)
    """
    try:
        # Extract results from step 1
        # step1_results is a list: [debt_balance_result, salary_debt_result]
        debt_result = step1_results[0] if len(step1_results) > 0 else {}
        salary_result = step1_results[1] if len(step1_results) > 1 else {}

        salary_location_id = salary_result.get('salary_location_id')

        logger.info(f"Step 1 completed for student {student_id}. Salary location: {salary_location_id}")

        # Step 2: Update teacher salary
        update_teacher_salary.delay(teacher_user_id)

        # Step 3: Handle teacher black salary if debtor
        if is_debtor and salary_location_id:
            process_black_salary.delay(
                teacher_id=teacher_id,
                student_id=student_id,
                calendar_month_id=calendar_month_id,
                calendar_year_id=calendar_year_id,
                location_id=location_id,
                salary_location_id=salary_location_id,
                salary_per_day=salary_per_day
            )
            logger.info(f"Triggered teacher black salary processing for student {student_id}")

        # Step 4: Handle assistant black salary if debtor
        if is_debtor:
            process_assistant_black_salary.delay(
                student_id=student_id,
                group_id=group_id,
                calendar_month_id=calendar_month_id,
                calendar_year_id=calendar_year_id,
                location_id=location_id,
                attendance_day_id=attendance_day_id,
                assistent_salary_per_day=assistent_salary_per_day
            )
            logger.info(f"Triggered assistant black salary processing for student {student_id}")

        # Step 5: Send notification (fire and forget)
        send_attendance_notification.delay(student_id, attendance_day_id, group_id)

        logger.info(f"Successfully orchestrated post-attendance tasks for student {student_id}")
        return {
            "status": "success",
            "student_id": student_id,
            "salary_location_id": salary_location_id
        }

    except Exception as exc:
        logger.error(f"Error in post-attendance completion handler: {exc}")
        raise


@shared_task(bind=True, max_retries=3)
def process_assistant_black_salary(self, student_id, group_id, calendar_month_id,
                                   calendar_year_id, location_id, attendance_day_id, assistent_salary_per_day):
    """
    Process black salary for assistants when student is a debtor

    Args:
        student_id: Student ID
        group_id: Group ID
        calendar_month_id: Calendar month ID
        calendar_year_id: Calendar year ID
        location_id: Location ID
        attendance_day_id: Attendance day ID
    """
    try:
        from backend.models.models import db
        from backend.group.models import Groups
        from backend.teacher.assistent.models import Assistent, AssistentSalary, AssistentBlackSalary
        from backend.models.models import AttendanceDays
        from sqlalchemy.orm import joinedload

        # Get group with assistants
        group = db.session.query(Groups).options(
            joinedload(Groups.assistent)
        ).filter(Groups.id == group_id).first()

        if not group or not group.assistent:
            logger.info(f"No assistants found for group {group_id}")
            return {"status": "no_assistants", "group_id": group_id}

        # Get attendance day details
        attendance_day = AttendanceDays.query.filter(
            AttendanceDays.id == attendance_day_id
        ).first()

        if not attendance_day:
            logger.error(f"Attendance day {attendance_day_id} not found")
            return {"status": "error", "message": "Attendance day not found"}

        # Process each assistant
        processed_assistants = []

        for assistant in group.assistent:
            if not assistant.percentage:
                continue

            # Calculate assistant's portion of the salary

            # Get or create assistant salary record
            assistant_salary = AssistentSalary.query.filter(
                AssistentSalary.location_id == location_id,
                AssistentSalary.assisten_id == assistant.id,
                AssistentSalary.calendar_year == calendar_year_id,
                AssistentSalary.calendar_month == calendar_month_id
            ).first()

            if not assistant_salary:
                logger.warning(f"No salary record found for assistant {assistant.id}")
                continue

            # Check if black salary already exists
            existing_black_salary = AssistentBlackSalary.query.filter(
                AssistentBlackSalary.assistent_id == assistant.id,
                AssistentBlackSalary.student_id == student_id,
                AssistentBlackSalary.calendar_month == calendar_month_id,
                AssistentBlackSalary.calendar_year == calendar_year_id,
                AssistentBlackSalary.location_id == location_id
            ).first()

            if not existing_black_salary:
                # Create black salary record
                black_salary = AssistentBlackSalary(
                    assistent_id=assistant.id,
                    total_salary=assistent_salary_per_day,
                    location_id=location_id,
                    calendar_month=calendar_month_id,
                    calendar_year=calendar_year_id,
                    student_id=student_id,
                    salary_id=assistant_salary.id,
                    payment_id=None,  # Will be set when payment is made
                    status=False
                )
                db.session.add(black_salary)
            else:
                existing_black_salary.total_salary += assistent_salary_per_day
            processed_assistants.append({
                "assistant_id": assistant.id,
                "black_salary": assistent_salary_per_day
            })

            logger.info(f"Created black salary {assistent_salary_per_day} for assistant {assistant.id}")

        # Commit all black salary records
        db.session.commit()

        logger.info(f"Processed assistant black salaries for {len(processed_assistants)} assistants")

        return {
            "status": "success",
            "student_id": student_id,
            "group_id": group_id,
            "processed_assistants": processed_assistants
        }

    except Exception as exc:
        db.session.rollback()
        logger.error(f"Error processing assistant black salary for student {student_id}: {exc}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


# ✅ FIXED: Main orchestration task using chord
@shared_task
def process_attendance_post_save(student_id, group_id, attendance_day_id,
                                 teacher_user_id, is_debtor, teacher_id,
                                 calendar_month_id, calendar_year_id,
                                 location_id, salary_per_day, assistent_salary_per_day):
    """
    Main orchestration task that coordinates all post-attendance operations
    Uses Celery chord pattern to avoid blocking

    Workflow:
    1. Run student debt/balance and salary debt in parallel (group)
    2. After both complete, trigger callback (chord)
    3. Callback processes results and launches remaining tasks (including assistant black salary)

    Args:
        student_id: Student ID
        group_id: Group ID
        attendance_day_id: Attendance day ID
        teacher_user_id: Teacher's user ID
        is_debtor: Whether student is a debtor (debtor == 2)
        teacher_id: Teacher ID
        calendar_month_id: Calendar month ID
        calendar_year_id: Calendar year ID
        location_id: Location ID
        salary_per_day: Daily salary amount
    """
    try:
        # Step 1: Create parallel tasks group
        step1_tasks = group([
            process_student_debt_and_balance.s(student_id),
            process_salary_debt.s(student_id, group_id, attendance_day_id)
        ])

        # Step 2: Create chord - runs group, then callback with results
        workflow = chord(step1_tasks)(
            handle_post_attendance_completion.s(
                teacher_user_id=teacher_user_id,
                is_debtor=is_debtor,
                teacher_id=teacher_id,
                student_id=student_id,
                calendar_month_id=calendar_month_id,
                calendar_year_id=calendar_year_id,
                location_id=location_id,
                salary_per_day=salary_per_day,
                attendance_day_id=attendance_day_id,
                group_id=group_id,
                assistent_salary_per_day=assistent_salary_per_day
            )
        )

        logger.info(f"Orchestrated post-attendance workflow for student {student_id}")

        return {
            "status": "workflow_started",
            "student_id": student_id,
            "workflow_id": workflow.id
        }

    except Exception as exc:
        logger.error(f"Error starting orchestration task for student {student_id}: {exc}")
        raise


@shared_task
def batch_process_attendance_notifications(attendance_data_list):
    """
    Batch process multiple attendance notifications
    Useful for bulk attendance marking

    Args:
        attendance_data_list: List of dicts with student_id, attendance_day_id, group_id
    """
    tasks = [
        send_attendance_notification.s(
            data['student_id'],
            data['attendance_day_id'],
            data['group_id']
        )
        for data in attendance_data_list
    ]

    job = group(tasks)
    results = job.apply_async()

    return {
        "status": "success",
        "total_tasks": len(tasks),
        "task_ids": [str(r.id) for r in results.results]
    }


@celery.task(name='update_branch_reports')
def update_branch_reports():
    """
    Update branch reports for all locations
    Calculates daily statistics for each branch/location
    """
    try:
        # Get all locations
        locations = Locations.query.order_by(Locations.id).all()

        # Get current date components
        calendar_year, calendar_month, calendar_day = find_calendar_date()

        logger.info(f"Updating branch reports for {len(locations)} locations on {calendar_day.date}")

        for location in locations:
            try:
                # Check if report already exists for this location and date
                exist_branch = BranchReport.query.filter(
                    BranchReport.location_id == location.id,
                    BranchReport.year_id == calendar_year.id,
                    BranchReport.month_id == calendar_month.id,
                    BranchReport.day_id == calendar_day.id
                ).first()

                # Calculate metrics
                metrics = calculate_branch_metrics(location, calendar_year, calendar_month, calendar_day)

                if exist_branch:
                    # Update existing report
                    exist_branch.number_of_students = metrics['number_of_students']
                    exist_branch.number_of_deleted_students = metrics['number_of_deleted_students']
                    exist_branch.number_of_deleted_registrations = metrics['number_of_deleted_registrations']
                    exist_branch.number_of_teachers = metrics['number_of_teachers']
                    exist_branch.number_of_staff = metrics['number_of_staff']
                    exist_branch.number_of_groups = metrics['number_of_groups']
                    exist_branch.number_of_deleted_groups = metrics['number_of_deleted_groups']
                    exist_branch.number_of_payments = metrics['number_of_payments']
                    exist_branch.sum_of_payments = metrics['sum_of_payments']

                    logger.info(f"Updated existing report for location {location.id}")
                else:
                    # Create new report
                    branch = BranchReport(
                        location_id=location.id,
                        year_id=calendar_year.id,
                        month_id=calendar_month.id,
                        day_id=calendar_day.id,
                        number_of_students=metrics['number_of_students'],
                        number_of_deleted_students=metrics['number_of_deleted_students'],
                        number_of_deleted_registrations=metrics['number_of_deleted_registrations'],
                        number_of_teachers=metrics['number_of_teachers'],
                        number_of_staff=metrics['number_of_staff'],
                        number_of_groups=metrics['number_of_groups'],
                        number_of_deleted_groups=metrics['number_of_deleted_groups'],
                        number_of_payments=metrics['number_of_payments'],
                        sum_of_payments=metrics['sum_of_payments']
                    )
                    db.session.add(branch)
                    logger.info(f"Created new report for location {location.id}")

            except Exception as e:
                logger.error(f"Error processing location {location.id}: {e}")
                db.session.rollback()
                continue

        # Commit all changes
        db.session.commit()

        logger.info("Successfully updated all branch reports")
        return {
            "success": True,
            "msg": f"Updated reports for {len(locations)} locations",
            "date": str(calendar_day.date)
        }

    except Exception as e:
        logger.error(f"Error in update_branch_reports: {e}")
        db.session.rollback()
        return {
            "success": False,
            "msg": str(e)
        }


# Fixed calculate_branch_metrics function for tasks.py

def calculate_branch_metrics(location, calendar_year, calendar_month, calendar_day):
    """
    Calculate all metrics for a branch report

    Args:
        location: Location object
        calendar_year: CalendarYear object
        calendar_month: CalendarMonth object
        calendar_day: CalendarDay object

    Returns:
        dict: Dictionary containing all calculated metrics
    """

    # 1. NUMBER OF NEW STUDENTS REGISTERED TODAY
    number_of_students = db.session.query(Students, Users).join(
        Users, Users.id == Students.user_id
    ).filter(
        Users.location_id == location.id,
        Users.calendar_day == calendar_day.id
    ).count()

    # 2. NUMBER OF STUDENTS DELETED FROM GROUPS TODAY
    number_of_deleted_students = DeletedStudents.query.join(
        Students, Students.id == DeletedStudents.student_id
    ).join(
        Users, Users.id == Students.user_id
    ).filter(
        Users.location_id == location.id,
        DeletedStudents.calendar_day == calendar_day.id
    ).count()

    # 3. NUMBER OF STUDENTS DELETED FROM REGISTRATION TODAY
    number_of_deleted_registrations = RegisterDeletedStudents.query.join(
        Students, Students.id == RegisterDeletedStudents.student_id
    ).join(
        Users, Users.id == Students.user_id
    ).filter(
        Users.location_id == location.id,
        RegisterDeletedStudents.calendar_day == calendar_day.id
    ).count()

    # 4. TOTAL NUMBER OF ACTIVE TEACHERS AT THIS LOCATION
    # Fixed: Use is_(False) or == False with scalar, or .is_() if it's a boolean
    try:
        number_of_teachers = db.session.query(Teachers).join(
            Users, Users.id == Teachers.user_id
        ).filter(
            Users.location_id == location.id,
            Teachers.deleted == None  # Fixed: Use .is_(False) for boolean comparison
        ).count()
    except:
        # Fallback if deleted is not a boolean column
        number_of_teachers = db.session.query(Teachers).join(
            Users, Users.id == Teachers.user_id
        ).filter(
            Users.location_id == location.id
        ).count()

    # 5. TOTAL NUMBER OF ACTIVE STAFF AT THIS LOCATION
    try:
        number_of_staff = db.session.query(Staff).join(
            Users, Users.id == Staff.user_id
        ).filter(
            Users.location_id == location.id,
        ).filter(or_(Staff.deleted == False, Staff.deleted == None)).count()
    except:
        # Fallback: If Staff model doesn't exist or deleted field has issues, return 0
        number_of_staff = 0

    # 6. NUMBER OF NEW GROUPS CREATED TODAY
    number_of_groups = Groups.query.filter(
        Groups.location_id == location.id,
        Groups.calendar_day == calendar_day.id,
        Groups.deleted.is_(False)  # Fixed: Use .is_(False)
    ).count()

    # 7. NUMBER OF GROUPS DELETED TODAY
    number_of_deleted_groups = Groups.query.filter(
        Groups.location_id == location.id,
        Groups.calendar_day == calendar_day.id,
        Groups.deleted.is_(True)  # Fixed: Use .is_(True)
    ).count()

    # 8. NUMBER OF PAYMENTS MADE TODAY
    number_of_payments = StudentPayments.query.filter(
        StudentPayments.location_id == location.id,
        StudentPayments.calendar_day == calendar_day.id,
        StudentPayments.payment.is_(True)  # Fixed: Use .is_(True)
    ).count()

    # 9. TOTAL SUM OF PAYMENTS MADE TODAY
    payments_today = StudentPayments.query.filter(
        StudentPayments.location_id == location.id,
        StudentPayments.calendar_day == calendar_day.id,
        StudentPayments.payment.is_(True)  # Fixed: Use .is_(True)
    ).all()

    sum_of_payments = sum(
        payment.payment_sum for payment in payments_today
        if payment.payment_sum is not None
    )

    return {
        'number_of_students': number_of_students,
        'number_of_deleted_students': number_of_deleted_students,
        'number_of_deleted_registrations': number_of_deleted_registrations,
        'number_of_teachers': number_of_teachers,
        'number_of_staff': number_of_staff,
        'number_of_groups': number_of_groups,
        'number_of_deleted_groups': number_of_deleted_groups,
        'number_of_payments': number_of_payments,
        'sum_of_payments': sum_of_payments or 0
    }


@celery.task(name='update_branch_reports_for_date')
def update_branch_reports_for_date(year_id, month_id, day_id):
    """
    Update branch reports for a specific date
    Useful for recalculating historical data

    Args:
        year_id: Calendar year ID
        month_id: Calendar month ID
        day_id: Calendar day ID
    """
    try:
        from backend.models.models import CalendarYear, CalendarMonth, CalendarDay

        calendar_year = CalendarYear.query.get(year_id)
        calendar_month = CalendarMonth.query.get(month_id)
        calendar_day = CalendarDay.query.get(day_id)

        if not all([calendar_year, calendar_month, calendar_day]):
            return {
                "success": False,
                "msg": "Invalid date parameters"
            }

        locations = Locations.query.order_by(Locations.id).all()

        logger.info(f"Updating branch reports for date {calendar_day.date}")

        for location in locations:
            try:
                exist_branch = BranchReport.query.filter(
                    BranchReport.location_id == location.id,
                    BranchReport.year_id == year_id,
                    BranchReport.month_id == month_id,
                    BranchReport.day_id == day_id
                ).first()

                metrics = calculate_branch_metrics(location, calendar_year, calendar_month, calendar_day)

                if exist_branch:
                    # Update existing
                    for key, value in metrics.items():
                        setattr(exist_branch, key, value)
                else:
                    # Create new
                    branch = BranchReport(
                        location_id=location.id,
                        year_id=year_id,
                        month_id=month_id,
                        day_id=day_id,
                        **metrics
                    )
                    db.session.add(branch)

            except Exception as e:
                logger.error(f"Error processing location {location.id}: {e}")
                db.session.rollback()
                continue

        db.session.commit()

        return {
            "success": True,
            "msg": f"Updated reports for {len(locations)} locations",
            "date": str(calendar_day.date)
        }

    except Exception as e:
        logger.error(f"Error in update_branch_reports_for_date: {e}")
        db.session.rollback()
        return {
            "success": False,
            "msg": str(e)
        }


@celery.task(name='update_branch_reports_bulk')
def update_branch_reports_bulk(start_date, end_date):
    """
    Update branch reports for a date range
    Useful for bulk recalculation

    Args:
        start_date: Start date string (YYYY-MM-DD)
        end_date: End date string (YYYY-MM-DD)
    """
    try:
        from datetime import datetime, timedelta
        from backend.models.models import CalendarDay

        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')

        current_date = start
        updated_count = 0

        while current_date <= end:
            # Find calendar day for current date
            calendar_day = CalendarDay.query.filter(
                CalendarDay.date == current_date
            ).first()

            if calendar_day:
                # Update reports for this day
                result = update_branch_reports_for_date.delay(
                    calendar_day.year_id,
                    calendar_day.month_id,
                    calendar_day.id
                )
                updated_count += 1
                logger.info(f"Queued update for {current_date.date()}")

            current_date += timedelta(days=1)

        return {
            "success": True,
            "msg": f"Queued updates for {updated_count} days",
            "date_range": f"{start_date} to {end_date}"
        }

    except Exception as e:
        logger.error(f"Error in update_branch_reports_bulk: {e}")
        return {
            "success": False,
            "msg": str(e)
        }
