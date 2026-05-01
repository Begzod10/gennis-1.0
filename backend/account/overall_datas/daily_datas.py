from flask import Blueprint
from flask import request, jsonify
from flask_jwt_extended import jwt_required
from backend.models.models import CalendarDay, BranchReport, CalendarYear, CalendarMonth
from backend.functions.utils import iterate_models
from datetime import datetime

daily_datas = Blueprint('daily_datas', __name__)


@daily_datas.route('list/', methods=['GET'])
def get_one_day_data():
    location_id = request.args.get('location_id')
    month = request.args.get('month')
    year = request.args.get('year')
    month_date = year + '-' + month
    year_obj = datetime.strptime(year, '%Y')
    month_date_obj = datetime.strptime(month_date, '%Y-%m')

    year_id = CalendarYear.query.filter(CalendarYear.date == year_obj).first().id
    month_id = CalendarMonth.query.filter(
        CalendarMonth.date == month_date_obj,
        CalendarMonth.year_id == year_id
    ).first().id
    branch_report = BranchReport.query.filter(BranchReport.location_id == location_id, BranchReport.year_id == year_id,
                                              BranchReport.month_id == month_id).all()
    return jsonify({
        "reports_list": iterate_models(branch_report)
    })
