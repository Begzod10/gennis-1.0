from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import desc, and_, func, or_
from sqlalchemy.orm import contains_eager

from backend.functions.filters import old_current_dates, iterate_models
from backend.functions.utils import get_json_field, find_calendar_date
from backend.models.models import AccountingPeriod, CalendarMonth, PaymentTypes, StudentPayments, Students, CalendarDay, \
    StaffSalaries, TeacherSalaries, CenterBalanceOverhead, Overhead, CalendarYear, BranchPayment, AccountingInfo, \
    DeletedStudentPayments, DeletedOverhead, DeletedTeacherSalaries, DeletedStaffSalaries, Users, Teachers, Dividend, \
    CapitalExpenditure, Investment, db, Groups, StudentExcuses
from backend.models.settings import sum_money

account_bp = Blueprint('account_bp', __name__)


@account_bp.route(f'/account_info/', defaults={"type_filter": None}, methods=["POST"])
@account_bp.route(f'/account_info/<type_filter>', methods=["POST"])
@jwt_required()
def account_info(type_filter):
    type_account = get_json_field('type')
    location = get_json_field('locationId')
    calendar_year, calendar_month, calendar_day = find_calendar_date()

    # pagination
    limit = request.args.get("limit", type=int)
    offset = request.args.get("offset", default=0, type=int)

    accounting_period = AccountingPeriod.query.join(CalendarMonth).order_by(desc(CalendarMonth.id)).first().id
    payments_list = []
    final_list = []

    if type_account == "dividends":
        query = Dividend.query.filter(Dividend.location_id == location)
        if not type_filter:
            query = query.filter(Dividend.account_period_id == accounting_period)
        dividends = query.order_by(desc(Dividend.id)).all()
        type_account = "user"
        payments_list = iterate_models(dividends)

    elif type_account == "investments":
        query = Investment.query.filter(Investment.location_id == location, Investment.deleted_status == False)
        if not type_filter:
            query = query.filter(Investment.account_period_id == accounting_period)
        investments = query.order_by(desc(Investment.id)).all()
        type_account = "user"
        payments_list = iterate_models(investments)


    elif type_account == "payments":
        search = request.args.get("search", type=str)
        query = StudentPayments.query.join(StudentPayments.student).join(Students.user).filter(
            StudentPayments.location_id == location,
            StudentPayments.payment == True
        )
        if not type_filter:
            query = query.filter(StudentPayments.account_period_id == accounting_period)
        if search:
            search_term = f"%{search}%"
            query = query.filter(or_(
                Users.name.ilike(search_term),
                Users.surname.ilike(search_term)
            ))
        payments = query.order_by(desc(StudentPayments.id)).all()
        type_account = "user"
        payments_list = [{
            "id": p.id,
            "name": p.student.user.name.title(),
            "surname": p.student.user.surname.title(),
            "payment": p.payment_sum,
            "typePayment": p.payment_type.name,
            "date": p.day.date.strftime("%Y-%m-%d"),
            "day": str(p.calendar_day),
            "month": str(p.calendar_month),
            "year": str(p.calendar_year),
            "user_id": p.student.user_id
        } for p in payments]

    # Apply pagination
    pagination_data = None
    if isinstance(payments_list, list) and limit:
        total = len(payments_list)
        payments_list = payments_list[offset:offset + limit]
        pagination_data = {"total": total, "page": offset, "limit": limit, "has_more": (offset + limit) < total}
    elif isinstance(payments_list, dict) and limit:
        pagination_data = {}
        for key in payments_list:
            total = len(payments_list[key])
            payments_list[key] = payments_list[key][offset:offset + limit]
            pagination_data[key] = {"total": total, "page": offset, "limit": limit,
                                    "has_more": (offset + limit) < total}

    return jsonify({"data": {"typeOfMoney": type_account, "data": payments_list, "pagination": pagination_data,
                             "overhead_tools": old_current_dates(observation=True),
                             "capital_tools": old_current_dates(observation=True),
                             "teacher_list": final_list, "location": location}})


@account_bp.route('/account_info/students_payments/', methods=["GET"])
@jwt_required()
def account_info_payments():
    location = request.args.get('locationId')
    type_filter = request.args.get('typeFilter')
    payment_type = request.args.get('paymentType')
    year = request.args.get('year')
    month = request.args.get('month')
    day = request.args.get('day')
    calendar_year = None
    calendar_month = None
    calendar_day = None
    if year:
        calendar_year = CalendarYear.query.filter(CalendarYear.id == year).first()
    if month:
        calendar_month = CalendarMonth.query.filter(CalendarMonth.id == month).first()
    if day:
        calendar_day = CalendarDay.query.filter(CalendarDay.id == day).first()

    accounting_period = AccountingPeriod.query.join(CalendarMonth).order_by(desc(CalendarMonth.id)).first().id
    search = request.args.get("search", type=str)
    query = StudentPayments.query.join(StudentPayments.student).join(Students.user).filter(
        StudentPayments.location_id == location,
        StudentPayments.payment == True
    )
    if not type_filter:
        query = query.filter(StudentPayments.account_period_id == accounting_period)
    if search:
        search_term = f"%{search}%"
        query = query.filter(or_(
            Users.name.ilike(search_term),
            Users.surname.ilike(search_term)
        ))
    if payment_type:
        payment_type = PaymentTypes.query.filter(PaymentTypes.name == payment_type).first().id
        query = query.filter(StudentPayments.payment_type_id == payment_type)
    if calendar_year:
        query = query.filter(StudentPayments.calendar_year == calendar_year.id)
    if calendar_month:
        query = query.filter(StudentPayments.calendar_month == calendar_month.id)
    if calendar_day:
        query = query.filter(StudentPayments.calendar_day == calendar_day.id)
    payments = query.order_by(desc(StudentPayments.id)).all()
    payments_list = [{
        "id": p.id,
        "name": p.student.user.name.title(),
        "surname": p.student.user.surname.title(),
        "payment": p.payment_sum,
        "typePayment": p.payment_type.name,
        "date": p.day.date.strftime("%Y-%m-%d"),
        "day": str(p.calendar_day),
        "month": str(p.calendar_month),
        "year": str(p.calendar_year),
        "user_id": p.student.user_id
    } for p in payments]
    pagination_data = None
    limit = request.args.get("limit", type=int)
    offset = request.args.get("offset", default=0, type=int)
    if limit:
        total = len(payments_list)
        payments_list = payments_list[offset:offset + limit]
        pagination_data = {"total": total, "page": offset, "limit": limit, "has_more": (offset + limit) < total}
    return jsonify({"data": {"typeOfMoney": "payments", "data": payments_list, "pagination": pagination_data,
                             "overhead_tools": old_current_dates(observation=True),
                             "capital_tools": old_current_dates(observation=True),
                             "location": location}})


