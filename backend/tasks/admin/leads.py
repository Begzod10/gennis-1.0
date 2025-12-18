from datetime import datetime

from flask import jsonify, request
from flask_jwt_extended import jwt_required

from backend.functions.utils import find_calendar_date, get_json_field, iterate_models
from backend.lead.models import Lead, LeadInfos, LeadInfosRecord
from backend.models.models import db, TasksStatistics, TaskDailyStatistics, Tasks
from backend.tasks.utils import filter_new_leads, update_all_ratings
from backend.vats.vats_process import VatsProcess, wait_until_call_finished
from backend.celery.admin_calls import process_call_and_save_record
from flask import Blueprint
from pprint import pprint
import aiohttp
from datetime import timedelta
import os

task_leads_bp = Blueprint('task_leads', __name__)


@task_leads_bp.route(f"/test-call", methods=["POST"])
async def test_call():
    data = request.get_json()
    lead_id = data.get("lead_id")

    if not lead_id:
        return jsonify({"error": "Missing 'lead_id'"}), 400

    # Queue the task
    task = process_call_and_save_record.delay(lead_id)

    return jsonify({
        "message": "Call processing started",
        "task_id": task.id,
        "status": "processing"
    }), 202


# @task_leads_bp.route('/check-history', methods=["GET"])
# async def check_history():  # ✅ Make it async
#     vats = VatsProcess()
#
#     users_online = await vats.get_online_users()
#     users = await vats.list_all_users()
#     calls = await vats.get_today_calls()
#     calls = await vats.get_and_log_today_calls_for_user("turon_center")
#
#     print("[INFO] Waiting for call to finish...")
#
#     print("[CALL ENDED]", final_info)
#
#     return jsonify({"users": users, "users_online": users_online, "calls": calls}), 200


@task_leads_bp.route(f'/task_leads/<int:location_id>/<date>', methods=["POST", "GET"])
@jwt_required()
def task_leads(location_id, date):
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    date = datetime.strptime(date, "%Y-%m-%d")
    if date == calendar_day.date:
        leads, task_statistics, completed = filter_new_leads(location_id)
        daily_statistics = update_all_ratings(location_id)
    else:
        leads = []
        task_statistics = None
        daily_statistics = None

    return jsonify(
        {"leads": iterate_models(leads), "task_statistics": task_statistics.convert_json() if task_statistics else None,
         "task_daily_statistics": daily_statistics.convert_json() if daily_statistics else None}), 200


@task_leads_bp.route(f'/completed_leads/<int:location_id>/<date>', methods=["POST", "GET"])
@jwt_required()
def completed_leads(location_id, date):
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    date = datetime.strptime(date, "%Y-%m-%d")
    task_type = Tasks.query.filter(Tasks.name == 'leads').first()
    table = True
    if date == calendar_day.date:
        _, task_statistics, leads = filter_new_leads(location_id)
        daily_statistics = update_all_ratings(location_id)

        table = False
    elif date > calendar_day.date:
        leads = db.session.query(Lead).join(Lead.infos).filter(Lead.deleted == False, Lead.location_id == location_id,
                                                               LeadInfos.day == date).all()
        task_statistics = None
        daily_statistics = None
    else:
        leads = db.session.query(Lead).join(Lead.infos).filter(Lead.deleted == False, Lead.location_id == location_id,
                                                               LeadInfos.added_date == date).all()
        task_statistics = TasksStatistics.query.filter(TasksStatistics.task_id == task_type.id,
                                                       TasksStatistics.calendar_day == calendar_day.id,
                                                       TasksStatistics.location_id == location_id).first()
        daily_statistics = TaskDailyStatistics.query.filter(
            TaskDailyStatistics.location_id == location_id,
            TaskDailyStatistics.calendar_day == calendar_day.id).first()
    return jsonify(
        {"leads": iterate_models(leads), "task_statistics": task_statistics.convert_json() if task_statistics else None,
         "task_daily_statistics": daily_statistics.convert_json() if daily_statistics else None,
         "table": table}), 200


@task_leads_bp.route(f'/task_leads_update/<int:pk>', methods=["POST", "GET"])
@jwt_required()
def task_leads_update(pk):
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    lead = Lead.query.filter(Lead.id == pk).first()
    comment = get_json_field('comment')
    date = get_json_field('date')
    date = datetime.strptime(date, '%Y-%m-%d')
    info = {
        "lead_id": lead.id,
        "day": date,
        "comment": comment,
        'added_date': calendar_day.date
    }
    if date > calendar_day.date:
        exist_lead = LeadInfos.query.filter(LeadInfos.lead_id == lead.id,
                                            LeadInfos.added_date == calendar_day.date).first()
        if not exist_lead:
            info = LeadInfos(**info)
            info.add()
        leads, task_statistics, _ = filter_new_leads(lead.location_id)
        daily_statistics = update_all_ratings(lead.location_id)
        return jsonify({
            "msg": "Komment belgilandi",
            "success": True,
            "lead_id": lead.id,
            "task_statistics": task_statistics.convert_json(),
            "task_daily_statistics": daily_statistics.convert_json()

        })
    else:
        return jsonify({
            'msg': "Eski sana kiritilgan",

        })


@task_leads_bp.route(f'/task_leads_delete/<int:pk>', methods=["DELETE"])
@jwt_required()
def task_leads_delete(pk):
    lead = Lead.query.filter(Lead.id == pk).first()
    lead.deleted = True
    db.session.commit()
    leads, task_statistics, _ = filter_new_leads(lead.location_id)
    daily_statistics = update_all_ratings(lead.location_id)

    return jsonify({
        "leads": [lead.convert_json() for lead in leads],
        "task_statistics": task_statistics.convert_json(),
        "task_daily_statistics": daily_statistics.convert_json(),
        "msg": "O'quvchi o'chirildi", "success": True,
    }), 200
