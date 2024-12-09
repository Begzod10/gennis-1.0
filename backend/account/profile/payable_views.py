from flask import jsonify, request
from flask_jwt_extended import jwt_required
from app import app, db
from backend.models.models import AccountPayable, CalendarDay, CalendarMonth, CalendarYear, Account, \
    AccountPayableHistory
from backend.functions.utils import api, find_calendar_date, iterate_models
import datetime
from .utils import update_account, payable_sum_calculate, calculate_history


@app.route(f'{api}/get_accounts', methods=['GET'])
@jwt_required()
def get_accounts():
    accounts = Account.query.all()
    account_list = iterate_models(accounts)
    return jsonify({"accounts": account_list}), 201


@app.route(f'{api}/create_account', methods=['POST', 'GET'])
@jwt_required()
def create_account():
    data = request.get_json()
    account = Account(name=data['name'])
    account.add()
    return jsonify({'account': account.convert_json()}), 201


@app.route(f'{api}/delete_account/<int:id>/', methods=['DELETE'])
@jwt_required()
def delete_account(id):
    account = Account.query.filter(Account.id == id).first()
    account.delete()
    return jsonify({'message': 'Account deleted successfully'}), 201


@app.route(f'{api}/account_profile/<int:id>/', methods=['GET'])
@jwt_required()
def account_profile(id):
    account = Account.query.filter(Account.id == id).first()
    return jsonify({'account': account.convert_json()}), 201


@app.route(f'{api}/crud_account/<int:id>/', methods=['POST'])
@jwt_required()
def crud_account(id):
    data = request.get_json()
    account = Account.query.filter(Account.id == id).first()
    account.name = data['name']
    db.session.commit()
    return jsonify({'account': account.convert_json()}), 201


@app.route(f'{api}/payable_datas/<int:id>/', methods=['GET'])
@jwt_required()
def payable_datas(id):
    payables = AccountPayable.query.filter(AccountPayable.account_id == id).order_by(
        AccountPayable.id).all()
    month_ids = {payable.month_id for payable in payables}
    years_ids = {payable.year_id for payable in payables}
    months = CalendarMonth.query.filter(CalendarMonth.id.in_(month_ids)).order_by(CalendarMonth.date).all()
    years = CalendarYear.query.filter(CalendarYear.id.in_(years_ids)).order_by(CalendarYear.date).all()
    return jsonify({"years": iterate_models(years), "months": iterate_models(months)})


@app.route(f'{api}/account_payables/<int:id>/<int:month_id>/<deleted>/<archive>/', methods=['POST', 'GET'])
@jwt_required()
def account_payables(id, month_id, deleted, archive):
    deleted = deleted.capitalize()
    archive = archive.capitalize()
    if archive != "True":
        payables = AccountPayable.query.filter(AccountPayable.account_id == id,
                                               AccountPayable.deleted == deleted).order_by(AccountPayable.id).all()
    else:
        payables = AccountPayable.query.filter(AccountPayable.account_id == id,
                                               AccountPayable.month_id == month_id,
                                               AccountPayable.deleted == deleted).order_by(AccountPayable.id).all()
    return jsonify({"payables": iterate_models(payables)})


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

    amount_sum = data['amount_sum']
    payment_type_id = data['type_payment']
    desc = data['desc']
    status = data['status']
    new_account_payable = AccountPayable(
        account_id=data['account_id'],
        amount_sum=amount_sum,
        day_id=calendar_day.id,
        status=bool(status),
        month_id=calendar_month.id,
        year_id=calendar_year.id,
        payment_type_id=payment_type_id,
        desc=desc,
        remaining_sum=amount_sum
    )
    db.session.add(new_account_payable)
    db.session.commit()
    update_account()
    payable_sum_calculate(calendar_year.id, calendar_month.id, payment_type_id)
    return jsonify({'account_payable': new_account_payable.convert_json()}), 201


@app.route(f'{api}/get_payable_histories/<int:id>/', methods=['GET'])
@jwt_required()
def get_payable_histories(id):
    histories = AccountPayableHistory.query.filter(AccountPayableHistory.account_payable_id == id).all()
    return jsonify({"histories": iterate_models(histories)})


