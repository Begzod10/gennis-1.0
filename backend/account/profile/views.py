from app import app, request, db, jsonify
from backend.models.models import Users, Dividend, AccountPayable, CampStaff, PhoneList, Roles, Professions, \
    CalendarDay, CalendarMonth, CalendarYear, CampStaffSalary
from backend.functions.utils import api, find_calendar_date, refreshdatas
from flask_jwt_extended import jwt_required, get_jwt_identity
import datetime
from werkzeug.security import generate_password_hash
from datetime import datetime
from sqlalchemy import extract
from datetime import date

import datetime


@app.route(f'{api}/take_dividend', methods=['POST'])
@jwt_required()
def take_dividend():
    data = request.get_json()
    day = datetime.datetime.strptime(data['date'], '%Y-%m-%d')
    month = datetime.datetime.strptime(day.strftime('%Y-%m'), '%Y-%m')
    year = datetime.datetime.strptime(day.strftime('%Y'), '%Y')
    calendar_year, calendar_month, calendar_day = find_calendar_date(
        date_day=day,
        date_month=month,
        date_year=year
    )

    location_id = data['locations']
    amount_sum = data['amount']
    payment_type_id = data['type_payment']
    desc = data['desc']

    new_dividend = Dividend(
        amount_sum=amount_sum,
        location_id=location_id,
        day_id=calendar_day.id,
        month_id=calendar_month.id,
        year_id=calendar_year.id,
        payment_type_id=payment_type_id,
        desc=desc
    )
    db.session.add(new_dividend)
    db.session.commit()
    new_dividend = Dividend.query.filter(Dividend.id == new_dividend.id).first()
    day = CalendarDay.query.filter(CalendarDay.id == new_dividend.day_id).first()
    dividend = {"amount": new_dividend.amount_sum, "payment_type": {
        'name': new_dividend.payment_type.name,
        'id': new_dividend.payment_type.id,
    },
                "location": new_dividend.location.name, "id": new_dividend.id,
                "date": day.date.strftime('%Y-%m-%d'), }
    return jsonify({'dividend': dividend}), 201


@app.route(f'{api}/crud_dividend/<int:pk>', methods=['POST'])
@jwt_required()
def crud_dividend(pk):
    data = request.get_json()
    payment_type_id = data['payment_type_id']
    dividend = Dividend.query.filter(Dividend.id == pk).first()
    dividend.payment_type_id = payment_type_id
    db.session.commit()
    return jsonify(
        {"payment_type": {'name': dividend.payment_type.name, 'id': dividend.payment_type.id, }}), 201


@app.route(f'{api}/delete_dividend/<int:pk>', methods=['POST'])
@jwt_required()
def delete_dividend(pk):
    data = request.get_json()
    deleted_comment = data['otherReason']
    dividend = Dividend.query.filter(Dividend.id == pk).first()
    dividend.deleted = True
    dividend.deleted_comment = deleted_comment
    db.session.commit()
    return jsonify({'message': 'Dividend deleted successfully'}), 201


@app.route(f'{api}/get_dividend/<int:location_id>', methods=['GET'])
@jwt_required()
def get_dividend(location_id):
    dividends = Dividend.query.filter(Dividend.location_id == location_id, Dividend.deleted == False).order_by(
        Dividend.id).all()
    dividend_list = [
        {"amount": dividend.amount_sum, "payment_type": {
            'name': dividend.payment_type.name,
            'id': dividend.payment_type.id,
        },
         "location": dividend.location.name,
         "id": dividend.id,
         "date": CalendarDay.query.filter(CalendarDay.id == dividend.day_id).first().date.strftime('%Y-%m-%d'), } for
        dividend in dividends]
    return jsonify({'dividends': dividend_list}), 201


@app.route(f'{api}/add_account_payable', methods=['POST'])
@jwt_required()
def add_account_payable():
    data = request.get_json()
    day = datetime.datetime.strptime(data['date'], '%Y-%m-%d')
    month = datetime.datetime.strftime(day, '%Y-%m')
    month = datetime.datetime.strptime(month, '%Y-%m')
    year = datetime.datetime.strftime(day, '%Y')
    year = datetime.datetime.strptime(year, '%Y')
    calendar_year, calendar_month, calendar_day = find_calendar_date(date_day=day,
                                                                     date_month=month,
                                                                     date_year=year)
    location_id = None
    if 'location_id' in data:
        location_id = data['location_id']
    amount_sum = data['amount_sum']
    payment_type_id = data['type_payment']
    desc = data['desc']
    status = data['debtor']
    new_account_payable = AccountPayable(
        amount_sum=amount_sum,
        location_id=location_id,
        day_id=calendar_day.id,
        status=bool(status),
        month_id=calendar_month.id,
        year_id=calendar_year.id,
        payment_type_id=payment_type_id,
        desc=desc
    )
    db.session.add(new_account_payable)
    db.session.commit()
    new_dividend = AccountPayable.query.filter(AccountPayable.id == new_account_payable.id).first()
    dividend = {"amount": new_dividend.amount_sum, "desc": new_dividend.desc, "payment_type": {
        'name': new_dividend.payment_type.name,
        'id': new_dividend.payment_type.id,
    },
                "location": new_dividend.location.name, "id": new_dividend.id, "debtor": new_dividend.status,
                "date": CalendarDay.query.filter(CalendarDay.id == new_dividend.day_id).first().date.strftime(
                    '%Y-%m-%d'), }
    return jsonify({'account_payable': dividend}), 201


