from datetime import datetime

from flask import Blueprint
from flask import request, jsonify
from sqlalchemy import or_, and_, func

from backend.models.models import Staff, Users, Teachers, TeacherSalary, StaffSalary, CalendarMonth, CalendarYear, \
    TeacherBlackSalary, db, AttendanceHistoryStudent, Students, Groups, Subjects, \
    DeletedStudents, CalendarDay, DeletedTeachers, Overhead, StudentPayments

home_screen_bp = Blueprint('home_screen_bp', __name__)


@home_screen_bp.route('/debtors/', methods=['GET'])
def home_screen_debtors():
    location_id = request.args.get('location_id')
    month = request.args.get('month')
    year = request.args.get('year')
    month_date = year + '-' + month
    year_obj = datetime.strptime(year, '%Y')
    month_date_obj = datetime.strptime(month_date, '%Y-%m')

    year_id = CalendarYear.query.filter(CalendarYear.date == year_obj).first().id
    month_id = CalendarMonth.query.filter(
        CalendarMonth.date == month_date_obj,
        CalendarMonth.year_id == year_id
    ).first().id

    attendance_records = (
        db.session.query(
            AttendanceHistoryStudent,
            Students,
            Users,
            Groups,
            Subjects,
            DeletedStudents,
            CalendarDay
        )
        .join(Students, AttendanceHistoryStudent.student_id == Students.id)
        .join(Users, Students.user_id == Users.id)
        .join(Groups, AttendanceHistoryStudent.group_id == Groups.id)
        .join(Subjects, Groups.subject_id == Subjects.id)
        .outerjoin(DeletedStudents, Students.id == DeletedStudents.student_id)
        .outerjoin(CalendarDay, DeletedStudents.calendar_day == CalendarDay.id)
        .outerjoin(CalendarMonth, CalendarDay.month_id == CalendarMonth.id)
        .filter(
            AttendanceHistoryStudent.calendar_month == month_id,
            AttendanceHistoryStudent.calendar_year == year_id,
            Users.location_id == location_id,
            Groups.status == True,
            or_(
                DeletedStudents.id == None,
                CalendarDay.date >= month_date_obj.replace(day=1)  # Fixed: proper date comparison
            )
        )
        .order_by(Students.id)
        .all()
    )

    students_dict = {}
    calculated_discounts = {}  # Cache to avoid duplicate queries
    total_debt = 0
    payment = 0
    total_discount = 0
    total_first_discount = 0

    for attendance, student, user, group, subject, deleted_student, calendar_day in attendance_records:
        # Calculate discount only once per student
        if student.id not in calculated_discounts:
            student_discounts = StudentPayments.query.filter(
                StudentPayments.student_id == student.id,
                StudentPayments.calendar_month == month_id,
                StudentPayments.calendar_year == year_id,
                StudentPayments.location_id == location_id,
                StudentPayments.payment == False
            ).all()

            for_student_total_discount = sum(d.payment_sum for d in student_discounts if d.payment_sum)
            calculated_discounts[student.id] = for_student_total_discount
            total_first_discount += for_student_total_discount
        else:
            for_student_total_discount = calculated_discounts[student.id]

        if student.id not in students_dict:
            students_dict[student.id] = {
                'id': student.id,
                'student_name': f"{user.name} {user.surname}",
                "month": month_date_obj.strftime("%Y-%m"),
                "is_deleted": deleted_student is not None,
                "deleted_date": calendar_day.date.strftime("%Y-%m") if calendar_day else None,
                "groups": []
            }

        # Handle NULL values properly
        total_debt += attendance.total_debt if attendance.total_debt else 0
        payment += attendance.payment if attendance.payment else 0
        total_discount += attendance.total_discount if attendance.total_discount else 0

        students_dict[student.id]['groups'].append({
            'group_name': group.name,
            "subject_name": subject.name,
            "remaining_debt": attendance.remaining_debt if attendance.remaining_debt is not None else 0,
            "total_debt": attendance.total_debt if attendance.total_debt else 0,
            "payment": attendance.payment if attendance.payment else 0,
            "total_discount": attendance.total_discount if attendance.total_discount else 0,
            "for_student_total_discount": for_student_total_discount
        })

    attendance_history_list = list(students_dict.values())

    return jsonify({
        "student_list": attendance_history_list,
        "total_debt": total_debt,
        "remaining_debt": total_debt + payment,
        "payment": payment,
        "total_discount": total_discount,
        "total_first_discount": total_first_discount
    })


