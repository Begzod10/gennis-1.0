from datetime import datetime

from flask import jsonify, request
from flask_jwt_extended import jwt_required

from backend.functions.utils import find_calendar_date, get_json_field, iterate_models
from backend.lead.models import Lead, LeadInfos, LeadInfosRecord
from backend.models.models import db, TasksStatistics, TaskDailyStatistics, Tasks
from backend.tasks.utils import filter_new_leads, update_all_ratings
from backend.vats.vats_process import VatsProcess, wait_until_call_finished
from backend.celery.lead_calls import process_call_and_save_record
from flask import Blueprint
from pprint import pprint
import aiohttp
from datetime import timedelta
import os

task_leads_bp = Blueprint('task_leads', __name__)


@task_leads_bp.route(f"/call-to-lead", methods=["POST"])
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


@task_leads_bp.route(f"/call-status/<task_id>", methods=["GET"])
def check_call_status(task_id):
    task = process_call_and_save_record.AsyncResult(task_id)

    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'status': 'Task is waiting...'
        }
    elif task.state == 'SUCCESS':
        response = {
            'state': task.state,
            'result': task.result
        }
    elif task.state == 'FAILURE':
        response = {
            'state': task.state,
            'error': str(task.info)
        }
    else:
        response = {
            'state': task.state,
            'status': str(task.info)
        }

    return jsonify(response)


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
    lead_infos = LeadInfos.query.filter(LeadInfos.id == pk).first()
    comment = get_json_field('comment')
    date = get_json_field('date')
    date = datetime.strptime(date, '%Y-%m-%d')

    if date > calendar_day.date:
        lead_infos.comment = comment
        lead_infos.day = date
        db.session.commit()
        leads, task_statistics, _ = filter_new_leads(lead_infos.lead.location_id)
        daily_statistics = update_all_ratings(lead_infos.lead.location_id)
        return jsonify({
            "msg": "Komment belgilandi",
            "success": True,
            "lead_id": lead_infos.lead.id,
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
