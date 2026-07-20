"""
GET /api/dashboard/summary
Dashboard用の集計データを1回のAPIで返す。
"""
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from backend.app import db
from backend.app.models import UserDailyLog, SupportPlan, CaseConferenceLog, User
from datetime import date, datetime
from backend.app.utils.timezone import get_jst_today
from backend.app.utils.tenant import extract_staff_id, resolve_tenant_scope, get_accessible_users_subquery
from backend.app.domain.attendance.exceptions import handle_attendance_errors

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')

@dashboard_bp.route('/summary', methods=['GET'])
@jwt_required()
@handle_attendance_errors
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
    identity = get_jwt_identity()
    staff_id = extract_staff_id(identity)
    claims = get_jwt()
    scope = resolve_tenant_scope(staff_id, claims.get('role_scopes', []))

    today = get_jst_today()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())

    users_sq = get_accessible_users_subquery(scope, today, staff_id)
    if users_sq is not None:
        # Check if the subquery yields any results (fail closed)
        has_access = db.session.query(users_sq.c.user_id).first() is not None
        if not has_access:
            return jsonify({
                "today_users": 0,
                "pending_daily_logs": 0,
                "pending_approvals": 0,
                "monitoring_due_count": 0,
                "action_items": 0,
                "today_case_conferences": 0,
            }), 200

    # 今日の通所者数（本日のCHECK_IN実績が存在するユニーク利用者数）
    from backend.app.models.support.attendance_workflow import AttendanceRecord
    from sqlalchemy import func, select

    q_today = db.session.query(AttendanceRecord.user_id).filter(
        AttendanceRecord.record_type == 'CHECK_IN',
        func.date(AttendanceRecord.timestamp) == today
    )
    if users_sq is not None:
        q_today = q_today.filter(AttendanceRecord.user_id.in_(select(users_sq.c.user_id)))
    today_users = q_today.distinct().count()

    # 未完了日報数（DRAFT状態）
    q_logs = UserDailyLog.query.filter(UserDailyLog.log_status == 'DRAFT')
    if users_sq is not None:
        q_logs = q_logs.filter(UserDailyLog.user_id.in_(select(users_sq.c.user_id)))
    pending_daily_logs = q_logs.count()

    # 承認待ち計画数
    q_plans = SupportPlan.query.filter(SupportPlan.plan_status == 'PENDING_CONSENT')
    if users_sq is not None:
        q_plans = q_plans.filter(SupportPlan.user_id.in_(select(users_sq.c.user_id)))
    pending_approvals = q_plans.count()

    # 未実施モニタリング数
    q_mon = SupportPlan.query.filter(SupportPlan.plan_status == 'ACTIVE').filter(SupportPlan.plan_end_date <= today)
    if users_sq is not None:
        q_mon = q_mon.filter(SupportPlan.user_id.in_(select(users_sq.c.user_id)))
    monitoring_due_count = q_mon.count()

    # 本日のケース会議数
    q_conf = CaseConferenceLog.query.filter(
        CaseConferenceLog.conference_datetime >= today_start,
        CaseConferenceLog.conference_datetime <= today_end
    )
    if users_sq is not None:
        q_conf = q_conf.filter(CaseConferenceLog.user_id.in_(select(users_sq.c.user_id)))
    today_case_conferences = q_conf.count()

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
@handle_attendance_errors
def get_today_users():
    """
    本日来所している利用者の一覧と打刻時間、日報ステータスを返す。
    """
    identity = get_jwt_identity()
    staff_id = extract_staff_id(identity)
    claims = get_jwt()
    scope = resolve_tenant_scope(staff_id, claims.get('role_scopes', []))

    from backend.app.models.support.attendance_workflow import AttendanceRecord
    from sqlalchemy import func, select

    today = get_jst_today()
    users_sq = get_accessible_users_subquery(scope, today, staff_id)
    if users_sq is not None:
        has_access = db.session.query(users_sq.c.user_id).first() is not None
        if not has_access:
            return jsonify({"items": []}), 200

    # 本日のCHECK_IN実績を取得
    q_check_ins = AttendanceRecord.query.filter(
        AttendanceRecord.record_type == 'CHECK_IN',
        func.date(AttendanceRecord.timestamp) == today
    )
    if users_sq is not None:
        q_check_ins = q_check_ins.filter(
            AttendanceRecord.user_id.in_(select(users_sq.c.user_id))
        )

    check_ins = q_check_ins.order_by(AttendanceRecord.timestamp.asc()).all()

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
        log = UserDailyLog.query.filter_by(user_id=user_id, log_date=today).first()
        
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