@home_screen_bp.route('/salaries/', methods=['GET'])
def home_screen_salaries():
    location_id = request.args.get('location_id')
    month = request.args.get('month')
    year = request.args.get('year')
    type_salary = request.args.get('type_salary')
    month_date = year + '-' + month
    year_obj = datetime.strptime(year, '%Y')
    month_date_obj = datetime.strptime(month_date, '%Y-%m')

    year_id = CalendarYear.query.filter(CalendarYear.date == year_obj).first().id
    month_id = CalendarMonth.query.filter(
        CalendarMonth.date == month_date_obj,
        CalendarMonth.year_id == year_id
    ).first().id

    if type_salary == "teacher":
        salary_records = (
            db.session.query(
                TeacherSalary,
                Teachers,
                Users,
                CalendarMonth,
                CalendarYear,
                DeletedTeachers
            )
            .join(Teachers, TeacherSalary.teacher_id == Teachers.id)  # Fixed join order
            .join(Users, Teachers.user_id == Users.id)
            .join(CalendarMonth, TeacherSalary.calendar_month == CalendarMonth.id)
            .join(CalendarYear, CalendarMonth.year_id == CalendarYear.id)
            .outerjoin(DeletedTeachers, Teachers.id == DeletedTeachers.teacher_id)  # Changed to outerjoin
            .filter(
                TeacherSalary.calendar_month == month_id,
                TeacherSalary.calendar_year == year_id,
                Users.location_id == location_id,
                TeacherSalary.location_id == location_id,
                or_(
                    DeletedTeachers.id == None,
                    CalendarMonth.date > month_date_obj
                )
            )
        )

        salary_dict = {}
        total_salary = 0
        total_taken_money = 0
        total_black_salary = 0
        total_debt = 0
        total_fine = 0
        total_remaining_salary = 0
        # Fix: Unpack in the same order as the query
        for salary, teacher, user, calendar_month, calendar_year, deleted_teacher in salary_records:
            teacher_name = f"{user.name} {user.surname}"
            teacher_salary = salary.total_salary
            teacher_black_salaries = TeacherBlackSalary.query.filter(
                TeacherBlackSalary.calendar_month == salary.calendar_month, TeacherBlackSalary.teacher_id == teacher.id,
                TeacherBlackSalary.location_id == location_id, TeacherBlackSalary.status == False).all()
            black_salary = 0
            for black in teacher_black_salaries:
                black_salary += black.total_salary
            debt = salary.debt if salary.debt else 0
            taken_money = salary.taken_money if salary.taken_money else 0
            fine = salary.total_fine if salary.total_fine else 0
            remaining_salary = teacher_salary - (taken_money + black_salary + fine - debt)
            # if teacher.id not in salary_dict:
            salary_dict[teacher.id] = {
                'id': teacher.id,
                'teacher_name': teacher_name,
                "month": month_date_obj.strftime("%Y-%m"),
                "is_deleted": deleted_teacher is not None,
                "deleted_date": calendar_year.date.strftime("%Y-%m") if deleted_teacher else None,
                "teacher_salary": teacher_salary,
                "taken_money": taken_money,
                "remaining_salary": remaining_salary,
                "black_salary": black_salary,
                "debt": debt,
                "fine": fine
            }
            total_remaining_salary += remaining_salary
            total_fine += fine
            total_debt += debt
            total_black_salary += black_salary
            total_salary += teacher_salary
            total_taken_money += salary.taken_money if salary.taken_money else 0

        salary_list = list(salary_dict.values())

        return jsonify({
            "salary_list": salary_list,
            "total_salary": total_salary,
            "taken_money": total_taken_money,
            "remaining_salary": total_remaining_salary,
            "black_salary": total_black_salary,
            "debt": total_debt,
            "fine": total_fine
        })
    else:
        salary_dict = {}
        total_salary = 0
        total_taken_money = 0

        salary_records = (
            db.session.query(
                StaffSalary,
                Staff,
                Users,
                CalendarMonth,
                CalendarYear
            )
            .join(Staff, StaffSalary.staff_id == Staff.id)
            .join(Users, Staff.user_id == Users.id)
            .join(CalendarMonth, StaffSalary.calendar_month == CalendarMonth.id)
            .join(CalendarYear, CalendarMonth.year_id == CalendarYear.id)
            .filter(
                StaffSalary.calendar_month == month_id,
                StaffSalary.calendar_year == year_id,
                Users.location_id == location_id,
                or_(
                    Staff.deleted == False,  # Staff not deleted
                    and_(
                        Staff.deleted == True,
                        func.date_trunc('month', Staff.deleted_date) >= month_date_obj
                        # Deleted on/after the requested month
                    )
                )
            )
        )

        # Loop through results
        for salary, staff, user, calendar_month, calendar_year in salary_records:
            staff_name = f"{user.name} {user.surname}"
            staff_salary = salary.total_salary

            if staff.id not in salary_dict:
                salary_dict[staff.id] = {
                    'id': staff.id,
                    'staff_name': staff_name,
                    "month": month_date_obj.strftime("%Y-%m"),
                    "is_deleted": staff.deleted,
                    "deleted_date": staff.deleted_date.strftime("%Y-%m") if staff.deleted_date else None,
                    "deleted_comment": staff.deleted_comment,
                    "staff_salary": staff_salary,
                    "taken_money": salary.taken_money if salary.taken_money else 0,
                    "remaining_salary": staff_salary - (salary.taken_money if salary.taken_money else 0)
                }

            total_salary += staff_salary
            total_taken_money += salary.taken_money if salary.taken_money else 0

        salary_list = list(salary_dict.values())

        return jsonify({
            "salary_list": salary_list,
            "total_salary": total_salary,
            "taken_money": total_taken_money,
            "remaining_salary": total_salary - total_taken_money
        })


