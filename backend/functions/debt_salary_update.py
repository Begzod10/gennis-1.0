from backend.models.models import TeacherBlackSalary, Subjects, Teachers, Attendance, AttendanceDays, Groups, \
    AttendanceHistoryStudent, CalendarDay, db, AttendanceHistoryTeacher, CampStaffSalary, TeacherSalary, Students, \
    Staff, StaffSalary, CampStaff, CalendarMonth
from sqlalchemy import extract, or_
from sqlalchemy.orm import contains_eager
from backend.functions.utils import find_calendar_date


def salary_debt(student_id, group_id, attendance_id, status_attendance, type_attendance):
    """
    Update Student balance and Teacher balance
    """
    # Fetch all required objects
    group = Groups.query.filter(Groups.id == group_id).first()
    subject = Subjects.query.filter(Subjects.id == group.subject_id).first()
    teacher = Teachers.query.filter(Teachers.id == group.teacher_id).first()
    attendancedays = AttendanceDays.query.filter(AttendanceDays.id == attendance_id).first()
    attendance = Attendance.query.filter(Attendance.id == attendancedays.attendance_id).first()

    months = int(attendance.month.date.strftime('%m'))
    current_year = int(attendance.year.date.strftime('%Y'))

    # Delete attendance day if needed
    if status_attendance:
        db.session.delete(attendancedays)
        db.session.commit()

    # Get or create attendance history
    attendance_history_student = AttendanceHistoryStudent.query.filter(
        AttendanceHistoryStudent.calendar_month == attendance.calendar_month,
        AttendanceHistoryStudent.calendar_year == attendance.calendar_year,
        AttendanceHistoryStudent.student_id == student_id,
        AttendanceHistoryStudent.group_id == group_id,
        AttendanceHistoryStudent.subject_id == subject.id,
        AttendanceHistoryStudent.location_id == group.location_id
    ).first()

    # Calculate student balance
    attendance_student_balance = db.session.query(AttendanceDays).join(
        AttendanceDays.day
    ).options(
        contains_eager(AttendanceDays.day)
    ).filter(
        extract("year", CalendarDay.date) == current_year,
        extract("month", CalendarDay.date) == months,
        AttendanceDays.student_id == student_id,
        AttendanceDays.group_id == group_id,
        AttendanceDays.location_id == group.location_id
    ).all()

    total_balance = 0
    total_discount = 0
    for balance in attendance_student_balance:
        if not balance.discount:
            total_balance += balance.balance_per_day
        else:
            total_balance += balance.balance_with_discount
        if balance.discount_per_day:
            total_discount += balance.discount_per_day  # Fixed: += instead of =

    # Handle payment and remaining debt
    if attendance_history_student and attendance_history_student.payment:
        remaining_debt = total_balance - attendance_history_student.payment  # Fixed: removed negation

        AttendanceHistoryStudent.query.filter(
            AttendanceHistoryStudent.id == attendance_history_student.id
        ).update({'remaining_debt': remaining_debt})  # Fixed: not negated
        db.session.commit()

        student = Students.query.filter(Students.id == student_id).first()

        # Handle extra payment logic
        if type_attendance == "add" and student.extra_payment:
            total_payment = student.extra_payment + attendance_history_student.payment

            if total_payment >= total_balance:
                # Student has paid enough
                extra = total_payment - total_balance
                AttendanceHistoryStudent.query.filter(
                    AttendanceHistoryStudent.id == attendance_history_student.id
                ).update({
                    "payment": total_balance,
                    "remaining_debt": 0
                })
                Students.query.filter(Students.id == student_id).update({"extra_payment": extra})
            else:
                # Student still owes money
                remaining = total_balance - total_payment
                AttendanceHistoryStudent.query.filter(
                    AttendanceHistoryStudent.id == attendance_history_student.id
                ).update({
                    "payment": total_payment,
                    "remaining_debt": remaining
                })
                Students.query.filter(Students.id == student_id).update({"extra_payment": 0})
            db.session.commit()

        elif type_attendance != "add" and attendance_history_student.payment > total_balance:
            # Overpayment case
            extra_payment = attendance_history_student.payment - total_balance
            Students.query.filter(Students.id == student_id).update({"extra_payment": extra_payment})
            AttendanceHistoryStudent.query.filter(
                AttendanceHistoryStudent.id == attendance_history_student.id
            ).update({
                "payment": total_balance,
                "remaining_debt": 0
            })
            db.session.commit()

    # Calculate attendance statistics
    attendance_student_present = db.session.query(AttendanceDays).join(
        AttendanceDays.day
    ).options(
        contains_eager(AttendanceDays.day)
    ).filter(
        extract("year", CalendarDay.date) == current_year,
        extract("month", CalendarDay.date) == months,
        AttendanceDays.student_id == student_id,
        AttendanceDays.group_id == group_id,
        AttendanceDays.status == 1,
        AttendanceDays.location_id == group.location_id
    ).count()

    attendance_student_absent = db.session.query(AttendanceDays).join(
        AttendanceDays.day
    ).options(
        contains_eager(AttendanceDays.day)
    ).filter(
        extract("year", CalendarDay.date) == current_year,
        extract("month", CalendarDay.date) == months,
        AttendanceDays.student_id == student_id,
        AttendanceDays.group_id == group_id,
        AttendanceDays.status == 0,
        AttendanceDays.location_id == group.location_id
    ).count()

    attendance_student_balls = db.session.query(AttendanceDays).join(
        AttendanceDays.day
    ).options(
        contains_eager(AttendanceDays.day)
    ).filter(
        extract("year", CalendarDay.date) == current_year,
        extract("month", CalendarDay.date) == months,
        AttendanceDays.student_id == student_id,
        AttendanceDays.group_id == group_id,
        AttendanceDays.status == 2,
        AttendanceDays.location_id == group.location_id
    ).all()

    scored_days = len(attendance_student_balls)
    total_average = 0
    if attendance_student_balls:
        total_average = sum(ball.average_ball for ball in attendance_student_balls)
        total_average = round(total_average / len(attendance_student_balls))

    # Create or update attendance history
    if not attendance_history_student:
        attendance_history_student = AttendanceHistoryStudent(
            student_id=student_id,
            subject_id=subject.id,
            group_id=group_id,
            total_debt=-total_balance,  # Keep your convention
            present_days=attendance_student_present,
            absent_days=attendance_student_absent,
            average_ball=total_average,
            location_id=group.location_id,
            calendar_month=attendance.calendar_month,
            calendar_year=attendance.calendar_year,
            total_discount=total_discount,
            scored_days=scored_days
        )
        db.session.add(attendance_history_student)
        db.session.commit()
    else:
        AttendanceHistoryStudent.query.filter(
            AttendanceHistoryStudent.id == attendance_history_student.id
        ).update({
            "total_debt": -total_balance,
            "present_days": attendance_student_present,
            "absent_days": attendance_student_absent,
            "average_ball": total_average,
            'total_discount': total_discount,
            "scored_days": scored_days
        })
        db.session.commit()
        db.session.refresh(attendance_history_student)  # Refresh instead of re-query

    # Update payment status
    if attendance_history_student.payment and attendance_history_student.payment >= abs(
            attendance_history_student.total_debt):
        attendance_history_student.status = True
    else:
        attendance_history_student.status = False
    db.session.commit()

    # Calculate teacher salary
    attendance_teacher_salary = db.session.query(AttendanceDays).join(
        AttendanceDays.day
    ).options(
        contains_eager(AttendanceDays.day)
    ).filter(
        extract("year", CalendarDay.date) == current_year,
        extract("month", CalendarDay.date) == months,
        AttendanceDays.teacher_id == teacher.id,
        AttendanceDays.location_id == group.location_id
    ).all()

    total_salary = sum(s.salary_per_day for s in attendance_teacher_salary)
    total_fine = sum(s.fine for s in attendance_teacher_salary if s.fine)

    # Get or create teacher salary record
    # Delete all duplicates first, keep only one
    existing_records = TeacherSalary.query.filter(
        TeacherSalary.location_id == group.location_id,
        TeacherSalary.teacher_id == teacher.id,
        TeacherSalary.calendar_year == attendance.calendar_year,
        TeacherSalary.calendar_month == attendance.calendar_month
    ).all()

    if len(existing_records) > 1:
        # Keep the first, delete the rest
        for record in existing_records[1:]:
            db.session.delete(record)
        db.session.commit()
        salary_location = existing_records[0]
    elif len(existing_records) == 1:
        salary_location = existing_records[0]
    else:
        salary_location = None

    # Now update or create
    if not salary_location:
        salary_location = TeacherSalary(
            location_id=group.location_id,
            teacher_id=teacher.id,
            total_fine=total_fine,
            calendar_month=attendance.calendar_month,
            calendar_year=attendance.calendar_year,
            total_salary=total_salary
        )
        db.session.add(salary_location)
    else:
        salary_location.total_fine = total_fine
        salary_location.total_salary = total_salary
        salary_location.status = False

    db.session.commit()

    # Calculate black salary
    black_salaries = TeacherBlackSalary.query.filter(
        TeacherBlackSalary.teacher_id == teacher.id,
        TeacherBlackSalary.calendar_month == attendance.calendar_month,
        TeacherBlackSalary.calendar_year == attendance.calendar_year,
        TeacherBlackSalary.location_id == group.location_id,
        or_(
            TeacherBlackSalary.status == False,
            TeacherBlackSalary.status == None
        )
    ).all()

    black_salary = sum(s.total_salary for s in black_salaries)
    debt = salary_location.debt if salary_location.debt else 0

    if salary_location.taken_money:
        remaining_salary = salary_location.total_salary - (
                salary_location.taken_money + black_salary + salary_location.total_fine - debt
        )
        salary_location.remaining_salary = remaining_salary

        if salary_location.taken_money >= salary_location.total_salary:
            salary_location.status = True
        else:
            salary_location.status = False

        db.session.commit()

    return salary_location


