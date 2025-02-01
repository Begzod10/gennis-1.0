from app import app, request, jsonify
from backend.functions.utils import api
from backend.models.models import Users, Students, Teachers


@app.route(f'{api}/send_user_data/<user_id>')
def send_user_data(user_id):
    user = Users.query.filter(Users.id == user_id).first()
    print(True)
    if user.student:
        get_user = Students.query.filter(Students.user_id == user_id).first()
    else:
        get_user = Teachers.query.filter(Teachers.user_id == user_id).first()

    return jsonify({"status": "true", "user": get_user.convert_groups()})