@app.route(f'{api}/get_account_payable/<int:location_id>', methods=['GET'])
@jwt_required()
def get_account_payable(location_id):
    account_payables = AccountPayable.query.filter(AccountPayable.location_id == location_id,
                                                   AccountPayable.deleted == False).order_by(
        AccountPayable.id).all()
    dividend_list = [
        {"amount": account_payable.amount_sum, "payment_type": {
            'name': account_payable.payment_type.name,
            'id': account_payable.payment_type.id,
        },
         "location": account_payable.location.name, "id": account_payable.id, "debtor": account_payable.status,
         "desc": account_payable.desc,
         "date": CalendarDay.query.filter(CalendarDay.id == account_payable.day_id).first().date.strftime(
             '%Y-%m-%d'), } for
        account_payable in account_payables]
    return jsonify({'account_payables': dividend_list}), 201


@app.route(f'{api}/crud_account_payable/<int:pk>', methods=['POST'])
@jwt_required()
def crud_account_payable(pk):
    data = request.get_json()
    payment_type_id = data['payment_type_id']
    account_payable = AccountPayable.query.filter(AccountPayable.id == pk).first()
    account_payable.payment_type_id = payment_type_id
    db.session.commit()
    return jsonify(
        {"payment_type": {'name': account_payable.payment_type.name, 'id': account_payable.payment_type.id, }}), 201


@app.route(f'{api}/delete_account_payable/<int:pk>', methods=['POST'])
@jwt_required()
def delete_account_payable(pk):
    data = request.get_json()
    deleted_comment = data['otherReason']
    dividend = AccountPayable.query.filter(AccountPayable.id == pk).first()
    dividend.deleted = True
    dividend.deleted_comment = deleted_comment
    db.session.commit()
    return jsonify({'message': 'Dividend deleted successfully'}), 201


@app.route(f'{api}/get_staff_salary', methods=['GET'])
@jwt_required()
def get_staff_salary():
    staff_salarys = CampStaffSalary.query.order_by(CampStaffSalary.id).all()
    dividend_list = [
        {"salary": staff_salary.amount_sum, "date": staff_salary.month.date,
         "desc": staff_salary.desc} for
        staff_salary in staff_salarys]
    return jsonify({'dividends': dividend_list}), 201


def find_calendar_date2(date_day=None, date_month=None, date_year=None):
    """Find or create calendar date entities."""
    if date_day and date_month and date_year:
        year = CalendarYear.query.filter(extract('year', CalendarYear.date) == date_year).first()
        if not year:
            year = CalendarYear(date=date(date_year, 1, 1))
            db.session.add(year)
            db.session.commit()

        month = CalendarMonth.query.filter(
            extract('year', CalendarMonth.date) == date_year,
            extract('month', CalendarMonth.date) == date_month
        ).first()
        if not month:
            month = CalendarMonth(date=date(date_year, date_month, 1),
                                  year_id=year.id)  # Set the first day of the month
            db.session.add(month)
            db.session.commit()

        day = CalendarDay.query.filter(
            extract('year', CalendarDay.date) == date_year,
            extract('month', CalendarDay.date) == date_month,
            extract('day', CalendarDay.date) == date_day
        ).first()
        if not day:
            day = CalendarDay(date=date(date_year, date_month, date_day), month_id=month.id)
            db.session.add(day)
            db.session.commit()

        return year, month, day

    today = date.today()
    return find_calendar_date(today.day, today.month, today.year)


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
        phone = data['phone']
        born_year, born_month, born_day = map(int, data['birth_date'].split('-'))
        calendar_year, calendar_month, calendar_day = find_calendar_date2(
            date_day=born_day,
            date_month=born_month,
            date_year=born_year
        )
        user = Users(
            name=name,
            surname=surname,
            username=username,
            password=password,
            role_id=role_id,
            father_name=father_name,
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
            role_id=role_id
        )
        staff_camp.add()
        return jsonify({'message': 'Campus Staff registered successfully'}), 201
    else:
        camps = CampStaff.query.filter(CampStaff.deleted == False).order_by(CampStaff.id).all()
        camp_list = [
            {"name": camp.user.name, "surname": camp.user.surname, "username": camp.user.username,
             "age": camp.user.age, "role": Roles.query.filter(Roles.id == camp.user.role_id).first().type_role,
             "phone": PhoneList.query.filter(Users.id == camp.user.id).first().phone} for
            camp in camps]
        return jsonify({'staffs': camp_list}), 201


@app.route(f'{api}/roles', methods=['GET'])
@jwt_required()
def get_roles():
    roles = Roles.query.order_by(Roles.id).all()
    roles = [{'id': location.id, "name": location.type_role} for location in roles]
    return jsonify({'roles': roles}), 201
