import pprint

from flask import request, jsonify
from flask_jwt_extended import jwt_required
from backend.models.models import CampStaff, CampStaffSalary, CampStaffSalaries, Users, PhoneList, Roles, PaymentTypes
from backend.functions.utils import api, find_calendar_date, refreshdatas, update_camp_salary_id, get_json_field, \
    iterate_models
from backend.functions.debt_salary_update import camp_staff_salary_update

from sqlalchemy import desc
import datetime
from app import app, db
from werkzeug.security import generate_password_hash
from .utils import update_account


@app.route(f'{api}/get_staff_salary', methods=['GET'])
@jwt_required()
def get_staff_salary():
    staff_salarys = CampStaffSalary.query.order_by(CampStaffSalary.id).all()
    dividend_list = [
        {"salary": staff_salary.amount_sum, "date": staff_salary.month.date,
         "desc": staff_salary.desc} for
        staff_salary in staff_salarys]
    return jsonify({'dividends': dividend_list}), 201


@app.route(f'{api}/camp_staff/<int:user_id>')
@jwt_required()
def camp_staff(user_id):
    """

    :param user_id: User table primary key
    :param location_id: Location table primary key
    :return: TeacherSalary table and StaffSalary table data
    """

    staff = CampStaff.query.filter(CampStaff.user_id == user_id).first()

    staff_salaries = CampStaffSalary.query.filter(CampStaffSalary.camp_staff_id == staff.id).order_by(
        desc(CampStaffSalary.id)).all()
    teacher_salary_list = iterate_models(staff_salaries)

    return jsonify({
        "data": teacher_salary_list
    })


@app.route(f'{api}/camp_staff_inside/<int:salary_id>/', defaults={'deleted': False})
@app.route(f'{api}/camp_staff_inside/<int:salary_id>/<deleted>/')
@jwt_required()
def camp_staff_inside(salary_id, deleted):
    """

    :param salary_id: TeacherSalary and StaffSalary primary key
    :param user_id: User table primary key
    :return: TeacherSalaries table and StaffSalaries table data
    """
    deleted = deleted.capitalize()

    salary = CampStaffSalary.query.filter(CampStaffSalary.id == salary_id).first()
    update_camp_salary_id(salary_id)
    salaries = CampStaffSalaries.query.filter(CampStaffSalaries.salary_id == salary_id,
                                              CampStaffSalaries.deleted == deleted).order_by(
        CampStaffSalaries.id).all()
    list_salaries = iterate_models(salaries)

    exist_money = salary.remaining_salary if salary.remaining_salary else salary.total_salary

    return jsonify({
        "data": {
            "salary": salary.total_salary,
            "residue": salary.remaining_salary,
            "taken_salary": salary.taken_money,
            "exist_salary": exist_money,
            "month": salary.month.date.strftime("%Y-%m"),
            "data": list_salaries,
        }
    })


@app.route(f'{api}/camp_staff_salary/<int:salary_id>', methods=['POST'])
@jwt_required()
def camp_staff_salary(salary_id):
    pprint.pprint(request.get_json())
    get_salary = int(get_json_field('payment'))
    reason = get_json_field('reason')
    payment_type = int(get_json_field('typePayment'))
    current_year = datetime.datetime.now().year
    old_year = datetime.datetime.now().year - 1
    month = str(datetime.datetime.now().month)
    month_get = get_json_field('month')
    day = get_json_field('day')
    if month_get == "12" and month == "01":
        current_year = old_year
    if not month_get:
        month_get = month

    date_day = str(current_year) + "-" + str(month_get) + "-" + str(day)
    date_month = str(current_year) + "-" + str(month_get)
    date_year = str(current_year)
    date_day = datetime.datetime.strptime(date_day, "%Y-%m-%d")
    date_month = datetime.datetime.strptime(date_month, "%Y-%m")
    date_year = datetime.datetime.strptime(date_year, "%Y")
    calendar_year, calendar_month, calendar_day = find_calendar_date(date_day, date_month, date_year)
    payment_type_id = PaymentTypes.query.filter(PaymentTypes.id == payment_type).first()

    staff_cash = CampStaffSalary.query.filter(CampStaffSalary.id == salary_id).first()
    if staff_cash.remaining_salary:
        total_salary = staff_cash.remaining_salary
    else:
        total_salary = staff_cash.total_salary
    if get_salary > total_salary:
        return jsonify({
            "success": False,
            "msg": "Kiritilgan summa miqdori umumiy oylik miqdoridan kop"
        })
    else:
        add = CampStaffSalaries(amount_sum=get_salary, reason=reason, payment_type_id=payment_type_id.id,
                                camp_staff_id=staff_cash.camp_staff_id,
                                month_id=calendar_month.id, day_id=calendar_day.id,
                                year_id=calendar_year.id,
                                salary_id=staff_cash.id)
        db.session.add(add)
        db.session.commit()
    update_camp_salary_id(salary_id)
    update_account()
    return jsonify({
        "success": True,
        "msg": "Muvaffaqiyatli qo'shildi"
    })


