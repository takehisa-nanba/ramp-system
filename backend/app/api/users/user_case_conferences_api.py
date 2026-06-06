"""
GET /api/users/<user_id>/case-conferences
利用者のケース会議記録一覧を返す。
"""
from flask import jsonify
from flask_jwt_extended import jwt_required
from backend.app import db
from backend.app.models import User, CaseConferenceLog, Supporter
from . import users_bp


@users_bp.route('/<int:user_id>/case-conferences', methods=['GET'])
@jwt_required()
def get_user_case_conferences(user_id: int):
    """
    利用者のケース会議記録を取得する（新しい順）。
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

    conferences = CaseConferenceLog.query\
        .filter_by(user_id=user_id)\
        .order_by(CaseConferenceLog.conference_datetime.desc())\
        .all()

    items = []
    for conf in conferences:
        initiator = db.session.get(Supporter, conf.initiator_supporter_id)
        initiator_name = initiator.display_name if initiator and hasattr(initiator, 'display_name') else f"ID:{conf.initiator_supporter_id}"

        # 参加者のリスト (participants は lazy='dynamic' なので .all() で取得)
        participants = []
        for p in conf.participants.all():
            supporter = db.session.get(Supporter, p.supporter_id)
            if supporter and hasattr(supporter, 'display_name'):
                participants.append(supporter.display_name)

        items.append({
            "id": conf.id,
            "conference_datetime": conf.conference_datetime.isoformat() if conf.conference_datetime else None,
            "conference_type": conf.conference_type,
            "concern_summary": conf.concern_summary,
            "agreed_action": conf.agreed_action,
            "plan_direction_update": conf.plan_direction_update,
            "external_collaboration_required": conf.external_collaboration_required,
            "initiator_name": initiator_name,
            "participants": participants,
        })

    return jsonify({"items": items}), 200
