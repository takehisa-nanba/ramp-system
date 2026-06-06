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

    # 今日の通所者数（本日のCHECK_IN実績が存在するユニーク利用者数）
    from backend.app.models.support.attendance_workflow import AttendanceRecord
    from sqlalchemy import func
    
    today_users = db.session.query(AttendanceRecord.user_id)\
        .filter(
            AttendanceRecord.record_type == 'CHECK_IN',
            func.date(AttendanceRecord.timestamp) == today
        ).distinct().count()

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

@dashboard_bp.route('/today-users', methods=['GET'])
@jwt_required()
def get_today_users():
    """
    本日来所している利用者の一覧と打刻時間、日報ステータスを返す。
    """
    from backend.app.models.support.attendance_workflow import AttendanceRecord
    from sqlalchemy import func
    
    today = date.today()
    
    # 本日のCHECK_IN実績を取得
    check_ins = AttendanceRecord.query.filter(
        AttendanceRecord.record_type == 'CHECK_IN',
        func.date(AttendanceRecord.timestamp) == today
    ).order_by(AttendanceRecord.timestamp.asc()).all()
    
    items = []
    for att in check_ins:
        user_id = att.user_id
        user_name = att.user.display_name if att.user else "不明"
        
        # 同日の退所打刻 (CHECK_OUT) が存在するか探す
        check_out = AttendanceRecord.query.filter_by(
            user_id=user_id, 
            record_type='CHECK_OUT'
        ).filter(
            func.date(AttendanceRecord.timestamp) == today
        ).first()
        
        # 同日の日報を探す
        log = DailyLog.query.filter_by(user_id=user_id, log_date=today).first()
        
        daily_log_status = "missing"
        if log:
            if log.log_status == 'COMPLETED':
                daily_log_status = "completed"
            elif log.log_status == 'DRAFT':
                daily_log_status = "draft"
                
        status = "CHECKED_OUT" if check_out else "CHECKED_IN"
        
        items.append({
            "user_id": user_id,
            "user_name": user_name,
            "attendance_record_id": att.id,
            "check_in_at": att.timestamp.isoformat(),
            "check_out_at": check_out.timestamp.isoformat() if check_out else None,
            "status": status,
            "daily_log_status": daily_log_status
        })
        
    return jsonify({"items": items}), 200

