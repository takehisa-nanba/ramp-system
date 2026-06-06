"""
GET /api/users/<user_id>/attendance-records
利用者の実績（来退所打刻）一覧を返す。
"""
from flask import jsonify
from flask_jwt_extended import jwt_required
from backend.app import db
from backend.app.models import User, DailyLog
from backend.app.models.support.attendance_workflow import AttendanceRecord
from sqlalchemy import func
from . import users_bp

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
        
        # 同日の日報を探す
        log = DailyLog.query.filter_by(user_id=user_id, log_date=att_date).first()
        if log:
            if log.log_status == 'COMPLETED':
                info["daily_log_status"] = "completed"
            elif log.log_status == 'DRAFT':
                info["daily_log_status"] = "draft"
        
        # 来所記録がない（CHECK_OUT単体など）場合のフォールバック
        if not info["attendance_record_id"]:
            info["attendance_record_id"] = 0
            
        items.append(info)
        
    # 日付の降順（新しい順）でソート
    items.sort(key=lambda x: x["date"], reverse=True)

    return jsonify({"items": items}), 200
