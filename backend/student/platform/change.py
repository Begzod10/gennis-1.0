from app import api, app, db, request, jwt_required, jsonify, generate_password_hash, classroom_server
import os
from backend.models.models import Users, PhoneList, Students, Teachers, Roles, StudentExcuses, Subjects
from backend.functions.small_info import checkFile, user_photo_folder
from backend.functions.utils import find_calendar_date, send_user_info
from werkzeug.utils import secure_filename
from datetime import datetime
import requests
from werkzeug.security import generate_password_hash


@app.route(f'{api}/change_student_classroom/<user_id>',methods=['POST'])
def change_student_classroom(user_id):
    user = Users.query.filter(Users.id == user_id).first()
    username = request.get_json()['username']
    user.username = username
    db.session.commit()
    return jsonify({
        "success": True,
        "msg": "Ma'lumotlar o'zgartirildi",
        "username": username
    })


@app.route(f'{api}/change_student_password/<user_id>', methods=['POST'])
def change_student_password(user_id):
    user = Users.query.filter(Users.id == user_id).first()
    password = request.get_json()['password']
    user.password = generate_password_hash(password)
    db.session.commit()
    return jsonify({
        "success": True,
        "msg": "Ma'lumotlar o'zgartirildi"
    })
