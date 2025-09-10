from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import desc
from sqlalchemy import func

from app import db
from backend.functions.utils import iterate_models, find_calendar_date
from backend.models.models import StudentPayments, Investment, CalendarYear, Overhead, Capital, TeacherSalaries, \
    StaffSalaries, Dividend, MainOverhead, AccountPayable, CampStaffSalaries, AccountPayableHistory

account_debit_credit = Blueprint('account_debit_credit', __name__)


@account_debit_credit.route(f'/month_years_calendar', methods=['POST', 'GET'])
@jwt_required()
def month_years_calendar():
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    years = CalendarYear.query.filter(CalendarYear.date >= '2021-01-01').order_by(desc(CalendarYear.date)).all()
    return jsonify({
        'years': iterate_models(years),
        "month": calendar_month.convert_json(),
        "year": calendar_year.convert_json()
    })


@account_debit_credit.route(f'/debit_credit/<int:location_id>', methods=['POST', 'GET'])
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
        Capital.calendar_year == year_id,
        Capital.deleted == False
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
        StaffSalaries.calendar_year == year_id,

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


@account_debit_credit.route(f'/debit_credit_account', methods=['POST', 'GET'])
@jwt_required()
def debit_credit_all():
    data = request.get_json()
    month_id = data['month_id']
    year_id = data['years_id']
    payment_type = data['payment_type_id']

    dividend_query = Dividend.query.filter(
        Dividend.payment_type_id == payment_type,
        Dividend.month_id == month_id,
        Dividend.year_id == year_id,
        Dividend.deleted == False
    ).all()

    overhead_query = MainOverhead.query.filter(
        MainOverhead.payment_type_id == payment_type,
        MainOverhead.month_id == month_id,
        MainOverhead.year_id == year_id,
        MainOverhead.deleted == False
    ).all()

    payable_query = AccountPayable.query.filter(
        AccountPayable.payment_type_id == payment_type,
        AccountPayable.month_id == month_id,
        AccountPayable.year_id == year_id,
        AccountPayable.type_account == "payable",
        AccountPayable.deleted == False
    ).all()
    receivables_query = AccountPayable.query.filter(
        AccountPayable.payment_type_id == payment_type,
        AccountPayable.month_id == month_id,
        AccountPayable.year_id == year_id,
        AccountPayable.type_account == "receivable",
        AccountPayable.deleted == False
    ).all()
    investments = Investment.query.filter(
        Investment.payment_type_id == payment_type,
        Investment.calendar_month == month_id,
        Investment.calendar_year == year_id,
        Investment.deleted_status == False,
    ).all()
    camp_staff_salaries = CampStaffSalaries.query.filter(
        CampStaffSalaries.payment_type_id == payment_type,
        CampStaffSalaries.month_id == month_id,
        CampStaffSalaries.year_id == year_id,
        CampStaffSalaries.deleted == False
    ).all()
    sub_account_payable = AccountPayableHistory.query.filter(
        AccountPayableHistory.payment_type_id == payment_type,
        AccountPayableHistory.month_id == month_id,
        AccountPayableHistory.year_id == year_id,
        AccountPayableHistory.deleted == False,
        AccountPayableHistory.type_account == "payable"
    ).all()
    sub_account_receivables = AccountPayableHistory.query.filter(
        AccountPayableHistory.payment_type_id == payment_type,
        AccountPayableHistory.month_id == month_id,
        AccountPayableHistory.year_id == year_id,
        AccountPayableHistory.deleted == False,
        AccountPayableHistory.type_account == "receivable"
    ).all()

    dividend_query_total = \
        db.session.query(func.sum(Dividend.amount_sum)).filter(
            Dividend.payment_type_id == payment_type,
            Dividend.month_id == month_id,
            Dividend.year_id == year_id,
            Dividend.deleted == False
        ).first()[0]

    overhead_query_total = \
        db.session.query(func.sum(MainOverhead.amount_sum)).filter(
            MainOverhead.payment_type_id == payment_type,
            MainOverhead.month_id == month_id,
            MainOverhead.year_id == year_id,
            MainOverhead.deleted == False
        ).first()[0]
    payable_query_total = \
        db.session.query(func.sum(AccountPayable.amount_sum)).filter(
            AccountPayable.payment_type_id == payment_type,
            AccountPayable.month_id == month_id,
            AccountPayable.year_id == year_id,
            AccountPayable.type_account == "payable",
            AccountPayable.deleted == False
        ).first()[0]
    receivables_query_total = \
        db.session.query(func.sum(AccountPayable.amount_sum)).filter(
            AccountPayable.payment_type_id == payment_type,
            AccountPayable.month_id == month_id,
            AccountPayable.year_id == year_id,
            AccountPayable.type_account == "receivable",
            AccountPayable.deleted == False
        ).first()[0]

    investments_total = \
        db.session.query(func.sum(Investment.amount)).filter(
            Investment.calendar_year == year_id,
            Investment.calendar_month == month_id,
            Investment.deleted_status != True,
            Investment.payment_type_id == payment_type).first()[0]

    camp_staff_salaries_total = \
        db.session.query(func.sum(CampStaffSalaries.amount_sum)).filter(
            CampStaffSalaries.year_id == year_id,
            CampStaffSalaries.month_id == month_id,
            CampStaffSalaries.deleted != True,
            CampStaffSalaries.payment_type_id == payment_type).first()[0]

    sub_account_payable_total = \
        db.session.query(func.sum(AccountPayableHistory.sum)).filter(
            AccountPayableHistory.year_id == year_id,
            AccountPayableHistory.month_id == month_id,
            AccountPayableHistory.deleted != True,
            AccountPayableHistory.payment_type_id == payment_type,
            AccountPayableHistory.type_account == "payable").first()[0]

    sub_account_receivables_total = \
        db.session.query(func.sum(AccountPayableHistory.sum)).filter(
            AccountPayableHistory.year_id == year_id,
            AccountPayableHistory.month_id == month_id,
            AccountPayableHistory.deleted != True,
            AccountPayableHistory.payment_type_id == payment_type,
            AccountPayableHistory.type_account == "receivable").first()[0]
    dividend_query_total = dividend_query_total if dividend_query_total is not None else 0
    overhead_query_total = overhead_query_total if overhead_query_total is not None else 0
    payable_query_total = payable_query_total if payable_query_total is not None else 0
    receivables_query_total = receivables_query_total if receivables_query_total is not None else 0
    investments_total = investments_total if investments_total is not None else 0
    camp_staff_salaries_total = camp_staff_salaries_total if camp_staff_salaries_total is not None else 0
    sub_account_payable_total = sub_account_payable_total if sub_account_payable_total is not None else 0
    sub_account_receivables_total = sub_account_receivables_total if sub_account_receivables_total is not None else 0

    left_total = dividend_query_total + receivables_query_total + sub_account_receivables_total
    right_total = overhead_query_total + payable_query_total + investments_total + camp_staff_salaries_total + sub_account_payable_total

    total = left_total - right_total

    return jsonify(
        {'left': iterate_models(dividend_query) + iterate_models(receivables_query) + iterate_models(
            sub_account_receivables),
         "right": iterate_models(overhead_query) + iterate_models(payable_query) + iterate_models(
             investments) + iterate_models(camp_staff_salaries) + iterate_models(sub_account_payable),
         "left_total": left_total,
         "right_total": right_total,
         "overall": total}
    )