@app.route(f'{api}/create_payable_history/<int:payable_id>/', methods=['POST'])
@jwt_required()
def create_payable_history(payable_id):
    data = request.get_json()
    day = datetime.datetime.strptime(data['date'], '%Y-%m-%d')
    month = datetime.datetime.strftime(day, '%Y-%m')
    month = datetime.datetime.strptime(month, '%Y-%m')
    year = datetime.datetime.strftime(day, '%Y')
    year = datetime.datetime.strptime(year, '%Y')
    calendar_year, calendar_month, calendar_day = find_calendar_date(date_day=day,
                                                                     date_month=month,
                                                                     date_year=year)
    history = AccountPayableHistory(sum=data['sum'], year_id=calendar_year.id, month_id=calendar_month.id,
                                    day_id=calendar_day.id, payment_type_id=data['type_payment'], reason=data['reason'],
                                    account_payable_id=payable_id)
    history.add()
    calculate_history(payable_id)
    return jsonify({"history": history.convert_json()})


@app.route(f'{api}/crud_history/<int:history_id>/', methods=['POST'])
@jwt_required()
def crud_history(history_id):
    data = request.get_json()
    history = AccountPayableHistory.query.filter(AccountPayableHistory.id == history_id).first()
    history.payment_type_id = data['payment_type_id']
    db.session.commit()
    return jsonify({"history": history.convert_json()})


@app.route(f'{api}/delete_history/<int:history_id>/', methods=['DELETE'])
@jwt_required()
def delete_history(history_id):
    history = AccountPayableHistory.query.filter(AccountPayableHistory.id == history_id).first()
    payable_id = history.account_payable_id
    history.delete()
    calculate_history(payable_id)
    return jsonify({'message': 'History deleted successfully'}), 201


@app.route(f'{api}/get_account_payable/<deleted>/<archive>/', methods=['GET'])
@jwt_required()
def get_account_payable(deleted, archive):
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    deleted = deleted.capitalize()
    archive = archive.capitalize()
    if archive != "True":
        account_payables = AccountPayable.query.filter(AccountPayable.deleted == deleted).order_by(
            AccountPayable.id).all()
    else:
        account_payables = AccountPayable.query.filter(AccountPayable.year_id == calendar_year.id,
                                                       AccountPayable.month_id == calendar_month.id,
                                                       AccountPayable.deleted == deleted).order_by(
            AccountPayable.id).all()
    dividend_list = []
    for payable in account_payables:
        dividend_list.append(
            {
                "id": payable.id,
                "date": payable.day.date.strftime("%Y-%m-%d"),
                "month": payable.month.date.strftime("%Y-%m"),
                "year_id": payable.year.date.strftime("%Y"),
                "amount": payable.amount_sum,
                "payment_type": {
                    "id": payable.payment_type_id,
                    "name": payable.payment_type.name
                },
                "payment_type_id": payable.payment_type_id,
                "payment_type_name": payable.payment_type.name,
                "desc": payable.desc,
                "status": False if payable.status == True else True,
                "remaining_sum": payable.remaining_sum,
                "taken_sum": payable.taken_sum
            }
        )
    return jsonify({'account_payables': dividend_list}), 201


@app.route(f'{api}/crud_account_payable/<int:pk>/', methods=['POST'])
@jwt_required()
def crud_account_payable(pk):
    data = request.get_json()
    payment_type_id = data['payment_type_id']
    account_payable = AccountPayable.query.filter(AccountPayable.id == pk).first()
    account_payable.payment_type_id = payment_type_id
    db.session.commit()
    return jsonify(
        {"payment_type": account_payable.convert_json()}), 201


@app.route(f'{api}/delete_account_payable/<int:pk>/', methods=['POST'])
@jwt_required()
def delete_account_payable(pk):
    data = request.get_json()
    deleted_comment = data['otherReason']
    dividend = AccountPayable.query.filter(AccountPayable.id == pk).first()
    dividend.deleted = True
    dividend.deleted_comment = deleted_comment
    db.session.commit()
    payable_sum_calculate(dividend.year_id, dividend.month_id, dividend.payment_type_id)
    return jsonify({'message': 'Dividend deleted successfully'}), 201
