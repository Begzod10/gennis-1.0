import datetime

from flask import Blueprint
from flask import request, jsonify
from flask_jwt_extended import jwt_required

from app import db
from backend.functions.utils import find_calendar_date, iterate_models
from backend.models.models import MainOverhead, PaymentTypes
from .utils import update_account

account_overhead_bp = Blueprint('account_overhead_bp', __name__)


@account_overhead_bp.route(f'/account/overhead', methods=['POST'])
@jwt_required()
def account_overhead():
    data = request.get_json()
    day = datetime.datetime.strptime(data['date'], '%Y-%m-%d')
    month = datetime.datetime.strftime(day, '%Y-%m')
    month = datetime.datetime.strptime(month, '%Y-%m')
    year = datetime.datetime.strftime(day, '%Y')
    year = datetime.datetime.strptime(year, '%Y')
    calendar_year, calendar_month, calendar_day = find_calendar_date(date_day=day,
                                                                     date_month=month,
                                                                     date_year=year)

    amount_sum = data['amount']
    payment_type_id = data['type_payment']
    reason = data['reason']

    new_overhead = MainOverhead(
        amount_sum=amount_sum,
        day_id=calendar_day.id,
        month_id=calendar_month.id,
        year_id=calendar_year.id,
        payment_type_id=payment_type_id,
        reason=reason
    )
    db.session.add(new_overhead)
    db.session.commit()
    update_account(payment_type_id)
    return jsonify({
        "success": True,
        "data": new_overhead.convert_json(),
        'message': 'Overhead created successfully'
    }), 200


@account_overhead_bp.route(f'/get_account_overhead/<deleted>/<archive>/', methods=['GET'])
@jwt_required()
def get_account_overhead(deleted, archive):
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    deleted = deleted.capitalize()
    archive = archive.capitalize()
    if archive == "True":
        overheads = MainOverhead.query.filter(MainOverhead.deleted == deleted).order_by(MainOverhead.id).all()
    else:
        overheads = MainOverhead.query.filter(MainOverhead.year_id == calendar_year.id,
                                              MainOverhead.month_id == calendar_month.id,
                                              MainOverhead.deleted == deleted).order_by(MainOverhead.id).all()
    overhead_list = iterate_models(overheads)
    return jsonify({'overheads': overhead_list}), 201


@account_overhead_bp.route(f'/delete_account_overhead/<int:overhead_id>', methods=['DELETE'])
@jwt_required()
def delete_account_overhead(overhead_id):
    overhead = MainOverhead.query.filter(MainOverhead.id == overhead_id).first()
    overhead.deleted = True
    db.session.commit()
    update_account(overhead.payment_type_id)
    return jsonify({
        "success": True,
        "data": overhead.convert_json(),
        'message': 'Overhead deleted successfully'
    })


@account_overhead_bp.route(f'/change_account_overhead/<int:overhead>/<type_id>', methods=['POST'])
@jwt_required()
def change_account_overhead(overhead, type_id):
    payment_type = PaymentTypes.query.filter(PaymentTypes.id == type_id).first()
    overhead_get = MainOverhead.query.filter(MainOverhead.id == overhead).first()
    MainOverhead.query.filter(MainOverhead.id == overhead_get.id).update({
        "payment_type_id": payment_type.id
    })
    db.session.commit()
    update_account(payment_type.id)
    return jsonify({
        "success": True,
        "data": overhead_get.convert_json(),
        "msg": "Xarajat summa turi o'zgartirildi"
    })
