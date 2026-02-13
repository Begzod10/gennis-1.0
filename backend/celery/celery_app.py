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
        'backend.celery.new_students',
        'backend.celery.check_lesson_plan'
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
    'check-lesson-plans-daily': {
        'task': 'check_lesson_plans',
        # 'schedule': crontab(hour=21, minute="0"),
        'schedule': crontab(minute="*/1"),
        'options': {'expires': 3600}
    },
}


def get_flask_app():
    """Lazy import Flask app to avoid circular imports"""
    import sys
    import os

    # Add project root to path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # ✅ Import the create_app factory
    import app as app_module

    # ✅ Call the factory to create Flask app
    flask_application = app_module.create_app()

    return flask_application


class ContextTask(celery.Task):
    """
    Custom task class that ensures Flask app context is available
    in all Celery task executions
    """
    _flask_app_instance = None  # ✅ More explicit name

    @property
    def flask_app(self):
        """Lazy load Flask app (only create once)"""
        if self._flask_app_instance is None:
            import logging
            logger = logging.getLogger(__name__)

            self._flask_app_instance = get_flask_app()
            logger.info(f"Flask app loaded: {type(self._flask_app_instance).__name__}")

            # Verify it's a Flask app
            if not hasattr(self._flask_app_instance, 'app_context'):
                logger.error(f"ERROR: Got {type(self._flask_app_instance)}, not Flask app!")
                raise TypeError(f"Expected Flask app, got {type(self._flask_app_instance)}")

        return self._flask_app_instance

    def __call__(self, *args, **kwargs):
        with self.flask_app.app_context():
            return self.run(*args, **kwargs)


# Set the default task class
celery.Task = ContextTask


# For Flask app initialization (when calling tasks from routes)
def init_celery(flask_app):
    """
    Initialize Celery with Flask app config
    """
    celery.conf.update(flask_app.config)
    return celery
