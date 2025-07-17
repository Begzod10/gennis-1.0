from app import app, request, jsonify
from backend.functions.utils import api
from backend.models.models import Users, Students, Teachers
from backend.parent.models import Parent


@app.route(f'{api}/send_user_data/<user_id>')
def send_user_data(user_id):
    user = Users.query.filter(Users.id == user_id).first()

    if user.student:
        get_user = Students.query.filter(Students.user_id == user_id).first()
    else:
        get_user = Teachers.query.filter(Teachers.user_id == user_id).first()
    return jsonify({"status": "true", "user": get_user.convert_groups()})


@app.route(f'{api}/send_parent_data/<user_id>')
def send_parent_data(user_id):
    user = Users.query.filter(Users.id == user_id).first()

    if user.parent:
        get_user = Parent.query.filter(Parent.user_id == user_id).first()
    return jsonify({"status": "true", "user": get_user.convert_json()})


@app.route(f'{api}/send_student_data/<user_id>')
def send_student_data(user_id):
    user = Users.query.filter(Users.id == user_id).first()

    return jsonify({"status": "true", "user": user.convert_json()})
