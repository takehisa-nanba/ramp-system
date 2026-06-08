"""
GET /api/users/<user_id>/daily-logs
利用者の日報一覧を返す（新しい順）。
"""
from flask import jsonify, request
from flask_jwt_extended import jwt_required
from backend.app import db
from backend.app.models import User, UserDailyLog, SupportRecord, Supporter
from . import users_bp


@users_bp.route('/<int:user_id>/daily-logs', methods=['GET'])
@jwt_required()
def get_user_daily_logs(user_id: int):
    """
    利用者の日報履歴を取得する。
    クエリパラメータ: limit (default: 20), offset (default: 0)
    """
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({
            "success": False,
            "error": {
                "code": "NOT_FOUND",
                "message": "利用者が見つかりません。"
            }
        }), 404

    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)

    logs_query = UserDailyLog.query.filter_by(user_id=user_id)\
        .order_by(UserDailyLog.log_date.desc())\
        .limit(limit).offset(offset).all()

    items = []
    for log in logs_query:
        # その日の支援記録（SupportRecord）を取得
        records = SupportRecord.query.filter_by(user_id=user_id, log_date=log.log_date)\
            .order_by(SupportRecord.support_start_time.asc()).all()
        activities = []
        for act in records:
            supporter = db.session.get(Supporter, act.supporter_id)
            supporter_name = supporter.display_name if supporter and hasattr(supporter, 'display_name') else f"ID:{act.supporter_id}"
            activities.append({
                "id": act.id,
                "support_content": act.support_content,
                "start_time": act.support_start_time.strftime('%H:%M') if act.support_start_time else None,
                "end_time": act.support_end_time.strftime('%H:%M') if act.support_end_time else None,
                "duration_seconds": act.support_duration_seconds,
                "supporter_name": supporter_name,
            })

        items.append({
            "id": log.id,
            "log_date": log.log_date.isoformat(),
            "log_status": log.log_status,
            "support_content_notes": log.support_content_notes,
            "location_type": log.location_type,
            "activities": activities,
        })

    return jsonify({"items": items}), 200
