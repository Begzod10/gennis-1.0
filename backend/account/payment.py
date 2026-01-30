from datetime import datetime
from datetime import timedelta

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from sqlalchemy import and_, or_, desc
from sqlalchemy.orm import contains_eager, joinedload
from backend.functions.utils import get_json_field, find_calendar_date, update_salary
from backend.models.models import AccountingPeriod, StudentPayments, Students, AttendanceHistoryStudent, PaymentTypes, \
    CalendarMonth, Groups, DeletedBookPayments, StudentCharity, DeletedStudentPayments, BookPayments, \
    TeacherBlackSalary, Teachers, TaskStudents, TasksStatistics, Tasks, db
from backend.student.class_model import Student_Functions

account_payment_bp = Blueprint('account_payment_bp', __name__)


@account_payment_bp.route(f'/delete_payment/<int:payment_id>', methods=['POST'])
@jwt_required()
def delete_payment(payment_id):
    """
    delete data from StudentPayments table
    :param payment_id: StudentPayments table primary key
    :return:
    """
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    reason = get_json_field('otherReason')
    accounting_period = db.session.query(AccountingPeriod).join(AccountingPeriod.month).options(
        contains_eager(AccountingPeriod.month)).order_by(desc(CalendarMonth.id)).first()
    type = get_json_field('type')
    if type == "bookPayment":
        book_payment = BookPayments.query.filter(BookPayments.id == payment_id).first()
        student = Students.query.filter(Students.id == book_payment.student_id).first()
        add = DeletedBookPayments(student_id=student.id, location_id=book_payment.location_id,
                                  calendar_day=calendar_day.id, calendar_month=calendar_month.id,
                                  calendar_year=calendar_year.id, payment_sum=book_payment.payment_sum,
                                  account_period_id=accounting_period.id)
        db.session.add(add)
        db.session.commit()
        db.session.delete(book_payment)
        db.session.commit()
        st_functions = Student_Functions(student_id=student.id)
        st_functions.update_debt()
        st_functions.update_balance()
        return jsonify({
            "success": True,
            "msg": "Kitob to'lovi o'chirildi"
        })
    else:

        payment = StudentPayments.query.filter(StudentPayments.id == payment_id).first()

        deleted_payment = DeletedStudentPayments(student_id=payment.student_id, reason=reason,
                                                 location_id=payment.location_id,
                                                 calendar_day=payment.calendar_day,
                                                 calendar_month=payment.calendar_month,
                                                 calendar_year=payment.calendar_year,
                                                 payment_type_id=payment.payment_type_id,
                                                 payment_sum=payment.payment_sum, deleted_date=calendar_day.date,
                                                 account_period_id=accounting_period.id,
                                                 payment=payment.payment)
        db.session.add(deleted_payment)
        db.session.commit()
        all_payments = payment.payment_sum

        student = Students.query.filter(Students.id == payment.student_id).first()
        attendance_history = AttendanceHistoryStudent.query.filter(
            AttendanceHistoryStudent.student_id == payment.student_id,
            AttendanceHistoryStudent.payment != None, AttendanceHistoryStudent.payment != 0).order_by(
            AttendanceHistoryStudent.id).order_by(desc(AttendanceHistoryStudent.id)).all()
        if attendance_history:
            for attendance in attendance_history:
                if student.extra_payment:
                    extra_payment = student.extra_payment - all_payments
                    if extra_payment > 0:
                        Students.query.filter(Students.id == student.id).update({"extra_payment": extra_payment})
                        all_payments = 0
                    else:
                        Students.query.filter(Students.id == student.id).update({"extra_payment": 0})
                        all_payments = abs(extra_payment)
                    db.session.commit()

                if attendance:
                    result = all_payments - attendance.payment
                    if result >= 0:
                        AttendanceHistoryStudent.query.filter(AttendanceHistoryStudent.id == attendance.id).update({
                            "status": False,
                            "payment": 0
                        })
                        db.session.commit()

                        AttendanceHistoryStudent.query.filter(
                            AttendanceHistoryStudent.id == attendance.id).update({
                            "remaining_debt": 0
                        })
                        db.session.commit()
                        all_payments = abs(result)
                        continue
                    elif result < 0:
                        AttendanceHistoryStudent.query.filter(AttendanceHistoryStudent.id == attendance.id).update({
                            "status": False,
                            "payment": abs(result)
                        })
                        db.session.commit()

                        remaining_debt = attendance.total_debt + attendance.payment
                        AttendanceHistoryStudent.query.filter(
                            AttendanceHistoryStudent.id == attendance.id).update({
                            "remaining_debt": remaining_debt
                        })
                        db.session.commit()
                        break
        else:
            if student.extra_payment:
                extra_payment = student.extra_payment - all_payments
                if extra_payment > 0:
                    Students.query.filter(Students.id == student.id).update({"extra_payment": extra_payment})
                else:
                    Students.query.filter(Students.id == student.id).update({"extra_payment": 0})
                db.session.commit()

        black_salaries = TeacherBlackSalary.query.filter(TeacherBlackSalary.student_id == student.id,
                                                         TeacherBlackSalary.payment_id == payment_id).all()
        for salary in black_salaries:
            salary.status = False
            salary.payment_id = None
            db.session.commit()
            teacher = Teachers.query.filter(Teachers.id == salary.teacher_id).first()
            update_salary(teacher.user_id)
        db.session.delete(payment)
        db.session.commit()
        st_functions = Student_Functions(student_id=student.id)
        st_functions.update_debt()
        st_functions.update_balance()

        return jsonify({
            "success": True,
            "msg": "To'lov o'chirildi"
        })