@account_bp.route('/account_info/book_payments/', methods=["GET"])
@jwt_required()
def account_info_book_payments():
    location = request.args.get('locationId')
    type_filter = request.args.get('typeFilter')
    accounting_period = request.args.get('accountingPeriod')
    offset = request.args.get('offset', default=0, type=int)
    limit = request.args.get('limit', type=int)
    type_pagenation = request.args.get("type_pagenation")

    type_account = "studentBookPayment"

    # Queries
    if not type_filter:
        branch_payments = BranchPayment.query.filter(
            BranchPayment.location_id == location,
            BranchPayment.account_period_id == accounting_period
        ).order_by(BranchPayment.id).all()

        center_balance_overhead = CenterBalanceOverhead.query.filter(
            CenterBalanceOverhead.location_id == location,
            CenterBalanceOverhead.account_period_id == accounting_period,
            CenterBalanceOverhead.deleted == False
        ).order_by(CenterBalanceOverhead.id).all()
    else:
        branch_payments = BranchPayment.query.filter(
            BranchPayment.location_id == location
        ).order_by(BranchPayment.id).all()

        center_balance_overhead = CenterBalanceOverhead.query.filter(
            CenterBalanceOverhead.location_id == location,
            CenterBalanceOverhead.deleted == False
        ).order_by(CenterBalanceOverhead.id).all()

    # FULL list
    full_book_payments = [{
        "id": p.id,
        "name": "Kitobchiga pul",
        "price": int(p.order.book.own_price) if p.order.book else 0,
        "typePayment": p.payment_type.name,
        "date": p.order.day.date.strftime("%Y-%m-%d"),
        "day": str(p.calendar_day),
        "month": str(p.calendar_month),
        "year": str(p.calendar_year),
        "reason": "",
        "type": "book_payments",
    } for p in branch_payments]

    if type_pagenation == "book_payments" and limit is not None:
        total = len(full_book_payments)
        paginated_book_payments = full_book_payments[offset:offset + limit]
        pagination_data = {
            "total": total,
            "offset": offset,
            "limit": limit,
            "has_more": (offset + limit) < total
        }
    else:
        paginated_book_payments = full_book_payments
        pagination_data = None

    book_overheads = [{
        "id": o.id,
        "name": "Kitob pulidan",
        "price": int(o.payment_sum),
        "typePayment": o.payment_type.name,
        "date": o.day.date.strftime("%Y-%m-%d"),
        "day": str(o.calendar_day),
        "month": str(o.calendar_month),
        "year": str(o.calendar_year),
        "reason": "",
        "type": "book_overheads",
    } for o in center_balance_overhead]

    payments_list = {
        "book_overheads": book_overheads,
        "book_payments": paginated_book_payments,
    }

    return jsonify({
        "data": {
            "typeOfMoney": type_account,
            "data": payments_list,
            "pagination": pagination_data,
            "overhead_tools": old_current_dates(observation=True),
            "capital_tools": old_current_dates(observation=True),
            "location": location
        }
    })


@account_bp.route('/account_info/teacher_salary/', methods=["GET"])
@jwt_required()
def account_info_teacher_salary():
    location = request.args.get('locationId')
    type_filter = request.args.get('typeFilter')
    payment_type = request.args.get('paymentType')
    year = request.args.get('year')
    month = request.args.get('month')
    day = request.args.get('day')
    calendar_year = None
    calendar_month = None
    calendar_day = None
    if year:
        calendar_year = CalendarYear.query.filter(CalendarYear.id == year).first()
    if month:
        calendar_month = CalendarMonth.query.filter(CalendarMonth.id == month).first()
    if day:
        calendar_day = CalendarDay.query.filter(CalendarDay.id == day).first()

    accounting_period = AccountingPeriod.query.join(CalendarMonth).order_by(desc(CalendarMonth.id)).first().id
    query = TeacherSalaries.query.filter(TeacherSalaries.location_id == location)
    if not type_filter:
        query = query.filter(TeacherSalaries.account_period_id == accounting_period)
    if payment_type:
        payment_type = PaymentTypes.query.filter(PaymentTypes.name == payment_type).first().id
        query = query.filter(TeacherSalaries.payment_type_id == payment_type)
    if calendar_year:
        query = query.filter(TeacherSalaries.calendar_year == calendar_year.id)
    if calendar_month:
        query = query.filter(TeacherSalaries.calendar_month == calendar_month.id)
    if calendar_day:
        query = query.filter(TeacherSalaries.calendar_day == calendar_day.id)

    teacher_salaries = query.order_by(desc(TeacherSalaries.id)).all()

    payments_list = [{"id": s.id, "name": s.teacher.user.name.title(), "surname": s.teacher.user.surname.title(),
                      "salary": s.payment_sum, "typePayment": s.payment_type.name,
                      "date": s.day.date.strftime("%Y-%m-%d"),
                      "day": str(s.calendar_day), "month": str(s.calendar_month), "year": str(s.calendar_year),
                      "user_id": s.teacher.user_id} for s in teacher_salaries]

    pagination_data = None
    limit = request.args.get("limit", type=int)
    offset = request.args.get("offset", default=0, type=int)
    if limit:
        total = len(payments_list)
        payments_list = payments_list[offset:offset + limit]
        pagination_data = {"total": total, "page": offset, "limit": limit, "has_more": (offset + limit) < total}
    return jsonify({"data": {"typeOfMoney": "teacher_salary", "data": payments_list, "pagination": pagination_data,
                             "overhead_tools": old_current_dates(observation=True),
                             "capital_tools": old_current_dates(observation=True),
                             "location": location}})


@account_bp.route('/account_info/staff_salary/', methods=["GET"])
@jwt_required()
def account_info_staff_salary():
    location = request.args.get('locationId')
    type_filter = request.args.get('typeFilter')
    payment_type = request.args.get('paymentType')
    year = request.args.get('year')
    month = request.args.get('month')
    day = request.args.get('day')
    calendar_year = None
    calendar_month = None
    calendar_day = None
    if year:
        calendar_year = CalendarYear.query.filter(CalendarYear.id == year).first()
    if month:
        calendar_month = CalendarMonth.query.filter(CalendarMonth.id == month).first()
    if day:
        calendar_day = CalendarDay.query.filter(CalendarDay.id == day).first()

    accounting_period = AccountingPeriod.query.join(CalendarMonth).order_by(desc(CalendarMonth.id)).first().id
    query = StaffSalaries.query.filter(StaffSalaries.location_id == location)
    if not type_filter:
        query = query.filter(StaffSalaries.account_period_id == accounting_period)
    if payment_type:
        payment_type = PaymentTypes.query.filter(PaymentTypes.name == payment_type).first().id
        query = query.filter(StaffSalaries.payment_type_id == payment_type)
    if calendar_year:
        query = query.filter(StaffSalaries.calendar_year == calendar_year.id)
    if calendar_month:
        query = query.filter(StaffSalaries.calendar_month == calendar_month.id)
    if calendar_day:
        query = query.filter(StaffSalaries.calendar_day_id == calendar_day.id)
    staff_salaries = query.order_by(desc(StaffSalaries.id)).all()
    payments_list = [{"id": s.id, "name": s.staff.user.name.title(), "surname": s.staff.user.surname.title(),
                      "salary": s.payment_sum, "typePayment": s.payment_type.name,
                      "date": s.day.date.strftime("%Y-%m-%d"),
                      "day": str(s.calendar_day), "month": str(s.calendar_month), "year": str(s.calendar_year),
                      "user_id": s.staff.user_id, "job": s.profession.name} for s in staff_salaries]
    pagination_data = None
    limit = request.args.get("limit", type=int)
    offset = request.args.get("offset", default=0, type=int)
    if limit:
        total = len(payments_list)
        payments_list = payments_list[offset:offset + limit]
        pagination_data = {"total": total, "page": offset, "limit": limit, "has_more": (offset + limit) < total}
    return jsonify({"data": {"typeOfMoney": "staff_salary", "data": payments_list, "pagination": pagination_data,
                             "overhead_tools": old_current_dates(observation=True),
                             "capital_tools": old_current_dates(observation=True),
                             "location": location}})


