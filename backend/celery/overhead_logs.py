import logging
from datetime import datetime

import pytz

from backend.celery.celery_app import celery
from backend.functions.utils import get_or_create
from backend.models.models import (
    CalendarYear, CalendarMonth, OverheadType, OverheadTypeLog, db
)

logger = logging.getLogger(__name__)


def _tashkent_now():
    return datetime.now(pytz.timezone('Asia/Tashkent'))


@celery.task(name='generate_monthly_overhead_logs')
def generate_monthly_overhead_logs():
    """
    Runs on the 1st of every month.
    Creates OverheadTypeLog entries for all fixed (non-changeable) overhead types
    for the new month so admins have a ready reminder list.
    """
    try:
        now = _tashkent_now()
        month_date = now.date().replace(day=1)
        year_date = now.date().replace(month=1, day=1)

        year, _ = get_or_create(db.session, CalendarYear, date=year_date)
        db.session.flush()
        year = CalendarYear.query.filter_by(date=year_date).first()
        month, _ = get_or_create(db.session, CalendarMonth, date=month_date, year_id=year.id)
        db.session.flush()

        fixed_types = OverheadType.query.filter(
            OverheadType.changeable == False,
            OverheadType.cost != None,
            OverheadType.deleted == False
        ).all()

        created = 0
        for ot in fixed_types:
            exists = OverheadTypeLog.query.filter_by(
                overhead_type_id=ot.id,
                location_id=ot.location_id,
                calendar_month=month.id,
                calendar_year=year.id
            ).first()
            if not exists:
                log = OverheadTypeLog(
                    overhead_type_id=ot.id,
                    cost=ot.cost,
                    is_paid=False,
                    is_prepaid=False,
                    location_id=ot.location_id,
                    calendar_month=month.id,
                    calendar_year=year.id
                )
                db.session.add(log)
                created += 1

        db.session.commit()

        logger.info(f"generate_monthly_overhead_logs: created {created} logs for {month_date}")
        return {'success': True, 'created': created, 'month': str(month_date)}

    except Exception as exc:
        db.session.rollback()
        logger.error(f"generate_monthly_overhead_logs failed: {exc}")
        return {'success': False, 'error': str(exc)}
