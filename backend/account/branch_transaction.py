from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import desc, or_

from backend.functions.filters import old_current_dates
from backend.functions.utils import find_calendar_date
from backend.models.models import (
    BranchTransaction,
    CalendarDay,
    CalendarMonth,
    CalendarYear,
    PaymentTypes,
    Users,
    db,
    func,
)

branch_transaction_bp = Blueprint('branch_transaction_bp', __name__)


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

@branch_transaction_bp.route('/branch_transaction', methods=['POST'])
@jwt_required()
def create_branch_transaction():
    """
    Body:
        amount          — integer
        is_give         — bool (True = gave out, False = received)
        reason          — string (optional)
        payment_type_id — PaymentTypes.id
        location_id     — Locations.id
        date            — 'YYYY-MM-DD'

        Person (one of the two):
            person_id                        — Users.id (system user)
            person_name / person_surname / person_phone  — manual entry
    """
    data = request.get_json()

    amount = data.get('amount')
    is_give = data.get('is_give')
    reason = data.get('reason')
    payment_type_id = data.get('payment_type_id')
    location_id = data.get('location_id')
    date_str = data.get('date')

    person_id = data.get('person_id')
    person_name = data.get('person_name')
    person_surname = data.get('person_surname')
    person_phone = data.get('person_phone')

    if amount is None or is_give is None or not payment_type_id or not location_id or not date_str:
        return jsonify({'success': False, 'message': 'amount, is_give, payment_type_id, location_id, date kerak'}), 400

    if not person_id and not person_name:
        return jsonify({'success': False, 'message': 'person_id yoki person_name kerak'}), 400

    if person_id and person_name:
        return jsonify({'success': False, 'message': 'person_id va person_name ikkalasini birga yuborish mumkin emas'}), 400

    day_dt = datetime.strptime(date_str, '%Y-%m-%d')
    month_dt = day_dt.replace(day=1)
    year_dt = day_dt.replace(month=1, day=1)
    calendar_year, calendar_month, calendar_day = find_calendar_date(
        date_day=day_dt.date(),
        date_month=month_dt.date(),
        date_year=year_dt.date()
    )

    current_user = Users.query.filter_by(user_id=get_jwt_identity()).first()
    tx = BranchTransaction(
        amount=amount,
        is_give=is_give,
        reason=reason,
        payment_type_id=payment_type_id,
        location_id=location_id,
        calendar_day=calendar_day.id,
        calendar_month=calendar_month.id,
        calendar_year=calendar_year.id,
        created_by=current_user.id if current_user else None,
        person_id=person_id,
        person_name=person_name if not person_id else None,
        person_surname=person_surname if not person_id else None,
        person_phone=person_phone if not person_id else None,
    )
    db.session.add(tx)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': "Tranzaksiya qo'shildi",
        'data': tx.convert_json()
    }), 201


# ---------------------------------------------------------------------------
# List with filters + summary
# ---------------------------------------------------------------------------

@branch_transaction_bp.route('/branch_transaction/<int:month>/<int:year>', methods=['GET'])
@jwt_required()
def get_branch_transactions(month, year):
    """
    Query params:
        direction   — 'give' | 'receive' | 'all' (default: all)
        location_id — filter by branch (optional)
    """
    from datetime import date
    year_obj = CalendarYear.query.filter_by(date=date(year, 1, 1)).first()
    month_obj = CalendarMonth.query.filter_by(date=date(year, month, 1)).first() if year_obj else None

    if not year_obj or not month_obj:
        return jsonify({'success': True, 'summary': {'total_given': 0, 'total_received': 0, 'net': 0}, 'data': []})

    month_id = month_obj.id
    year_id = year_obj.id

    direction = request.args.get('direction', 'all')
    location_id = request.args.get('location_id', type=int)

    query = BranchTransaction.query.filter_by(
        calendar_month=month_id,
        calendar_year=year_id,
        deleted=False
    )

    if location_id:
        query = query.filter(BranchTransaction.location_id == location_id)

    if direction == 'give':
        query = query.filter(BranchTransaction.is_give == True)
    elif direction == 'receive':
        query = query.filter(BranchTransaction.is_give == False)

    transactions = query.order_by(BranchTransaction.id.desc()).all()

    give_filters = [
        BranchTransaction.calendar_month == month_id,
        BranchTransaction.calendar_year == year_id,
        BranchTransaction.deleted == False,
        BranchTransaction.is_give == True,
    ]
    receive_filters = [
        BranchTransaction.calendar_month == month_id,
        BranchTransaction.calendar_year == year_id,
        BranchTransaction.deleted == False,
        BranchTransaction.is_give == False,
    ]
    if location_id:
        give_filters.append(BranchTransaction.location_id == location_id)
        receive_filters.append(BranchTransaction.location_id == location_id)

    total_given = db.session.query(
        func.coalesce(func.sum(BranchTransaction.amount), 0)
    ).filter(*give_filters).scalar()

    total_received = db.session.query(
        func.coalesce(func.sum(BranchTransaction.amount), 0)
    ).filter(*receive_filters).scalar()

    return jsonify({
        'success': True,
        'summary': {
            'total_given': total_given,
            'total_received': total_received,
            'net': total_received - total_given
        },
        'data': [tx.convert_json() for tx in transactions]
    })


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

