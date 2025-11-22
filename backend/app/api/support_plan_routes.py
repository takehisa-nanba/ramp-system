from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.app.extensions import db
from backend.app.models import SupportPlan, Supporter, DocumentConsentLog
from backend.app.services.support_service import SupportService
from backend.app.services.core_service import check_permission
from datetime import datetime

support_plan_bp = Blueprint('support_plans', __name__)
service = SupportService()

@support_plan_bp.route('/', methods=['POST'])
@jwt_required()
def create_draft():
    """
    計画原案(DRAFT)の作成API。
    """
    current_supporter_id = int(get_jwt_identity())
    data = request.get_json()
    
    # 1. 権限チェック (サビ管のみ作成可能とする場合)
    # if not check_permission(current_supporter_id, 'create_plan'): ...
    
    try:
        new_plan = service.create_plan_draft(
            user_id=data.get('user_id'),
            sabikan_id=current_supporter_id,
            based_on_policy_id=data.get('policy_id')
        )
        db.session.commit()
        return jsonify({"msg": "Draft plan created", "id": new_plan.id, "status": new_plan.plan_status}), 201
        
    except Exception as e:
        return jsonify({"msg": str(e)}), 400

@support_plan_bp.route('/<int:plan_id>/conference', methods=['POST'])
@jwt_required()
def record_conference(plan_id):
    """
    支援会議の記録＆サビ管承認API (Lock 1)。
    """
    current_supporter_id = int(get_jwt_identity())
    data = request.get_json()
    
    try:
        conf_date = datetime.fromisoformat(data.get('conference_date'))
        
        log = service.log_support_conference_and_approve(
            plan_id=plan_id,
            sabikan_id=current_supporter_id,
            conference_date=conf_date,
            content=data.get('content'),
            user_participated=data.get('user_participated'),
            reason_for_absence=data.get('reason_for_absence')
        )
        db.session.commit()
        return jsonify({"msg": "Conference logged & Plan approved", "status": "PENDING_CONSENT"}), 200
        
    except Exception as e:
        return jsonify({"msg": str(e)}), 400

@support_plan_bp.route('/<int:plan_id>/finalize', methods=['POST'])
@jwt_required()
def finalize_plan(plan_id):
    """
    利用者同意に基づく成案化API (Lock 2)。
    """
    data = request.get_json()
    consent_log_id = data.get('consent_log_id')
    
    try:
        final_plan = service.finalize_and_activate_plan(
            plan_id=plan_id,
            consent_log_id=consent_log_id
        )
        db.session.commit()
        return jsonify({
            "msg": "Plan finalized and activated", 
            "id": final_plan.id, 
            "status": final_plan.plan_status
        }), 200
        
    except Exception as e:
        return jsonify({"msg": str(e)}), 400