@account_payment_bp.route('/get_payment/', methods=['POST', 'GET'])
@jwt_required()
def get_payment(user_id):
    """Process student payment"""

    # Validate user
    student = Students.query.filter(Students.user_id == user_id).first()
    if not student:
        return jsonify({"success": False, "msg": "Student not found"}), 404

    if request.method == "POST":
        try:
            # Extract and validate input
            status = get_json_field('type') == "payment"
            type_payment = get_json_field('typePayment')
            payment_sum = int(get_json_field('payment'))

            # Validate payment amount
            if payment_sum <= 0:
                return jsonify({"success": False, "msg": "Invalid payment amount"}), 400

            # Process date
            calendar_year, calendar_month, calendar_day = process_payment_date(
                request.json.get('date')
            )

            # Get payment type
            payment_type = PaymentTypes.query.get(type_payment) if type_payment else PaymentTypes.query.first()
            if not payment_type:
                return jsonify({"success": False, "msg": "Payment type not found"}), 404

            # Get accounting period
            accounting_period = db.session.query(AccountingPeriod).join(
                AccountingPeriod.month
            ).options(
                contains_eager(AccountingPeriod.month)
            ).order_by(desc(CalendarMonth.id)).first()

            # Create payment record with rate limiting
            payment_time = datetime.utcnow() + timedelta(minutes=2)

            new_payment = StudentPayments(
                student_id=student.id,
                location_id=student.user.location_id,
                calendar_day=calendar_day.id,
                calendar_month=calendar_month.id,
                calendar_year=calendar_year.id,
                payment_type_id=payment_type.id,
                payment_sum=payment_sum,
                account_period_id=accounting_period.id,
                payment=status,
                payment_data=payment_time
            )
            db.session.add(new_payment)

            # Process payment distribution
            remaining_amount = distribute_payment(student.id, payment_sum, new_payment.id)

            # Handle extra payment
            if remaining_amount > 0:
                student.extra_payment = (student.extra_payment or 0) + remaining_amount

            # Update student financials
            st_functions = Student_Functions(student_id=student.id)
            st_functions.update_debt()
            st_functions.update_balance()

            # Handle task completion if debt cleared
            if student.debtor == 0:
                update_task_status(student.id, calendar_day.id, student.user.location_id)

            db.session.commit()

            return jsonify({"success": True, "msg": "To'lov qabul qilindi"})

        except ValueError as e:
            db.session.rollback()
            return jsonify({"success": False, "msg": "Invalid input"}), 400
        except Exception as e:
            db.session.rollback()
            return jsonify({"success": False, "msg": "Payment processing failed"}), 500

    else:  # GET request
        return get_payment_info(student)


def process_payment_date(date_str=None):
    """Process and validate payment date"""
    if date_str:
        try:
            year, month, day = date_str.split("-")
            date_day = datetime.strptime(f"{year}-{month}-{day}", "%Y-%m-%d")
            date_month = datetime.strptime(f"{year}-{month}", "%Y-%m")
            date_year = datetime.strptime(year, "%Y")
        except ValueError:
            raise ValueError("Invalid date format")
    else:
        date_day = date_month = date_year = None

    return find_calendar_date(
        date_day=date_day,
        date_month=date_month,
        date_year=date_year
    )


def distribute_payment(student_id, payment_amount, payment_id):
    """Distribute payment across unpaid attendance records"""

    # Fetch all unpaid attendance records at once
    unpaid_attendances = AttendanceHistoryStudent.query.filter(
        AttendanceHistoryStudent.student_id == student_id,
        AttendanceHistoryStudent.status == False
    ).order_by(AttendanceHistoryStudent.id).all()

    remaining = payment_amount

    for attendance in unpaid_attendances:
        if remaining <= 0:
            break

        # Calculate debt
        debt = abs(attendance.remaining_debt if attendance.remaining_debt else attendance.total_debt)

        if remaining >= debt:
            # Full payment
            attendance.status = True
            attendance.remaining_debt = 0
            attendance.payment = abs(attendance.total_debt)
            remaining -= debt
        else:
            # Partial payment
            new_remaining_debt = -(debt - remaining)
            attendance.remaining_debt = new_remaining_debt
            attendance.payment = abs(attendance.total_debt) - debt
            remaining = 0

    # Update teacher salaries
    update_teacher_salaries(student_id, payment_id)

    return remaining


