# backend/celery/worker.py
"""
Celery Worker Startup Script
Run from backend/celery directory: python worker.py
"""
import os
import sys

# Add project root to Python path FIRST
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Set as environment variable too
os.environ['PYTHONPATH'] = project_root

print("=" * 60)
print("[INIT] Python path: {}".format(project_root))
print("[INIT] Importing Flask app...")

# Import Flask app
from app import app as flask_app

print("[OK] Flask app imported")
print("[INIT] Initializing Celery...")

# Import from current directory (celery_app.py is in same folder)
from celery_app import celery, init_celery

# Initialize with Flask context
init_celery(flask_app)

print("[OK] Celery initialized with Flask app context")
print("=" * 60)

# Start worker
if __name__ == '__main__':
    celery.worker_main(['worker', '--loglevel=info', '--pool=solo'])