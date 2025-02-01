import pprint

from app import app, api, contains_eager, db, request
from flask import jsonify
from flask_jwt_extended import jwt_required
from backend.functions.utils import find_calendar_date, get_json_field
from backend.models.models import AttendanceHistoryStudent, Students, Groups, Roles, Week, Group_Room_Week, Rooms
from datetime import datetime
from backend.functions.filters import update_lesson_plan, old_current_dates
from backend.group.class_model import Group_Functions


@app.route(f'{api}/group_profile_classroom/<group_id>')
def group_profile_classroom(group_id):
    students = db.session.query(Students).join(Students.group).options(contains_eager(Students.group)).filter(
        Groups.id == group_id).order_by(Students.id).all()
    user_id_list = [st.user_id for st in students]
    return jsonify({'user_id_list': user_id_list})
