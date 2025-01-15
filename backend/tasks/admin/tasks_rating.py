from app import app, db, jsonify, request, desc
from backend.models.models import TaskRatingsMonthly, TaskRatings, CalendarMonth
from backend.functions.utils import api, find_calendar_date, iterate_models


@app.route(f'{api}/task_rating_statistics/', defaults={'task_type_id': None})
@app.route(f'{api}/task_rating_statistics/<year_id>/<task_type_id>')
def task_rating_statistics(task_type_id, year_id):
    task_types = TaskRatings.query.filter(TaskRatings.task_id == task_type_id,
                                          TaskRatings.calendar_year == year_id).join(TaskRatings.month).order_by(
        desc(CalendarMonth.date)).all()
    task_types2 = TaskRatings.query.filter(TaskRatings.task_id == task_type_id,
                                           TaskRatings.calendar_year == year_id).order_by(
        desc(TaskRatings.calendar_month)).all()
    print(task_types2, "months")
    month_id_list = [task.calendar_month for task in task_types]
    task_rating_list = []
    if task_type_id:
        for month_id in month_id_list:
            task_rating = TaskRatings.query.filter(TaskRatings.calendar_month == month_id,
                                                   TaskRatings.task_id == task_type_id).first()
            task_rating_list.append(task_rating.convert_json())
    else:
        for month_id in month_id_list:
            task_rating = TaskRatingsMonthly.query.filter(TaskRatingsMonthly.calendar_year == month_id,
                                                          ).first()
            task_rating_list.append(task_rating.convert_json())

    return jsonify({"data": task_rating_list})
