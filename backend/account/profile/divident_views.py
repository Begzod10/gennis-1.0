from app import app, db
from flask import request, jsonify
from flask_jwt_extended import jwt_required
import datetime
from backend.functions.utils import api, find_calendar_date, iterate_models
from backend.models.models import Dividend, AccountingPeriod, CalendarDay, CalendarMonth, CalendarYear
from .utils import update_account, payable_sum_calculate
from app import desc as dc


@app.route(f'{api}/take_dividend', methods=['POST'])
@jwt_required()
def take_dividend():
    data = request.get_json()
    accounting_period = AccountingPeriod.query.join(CalendarMonth).order_by(dc(CalendarMonth.id)).first().id
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
        account_period_id=accounting_period,
        desc=desc
    )
    db.session.add(new_dividend)
    db.session.commit()
    payable_sum_calculate(calendar_year.id, calendar_month.id, payment_type_id)
    return jsonify({'dividend': new_dividend.convert_json()}), 201


@app.route(f'{api}/crud_dividend/<int:pk>', methods=['POST'])
@jwt_required()
def crud_dividend(pk):
    data = request.get_json()
    payment_type_id = data['payment_type_id']
    dividend = Dividend.query.filter(Dividend.id == pk).first()
    dividend.payment_type_id = payment_type_id
    db.session.commit()
    update_account()
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
    update_account()
    return jsonify({'message': 'Dividend deleted successfully'}), 201


@app.route(f'{api}/get_dividend/<deleted>/<archive>/', methods=['GET'])
@jwt_required()
def get_dividend(deleted, archive):
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    deleted = deleted.capitalize()
    archive = archive.capitalize()
    if archive != "True":
        dividends = Dividend.query.filter(Dividend.deleted == deleted).order_by(
            Dividend.id).all()
    else:
        dividends = Dividend.query.filter(Dividend.year_id == calendar_year.id, Dividend.month_id == calendar_month.id,
                                          Dividend.deleted == deleted).order_by(
            Dividend.id).all()
    dividend_list = iterate_models(dividends)
    return jsonify({'dividends': dividend_list}), 201
