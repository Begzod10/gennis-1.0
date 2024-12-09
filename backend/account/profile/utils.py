from backend.models.models import db, CampStaffSalaries, Dividend, \
    MainOverhead, AccountReport, PaymentTypes, AccountPayable, AccountPayableHistory
from backend.functions.utils import find_calendar_date
from app import func


def update_account():
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    payment_types = PaymentTypes.query.order_by(PaymentTypes.id).all()

    for payment_type in payment_types:
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

        salaries = salaries if salaries else 0
        overheads = overheads if overheads else 0
        dividends = dividends if dividends else 0
        balance = dividends - (overheads + salaries)
        print('payment_type', payment_type.name)
        print('balance', balance)
        print('dividends', dividends)
        print('salaries', salaries)
        print('overheads', overheads)

        exist_report = AccountReport.query.filter(AccountReport.year_id == calendar_year.id,
                                                  AccountReport.month_id == calendar_month.id,
                                                  AccountReport.payment_type_id == payment_type.id).first()
        if not exist_report:
            account_report = AccountReport(payment_type_id=payment_type.id, month_id=calendar_month.id,
                                           year_id=calendar_year.id, balance=balance,
                                           all_dividend=dividends, all_overheads=overheads, all_salaries=salaries)
            account_report.add()
        else:
            exist_report.all_dividend = dividends
            exist_report.all_overheads = overheads
            exist_report.all_salaries = salaries
            exist_report.balance = balance
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
    exist_report = AccountReport.query.filter(AccountReport.payment_type_id == payment_type_id,
                                              AccountReport.month_id == calendar_month_id,
                                              AccountReport.year_id == calendar_year_id).first()
    all_dividend = getattr(exist_report, 'all_dividend', 0) or 0
    all_overheads = getattr(exist_report, 'all_overheads', 0) or 0
    all_salaries = getattr(exist_report, 'all_salaries', 0) or 0

    balance = (
            returned_receivables + unpaid_payables + all_dividend - paid_payables - all_overheads - all_salaries
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


def calculate_history(payable_id):
    payable = AccountPayable.query.filter(AccountPayable.id == payable_id).first()
    history = db.session.query(db.func.sum(AccountPayableHistory.sum)).filter_by(
        account_payable_id=payable_id).scalar() or 0


    payable.remaining_sum = payable.amount_sum - history
    payable.taken_sum = history
    if payable.remaining_sum == 0:
        payable.finished = True
    db.session.commit()
