"""Retention lifecycle built on the shared RAMP core."""
import json
from functools import wraps
from datetime import date
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from backend.app.extensions import db
from backend.app.models import (User, Supporter, OfficeServiceConfiguration, ServiceTypeMaster,
    ServiceCertificate, GrantedService, JobPlacementLog, JobRetentionContract, AuditActionLog, SupportPlan)
from backend.app.services.core_service import check_permission
from backend.app.utils.errors import ValidationError, PermissionDenied, NotFoundError, BusinessRuleError, ConflictError
from backend.app.utils.timezone import get_jst_today
from backend.app.domain.employment.retention_eligibility import is_retention_eligible


def atomic_event(method):
    @wraps(method)
    def wrapped(*args, **kwargs):
        try:
            result = method(*args, **kwargs)
            db.session.commit()
            return result
        except IntegrityError as exc:
            db.session.rollback()
            raise ConflictError('契約が同時に更新されました。再読み込みしてください。') from exc
        except Exception:
            db.session.rollback()
            raise
    return wrapped


def valid_retention_designation(config_id, on_date=None):
    on_date = on_date or get_jst_today()
    config = db.session.get(OfficeServiceConfiguration, config_id)
    if not config or not config.office or not config.office.is_active:
        return False
    service_type = db.session.get(ServiceTypeMaster, config.service_type_master_id)
    return bool(service_type and service_type.service_code == 'RETENTION'
                and config.initial_designation_date and config.designation_expiry_date
                and config.initial_designation_date <= on_date <= config.designation_expiry_date)


