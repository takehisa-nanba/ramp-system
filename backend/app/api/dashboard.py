"""
GET /api/dashboard/summary
Dashboard用の集計データを1回のAPIで返す。
"""
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from backend.app import db
from backend.app.models import DailyLog, SupportPlan, CaseConferenceLog
from datetime import date, datetime

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')


@dashboard_bp.route('/summary', methods=['GET'])
@jwt_required()
def get_dashboard_summary():
    """
    Dashboard表示に必要な集計値を返す。
    - today_users: 本日の日報が存在する利用者数（実通所者数の近似値）
    - pending_daily_logs: 下書き（未完了）の日報数
    - pending_approvals: 承認待ちの計画数（PENDING_CONSENT状態）
    - monitoring_due_count: モニタリング期限が近い/過ぎているACTIVE計画数
      ※ TODO: replace plan_end_date fallback with formal monitoring schedule field
    - action_items: pending_daily_logs + pending_approvals + monitoring_due_count の合計
    - today_case_conferences: 本日開催のケース会議数
    """
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())

    # 今日の通所者数（本日の日報が存在するユニーク利用者数）
    today_users = db.session.query(DailyLog.user_id)\
        .filter(DailyLog.log_date == today)\
        .distinct().count()

    # 未完了日報数（DRAFT状態）
    pending_daily_logs = DailyLog.query\
        .filter(DailyLog.log_status == 'DRAFT')\
        .count()

    # 承認待ち計画数
    pending_approvals = SupportPlan.query\
        .filter(SupportPlan.plan_status == 'PENDING_CONSENT')\
        .count()

    # 未実施モニタリング数
    # ACTIVE計画のうち plan_end_date が今日以前のもの（期限切れまたは本日が期限）を対象とする。
    # TODO: replace plan_end_date fallback with formal monitoring schedule field
    # 正式な monitoring_schedule が実装されたら next_monitoring_due < today で判定する。
    monitoring_due_count = SupportPlan.query\
        .filter(SupportPlan.plan_status == 'ACTIVE')\
        .filter(SupportPlan.plan_end_date <= today)\
        .count()

    # 本日のケース会議数
    today_case_conferences = CaseConferenceLog.query\
        .filter(CaseConferenceLog.conference_datetime >= today_start)\
        .filter(CaseConferenceLog.conference_datetime <= today_end)\
        .count()

    # action_items は全未処理事項の合計
    action_items = pending_daily_logs + pending_approvals + monitoring_due_count

    return jsonify({
        "today_users": today_users,
        "pending_daily_logs": pending_daily_logs,
        "pending_approvals": pending_approvals,
        "monitoring_due_count": monitoring_due_count,
        "action_items": action_items,
        "today_case_conferences": today_case_conferences,
    }), 200
