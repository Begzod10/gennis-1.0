from flask import Flask, jsonify, request, render_template, session, json, send_file, send_from_directory
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from backend.school.models import custom_migrate, register_commands
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from backend.models.models import *
from flask_restful import Api
from flask_admin import Admin
import logging
import hmac
import hashlib
import subprocess
from flask import request, Response
from backend.parent.views import register_parent_views

from backend.telegram_bot.views import register_telegram_bot_routes
import os
from dotenv import load_dotenv

load_dotenv()



# from backend.class_room.urls import register_classroom_views


GITHUB_SECRET = b''  # optional
logging.basicConfig(level=logging.DEBUG)

app = Flask(
    __name__,
    static_folder="frontend/build",  # React build
    static_url_path="/"  # Serve React from root
)

CORS(app, resources={r"/api/*": {"origins": "*"}})

app.config.from_object('backend.models.config')
db = db_setup(app)
apis = Api(app)

migrate = Migrate(app, db)
jwt = JWTManager(app)
register_commands(app)
admin = Admin(
    app,
    name='Gennis',
    template_mode='bootstrap3',
    static_url_path='/flask_static'
)

classroom_server = os.getenv("CLASSROOM_SERVER_URL")

school_server = os.getenv("SCHOOL_SERVER_URL")

api = 'api/'
from backend.tasks.admin.views import register_task_rating_views
from backend.student.views import register_student_views
from backend.teacher.views import register_teacher_views
from backend.lead.views import register_lead_views
from backend.home_page.views import register_home_views
from backend.account.views import register_account_views
from backend.book.views import register_book_views
from backend.student.register_for_tes.views import register_for_tes_views
from backend.school.views import register_school_views
from backend.functions.views import register_filters_views

register_parent_views(api, app)
register_task_rating_views(api, app)
register_student_views(api, app)
register_telegram_bot_routes(api, app)
register_teacher_views(api, app)
register_lead_views(api, app)
register_home_views(api, app)
register_account_views(api, app)
register_book_views(api, app)
register_for_tes_views(api, app)
register_school_views(api, app)
register_filters_views(api, app)
# register_classroom_views(api, app)



# filters



# functions folder
from backend.functions.checks import *
from backend.functions.small_info import *

# QR code
from backend.QR_code.qr_code import *

# routes
from backend.routes.views import *

# programmers
from backend.for_programmers.for_programmers import *


# group
from backend.group.create_group import *
from backend.group.view import *
from backend.group.change import *
from backend.group.test import *

# time_table
from backend.time_table.view import *
from backend.time_table.room import *


# certificate
from backend.certificate.views import *
# get api
from backend.routes.get_api import *

# classroom
from backend.class_room.views import *

# bot
from backend.telegram_bot.views import *





# mobile
from backend.mobile.views import *

# tasks
from backend.tasks.admin.views import *





from backend.models.views import *


# teacher observation, attendance, teacher_group_statistics


def check_auth(username, password):
    return username == 'rimefara' and password == 'top12'


def authenticate():
    return Response(
        'Unauthorized access.', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})


@app.before_request
def require_auth_for_admin():
    if request.path.startswith('/admin'):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()


@app.route('/flask_static/<path:filename>')
def flask_admin_static(filename):
    return send_from_directory('static', filename)


@app.route("/api/payload", methods=["POST"])
def payload():
    # (Optional) verify signature
    if GITHUB_SECRET:
        signature = request.headers.get("X-Hub-Signature-256")
        body = request.get_data()
        expected = 'sha256=' + hmac.new(GITHUB_SECRET, body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            return "Invalid signature", 403

    # Run deploy script
    subprocess.Popen(["/home/gennis/deploy_bot.sh"])
    repo_path = "/home/gennis/gennis_bot"
    pull_result = subprocess.run(
        ["git", "pull"],
        cwd=repo_path,
        capture_output=True,
        text=True
    )
    return "Updated", 200


if __name__ == '__main__':
    app.run()
