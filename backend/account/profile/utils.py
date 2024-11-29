from backend.models.models import db, CampStaffSalaries, Dividend, \
    MainOverhead, AccountReport, PaymentTypes
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