@account_bp.route('/account_info/discounts/', methods=["GET"])
@jwt_required()
def account_info_discounts():
    location = request.args.get('locationId')
    type_filter = request.args.get('typeFilter')
    accounting_period = AccountingPeriod.query.join(CalendarMonth).order_by(desc(CalendarMonth.id)).first().id
    query = StudentPayments.query.filter(StudentPayments.location_id == location, StudentPayments.payment == False)
    if not type_filter:
        query = query.filter(StudentPayments.account_period_id == accounting_period)
    discounts = query.order_by(desc(StudentPayments.id)).all()
    payments_list = [{"id": p.id, "name": p.student.user.name.title(), "surname": p.student.user.surname.title(),
                      "payment": p.payment_sum, "typePayment": p.payment_type.name,
                      "date": p.day.date.strftime("%Y-%m-%d"),
                      "day": str(p.calendar_day), "month": str(p.calendar_month), "year": str(p.calendar_year),
                      "user_id": p.student.user_id} for p in discounts]
    pagination_data = None
    limit = request.args.get("limit", type=int)
    offset = request.args.get("offset", default=0, type=int)
    if limit:
        total = len(payments_list)
        payments_list = payments_list[offset:offset + limit]
        pagination_data = {"total": total, "page": offset, "limit": limit, "has_more": (offset + limit) < total}
    return jsonify({"data": {"typeOfMoney": "discountss", "data": payments_list, "pagination": pagination_data,
                             "overhead_tools": old_current_dates(observation=True),
                             "capital_tools": old_current_dates(observation=True),
                             "location": location}})


@account_bp.route('/account_info/capital/', methods=["GET"])
@jwt_required()
def account_info_capital():
    location = request.args.get('locationId')
    type_filter = request.args.get('typeFilter')
    payment_type = request.args.get('paymentType')
    year = request.args.get('year')
    month = request.args.get('month')
    day = request.args.get('day')
    calendar_year = None
    calendar_month = None
    calendar_day = None
    if year:
        calendar_year = CalendarYear.query.filter(CalendarYear.id == year).first()
    if month:
        calendar_month = CalendarMonth.query.filter(CalendarMonth.id == month).first()
    if day:
        calendar_day = CalendarDay.query.filter(CalendarDay.id == day).first()

    accounting_period = AccountingPeriod.query.join(CalendarMonth).order_by(desc(CalendarMonth.id)).first().id
    query = CapitalExpenditure.query.filter(CapitalExpenditure.location_id == location)
    if not type_filter:
        query = query.filter(CapitalExpenditure.account_period_id == accounting_period)
    if calendar_year:
        query = query.filter(CapitalExpenditure.calendar_year == calendar_year.id)
    if calendar_month:
        query = query.filter(CapitalExpenditure.calendar_month == calendar_month.id)
    if calendar_day:
        query = query.filter(CapitalExpenditure.calendar_day == calendar_day.id)
    if payment_type:
        payment_type = PaymentTypes.query.filter(PaymentTypes.name == payment_type).first().id
        query = query.filter(CapitalExpenditure.payment_type_id == payment_type)
    capital = query.order_by(desc(CapitalExpenditure.id)).all()
    payments_list = [{"id": c.id, "name": c.item_name, "price": c.item_sum, "typePayment": c.payment_type.name,
                      "date": c.day.date.strftime("%Y-%m-%d"), "day": str(c.calendar_day),
                      "month": str(c.calendar_month),
                      "year": str(c.calendar_year)} for c in capital]
    pagination_data = None
    limit = request.args.get("limit", type=int)
    offset = request.args.get("offset", default=0, type=int)
    if limit:
        total = len(payments_list)
        payments_list = payments_list[offset:offset + limit]
        pagination_data = {"total": total, "page": offset, "limit": limit, "has_more": (offset + limit) < total}
    return jsonify({"data": {"typeOfMoney": "capital", "data": payments_list, "pagination": pagination_data,
                             "overhead_tools": old_current_dates(observation=True),
                             "capital_tools": old_current_dates(observation=True),
                             "location": location}})


@account_bp.route('/account_info/overhead/', methods=["GET"])
@jwt_required()
def account_info_overhead():
    location = request.args.get('locationId')
    type_filter = request.args.get('typeFilter')
    payment_type = request.args.get('paymentType')
    overhead_type = request.args.get('overheadType')
    year = request.args.get('year')
    month = request.args.get('month')
    day = request.args.get('day')
    calendar_year = None
    calendar_month = None
    calendar_day = None
    if year:
        calendar_year = CalendarYear.query.filter(CalendarYear.id == year).first()
    if month:
        calendar_month = CalendarMonth.query.filter(CalendarMonth.id == month).first()
    if day:
        calendar_day = CalendarDay.query.filter(CalendarDay.id == day).first()
    accounting_period = AccountingPeriod.query.join(CalendarMonth).order_by(desc(CalendarMonth.id)).first().id
    query = Overhead.query.filter(Overhead.location_id == location)
    if not type_filter:
        query = query.filter(Overhead.account_period_id == accounting_period)
    if calendar_year:
        query = query.filter(Overhead.calendar_year == calendar_year.id)
    if calendar_month:
        query = query.filter(Overhead.calendar_month == calendar_month.id)
    if calendar_day:
        query = query.filter(Overhead.calendar_day == calendar_day.id)
    if payment_type:
        payment_type = PaymentTypes.query.filter(PaymentTypes.name == payment_type).first().id
        query = query.filter(Overhead.payment_type_id == payment_type)
    if overhead_type:
        query = query.filter(Overhead.item_name == overhead_type)
    overheads = query.order_by(desc(Overhead.id)).all()
    payments_list = [{"id": o.id, "name": o.item_name, "price": int(o.item_sum), "typePayment": o.payment_type.name,
                      "date": o.day.date.strftime("%Y-%m-%d"), "day": str(o.calendar_day),
                      "month": str(o.calendar_month),
                      "year": str(o.calendar_year), "reason": "", "type": "overhead", } for o in overheads]
    pagination_data = None
    limit = request.args.get("limit", type=int)
    offset = request.args.get("offset", default=0, type=int)
    if limit:
        total = len(payments_list)
        payments_list = payments_list[offset:offset + limit]
        pagination_data = {
            "total": total,
            "page": offset,
            "limit": limit,
            "has_more": (offset + limit) < total
        }

    return jsonify({"data": {"typeOfMoney": "overhead", "data": payments_list, "pagination": pagination_data,
                             "overhead_tools": old_current_dates(observation=True),
                             "capital_tools": old_current_dates(observation=True),
                             "location": location}})


