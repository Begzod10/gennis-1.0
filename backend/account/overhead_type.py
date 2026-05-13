from datetime import datetime

import pytz
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from backend.functions.utils import find_calendar_date, get_or_create
from backend.models.models import (
    CalendarMonth, CalendarYear, CalendarDay,
    Overhead, OverheadType, OverheadTypeLog, Users, db, func
)

overhead_type_bp = Blueprint('overhead_type_bp', __name__)


def _tashkent_now():
    return datetime.now(pytz.timezone('Asia/Tashkent'))


def _resolve_month_year(month_str):
    """
    Given 'YYYY-MM' string, get_or_create CalendarYear and CalendarMonth.
    Returns (CalendarYear, CalendarMonth).
    """
    month_dt = datetime.strptime(month_str, '%Y-%m')
    year_dt = month_dt.replace(month=1, day=1)
    month_date = month_dt.date().replace(day=1)
    year_date = year_dt.date()

    year, _ = get_or_create(db.session, CalendarYear, date=year_date)
    db.session.flush()
    year = CalendarYear.query.filter_by(date=year_date).first()
    month, _ = get_or_create(db.session, CalendarMonth, date=month_date, year_id=year.id)
    db.session.flush()
    return year, month


def _generate_logs_for_month(month_id, year_id, location_id=None):
    """Create OverheadTypeLog entries for every fixed overhead type that doesn't have one yet."""
    query = OverheadType.query.filter(
        OverheadType.changeable == False,
        OverheadType.cost != None,
        OverheadType.deleted == False
    )
    if location_id is not None:
        query = query.filter(OverheadType.location_id == location_id)

    for ot in query.all():
        exists = OverheadTypeLog.query.filter_by(
            overhead_type_id=ot.id,
            location_id=location_id,
            calendar_month=month_id,
            calendar_year=year_id
        ).first()
        if not exists:
            log = OverheadTypeLog(
                overhead_type_id=ot.id,
                cost=ot.cost,
                is_paid=False,
                is_prepaid=False,
                location_id=location_id,
                calendar_month=month_id,
                calendar_year=year_id
            )
            db.session.add(log)
    db.session.commit()


# ---------------------------------------------------------------------------
# OverheadType — list only (CRUD managed by management project)
# ---------------------------------------------------------------------------

@overhead_type_bp.route('/overhead_type', methods=['GET'])
@jwt_required()
def get_overhead_types():
    """List active overhead types. Pass ?location_id= to scope to one location."""
    location_id = request.args.get('location_id', type=int)
    query = OverheadType.query.filter_by(deleted=False)
    if location_id:
        query = query.filter(OverheadType.location_id == location_id)
    types = query.order_by(OverheadType.id).all()
    return jsonify({
        'success': True,
        'data': [{
            'id': t.id,
            'name': t.name,
            'cost': t.cost,
            'changeable': t.changeable,
            'location_id': t.location_id,
        } for t in types]
    })


@overhead_type_bp.route('/overhead_type/<int:overhead_type_id>', methods=['PATCH'])
@jwt_required()
def update_overhead_type(overhead_type_id):
    """Update `changeable` and/or `cost` on a single Gennis OverheadType row.

    Only these two fields are accepted — `name` stays owned by the management
    project and is propagated from there. Pass at least one field in the body.
    """
    ot = OverheadType.query.filter_by(id=overhead_type_id, deleted=False).first()
    if not ot:
        return jsonify({'success': False, 'message': 'Overhead type not found'}), 404

    data = request.get_json(silent=True) or {}
    updated = False

    if 'changeable' in data:
        if not isinstance(data['changeable'], bool):
            return jsonify({'success': False, 'message': '`changeable` must be a boolean'}), 400
        ot.changeable = data['changeable']
        updated = True

    if 'cost' in data:
        cost = data['cost']
        if cost is not None and not isinstance(cost, int):
            return jsonify({'success': False, 'message': '`cost` must be an integer or null'}), 400
        ot.cost = cost
        updated = True

    if not updated:
        return jsonify({'success': False, 'message': 'No updatable fields provided'}), 400

    db.session.commit()
    return jsonify({
        'success': True,
        'data': {
            'id': ot.id,
            'name': ot.name,
            'cost': ot.cost,
            'changeable': ot.changeable,
            'location_id': ot.location_id,
            'management_id': ot.management_id,
        },
    })


