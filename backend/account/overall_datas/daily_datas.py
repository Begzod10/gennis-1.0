from flask import Blueprint
from flask import request, jsonify
from flask_jwt_extended import jwt_required
from backend.models.models import CalendarDay, BranchReport
from backend.functions.utils import iterate_models

daily_datas = Blueprint('daily_datas', __name__)


@daily_datas.route('list/', methods=['GET'])
def get_one_day_data():
    branch_report = BranchReport.query.all()
    return jsonify({
        "reports_list": iterate_models(branch_report)
    })