@account_bp.route('/account_info/debts/', methods=["GET"])
@jwt_required()
def account_info_debts():
    location = request.args.get('locationId')
    color = request.args.get("color", type=str)
    limit = request.args.get("limit", type=int)
    group_status = request.args.get("groupStatus", type=str)
    teacher_id = request.args.get("teacherId", type=int)
    offset = request.args.get("offset", default=0, type=int)

    payments_list = []

    # Base query
    students_query = (
        db.session.query(Students)
        .join(Students.user)
        .options(contains_eager(Students.user))
        .filter(Users.balance < 0)
    )

    if location:
        students_query = students_query.filter(Users.location_id == location)

    if teacher_id:
        if teacher_id != "all":
            students_query = (
                students_query.join(Students.group)
                .options(contains_eager(Students.group))
                .filter(Groups.teacher_id == teacher_id)
            )
    if group_status:
        if group_status == "Guruh":
            students_query = students_query.filter(Students.group != None)
        else:
            students_query = students_query.filter(Students.group == None)

    if color:
        colors = ["green", "yellow", "red", "navy", "black"]
        if color in colors:
            students_query = students_query.filter(Students.debtor == colors.index(color))

    students = students_query.order_by(Users.balance).all()

    for student in students:
        phone = student.user.phone[0].phone if student.user.phone else None
        student_excuse = StudentExcuses.query.filter_by(student_id=student.id).order_by(desc(StudentExcuses.id)).first()
        info = {
            "id": student.user.id,
            "name": student.user.name.title(),
            "surname": student.user.surname.title(),
            "moneyType": ["green", "yellow", "red", "navy", "black"][student.debtor],
            "phone": phone,
            "balance": student.user.balance,
            "status": "Guruh" if student.group else "Guruhsiz",
            "teacher": [],
            "reason": student_excuse.reason if student_excuse else "",
            "date": student_excuse.added_date.strftime("%Y-%m-%d") if student_excuse else "",
            "payment_reason": "tel qilinmaganlar",
            "reason_days": ""
        }

        if student.group:
            teachers = (
                db.session.query(Teachers)
                .join(Teachers.group)
                .options(contains_eager(Teachers.group))
                .filter(
                    Groups.teacher_id == teacher_id,
                    Groups.id.in_([gr.id for gr in student.group])
                )
                .all()
            )
            if teachers:
                info['teacher'] = [t.user_id for t in teachers]

        payments_list.append(info)

    # Pagination
    pagination_data = None
    if limit:
        total = len(payments_list)
        payments_list = payments_list[offset:offset + limit]
        pagination_data = {
            "total": total,
            "page": offset,
            "limit": limit,
            "has_more": (offset + limit) < total
        }

    return jsonify({
        "data": {
            "data": payments_list,
            "pagination": pagination_data,
            "overhead_tools": old_current_dates(observation=True),
            "capital_tools": old_current_dates(observation=True),
            "location": location
        }
    })