def update_teacher_salary(teacher_id, salary_id):
    """
    Update teacher salary calculations for a specific month/location
    """
    teacher = Teachers.query.filter(Teachers.id == teacher_id).first()
    salary_location = TeacherSalary.query.filter(TeacherSalary.id == salary_id).first()

    if not teacher or not salary_location:
        return None

    # Get month and year
    calendar_month = CalendarMonth.query.get(salary_location.calendar_month)
    months = int(calendar_month.date.strftime('%m'))
    current_year = int(calendar_month.year.date.strftime('%Y'))

    # Calculate total salary and fines from attendance
    attendance_teacher_salary = db.session.query(AttendanceDays).join(
        AttendanceDays.day
    ).options(
        contains_eager(AttendanceDays.day)
    ).filter(
        extract("year", CalendarDay.date) == current_year,
        extract("month", CalendarDay.date) == months,
        AttendanceDays.teacher_id == teacher.id,
        AttendanceDays.location_id == salary_location.location_id
    ).all()
    day_salary_info = []
    for s in attendance_teacher_salary:
        day_salary_info.append({
            "salary_per_day": s.salary_per_day,
            "fine": s.fine
        })

    # Use sum() for cleaner aggregation - NO commits in loop!
    total_salary = sum(s.salary_per_day for s in attendance_teacher_salary if s.salary_per_day)
    total_fine = sum(s.fine for s in attendance_teacher_salary if s.fine)

    # Handle duplicate salary records (this shouldn't happen - add DB constraint!)
    salary_locations = TeacherSalary.query.filter(
        TeacherSalary.location_id == salary_location.location_id,
        TeacherSalary.teacher_id == teacher.id,
        TeacherSalary.calendar_year == salary_location.calendar_year,
        TeacherSalary.calendar_month == salary_location.calendar_month
    ).all()

    if len(salary_locations) > 1:
        # Delete all duplicates except the first one
        for duplicate in salary_locations[1:]:
            # Delete related black salaries
            TeacherBlackSalary.query.filter(
                TeacherBlackSalary.salary_id == duplicate.id
            ).delete()
            db.session.delete(duplicate)
        db.session.commit()

    # Update main salary record
    salary_location.total_fine = total_fine
    salary_location.total_salary = total_salary
    salary_location.status = False
    db.session.commit()

    # Calculate black salary (only unpaid ones for this month/location)
    black_salaries = TeacherBlackSalary.query.filter(
        TeacherBlackSalary.teacher_id == teacher.id,
        TeacherBlackSalary.calendar_month == salary_location.calendar_month,
        TeacherBlackSalary.calendar_year == salary_location.calendar_year,
        TeacherBlackSalary.location_id == salary_location.location_id,
        or_(
            TeacherBlackSalary.status == False,
            TeacherBlackSalary.status == None
        )
    ).all()

    black_salary = sum(s.total_salary for s in black_salaries if s.total_salary)
    debt = salary_location.debt if salary_location.debt else 0

    # Calculate remaining salary
    # Formula: total_salary - (taken_money + black_salary + fines - debt)
    taken_money = salary_location.taken_money if salary_location.taken_money else 0
    remaining_salary = salary_location.total_salary - (
            taken_money + black_salary + salary_location.total_fine - debt
    )

    # Update remaining salary and status
    salary_location.remaining_salary = remaining_salary

    if taken_money >= salary_location.total_salary:
        salary_location.status = True
    else:
        salary_location.status = False

    db.session.commit()

    return day_salary_info


