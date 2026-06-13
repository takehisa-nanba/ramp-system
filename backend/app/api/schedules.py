from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from backend.app import db
from backend.app.models import User, UserDailySchedule, UserDailyLog
from backend.app.models.support.attendance_workflow import AttendanceRecord
from sqlalchemy import func
from datetime import datetime
from backend.app.utils.timezone import get_jst_today

schedules_bp = Blueprint('schedules', __name__, url_prefix='/api/schedules')

@schedules_bp.route('/daily-actuals', methods=['GET'])
@jwt_required()
def get_daily_actuals():
    target_date_str = request.args.get('date')
    try:
        if target_date_str:
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
        else:
            target_date = get_jst_today()
    except ValueError:
        return jsonify({
            "success": False,
            "error": {"code": "VALIDATION_ERROR", "message": "Invalid date format."}
        }), 400

    # アクティブな全利用者
    users = User.query.filter(User.deleted_at.is_(None)).all()
    user_ids = [u.id for u in users]

    if not user_ids:
        return jsonify({"items": []}), 200

    # 予定を取得
    schedules = UserDailySchedule.query.filter(
        UserDailySchedule.user_id.in_(user_ids),
        UserDailySchedule.date == target_date
    ).all()
    sched_map = {s.user_id: s for s in schedules}

    # 実績（打刻）を取得
    attendances = AttendanceRecord.query.filter(
        AttendanceRecord.user_id.in_(user_ids),
        func.date(AttendanceRecord.timestamp) == target_date
    ).all()
    
    att_map = {}
    for att in attendances:
        if att.user_id not in att_map:
            att_map[att.user_id] = {"check_in": None, "check_out": None}
        if att.record_type == 'CHECK_IN':
            if not att_map[att.user_id]["check_in"] or att.timestamp < att_map[att.user_id]["check_in"]:
                att_map[att.user_id]["check_in"] = att.timestamp
        elif att.record_type == 'CHECK_OUT':
            if not att_map[att.user_id]["check_out"] or att.timestamp > att_map[att.user_id]["check_out"]:
                att_map[att.user_id]["check_out"] = att.timestamp

    # 支援記録（日報）を取得
    logs = UserDailyLog.query.filter(
        UserDailyLog.user_id.in_(user_ids),
        UserDailyLog.log_date == target_date
    ).all()
    log_map = {log.user_id: log for log in logs}

    items = []
    for u in users:
        sched = sched_map.get(u.id)
        att = att_map.get(u.id)
        log = log_map.get(u.id)

        check_in = att["check_in"] if att else None
        check_out = att["check_out"] if att else None
        
        is_scheduled = sched.is_scheduled if sched else False
        schedule_status = sched.schedule_status if sched else None
        
        # effective_status の判定
        effective_status = "NONE"
        if check_in:
            if log and log.log_status == 'COMPLETED':
                effective_status = "ARRIVED_AS_SCHEDULED" if is_scheduled else "UNSCHEDULED_ARRIVAL"
            else:
                # 来所しているが支援記録が未完了
                effective_status = "MISSING_SUPPORT_RECORD"
        else:
            if sched and (sched.approval_status == 'CANCELLED' or (not sched.is_scheduled and sched.decision_reason)):
                effective_status = "CANCELLED"
            elif is_scheduled:
                effective_status = "SCHEDULED_NOT_ARRIVED"
            else:
                effective_status = "NONE"

        items.append({
            "user_id": u.id,
            "user_name": u.display_name,
            "is_scheduled": is_scheduled,
            "scheduled_start_time": sched.start_time if sched else None,
            "scheduled_end_time": sched.end_time if sched else None,
            "schedule_status": schedule_status,
            "check_in_at": check_in.isoformat() if check_in else None,
            "check_out_at": check_out.isoformat() if check_out else None,
            "effective_status": effective_status,
            "daily_log_status": log.log_status if log else "missing",
            "decision_reason": sched.decision_reason if sched else None
        })

    # effective_status でソート（例えば MISSING_SUPPORT_RECORD を上に）
    def status_priority(status):
        priorities = {
            "MISSING_SUPPORT_RECORD": 1,
            "SCHEDULED_NOT_ARRIVED": 2,
            "UNSCHEDULED_ARRIVAL": 3,
            "ARRIVED_AS_SCHEDULED": 4,
            "CANCELLED": 5,
            "NONE": 6
        }
        return priorities.get(status, 99)

    items.sort(key=lambda x: (status_priority(x["effective_status"]), x["user_id"]))

    return jsonify({"items": items}), 200
