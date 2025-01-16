from app import app, api, contains_eager, db, request
from flask import jsonify
from flask_jwt_extended import jwt_required
from backend.functions.utils import find_calendar_date, get_json_field
from backend.models.models import AttendanceHistoryStudent, Students, Groups, Roles, Week, Group_Room_Week, Rooms
from datetime import datetime
from backend.functions.filters import update_lesson_plan, old_current_dates
from backend.group.class_model import Group_Functions


@app.route(f'{api}/group_dates2_classroom/<int:group_id>')
def group_dates2_classroom(group_id):
    print(group_id)
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    year_list = []
    month_list = []
    attendance_month = AttendanceHistoryStudent.query.filter(
        AttendanceHistoryStudent.group_id == group_id,
    ).order_by(AttendanceHistoryStudent.id).all()
    for attendance in attendance_month:
        year = AttendanceHistoryStudent.query.filter(AttendanceHistoryStudent.group_id == group_id,
                                                     AttendanceHistoryStudent.calendar_year == attendance.calendar_year).all()
        info = {
            'year': '',
            'months': []
        }
        if info['year'] != attendance.year.date.strftime("%Y"):
            info['year'] = attendance.year.date.strftime("%Y")
        for month in year:
            if attendance.year.date.strftime("%Y") not in year_list:
                year_list.append(attendance.year.date.strftime("%Y"))
            if month.month.date.strftime("%m") not in info['months']:
                info['months'].append(month.month.date.strftime("%m"))
                info['months'].sort()
        #
        # if info['year'] != calendar_year.date.strftime("%Y"):
        #     info['year'] = calendar_year.date.strftime("%Y")
        # if calendar_month.date.strftime("%m") not in info['months']:
        #     print(calendar_year.date.strftime("%Y"))
        #     info['months'].append(calendar_month.date.strftime("%m"))
        month_list.append(info)
    year_list = list(dict.fromkeys(year_list))
    if calendar_year.date.strftime("%Y") not in year_list:
        year_list.append(calendar_year.date.strftime("%Y"))
    filtered_list = []
    for student in month_list:
        added_to_existing = False
        for merged in filtered_list:
            if merged['year'] == student['year']:
                added_to_existing = True
            if added_to_existing:
                break
        if not added_to_existing:
            filtered_list.append(student)
    return jsonify({
        "data": {
            "months": filtered_list,
            "years": year_list,
            "current_year": calendar_year.date.strftime("%Y"),
            "current_month": calendar_month.date.strftime("%m"),
        }
    })


@app.route(f'{api}/attendances_classroom/<int:group_id>', methods=['GET', "POST"])
def attendances_classroom(group_id):
    update_lesson_plan(group_id)
    students = db.session.query(Students).join(Students.group).options(contains_eager(Students.group)).filter(
        Groups.id == group_id).order_by(Students.id).all()
    student_list = [{
        "id": st.user.id,
        "img": None,
        "name": st.user.name.title(),
        "surname": st.user.surname.title(),
        "money": st.user.balance,
        "moneyType": ["green", "yellow", "red", "navy", "black"][st.debtor] if st.debtor else 0,
        "comment": st.user.comment,
        "reg_date": st.user.day.date.strftime("%Y-%m-%d"),
        "phone": st.user.phone[0].phone,
        "username": st.user.username,
        "age": st.user.age,
        "photo_profile": st.user.photo_profile,
        "role": Roles.query.filter(Roles.id == st.user.role_id).first().role
    } for st in students]

    gr_functions = Group_Functions(group_id=group_id)
    if request.method == "GET":
        current_month = datetime.now().month
        if len(str(current_month)) == 1:
            current_month = "0" + str(current_month)
        current_year = datetime.now().year

        return jsonify({

            "data": {
                "attendance_filter": gr_functions.attendance_filter(month=current_month, year=current_year),
                "students": student_list,
                "date": old_current_dates(group_id),
            }
        })
    else:
        year = get_json_field('year')

        month = get_json_field('month')
        print(year)
        print(month)
        return jsonify({

            "data": {
                "attendance_filter": gr_functions.attendance_filter(month=month, year=year),
                "students": student_list,
                "date": old_current_dates(group_id),
            }
        })


@app.route(f'{api}/group_time_table_classroom/<int:group_id>')
def group_time_table_classroom(group_id):
    group = Groups.query.filter(Groups.id == group_id).first()
    week_days = Week.query.filter(Week.location_id == group.location_id).order_by(Week.order).all()
    table_list = []
    weeks = []
    for week in week_days:
        weeks.append(week.name)
    rooms = db.session.query(Rooms).join(Rooms.time_table).options(contains_eager(Rooms.time_table)).filter(
        Group_Room_Week.group_id == group_id, Rooms.location_id == group.location_id).all()
    for room in rooms:
        room_info = {
            "room": room.name,
            "id": room.id,
            "lesson": []
        }
        week_list = []
        for week in week_days:
            info = {
                "from": "",
                "to": ""
            }
            time_table = Group_Room_Week.query.filter(Group_Room_Week.group_id == group_id,
                                                      Group_Room_Week.week_id == week.id,
                                                      Group_Room_Week.room_id == room.id).order_by(
                Group_Room_Week.group_id).first()
            if time_table:
                info["from"] = time_table.start_time.strftime("%H:%M")
                info["to"] = time_table.end_time.strftime("%H:%M")

            week_list.append(info)
            room_info['lesson'] = week_list
        table_list.append(room_info)
    return jsonify({
        "success": True,
        "data": table_list,
        "days": weeks
    })
