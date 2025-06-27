import datetime
from datetime import datetime

from flask import Blueprint
from flask_jwt_extended import jwt_required

from app import db, jsonify, request, desc
from backend.functions.utils import find_calendar_date
from backend.models.models import Locations as Location
from backend.models.models import TaskRatingsMonthly, TaskRatings, CalendarMonth,TaskDailyStatistics
from backend.models.models import Users, Students, CalendarDay, TaskStudents, StudentCallingInfo, LeadInfos, Lead
from backend.tasks.utils import filter_new_leads
from backend.tasks.utils import filter_new_students

task_rating_bp = Blueprint('task_rating_bp', __name__)
from backend.tasks.utils import update_debt_progress


@task_rating_bp.route('/task_rating_statistics', methods=['POST'])
def task_rating_statistics():
    data = request.get_json()
    year_id = data.get('year_id')
    month_id = data.get('month_id')
    task_type_id = data.get('task_type_id')

    task_types = TaskRatings.query.filter(
        TaskRatings.task_id == task_type_id,
        TaskRatings.calendar_year == year_id
    ).join(TaskRatings.month).order_by(desc(CalendarMonth.date)).all()

    month_id_list = [task.calendar_month for task in task_types]
    task_rating_list = []

    if task_type_id:
        task_rating = TaskRatingsMonthly.query.filter(
            TaskRatingsMonthly.calendar_year == month_id,
            TaskRatingsMonthly.task_id == task_type_id
        ).first()
    else:
        task_rating = TaskRatingsMonthly.query.filter(
            TaskRatingsMonthly.calendar_year == month_id
        ).first()

    if task_rating:
        task_rating_list.append(task_rating.convert_json())

    return jsonify({"data": task_rating_list})

@task_rating_bp.route('/task_rating', methods=['GET'])
@jwt_required()
def task_rating():
    import re
    from datetime import timedelta

    date_str = request.args.get("date", None)
    today = datetime.today()

    if not date_str:
        period = "month"
        year, month = today.year, today.month
        date = datetime(year, month, 1)
    elif re.fullmatch(r"\d{4}-\d{2}$", date_str):
        period = "month"
        year, month = map(int, date_str.split("-"))
        date = datetime(year, month, 1)
    else:
        period = "day"
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "Date format must be YYYY-MM-DD or YYYY-MM"}), 400

    calendar_year, calendar_month, calendar_day = find_calendar_date()
    locations = Location.query.all()
    results = []

    for location in locations:
        location_id = location.id

        if period == "month":
            # Topish
            monthly_stats = TaskRatingsMonthly.query.filter_by(
                calendar_year=calendar_year.id,
                calendar_month=calendar_month.id,
                location_id=location_id
            ).first()

            # Hisoblash
            new_students_total = 0
            completed_new_students_total = 0
            leads_total = 0
            completed_leads_total = 0
            debt_students_total = 0

            current_day = date
            while current_day.month == date.month:
                calendar = CalendarDay.query.filter(CalendarDay.date == current_day.date()).first()

                if current_day.date() == calendar_day.date:
                    new_students, _, _ = filter_new_students(location_id)
                    _, _, completed_ns = filter_new_students(location_id)
                    leads, _, completed_leads = filter_new_leads(location_id)
                    debt_students, _ = update_debt_progress(location_id)
                else:
                    new_students = db.session.query(Students).join(Students.student_calling_info).join(Users).filter(
                        Users.location_id == location_id,
                        StudentCallingInfo.day == current_day.date()
                    ).distinct().all() if calendar else []

                    completed_ns = new_students

                    leads = db.session.query(Lead).join(Lead.infos).filter(
                        Lead.deleted == False,
                        Lead.location_id == location_id,
                        LeadInfos.added_date == current_day.date()
                    ).all() if calendar else []

                    completed_leads = leads

                    debt_students = db.session.query(Students).join(Students.user).join(Students.students_tasks).filter(
                        Users.location_id == location_id,
                        TaskStudents.status == False,
                        TaskStudents.calendar_day == calendar.id
                    ).all() if calendar else []

                new_students_total += len(new_students)
                completed_new_students_total += len(completed_ns)
                leads_total += len(leads)
                completed_leads_total += len(completed_leads)
                debt_students_total += len(debt_students)

                current_day += timedelta(days=1)

            results.append({
                "location_id": location_id,
                "location_name": location.name,
                "new_students": new_students_total,
                "completed_new_students": completed_new_students_total,
                "leads": leads_total,
                "completed_leads": completed_leads_total,
                "not_completed_leads": max(leads_total - completed_leads_total, 0),
                "debt_students": debt_students_total,
                "task_statistics": monthly_stats.convert_json() if monthly_stats else None
            })

        else:
            # DAY
            if date.date() == calendar_day.date:
                new_students, _, _ = filter_new_students(location_id)
                _, _, completed_ns = filter_new_students(location_id)
                leads, _, completed_leads = filter_new_leads(location_id)
                debt_students, _ = update_debt_progress(location_id)
            else:
                calendar = CalendarDay.query.filter(CalendarDay.date == date.date()).first()

                new_students = db.session.query(Students).join(Students.student_calling_info).join(Users).filter(
                    Users.location_id == location_id,
                    StudentCallingInfo.day == date.date()
                ).distinct().all() if calendar else []

                completed_ns = new_students

                leads = db.session.query(Lead).join(Lead.infos).filter(
                    Lead.deleted == False,
                    Lead.location_id == location_id,
                    LeadInfos.added_date == date.date()
                ).all() if calendar else []

                completed_leads = leads

                debt_students = db.session.query(Students).join(Students.user).join(Students.students_tasks).filter(
                    Users.location_id == location_id,
                    TaskStudents.status == False,
                    TaskStudents.calendar_day == calendar.id
                ).all() if calendar else []

            daily_stats = TaskDailyStatistics.query.filter_by(
                location_id=location_id,
                calendar_day=calendar_day.id
            ).first()

            results.append({
                "location_id": location_id,
                "location_name": location.name,
                "new_students": len(new_students),
                "completed_new_students": len(completed_ns),
                "leads": len(leads),
                "completed_leads": len(completed_leads),
                "not_completed_leads": max(len(leads) - len(completed_leads), 0),
                "debt_students": len(debt_students),
                "task_statistics": daily_stats.convert_json() if daily_stats else None
            })

    return jsonify({
        "period": period,
        "date": date.strftime("%Y-%m" if period == "month" else "%Y-%m-%d"),
        "data": results
    }), 200
