from flask import Flask, jsonify, request, render_template, session, json, send_file, send_from_directory
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from backend.school.models import custom_migrate, register_commands
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from backend.models.models import *
from flask_restful import Api
# from flask_admin import Admin
import logging
import hmac
import hashlib
import os
import subprocess

from backend.parent.views import register_parent_views

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
# admin = Admin(
#     app,
#     name='Gennis',
#     template_mode='bootstrap3',
#     static_url_path='/flask_static'
# )


# classroom_server = "http://192.168.1.15:5001"

classroom_server = "https://classroom.gennis.uz"
# telegram_bot_server = "http://127.0.0.1:5000"
django_server = "https://school.gennis.uz"
# django_server = "http://192.168.1.14:7622"


api = 'api/'
register_parent_views(api, app)

# test block
from backend.student.register_for_tes.resources import *

# filters
from backend.functions.filters import *

# account folder
from backend.account.payment import *
from backend.account.account import *
from backend.account.overhead_capital import *
from backend.account.salary import *
from backend.account.test_acc import *

# functions folder
from backend.functions.checks import *
from backend.functions.small_info import *

# QR code
from backend.QR_code.qr_code import *

# routes
from backend.routes.views import *

# student
from backend.student.views import *

# programmers
from backend.for_programmers.for_programmers import *

# teacher
from backend.teacher.views import *

# group
from backend.group.create_group import *
from backend.group.view import *
from backend.group.change import *
from backend.group.test import *

# time_table
from backend.time_table.view import *
from backend.time_table.room import *

# home
from backend.home_page.route import *
# certificate
from backend.certificate.views import *
# get api
from backend.routes.get_api import *

# classroom
from backend.class_room.views import *

# bot
from backend.telegram_bot.route import *

# book
from backend.book.main import *

# lead
from backend.lead.views import *

# mobile
from backend.mobile.views import *

# tasks
from backend.tasks.admin.views import *

# investment
from backend.account.profile.investment import *

# buxgalter
from backend.account.profile.views import *

# from backend.account.debit_credit.views import *

from backend.account.debit_credit.views import *

from backend.school.views import *
from backend.telegram_bot.route import *


# from backend.models.views import *

# teacher observation, attendance, teacher_group_statistics


# @app.route('/flask_static/<path:filename>')
# def flask_admin_static(filename):
#     return send_from_directory('static', filename)

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
    print("GIT PULL:", pull_result.stdout)
    return "Updated", 200


if __name__ == '__main__':
    app.run()
