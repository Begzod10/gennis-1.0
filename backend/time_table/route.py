from backend.models.models import Week, Group_Room_Week, Rooms, Groups, db
from backend.functions.utils import update_week

from flask_jwt_extended import jwt_required
from flask import Blueprint, jsonify
from sqlalchemy.orm import joinedload

time_table = Blueprint('time_table', __name__)


@time_table.route(f'/view_table2/<int:location_id>/<day>', methods=['GET'])
@jwt_required()
def view_table(location_id, day):
    update_week(location_id)

    week_day = Week.query.filter(Week.location_id == location_id, Week.eng_name == day).order_by(
        Week.id).first()
    if not week_day:
        return jsonify({"success": False, "error": "Day not found"}), 404

    week_days = Week.query.filter(Week.location_id == location_id).order_by(Week.order).all()

    time_table_data = db.session.query(Group_Room_Week).options(
        joinedload(Group_Room_Week.teacher).joinedload('user'),
        joinedload(Group_Room_Week.group)
    ).filter(
        Group_Room_Week.location_id == location_id,
        Group_Room_Week.week_id == week_day.id
    ).order_by(Group_Room_Week.id).all()

    rooms = Rooms.query.filter(Rooms.location_id == location_id).order_by(Rooms.id).all()

    # Merge same-room same-time entries (teacher's two groups sharing one room)
    merged = {}
    for time in time_table_data:
        group = time.group
        key = (time.room_id, time.start_time.strftime("%H:%M"), time.end_time.strftime("%H:%M"))

        teacher_entries = [
            {
                "name": teach.user.name,
                "surname": teach.user.surname,
                "color": teach.table_color,
                "group_id": time.group_id,
                "group_name": group.name if group else None
            }
            for teach in time.teacher
        ]

        if key in merged:
            merged[key]["teacher"].extend(teacher_entries)
        else:
            merged[key] = {
                "id": time.id,
                "teacher": teacher_entries,
                "from": time.start_time.strftime("%H:%M"),
                "to": time.end_time.strftime("%H:%M"),
                "room": time.room_id,
                "week": time.week_id
            }

    time_table_list = list(merged.values())

    rooms_list = [{"id": room.id, "name": room.name} for room in rooms]
    week_days_list = [
        {"id": wd.id, "name": wd.name, "value": wd.eng_name}
        for wd in week_days
    ]

    return jsonify({
        "time_table": time_table_list,
        "rooms": rooms_list,
        "week_days": week_days_list,
        "success": True
    })