# ---------------------------------------------------------------------------
# OverheadTypeLog — reminders
# ---------------------------------------------------------------------------

@overhead_type_bp.route('/overhead_type_logs/<int:month>/<int:year>', methods=['GET'])
@jwt_required()
def get_overhead_type_logs(month, year):
    """
    Return the reminder list for a given month filtered by paid status.
    Auto-generates missing log entries.

    Query params:
        status — 'paid' | 'unpaid' | 'all' (default: 'all')
    """
    from datetime import date
    year_obj = CalendarYear.query.filter_by(date=date(year, 1, 1)).first()
    month_obj = CalendarMonth.query.filter_by(date=date(year, month, 1)).first() if year_obj else None

    if not year_obj or not month_obj:
        return jsonify({'success': True, 'summary': {'total_count': 0, 'paid_count': 0, 'unpaid_count': 0, 'total_sum': 0, 'paid_sum': 0, 'unpaid_sum': 0}, 'data': []})

    month_id = month_obj.id
    year_id = year_obj.id

    location_id = request.args.get('location_id', type=int)
    status = request.args.get('status', 'all')

    _generate_logs_for_month(month_id, year_id, location_id)

    base_filters = [
        OverheadTypeLog.calendar_month == month_id,
        OverheadTypeLog.calendar_year == year_id,
        OverheadTypeLog.deleted == False,
    ]
    if location_id:
        base_filters.append(OverheadType.location_id == location_id)

    base_query = OverheadTypeLog.query.join(
        OverheadType, OverheadType.id == OverheadTypeLog.overhead_type_id
    ).filter(*base_filters)

    query = base_query
    if status == 'paid':
        query = query.filter(OverheadTypeLog.is_paid == True)
    elif status == 'unpaid':
        query = query.filter(OverheadTypeLog.is_paid == False)

    logs = query.order_by(OverheadTypeLog.id).all()

    total_count = base_query.count()
    paid_count = base_query.filter(OverheadTypeLog.is_paid == True).count()

    total_sum = base_query.with_entities(
        func.coalesce(func.sum(OverheadTypeLog.cost), 0)
    ).scalar()

    paid_sum = base_query.filter(OverheadTypeLog.is_paid == True).with_entities(
        func.coalesce(func.sum(OverheadTypeLog.cost), 0)
    ).scalar()

    return jsonify({
        'success': True,
        'summary': {
            'total_count': total_count,
            'paid_count': paid_count,
            'unpaid_count': total_count - paid_count,
            'total_sum': total_sum,
            'paid_sum': paid_sum,
            'unpaid_sum': total_sum - paid_sum
        },
        'data': [log.convert_json() for log in logs]
    })


@overhead_type_bp.route('/overhead_type_logs/generate/<int:month>/<int:year>', methods=['POST'])
@jwt_required()
def generate_overhead_type_logs(month, year):
    """Manually trigger log generation for a month."""
    from datetime import date
    year_obj = CalendarYear.query.filter_by(date=date(year, 1, 1)).first()
    month_obj = CalendarMonth.query.filter_by(date=date(year, month, 1)).first() if year_obj else None
    if not year_obj or not month_obj:
        return jsonify({'success': False, 'message': 'Oy yoki yil topilmadi'}), 404
    _generate_logs_for_month(month_obj.id, year_obj.id)
    return jsonify({'success': True, 'message': 'Loglar yaratildi'})


# ---------------------------------------------------------------------------
# Pay — covers both same-month payment and prepayment for a future month.
#
# For same-month: pass log_id of the current month's log.
# For prepayment: pass overhead_type_id + paid_for_month ("YYYY-MM").
#   The system finds or creates the future month's log and marks it prepaid.
#   The current month's log stays untouched (still needs to be paid separately).
# ---------------------------------------------------------------------------

