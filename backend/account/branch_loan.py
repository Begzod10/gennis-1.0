from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import desc

from backend.functions.utils import find_calendar_date
from backend.models.models import (
    BranchLoan,
    BranchTransaction,
    PaymentTypes,
    Users,
    db,
    func,
)

branch_loan_bp = Blueprint('branch_loan_bp', __name__)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _parse_date(s):
    try:
        return datetime.strptime(s, '%Y-%m-%d').date() if s else None
    except (TypeError, ValueError):
        return None


def _resolve_counterparty(data):
    cp_id = data.get('counterparty_id')
    cp_name = data.get('counterparty_name')

    if cp_id and cp_name:
        return None, "counterparty_id va counterparty_name ikkalasini birga yuborish mumkin emas"
    if not cp_id and not cp_name:
        return None, "counterparty_id yoki counterparty_name kerak"

    if cp_id:
        cp = Users.query.get(cp_id)
        if not cp:
            return None, "Foydalanuvchi topilmadi"
        return {'user_id': cp.id}, None
    return {
        'name': cp_name,
        'surname': data.get('counterparty_surname'),
        'phone': data.get('counterparty_phone'),
    }, None


def _current_user_id():
    user = Users.query.filter_by(user_id=get_jwt_identity()).first()
    return user.id if user else None


# ---------------------------------------------------------------------------
# Create loan + initial transaction
# ---------------------------------------------------------------------------

@branch_loan_bp.route('/branch_loans/', methods=['POST'])
@jwt_required()
def create_loan():
    """
    Body:
        location_id, direction ('out'|'in'), principal_amount, issued_date YYYY-MM-DD,
        payment_type_id, due_date? YYYY-MM-DD, reason?, notes?,
        counterparty_id  XOR  counterparty_name (+ surname/phone)
    """
    data = request.get_json() or {}

    for field in ('location_id', 'direction', 'principal_amount', 'issued_date', 'payment_type_id'):
        if data.get(field) in (None, ''):
            return jsonify({'success': False, 'message': f"{field} kerak"}), 400

    direction = str(data.get('direction')).strip().lower()
    if direction not in ('out', 'in'):
        return jsonify({'success': False, 'message': "direction 'out' yoki 'in' bo'lishi kerak"}), 400

    try:
        principal = int(data.get('principal_amount'))
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': "principal_amount noto'g'ri"}), 400
    if principal <= 0:
        return jsonify({'success': False, 'message': "principal_amount > 0 bo'lishi kerak"}), 400

    issued_date = _parse_date(data.get('issued_date'))
    if not issued_date:
        return jsonify({'success': False, 'message': "issued_date YYYY-MM-DD"}), 400

    due_date = _parse_date(data.get('due_date')) if data.get('due_date') else None

    if not PaymentTypes.query.get(data['payment_type_id']):
        return jsonify({'success': False, 'message': "To'lov turi topilmadi"}), 404

    cp, err = _resolve_counterparty(data)
    if err:
        return jsonify({'success': False, 'message': err}), 400

    # Resolve calendar refs for the disbursement transaction
    calendar_year, calendar_month, calendar_day = find_calendar_date(
        date_day=issued_date,
        date_month=issued_date.replace(day=1),
        date_year=issued_date.replace(month=1, day=1),
    )

    creator_id = _current_user_id()

    loan = BranchLoan(
        location_id=data['location_id'],
        counterparty_id=cp.get('user_id'),
        counterparty_name=cp.get('name'),
        counterparty_surname=cp.get('surname'),
        counterparty_phone=cp.get('phone'),
        direction=direction,
        principal_amount=principal,
        issued_date=issued_date,
        due_date=due_date,
        reason=data.get('reason'),
        notes=data.get('notes'),
        status='active',
        created_by=creator_id,
    )
    db.session.add(loan)
    db.session.flush()  # populate loan.id

    tx = BranchTransaction(
        amount=principal,
        is_give=(direction == 'out'),
        reason=data.get('reason'),
        person_id=cp.get('user_id'),
        person_name=cp.get('name'),
        person_surname=cp.get('surname'),
        person_phone=cp.get('phone'),
        payment_type_id=data['payment_type_id'],
        location_id=data['location_id'],
        calendar_day=calendar_day.id,
        calendar_month=calendar_month.id,
        calendar_year=calendar_year.id,
        created_by=creator_id,
        loan_id=loan.id,
    )
    db.session.add(tx)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Qarz yaratildi',
        'data': loan.convert_json(with_transactions=True),
    }), 201


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

