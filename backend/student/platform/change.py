from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash

from app import db
from backend.models.models import Users

chang_student_bp = Blueprint('change_student', __name__)


@chang_student_bp.route(f'/change_student_classroom/<user_id>', methods=['POST'])
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


@chang_student_bp.route(f'/change_student_password/<user_id>', methods=['POST'])
def change_student_password(user_id):
    user = Users.query.filter(Users.id == user_id).first()
    password = request.get_json()['password']
    user.password = generate_password_hash(password)
    db.session.commit()
    return jsonify({
        "success": True,
        "msg": "Ma'lumotlar o'zgartirildi"
    })