@overhead_type_bp.route('/overhead_type_logs/pay', methods=['POST'])
@jwt_required()
def pay_overhead_type_log():
    """
    Body:
        payment_type_id     — PaymentTypes.id
        location_id         — Locations.id
        date                — payment date 'YYYY-MM-DD'

        Same-month payment:
            log_id          — OverheadTypeLog.id to mark as paid

        Prepayment for a future month:
            overhead_type_id — OverheadType.id
            paid_for_month   — 'YYYY-MM' of the month being paid for
    """
    data = request.get_json()
    payment_type_id = data.get('payment_type_id')
    location_id = data.get('location_id')
    date_str = data.get('date')
    log_id = data.get('log_id')
    overhead_type_id = data.get('overhead_type_id')
    paid_for_month_str = data.get('paid_for_month')

    is_prepaid = paid_for_month_str is not None
    current_user = Users.query.filter_by(user_id=get_jwt_identity()).first()
    current_user_id = current_user.id if current_user else None

    if not is_prepaid and not log_id:
        return jsonify({'success': False, 'message': 'log_id yoki paid_for_month kerak'}), 400
    if is_prepaid and not overhead_type_id:
        return jsonify({'success': False, 'message': 'paid_for_month bilan overhead_type_id kerak'}), 400

    # resolve actual payment date
    day_dt = datetime.strptime(date_str, '%Y-%m-%d')
    month_dt = day_dt.replace(day=1)
    year_dt = day_dt.replace(month=1, day=1)
    calendar_year, calendar_month, calendar_day = find_calendar_date(
        date_day=day_dt.date(),
        date_month=month_dt.date(),
        date_year=year_dt.date()
    )

    now = _tashkent_now()

    if is_prepaid:
        ot = OverheadType.query.get_or_404(overhead_type_id)
        if ot.changeable:
            return jsonify({'success': False, 'message': 'Changeable overhead type prepay qilib bolmaydi'}), 400

        target_year, target_month = _resolve_month_year(paid_for_month_str)

        target_log = OverheadTypeLog.query.filter_by(
            overhead_type_id=ot.id,
            calendar_month=target_month.id,
            calendar_year=target_year.id
        ).first()

        if target_log and target_log.is_paid:
            return jsonify({'success': False, 'message': 'Bu oy allaqachon to\'langan'}), 400

        if not target_log:
            target_log = OverheadTypeLog(
                overhead_type_id=ot.id,
                cost=ot.cost,
                location_id=location_id,
                calendar_month=target_month.id,
                calendar_year=target_year.id
            )
            db.session.add(target_log)
            db.session.flush()

        overhead = Overhead(
            item_sum=ot.cost,
            item_name=ot.name,
            overhead_type_id=ot.id,
            payment_type_id=payment_type_id,
            location_id=location_id,
            calendar_day=calendar_day.id,
            calendar_month=calendar_month.id,
            calendar_year=calendar_year.id,
            paid_for_month=target_month.id,
            paid_for_year=target_year.id,
            by_who=current_user_id
        )
        db.session.add(overhead)
        db.session.flush()

        target_log.is_paid = True
        target_log.is_prepaid = True
        target_log.paid_date = now
        target_log.overhead_id = overhead.id
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f"{ot.name} oldindan to'landi",
            'overhead': overhead.convert_json(),
            'log': target_log.convert_json()
        })

    else:
        log = OverheadTypeLog.query.get_or_404(log_id)
        if log.is_paid:
            return jsonify({'success': False, 'message': 'Bu overhead allaqachon to\'langan'}), 400

        overhead = Overhead(
            item_sum=log.cost,
            item_name=log.overhead_type.name,
            overhead_type_id=log.overhead_type_id,
            payment_type_id=payment_type_id,
            location_id=location_id,
            calendar_day=calendar_day.id,
            calendar_month=calendar_month.id,
            calendar_year=calendar_year.id,
            paid_for_month=None,
            paid_for_year=None,
            by_who=current_user_id
        )
        db.session.add(overhead)
        db.session.flush()

        log.is_paid = True
        log.is_prepaid = False
        log.paid_date = now
        log.overhead_id = overhead.id
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f"{log.overhead_type.name} to'landi",
            'overhead': overhead.convert_json(),
            'log': log.convert_json()
        })
