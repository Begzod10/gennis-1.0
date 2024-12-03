from flask_jwt_extended import jwt_required
from sqlalchemy import desc

from app import app, jsonify, request
from backend.functions.utils import api
from backend.functions.utils import iterate_models
from backend.models.models import StudentPayments, Investment, CalendarYear, Overhead, Capital, TeacherSalaries, \
    StaffSalaries, Dividend, MainOverhead


@app.route(f'{api}/month_years_calendar', methods=['POST', 'GET'])
@jwt_required()
def month_years_calendar():
    years = CalendarYear.query.order_by(desc(CalendarYear.id)).all()
    return jsonify({'years': iterate_models(years)})


@app.route(f'{api}/debit_credit/<int:location_id>', methods=['POST', 'GET'])
@jwt_required()
def debit_credit(location_id):
    data = request.get_json()
    month_id = data['month_id']
    year_id = data['years_id']
    payment_type = data['payment_type_id']
    student_payments = StudentPayments.query.filter(
        StudentPayments.payment == True,
        StudentPayments.location_id == location_id,
        StudentPayments.payment_type_id == payment_type,
        StudentPayments.calendar_month == month_id,
        StudentPayments.calendar_year == year_id
    ).all()
    investments = Investment.query.filter(
        Investment.deleted_status == False,
        Investment.location_id == location_id,
        Investment.payment_type_id == payment_type,
        Investment.calendar_month == month_id,
        Investment.calendar_year == year_id
    ).all()
    overhead = Overhead.query.filter(
        Overhead.location_id == location_id,
        Overhead.payment_type_id == payment_type,
        Overhead.calendar_month == month_id,
        Overhead.calendar_year == year_id
    ).all()
    capital = Capital.query.filter(
        Capital.location_id == location_id,
        Capital.payment_type_id == payment_type,
        Capital.calendar_month == month_id,
        Capital.calendar_year == year_id
    ).all()
    teacher_salaries = TeacherSalaries.query.filter(
        TeacherSalaries.location_id == location_id,
        TeacherSalaries.payment_type_id == payment_type,
        TeacherSalaries.calendar_month == month_id,
        TeacherSalaries.calendar_year == year_id
    ).all()
    staff_salaries = StaffSalaries.query.filter(
        StaffSalaries.location_id == location_id,
        StaffSalaries.payment_type_id == payment_type,
        StaffSalaries.calendar_month == month_id,
        StaffSalaries.calendar_year == year_id
    ).all()
    left = (
            iterate_models(student_payments) +
            iterate_models(investments)
    )
    right = (
            iterate_models(teacher_salaries) +
            iterate_models(staff_salaries) +
            iterate_models(capital) +
            iterate_models(overhead)
    )
    left_total = sum(item['amount'] for item in left)
    right_total = sum(item['amount'] for item in right)
    overall = left_total - right_total
    return jsonify({
        'left': left,
        'right': right,
        'left_total': left_total,
        'right_total': right_total,
        'overall': overall
    })


@app.route(f'{api}/debit_credit_account', methods=['POST', 'GET'])
@jwt_required()
def debit_credit_all():
    data = request.get_json()
    month_id = data['month_id']
    year_id = data['years_id']
    payment_type = data['payment_type_id']
    dividend = Dividend.query.filter(
        Dividend.payment_type_id == payment_type,
        Dividend.month_id == month_id,
        Dividend.year_id == year_id
    ).all()
    dividend_list = iterate_models(dividend)
    overhead = MainOverhead.query.filter(
        MainOverhead.payment_type_id == payment_type,
        MainOverhead.month_id == month_id,
        MainOverhead.year_id == year_id
    ).all()
    overhead = iterate_models(overhead)
    left_total = sum(item['amount'] for item in dividend_list)
    right_total = sum(item['amount_sum'] for item in overhead)
    total = left_total - right_total
    return jsonify(
        {'left': dividend_list, "right": overhead, "left_total": left_total, "right_total": right_total, "overall": total})