@account_bp.route('/account_info_deleted/', defaults={"type_filter": None}, methods=["POST"])
@account_bp.route('/account_info_deleted/<type_filter>', methods=["POST"])
@jwt_required()
def account_info_deleted(type_filter):
    type_account = get_json_field('type')
    location = get_json_field('locationId')
    accounting_period = AccountingPeriod.query.join(CalendarMonth).order_by(desc(CalendarMonth.id)).first().id

    # pagination
    limit = request.args.get("limit", type=int)
    offset = request.args.get("offset", type=int, default=0)

    def apply_pagination(query):
        if limit is not None:
            return query.offset(offset).limit(limit).all()
        return query.all()

    payments_list = []

    if type_account == "dividends":
        query = Dividend.query.filter(Dividend.location_id == location, Dividend.deleted == True)
        if not type_filter:
            query = query.filter(Dividend.account_period_id == accounting_period)
        dividends = apply_pagination(query.order_by(Dividend.id))
        type_account = "user"
        payments_list = iterate_models(dividends)

    elif type_account == "investments":
        query = Investment.query.filter(Investment.location_id == location, Investment.deleted_status == True)
        if not type_filter:
            query = query.filter(Investment.account_period_id == accounting_period)
        investments = apply_pagination(query.order_by(desc(Investment.id)))
        type_account = "user"
        payments_list = iterate_models(investments)

    elif type_account == "payments":
        query = DeletedStudentPayments.query.filter(
            DeletedStudentPayments.location_id == location,
            DeletedStudentPayments.payment == True
        )
        if not type_filter:
            query = query.filter(DeletedStudentPayments.account_period_id == accounting_period)
        payments = apply_pagination(query.order_by(DeletedStudentPayments.id))
        type_account = "user"
        payments_list = [{
            "id": p.id, "name": p.student.user.name.title(), "surname": p.student.user.surname.title(),
            "payment": p.payment_sum, "typePayment": p.payment_type.name,
            "date": p.day.date.strftime("%Y-%m-%d"),
            "day": str(p.calendar_day), "month": str(p.calendar_month), "year": str(p.calendar_year),
            "user_id": p.student.user_id, "reason": p.reason
        } for p in payments]


    elif type_account == "book_payments":

        type_account = "studentBookPayment"

        type_pagenation = get_json_field("type_pagenation")  # book_payments, book_overheads, or None

        # So‘rovlar

        branch_query = BranchPayment.query.filter(BranchPayment.location_id == location)

        overhead_query = CenterBalanceOverhead.query.filter(

            CenterBalanceOverhead.location_id == location,

            CenterBalanceOverhead.deleted == True

        )

        # Faqat shu AccountingPeriod bo‘yicha

        if not type_filter:
            branch_query = branch_query.filter(BranchPayment.account_period_id == accounting_period)

            overhead_query = overhead_query.filter(CenterBalanceOverhead.account_period_id == accounting_period)

        # Paginate bo‘ladimi?

        if type_pagenation == "book_payments":

            book_payments = apply_pagination(branch_query.order_by(BranchPayment.id))

        else:

            book_payments = branch_query.order_by(BranchPayment.id).all()

        if type_pagenation == "book_overheads":

            book_overheads = apply_pagination(overhead_query.order_by(CenterBalanceOverhead.id))

        else:

            book_overheads = overhead_query.order_by(CenterBalanceOverhead.id).all()

        # JSONga aylantirish

        payments_list = {

            "book_payments": [{

                "id": p.id,

                "name": "Kitobchiga pul",

                "price": int(p.order.book.own_price) if p.order and p.order.book else 0,

                "typePayment": p.payment_type.name,

                "date": p.order.day.date.strftime("%Y-%m-%d") if p.order and p.order.day else "",

                "day": str(p.calendar_day),

                "month": str(p.calendar_month),

                "year": str(p.calendar_year),

                "reason": "",

                "type": "book"

            } for p in book_payments],

            "book_overheads": [{

                "id": o.id,

                "name": "Kitob pulidan",

                "price": int(o.payment_sum),

                "typePayment": o.payment_type.name,

                "date": o.day.date.strftime("%Y-%m-%d") if o.day else "",

                "day": str(o.calendar_day),

                "month": str(o.calendar_month),

                "year": str(o.calendar_year),

                "reason": "",

                "type": "book"

            } for o in book_overheads]

        }


    elif type_account == "teacher_salary":
        query = DeletedTeacherSalaries.query.filter(DeletedTeacherSalaries.location_id == location)
        if not type_filter:
            query = query.filter(DeletedTeacherSalaries == accounting_period)

        teacher_salaries = apply_pagination(query.order_by(DeletedTeacherSalaries.id))
        type_account = "user"
        payments_list = [{
            "id": p.id, "name": p.teacher.user.name.title(), "surname": p.teacher.user.surname.title(),
            "salary": p.payment_sum, "typePayment": p.payment_type.name,
            "date": p.day.date.strftime("%Y-%m-%d"),
            "day": str(p.calendar_day), "month": str(p.calendar_month), "year": str(p.calendar_year),
            "user_id": p.teacher.user_id, "reason": p.reason_deleted
        } for p in teacher_salaries]

    elif type_account == "staff_salary":
        query = DeletedStaffSalaries.query.filter(DeletedStaffSalaries.location_id == location)
        if not type_filter:
            query = query.filter(DeletedStaffSalaries.account_period_id == accounting_period)
        staff_salaries = apply_pagination(query.order_by(DeletedStaffSalaries.id))
        type_account = "user"
        payments_list = [{
            "id": p.id, "name": p.staff.user.name.title(), "surname": p.staff.user.surname.title(),
            "salary": p.payment_sum, "typePayment": p.payment_type.name,
            "date": p.day.date.strftime("%Y-%m-%d"),
            "day": str(p.calendar_day), "month": str(p.calendar_month), "year": str(p.calendar_year),
            "user_id": p.staff.user_id, "job": p.profession.name, "reason": p.reason_deleted
        } for p in staff_salaries]

    elif type_account == "discounts":
        query = DeletedStudentPayments.query.filter(
            DeletedStudentPayments.location_id == location,
            DeletedStudentPayments.payment == False
        )
        if not type_filter:
            query = query.filter(DeletedStudentPayments.account_period_id == accounting_period)
        payments = apply_pagination(query.order_by(DeletedStudentPayments.id))
        type_account = "user"
        payments_list = [{
            "id": p.id, "name": p.student.user.name.title(), "surname": p.student.user.surname.title(),
            "payment": p.payment_sum, "typePayment": p.payment_type.name,
            "date": p.day.date.strftime("%Y-%m-%d"),
            "day": str(p.calendar_day), "month": str(p.calendar_month), "year": str(p.calendar_year),
            "user_id": p.student.user_id, "reason": p.reason
        } for p in payments]

    elif type_account == "overhead":
        type_account = ""
        overhead_query = DeletedOverhead.query.filter(DeletedOverhead.location_id == location)
        overhead_center_query = CenterBalanceOverhead.query.filter(
            CenterBalanceOverhead.location_id == location,
            CenterBalanceOverhead.deleted == True
        )
        if not type_filter:
            overhead_query = overhead_query.filter(DeletedOverhead.account_period_id == accounting_period)
            overhead_center_query = overhead_center_query.filter(
                CenterBalanceOverhead.account_period_id == accounting_period
            )

        overheads = apply_pagination(overhead_query.order_by(DeletedOverhead.id))
        center_overheads = apply_pagination(overhead_center_query.order_by(CenterBalanceOverhead.id))

        payments_list = [{
            "id": o.id, "name": o.item_name, "price": int(o.item_sum), "typePayment": o.payment_type.name,
            "date": o.day.date.strftime("%Y-%m-%d"),
            "day": str(o.calendar_day), "month": str(o.calendar_month), "year": str(o.calendar_year),
            "reason": o.reason, "type": "overhead"
        } for o in overheads] + [{
            "id": c.id, "name": "Kitob pulidan", "price": int(c.payment_sum), "typePayment": c.payment_type.name,
            "date": c.day.date.strftime("%Y-%m-%d"),
            "day": str(c.calendar_day), "month": str(c.calendar_month), "year": str(c.calendar_year),
            "reason": "", "type": "book"
        } for c in center_overheads]

    elif type_account == "capital":
        type_account = ""
        # Note: Capital qismini siz izohlab qo‘yibsiz. Agar kerak bo‘lsa, shu joyga query qo‘shiladi.
        payments_list = []
    if isinstance(payments_list, list) and limit:
        total = len(payments_list)
        payments_list = payments_list[offset:offset + limit]
        pagination_data = {
            "total": total,
            "page": offset,
            "limit": limit,
            "has_more": (offset + limit) < total
        }
    elif isinstance(payments_list, dict) and limit:
        pagination_data = {}
        for key in payments_list:
            total = len(payments_list[key])
            payments_list[key] = payments_list[key][offset:offset + limit]
            pagination_data[key] = {
                "total": total,
                "page": offset,
                "limit": limit,
                "has_more": (offset + limit) < total
            }
    else:
        pagination_data = {}

    return jsonify({
        "data": {
            "typeOfMoney": type_account,
            "data": payments_list,
            "overhead_tools": old_current_dates(),
            "capital_tools": old_current_dates(),
            "location": location,
            "pagination": pagination_data,
        }
    })


