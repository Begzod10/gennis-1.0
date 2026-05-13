from backend.models.models import TeacherBlackSalary, Subjects, Teachers, Attendance, AttendanceDays, Groups, \
    AttendanceHistoryStudent, CalendarDay, db, AttendanceHistoryTeacher, CampStaffSalary, TeacherSalary, Students, \
    Staff, StaffSalary, CampStaff, CalendarMonth, Assistent, AssistentSalary, AssistentBlackSalary, AssistentSalaries, \
    CalendarYear, UserBooks
from sqlalchemy import extract, or_
from sqlalchemy.orm import contains_eager, joinedload
from backend.functions.utils import find_calendar_date
import datetime


def salary_debt(student_id, group_id, attendance_id, status_attendance, type_attendance):
    """
    Update Student balance and Teacher balance - FULLY OPTIMIZED
    """
    # OPTIMIZATION: Single query with all eager loading
    attendancedays = db.session.query(AttendanceDays).options(
        joinedload(AttendanceDays.day),
        joinedload(AttendanceDays.attendance).joinedload(Attendance.month),
        joinedload(AttendanceDays.attendance).joinedload(Attendance.year)
    ).filter(AttendanceDays.id == attendance_id).first()

    if not attendancedays:
        return None

    attendance = attendancedays.attendance
    months = int(attendance.month.date.strftime('%m'))
    current_year = int(attendance.year.date.strftime('%Y'))

    # Delete attendance day FIRST so deletion is not blocked by missing
    # group/teacher relationships further down. Recalc still proceeds best-effort.
    if status_attendance:
        db.session.delete(attendancedays)
        db.session.flush()

    # OPTIMIZATION: Single query for group with all related data
    group = db.session.query(Groups).options(
        joinedload(Groups.subject),
        joinedload(Groups.teacher).joinedload(Teachers.user),
        joinedload(Groups.teacher).joinedload(Teachers.assistent)
    ).filter(Groups.id == group_id).first()

    if not group:
        db.session.commit()
        return None

    subject = group.subject
    teacher = group.teacher[0] if group.teacher else None

    if not teacher:
        db.session.commit()
        return None

    # Get or create attendance history
    attendance_history_student = AttendanceHistoryStudent.query.filter(
        AttendanceHistoryStudent.calendar_month == attendance.calendar_month,
        AttendanceHistoryStudent.calendar_year == attendance.calendar_year,
        AttendanceHistoryStudent.student_id == student_id,
        AttendanceHistoryStudent.group_id == group_id,
        AttendanceHistoryStudent.subject_id == subject.id,
        AttendanceHistoryStudent.location_id == group.location_id
    ).first()

    # OPTIMIZATION: Single query for all student attendance data
    attendance_student_all = db.session.query(AttendanceDays).join(
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

    # Calculate all student statistics in memory
    total_balance = 0
    total_discount = 0
    attendance_student_present = 0
    attendance_student_absent = 0
    attendance_student_balls = []

    for record in attendance_student_all:
        # Balance calculation
        if not record.discount:
            total_balance += record.balance_per_day
        else:
            total_balance += record.balance_with_discount

        if record.discount_per_day:
            total_discount += record.discount_per_day

        # Status counting
        if record.status == 1:
            attendance_student_present += 1
        elif record.status == 0:
            attendance_student_absent += 1
        elif record.status == 2:
            attendance_student_balls.append(record)

    scored_days = len(attendance_student_balls)
    total_average = 0
    if attendance_student_balls:
        total_average = sum(ball.average_ball for ball in attendance_student_balls)
        total_average = round(total_average / len(attendance_student_balls))

    # Handle payment and remaining debt
    if attendance_history_student and attendance_history_student.payment:
        remaining_debt = total_balance - attendance_history_student.payment
        attendance_history_student.remaining_debt = remaining_debt

        student = Students.query.filter(Students.id == student_id).first()

        # Handle extra payment logic
        if type_attendance == "add" and student.extra_payment:
            total_payment = student.extra_payment + attendance_history_student.payment

            if total_payment >= total_balance:
                extra = total_payment - total_balance
                attendance_history_student.payment = total_balance
                attendance_history_student.remaining_debt = 0
                student.extra_payment = extra
            else:
                remaining = total_balance - total_payment
                attendance_history_student.payment = total_payment
                attendance_history_student.remaining_debt = remaining
                student.extra_payment = 0

        elif type_attendance != "add" and attendance_history_student.payment > total_balance:
            extra_payment = attendance_history_student.payment - total_balance
            student.extra_payment = extra_payment
            attendance_history_student.payment = total_balance
            attendance_history_student.remaining_debt = 0

    # Create or update attendance history
    if not attendance_history_student:
        attendance_history_student = AttendanceHistoryStudent(
            student_id=student_id,
            subject_id=subject.id,
            group_id=group_id,
            total_debt=-total_balance,
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
    else:
        attendance_history_student.total_debt = -total_balance
        attendance_history_student.present_days = attendance_student_present
        attendance_history_student.absent_days = attendance_student_absent
        attendance_history_student.average_ball = total_average
        attendance_history_student.total_discount = total_discount
        attendance_history_student.scored_days = scored_days
    db.session.flush()

    # Update payment status
    if attendance_history_student.payment and attendance_history_student.payment >= abs(
            attendance_history_student.total_debt):
        attendance_history_student.status = True
    else:
        attendance_history_student.status = False

    # OPTIMIZATION: Single query for teacher salary data
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

    # OPTIMIZATION: Single query for black salaries
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

    # Calculate in memory
    black_salary = sum(s.total_salary for s in black_salaries)
    total_salary = sum(s.salary_per_day for s in attendance_teacher_salary)
    total_fine = sum(s.fine for s in attendance_teacher_salary if s.fine)

    teacher_salary = 0
    teacher_fine = 0
    teacher_black_salary = 0

    # OPTIMIZATION: Calculate previous month calendar once
    current_month = int(attendance.month.date.strftime("%m"))
    current_year_num = int(attendance.year.date.strftime("%Y"))

    prev_month = current_month - 1
    prev_year = current_year_num
    if prev_month == 0:
        prev_month = 12
        prev_year -= 1

    prev_date = datetime.date(prev_year, prev_month, 1)
    prev_year_str = str(prev_year)

    # OPTIMIZATION: Fetch previous month calendar data once
    prev_calendar_year = CalendarYear.query.filter(
        CalendarYear.date == datetime.datetime.strptime(prev_year_str, "%Y")
    ).first()
    prev_calendar_month = CalendarMonth.query.filter(
        CalendarMonth.date == prev_date
    ).first()
    assistent = group.assistent if group.assistent else None
    if assistent:
        asistent_black_salaries = AssistentBlackSalary.query.filter(
            AssistentBlackSalary.assistent_id == assistent.id,
            AssistentBlackSalary.calendar_month == attendance.calendar_month,
            AssistentBlackSalary.calendar_year == attendance.calendar_year,
            AssistentBlackSalary.location_id == group.location_id,
            or_(
                AssistentBlackSalary.status == False,
                AssistentBlackSalary.status == None
            )

        ).all()
        assistent_salary = sum(
            s.assistent_salary_per_day for s in attendance_teacher_salary if s.assistent_salary_per_day)
        assistent_fine = sum(s.assistent_fine for s in attendance_teacher_salary if s.assistent_fine)
        assistent_black_salary = sum(s.total_salary for s in asistent_black_salaries)

        teacher_salary += assistent_salary
        teacher_fine += assistent_fine
        teacher_black_salary += assistent_black_salary

        salary_location = AssistentSalary.query.filter(
            AssistentSalary.assisten_id == assistent.id,
            AssistentSalary.location_id == group.location_id,
            AssistentSalary.calendar_month == attendance.calendar_month,
            AssistentSalary.calendar_year == attendance.calendar_year
        ).first()

        if not salary_location:
            salary_location = AssistentSalary(
                location_id=group.location_id,
                assisten_id=assistent.id,
                total_fine=assistent_fine,
                calendar_month=attendance.calendar_month,
                calendar_year=attendance.calendar_year,
                total_salary=assistent_salary
            )
            db.session.add(salary_location)
            db.session.flush()  # Flush to get the ID and relationships
        else:
            salary_location.total_fine = assistent_fine
            salary_location.total_salary = assistent_salary
            salary_location.status = False

        old_salary = None
        if prev_calendar_year and prev_calendar_month:
            old_salary = AssistentSalary.query.filter(
                AssistentSalary.assisten_id == assistent.id,
                AssistentSalary.location_id == group.location_id,
                AssistentSalary.calendar_month == prev_calendar_month.id,
                AssistentSalary.calendar_year == prev_calendar_year.id
            ).first()
        if old_salary:
            remaining = old_salary.remaining_salary or 0
            salary_location.debt = remaining if remaining < 0 else 0

        debt = salary_location.debt if salary_location.debt else 0
        if salary_location.taken_money:
            remaining_salary = salary_location.total_salary - (
                    salary_location.taken_money + assistent_black_salary +
                    salary_location.total_fine - debt
            )
            salary_location.remaining_salary = remaining_salary
            salary_location.status = salary_location.taken_money >= salary_location.total_salary

    # Calculate teacher's portion
    total_fine = total_fine - teacher_fine
    total_salary = total_salary - teacher_salary
    black_salary = black_salary - teacher_black_salary

    # OPTIMIZATION: Single query for teacher salary with eager loading
    salary_location = db.session.query(TeacherSalary).options(
        joinedload(TeacherSalary.month)
    ).filter(
        TeacherSalary.location_id == group.location_id,
        TeacherSalary.teacher_id == teacher.id,
        TeacherSalary.calendar_year == attendance.calendar_year,
        TeacherSalary.calendar_month == attendance.calendar_month
    ).first()

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
        db.session.flush()  # Flush to get relationships loaded
    else:
        salary_location.total_fine = total_fine
        salary_location.total_salary = total_salary
        salary_location.status = False

    # OPTIMIZATION: Fetch user books once
    user_books = UserBooks.query.filter(
        UserBooks.user_id == teacher.user_id,
        UserBooks.salary_location_id == salary_location.id
    ).all()

    book_payments = sum(pay.payment_sum for pay in user_books)

    # OPTIMIZATION: Fetch previous month teacher salary
    old_salary = None
    if prev_calendar_year and prev_calendar_month:
        old_salary = TeacherSalary.query.filter(
            TeacherSalary.teacher_id == teacher.id,
            TeacherSalary.calendar_year == prev_calendar_year.id,
            TeacherSalary.calendar_month == prev_calendar_month.id,
            TeacherSalary.location_id == salary_location.location_id
        ).first()

    if old_salary:
        if old_salary.remaining_salary:
            if old_salary.remaining_salary < 0:
                salary_location.debt = old_salary.remaining_salary
            else:
                salary_location.debt = 0

    debt = salary_location.debt if salary_location.debt else 0
    if salary_location.taken_money:
        remaining_salary = salary_location.total_salary - (
                salary_location.taken_money + black_salary +
                salary_location.total_fine + book_payments - debt
        )
        salary_location.remaining_salary = remaining_salary
        salary_location.status = salary_location.taken_money >= salary_location.total_salary

    # OPTIMIZATION: Single commit at the end
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