class JobRetentionService:
    @staticmethod
    def authorize(actor_id, permission, config_id=None):
        actor = db.session.get(Supporter, actor_id)
        today = get_jst_today()
        if (not actor or not actor.is_active or actor.hire_date > today
                or (actor.retirement_date and actor.retirement_date <= today)
                or not check_permission(actor_id, permission)):
            raise PermissionDenied()
        if config_id is not None:
            config = db.session.get(OfficeServiceConfiguration, config_id)
            if not config or config.office_id != actor.office_id:
                raise PermissionDenied()
        return actor

    @staticmethod
    def serialize(contract):
        return {key: (value.isoformat() if isinstance(value, date) else value)
                for key in ('id', 'user_id', 'office_service_configuration_id',
                            'contract_start_date', 'contract_end_date', 'status')
                for value in [getattr(contract, key)]}

    @classmethod
    def contracts_query(cls, actor_id):
        actor = cls.authorize(actor_id, 'VIEW')
        return JobRetentionContract.query.join(OfficeServiceConfiguration).filter(
            OfficeServiceConfiguration.office_id == actor.office_id,
            JobRetentionContract.deleted_at.is_(None))

    @classmethod
    def list_users(cls, actor_id):
        today = get_jst_today()
        contracts = cls.contracts_query(actor_id).join(User).filter(
            JobRetentionContract.status == 'ACTIVE',
            JobRetentionContract.contract_start_date <= today,
            JobRetentionContract.contract_end_date >= today,
            User.deleted_at.is_(None)).order_by(JobRetentionContract.id.desc()).all()
        return [dict(cls.serialize(c), display_name=c.user.display_name,
                     office_name=c.service_configuration.office.office_name) for c in contracts]

    @classmethod
    def get_contract(cls, contract_id, actor_id):
        contract = cls.contracts_query(actor_id).filter(JobRetentionContract.id == contract_id).first()
        if not contract:
            raise NotFoundError()
        return contract

    @staticmethod
    def audit(contract, actor_id, action, before, reason, ip_address, user_agent):
        db.session.add(AuditActionLog(
            actor_supporter_id=actor_id, user_id=contract.user_id, action=action,
            entity_type='JobRetentionContract', entity_id=contract.id,
            before_value=json.dumps(before, ensure_ascii=False),
            after_value=json.dumps(JobRetentionService.serialize(contract), ensure_ascii=False),
            reason=reason, ip_address=ip_address, user_agent=user_agent))

    @classmethod
    @atomic_event
    def start_retention_support(cls, user_id, config_id, start_date, end_date,
                                actor_id, reason, ip_address=None, user_agent=None):
        cls.authorize(actor_id, 'CREATE', config_id)
        if not isinstance(reason, str) or not reason.strip():
            raise ValidationError('開始理由を入力してください。')
        if not isinstance(start_date, date) or not isinstance(end_date, date) or end_date < start_date:
            raise ValidationError('契約期間を確認してください。')
        if start_date > get_jst_today():
            raise ValidationError('開始日が未来の契約は開始できません。')
        # Serialize concurrent starts for the same user on PostgreSQL.
        user = User.query.filter_by(id=user_id).with_for_update().first()
        if not user or user.deleted_at:
            raise NotFoundError('利用者が見つかりません。')
        placement = JobPlacementLog.query.filter(
            JobPlacementLog.user_id == user_id,
            JobPlacementLog.placement_date <= start_date
        ).order_by(JobPlacementLog.placement_date.desc(), JobPlacementLog.id.desc()).first()
        if not placement or not is_retention_eligible(placement.placement_date, placement.separation_date, start_date):
            raise BusinessRuleError('就職から6か月の経過と在職状況を確認してください。')
        grant = GrantedService.query.join(ServiceCertificate).join(ServiceTypeMaster).filter(
            ServiceCertificate.user_id == user_id,
            ServiceCertificate.office_service_configuration_id == config_id,
            ServiceCertificate.status == 'ACTIVE', ServiceCertificate.voided_at.is_(None),
            ServiceCertificate.certificate_issue_date <= start_date,
            ServiceTypeMaster.service_code == 'RETENTION',
            GrantedService.is_tentative.is_(False),
            GrantedService.granted_start_date <= start_date,
            GrantedService.granted_end_date >= end_date).first()
        if not grant:
            raise BusinessRuleError('契約期間を満たす承認済みの定着支援支給決定が確認できません。')
        if not valid_retention_designation(config_id, start_date) or not valid_retention_designation(config_id, end_date):
            raise BusinessRuleError('契約期間を満たす事業所の定着支援指定が確認できません。')
        existing = JobRetentionContract.query.filter(
            JobRetentionContract.user_id == user_id, JobRetentionContract.deleted_at.is_(None),
            or_(JobRetentionContract.status == 'ACTIVE',
                (JobRetentionContract.contract_start_date <= end_date)
                & (JobRetentionContract.contract_end_date >= start_date))).first()
        if existing:
            raise ConflictError('有効な契約または期間が重なる契約があります。')
        contract = JobRetentionContract(user_id=user_id, office_service_configuration_id=config_id,
            contract_start_date=start_date, contract_end_date=end_date, status='ACTIVE')
        db.session.add(contract)
        db.session.flush()
        cls.audit(contract, actor_id, 'START_RETENTION_SUPPORT', None, reason, ip_address, user_agent)
        return contract

    @classmethod
    @atomic_event
    def finish_retention_support(cls, contract_id, end_date, actor_id, reason,
                                 ip_address=None, user_agent=None):
        contract = cls.get_contract(contract_id, actor_id)
        cls.authorize(actor_id, 'EDIT', contract.office_service_configuration_id)
        contract = JobRetentionContract.query.filter_by(id=contract_id).with_for_update().populate_existing().one()
        if contract.status != 'ACTIVE' or contract.deleted_at:
            raise ConflictError('開始済みの契約のみ終了できます。')
        if (not isinstance(end_date, date) or end_date < contract.contract_start_date
                or end_date > min(get_jst_today(), contract.contract_end_date)):
            raise ValidationError('終了日を確認してください。')
        if not isinstance(reason, str) or not reason.strip():
            raise ValidationError('終了理由を入力してください。')
        before = cls.serialize(contract)
        plans = SupportPlan.query.filter_by(
            user_id=contract.user_id,
            office_service_configuration_id=contract.office_service_configuration_id,
            plan_status='ACTIVE').with_for_update().populate_existing().all()
        for plan in plans:
            plan.plan_status = 'ARCHIVED'
            # Signed document dates are immutable; only lifecycle status changes.
            db.session.add(AuditActionLog(
                actor_supporter_id=actor_id, user_id=contract.user_id,
                action='ARCHIVE_SUPPORT_PLAN', entity_type='SupportPlan', entity_id=plan.id,
                before_value=json.dumps({'plan_status': 'ACTIVE'}),
                after_value=json.dumps({'plan_status': 'ARCHIVED'}),
                reason=f'定着支援契約 {contract.id} 終了: {reason}',
                ip_address=ip_address, user_agent=user_agent))
        contract.status = 'FINISHED'
        contract.contract_end_date = end_date
        cls.audit(contract, actor_id, 'FINISH_RETENTION_SUPPORT', before, reason, ip_address, user_agent)
        return contract
