# celery_app.py - Production Ready with Auto Flask Context
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
    include=['tasks']  # Load tasks from tasks.py
)

# Configure Celery
celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Tashkent',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes

    # Windows compatibility
    worker_pool='solo' if sys.platform == 'win32' else 'prefork',
    worker_concurrency=1 if sys.platform == 'win32' else None,
)

# Schedule: Every minute for testing
# Change to crontab(hour=20, minute=0) for daily at 8 PM
celery.conf.beat_schedule = {
    'update-branch-reports-every-minute': {
        'task': 'update_branch_reports',
        'schedule': crontab(minute="*/1"),  # Every minute
        # For production (daily at 20:00):
        # 'schedule': crontab(hour=20, minute=0),
        'options': {
            'expires': 3600,
        }
    },
}


def init_celery(app):
    """
    Initialize Celery with Flask app context
    Call this from Flask app: init_celery(app)
    """
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    import tasks  # noqa
    return celery


# =============================================================================
# AUTO-INITIALIZATION: Sets up Flask context when running celery worker directly
# =============================================================================
try:
    # Add project root to Python path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # Import Flask app
    from app import app as flask_app


    # Wrap all Celery tasks with Flask app context
    class FlaskTask(celery.Task):
        """Custom task class that runs in Flask application context"""

        def __call__(self, *args, **kwargs):
            with flask_app.app_context():
                return self.run(*args, **kwargs)


    # Apply FlaskTask to all tasks
    celery.Task = FlaskTask

    # Import tasks after context is configured
    import tasks  # noqa

    print("=" * 60)
    print("✓ Flask app context initialized for Celery tasks")
    print("✓ Database operations will work correctly")
    print("=" * 60)

except ImportError as e:
    print("=" * 60)
    print(f"⚠ Warning: Could not import Flask app: {e}")
    print("⚠ Make sure 'app.py' exists at project root")
    print("⚠ Tasks requiring Flask context may fail")
    print("=" * 60)

except Exception as e:
    print("=" * 60)
    print(f"⚠ Warning: Could not auto-initialize Flask context: {e}")
    print("⚠ You may need to call init_celery(app) manually")
    print("=" * 60)