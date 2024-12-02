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
from backend.tasks.utils import update_all_ratings
from backend.tasks.models.models import Tasks, TasksStatistics, TaskDailyStatistics


