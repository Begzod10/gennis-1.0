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


def get_flask_app():
    """Lazy import Flask app to avoid circular imports"""
    import sys
    import os

    # Add project root to path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # ✅ Import create_app function directly, not the app variable
    from app import create_app

    # ✅ Call create_app() to get Flask app
    flask_app = create_app()

    # ✅ Verify we got a Flask app, not Celery
    from flask import Flask
    if not isinstance(flask_app, Flask):
        raise TypeError(f"Expected Flask app, got {type(flask_app)}")

    return flask_app


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
            print(f"✅ Flask app loaded: {type(self._app)}")  # Debug
        return self._app

    def __call__(self, *args, **kwargs):
        # ✅ Add error checking
        flask_app = self.flask_app

        if not hasattr(flask_app, 'app_context'):
            raise AttributeError(f"Object {type(flask_app)} doesn't have app_context. Expected Flask app.")

        with flask_app.app_context():
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