@account_bp.route(f'/account_details/<int:location_id>', methods=["POST", "GET"])
@jwt_required()
def account_details(location_id):
    """
    function to get account data
    :param location_id: Location table primary key
    :return: account datas  filtering them by date and location_id
    """
    if request.method == "POST":
        ot = request.get_json()['ot']
        do = request.get_json()['do']
        ot = datetime.strptime(ot, "%Y-%m-%d")
        do = datetime.strptime(do, "%Y-%m-%d")
        activeFilter = request.get_json()['activeFilter']
        payment_type = PaymentTypes.query.filter(PaymentTypes.name == activeFilter).first()
        student_payments = db.session.query(StudentPayments).join(StudentPayments.day).options(
            contains_eager(StudentPayments.day)).filter(
            and_(CalendarDay.date >= ot, CalendarDay.date <= do, StudentPayments.location_id == location_id,
                 StudentPayments.payment_type_id == payment_type.id, StudentPayments.payment == True, )).order_by(
            desc(StudentPayments.id)).all()

        all_payment = db.session.query(func.sum(StudentPayments.payment_sum)).join(CalendarDay,
                                                                                   CalendarDay.id == StudentPayments.calendar_day).filter(
            and_(CalendarDay.date >= ot, CalendarDay.date <= do, StudentPayments.location_id == location_id,
                 StudentPayments.payment_type_id == payment_type.id, StudentPayments.payment == True, )).first()[
            0] if student_payments else 0

        investments = db.session.query(Investment).join(Investment.day).options(contains_eager(Investment.day)).filter(
            and_(CalendarDay.date >= ot, CalendarDay.date <= do, Investment.location_id == location_id,
                 Investment.payment_type_id == payment_type.id, Investment.deleted_status == False, )).order_by(
            desc(Investment.id)).all()

        teacher_salaries = db.session.query(TeacherSalaries).join(TeacherSalaries.day).options(
            contains_eager(TeacherSalaries.day)).filter(
            and_(CalendarDay.date >= ot, CalendarDay.date <= do, TeacherSalaries.location_id == location_id,
                 TeacherSalaries.payment_type_id == payment_type.id)).order_by(desc(TeacherSalaries.id)).all()

        all_teacher = db.session.query(func.sum(TeacherSalaries.payment_sum)).join(CalendarDay,
                                                                                   CalendarDay.id == TeacherSalaries.calendar_day).filter(
            and_(CalendarDay.date >= ot, CalendarDay.date <= do, TeacherSalaries.location_id == location_id,
                 TeacherSalaries.payment_type_id == payment_type.id)).first()[0] if teacher_salaries else 0

        staff_salaries = db.session.query(StaffSalaries).join(StaffSalaries.day).options(
            contains_eager(StaffSalaries.day)).filter(
            and_(CalendarDay.date >= ot, CalendarDay.date <= do, StaffSalaries.location_id == location_id,
                 StaffSalaries.payment_type_id == payment_type.id)).order_by(StaffSalaries.id).all()

        all_staff = db.session.query(func.sum(StaffSalaries.payment_sum)).join(CalendarDay,
                                                                               CalendarDay.id == StaffSalaries.calendar_day).filter(
            and_(CalendarDay.date >= ot, CalendarDay.date <= do, StaffSalaries.location_id == location_id,
                 StaffSalaries.payment_type_id == payment_type.id)).first()[0] if staff_salaries else 0
        overhead = db.session.query(Overhead).join(Overhead.day).options(contains_eager(Overhead.day)).filter(
            and_(CalendarDay.date >= ot, CalendarDay.date <= do, Overhead.location_id == location_id,
                 Overhead.payment_type_id == payment_type.id)).order_by(desc(Overhead.id)).all()

        all_overhead = \
            db.session.query(func.sum(Overhead.item_sum)).join(CalendarDay,
                                                               CalendarDay.id == Overhead.calendar_day).filter(
                and_(CalendarDay.date >= ot, CalendarDay.date <= do, Overhead.location_id == location_id,
                     Overhead.payment_type_id == payment_type.id)).first()[0] if overhead else 0

        branch_payments = BranchPayment.query.join(CalendarDay).filter(
            BranchPayment.location_id == location_id, ).filter(
            and_(CalendarDay.date >= ot, CalendarDay.date <= do, BranchPayment.location_id == location_id,
                 BranchPayment.payment_type_id == payment_type.id)).order_by(BranchPayment.id).all()

        branch_payments_all = db.session.query(func.sum(BranchPayment.payment_sum)).join(CalendarDay,
                                                                                         CalendarDay.id == BranchPayment.calendar_day).filter(
            and_(CalendarDay.date >= ot, CalendarDay.date <= do, BranchPayment.location_id == location_id,
                 BranchPayment.payment_type_id == payment_type.id)).first()[0] if branch_payments else 0

        center_balance_overhead = db.session.query(CenterBalanceOverhead).join(CenterBalanceOverhead.day).options(
            contains_eager(CenterBalanceOverhead.day)).filter(CenterBalanceOverhead.location_id == location_id,
                                                              CenterBalanceOverhead.deleted == False).filter(
            and_(CalendarDay.date >= ot, CalendarDay.date <= do,
                 CenterBalanceOverhead.payment_type_id == payment_type.id)).order_by(CenterBalanceOverhead.id).all()

        center_balance_all = db.session.query(func.sum(CenterBalanceOverhead.payment_sum)).join(CalendarDay,
                                                                                                CalendarDay.id == CenterBalanceOverhead.calendar_day).filter(
            and_(CalendarDay.date >= ot, CalendarDay.date <= do, CenterBalanceOverhead.location_id == location_id,
                 CenterBalanceOverhead.payment_type_id == payment_type.id)).first()[0] if center_balance_overhead else 0

        # capitals = db.session.query(Capital).join(Capital.day).options(
        #     contains_eager(Capital.day)).filter(
        #     and_(CalendarDay.date >= ot, CalendarDay.date <= do, Capital.location_id == location_id,
        #          Capital.payment_type_id == payment_type.id
        #          )).order_by(
        #     desc(Capital.id)).all()
        #
        # all_capital = db.session.query(
        #     func.sum(Capital.price
        #              )).join(CalendarDay, CalendarDay.id == Capital.calendar_day).filter(
        #     and_(CalendarDay.date >= ot, CalendarDay.date <= do, Capital.location_id == location_id,
        #          Capital.payment_type_id == payment_type.id
        #          )).first()[0] if capitals else 0

        capitals = db.session.query(CapitalExpenditure).join(CapitalExpenditure.day).options(
            contains_eager(CapitalExpenditure.day)).filter(
            and_(CalendarDay.date >= ot, CalendarDay.date <= do, CapitalExpenditure.location_id == location_id,
                 CapitalExpenditure.payment_type_id == payment_type.id)).order_by(desc(CapitalExpenditure.id)).all()

        all_capital = db.session.query(func.sum(CapitalExpenditure.item_sum)).join(CalendarDay,
                                                                                   CalendarDay.id == CapitalExpenditure.calendar_day).filter(
            and_(CalendarDay.date >= ot, CalendarDay.date <= do, CapitalExpenditure.location_id == location_id,
                 CapitalExpenditure.payment_type_id == payment_type.id)).first()[0] if capitals else 0
        dividends = db.session.query(Dividend).join(Dividend.day).options(contains_eager(Dividend.day)).filter(
            and_(CalendarDay.date >= ot, CalendarDay.date <= do, Dividend.location_id == location_id,
                 Dividend.payment_type_id == payment_type.id, Dividend.deleted == False)).order_by(
            desc(Dividend.id)).all()
        all_dividend = \
            db.session.query(func.sum(Dividend.amount_sum)).join(CalendarDay, CalendarDay.id == Dividend.day_id).filter(
                and_(CalendarDay.date >= ot, CalendarDay.date <= do, Dividend.location_id == location_id,
                     Dividend.deleted == False, Dividend.payment_type_id == payment_type.id, )).first()[
                0] if dividends else 0

        payments_list = [{"id": payment.id, "name": payment.student.user.name.title(),
                          "surname": payment.student.user.surname.title(), "payment": payment.payment_sum,
                          "date": payment.day.date.strftime('%Y-%m-%d'), "user_id": payment.student.user_id} for payment
                         in
                         student_payments]

        teacher_salary = [
            {"id": salary.id, "name": salary.teacher.user.name.title(), "surname": salary.teacher.user.surname.title(),
             "salary": salary.payment_sum, "reason": salary.reason,
             "month": salary.salary.month.date.strftime("%Y-%m") if salary.salary else None,
             "date": salary.day.date.strftime('%Y-%m-%d'), "user_id": salary.teacher.user_id} for salary in
            teacher_salaries]
        staff_salary = [{"id": salary.id, "name": salary.staff.user.name.title() if salary.staff else None,
                         "surname": salary.staff.user.surname if salary.staff else None, "payment": salary.payment_sum,
                         "month": salary.month.date.strftime("%Y-%m"), "date": salary.day.date.strftime('%Y-%m-%d'),
                         "user_id": salary.staff.user_id if salary.staff else None} for salary in staff_salaries]

        overhead_list = [{"id": salary.id, "name": salary.item_name, "payment": salary.item_sum,
                          "date": salary.day.date.strftime('%Y-%m-%d')} for salary in overhead]
        overhead_list += [{"id": branch_payment.id, "name": "Kitobchiga pul ", "payment": branch_payment.payment_sum,
                           "date": branch_payment.day.date.strftime('%Y-%m-%d')} for branch_payment in branch_payments]

        overhead_list += [{"id": branch_payment.id, "name": "Kitob pulidan", "payment": branch_payment.payment_sum,
                           "date": branch_payment.day.date.strftime('%Y-%m-%d')} for branch_payment in
                          center_balance_overhead]
        # capital_list = [{
        #     "id": salary.id,
        #     "name": salary.name,
        #     "payment": salary.price,
        #     "date": salary.day.date.strftime('%Y-%m-%d')
        # } for salary in capitals]

        capital_list = [{"id": salary.id, "name": salary.item_name, "payment": salary.item_sum,
                         "date": salary.day.date.strftime('%Y-%m-%d')} for salary in capitals]
        investment_list = iterate_models(investments)
        # all_investment = all_investment if all_investment else 0
        all_investment = sum([investment.amount for investment in investments])
        result = (all_payment + all_investment) - (
                all_overhead + all_teacher + all_staff + all_capital + center_balance_all + branch_payments_all + all_dividend)
        return jsonify({"data": {"data": {"studentPayment": {"list": payments_list, "value": all_payment},
                                          "teacherSalary": {"list": teacher_salary, "value": all_teacher},
                                          "employeeSalary": {"list": staff_salary, "value": all_staff},
                                          "overheads": {"list": overhead_list, "value": all_overhead},
                                          "capitals": {"list": capital_list, "value": all_capital},
                                          "investments": {"list": investment_list, "value": all_investment},
                                          "dividends": {"list": iterate_models(dividends), "value": all_dividend},
                                          "result": result}, }})


