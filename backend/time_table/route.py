from backend.models.models import Week, Group_Room_Week, Rooms, Groups, db, Teachers, Users, time_table_teacher
from backend.functions.utils import update_week

from flask_jwt_extended import jwt_required
from flask import Blueprint, jsonify, request
from sqlalchemy.orm import joinedload
from sqlalchemy import and_

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
        joinedload(Group_Room_Week.teacher).joinedload(Teachers.user),
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


@time_table.route('/teacher_time_table/<int:teacher_id>/weekly-schedule', methods=['GET'])
def get_teacher_weekly_schedule(teacher_id):
    location_id = request.args.get('location_id', type=int)

    if not location_id:
        return jsonify({"error": "location_id is required"}), 400

    teacher = Teachers.query.get(teacher_id)
    if not teacher:
        return jsonify({"error": "Teacher not found"}), 404

    schedule_query = (
        db.session.query(Group_Room_Week)
        .join(
            time_table_teacher,
            time_table_teacher.c.group_room_week == Group_Room_Week.id
        )
        .join(
            Week,
            Week.id == Group_Room_Week.week_id
        )
        .join(
            Groups,
            Groups.id == Group_Room_Week.group_id
        )
        .join(
            Rooms,
            Rooms.id == Group_Room_Week.room_id
        )
        .filter(
            and_(
                time_table_teacher.c.teacher_id == teacher_id,
                Group_Room_Week.location_id == location_id
            )
        )
        .order_by(
            Week.order.asc(),
            Group_Room_Week.start_time.asc()
        )
        .all()
    )

    # Hafta kunlari bo'yicha guruhlash
    schedule_by_week = {}

    for grw in schedule_query:
        week = grw.week
        week_key = week.id

        if week_key not in schedule_by_week:
            schedule_by_week[week_key] = {
                "week_id": week.id,
                "week_name": week.name,
                "week_eng_name": week.eng_name,
                "week_order": week.order,
                "lessons": []
            }

        # Guruh ma'lumotlari
        group = grw.group
        room = grw.room

        lesson = {
            "schedule_id": grw.id,
            "group": {
                "id": group.id,
                "name": group.name,
            },
            "room": {
                "id": room.id,
                "name": room.name,
            },
            "start_time": grw.start_time.strftime("%H:%M") if grw.start_time else None,
            "end_time": grw.end_time.strftime("%H:%M") if grw.end_time else None,
            "location_id": grw.location_id
        }

        schedule_by_week[week_key]["lessons"].append(lesson)

    sorted_schedule = sorted(schedule_by_week.values(), key=lambda x: x["week_order"])

    return jsonify({
        "teacher_id": teacher_id,
        "location_id": location_id,
        "weekly_schedule": sorted_schedule
    }), 200
