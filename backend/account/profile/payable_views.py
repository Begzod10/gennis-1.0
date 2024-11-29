from flask import jsonify, request
from flask_jwt_extended import jwt_required
from app import app, db
from backend.models.models import AccountPayable, CalendarDay, CalendarMonth, CalendarYear
from backend.functions.utils import api, find_calendar_date, iterate_models
import datetime
from .utils import update_account


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
    update_account()
    return jsonify({'account_payable': new_account_payable.convert_json()}), 201


@app.route(f'{api}/get_account_payable/<int:location_id>/<deleted>/<archive>/', methods=['GET'])
@jwt_required()
def get_account_payable(location_id, deleted, archive):
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    deleted = deleted.capitalize()
    archive = archive.capitalize()
    if archive != "True":
        account_payables = AccountPayable.query.filter(AccountPayable.location_id == location_id,
                                                       AccountPayable.deleted == deleted).order_by(
            AccountPayable.id).all()
    else:
        account_payables = AccountPayable.query.filter(AccountPayable.location_id == location_id,
                                                       AccountPayable.year_id == calendar_year.id,
                                                       AccountPayable.month_id == calendar_month.id,
                                                       AccountPayable.deleted == deleted).order_by(
            AccountPayable.id).all()
    dividend_list = iterate_models(account_payables)
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
