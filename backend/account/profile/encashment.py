from app import db, app, request, jsonify, func
from backend.models.models import MainOverhead, CalendarDay, AccountReport, CampStaffSalaries, Dividend, PaymentTypes, \
    and_, CalendarYear
from backend.functions.utils import api, find_calendar_date, desc, contains_eager, iterate_models
from flask_jwt_extended import jwt_required
from datetime import datetime


@app.route(f'{api}/encashment/<location_id>', methods=['POST'])
@jwt_required()
def encashment(location_id):
    ot = request.get_json()['ot']
    do = request.get_json()['do']
    ot = datetime.strptime(ot, "%Y-%m-%d")
    do = datetime.strptime(do, "%Y-%m-%d")
    activeFilter = request.get_json()['activeFilter']
    payment_type = PaymentTypes.query.filter(PaymentTypes.name == activeFilter).first()
    dividends = db.session.query(Dividend).join(Dividend.day).options(
        contains_eager(Dividend.day)).filter(
        and_(CalendarDay.date >= ot, CalendarDay.date <= do, Dividend.location_id == location_id,
             Dividend.payment_type_id == payment_type.id,
             )).order_by(
        desc(Dividend.id)).all()
    all_dividend = db.session.query(
        func.sum(Dividend.amount_sum)).join(CalendarDay,
                                            CalendarDay.id == Dividend.day_id).filter(
        and_(CalendarDay.date >= ot, CalendarDay.date <= do, Dividend.location_id == location_id,
             Dividend.payment_type_id == payment_type.id,
             )).first()[0] if dividends else 0

    salaries = db.session.query(CampStaffSalaries).join(Dividend.day).options(
        contains_eager(CampStaffSalaries.day)).filter(
        and_(CalendarDay.date >= ot, CalendarDay.date <= do,
             CampStaffSalaries.payment_type_id == payment_type.id
             )).order_by(
        desc(CampStaffSalaries.id)).all()

    all_salary = db.session.query(
        func.sum(CampStaffSalaries.amount_sum)).join(CalendarDay,
                                                     CalendarDay.id == CampStaffSalaries.day_id).filter(
        and_(CalendarDay.date >= ot, CalendarDay.date <= do,
             CampStaffSalaries.payment_type_id == payment_type.id
             )).first()[0] if salaries else 0

    overheads = db.session.query(MainOverhead).join(MainOverhead.day).options(
        contains_eager(MainOverhead.day)).filter(
        and_(CalendarDay.date >= ot, CalendarDay.date <= do,
             MainOverhead.payment_type_id == payment_type.id
             )).order_by(
        desc(MainOverhead.id)).all()
    all_overheads = db.session.query(
        func.sum(MainOverhead.amount_sum)).join(CalendarDay,
                                                CalendarDay.id == MainOverhead.day_id).filter(
        and_(CalendarDay.date >= ot, CalendarDay.date <= do,
             MainOverhead.payment_type_id == payment_type.id
             )).first()[0] if overheads else 0

    result = all_dividend - (all_salary + all_overheads)

    return jsonify({
        'all_dividend': all_dividend,
        'all_salary': all_salary,
        "all_overheads": all_overheads,
        "overheads": iterate_models(overheads),
        "dividends": iterate_models(dividends),
        "salaries": iterate_models(salaries),
        'result': result
    }), 200


@app.route(f'{api}/account_report')
@jwt_required()
def get_account_report():
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    account_reports = AccountReport.query.filter(AccountReport.year_id == calendar_year.id,
                                                 AccountReport.month_id == calendar_month.id).order_by(
        AccountReport.id).all()
    return jsonify({'account_reports': iterate_models(account_reports)}), 200


@app.route(f'{api}/account_report_datas/')
@jwt_required()
def get_account_report_datas():
    account_reports = AccountReport.query.order_by(AccountReport.id).all()
    data = []
    seen_values = set()  # To track unique year_id values

    for report in account_reports:
        if report.year_id not in seen_values:  # Check for uniqueness
            calendar_year = CalendarYear.query.filter(CalendarYear.id == report.year_id).first()
            if calendar_year:  # Ensure calendar_year exists
                info = {
                    "value": report.year_id,
                    "name": calendar_year.date.strftime("%Y")
                }
                data.append(info)
                seen_values.add(report.year_id)  # Mark the value as seen

    print(data)

    return jsonify({'date': data}), 200


@app.route(f'{api}/account_report_filter/', methods=['POST'])
@jwt_required()
def get_account_report_filter():
    data = request.get_json()
    year_id = data['year_id']
    payment_type_id = data['payment_type_id']
    account_reports = AccountReport.query.filter(AccountReport.year_id == year_id,
                                                 AccountReport.payment_type_id == payment_type_id).order_by(
        AccountReport.id).all()
    return jsonify({'account_reports': iterate_models(account_reports)}), 200
