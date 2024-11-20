from app import app, request, db, jsonify
from backend.models.models import Users, Dividend, AccountPayable, CampStaff, PhoneList, Roles, Professions
from backend.functions.utils import api, find_calendar_date
from flask_jwt_extended import jwt_required, get_jwt_identity
import datetime
from werkzeug.security import generate_password_hash


@app.route(f'{api}/take_dividend', methods=['POST'])
@jwt_required()
def take_dividend():
    data = request.get_json()
    day = datetime.datetime.strptime(data['date'], '%Y-%m-%d')
    month = datetime.datetime.strftime(day, '%Y-%m')
    month = datetime.datetime.strptime(month, '%Y-%m')
    year = datetime.datetime.strftime(day, '%Y')
    year = datetime.datetime.strptime(year, '%Y')
    calendar_year, calendar_month, calendar_day = find_calendar_date(date_day=day,
                                                                     date_month=month,
                                                                     date_year=year)
    location_id = data['location_id']
    amount_sum = data['amount_sum']
    payment_type_id = data['payment_type_id']
    desc = data['desc']
    new_dividend = Dividend(
        amount_sum=amount_sum,
        location_id=location_id,
        calendar_day=calendar_day.id,
        calendar_month=calendar_month.id,
        calendar_year=calendar_year.id,
        payment_type_id=payment_type_id,
        desc=desc
    )
    db.session.add(new_dividend)
    db.session.commit()
    return jsonify({'message': 'Dividend created successfully'}), 201


@app.route(f'{api}/crud_dividend/<int:pk>', methods=['POST', 'DELETE'])
@jwt_required()
def crud_dividend(pk):
    if request.method == 'POST':
        data = request.get_json()
        payment_type_id = data['payment_type_id']
        dividend = Dividend.query.filter(Dividend.id == pk).first()
        dividend.payment_type_id = payment_type_id
        db.session.commit()
        return jsonify({'message': 'Dividend updated successfully'}), 201
    else:
        dividend = Dividend.query.filter(Dividend.id == pk).first()
        db.session.delete(dividend)
        db.session.commit()
        return jsonify({'message': 'Dividend deleted successfully'}), 201


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
    payment_type_id = data['payment_type_id']
    desc = data['desc']
    new_account_payable = AccountPayable(
        amount_sum=amount_sum,
        location_id=location_id,
        calendar_day=calendar_day.id,
        calendar_month=calendar_month.id,
        calendar_year=calendar_year.id,
        payment_type_id=payment_type_id,
        desc=desc
    )
    db.session.add(new_account_payable)
    db.session.commit()
    return jsonify({'message': 'Account Payable created successfully'}), 201


@app.route(f'{api}/crud_account_payable/<int:pk>', methods=['POST', 'DELETE'])
@jwt_required()
def crud_account_payable(pk):
    if request.method == 'POST':
        data = request.get_json()
        payment_type_id = data['payment_type_id']
        account_payable = AccountPayable.query.filter(AccountPayable.id == pk).first()
        account_payable.payment_type_id = payment_type_id
        db.session.commit()
        return jsonify({'message': 'Account Payable updated successfully'}), 201
    else:
        account_payable = AccountPayable.query.filter(AccountPayable.id == pk).first()
        db.session.delete(account_payable)
        db.session.commit()
        return jsonify({'message': 'Account Payable deleted successfully'}), 201


@app.route(f'{api}/register_camp_staff', methods=['POST', "GET"])
@jwt_required()
def register_camp_staff():
    if request.method == 'POST':
        data = request.get_json()
        name = data['name']
        surname = data['surname']
        username = data['username']
        password = generate_password_hash(data['password'])
        role_id = data['role_id']
        profession_id = data['profession_id']
        father_name = data['father_name']
        phone = data['phone']
        born_day = data['born_day']
        born_month = data['born_month']
        born_year = data['born_year']
        calendar_day, calendar_month, calendar_year = find_calendar_date()
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
            profession_id=profession_id
        )
        staff_camp.add()
        return jsonify({'message': 'Campus Staff registered successfully'}), 201
    else:
        roles = Roles.query.order_by(Roles.id).all()
        professions = Professions.query.order_by(Professions.id).all()
        return jsonify({'roles': roles, 'professions': professions}), 201


@app.route(f'{api}/roles', methods=['GET'])
@jwt_required()
def get_roles():
    roles = Roles.query.order_by(Roles.id).all()
    roles = [{'id': location.id, "name": location.type_role} for location in roles]
    return jsonify({'roles': roles}), 201