def staff_salary_update():
    """
    create salary data in StaffSalary table
    :return:
    """
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    staff = Staff.query.order_by(Staff.id).all()
    for item in staff:
        if item.salary:
            staff_salary_info = StaffSalary.query.filter(StaffSalary.calendar_month == calendar_month.id,
                                                         StaffSalary.calendar_year == calendar_year.id,
                                                         StaffSalary.staff_id == item.id).first()
            if not staff_salary_info:
                staff_salary_info = StaffSalary(calendar_month=calendar_month.id, calendar_year=calendar_year.id,
                                                total_salary=item.salary, staff_id=item.id,
                                                location_id=item.user.location_id)
                db.session.add(staff_salary_info)
                db.session.commit()


def camp_staff_salary_update():
    """
    create salary data in CampStaffSalary table
    :return:
    """
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    staff = CampStaff.query.order_by(CampStaff.id).all()
    for item in staff:
        if item.salary:
            staff_salary_info = CampStaffSalary.query.filter(CampStaffSalary.month_id == calendar_month.id,
                                                             CampStaffSalary.year_id == calendar_year.id,
                                                             CampStaffSalary.camp_staff_id == item.id).first()

            if not staff_salary_info:
                staff_salary_info = CampStaffSalary(month_id=calendar_month.id, year_id=calendar_year.id,
                                                    total_salary=item.salary, remaining_salary=item.salary,
                                                    taken_money=item.salary, camp_staff_id=item.id)
                db.session.add(staff_salary_info)
                db.session.commit()
