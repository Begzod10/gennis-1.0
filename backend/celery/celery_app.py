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
    ]
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
        'schedule': crontab(hour=20, minute="0"),
        'options': {'expires': 3600}
    },
}


# ✅ DEFINE get_flask_app BEFORE using it
def get_flask_app():
    """Lazy import Flask app to avoid circular imports"""
    import sys
    import os

    # Add project root to path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # Import Flask app
    from app import create_app

    # Create and return app instance
    return create_app()


class ContextTask(celery.Task):
    """
    Custom task class that ensures Flask app context is available
    in all Celery task executions
    """
    _app = None

    @property
    def flask_app(self):
        """Lazy load Flask app (only create once)"""
        if self._app is None:
            self._app = get_flask_app()
        return self._app

    def __call__(self, *args, **kwargs):
        with self.flask_app.app_context():
            return self.run(*args, **kwargs)


# Set the default task class
celery.Task = ContextTask


# For Flask app initialization (when calling tasks from routes)
def init_celery(app):
    """
    Initialize Celery with Flask app config (only needed in Flask app)
    This is for when you call celery tasks from Flask routes
    """
    celery.conf.update(app.config)
    return celery


celery.Task = ContextTask


# Optional: Keep init_celery for Flask app initialization
def init_celery(app):
    """
    Initialize Celery with Flask app config (only needed in Flask app)
    This is for when you call celery tasks from Flask routes
    """
    celery.conf.update(app.config)
    return celery
