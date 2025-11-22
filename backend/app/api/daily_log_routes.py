from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.app.extensions import db
from backend.app.models import DailyLog, Supporter
from backend.app.services.support_service import SupportService
from backend.app.services.core_service import check_permission
from datetime import datetime, timezone

daily_log_bp = Blueprint('daily_logs', __name__)
support_service = SupportService()

@daily_log_bp.route('/', methods=['POST'])
@jwt_required()
def create_daily_log():
    """
    日報の作成API。
    Plan-Activity ガードレールによる検証を行う（原理9）。
    """
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    user_id = data.get('user_id')
    goal_id = data.get('goal_id')
    
    # 1. ガードレール: 計画に基づかない支援は記録させない
    if not support_service.validate_daily_log_against_plan(user_id, goal_id):
        return jsonify({"msg": "Invalid goal or plan. Activity must link to an ACTIVE plan."}), 400

    # 2. データの作成
    try:
        log_date = datetime.strptime(data.get('log_date'), '%Y-%m-%d').date()
        
        new_log = DailyLog(
            user_id=user_id,
            goal_id=goal_id,
            log_date=log_date,
            supporter_id=current_user_id, # 作成者＝ログイン職員
            
            # 支援内容（事実）
            support_content_notes=data.get('support_content_notes'),
            
            # 意味のポケット（任意）
            heartwarming_episode=data.get('heartwarming_episode'),
            
            # 評価フラグ（相互覚知）
            staff_effectiveness_flag=data.get('staff_effectiveness_flag'),
            user_effectiveness_flag=data.get('user_effectiveness_flag'),
            
            # 利用者日報部分（あれば）
            daily_goal_commitment=data.get('daily_goal_commitment'),
            user_self_evaluation=data.get('user_self_evaluation'),
            
            log_status='DRAFT'
        )
        
        db.session.add(new_log)
        db.session.commit()
        
        return jsonify({"msg": "DailyLog created", "id": new_log.id}), 201
        
    except Exception as e:
        return jsonify({"msg": str(e)}), 500

@daily_log_bp.route('/<int:log_id>/approve', methods=['POST'])
@jwt_required()
def approve_daily_log(log_id):
    """
    日報の承認API。
    RBACにより、権限（APPROVE_DAILY_LOG）を持つ職員のみ実行可能。
    """
    current_supporter_id = int(get_jwt_identity())
    
    # 1. 権限チェック
    if not check_permission(current_supporter_id, 'APPROVE_DAILY_LOG'):
        return jsonify({"msg": "Permission denied"}), 403
        
    log = db.session.get(DailyLog, log_id)
    if not log:
        return jsonify({"msg": "Log not found"}), 404
        
    # 2. 承認実行
    log.log_status = 'FINALIZED'
    log.approver_id = current_supporter_id
    log.approved_at = datetime.now(timezone.utc)
    
    db.session.commit()
    
    return jsonify({"msg": "DailyLog approved", "status": log.log_status}), 200