from backend.app.models import SupportPlan


def serialize_plan(plan: SupportPlan) -> dict:
    """有効計画をフル形式でシリアライズする"""
    long_term_goals = []
    for ltg in plan.long_term_goals:
        short_term_goals = []
        for stg in ltg.short_term_goals:
            individual_goals = []
            for ig in stg.individual_goals:
                individual_goals.append({
                    "id": ig.id,
                    "concrete_goal": ig.concrete_goal,
                    "user_commitment": ig.user_commitment,
                    "support_actions": ig.support_actions,
                    "service_type": ig.service_type,
                })
            short_term_goals.append({
                "id": stg.id,
                "description": stg.description,
                "target_period_start": stg.target_period_start.isoformat() if stg.target_period_start else None,
                "target_period_end": stg.target_period_end.isoformat() if stg.target_period_end else None,
                "next_review_date": stg.next_review_date.isoformat() if stg.next_review_date else None,
                "individual_goals": individual_goals,
            })
        long_term_goals.append({
            "id": ltg.id,
            "description": ltg.description,
            "challenges": ltg.challenges,
            "target_period_start": ltg.target_period_start.isoformat() if ltg.target_period_start else None,
            "target_period_end": ltg.target_period_end.isoformat() if ltg.target_period_end else None,
            "short_term_goals": short_term_goals,
        })

    # モニタリング期限の算出
    # TODO: replace plan_end_date fallback with formal monitoring schedule field
    # 正式な monitoring_schedule テーブルが実装されたら、そちらから next_monitoring_due を参照する。
    # 現時点では plan_end_date を暫定表示する。
    next_monitoring_due = plan.plan_end_date.isoformat() if plan.plan_end_date else None

    return {
        "id": plan.id,
        "office_service_configuration_id": plan.office_service_configuration_id,
        "plan_version": plan.plan_version,
        "plan_status": plan.plan_status,
        "start_date": plan.plan_start_date.isoformat() if plan.plan_start_date else None,
        "end_date": plan.plan_end_date.isoformat() if plan.plan_end_date else None,
        "next_monitoring_due": next_monitoring_due,
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
        "based_on_plan_id": plan.based_on_plan_id,
        "holistic_policy": {
            "id": plan.holistic_policy.id,
            "user_intention_content": plan.holistic_policy.user_intention_content,
            "support_policy_content": plan.holistic_policy.support_policy_content
        } if plan.holistic_policy else None,
        "long_term_goals": long_term_goals,
    }
