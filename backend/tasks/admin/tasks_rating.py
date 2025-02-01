from app import app, db, jsonify, request, desc
from backend.models.models import TaskRatingsMonthly, TaskRatings, CalendarMonth
from backend.functions.utils import api, find_calendar_date, iterate_models


@app.route(f'{api}/task_rating_statistics', methods=['POST'])
def task_rating_statistics():
    year_id = request.get_json()['year_id']
    month_id = request.get_json()['month_id']
    task_type_id = request.get_json()['task_type_id']
    task_types = TaskRatings.query.filter(TaskRatings.task_id == task_type_id,
                                          TaskRatings.calendar_year == year_id).join(TaskRatings.month).order_by(
        desc(CalendarMonth.date)).all()
    month_id_list = [task.calendar_month for task in task_types]
    task_rating_list = []
    if task_type_id:

            task_rating = TaskRatingsMonthly.query.filter(TaskRatingsMonthly.calendar_year == month_id,
                                                   TaskRatings.task_id == task_type_id).first()
            task_rating_list.append(task_rating.convert_json())
    else:

        task_rating = TaskRatingsMonthly.query.filter(TaskRatingsMonthly.calendar_year == month_id,
                                                      ).first()
        task_rating_list.append(task_rating.convert_json())
    return jsonify({"data": task_rating_list})