def update_teacher_salaries(student_id, payment_id):
    """Update black salaries for teachers"""
    black_salaries = db.session.query(TeacherBlackSalary).options(
        joinedload(TeacherBlackSalary.teacher).joinedload(Teachers.user)
    ).filter(
        TeacherBlackSalary.student_id == student_id,
        TeacherBlackSalary.status.in_([False, None])
    ).all()

    for salary in black_salaries:
        salary.status = True
        salary.payment_id = payment_id
        update_salary(salary.teacher.user_id)


def update_task_status(student_id, calendar_day_id, location_id):
    """Update task status when debt is cleared"""
    task_type = Tasks.query.filter(Tasks.name == 'excuses').first()
    if not task_type:
        return

    task_statistics = TasksStatistics.query.filter(
        TasksStatistics.task_id == task_type.id,
        TasksStatistics.calendar_day == calendar_day_id,
        TasksStatistics.location_id == location_id
    ).first()

    if task_statistics:
        TaskStudents.query.filter(
            TaskStudents.task_id == task_type.id,
            TaskStudents.tasksstatistics_id == task_statistics.id,
            TaskStudents.student_id == student_id
        ).update({"status": True})


def get_payment_info(student):
    """Get payment information for GET requests"""
    group_ids = [group.id for group in student.group]

    # Fetch groups with charity info
    groups_with_charity = db.session.query(Groups).join(
        Groups.charity
    ).options(
        contains_eager(Groups.charity)
    ).filter(
        Groups.id.in_(group_ids),
        StudentCharity.student_id == student.id
    ).all()

    charity_group_ids = {g.id for g in groups_with_charity}

    group_list = []

    # Add charity groups
    for group in groups_with_charity:
        info = {
            "id": group.id,
            "name": group.name.title()
        }
        for charity in group.charity:
            info['charity'] = charity.discount
        group_list.append(info)

    # Add non-charity groups
    regular_group_ids = set(group_ids) - charity_group_ids
    if regular_group_ids:
        regular_groups = Groups.query.filter(Groups.id.in_(regular_group_ids)).all()
        for group in regular_groups:
            group_list.append({
                "id": group.id,
                "name": group.name.title()
            })

    return jsonify({"payment": {"groups": group_list}})


@account_payment_bp.route(f'/charity/<int:student_id>', methods=['POST'])
@jwt_required()
def charity(student_id):
    """
    add data to StudentCharity table
    :param student_id: Student table primary key
    :return:
    """
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    student = Students.query.filter(Students.user_id == student_id).first()
    accounting_period = db.session.query(AccountingPeriod).join(AccountingPeriod.month).options(
        contains_eager(AccountingPeriod.month)).order_by(desc(CalendarMonth.id)).first()

    group_id = int(get_json_field('group_id'))
    discount_amount = int(get_json_field('discount'))
    charity = StudentCharity.query.filter(StudentCharity.student_id == student.id,
                                          StudentCharity.group_id == group_id).first()
    if not charity:
        add = StudentCharity(student_id=student.id, discount=discount_amount, group_id=group_id,
                             calendar_day=calendar_day.id, calendar_month=calendar_month.id,
                             calendar_year=calendar_year.id, account_period_id=accounting_period.id,
                             location_id=student.user.location_id)
        db.session.add(add)
        db.session.commit()
    else:
        StudentCharity.query.filter(StudentCharity.student_id == student.id,
                                    StudentCharity.group_id == group_id).update({
            "discount": discount_amount
        })
        db.session.commit()
    return jsonify({
        "success": True,
        "msg": "Pul qabul qilindi"
    })


@account_payment_bp.route(f'/book_payment/<int:user_id>', methods=['POST'])
def book_payment(user_id):
    """
    add data to BookPayments table
    :param user_id: User table primary key
    :return:
    """
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    student = Students.query.filter(Students.user_id == user_id).first()
    accounting_period = db.session.query(AccountingPeriod).join(AccountingPeriod.month).options(
        contains_eager(AccountingPeriod.month)).order_by(desc(CalendarMonth.id)).first()
    payment = get_json_field('bookPayment')
    add = BookPayments(location_id=student.user.location_id, calendar_day=calendar_day.id, student_id=student.id,
                       calendar_month=calendar_month.id, calendar_year=calendar_year.id, payment_sum=payment,
                       account_period_id=accounting_period.id)
    db.session.add(add)
    db.session.commit()
    st_functions = Student_Functions(student_id=student.id)
    st_functions.update_debt()
    st_functions.update_balance()
    return jsonify({
        'msg': 'Kitobga pul olindi',
        'success': True
    })