@branch_transaction_bp.route('/branch_transaction/<int:tx_id>', methods=['PUT'])
@jwt_required()
def update_branch_transaction(tx_id):
    tx = BranchTransaction.query.get_or_404(tx_id)
    data = request.get_json()

    if 'amount' in data:
        tx.amount = data['amount']
    if 'is_give' in data:
        tx.is_give = data['is_give']
    if 'reason' in data:
        tx.reason = data['reason']
    if 'payment_type_id' in data:
        tx.payment_type_id = data['payment_type_id']
    if 'person_id' in data:
        tx.person_id = data['person_id']
        tx.person_name = None
        tx.person_surname = None
        tx.person_phone = None
    elif 'person_name' in data:
        tx.person_id = None
        tx.person_name = data.get('person_name')
        tx.person_surname = data.get('person_surname')
        tx.person_phone = data.get('person_phone')

    db.session.commit()
    return jsonify({
        'success': True,
        'message': 'Tranzaksiya yangilandi',
        'data': tx.convert_json()
    })


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

@branch_transaction_bp.route('/branch_transaction/<int:tx_id>', methods=['DELETE'])
@jwt_required()
def delete_branch_transaction(tx_id):
    tx = BranchTransaction.query.get_or_404(tx_id)
    tx.deleted = True
    db.session.commit()
    return jsonify({'success': True, 'message': "Tranzaksiya o'chirildi"})


# ---------------------------------------------------------------------------
# Deleted list
# ---------------------------------------------------------------------------

@branch_transaction_bp.route('/branch_transaction/deleted/<int:month>/<int:year>', methods=['GET'])
@jwt_required()
def get_deleted_branch_transactions(month, year):
    """
    Query params:
        location_id  — filter by branch (optional)
        payment_type — PaymentTypes.name (optional)
        is_give      — 'true' | 'false' (optional)
        direction    — 'give' | 'receive' (alias for is_give, optional)
        amount_min   — int (optional)
        amount_max   — int (optional)
        loan_id      — int (optional); pass 'null' to filter rows without a loan
        search       — substring in reason / person name / surname (optional)
        limit, offset — pagination (optional)
    """
    from datetime import date
    year_obj = CalendarYear.query.filter_by(date=date(year, 1, 1)).first()
    month_obj = CalendarMonth.query.filter_by(date=date(year, month, 1)).first() if year_obj else None

    if not year_obj or not month_obj:
        return jsonify({'success': True, 'total': 0, 'data': []})

    location_id = request.args.get('location_id', type=int)
    payment_type_name = request.args.get('payment_type')
    is_give_param = request.args.get('is_give')
    direction = (request.args.get('direction') or '').strip().lower()
    amount_min = request.args.get('amount_min', type=int)
    amount_max = request.args.get('amount_max', type=int)
    loan_id_raw = request.args.get('loan_id')
    search = (request.args.get('search') or '').strip()
    limit = request.args.get('limit', type=int)
    offset = request.args.get('offset', default=0, type=int)

    query = BranchTransaction.query.filter_by(
        calendar_month=month_obj.id,
        calendar_year=year_obj.id,
        deleted=True
    )

    if location_id:
        query = query.filter(BranchTransaction.location_id == location_id)

    if payment_type_name:
        pt = PaymentTypes.query.filter_by(name=payment_type_name).first()
        if pt:
            query = query.filter(BranchTransaction.payment_type_id == pt.id)
        else:
            query = query.filter(False)

    is_give_val = None
    if is_give_param is not None:
        v = str(is_give_param).strip().lower()
        if v in ('true', '1', 'yes'):
            is_give_val = True
        elif v in ('false', '0', 'no'):
            is_give_val = False
    if direction == 'give':
        is_give_val = True
    elif direction == 'receive':
        is_give_val = False
    if is_give_val is not None:
        query = query.filter(BranchTransaction.is_give == is_give_val)

    if amount_min is not None:
        query = query.filter(BranchTransaction.amount >= amount_min)
    if amount_max is not None:
        query = query.filter(BranchTransaction.amount <= amount_max)

    if loan_id_raw is not None:
        if str(loan_id_raw).strip().lower() == 'null':
            query = query.filter(BranchTransaction.loan_id.is_(None))
        else:
            try:
                query = query.filter(BranchTransaction.loan_id == int(loan_id_raw))
            except (TypeError, ValueError):
                pass

    if search:
        like = f"%{search}%"
        query = query.outerjoin(Users, Users.id == BranchTransaction.person_id).filter(
            or_(
                BranchTransaction.reason.ilike(like),
                BranchTransaction.person_name.ilike(like),
                BranchTransaction.person_surname.ilike(like),
                Users.name.ilike(like),
                Users.surname.ilike(like),
            )
        )

    total = query.count()
    query = query.order_by(BranchTransaction.id.desc())
    if offset:
        query = query.offset(offset)
    if limit:
        query = query.limit(limit)

    transactions = query.all()
    return jsonify({
        'success': True,
        'total': total,
        'data': [tx.convert_json() for tx in transactions]
    })


