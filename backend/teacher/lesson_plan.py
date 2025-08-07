from datetime import datetime

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

from app import db
from backend.functions.utils import find_calendar_date
from backend.functions.utils import get_json_field
from backend.models.models import LessonPlan, LessonPlanStudents, extract

lesson_plan_gennis_bp = Blueprint('lesson_plan_gennis', __name__)


@lesson_plan_gennis_bp.route(f'/change_lesson_plan/<int:plan_id>', methods=['POST'])
@jwt_required()
def change_lesson_plan(plan_id):
    lesson_plan_get = LessonPlan.query.filter(LessonPlan.id == plan_id).first()

    objective = get_json_field('objective')
    main_lesson = get_json_field('main_lesson')
    homework = get_json_field('homework')
    assessment = get_json_field('assessment')
    activities = get_json_field('activities')
    student_id_list = get_json_field("students")
    resources = get_json_field("resources")
    lesson_plan_get.objective = objective
    lesson_plan_get.homework = homework
    lesson_plan_get.assessment = assessment
    lesson_plan_get.main_lesson = main_lesson
    lesson_plan_get.activities = activities
    lesson_plan_get.resources = resources

    db.session.commit()
    for student in student_id_list:
        info = {
            "comment": student['comment'],
            "student_id": student['student']['id'],
            "lesson_plan_id": plan_id
        }
        student_add = LessonPlanStudents.query.filter(LessonPlanStudents.lesson_plan_id == plan_id,
                                                      LessonPlanStudents.student_id == student['student']['id']).first()
        if not student_add:
            student_add = LessonPlanStudents(**info)
            student_add.add()
        else:
            student_add.comment = student['comment']
            db.session.commit()
    return jsonify({
        "success": True,
        "msg": "Darslik rejasi tuzildi",
        "lesson_plan": lesson_plan_get.convert_json()
    })


@lesson_plan_gennis_bp.route(f'/lesson_plan_list/<int:group_id>', defaults={"date": None})
@lesson_plan_gennis_bp.route(f'/lesson_plan_list/<int:group_id>/<date>')
@jwt_required()
def lesson_plan_list(group_id, date):
    days_list = []
    month_list = []
    years_list = []
    plan_list = LessonPlan.query.filter(LessonPlan.group_id == group_id).order_by(LessonPlan.id).all()
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    if date:
        date = datetime.strptime(date, "%Y-%m")
    else:
        date = calendar_month.date

    plan_list_month = LessonPlan.query.filter(
        extract('month', LessonPlan.date) == int(date.strftime("%m")),
        extract('year', LessonPlan.date) == int(date.strftime("%Y")), LessonPlan.group_id == group_id).all()
    for data in plan_list_month:
        days_list.append(data.date.strftime("%d"))
    days_list.sort()
    for plan in plan_list:
        if plan.date:
            month_list.append(plan.date.strftime("%m"))
            years_list.append(plan.date.strftime("%Y"))
    month_list = list(dict.fromkeys(month_list))
    years_list = list(dict.fromkeys(years_list))
    month_list.sort()
    years_list.sort()
    return jsonify({
        "month_list": month_list,
        "years_list": years_list,
        "month": date.strftime("%m"),
        "year": date.strftime("%Y"),
        "days": days_list
    })


@lesson_plan_gennis_bp.route(f'/get_lesson_plan', methods=['POST'])
@jwt_required()
def get_lesson_plan():
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    day = get_json_field('day')
    month = get_json_field('month')
    year = get_json_field('year')
    group_id = get_json_field('group_id')
    date = year + "-" + month + "-" + day
    date = datetime.strptime(date, "%Y-%m-%d")
    status = True if calendar_day.date < date else False
    lesson_plan = LessonPlan.query.filter(LessonPlan.group_id == group_id, LessonPlan.date == date).first()
    return jsonify({
        "lesson_plan": lesson_plan.convert_json(),
        "status": status
    })
