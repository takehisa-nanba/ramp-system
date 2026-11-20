from datetime import date
from backend.app.extensions import db
from backend.app.models import OfficeServiceConfiguration, PlanAssessment, ServiceCertificate, User
from backend.app.services.job_retention_service import JobRetentionService
from backend.app.utils.errors import ConflictError, NotFoundError, PermissionDenied, ValidationError
from backend.app.utils.timezone import get_jst_today


def assessment_scope(user_id, config_id, actor_id, permission):
    actor = JobRetentionService.authorize(actor_id, permission, config_id)
    user = db.session.get(User, user_id)
    if not user or user.deleted_at:
        raise NotFoundError()
    certificates = ServiceCertificate.query.join(OfficeServiceConfiguration).filter(
        ServiceCertificate.user_id == user_id, ServiceCertificate.voided_at.is_(None),
        OfficeServiceConfiguration.office_id == actor.office_id)
    if config_id is not None:
        certificates = certificates.filter(ServiceCertificate.office_service_configuration_id == config_id)
    elif user.primary_supporter_id == actor_id or (actor.office_id and user.primary_supporter and user.primary_supporter.office_id == actor.office_id):
        return
    if not actor.office_id or not certificates.first():
        raise PermissionDenied()


def record_assessment(user_id, config_id, actor_id, data):
    assessment_scope(user_id, config_id, actor_id, "CREATE")
    try:
        interview_date = date.fromisoformat(data["interview_date"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValidationError("面談日を入力してください。") from exc
    method = data.get("method")
    reason = data.get("exception_reason")
    summary = data.get("summary")
    if interview_date > get_jst_today():
        raise ValidationError("実施済みの面談日を入力してください。")
    if method not in ("IN_PERSON", "VIDEO", "PHONE"):
        raise ValidationError("面談方法を選んでください。")
    if method != "IN_PERSON" and (not isinstance(reason, str) or not reason.strip()):
        raise ValidationError("対面以外で面談した理由を入力してください。")
    if not isinstance(summary, str) or not summary.strip():
        raise ValidationError("本人の希望と確認した内容を入力してください。")
    item = PlanAssessment(user_id=user_id, office_service_configuration_id=config_id,
        supporter_id=actor_id, method=method, summary=summary.strip(), interview_date=interview_date,
        exception_reason=reason.strip() if method != "IN_PERSON" else None)
    db.session.add(item)
    return item


def attach_assessment(plan, assessment_id, actor_id):
    assessment_scope(plan.user_id, plan.office_service_configuration_id, actor_id, "CREATE")
    item = PlanAssessment.query.filter_by(id=assessment_id, user_id=plan.user_id,
        office_service_configuration_id=plan.office_service_configuration_id).with_for_update().first()
    if not item:
        raise ValidationError("本人・サービスに対応するアセスメントを選んでください。")
    if plan.plan_status != "DRAFT" or item.plan_id is not None:
        raise ConflictError("この原案または面談記録はすでに更新されています。")
    if PlanAssessment.query.filter_by(plan_id=plan.id).first():
        raise ConflictError("原案にはすでに面談記録があります。")
    item.plan_id = plan.id
