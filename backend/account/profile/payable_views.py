import datetime

from flask import Blueprint
from flask import jsonify, request
from flask_jwt_extended import jwt_required

from app import db
from backend.functions.utils import find_calendar_date, iterate_models
from backend.models.models import AccountPayable, CalendarMonth, CalendarYear, Account, \
    AccountPayableHistory, or_
from .utils import update_account, calculate_history

account_payable = Blueprint('account_payable', __name__)


@account_payable.route(f'/get_accounts', methods=['GET'])
@jwt_required()
def get_accounts():
    accounts_payable = Account.query.filter(Account.type_account == "payable", Account.deleted == False).order_by(
        Account.id).all()
    accounts_receivable = Account.query.filter(Account.type_account == "receivable", Account.deleted == False).order_by(
        Account.id).all()

    return jsonify({"accounts_payable": iterate_models(accounts_payable),
                    "accounts_receivable": iterate_models(accounts_receivable)}), 201


@account_payable.route(f'/create_account', methods=['POST', 'GET'])
@jwt_required()
def create_account():
    data = request.get_json()
    type_account = data['type_account']
    account = Account(name=data['name'], type_account=type_account)
    account.add()
    return jsonify({"account": account.convert_json()}), 200


@account_payable.route(f'/delete_account/<int:id>/', methods=['DELETE'])
@jwt_required()
def delete_account(id):
    account = Account.query.filter(Account.id == id).first()
    if account.done:
        account.deleted = True
        db.session.commit()
        return jsonify({'message': 'Account deleted successfully'}), 200
    else:
        return jsonify({'message': 'Account has payable or receivable'}), 200


@account_payable.route(f'/account_profile/<int:id>/<deleted>/', methods=['GET'])
@jwt_required()
def account_profile(id, deleted):
    account = Account.query.filter(Account.id == id).first()
    account_payable = AccountPayable.query.filter(AccountPayable.account_id == id,
                                                  or_(AccountPayable.deleted == deleted,
                                                      AccountPayable.deleted == None)).order_by(
        AccountPayable.id).all()
    account_history = AccountPayableHistory.query.filter(
        AccountPayableHistory.account_id == account.id,
        AccountPayableHistory.deleted == deleted).order_by(
        AccountPayableHistory.id).all()
    calculate_history(id)
    if account.type_account == "receivable":
        data = {
            "left": iterate_models(account_payable),
            "right": iterate_models(account_history),
            "account": account.convert_json(),
            "type_account": account.type_account,
        }
    else:
        data = {
            "left": iterate_models(account_history),
            "right": iterate_models(account_payable),
            "type_account": account.type_account,
            "account": account.convert_json()
        }

    return jsonify({"data": data}), 201


@account_payable.route(f'/account_datas/<int:account_id>')
@jwt_required()
def account_datas(account_id):
    account = Account.query.filter(Account.id == account_id).first()
    return jsonify({"account": account.convert_json()}), 201


@account_payable.route(f'/crud_account/<int:id>/', methods=['POST'])
@jwt_required()
def crud_account(id):
    data = request.get_json()
    account = Account.query.filter(Account.id == id).first()
    account.name = data['name']
    db.session.commit()
    return jsonify({'account': account.convert_json()}), 201


@account_payable.route(f'/payable_datas/<int:id>/', methods=['GET'])
@jwt_required()
def payable_datas(id):
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    payables = AccountPayable.query.filter(AccountPayable.account_id == id).order_by(
        AccountPayable.id).all()
    month_ids = {payable.month_id for payable in payables}
    years_ids = {payable.year_id for payable in payables}
    months = CalendarMonth.query.filter(CalendarMonth.id.in_(month_ids)).order_by(CalendarMonth.date).all()
    years = CalendarYear.query.filter(CalendarYear.id.in_(years_ids)).order_by(CalendarYear.date).all()
    return jsonify({
        "years": iterate_models(years), "months": iterate_models(months),
        "year": calendar_year.convert_json(), "month": calendar_month.convert_json()
    })


@account_payable.route(f'/add_account_payable', methods=['POST'])
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
    account = Account.query.filter(Account.id == data['account_id']).first()
    new_account_payable = AccountPayable(
        account_id=data['account_id'],
        amount_sum=amount_sum,
        day_id=calendar_day.id,
        type_account=account.type_account,
        month_id=calendar_month.id,
        year_id=calendar_year.id,
        payment_type_id=payment_type_id,
        desc=desc,
        finished=False
    )
    db.session.add(new_account_payable)
    db.session.commit()

    update_account(payment_type_id)
    calculate_history(data['account_id'])
    return jsonify({'data': new_account_payable.convert_json()}), 201