# ---------------------------------------------------------------------------
# account_info/branch_transaction (paginated, account-info shape)
# ---------------------------------------------------------------------------

@branch_transaction_bp.route('/account_info/branch_transaction/', methods=['GET'])
@jwt_required()
def account_info_branch_transaction():
    """
    Mirrors /account_info/staff_salary/ shape.
    Query params:
        locationId   — required: filial ID
        paymentType  — optional: PaymentTypes.name
        year, month, day — optional: calendar IDs
        deleted      — optional: 1 = soft-deleted only
        direction    — optional: 'give' | 'receive'
        is_give      — optional: 'true' | 'false'
        limit, offset — pagination
    """
    location = request.args.get('locationId', type=int)
    payment_type_name = request.args.get('paymentType')
    year_id = request.args.get('year', type=int)
    month_id = request.args.get('month', type=int)
    day_id = request.args.get('day', type=int)
    deleted = request.args.get('deleted', type=int)
    direction = (request.args.get('direction') or '').strip().lower()
    is_give_param = request.args.get('is_give')

    limit = request.args.get('limit', type=int)
    offset = request.args.get('offset', default=0, type=int)

    if not location:
        return jsonify({'success': False, 'message': 'locationId kerak'}), 400

    query = BranchTransaction.query.filter(BranchTransaction.location_id == location)

    if deleted:
        query = query.filter(BranchTransaction.deleted == True)
    else:
        query = query.filter(BranchTransaction.deleted == False)

    if payment_type_name:
        payment_type_obj = PaymentTypes.query.filter_by(name=payment_type_name).first()
        if payment_type_obj:
            query = query.filter(BranchTransaction.payment_type_id == payment_type_obj.id)
        else:
            # No payment type with that name — return empty rather than ignoring
            query = query.filter(False)

    if year_id:
        query = query.filter(BranchTransaction.calendar_year == year_id)
    if month_id:
        query = query.filter(BranchTransaction.calendar_month == month_id)
    if day_id:
        query = query.filter(BranchTransaction.calendar_day == day_id)

    if direction == 'give':
        query = query.filter(BranchTransaction.is_give == True)
    elif direction == 'receive':
        query = query.filter(BranchTransaction.is_give == False)
    elif is_give_param is not None:
        if str(is_give_param).lower() in ('true', '1'):
            query = query.filter(BranchTransaction.is_give == True)
        elif str(is_give_param).lower() in ('false', '0'):
            query = query.filter(BranchTransaction.is_give == False)

    query = query.order_by(desc(BranchTransaction.id))

    total = query.count()

    given_total = db.session.query(func.coalesce(func.sum(BranchTransaction.amount), 0)).filter(
        BranchTransaction.location_id == location,
        BranchTransaction.deleted == bool(deleted),
        BranchTransaction.is_give == True,
    ).scalar()
    received_total = db.session.query(func.coalesce(func.sum(BranchTransaction.amount), 0)).filter(
        BranchTransaction.location_id == location,
        BranchTransaction.deleted == bool(deleted),
        BranchTransaction.is_give == False,
    ).scalar()

    if limit:
        query = query.offset(offset).limit(limit)

    transactions = query.all()

    payments_list = [tx.convert_json() for tx in transactions]

    pagination_data = {
        "total": total,
        "page": offset,
        "limit": limit,
        "has_more": (offset + (limit or total)) < total,
    } if limit else None

    return jsonify({
        "data": {
            "typeOfMoney": "branch_transaction",
            "data": payments_list,
            "pagination": pagination_data,
            "summary": {
                "total_given": int(given_total or 0),
                "total_received": int(received_total or 0),
                "net": int((received_total or 0) - (given_total or 0)),
            },
            "overhead_tools": old_current_dates(observation=True),
            "capital_tools": old_current_dates(observation=True),
            "location": location,
        }
    })
