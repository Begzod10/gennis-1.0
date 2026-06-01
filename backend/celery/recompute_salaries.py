import logging
from datetime import datetime

import pytz

from backend.celery.celery_app import celery
from backend.functions.debt_salary_update import update_teacher_salary
from backend.models.models import CalendarMonth, TeacherSalary, db

logger = logging.getLogger(__name__)


def _tashkent_now():
    return datetime.now(pytz.timezone('Asia/Tashkent'))


@celery.task(name='recompute_open_month_teacher_salaries')
def recompute_open_month_teacher_salaries():
    """
    Nightly safety net: force-recompute every TeacherSalary row in the
    current (Tashkent) month so it matches the attendance + black-salary
    + fines + taken_money state on disk. Catches drift introduced by
    code paths that mutate attendance/payment data without calling
    salary_debt or update_teacher_salary inline.

    Idempotent: rerunning on already-consistent rows is a no-op.
    """
    try:
        now = _tashkent_now()
        month_date = now.date().replace(day=1)

        calendar_month = CalendarMonth.query.filter_by(date=month_date).first()
        if not calendar_month:
            logger.info(
                f"recompute_open_month_teacher_salaries: no CalendarMonth "
                f"for {month_date}, skipping"
            )
            return {'success': True, 'processed': 0, 'failed': 0, 'month': str(month_date)}

        salary_rows = TeacherSalary.query.filter(
            TeacherSalary.calendar_month == calendar_month.id
        ).all()

        processed = 0
        failed = 0
        for row in salary_rows:
            try:
                update_teacher_salary(teacher_id=row.teacher_id, salary_id=row.id)
                processed += 1
            except Exception as row_exc:
                db.session.rollback()
                failed += 1
                logger.error(
                    f"recompute_open_month_teacher_salaries: row {row.id} "
                    f"(teacher {row.teacher_id}, loc {row.location_id}) "
                    f"failed: {row_exc}"
                )

        logger.info(
            f"recompute_open_month_teacher_salaries: month {month_date}, "
            f"processed={processed}, failed={failed}, total={len(salary_rows)}"
        )
        return {
            'success': True,
            'month': str(month_date),
            'total': len(salary_rows),
            'processed': processed,
            'failed': failed,
        }

    except Exception as exc:
        db.session.rollback()
        logger.error(f"recompute_open_month_teacher_salaries failed: {exc}")
        return {'success': False, 'error': str(exc)}