@account_payable.route(f'/get_payable_histories/<int:id>/', methods=['GET'])
@jwt_required()
def get_payable_histories(id):
    histories = AccountPayableHistory.query.filter(AccountPayableHistory.account_payable_id == id).all()
    return jsonify({"histories": iterate_models(histories)})


@account_payable.route(f'/create_payable_history', methods=['POST'])
@jwt_required()
def create_payable_history():
    data = request.get_json()
    day = datetime.datetime.strptime(data['date'], '%Y-%m-%d')
    month = datetime.datetime.strftime(day, '%Y-%m')
    month = datetime.datetime.strptime(month, '%Y-%m')
    year = datetime.datetime.strftime(day, '%Y')
    year = datetime.datetime.strptime(year, '%Y')
    account_id = data['account_id']
    account = Account.query.filter(Account.id == account_id).first()
    type_account = "payable" if account.type_account == "receivable" else "receivable"
    calendar_year, calendar_month, calendar_day = find_calendar_date(date_day=day,
                                                                     date_month=month,
                                                                     date_year=year)
    history = AccountPayableHistory(sum=data['amount_sum'], year_id=calendar_year.id, month_id=calendar_month.id,
                                    account_id=account_id,
                                    day_id=calendar_day.id, payment_type_id=data['type_payment'], reason=data['desc'],
                                    type_account=type_account)
    history.add()
    update_account(history.payment_type_id)
    calculate_history(account_id)
    return jsonify({"data": history.convert_json()})


@account_payable.route(f'/crud_history/<int:history_id>/', methods=['POST'])
@jwt_required()
def crud_history(history_id):
    data = request.get_json()
    history = AccountPayableHistory.query.filter(AccountPayableHistory.id == history_id).first()
    history.payment_type_id = data['payment_type_id']
    db.session.commit()
    update_account(history.payment_type_id)
    return jsonify({"history": history.convert_json()})


@account_payable.route(f'/delete_history/<int:history_id>/', methods=['DELETE'])
@jwt_required()
def delete_history(history_id):
    history = AccountPayableHistory.query.filter(AccountPayableHistory.id == history_id).first()
    history.deleted = True
    history.deleted_reason = request.get_json()['otherReason']
    db.session.commit()
    calculate_history(history.account_id)
    update_account(history.payment_type_id)
    return jsonify({'message': 'History deleted successfully'}), 201


@account_payable.route(f'/get_account_payable/<deleted>/<archive>/', methods=['GET'])
@jwt_required()
def get_account_payable(deleted, archive):
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    deleted = deleted.capitalize()
    archive = archive.capitalize()
    if archive == "True":
        account_payables = AccountPayable.query.filter(AccountPayable.deleted == deleted).order_by(
            AccountPayable.id).all()
    else:
        account_payables = AccountPayable.query.filter(AccountPayable.year_id == calendar_year.id,
                                                       AccountPayable.month_id == calendar_month.id,
                                                       AccountPayable.deleted == deleted).order_by(
            AccountPayable.id).all()
    dividend_list = iterate_models(account_payables)

    return jsonify({'account_payables': dividend_list}), 201


@account_payable.route(f'/crud_account_payable/<int:pk>/', methods=['POST'])
@jwt_required()
def crud_account_payable(pk):
    data = request.get_json()
    payment_type_id = data['payment_type_id']
    account_payable = AccountPayable.query.filter(AccountPayable.id == pk).first()
    account_payable.payment_type_id = payment_type_id
    db.session.commit()
    update_account(payment_type_id)
    return jsonify(
        {"payment_type": account_payable.convert_json()}), 201


@account_payable.route(f'/delete_account_payable/<int:pk>/', methods=['DELETE'])
@jwt_required()
def delete_account_payable(pk):
    data = request.get_json()
    deleted_comment = data['otherReason']
    payable = AccountPayable.query.filter(AccountPayable.id == pk).first()
    payable.deleted = True
    payable.deleted_comment = deleted_comment
    db.session.commit()
    calculate_history(payable.account_id)
    update_account(payable.payment_type_id)
    return jsonify({'message': 'Dividend deleted successfully'}), 201
