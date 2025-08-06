import datetime

from flask import Blueprint
from flask import request, jsonify
from flask_jwt_extended import jwt_required
from sqlalchemy import desc

from app import db
from backend.functions.utils import find_calendar_date, refreshdatas, get_json_field, iterate_models
from backend.models.models import Investment, AccountingPeriod, CalendarMonth, PaymentTypes, Locations
from .utils import update_account

account_investment = Blueprint('account_investment', __name__)


@account_investment.route(f'/investment/<location_id>/', methods=['POST'])
@jwt_required()
def add_investment(location_id):
    refreshdatas()
    data = request.get_json()
    day = datetime.datetime.strptime(data['date'], '%Y-%m-%d')
    month = datetime.datetime.strftime(day, '%Y-%m')
    month = datetime.datetime.strptime(month, '%Y-%m')
    year = datetime.datetime.strftime(day, '%Y')
    year = datetime.datetime.strptime(year, '%Y')
    calendar_year, calendar_month, calendar_day = find_calendar_date(date_day=day,
                                                                     date_month=month,
                                                                     date_year=year)
    accounting_period = AccountingPeriod.query.join(CalendarMonth).order_by(desc(CalendarMonth.id)).first().id
    if type(location_id) != str:
        location = Locations.query.filter(Locations.id == location_id).first()

        new_investment = Investment(
            name=data['name'],
            amount=data['amount'],
            location_id=location.id,
            calendar_day=calendar_day.id,
            calendar_month=calendar_month.id,
            calendar_year=calendar_year.id,
            account_period_id=accounting_period,
            payment_type_id=data['payment_type_id']
        )
        db.session.add(new_investment)
        db.session.commit()
    else:
        reason = get_json_field('otherReason')
        new_investment = Investment(
            name=data['name'],
            amount=data['amount'],
            calendar_day=calendar_day.id,
            calendar_month=calendar_month.id,
            calendar_year=calendar_year.id,
            account_period_id=accounting_period,
            payment_type_id=data['payment_type_id'],
            reason=reason
        )
        db.session.add(new_investment)
        db.session.commit()
    update_account(data['payment_type_id'])
    return jsonify({'investment': new_investment.convert_json()}), 201


@account_investment.route(f'/get_investments/<deleted>/<archive>/', methods=['GET'])
@jwt_required()
def get_investments(deleted, archive):
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    deleted = deleted.capitalize()
    archive = archive.capitalize()
    if archive == "True":
        investments = Investment.query.filter(Investment.deleted_status == deleted).order_by(
            Investment.id).all()
    else:
        investments = Investment.query.filter(Investment.calendar_year == calendar_year.id,
                                              Investment.calendar_month == calendar_month.id,
                                              Investment.deleted_status == deleted).order_by(
            Investment.id).all()
    investments_list = iterate_models(investments)
    return jsonify({"investments": investments_list})


@account_investment.route(f'/update_payment_type/<int:id>/<payment_type_id>/', methods=['POST'])
@jwt_required()
def update_payment_type(id, payment_type_id):
    # Fetch the investment record by ID
    investment = Investment.query.get(id)
    payment_type = PaymentTypes.query.filter(PaymentTypes.id == payment_type_id).first()
    if not investment:
        return jsonify({"error": "Investment not found"}), 404

    # Update the payment_type_id
    investment.payment_type_id = payment_type.id
    db.session.commit()
    update_account(payment_type.id)
    return jsonify({"message": "Payment type updated successfully", "investment": investment.convert_json()}), 200


@account_investment.route(f'/delete_investment/<int:id>/', methods=['DELETE'])
@jwt_required()
def delete_investment(id):
    # Fetch the investment record by ID
    reason = get_json_field('otherReason')
    investment = Investment.query.get(id)

    if not investment:
        return jsonify({"error": "Investment not found"}), 404

    # Delete the investment record
    investment.deleted_status = True
    investment.reason = reason
    db.session.commit()
    update_account(investment.payment_type_id)
    return jsonify({"message": "Investment deleted successfully", "investment_id": id}), 200