@account_bp.route(f'/get_location_money/<int:location_id>')
@jwt_required()
def get_location_money(location_id):
    """

    :param location_id: Location table primary key
    :return:
    """

    accounting_period = AccountingPeriod.query.join(CalendarMonth).order_by(desc(CalendarMonth.id)).first()
    # accounting_period = db.session.query(AccountingPeriod).join(AccountingPeriod.month).options(
    #     contains_eager(AccountingPeriod.month)).filter(AccountingPeriod.id == 11).order_by(
    #     desc(CalendarMonth.id)).first()

    # periods = AccountingPeriod.query.order_by(
    #     AccountingPeriod.id).all()
    # print(periods)
    # payments = StudentPayments.query.filter(StudentPayments.location_id == 1).order_by(StudentPayments.id).all()
    # payments = TeacherSalaries.query.order_by(TeacherSalaries.id).all()
    # payments = StaffSalaries.query.order_by(StaffSalaries.id).all()
    # payments = Overhead.query.order_by(Overhead.id).all()
    # payments = CapitalExpenditure.query.order_by(CapitalExpenditure.id).all()
    # payments = StudentCharity.query.order_by(StudentCharity.id).all()
    # #
    # print(len(payments))
    # counter = 0
    # for payment in payments:
    #
    #     for period in periods:
    #         if payment.day.date >= period.from_date and payment.day.date <= period.to_date:
    #             # counter += 1
    #             if payment.account_period_id != period.id:
    #                 payment.account_period_id = period.id
    #                 db.session.commit()
    # print("tugadi")
    # print(periods)
    # for period in periods:
    #     # from_month_year = period.from_date.strftime("%Y-%m") + "-11"
    #     # to_month_year = period.to_date.strftime("%Y-%m") + "-10"
    #     # from_month_year = datetime.strptime(from_month_year, "%Y-%m-%d")
    #     # to_month_year = datetime.strptime(to_month_year, "%Y-%m-%d")
    #     # AccountingPeriod.query.filter(AccountingPeriod.id == period.id).update({
    #     #     "from_date": from_month_year,
    #     #     "to_date": to_month_year
    #     # })
    #     # db.session.commit()
    #     month_period = period.from_date.strftime("%Y-%m")
    #     month_period = datetime.strptime(month_period, "%Y-%m")
    #     month = CalendarMonth.query.filter(CalendarMonth.date == month_period).first()
    #     # print(month.id)
    #     print("bosh", period.from_date, period.to_date, period.month.id)
    #     period.month_id = month.id
    #     db.session.commit()
    #     print(period.id)

    payment_types = PaymentTypes.query.order_by(PaymentTypes.id).all()

    account_list = []
    for payment_type in payment_types:
        student_payments = sum_money(StudentPayments.payment_sum, StudentPayments.account_period_id,
                                     accounting_period.id, StudentPayments.location_id, location_id,
                                     StudentPayments.payment_type_id, payment_type.id, type_payment="payment",
                                     status_payment=True)
        student_discounts = sum_money(StudentPayments.payment_sum, StudentPayments.account_period_id,
                                      accounting_period.id, StudentPayments.location_id, location_id,
                                      StudentPayments.payment_type_id, payment_type.id, type_payment="payment",
                                      status_payment=False)
        # book_payments = sum_money(BookPayments.payment_sum, BookPayments.account_period_id, accounting_period.id,
        #                           BookPayments.location_id, location_id, BookPayments)
        teacher_salaries = sum_money(TeacherSalaries.payment_sum, TeacherSalaries.account_period_id,
                                     accounting_period.id, TeacherSalaries.location_id, location_id,
                                     TeacherSalaries.payment_type_id, payment_type.id)
        staff_salaries = sum_money(StaffSalaries.payment_sum, StaffSalaries.account_period_id, accounting_period.id,
                                   StaffSalaries.location_id, location_id, StaffSalaries.payment_type_id,
                                   payment_type.id)
        overhead = sum_money(Overhead.item_sum, Overhead.account_period_id, accounting_period.id, Overhead.location_id,
                             location_id, Overhead.payment_type_id, payment_type.id)
        dividends = db.session.query(Dividend).join(Dividend.day).options(contains_eager(Dividend.day)).filter(
            and_(Dividend.location_id == location_id, Dividend.account_period_id == accounting_period.id,
                 Dividend.payment_type_id == payment_type.id, Dividend.deleted == False)).order_by(
            desc(Dividend.id)).all()
        all_dividend = \
            db.session.query(func.sum(Dividend.amount_sum)).join(CalendarDay, CalendarDay.id == Dividend.day_id).filter(
                and_(Dividend.location_id == location_id, Dividend.deleted == False,
                     Dividend.account_period_id == accounting_period.id,
                     Dividend.payment_type_id == payment_type.id, )).first()[0] if dividends else 0
        # center_balance = CenterBalance.query.filter(CenterBalance.location_id == location_id,
        #                                             CenterBalance.account_period_id == accounting_period).first()

        # center_balance_sum =

        branch_payments = db.session.query(func.sum(BranchPayment.payment_sum)).filter(
            BranchPayment.location_id == location_id, BranchPayment.account_period_id == accounting_period.id,
            BranchPayment.payment_type_id == payment_type.id).first()
        center_balance_overhead = db.session.query(func.sum(CenterBalanceOverhead.payment_sum)).filter(
            CenterBalanceOverhead.location_id == location_id,
            CenterBalanceOverhead.account_period_id == accounting_period.id, CenterBalanceOverhead.deleted == False,
            CenterBalanceOverhead.payment_type_id == payment_type.id).first()
        # capital = sum_money(Capital.price, Capital.account_period_id,
        #                     accounting_period.id, Capital.location_id, location_id,
        #                     Capital.payment_type_id, payment_type.id,
        #                     )
        capital = sum_money(CapitalExpenditure.item_sum, CapitalExpenditure.account_period_id, accounting_period.id,
                            CapitalExpenditure.location_id, location_id, CapitalExpenditure.payment_type_id,
                            payment_type.id, )
        if branch_payments[0]:
            branch_payments = branch_payments[0]
        else:
            branch_payments = 0

        if center_balance_overhead[0]:
            center_balance_overhead = center_balance_overhead[0]
        else:
            center_balance_overhead = 0

        current_cash = student_payments - (
                teacher_salaries + staff_salaries + overhead + capital + center_balance_overhead + branch_payments + all_dividend)

        account_list += [{"value": current_cash, "type": payment_type.name, "student_payments": student_payments,
                          "teacher_salaries": teacher_salaries, "staff_salaries": staff_salaries,
                          "overhead": overhead + branch_payments + center_balance_overhead, "capital": capital,
                          "dividend": all_dividend}]

        account_get = AccountingInfo.query.filter(AccountingInfo.account_period_id == accounting_period.id,
                                                  AccountingInfo.location_id == location_id,
                                                  AccountingInfo.payment_type_id == payment_type.id,
                                                  AccountingInfo.calendar_year == accounting_period.year_id).first()

        # if not account_get:  #     add = AccountingInfo(account_period_id=accounting_period.id, all_payments=student_payments,  #                          location_id=location_id, all_teacher_salaries=teacher_salaries,  #                          all_dividend=all_dividend,  #                          payment_type_id=payment_type.id, all_staff_salaries=staff_salaries,  #                          all_overhead=overhead + branch_payments + center_balance_overhead, all_capital=capital,  #                          all_charity=student_discounts, current_cash=current_cash,  #                          calendar_year=accounting_period.year_id)  #     add.add()  # else:  #     account_get.all_payments = student_payments  #     account_get.all_teacher_salaries = teacher_salaries  #     account_get.all_staff_salaries = staff_salaries  #     account_get.all_overhead = overhead + branch_payments + center_balance_overhead  #     account_get.all_capital = capital  #     account_get.all_charity = student_discounts  #     account_get.current_cash = current_cash  #     account_get.all_dividend = all_dividend  #     accounting_period.all_investment = 0  # db.session.commit()

    return jsonify({"data": account_list})


