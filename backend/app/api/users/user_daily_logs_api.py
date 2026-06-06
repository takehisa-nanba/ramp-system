"""
GET /api/users/<user_id>/daily-logs
利用者の日報一覧を返す（新しい順）。
"""
from flask import jsonify, request
from flask_jwt_extended import jwt_required
from backend.app import db
from backend.app.models import User, DailyLog, DailyLogActivity, Supporter
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

    logs_query = DailyLog.query.filter_by(user_id=user_id)\
        .order_by(DailyLog.log_date.desc())\
        .limit(limit).offset(offset).all()

    items = []
    for log in logs_query:
        # 活動明細（支援記録）を取得
        activities = []
        for act in log.activities:
            supporter = db.session.get(Supporter, act.supporter_id)
            supporter_name = supporter.display_name if supporter and hasattr(supporter, 'display_name') else f"ID:{act.supporter_id}"
            activities.append({
                "id": act.id,
                "support_content": act.support_content,
                "start_time": act.support_start_time.strftime('%H:%M') if act.support_start_time else None,
                "end_time": act.support_end_time.strftime('%H:%M') if act.support_end_time else None,
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
