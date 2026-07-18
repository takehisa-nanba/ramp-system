"""
GET /api/users/<user_id>/attendance-records
利用者の実績（来退所打刻）一覧を返す。
"""
from flask import jsonify
from flask_jwt_extended import jwt_required
from backend.app import db
from backend.app.models import User, UserDailyLog
from backend.app.models.support.attendance_workflow import AttendanceRecord
from sqlalchemy import func
from backend.app.services.user_schedule_service import get_legacy_schedule_status
from . import users_bp

from flask import request
from datetime import datetime
from backend.app.utils.timezone import JST

@users_bp.route('/<int:user_id>/attendance-records', methods=['POST'])
@jwt_required()
def create_user_attendance_record(user_id: int):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"success": False, "error": {"code": "NOT_FOUND", "message": "利用者が見つかりません。"}}), 404

    data = request.get_json() or {}
    record_type = data.get('type') # 'CHECK_IN' or 'CHECK_OUT'
    
    if record_type not in ['CHECK_IN', 'CHECK_OUT']:
        return jsonify({"success": False, "error": {"code": "VALIDATION_ERROR", "message": "Invalid record type"}}), 400
        
    timestamp_str = data.get('timestamp')
    if timestamp_str:
        try:
            record_timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except ValueError:
            return jsonify({"success": False, "error": {"code": "VALIDATION_ERROR", "message": "Invalid timestamp format"}}), 400
    else:
        record_timestamp = datetime.now(JST)

    new_record = AttendanceRecord(
        user_id=user_id,
        record_type=record_type,
        timestamp=record_timestamp,
        location_data=data.get('location')
    )
    db.session.add(new_record)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "item": {
            "id": new_record.id,
            "type": new_record.record_type,
            "timestamp": new_record.timestamp.isoformat()
        }
    }), 201

@users_bp.route('/<int:user_id>/attendance-records', methods=['GET'])
@jwt_required()
def get_user_attendance_records(user_id: int):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({
            "success": False,
            "error": {
                "code": "NOT_FOUND",
                "message": "利用者が見つかりません。"
            }
        }), 404

    # 利用実績を取得（最新の打刻日時順）
    attendances = AttendanceRecord.query.filter_by(user_id=user_id).order_by(AttendanceRecord.timestamp.desc()).all()

    # 日付ごとにグルーピングして、来所・退所・日報ステータスを突き合わせる
    grouped = {}
    
    for att in attendances:
        if not att.timestamp:
            continue
        att_date = att.timestamp.date()
        date_str = att_date.strftime('%Y-%m-%d')
        
        if date_str not in grouped:
            grouped[date_str] = {
                "attendance_record_id": None,
                "date": date_str,
                "check_in_at": None,
                "check_out_at": None,
                "status": "IDLE",
                "daily_log_status": "missing"
            }
            
        if att.record_type == 'CHECK_IN':
            grouped[date_str]["attendance_record_id"] = att.id
            grouped[date_str]["check_in_at"] = att.timestamp.isoformat()
            if grouped[date_str]["status"] == "IDLE":
                grouped[date_str]["status"] = "CHECKED_IN"
        elif att.record_type == 'CHECK_OUT':
            grouped[date_str]["check_out_at"] = att.timestamp.isoformat()
            grouped[date_str]["status"] = "CHECKED_OUT"

    # 各日付の DailyLog の状態をロードして突き合わせる
    items = []
    for date_str, info in grouped.items():
        from datetime import datetime
        att_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # 予定を取得
        from backend.app.models import UserDailySchedule
        sched = UserDailySchedule.query.filter_by(user_id=user_id, date=att_date).first()
        if sched:
            info["scheduled_location_type"] = sched.location_type
            info["scheduled_start_time"] = sched.start_time
            info["scheduled_end_time"] = sched.end_time
            info["is_scheduled"] = sched.is_scheduled
            info["schedule_status"] = get_legacy_schedule_status(sched)
            info["approval_status"] = sched.approval_status
        else:
            info["scheduled_location_type"] = None
            info["scheduled_start_time"] = None
            info["scheduled_end_time"] = None
            info["is_scheduled"] = False
            info["schedule_status"] = None
            info["approval_status"] = None

        # 同日の日報を探す
        log = UserDailyLog.query.filter_by(user_id=user_id, log_date=att_date).first()
        if log:
            info["actual_location_type"] = log.location_type
            if log.log_status == 'COMPLETED':
                info["daily_log_status"] = "completed"
            elif log.log_status == 'DRAFT':
                info["daily_log_status"] = "draft"
        else:
            info["actual_location_type"] = None
        
        # 来所記録がない（CHECK_OUT単体など）場合のフォールバック
        if not info["attendance_record_id"]:
            info["attendance_record_id"] = 0
            
        items.append(info)
        
    # 日付の降順（新しい順）でソート
    items.sort(key=lambda x: x["date"], reverse=True)

    return jsonify({"items": items}), 200

@users_bp.route('/<int:user_id>/attendance-actuals/<date_str>', methods=['PUT'])
@jwt_required()
def update_user_attendance_actuals(user_id: int, date_str: str):
    from flask_jwt_extended import get_jwt_identity
    identity = get_jwt_identity()
    if not identity.startswith('staff:'):
        return jsonify({"success": False, "error": {"code": "FORBIDDEN", "message": "この操作には職員権限が必要です。"}}), 403

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"success": False, "error": {"code": "NOT_FOUND", "message": "利用者が見つかりません。"}}), 404

    from datetime import datetime
    from backend.app.utils.timezone import JST
    from backend.app.models.support.attendance_workflow import AttendanceRecord
    from sqlalchemy import func

    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({"success": False, "error": {"code": "VALIDATION_ERROR", "message": "日付のフォーマットが不正です。"}}), 400

    data = request.get_json() or {}
    check_in_time = data.get('actual_check_in') # "HH:MM" or None
    check_out_time = data.get('actual_check_out') # "HH:MM" or None

    attendances = AttendanceRecord.query.filter_by(user_id=user_id).filter(func.date(AttendanceRecord.timestamp) == target_date).all()
    in_record = next((r for r in attendances if r.record_type == 'CHECK_IN'), None)
    out_record = next((r for r in attendances if r.record_type == 'CHECK_OUT'), None)

    def make_timestamp(time_str):
        if not time_str: return None
        return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M").replace(tzinfo=JST)

    if check_in_time:
        new_ts = make_timestamp(check_in_time)
        if in_record:
            in_record.timestamp = new_ts
        else:
            in_record = AttendanceRecord(user_id=user_id, record_type='CHECK_IN', timestamp=new_ts)
            db.session.add(in_record)
    else:
        if in_record: db.session.delete(in_record)

    if check_out_time:
        new_ts = make_timestamp(check_out_time)
        if out_record:
            out_record.timestamp = new_ts
        else:
            out_record = AttendanceRecord(user_id=user_id, record_type='CHECK_OUT', timestamp=new_ts)
            db.session.add(out_record)
    else:
        if out_record: db.session.delete(out_record)

    db.session.commit()
    return jsonify({"success": True, "msg": "実績を更新しました"}), 200
