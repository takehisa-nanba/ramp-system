from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.app import db
from backend.app.services.case_conference_service import CaseConferenceService
from backend.app.services.core_service import parse_jwt_identity
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
case_conferences_bp = Blueprint('case_conferences', __name__, url_prefix='/api/case-conferences')
case_conference_service = CaseConferenceService()

@case_conferences_bp.route('', methods=['POST'])
@jwt_required()
def create_case_conference():
    _, supporter_id = parse_jwt_identity(get_jwt_identity())
    data = request.get_json()
    
    user_id = data.get('user_id')
    conference_type = data.get('conference_type', 'AD_HOC')
    concern_summary = data.get('concern_summary')
    agreed_action = data.get('agreed_action')
    participant_ids = data.get('participant_ids', [])
    
    if not user_id or not concern_summary or not agreed_action:
        return jsonify({"msg": "Missing required fields (user_id, concern_summary, agreed_action)"}), 400
        
    try:
        conf_datetime_str = data.get('conference_datetime')
        conf_datetime = datetime.fromisoformat(conf_datetime_str) if conf_datetime_str else None
        
        conference = case_conference_service.record_case_conference(
            initiator_id=supporter_id,
            user_id=user_id,
            conference_type=conference_type,
            concern_summary=concern_summary,
            agreed_action=agreed_action,
            participant_ids=participant_ids,
            conference_datetime=conf_datetime,
            triggering_log_reference=data.get('triggering_log_reference'),
            plan_direction_update=data.get('plan_direction_update'),
            external_collaboration_required=data.get('external_collaboration_required', False),
            issue_category_id=data.get('issue_category_id')
        )
        db.session.commit()
        return jsonify({"msg": "Case conference recorded", "id": conference.id}), 201
    except Exception as e:
        db.session.rollback()
        logger.exception(e)
        return jsonify({"msg": "Failed to record case conference"}), 500