@branch_loan_bp.route('/branch_loans/', methods=['GET'])
@jwt_required()
def list_loans():
    location_id = request.args.get('location_id', type=int) or request.args.get('locationId', type=int)
    status_param = request.args.get('status')
    direction = request.args.get('direction')
    counterparty_id = request.args.get('counterparty_id', type=int)
    limit = request.args.get('limit', type=int)
    offset = request.args.get('offset', default=0, type=int)

    if not location_id:
        return jsonify({'success': False, 'message': 'location_id kerak'}), 400

    q = BranchLoan.query.filter(
        BranchLoan.location_id == location_id,
        BranchLoan.deleted == False,
    )

    if status_param in ('active', 'settled', 'cancelled'):
        q = q.filter(BranchLoan.status == status_param)
    if direction in ('out', 'in'):
        q = q.filter(BranchLoan.direction == direction)
    if counterparty_id:
        q = q.filter(BranchLoan.counterparty_id == counterparty_id)

    q = q.order_by(desc(BranchLoan.id))
    total = q.count()

    if limit:
        q = q.offset(offset).limit(limit)

    rows = q.all()

    return jsonify({
        'success': True,
        'data': {
            'data': [l.convert_json() for l in rows],
            'pagination': {
                'total': total,
                'page': offset,
                'limit': limit,
                'has_more': (offset + (limit or total)) < total,
            } if limit else None,
            'location': location_id,
        },
    })


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------

@branch_loan_bp.route('/branch_loans/<int:loan_id>/', methods=['GET'])
@jwt_required()
def get_loan(loan_id):
    loan = BranchLoan.query.filter_by(id=loan_id, deleted=False).first()
    if not loan:
        return jsonify({'success': False, 'message': 'Qarz topilmadi'}), 404
    return jsonify({'success': True, 'data': loan.convert_json(with_transactions=True)})


# ---------------------------------------------------------------------------
# Update terms
# ---------------------------------------------------------------------------

@branch_loan_bp.route('/branch_loans/<int:loan_id>/', methods=['PATCH'])
@jwt_required()
def update_loan(loan_id):
    loan = BranchLoan.query.filter_by(id=loan_id, deleted=False).first()
    if not loan:
        return jsonify({'success': False, 'message': 'Qarz topilmadi'}), 404
    if loan.status == 'cancelled':
        return jsonify({'success': False, 'message': "Bekor qilingan qarzni o'zgartirib bo'lmaydi"}), 400

    data = request.get_json() or {}
    if 'due_date' in data:
        if data['due_date']:
            d = _parse_date(data['due_date'])
            if not d:
                return jsonify({'success': False, 'message': "due_date YYYY-MM-DD"}), 400
            loan.due_date = d
        else:
            loan.due_date = None
    if 'reason' in data:
        loan.reason = data['reason']
    if 'notes' in data:
        loan.notes = data['notes']

    db.session.commit()
    return jsonify({
        'success': True,
        'message': 'Yangilandi',
        'data': loan.convert_json(with_transactions=True),
    })


# ---------------------------------------------------------------------------
# Repay
# ---------------------------------------------------------------------------

