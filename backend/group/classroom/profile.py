import pprint

from app import app, api, contains_eager, db, request
from flask import jsonify
from flask_jwt_extended import jwt_required
from backend.functions.utils import find_calendar_date, get_json_field
from backend.models.models import AttendanceHistoryStudent, Students, Groups, Roles, Week, Group_Room_Week, Rooms, \
    GroupTest, LessonPlan, desc
from datetime import datetime
from backend.functions.filters import update_lesson_plan, old_current_dates
from backend.group.class_model import Group_Functions
from backend.functions.functions import update_user_time_table, get_dates_for_weekdays


@app.route(f'{api}/group_profile_classroom/<group_id>')
def group_profile_classroom(group_id):
    group = Groups.query.filter(Groups.id == group_id).first()
    students = db.session.query(Students).join(Students.group).options(contains_eager(Students.group)).filter(
        Groups.id == group_id).order_by(Students.id).all()
    user_id_list = [st.user_id for st in students]
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    group_time_table = Group_Room_Week.query.filter(Group_Room_Week.group_id == group_id).order_by(
        Group_Room_Week.id).all()
    test_status = GroupTest.query.filter(GroupTest.group_id == group_id, GroupTest.calendar_year == calendar_year.id,
                                         GroupTest.calendar_month == calendar_month.id,
                                         GroupTest.student_tests == None).first()
    last_test = GroupTest.query.filter(GroupTest.group_id == group_id, GroupTest.calendar_month == calendar_month.id,
                                       GroupTest.calendar_year == calendar_year.id,
                                       GroupTest.student_tests != None).order_by(desc(GroupTest.id)).first()
    errors = []

    if test_status:
        errors.append(
            f"Guruhda {test_status.day.date.strftime('%d')} kuni {test_status.level} leveli bo'yicha test olinishi kerak.")
    elif last_test and not test_status:
        errors.append(
            f"Guruhda oxirgi marta {last_test.day.date.strftime('%d')} kuni {last_test.level} leveli bo'yicha test olingan.")
    else:
        errors.append(f"Guruh uchun {calendar_month.date.strftime('%B')} oyi uchun test kuni belgilanmagan.")
    week_names = [time.week.eng_name for time in group_time_table]

    target_dates = [d.date() for d in get_dates_for_weekdays(week_names)]

    lesson_plans = LessonPlan.query.filter(
        LessonPlan.group_id == group.id,
        LessonPlan.date.in_(target_dates),
        LessonPlan.main_lesson == None,
        LessonPlan.homework == None
    ).all()
    filled_lesson_plan = LessonPlan.query.filter(
        LessonPlan.group_id == group.id,
        LessonPlan.date.in_(target_dates),
        LessonPlan.main_lesson != None,
        LessonPlan.homework != None).first()

    for lesson_plan in lesson_plans:
        errors.append(f"{lesson_plan.date.strftime('%m-%d')} shu kunda lesson plan qilinmagan.")
    return jsonify({'user_id_list': user_id_list, "errors": errors})