@account_bp.route(f'/account_history/<int:location_id>', methods=['POST'])
def account_history(location_id):
    """
    function to get account data year and payment type
    :param location_id: Location table primary key
    :return:
    """

    if request.method == "POST":
        year = get_json_field('year')
        payment_type = get_json_field('activeFilter')

        year = datetime.strptime(year, '%Y')
        year = CalendarYear.query.filter(CalendarYear.date == year).first()
        payment_type = PaymentTypes.query.filter(PaymentTypes.name == payment_type).first()

        account_infos = AccountingInfo.query.filter(AccountingInfo.location_id == location_id,
                                                    AccountingInfo.payment_type_id == payment_type.id,
                                                    AccountingInfo.calendar_year == year.id).order_by(
            desc(AccountingInfo.id)).all()
        account_list = [
            {"id": account.id, "month": account.period.month.date.strftime("%h"), "type": account.payment_type.name,
             "payment": account.all_payments, "teacherSalary": account.all_teacher_salaries,
             "employeesSalary": account.all_staff_salaries, "overheads": account.all_overhead,
             "capitalExpenditures": account.all_capital, "current_cash": account.current_cash,
             "old_cash": account.old_cash, "period_id": account.account_period_id, "discount": account.all_charity,
             "dividend": account.all_dividend} for account in account_infos]

        return jsonify({"data": account_list, })


@account_bp.route(f'/account_years/<int:location_id>')
def account_years(location_id):
    """

    :param location_id: Location table primary key
    :return: year list
    """

    # for data in account_datas:
    #     db.session.delete(data)
    #     db.session.commit()

    # account_period = AccountingPeriod.query.filter(AccountingPeriod.student_payments != None).order_by(
    #     AccountingPeriod.id).all()
    # payment_types = PaymentTypes.query.order_by(PaymentTypes.id).all()
    # for period in account_period:
    #     print(f"{period.from_date}   {period.to_date}")
    #     for payment_type in payment_types:
    #         student_payments = sum_money(StudentPayments.payment_sum, StudentPayments.account_period_id,
    #                                      period.id, StudentPayments.location_id, location_id,
    #                                      StudentPayments.payment_type_id, payment_type.id, type_payment="payment",
    #                                      status_payment=True)
    #         student_discounts = sum_money(StudentPayments.payment_sum, StudentPayments.account_period_id,
    #                                       period.id, StudentPayments.location_id, location_id,
    #                                       StudentPayments.payment_type_id, payment_type.id, type_payment="payment",
    #                                       status_payment=False)
    #         teacher_salaries = sum_money(TeacherSalaries.payment_sum, TeacherSalaries.account_period_id,
    #                                      period.id, TeacherSalaries.location_id, location_id,
    #                                      TeacherSalaries.payment_type_id, payment_type.id)
    #         staff_salaries = sum_money(StaffSalaries.payment_sum, StaffSalaries.account_period_id,
    #                                    period.id, StaffSalaries.location_id, location_id,
    #                                    StaffSalaries.payment_type_id, payment_type.id)
    #         overhead = sum_money(Overhead.item_sum, Overhead.account_period_id,
    #                              period.id, Overhead.location_id, location_id,
    #                              Overhead.payment_type_id, payment_type.id)
    #         capital = sum_money(CapitalExpenditure.item_sum, CapitalExpenditure.account_period_id,
    #                             period.id, CapitalExpenditure.location_id, location_id,
    #                             CapitalExpenditure.payment_type_id, payment_type.id,
    #                             )
    #         current_cash = student_payments - (teacher_salaries + staff_salaries + overhead + capital)
    #         account_get = AccountingInfo.query.filter(AccountingInfo.account_period_id == period.id,
    #                                                   AccountingInfo.location_id == location_id,
    #                                                   AccountingInfo.payment_type_id == payment_type.id,
    #                                                   AccountingInfo.calendar_year == period.year_id).first()
    #
    #         if not account_get:
    #             add = AccountingInfo(account_period_id=period.id, all_payments=student_payments,
    #                                  location_id=location_id, all_teacher_salaries=teacher_salaries,
    #                                  payment_type_id=payment_type.id, all_staff_salaries=staff_salaries,
    #                                  all_overhead=overhead, all_capital=capital, all_charity=student_discounts,
    #                                  calendar_year=period.year_id)
    #             add.add()
    #         else:
    #             account_get.all_payments = student_payments
    #             account_get.all_teacher_salaries = teacher_salaries
    #             account_get.all_staff_salaries = staff_salaries
    #             account_get.all_overhead = overhead
    #             account_get.all_capital = capital
    #             account_get.all_charity = student_discounts
    #             account_get.current_cash = current_cash
    #             db.session.commit()

    year_list = []
    account_datas = AccountingInfo.query.order_by(AccountingInfo.location_id == location_id).all()
    for data in account_datas:
        year_list.append(data.year.date.strftime("%Y"))
    year_list = list(dict.fromkeys(year_list))
    return jsonify({"years": year_list})
