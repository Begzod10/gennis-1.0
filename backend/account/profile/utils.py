from backend.models.models import db, CampStaffSalaries, Dividend, \
    MainOverhead, AccountReport, PaymentTypes, AccountPayable, AccountPayableHistory, Account, or_
from backend.account.models import Investment
from backend.functions.utils import find_calendar_date
from sqlalchemy import func


def update_account(payment_type_id):
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    print('calendar_year', calendar_year, 'calendar_month', calendar_month)
    payment_type = PaymentTypes.query.filter(PaymentTypes.id == payment_type_id).first()
    dividends = \
        db.session.query(func.sum(Dividend.amount_sum)).filter(
            Dividend.year_id == calendar_year.id,
            Dividend.month_id == calendar_month.id,
            Dividend.deleted != True,
            Dividend.payment_type_id == payment_type.id).first()[0]
    overheads = \
        db.session.query(func.sum(MainOverhead.amount_sum)).filter(
            MainOverhead.year_id == calendar_year.id,
            MainOverhead.month_id == calendar_month.id,
            MainOverhead.deleted != True,
            MainOverhead.payment_type_id == payment_type.id).first()[0]
    salaries = \
        db.session.query(func.sum(CampStaffSalaries.amount_sum)).filter(
            CampStaffSalaries.year_id == calendar_year.id,
            CampStaffSalaries.month_id == calendar_month.id,
            CampStaffSalaries.deleted != True,
            CampStaffSalaries.payment_type_id == payment_type.id).first()[0]
    investments = \
        db.session.query(func.sum(Investment.amount)).filter(
            Investment.calendar_year == calendar_year.id,
            Investment.calendar_month == calendar_month.id,
            Investment.deleted_status != True,
            Investment.payment_type_id == payment_type.id).first()[0]

    account_payable = \
        db.session.query(func.sum(AccountPayable.amount_sum)).filter(
            AccountPayable.year_id == calendar_year.id,
            AccountPayable.month_id == calendar_month.id,
            AccountPayable.deleted != True,
            AccountPayable.payment_type_id == payment_type.id,
            AccountPayable.type_account == "payable",
            AccountPayable.finished == False).first()[0]
    account_receivables = \
        db.session.query(func.sum(AccountPayable.amount_sum)).filter(
            AccountPayable.year_id == calendar_year.id,
            AccountPayable.month_id == calendar_month.id,
            AccountPayable.deleted != True,
            AccountPayable.payment_type_id == payment_type.id,
            AccountPayable.type_account == "receivable",
            AccountPayable.finished == False).first()[0]
    sub_account_receivables = \
        db.session.query(func.sum(AccountPayableHistory.sum)).filter(
            AccountPayableHistory.year_id == calendar_year.id,
            AccountPayableHistory.month_id == calendar_month.id,
            AccountPayableHistory.deleted != True,
            AccountPayableHistory.payment_type_id == payment_type.id,
            AccountPayableHistory.type_account == "receivable").first()[0]
    sub_account_payable = \
        db.session.query(func.sum(AccountPayableHistory.sum)).filter(
            AccountPayableHistory.year_id == calendar_year.id,
            AccountPayableHistory.month_id == calendar_month.id,
            AccountPayableHistory.deleted != True,
            AccountPayableHistory.payment_type_id == payment_type.id,
            AccountPayableHistory.type_account == "payable").first()[0]
    sub_account_receivables = sub_account_receivables if sub_account_receivables else 0
    sub_account_payable = sub_account_payable if sub_account_payable else 0
    salaries = salaries if salaries else 0
    overheads = overheads if overheads else 0
    dividends = dividends if dividends else 0
    investments = investments if investments else 0
    account_payable = account_payable if account_payable else 0
    account_receivables = account_receivables if account_receivables else 0
    balance = (dividends + account_receivables + sub_account_receivables) - (
            overheads + salaries + investments + account_payable + sub_account_payable)

    exist_report = AccountReport.query.filter(AccountReport.year_id == calendar_year.id,
                                              AccountReport.month_id == calendar_month.id,
                                              AccountReport.payment_type_id == payment_type.id).first()
    if not exist_report:
        account_report = AccountReport(payment_type_id=payment_type.id, month_id=calendar_month.id,
                                       year_id=calendar_year.id, balance=balance,
                                       all_dividend=dividends, all_overheads=overheads, all_salaries=salaries,
                                       payable=account_payable, receivables=account_receivables,
                                       sub_payable=sub_account_payable, sub_receivables=sub_account_receivables
                                       )
        account_report.add()
    else:
        exist_report.all_dividend = dividends
        exist_report.all_overheads = overheads
        exist_report.all_salaries = salaries
        exist_report.balance = balance
        exist_report.payable = account_payable
        exist_report.receivables = account_receivables
        exist_report.sub_payable = sub_account_payable
        exist_report.sub_receivables = sub_account_receivables

        db.session.commit()


