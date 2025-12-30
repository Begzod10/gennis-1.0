from datetime import datetime
from sqlalchemy import desc
from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from backend.functions.utils import find_calendar_date, get_json_field, iterate_models
from backend.lead.models import Lead, LeadInfos, LeadInfosRecord
from backend.models.models import db, TasksStatistics, TaskDailyStatistics, Tasks
from backend.tasks.utils import filter_new_leads, update_all_ratings
from backend.vats.vats_process import VatsProcess, wait_until_call_finished
from backend.celery.lead_calls import process_call_and_save_record
from flask import Blueprint
from sqlalchemy import func
from backend.models.models import Users

task_leads_bp = Blueprint('task_leads', __name__)


@task_leads_bp.route(f"/call-to-lead", methods=["POST"])
@jwt_required()
async def test_call():
    data = request.get_json()
    lead_id = data.get("lead_id")

    if not lead_id:
        return jsonify({"error": "Missing 'lead_id'"}), 400
    identity = get_jwt_identity()
    user = Users.query.filter(Users.user_id == identity).first()
    if not user.crm_username:
        return jsonify({"error": "Missing 'crm_username'"}), 400
    else:
        if user.crm_username not in ['gennis_center', 'gennis_chirchiq', 'gennis_chorvoq', 'gennis_gazalkent',
                                     'gennis_nurafshon']:
            return jsonify({"error": "CRM username is invalid"}), 400
    # Queue the task

    task = process_call_and_save_record.delay(lead_id, user.crm_username)
    print(user.crm_username)
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
    date_obj = datetime.strptime(date, "%Y-%m-%d").date()
    current_date = calendar_day.date.date() if hasattr(calendar_day.date, 'date') else calendar_day.date

    is_current = date_obj == current_date
    is_future = date_obj > current_date

    # Current day logic
    if is_current:
        _, task_statistics, leads = filter_new_leads(location_id)
        daily_statistics = update_all_ratings(location_id)

        # Lead infos added today - use func.date for comparison
        lead_infos = db.session.query(LeadInfos).join(LeadInfos.lead).filter(
            func.date(LeadInfos.added_date) == date_obj,
            Lead.location_id == location_id
        ).all()
        return jsonify({
            "leads": iterate_models(leads),
            "task_statistics": task_statistics.convert_json() if task_statistics else None,
            "task_daily_statistics": daily_statistics.convert_json() if daily_statistics else None,
            "lead_infos": iterate_models(lead_infos),
            "table": False
        }), 200

    # Future or Past date logic
    leads = db.session.query(Lead).join(Lead.infos).filter(
        Lead.deleted == False,
        Lead.location_id == location_id,
        func.date(LeadInfos.day) == date_obj
    ).all()

    lead_infos = db.session.query(LeadInfos).join(LeadInfos.lead).filter(
        func.date(LeadInfos.day) == date_obj,
        Lead.location_id == location_id
    ).all()

    # Statistics only for past dates
    if is_future:
        task_statistics = None
        daily_statistics = None
    else:
        task_type = Tasks.query.filter(Tasks.name == 'leads').first()

        task_statistics = TasksStatistics.query.filter(
            TasksStatistics.task_id == task_type.id,
            TasksStatistics.calendar_day == calendar_day.id,
            TasksStatistics.location_id == location_id
        ).first()

        daily_statistics = TaskDailyStatistics.query.filter(
            TaskDailyStatistics.location_id == location_id,
            TaskDailyStatistics.calendar_day == calendar_day.id
        ).first()
    return jsonify({
        # "leads": iterate_models(leads),
        "task_statistics": task_statistics.convert_json() if task_statistics else None,
        "task_daily_statistics": daily_statistics.convert_json() if daily_statistics else None,
        "lead_infos": iterate_models(lead_infos),
        "table": True
    }), 200


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


@task_leads_bp.route(f'/lead_records/<int:lead_id>/', methods=["GET", "POST"])
def lead_records(lead_id):
    lead = Lead.query.filter(Lead.id == lead_id).first()
    return jsonify({
        "comments": iterate_models(
            LeadInfos.query.filter(LeadInfos.lead_id == lead.id).order_by(
                desc(LeadInfos.id)).all(), entire=True),
        "info": Lead.query.filter(Lead.id == lead_id).first().convert_json()
    })
