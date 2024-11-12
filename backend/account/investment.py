import datetime
import pprint

from app import app, request, db, jsonify
from backend.models.models import Investment, AccountingPeriod, CalendarMonth, PaymentTypes
from backend.functions.utils import find_calendar_date, api, refreshdatas, get_json_field
from sqlalchemy import desc
from flask_jwt_extended import jwt_required


@app.route(f'{api}/investment/<int:location_id>', methods=['POST'])
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

    pprint.pprint(data)
    new_investment = Investment(
        name=data['name'],
        amount=data['amount'],
        location_id=location_id,
        calendar_day=calendar_day.id,
        calendar_month=calendar_month.id,
        calendar_year=calendar_year.id,
        account_period_id=accounting_period,
        payment_type_id=data['payment_type_id']
    )
    db.session.add(new_investment)
    db.session.commit()
    return jsonify({'message': 'Investment created successfully'}), 201


@app.route(f'{api}/update_payment_type/<int:id>/<payment_type_id>')
@jwt_required()
def update_payment_type(id, payment_type_id):
    # Fetch the investment record by ID
    investment = Investment.query.get(id)
    payment_type = PaymentTypes.query.filter(PaymentTypes.name == payment_type_id).first()
    if not investment:
        return jsonify({"error": "Investment not found"}), 404

    # Update the payment_type_id
    investment.payment_type_id = payment_type.id
    db.session.commit()

    return jsonify({"message": "Payment type updated successfully", "investment": {
        "id": investment.id,
        "name": investment.name,
        "payment_type_id": investment.payment_type_id
    }}), 200


@app.route(f'{api}/delete_investment/<int:id>', methods=['DELETE'])
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

    return jsonify({"message": "Investment deleted successfully", "investment_id": id}), 200