def payable_sum_calculate(calendar_year_id, calendar_month_id, payment_type_id):
    paid_payables = db.session.query(db.func.sum(AccountPayable.amount_sum)).filter_by(status=True,
                                                                                       finished=True,
                                                                                       deleted=False,
                                                                                       year_id=calendar_year_id,
                                                                                       month_id=calendar_month_id,
                                                                                       payment_type_id=payment_type_id).scalar() or 0
    unpaid_payables = db.session.query(db.func.sum(AccountPayable.amount_sum)).filter_by(status=True,
                                                                                         finished=False,
                                                                                         deleted=False,
                                                                                         year_id=calendar_year_id,
                                                                                         month_id=calendar_month_id,
                                                                                         payment_type_id=payment_type_id).scalar() or 0
    returned_receivables = db.session.query(db.func.sum(AccountPayable.amount_sum)).filter_by(status=False,
                                                                                              finished=True,
                                                                                              deleted=False,
                                                                                              year_id=calendar_year_id,
                                                                                              month_id=calendar_month_id,
                                                                                              payment_type_id=payment_type_id).scalar() or 0
    unreturned_receivables = db.session.query(db.func.sum(AccountPayable.amount_sum)).filter_by(status=False,
                                                                                                finished=False,
                                                                                                deleted=False,
                                                                                                year_id=calendar_year_id,
                                                                                                month_id=calendar_month_id,
                                                                                                payment_type_id=payment_type_id).scalar() or 0
    investment = db.session.query(db.func.sum(Investment.amount)).filter_by(deleted_status=False).scalar() or 0
    exist_report = AccountReport.query.filter(AccountReport.payment_type_id == payment_type_id,
                                              AccountReport.month_id == calendar_month_id,
                                              AccountReport.year_id == calendar_year_id).first()
    all_dividend = getattr(exist_report, 'all_dividend', 0) or 0
    all_overheads = getattr(exist_report, 'all_overheads', 0) or 0
    all_salaries = getattr(exist_report, 'all_salaries', 0) or 0

    balance = (
            returned_receivables + unpaid_payables + all_dividend - paid_payables - all_overheads - all_salaries - investment
    )

    if not exist_report:
        account_report = AccountReport(
            year_id=calendar_year_id,
            month_id=calendar_month_id,
            payment_type_id=payment_type_id,
            paid_payables=paid_payables,
            unpaid_payables=unpaid_payables,
            returned_receivables=returned_receivables,
            unreturned_receivables=unreturned_receivables,
            balance=balance
        )
        account_report.add()
    else:
        exist_report.paid_payables = paid_payables
        exist_report.unpaid_payables = unpaid_payables
        exist_report.returned_receivables = returned_receivables
        exist_report.unreturned_receivables = unreturned_receivables
        exist_report.balance = balance
        db.session.commit()


def calculate_history(account_id):
    account = Account.query.filter(Account.id == account_id).first()

    payable = db.session.query(db.func.sum(AccountPayable.amount_sum)).filter(
        AccountPayable.account_id == account_id,
        or_(AccountPayable.deleted == False, AccountPayable.deleted == None)).scalar() or 0
    history = db.session.query(db.func.sum(AccountPayableHistory.sum)).filter(
        AccountPayableHistory.account_id == account_id,
        or_(AccountPayableHistory.deleted == False, AccountPayableHistory.deleted == None)).scalar() or 0

    account.payment_sum = history
    account.total_sum = payable
    account.remaining_sum = account.total_sum - account.payment_sum
    account.done = True if account.remaining_sum == 0 else False
    db.session.commit()
