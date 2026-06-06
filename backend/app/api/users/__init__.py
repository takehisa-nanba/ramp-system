from flask import Blueprint

users_bp = Blueprint('users', __name__, url_prefix='/api/users')

from . import core, pii, certificates, drafts, \
    user_plans_api, user_daily_logs_api, user_monitoring_api, user_case_conferences_api, user_attendance_api