@app.route(f'{api}/update_camp_staff_salary/<int:salary_id>/<int:payment_type_id>', methods=['POST'])
@jwt_required()
def update_camp_staff_salary(salary_id, payment_type_id):
    staff_salary = CampStaffSalaries.query.filter(CampStaffSalaries.id == salary_id).first()
    payment_type = PaymentTypes.query.filter(PaymentTypes.id == payment_type_id).first()
    staff_salary.payment_type_id = payment_type.id
    db.session.commit()
    update_account()
    return jsonify({
        "success": True,
        "msg": "Avans summa turi o'zgartirildi"
    })


@app.route(f'{api}/delete_camp_staff_salary/<int:salary_id>', methods=['DELETE'])
@jwt_required()
def delete_camp_staff_salary(salary_id):
    staff_salary = CampStaffSalaries.query.filter(CampStaffSalaries.id == salary_id).first()
    staff_salary.deleted = True
    staff_salary.deleted_comment = get_json_field('otherReason')
    db.session.commit()
    update_account()
    return jsonify({
        "success": True,
        "msg": "Muvaffaqiyatli o'chirildi"
    })


@app.route(f'{api}/register_camp_staff', methods=['POST', "GET"])
@jwt_required()
def register_camp_staff():
    if request.method == 'POST':
        refreshdatas()
        data = request.get_json()
        name = data['name']
        surname = data['surname']
        username = data['username']
        password = generate_password_hash(data['password'])
        role_id = data['role_id']
        father_name = data['father_name']
        salary = int(data['salary'])
        phone = data['phone']
        born_year, born_month, born_day = map(int, data['birth_date'].split('-'))
        calendar_year, calendar_month, calendar_day = find_calendar_date()
        from datetime import datetime
        today = datetime.today()
        age = today.year - born_year
        if (today.month, today.day) < (born_month, born_day):
            age -= 1
        exist_user = Users.query.filter(Users.username == username).first()
        if exist_user:
            return jsonify({
                'message': 'Username already exists'
            })
        user = Users(
            name=name,
            surname=surname,
            username=username,
            password=password,
            role_id=role_id,
            father_name=father_name,
            age=age,
            born_day=born_day,
            born_month=born_month,
            born_year=born_year,
            calendar_day=calendar_day.id,
            calendar_month=calendar_month.id,
            calendar_year=calendar_year.id
        )
        user.add()
        phone_list = PhoneList(
            phone=phone,
            user_id=user.id,
            personal=True
        )
        phone_list.add()
        staff_camp = CampStaff(
            user_id=user.id,
            role_id=role_id,
            salary=salary,
        )
        staff_camp.add()
        return jsonify({
            'message': 'Campus Staff registered successfully',
            'user': {
                "id": user.id,
                "name": user.name,
                "surname": user.surname,
                "username": user.username,
                "role": Roles.query.filter(Roles.id == user.role_id).first().type_role,
                "phone": PhoneList.query.filter(Users.id == user.id).first().phone,
                "age": user.age}
        }), 201
    else:
        camp_staff_salary_update()
        camps = CampStaff.query.filter(CampStaff.deleted == False).order_by(CampStaff.id).all()
        camp_list = iterate_models(camps)
        return jsonify({'staffs': camp_list}), 201


@app.route(f'{api}/roles', methods=['GET'])
@jwt_required()
def get_roles():
    roles = Roles.query.order_by(Roles.id).all()
    roles = [{'id': location.id, "name": location.type_role} for location in roles]
    return jsonify({'roles': roles}), 201


@app.route(f'{api}/camp_staff_salaries/<deleted>/<archive>/', methods=['GET'])
@jwt_required()
def get_camp_staff_salaries(deleted, archive):
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    deleted = deleted.capitalize()
    archive = archive.capitalize()
    if archive != "True":
        salaries = CampStaffSalaries.query.filter(
            CampStaffSalaries.deleted == deleted,
            CampStaffSalaries.month_id == calendar_month.id,
            CampStaffSalaries.year_id == calendar_year.id).order_by(
            CampStaffSalaries.id).all()
    else:
        salaries = CampStaffSalaries.query.filter(
            CampStaffSalaries.deleted == deleted,
        ).order_by(
            CampStaffSalaries.id).all()
    list_salaries = iterate_models(salaries)
    return jsonify({'salaries': list_salaries}), 201
