from flask import Flask, send_from_directory, jsonify, request
from backend.school.models import register_commands
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from backend.models.models import db_setup
from flask_migrate import Migrate
from flask_restful import Api
from flask_admin import Admin
import logging
import hmac
import hashlib
import subprocess
from flask import Response
from backend.parent.views import register_parent_views
from backend.functions.utils import refreshdatas
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

from backend.time_table.views import register_time_table_views
from backend.student.views import register_student_views
from backend.teacher.views import register_teacher_views

from backend.group.views import register_group_views

from backend.lead.views import register_lead_views
from backend.home_page.views import register_home_views
from backend.account.views import register_account_views
from backend.book.views import register_book_views
from backend.student.register_for_tes.views import register_for_tes_views
from backend.school.views import register_school_views
from backend.routes.views import register_router_views
from backend.mobile.views import register_parent_mobile_views
from backend.for_programmers.views import register_programmers_views

register_time_table_views(api, app)
register_router_views(api, app)
register_parent_views(api, app)
register_task_rating_views(api, app)
register_student_views(api, app)
register_telegram_bot_routes(api, app)
register_teacher_views(api, app)
register_group_views(api, app)
register_lead_views(api, app)
register_home_views(api, app)
register_account_views(api, app)
register_book_views(api, app)
register_for_tes_views(api, app)
register_school_views(api, app)
register_parent_mobile_views(api, app)
register_programmers_views(api, app)


# register_classroom_views(api, app)


# functions folder

# classroom


def check_auth(username, password):
    return username == 'rimefara' and password == 'top12'


def authenticate():
    return Response(
        'Unauthorized access.', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})


@app.errorhandler(404)
def not_found(e):
    return app.send_static_file('index.html')


@app.errorhandler(413)
def img_larger(e):
    return jsonify({
        "success": False,
        "msg": "rasm hajmi kotta"
    })


@app.route('/', methods=['POST', 'GET'])
def index():
    refreshdatas()
    return app.send_static_file("index.html")


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
