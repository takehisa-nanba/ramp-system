"""Service-aware entry into the existing SupportRecord ledger."""
from datetime import date
from backend.app.extensions import db
from backend.app.models import SupportRecord, SupportPlan, JobRetentionContract, ServiceTypeMaster, OfficeServiceConfiguration
from backend.app.services.job_retention_service import JobRetentionService, atomic_event
from backend.app.utils.errors import ValidationError, BusinessRuleError


@atomic_event
def create_service_support_record(data, actor_id):
    config_id = data.get('office_service_configuration_id')
    if type(config_id) is not int:
        raise ValidationError('事業所サービスを指定してください。')
    JobRetentionService.authorize(actor_id, 'CREATE', config_id)
    try:
        log_date = date.fromisoformat(data['log_date'])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValidationError('支援日を指定してください。') from exc
    config = db.session.get(OfficeServiceConfiguration, config_id)
    service = db.session.get(ServiceTypeMaster, config.service_type_master_id)
    if service.service_code != 'RETENTION':
        raise ValidationError('このサービス指定による登録は定着支援が対象です。')
    contract = JobRetentionContract.query.filter(
        JobRetentionContract.user_id == data.get('user_id'),
        JobRetentionContract.office_service_configuration_id == config_id,
        JobRetentionContract.status.in_(['ACTIVE', 'FINISHED']),
        JobRetentionContract.deleted_at.is_(None),
        JobRetentionContract.contract_start_date <= log_date,
        JobRetentionContract.contract_end_date >= log_date).first()
    if not contract:
        raise BusinessRuleError('支援日を含む定着支援契約がありません。')
    duration = data.get('support_duration_seconds')
    record_type = data.get('support_record_type', 'DIRECT_SUPPORT')
    if duration is not None and (type(duration) is not int or duration < 0):
        raise ValidationError('支援時間は0以上の整数で指定してください。')
    if record_type == 'DIRECT_SUPPORT' and duration is None:
        raise ValidationError('直接支援の時間を入力してください。')
    content = data.get('support_content')
    if not isinstance(content, str) or not content.strip():
        raise ValidationError('支援内容を入力してください。')
    plan_id = data.get('support_plan_id')
    if plan_id is not None:
        plan = db.session.get(SupportPlan, plan_id)
        if not plan or plan.user_id != contract.user_id or plan.office_service_configuration_id != config_id:
            raise ValidationError('利用者・サービスと計画が一致していません。')
    record = SupportRecord(user_id=contract.user_id, supporter_id=actor_id,
        office_service_configuration_id=config_id, log_date=log_date,
        support_record_type=record_type, support_content=content,
        support_duration_seconds=duration, support_plan_id=plan_id,
        location_type=data.get('location_type'), location_detail=data.get('location_detail'),
        decision_reason=data.get('decision_reason'), observation_note=data.get('observation_note'))
    db.session.add(record)
    return record
