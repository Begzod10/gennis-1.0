import datetime

from app import app, db, jsonify, contains_eager, request, desc, or_
from backend.functions.utils import api, find_calendar_date, get_json_field, update_staff_salary_id, \
    update_teacher_salary_id, update_salary
from backend.models.models import Teachers, TeacherSalary, StaffSalary, Staff, PaymentTypes, DeletedStaffSalaries, \
    UserBooks, StaffSalaries, TeacherSalaries, DeletedTeacherSalaries, AccountingPeriod, CalendarMonth, StudentPayments, \
    Users, CalendarYear, Locations, TeacherBlackSalary, CalendarDay, Students
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.functions.debt_salary_update import staff_salary_update
from backend.functions.utils import iterate_models
from pprint import pprint


@app.route(f'{api}/salary_info2/<user_id>')
def salary_info2(user_id):
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    user = Users.query.filter(Users.id == user_id).first()
    teacher = Teachers.query.filter(Teachers.user_id == user.id).first()
    staff = Staff.query.filter(Staff.user_id == user.id).first()

    location = Locations.query.filter(Locations.id == user.location_id).first()
    locations = Locations.query.order_by(Locations.id).all()
    years_list = []
    if teacher:
        salary = TeacherSalary.query.filter(TeacherSalary.teacher_id == teacher.id).all()
        years = CalendarYear.query.filter(CalendarYear.id.in_([year.calendar_year for year in salary]))
        years_list = iterate_models(years)
    if teacher:
        if teacher:
            locations_list = [location.convert_json() for location in teacher.locations]
        else:
            locations_list = [location.convert_json() for location in locations]
    elif staff:
        locations_list = [location.convert_json()]
    else:
        locations_list = [location.convert_json()]

    return jsonify({
        "locations": locations_list,
        "years": years_list,
        "current_year": calendar_year.id
    })


@app.route(f'{api}/teacher_salary_inside2/<int:salary_id>/<int:user_id>')
def teacher_salary_inside2(salary_id, user_id):
    """

    :param salary_id: TeacherSalary and StaffSalary primary key
    :param user_id: User table primary key
    :return: TeacherSalaries table and StaffSalaries table data
    """
    staff_salary_update()
    teacher = Teachers.query.filter(Teachers.user_id == user_id).first()

    result = 0
    black_salary = 0
    if teacher:
        teacher_black_salaries = TeacherBlackSalary.query.filter(TeacherBlackSalary.salary_id == salary_id,
                                                                 TeacherBlackSalary.teacher_id == teacher.id,
                                                                 TeacherBlackSalary.status == False).all()

        for black in teacher_black_salaries:
            black_salary += black.total_salary
        salary = TeacherSalary.query.filter(TeacherSalary.id == salary_id).first()

        salaries = TeacherSalaries.query.filter(TeacherSalaries.salary_location_id == salary_id).order_by(
            TeacherSalaries.id).all()
        user_books = UserBooks.query.filter(UserBooks.user_id == user_id,
                                            UserBooks.salary_location_id == salary_id).order_by(UserBooks.id).all()
        book_payments = 0
        for pay in user_books:
            book_payments += pay.payment_sum
        all_salaries = 0
        for sal in salaries:
            all_salaries += sal.payment_sum

        result = salary.total_salary - (all_salaries + black_salary + book_payments)
        TeacherSalary.query.filter(TeacherSalary.id == salary_id).update({
            "remaining_salary": result,
            "taken_money": all_salaries,
        })
        db.session.commit()
        update_teacher_salary_id(salary_id)

    else:
        salary = StaffSalary.query.filter(StaffSalary.id == salary_id).first()
        user_books = UserBooks.query.filter(UserBooks.user_id == user_id,
                                            UserBooks.salary_id == salary_id).order_by(UserBooks.id).all()
        update_staff_salary_id(salary_id)
        salaries = StaffSalaries.query.filter(StaffSalaries.salary_id == salary_id).order_by(
            StaffSalaries.id).all()
    list_salaries = [{
        "id": sal.id,
        "salary": sal.payment_sum,
        "reason": sal.reason,
        "payment_type": sal.payment_type.name,
        "date": sal.day.date.strftime("%Y-%m-%d"),
        "status": False
    } for sal in salaries]

    for book in user_books:
        list_salaries.append(book.convert_json())

    if salary.remaining_salary:
        exist_money = salary.remaining_salary
    else:
        exist_money = salary.total_salary
    return jsonify({
        "data": {
            "salary": salary.total_salary,
            "residue": salary.remaining_salary,
            "taken_salary": salary.taken_money,
            "exist_salary": exist_money,
            "month": salary.month.date.strftime("%Y-%m"),
            "data": list_salaries,
            "black_salary": black_salary
        }
    })
