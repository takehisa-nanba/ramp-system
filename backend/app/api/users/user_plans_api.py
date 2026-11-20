"""
GET /api/users/<user_id>/support-plans
利用者の個別支援計画一覧（有効計画 + 履歴）を返す。
"""
from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.app import db
from backend.app.models import User, SupportPlan, LongTermGoal, ShortTermGoal, IndividualSupportGoal
from backend.app.services.plan_presentation import serialize_plan
from backend.app.services.core_service import parse_jwt_identity
from backend.app.services.support_plan_service import SupportPlanService
from backend.app.models import Supporter
from . import users_bp


def _serialize_plan_summary(plan: SupportPlan, supporter) -> dict:
    """計画の概要を返す（履歴表示用）"""
    long_term_goals = []
    for ltg in plan.long_term_goals:
        long_term_goals.append({
            "id": ltg.id,
            "description": ltg.description,
            "challenges": ltg.challenges,
            "short_term_goals": [{
                "description": stg.description
            } for stg in ltg.short_term_goals]
        })

    return {
        "id": plan.id,
        "office_service_configuration_id": plan.office_service_configuration_id,
        "plan_version": plan.plan_version,
        "plan_status": plan.plan_status,
        "start_date": plan.plan_start_date.isoformat() if plan.plan_start_date else None,
        "end_date": plan.plan_end_date.isoformat() if plan.plan_end_date else None,
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
        "based_on_plan_id": plan.based_on_plan_id,
        "can_approve": bool(supporter and plan.plan_status == "DRAFT" and SupportPlanService.can_approve_plan(supporter, plan)),
        "draft_created_at": plan.draft_created_at.isoformat() if plan.draft_created_at else None,
        "consented_at": plan.consented_at.isoformat() if plan.consented_at else None,
        "timeline_deviation_reason": plan.timeline_deviation_reason,
        "holistic_policy": {
            "id": plan.holistic_policy.id,
            "user_intention_content": plan.holistic_policy.user_intention_content,
            "support_policy_content": plan.holistic_policy.support_policy_content
        } if plan.holistic_policy else None,
        "long_term_goals": long_term_goals
    }


@users_bp.route('/<int:user_id>/support-plans', methods=['GET'])
@jwt_required()
def get_user_support_plans(user_id: int):
    """
    利用者の個別支援計画一覧を取得する。
    - active_plan: 現在有効な計画（詳細あり）
    - plan_history: 過去の計画の概要リスト
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

    config_id = request.args.get('office_service_configuration_id', type=int)
    plans = user.support_plans.filter_by(office_service_configuration_id=config_id)
    active_plan = plans.filter_by(plan_status='ACTIVE').first()
    history_plans = plans.filter(
        SupportPlan.plan_status.in_(['ARCHIVED', 'DRAFT', 'PENDING_CONSENT', 'PENDING_CONFERENCE'])
    ).order_by(SupportPlan.created_at.desc()).all()

    _, actor_id = parse_jwt_identity(get_jwt_identity())
    supporter = db.session.get(Supporter, actor_id)
    return jsonify({
        "active_plan": serialize_plan(active_plan) if active_plan else None,
        "plan_history": [_serialize_plan_summary(p, supporter) for p in history_plans],
    }), 200


@users_bp.route('/<int:user_id>/plan-assessments', methods=['GET', 'POST'])
@jwt_required()
def plan_assessments(user_id):
    from flask_jwt_extended import get_jwt_identity
    from backend.app.models import PlanAssessment
    from backend.app.services.core_service import parse_jwt_identity
    from backend.app.services.plan_assessment_service import assessment_scope, record_assessment, attach_assessment
    from backend.app.utils.errors import NotFoundError
    _, actor_id = parse_jwt_identity(get_jwt_identity())
    config_id = request.args.get('office_service_configuration_id', type=int)
    if request.method == 'POST':
        data = request.get_json()
        item = record_assessment(user_id, config_id, actor_id, data)
        if data.get('plan_id') is not None:
            plan = SupportPlan.query.filter_by(id=data['plan_id'], user_id=user_id,
                office_service_configuration_id=config_id).with_for_update().first()
            if not plan:
                raise NotFoundError()
            db.session.flush()
            attach_assessment(plan, item.id, actor_id)
        db.session.commit()
        return jsonify(id=item.id), 201
    assessment_scope(user_id, config_id, actor_id, "VIEW")
    items = PlanAssessment.query.filter_by(user_id=user_id, office_service_configuration_id=config_id).order_by(
        PlanAssessment.interview_date.desc(), PlanAssessment.id.desc()).all()
    return jsonify([dict(id=a.id, plan_id=a.plan_id, interview_date=a.interview_date.isoformat(),
        method=a.method, exception_reason=a.exception_reason, summary=a.summary) for a in items])
