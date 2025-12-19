# celery_app.py
from celery import Celery, shared_task, group
from celery.schedules import crontab
from dotenv import load_dotenv
import os
import sys

load_dotenv()

# Create Celery instance
celery = Celery(
    'gennis',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/2'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/2'),
    include=[
        'backend.celery.tasks',
        'backend.celery.lead_calls',
        'backend.celery.debt_calls',
        'backend.celery.new_students'
    ]  # ✅ Changed from 'tasks' to 'backend.celery.tasks'
)

# Configure Celery
# celery_app.py
celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Tashkent',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # ✅ 30 minutes hard limit (buffer above 20 min calls)
    task_soft_time_limit=25 * 60,  # ✅ 25 minutes soft limit
    worker_pool='solo' if sys.platform == 'win32' else 'prefork',
    worker_concurrency=1 if sys.platform == 'win32' else None,
)

# Schedule
celery.conf.beat_schedule = {
    'update-branch-reports-every-minute': {
        'task': 'update_branch_reports',
        'schedule': crontab(hour=20, minute="0"),
        'options': {'expires': 3600}
    },
}


def init_celery(app):
    """Initialize Celery with Flask app context"""
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery
