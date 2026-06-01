import logging
from datetime import datetime

import pytz

from backend.celery.celery_app import celery
from backend.functions.debt_salary_update import update_teacher_salary, update_assistent_salary
from backend.models.models import AssistentSalary, CalendarMonth, TeacherSalary, db

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

        teacher_rows = TeacherSalary.query.filter(
            TeacherSalary.calendar_month == calendar_month.id
        ).all()
        assistent_rows = AssistentSalary.query.filter(
            AssistentSalary.calendar_month == calendar_month.id
        ).all()

        t_processed = 0
        t_failed = 0
        for row in teacher_rows:
            try:
                update_teacher_salary(teacher_id=row.teacher_id, salary_id=row.id)
                t_processed += 1
            except Exception as row_exc:
                db.session.rollback()
                t_failed += 1
                logger.error(
                    f"recompute_open_month_teacher_salaries: teacher row {row.id} "
                    f"(teacher {row.teacher_id}, loc {row.location_id}) "
                    f"failed: {row_exc}"
                )

        a_processed = 0
        a_failed = 0
        for row in assistent_rows:
            try:
                update_assistent_salary(assistent_id=row.assisten_id, salary_id=row.id)
                a_processed += 1
            except Exception as row_exc:
                db.session.rollback()
                a_failed += 1
                logger.error(
                    f"recompute_open_month_teacher_salaries: assistent row {row.id} "
                    f"(assistent {row.assisten_id}, loc {row.location_id}) "
                    f"failed: {row_exc}"
                )

        logger.info(
            f"recompute_open_month_teacher_salaries: month {month_date}, "
            f"teachers processed={t_processed} failed={t_failed} total={len(teacher_rows)}, "
            f"assistents processed={a_processed} failed={a_failed} total={len(assistent_rows)}"
        )
        return {
            'success': True,
            'month': str(month_date),
            'teachers': {
                'total': len(teacher_rows),
                'processed': t_processed,
                'failed': t_failed,
            },
            'assistents': {
                'total': len(assistent_rows),
                'processed': a_processed,
                'failed': a_failed,
            },
        }

    except Exception as exc:
        db.session.rollback()
        logger.error(f"recompute_open_month_teacher_salaries failed: {exc}")
        return {'success': False, 'error': str(exc)}
