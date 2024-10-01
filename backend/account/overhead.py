from app import *
from backend.functions.functions import *
from backend.models.models import *
from flask_jwt_extended import *


@app.route(f'{api}/add_overhead/<int:location_id>', methods=["GET", 'POST'])
@jwt_required(refresh=True)
def add_overhead(location_id):
    refreshdatas()
    calendar_year = CalendarYear.query.filter(CalendarYear.date == new_year()).first()

    calendar_month = CalendarMonth.query.filter(CalendarMonth.date == new_month(),
                                                CalendarMonth.year_id == calendar_year.id).first()
    calendar_day = CalendarDay.query.filter(CalendarDay.date == new_today(),
                                            CalendarDay.month_id == calendar_month.id).first()
    if request.method == "POST":
        account_period = db.session.query(AccountingPeriod).join(AccountingPeriod.month).options(
            contains_eager(AccountingPeriod.month)).order_by(desc(CalendarMonth.id)).first()

        current_year = datetime.now().year
        month = request.get_json()['month']
        calendar_month = str(current_year) + "-" + str(month)
        day = request.get_json()['day']
        day = str(current_year) + "-" + str(month) + "-" + str(day)
        type_of_data = request.get_json()['typePayment']
        sum = int(request.get_json()['price'])
        name_item = request.get_json()['typeItem']
        payment_type = PaymentTypes.query.filter(PaymentTypes.id == type_of_data).first()
        month = datetime.strptime(calendar_month, "%Y-%m")
        day = datetime.strptime(day, "%Y-%m-%d")
        calendar_month = CalendarMonth.query.filter(CalendarMonth.date == month).first()
        calendar_day = CalendarDay.query.filter(CalendarDay.date == day).first()
        add = Overhead(item_sum=sum, item_name=name_item, payment_type_id=payment_type.id, location_id=location_id,
                       calendar_day=calendar_day.id, calendar_month=calendar_month.id, calendar_year=calendar_year.id,
                       account_period_id=account_period.id)
        db.session.add(add)
        db.session.commit()

        return jsonify({
            "success": True,
            "msg": "Qo'shimcha xarajat qo'shildi"
        })


@app.route(f'{api}/delete_overhead/<overhead_id>')
@jwt_required(refresh=True)
def delete_overhead(overhead_id):
    refreshdatas()
    calendar_year = CalendarYear.query.filter(CalendarYear.date == new_year()).first()

    calendar_month = CalendarMonth.query.filter(CalendarMonth.date == new_month(),
                                                CalendarMonth.year_id == calendar_year.id).first()
    calendar_day = CalendarDay.query.filter(CalendarDay.date == new_today(),
                                            CalendarDay.month_id == calendar_month.id).first()
    try:
        refreshdatas()
    except AttributeError:
        refreshdatas()
    overhead = Overhead.query.filter(Overhead.id == overhead_id).first()
    account_period = db.session.query(AccountingPeriod).join(AccountingPeriod.month).options(
        contains_eager(AccountingPeriod.month)).order_by(desc(CalendarMonth.id)).first()

    payment_type = PaymentTypes.query.filter(PaymentTypes.id == overhead.payment_type_id).first()

    deleted_overhead = DeletedOverhead(item_sum=overhead.item_sum, item_name=overhead.item_name,
                                       payment_type_id=overhead.payment_type_id, location_id=overhead.location_id,
                                       calendar_day=overhead.calendar_day, calendar_month=overhead.calendar_month,
                                       calendar_year=overhead.calendar_year,
                                       account_period_id=overhead.account_period_id, deleted_date=calendar_day.date,
                                       reason="reason qoshish kere frontendga")
    db.session.add(deleted_overhead)
    db.session.commit()
    db.session.delete(overhead)
    db.session.commit()
    return jsonify({
        "success": True,
        "msg": "Xarajat o'chirildi"
    })


@app.route(f'{api}/change_overhead/<int:overhead>/<type_id>')
def change_overhead(overhead, type_id):
    refreshdatas()
    calendar_year = CalendarYear.query.filter(CalendarYear.date == new_year()).first()

    calendar_month = CalendarMonth.query.filter(CalendarMonth.date == new_month(),
                                                CalendarMonth.year_id == calendar_year.id).first()
    calendar_day = CalendarDay.query.filter(CalendarDay.date == new_today(),
                                            CalendarDay.month_id == calendar_month.id).first()
    payment_type = PaymentTypes.query.filter(PaymentTypes.name == type_id).first()
    overhead_get = Overhead.query.filter(Overhead.id == overhead).first()

    Overhead.query.filter(Overhead.id == overhead_get.id).update({
        "payment_type_id": payment_type.id
    })
    db.session.commit()

    accounting_info = AccountingInfo.query.filter(AccountingInfo.payment_type_id == overhead_get.payment_type_id,
                                                  AccountingInfo.location_id == overhead_get.location_id,
                                                  AccountingInfo.account_period_id == overhead_get.account_period_id).first()

    return jsonify({
        "success": True,
        "msg": "Xarajat summa turi o'zgartirildi"
    })
