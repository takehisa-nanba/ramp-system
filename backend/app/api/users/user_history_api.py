"""Read the selected user's recorded support events in business-date order."""
from flask import jsonify
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import select, union_all, literal, cast, String, func
from backend.app.extensions import db
from backend.app.models import (
    CaseConferenceLog, MonitoringReport, OfficeServiceConfiguration, PlanAssessment,
    SupportPlan, SupportRecord, Supporter,
)
from backend.app.services.core_service import parse_jwt_identity
from backend.app.services.plan_assessment_service import assessment_scope
from . import users_bp


@users_bp.get('/<int:user_id>/history')
def support_history(user_id):
    _, actor_id = parse_jwt_identity(get_jwt_identity())
    assessment_scope(user_id, None, actor_id, 'VIEW')
    actor = db.session.get(Supporter, actor_id)
    configs = select(OfficeServiceConfiguration.id).where(OfficeServiceConfiguration.office_id == actor.office_id)

    def service_visible(column):
        return column.is_(None) | column.in_(configs)

    def event(title, model, day, by=None):
        return select(literal(title).label("title"), model.id.label("id"),
            cast(func.date(day), String).label("day"), (by if by is not None else literal(None)).label("actor_id"))

    plans = (SupportPlan.user_id == user_id, service_visible(SupportPlan.office_service_configuration_id))
    visible_plan_ids = select(SupportPlan.id).where(*plans)
    sources = [
        event("アセスメントを実施", PlanAssessment, PlanAssessment.interview_date, PlanAssessment.supporter_id)
            .where(PlanAssessment.user_id == user_id, service_visible(PlanAssessment.office_service_configuration_id)),
        event("支援記録を登録", SupportRecord, SupportRecord.log_date, SupportRecord.supporter_id)
            .where(SupportRecord.user_id == user_id, service_visible(SupportRecord.office_service_configuration_id)),
        event("ケース会議を実施", CaseConferenceLog, CaseConferenceLog.conference_datetime, CaseConferenceLog.initiator_supporter_id)
            .where(CaseConferenceLog.user_id == user_id, CaseConferenceLog.deleted_at.is_(None),
                   CaseConferenceLog.support_plan_id.is_(None) | CaseConferenceLog.support_plan_id.in_(visible_plan_ids)),
        event("モニタリングを実施", MonitoringReport, MonitoringReport.report_date, MonitoringReport.supporter_id)
            .where(MonitoringReport.support_plan_id.in_(visible_plan_ids), MonitoringReport.deleted_at.is_(None)),
    ]
    for title, day, by in (
        ("計画原案を作成", SupportPlan.draft_created_at, None),
        ("サビ管が計画を承認", SupportPlan.sabikan_approved_at, SupportPlan.sabikan_approved_by_id),
        ("計画への同意を記録", SupportPlan.consented_at, None),
        ("計画を有効化", SupportPlan.activated_at, None),
    ):
        sources.append(event(title, SupportPlan, day, by).where(*plans, day.is_not(None)))
    events = union_all(*sources).subquery()
    result = db.session.execute(select(events.c.title, events.c.day, events.c.id,
        Supporter.last_name, Supporter.first_name).outerjoin(Supporter, Supporter.id == events.c.actor_id)
        .order_by(events.c.day.desc(), events.c.title, events.c.id.desc()))
    return jsonify([dict(id=r.id, title=r.title, day=r.day,
        actor=f"{r.last_name} {r.first_name}" if r.last_name else None) for r in result])