@branch_loan_bp.route('/branch_loans/<int:loan_id>/repay/', methods=['POST'])
@jwt_required()
def repay_loan(loan_id):
    loan = BranchLoan.query.filter_by(id=loan_id, deleted=False).first()
    if not loan:
        return jsonify({'success': False, 'message': 'Qarz topilmadi'}), 404
    if loan.status == 'cancelled':
        return jsonify({'success': False, 'message': "Bekor qilingan qarzga to'lov qilib bo'lmaydi"}), 400

    data = request.get_json() or {}

    try:
        amount = int(data.get('amount'))
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': "amount kerak"}), 400
    if amount <= 0:
        return jsonify({'success': False, 'message': "amount > 0 bo'lishi kerak"}), 400

    payment_type_id = data.get('payment_type_id')
    if not payment_type_id or not PaymentTypes.query.get(payment_type_id):
        return jsonify({'success': False, 'message': "To'lov turi topilmadi"}), 404

    date = _parse_date(data.get('date'))
    if not date:
        return jsonify({'success': False, 'message': "date YYYY-MM-DD"}), 400

    calendar_year, calendar_month, calendar_day = find_calendar_date(
        date_day=date,
        date_month=date.replace(day=1),
        date_year=date.replace(month=1, day=1),
    )

    creator_id = _current_user_id()
    tx = BranchTransaction(
        amount=amount,
        is_give=(loan.direction == 'in'),  # repayment is opposite direction of loan
        reason=data.get('reason'),
        person_id=loan.counterparty_id,
        person_name=loan.counterparty_name,
        person_surname=loan.counterparty_surname,
        person_phone=loan.counterparty_phone,
        payment_type_id=payment_type_id,
        location_id=loan.location_id,
        calendar_day=calendar_day.id,
        calendar_month=calendar_month.id,
        calendar_year=calendar_year.id,
        created_by=creator_id,
        loan_id=loan.id,
    )
    db.session.add(tx)
    db.session.flush()

    # refresh transactions collection for paid_total recompute
    db.session.refresh(loan)
    loan.recompute_status()
    db.session.commit()

    return jsonify({
        'success': True,
        'message': "To'lov qabul qilindi",
        'data': loan.convert_json(with_transactions=True),
    }), 201


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------

@branch_loan_bp.route('/branch_loans/<int:loan_id>/cancel/', methods=['POST'])
@jwt_required()
def cancel_loan(loan_id):
    loan = BranchLoan.query.filter_by(id=loan_id, deleted=False).first()
    if not loan:
        return jsonify({'success': False, 'message': 'Qarz topilmadi'}), 404

    reason = (request.get_json() or {}).get('cancelled_reason', '').strip()
    if not reason:
        return jsonify({'success': False, 'message': "cancelled_reason kerak"}), 400

    loan.status = 'cancelled'
    loan.cancelled_reason = reason
    loan.settled_date = None
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Qarz bekor qilindi',
        'data': loan.convert_json(with_transactions=True),
    })


# ---------------------------------------------------------------------------
# Outstanding (per counterparty)
# ---------------------------------------------------------------------------

@branch_loan_bp.route('/branch_loans/outstanding/', methods=['GET'])
@jwt_required()
def outstanding_loans():
    location_id = request.args.get('location_id', type=int) or request.args.get('locationId', type=int)
    direction = request.args.get('direction')

    if not location_id:
        return jsonify({'success': False, 'message': 'location_id kerak'}), 400

    q = BranchLoan.query.filter(
        BranchLoan.location_id == location_id,
        BranchLoan.deleted == False,
        BranchLoan.status == 'active',
    )
    if direction in ('out', 'in'):
        q = q.filter(BranchLoan.direction == direction)

    loans = q.order_by(BranchLoan.issued_date, BranchLoan.id).all()

    groups = {}
    for loan in loans:
        cp_key = loan.counterparty_id or f"manual:{loan.counterparty_name}|{loan.counterparty_phone}"
        key = (loan.location_id, loan.direction, cp_key)
        paid = loan.paid_total()
        payload = loan.convert_json()

        entry = groups.setdefault(key, {
            'counterparty': loan.counterparty_payload(),
            'location_id': loan.location_id,
            'direction': loan.direction,
            'loaned_total': 0,
            'paid_total': 0,
            'outstanding': 0,
            'open_loans': [],
        })
        entry['loaned_total'] += payload['principal_amount']
        entry['paid_total'] += paid
        entry['outstanding'] += payload['remaining_amount']
        entry['open_loans'].append(payload)

    return jsonify({
        'success': True,
        'data': [g for g in groups.values() if g['outstanding'] > 0],
    })
