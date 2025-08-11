import os
<<<<<<< HEAD
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
=======
from datetime import timedelta
>>>>>>> 58726dd6176e228405343c91f5e3898ebe141e6e

load_dotenv()
SECRET_KEY = os.urandom(32)
# Grabs the folder where the script runs.
basedir = os.path.abspath(os.path.dirname(__file__))

DEBUG = True

DB_USER = os.getenv('FLASK_DB_USER', 'postgres')
DB_PASSWORD = os.getenv('FLASK_DB_PASSWORD', '123')
<<<<<<< HEAD
# DB_HOST = os.getenv('FLASK_DB_HOST', 'localhost:5433')
DB_HOST = os.getenv('DB_HOST', 'localhost:5432')
=======
DB_HOST = os.getenv('FLASK_DB_HOST', 'localhost')
>>>>>>> 58726dd6176e228405343c91f5e3898ebe141e6e
DB_NAME = os.getenv('FLASK_DB_NAME', 'gennis')
DB_PORT = os.getenv('FLASK_DB_PORT', '5432')

database_path = 'postgresql://{}:{}@{}:{}/{}'.format(DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME)
SQLALCHEMY_DATABASE_URI = database_path
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ECO = True
MAX_CONTENT_LENGTH = 26 * 1000 * 1000
JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
JWT_SECRET_KEY = "gennis_revolution"
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
FLASK_ENV = "development"
FLASK_DEBUG = 1
TEMPLATES_AUTO_RELOAD = True
SEND_FILE_MAX_AGE_DEFAULT = 0
