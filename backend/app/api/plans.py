# backend/app/api/plans.py

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.app import db
from backend.app.models import SupportPlan, IndividualSupportGoal
from backend.app.services.support_service import SupportService
from backend.app.services.core_service import check_permission

plans_bp = Blueprint('plans', __name__, url_prefix='/api/plans')
support_service = SupportService()

# -------------------------------------------------------------------
# 1. 計画作成 (DRAFT)
# -------------------------------------------------------------------

@plans_bp.route('/', methods=['POST'])
@jwt_required()
def create_plan():
    """
    新しい個別支援計画の原案 (DRAFT) を作成する。
    権限 'サービス管理責任者' が必要。
    """
    supporter_id = int(get_jwt_identity())
    data = request.get_json()
    user_id = data.get('user_id')
    policy_id = data.get('holistic_support_policy_id')

    if not check_permission(supporter_id, 'サービス管理責任者'):
        return jsonify({"msg": "Permission denied: Requires 'サービス管理責任者'"}), 403

    if not user_id or not policy_id:
        return jsonify({"msg": "Missing user_id or holistic_support_policy_id"}), 400

    try:
        new_plan = support_service.create_plan_draft(
            user_id=user_id,
            sabikan_id=supporter_id,
            based_on_policy_id=policy_id
        )
        db.session.commit()
        return jsonify({
            "msg": "Plan draft created successfully",
            "plan_id": new_plan.id,
            "user_id": new_plan.user_id,
            "status": new_plan.plan_status
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Plan creation failed: {e}"}), 500

# -------------------------------------------------------------------
# 2. 目標の追加 (IndividualSupportGoal)
# -------------------------------------------------------------------

@plans_bp.route('/<int:plan_id>/goal', methods=['POST'])
@jwt_required()
def add_individual_goal(plan_id):
    """
    既存の計画に具体的な個別支援目標を追加する。
    """
    supporter_id = int(get_jwt_identity())
    data = request.get_json()
    short_term_goal_id = data.get('short_term_goal_id')
    
    # 権限は CREATE_PLAN でカバーされると仮定

    if not short_term_goal_id or not data.get('concrete_goal'):
        return jsonify({"msg": "Missing required goal data"}), 400
        
    try:
        # ここでは、簡略化のため、LongTermGoal -> ShortTermGoal の階層構造は
        # フロントエンドが既に持っているものとし、直接 ShortTermGoal ID を使います。
        
        new_goal = IndividualSupportGoal(
            short_term_goal_id=short_term_goal_id,
            concrete_goal=data['concrete_goal'],
            user_commitment=data.get('user_commitment', '未記入'),
            support_actions=data.get('support_actions', '未記入'),
            service_type=data.get('service_type', 'TRAINING'),
            is_facility_in_deemed=data.get('is_facility_in_deemed', False),
            is_work_preparation_positioning=data.get('is_work_preparation_positioning', False)
        )
        
        db.session.add(new_goal)
        db.session.commit()
        
        return jsonify({
            "msg": "Individual goal added",
            "goal_id": new_goal.id,
            "plan_id": plan_id
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Goal creation failed: {e}"}), 500

# -------------------------------------------------------------------
# 3. 計画の承認・有効化 API
# -------------------------------------------------------------------

@plans_bp.route('/<int:plan_id>/activate', methods=['POST'])
@jwt_required()
def activate_plan(plan_id):
    """
    サビ管承認と利用者同意が完了した計画を ACTIVE にする。
    """
    supporter_id = int(get_jwt_identity())
    data = request.get_json()
    consent_log_id = data.get('consent_log_id')
    
    # 承認者はサビ管である必要があり、ここでは suppor_id がサビ管であることを前提とします
    
    if not consent_log_id:
        return jsonify({"msg": "Missing consent_log_id"}), 400
        
    try:
        final_plan = support_service.finalize_and_activate_plan(
            plan_id=plan_id,
            consent_log_id=consent_log_id
        )
        db.session.commit()
        
        return jsonify({
            "msg": "Plan activated successfully",
            "plan_id": final_plan.id,
            "status": final_plan.plan_status
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Activation failed: {e}"}), 500