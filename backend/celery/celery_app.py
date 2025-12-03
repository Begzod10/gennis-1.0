# celery_app.py - SIMPLEST VERSION (No Auto-Import, No Circular Dependency)
from celery import Celery
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
    include=['tasks']
)

# Configure Celery
celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Tashkent',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,
    worker_pool='solo' if sys.platform == 'win32' else 'prefork',
    worker_concurrency=1 if sys.platform == 'win32' else None,
)

# Schedule
celery.conf.beat_schedule = {
    'update-branch-reports-every-minute': {
        'task': 'update_branch_reports',
        'schedule': crontab(minute="*/1"),
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

