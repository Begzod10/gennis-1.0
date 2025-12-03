# tasks/salary.py
import sys
from celery_app import celery
from backend.functions.debt_salary_update import salary_debt, find_calendar_date
from backend.student.class_model import Student_Functions
from backend.functions.utils import update_salary
from backend.models.models import TeacherBlackSalary, Students, db, Locations, DeletedStudents, RegisterDeletedStudents, \
    Groups, StudentPayments, BranchReport, Users, Teachers, Staff
import logging

logger = logging.getLogger(__name__)


@celery.task(name='process_salary_debt')
def process_salary_debt(student_id, group_id, attendance_id, status_attendance, type_attendance, teacher_id,
                        calendar_month, calendar_year, salary_per_day):
    salary_location = salary_debt(
        student_id, group_id, attendance_id,
        status_attendance, type_attendance
    )

    update_salary(teacher_id)
    student_obj = Students.query.get(student_id)
    st_functions = Student_Functions(student_id=student_id)
    st_functions.update_debt()
    st_functions.update_balance()
    if type_attendance == "add":
        if student_obj.debtor == 2:
            black_salary = TeacherBlackSalary.query.filter_by(
                teacher_id=teacher_id,
                student_id=student_id,
                calendar_month=calendar_month.id,
                calendar_year=calendar_year.id,
                location_id=student_obj.user.location_id,
                salary_id=salary_location.id,
                status=False
            ).first()
            if not black_salary:
                black_salary = TeacherBlackSalary(
                    teacher_id=teacher_id,
                    total_salary=salary_per_day,
                    student_id=student_obj.id,
                    salary_id=salary_location.id,
                    calendar_month=calendar_month.id,
                    calendar_year=calendar_year.id,
                    location_id=student_obj.user.location_id
                )
                black_salary.add()
            else:
                black_salary.total_salary += salary_per_day
                db.session.commit()
    return {"salary_location_id": salary_location.id}


@celery.task(name='send_student_info')
def send_student_info(user_id, attendance_id):
    from backend.models.models import Users, Students, Parent, AttendanceDays
    attendance = AttendanceDays.query.get(attendance_id)
    user = Users.query.get(user_id)
    parent = Parent.query.filter_by(user_id=user.id).first()

    return {
        "user": user.convert_json(),
        "parent": bool(parent),
        "attendance": attendance.convert_json()
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
            Teachers.deleted.is_(False)  # Fixed: Use .is_(False) for boolean comparison
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
            Staff.deleted.is_(False)  # Fixed: Use .is_(False) for boolean comparison
        ).count()
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