@home_screen_bp.route(f'/overhead/')
def overhead():
    location_id = request.args.get('location_id')
    month = request.args.get('month')
    year = request.args.get('year')
    month_date = year + '-' + month
    year_obj = datetime.strptime(year, '%Y')
    month_date_obj = datetime.strptime(month_date, '%Y-%m')

    categories = ["gaz", "svet", "suv", "arenda"]

    year_id = CalendarYear.query.filter(CalendarYear.date == year_obj).first().id
    month_id = CalendarMonth.query.filter(
        CalendarMonth.date == month_date_obj,
        CalendarMonth.year_id == year_id
    ).first().id

    # Initialize totals
    total_gaz = 0
    total_svet = 0
    total_suv = 0
    total_arenda = 0
    total_other = 0
    overhead_list = []

    # Get ALL overheads once
    all_overheads = Overhead.query.filter(
        Overhead.calendar_month == month_id,
        Overhead.calendar_year == year_id,
        Overhead.location_id == location_id
    ).all()

    # Process each overhead item once
    for overhead in all_overheads:
        item_sum = overhead.item_sum if overhead.item_sum else 0

        # Categorize and sum
        if overhead.item_name == "gaz":
            total_gaz += item_sum
        elif overhead.item_name == "svet":
            total_svet += item_sum
        elif overhead.item_name == "suv":
            total_suv += item_sum
        elif overhead.item_name == "arenda":
            total_arenda += item_sum
        else:
            total_other += item_sum
        overhead_list.append({
            'id': overhead.id,
            'item_name': overhead.item_name,
            'item_sum': item_sum,
            'month': month_date_obj.strftime("%Y-%m"),
            "payment_type": overhead.payment_type.name
        })

    return jsonify({
        "overhead_list": overhead_list,
        "total_gaz": total_gaz,
        "total_svet": total_svet,
        "total_suv": total_suv,
        "total_arenda": total_arenda,
        "total_other": total_other
    })
