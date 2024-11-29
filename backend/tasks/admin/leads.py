from datetime import datetime

from flask_jwt_extended import jwt_required, get_jwt_identity

from app import app, request, jsonify
from backend.functions.utils import api, find_calendar_date, get_json_field, desc, CalendarMonth, AccountingPeriod, \
    iterate_models
from backend.lead.functions import update_posted_tasks, get_lead_tasks, get_completed_lead_tasks
from backend.lead.models import Lead, LeadInfos
from backend.models.models import Subjects
from backend.models.models import Users
from backend.models.models import db
from backend.student.calling_to_students import update_all_ratings
from backend.tasks.models.models import Tasks, TasksStatistics, TaskDailyStatistics


def get_current_period():
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    accounting_period = AccountingPeriod.query.join(CalendarMonth).order_by(desc(CalendarMonth.id)).first().id
    return calendar_day, accounting_period


def get_or_create_lead(name, phone, location_id, subject_id=None):
    existing_lead = Lead.query.filter(Lead.phone == phone, Lead.deleted == False).first()
    if not existing_lead:
        calendar_day, accounting_period = get_current_period()
        lead_data = {
            "name": name,
            "phone": phone,
            "calendar_day": calendar_day.id,
            "account_period_id": accounting_period,
            "location_id": location_id,
        }
        existing_lead = Lead(**lead_data)
        existing_lead.add()
    if subject_id:
        subject = Subjects.query.filter(Subjects.id == subject_id).first()
        if existing_lead not in subject.leads:
            subject.leads.append(existing_lead)
            db.session.commit()
    return existing_lead


@app.route(f'{api}/register_lead', methods=['POST'])
def register_lead():
    calendar_day, accounting_period = get_current_period()

    name = get_json_field('name')
    phone = get_json_field('phone')
    location_id = get_json_field('location_id')
    subject_id = get_json_field('subject_id') if 'subject_id' in request.get_json() else None

    lead = get_or_create_lead(name, phone, location_id, subject_id)

    return jsonify({
        "msg": "Siz muvaffaqiyatli ro'yxatdan o'tdingiz",
        "success": True
    })


@app.route(f'{api}/get_leads_location/<status>/<location_id>')
@jwt_required()
def get_leads_location(status, location_id):
    update_posted_tasks()

    filter_condition = Lead.deleted == False if status == "news" else Lead.deleted == True
    leads = Lead.query.filter(Lead.location_id == location_id, filter_condition).order_by(desc(Lead.id)).all()

    leads_info = []
    completed_tasks = []

    for lead in leads:
        if tasks := get_lead_tasks(lead):
            leads_info.append(tasks)
        if completed_tasks := get_completed_lead_tasks(lead):
            completed_tasks.append(completed_tasks)

    return jsonify({
        "leads": leads_info,
        'completed_tasks': completed_tasks
    })


@app.route(f'{api}/lead_crud/<int:pm>', methods=['POST', "GET", "DELETE", "PUT"])
@jwt_required()
def crud_lead(pm):
    user = Users.query.filter(Users.user_id == get_jwt_identity()).first()
    calendar_day, _ = get_current_period()

    lead = Lead.query.filter(Lead.id == pm).first()
    if not lead:
        return jsonify({"msg": "Lead not found", "success": False}), 404

    if request.method == "DELETE":
        return delete_lead(lead, calendar_day, user)

    if request.method == "POST":
        return post_lead_comment(lead, calendar_day)

    if request.method == "GET":
        return get_lead_comments(lead)


def delete_lead(lead, calendar_day, user):
    comment = get_json_field('comment')
    location_id = get_json_field('location_id')
    lead.deleted = True
    lead.comment = comment
    db.session.commit()

    update_task_statistics_on_deletion(lead, calendar_day, user, location_id)

    adjust_daily_statistics(calendar_day, location_id)

    return jsonify({"msg": "O'quvchi o'chirildi", "success": True})


def update_task_statistics_on_deletion(lead, calendar_day, user, location_id):
    task_type = Tasks.query.filter_by(name='leads').first()
    task_statistics = TasksStatistics.query.filter_by(
        task_id=task_type.id,
        calendar_day=calendar_day.id,
        location_id=user.location_id
    ).first()

    if task_statistics:
        task_statistics.total_tasks -= 1
        db.session.commit()
        task_statistics.in_progress_tasks = task_statistics.total_tasks - task_statistics.completed_tasks
        db.session.commit()

        completed_percentage = round(
            (task_statistics.completed_tasks / task_statistics.total_tasks) * 100) if task_statistics.total_tasks else 0
        TasksStatistics.query.filter_by(id=task_statistics.id).update({
            'completed_tasks_percentage': completed_percentage
        })
        db.session.commit()


def adjust_daily_statistics(calendar_day, location_id):
    daily_statistics = TaskDailyStatistics.query.filter(TaskDailyStatistics.calendar_day == calendar_day.id,
                                                        TaskDailyStatistics.location_id == location_id).first()
    if daily_statistics:
        daily_statistics.total_tasks -= 1
        db.session.commit()
        update_all_ratings()


def post_lead_comment(lead, calendar_day):
    comment = get_json_field('comment')
    date_str = get_json_field('date')
    date = datetime.strptime(date_str, '%Y-%m-%d')
    location_id = get_json_field('location_id')

    if date > calendar_day.date:
        if not LeadInfos.query.filter(LeadInfos.lead_id == lead.id,
                                      LeadInfos.added_date == calendar_day.date).first():
            info = LeadInfos(
                lead_id=lead.id,
                day=date,
                comment=comment,
                added_date=calendar_day.date
            )
            info.add()

        return jsonify({
            "msg": "Komment belgilandi",
            "success": True,
            "lead": lead.convert_json(),
            "lead_info": update_posted_tasks(),
            "info": update_all_ratings()
        })
    else:
        return jsonify({'msg': "Eski sana kiritilgan"})


def get_lead_comments(lead):
    get_comments = LeadInfos.query.filter(LeadInfos.lead_id == lead.id).order_by(desc(LeadInfos.id)).all()
    return jsonify({
        "comments": iterate_models(get_comments)
    })
