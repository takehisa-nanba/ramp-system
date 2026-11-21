"""Retention content transactions. Lock order: contract -> plan -> detail.

No lifecycle changes here. The common plan service owns approval/consent/activation.
"""
import json
from datetime import date, datetime, timezone
from functools import wraps
from sqlalchemy.exc import IntegrityError
from backend.app.extensions import db
from backend.app.models import (SupportPlan, ServiceTypeMaster, JobRetentionContract,
    JobRetentionPlanDetail, JobRetentionPlanSupportItem, JobPlacementLog, EmployerMaster,
    UserOrganizationLink, GoalAssessment, AssessorType, AuditActionLog)
from backend.app.services.job_retention_service import JobRetentionService
from backend.app.services.core_service import check_permission
from backend.app.utils.errors import ValidationError, ConflictError, NotFoundError, PermissionDenied

PLAN_FIELDS = ('handover_notes', 'physical_work_environment', 'human_work_environment',
    'job_description', 'contract_wage', 'holidays', 'daily_work_hours', 'break_time',
    'health_status_notes', 'living_environment_notes', 'user_needs', 'special_notes')
PRIVATE_FIELDS = ('health_status_notes', 'living_environment_notes')
ITEM_FIELDS = ('sequence_no', 'support_policy_content', 'start_date', 'end_date', 'frequency')
EVALUATION_FIELDS = ('implementation_status', 'achievement_status', 'effect_satisfaction_notes', 'remaining_issues_and_actions')
ACHIEVEMENT = ('ACHIEVED', 'PARTIAL', 'NOT_ACHIEVED')


def transaction(method):
    @wraps(method)
    def wrapped(*args, **kwargs):
        try:
            result = method(*args, **kwargs)
            db.session.commit()
            return result
        except IntegrityError as exc:
            db.session.rollback()
            raise ConflictError('同時更新または関連情報の競合があります。再読み込みしてください。') from exc
        except Exception:
            db.session.rollback()
            raise
    return wrapped


def parse_date(value):
    try:
        if not isinstance(value, str) or len(value) != 10:
            raise ValueError()
        return date.fromisoformat(value)
    except (ValueError, TypeError) as exc:
        raise ValidationError('日付はYYYY-MM-DD形式で指定してください。') from exc


def text_value(value):
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > 10000:
        raise ValidationError('文章は10000文字以内で入力してください。')
    return value.strip() or None


class JobRetentionPlanService:
    @staticmethod
    def is_retention(plan):
        config = plan.service_configuration
        service = db.session.get(ServiceTypeMaster, config.service_type_master_id) if config else None
        return bool(service and service.service_code == 'RETENTION')

    @classmethod
    def get_plan(cls, plan_id, actor_id, permission='VIEW', edit=False, evaluation=False):
        plan = db.session.get(SupportPlan, plan_id)
        if not plan:
            raise NotFoundError()
        if not cls.is_retention(plan):
            raise ValidationError('就労定着支援の計画を選択してください。')
        JobRetentionService.authorize(actor_id, permission, plan.office_service_configuration_id)
        if not plan.user or plan.user.deleted_at:
            raise NotFoundError()
        if edit:
            # Same first lock as finish and activate. Re-read state after waiting.
            from backend.app.services.support_plan_service import SupportPlanService
            SupportPlanService.validate_retention_plan_period(plan, plan.plan_start_date, plan.plan_end_date)
            plan = SupportPlan.query.filter_by(id=plan_id).with_for_update().populate_existing().one()
            allowed = ('ACTIVE',) if evaluation else ('DRAFT',)
            if plan.plan_status not in allowed:
                raise ConflictError('計画内容は下書き時、評価は有効な計画でのみ編集できます。')
            SupportPlanService.validate_retention_plan_period(plan, plan.plan_start_date, plan.plan_end_date)
        return plan

    @staticmethod
    def get_detail(plan, expected_version):
        detail = JobRetentionPlanDetail.query.filter_by(support_plan_id=plan.id).populate_existing().first()
        current = detail.version if detail else 0
        if type(expected_version) is not int or expected_version != current:
            raise ConflictError('他の職員による更新があります。再読み込みしてください。')
        return detail

    @staticmethod
    def audit(plan, actor_id, action, before, after, reason, ip_address=None, user_agent=None):
        # PII bodies must never be duplicated in plain audit JSON.
        def redact(data):
            result = dict(data or {})
            for key in PRIVATE_FIELDS:
                if key in result:
                    result[key] = {'recorded': result[key] is not None}
            return result
        db.session.add(AuditActionLog(actor_supporter_id=actor_id, user_id=plan.user_id,
            action=action, entity_type='JobRetentionPlanDetail', entity_id=plan.id,
            before_value=json.dumps(redact(before), ensure_ascii=False, default=str),
            after_value=json.dumps(redact(after), ensure_ascii=False, default=str),
            reason=reason, ip_address=ip_address, user_agent=user_agent))

    @staticmethod
    def item_dict(item):
        return {key: (value.isoformat() if isinstance(value, date) else value)
            for key in ('id',) + ITEM_FIELDS + EVALUATION_FIELDS for value in [getattr(item, key)]}

    @classmethod
    def read(cls, plan_id, actor_id):
        plan = cls.get_plan(plan_id, actor_id)
        detail = JobRetentionPlanDetail.query.filter_by(support_plan_id=plan.id).populate_existing().first()
        pii = check_permission(actor_id, 'VIEW_PII')
        contract = JobRetentionContract.query.filter_by(user_id=plan.user_id,
            office_service_configuration_id=plan.office_service_configuration_id,
            status='ACTIVE', deleted_at=None).filter(
                JobRetentionContract.contract_start_date <= plan.plan_start_date,
                JobRetentionContract.contract_end_date >= plan.plan_end_date).first() if plan.plan_start_date and plan.plan_end_date else None
        placements = JobPlacementLog.query.filter_by(user_id=plan.user_id).order_by(JobPlacementLog.placement_date.desc()).all()
        def employment(p):
            e = p.employer
            return dict(job_placement_id=p.id, employment_start_date=p.placement_date.isoformat(),
                employment_type=p.employment_status, employer_name=e.company_name,
                industry=e.industry_type, employer_address=e.address, employer_phone=e.contact_number,
                employer_contact_person=e.contact_person)
        result = dict(plan_id=plan.id, plan_status=plan.plan_status, version=detail.version if detail else 0,
            start_date=plan.plan_start_date, end_date=plan.plan_end_date,
            permissions=dict(edit=bool(contract and plan.plan_status == 'DRAFT' and check_permission(actor_id, 'EDIT')),
                create=bool(contract and plan.plan_status == 'DRAFT' and check_permission(actor_id, 'CREATE')),
                evaluate=bool(contract and plan.plan_status == 'ACTIVE' and detail and check_permission(actor_id, 'EDIT')),
                delete=bool(contract and plan.plan_status == 'DRAFT' and check_permission(actor_id, 'DELETE')),
                view_pii=pii, edit_pii=pii and check_permission(actor_id, 'EDIT_PII')),
            detail=None, employment_options=[employment(p) for p in placements],
            organization_options=[dict(id=link.id, name=link.organization.organization_name)
                for link in UserOrganizationLink.query.filter_by(user_id=plan.user_id).all()],
            related_support_organizations=[dict(id=link.id,name=link.organization.organization_name)
                for link in detail.organization_links] if detail else [],
            goals=[dict(goal_type=kind, goal_id=g.id, description=g.description,
                        start_date=g.target_period_start, end_date=g.target_period_end)
                for lt in plan.long_term_goals for kind,g in [('LONG',lt)]+[('SHORT',s) for s in lt.short_term_goals]],
            goal_assessments=[], assessor_types=[dict(id=a.id, name=a.name) for a in AssessorType.query.all()])
        for goal in result['goals']:
            assessment = GoalAssessment.query.filter_by(goal_type=goal['goal_type'], goal_id=goal['goal_id']).order_by(GoalAssessment.assessment_date.desc(), GoalAssessment.id.desc()).first()
            if assessment:
                result['goal_assessments'].append(dict(goal_type=assessment.goal_type, goal_id=assessment.goal_id,
                    achievement_status=assessment.achievement_status, assessment_date=assessment.assessment_date,
                    supporter_id=assessment.supporter_id))
        if detail:
            result['detail'] = {key: getattr(detail,key) for key in PLAN_FIELDS if key not in PRIVATE_FIELDS or pii}
            result['detail'].update(id=detail.id, job_placement_id=detail.job_placement_id,
                organization_link_ids=[link.id for link in detail.organization_links],
                created_by_id=detail.created_by_id, overall_evaluation=detail.overall_evaluation,
                evaluation_date=detail.evaluation_date, evaluation_author_id=detail.evaluation_author_id,
                support_items=[cls.item_dict(i) for i in detail.support_items if not i.deleted_at])
        # Explicit ISO dates rather than Flask's HTTP-date conversion.
        return json.loads(json.dumps(result, default=lambda v: v.isoformat()))

    @classmethod
    @transaction
    def view_detail(cls, plan_id, actor_id, **context):
        result = cls.read(plan_id, actor_id)
        if result['detail'] and result['permissions']['view_pii']:
            plan = db.session.get(SupportPlan,plan_id)
            cls.audit(plan,actor_id,'VIEW_PII',None,{'fields':list(PRIVATE_FIELDS)},'定着支援計画の健康・生活情報を閲覧',**context)
        return result

    @classmethod
    @transaction
    def save_detail(cls, plan_id, actor_id, data, **context):
        plan = cls.get_plan(plan_id, actor_id, 'VIEW', edit=True)
        detail = cls.get_detail(plan, data.get('version'))
        JobRetentionService.authorize(actor_id, 'EDIT' if detail else 'CREATE', plan.office_service_configuration_id)
        if set(data) - set(PLAN_FIELDS) - {'version','job_placement_id','employment','organization_link_ids'}:
            raise ValidationError('変更できない項目が含まれています。')
        if any(k in data for k in PRIVATE_FIELDS):
            JobRetentionService.authorize(actor_id, 'EDIT_PII', plan.office_service_configuration_id)
        before = {key: getattr(detail,key) for key in PLAN_FIELDS} if detail else {}
        if detail:
            before.update(job_placement_id=detail.job_placement_id,version=detail.version,
                organization_link_ids=[link.id for link in detail.organization_links])
        if not detail:
            detail = JobRetentionPlanDetail(support_plan_id=plan.id, created_by_id=actor_id, version=0)
            db.session.add(detail)
        if 'job_placement_id' in data:
            placement = db.session.get(JobPlacementLog, data['job_placement_id']) if type(data['job_placement_id']) is int else None
            if not placement or placement.user_id != plan.user_id:
                raise ValidationError('本人の就職記録を選択してください。')
            detail.job_placement_id = placement.id
        if 'organization_link_ids' in data:
            ids=data['organization_link_ids']
            if not isinstance(ids,list) or any(type(value) is not int or value<=0 for value in ids) or len(set(ids))!=len(ids):
                raise ValidationError('関係機関を確認してください。')
            links=UserOrganizationLink.query.filter(UserOrganizationLink.id.in_(ids),UserOrganizationLink.user_id==plan.user_id).all()
            if len(links)!=len(ids):
                raise ValidationError('本人の関係機関を選択してください。')
            detail.organization_links=links
        for key in PLAN_FIELDS:
            if key in data:
                setattr(detail,key,text_value(data[key]))
        detail.version += 1
        db.session.flush()
        if 'employment' in data:
            JobRetentionService.authorize(actor_id, 'EDIT', plan.office_service_configuration_id)
            if not isinstance(data['employment'], dict):
                raise ValidationError()
            cls.save_employment_source(plan, actor_id, detail, data['employment'], **context)
        cls.audit(plan, actor_id, 'SAVE_RETENTION_PLAN_DETAIL', before,
            dict({key:getattr(detail,key) for key in PLAN_FIELDS},job_placement_id=detail.job_placement_id,
                organization_link_ids=[link.id for link in detail.organization_links],
                version=detail.version,changed_fields=sorted(set(data)-{'version'})), '定着支援計画の入力', **context)
        return cls.read(plan.id, actor_id)

    @staticmethod
    def validate_items_period(plan, start_date, end_date):
        if plan.retention_detail:
            for item in plan.retention_detail.support_items:
                if not item.deleted_at and (not start_date or not end_date or item.start_date < start_date or item.end_date > end_date):
                    raise ValidationError('支援項目の期間を含む計画期間を指定してください。')

    @classmethod
    @transaction
    def save_item(cls, plan_id, actor_id, data, item_id=None, delete=False, **context):
        plan = cls.get_plan(plan_id, actor_id, 'DELETE' if delete else 'EDIT' if item_id else 'CREATE', edit=True)
        detail = cls.get_detail(plan, data.get('version'))
        if not detail:
            raise ValidationError('先に定着支援計画詳細を保存してください。')
        item = db.session.get(JobRetentionPlanSupportItem, item_id) if item_id else None
        if item_id and (not item or item.plan_detail_id != detail.id or item.deleted_at):
            raise NotFoundError()
        before = cls.item_dict(item) if item else {}
        if delete:
            if set(data) - {'version','reason'}:
                raise ValidationError()
            reason = text_value(data.get('reason'))
            if not reason or len(reason) < 10:
                raise ValidationError('削除理由を10文字以上で入力してください。')
            item.deleted_at = datetime.now(timezone.utc)
            item.deleted_by_id = actor_id
            item.delete_reason = reason
        else:
            if set(data) - set(ITEM_FIELDS) - {'version'}:
                raise ValidationError('評価は評価画面から入力してください。')
            values = {key:data.get(key,getattr(item,key,None)) for key in ITEM_FIELDS}
            if values['sequence_no'] is None and not item:
                values['sequence_no'] = max([i.sequence_no for i in detail.support_items] or [0])+1
            if type(values['sequence_no']) is not int or values['sequence_no'] <= 0:
                raise ValidationError('表示順は正の整数で指定してください。')
            for key in ('start_date','end_date'):
                if key in data or not item:
                    values[key] = parse_date(values[key])
            if not plan.plan_start_date <= values['start_date'] <= values['end_date'] <= plan.plan_end_date:
                raise ValidationError('支援項目の期間は計画期間内に設定してください。')
            for key in ('support_policy_content','frequency'):
                values[key] = text_value(values[key])
                if not values[key]:
                    raise ValidationError('支援内容と頻度を入力してください。')
            if not item:
                item = JobRetentionPlanSupportItem(plan_detail_id=detail.id)
                db.session.add(item)
            for key,value in values.items():
                setattr(item,key,value)
        detail.version += 1
        db.session.flush()
        db.session.expire(detail, ['support_items'])
        cls.audit(plan, actor_id, 'DELETE_RETENTION_SUPPORT_ITEM' if delete else 'SAVE_RETENTION_SUPPORT_ITEM',
            before, dict(cls.item_dict(item), deleted=delete), item.delete_reason if delete else '支援内容の入力', **context)
        return cls.read(plan.id, actor_id)

    @classmethod
    @transaction
    def update_employment(cls, plan_id, actor_id, data, **context):
        """Explicitly edit the shared source, never a second copy in plan detail.

        Once referenced by an approved plan, shared sources cannot be edited here.
        Employer reuse across users is also blocked to prevent cross-office edits.
        """
        plan = cls.get_plan(plan_id, actor_id, 'EDIT', edit=True)
        detail = cls.get_detail(plan,data.get('version'))
        cls.save_employment_source(plan, actor_id, detail, data, **context)
        detail.version += 1
        db.session.flush()
        return cls.read(plan_id,actor_id)

    @classmethod
    def save_employment_source(cls, plan, actor_id, detail, data, **context):
        if not detail or not detail.job_placement_id:
            raise ValidationError('先に就職記録を選択してください。')
        mapping = dict(employer_name='company_name',industry='industry_type',employer_address='address',
            employer_phone='contact_number',employer_contact_person='contact_person')
        if set(data)-set(mapping)-{'version','employment_start_date','employment_type'}:
            raise ValidationError()
        placement = JobPlacementLog.query.filter_by(id=detail.job_placement_id).with_for_update().populate_existing().one()
        employer = EmployerMaster.query.filter_by(id=placement.employer_id).with_for_update().populate_existing().one()
        if JobPlacementLog.query.filter(JobPlacementLog.employer_id == employer.id, JobPlacementLog.user_id != plan.user_id).first():
            raise ConflictError('他の利用者も参照する企業情報です。共通の企業管理で確認してください。')
        locked_reference = JobRetentionPlanDetail.query.join(SupportPlan).join(JobPlacementLog,
            JobRetentionPlanDetail.job_placement_id == JobPlacementLog.id).filter(
                JobPlacementLog.employer_id == employer.id, SupportPlan.plan_status != 'DRAFT').first()
        if locked_reference:
            raise ConflictError('承認済み計画が参照する就労情報はこの画面から変更できません。')
        before = {key:getattr(employer,column) for key,column in mapping.items()}
        before.update(employment_start_date=placement.placement_date,employment_type=placement.employment_status)
        for key,column in mapping.items():
            if key in data:
                value = text_value(data[key])
                if key == 'employer_name' and not value:
                    raise ValidationError('雇用事業主を入力してください。')
                limit = EmployerMaster.__table__.c[column].type.length
                if value and len(value) > limit:
                    raise ValidationError('就労先の入力が長すぎます。')
                setattr(employer,column,value)
        if 'employment_start_date' in data:
            proposed = parse_date(data['employment_start_date'])
            # Eligibility is already an established contract fact. Do not rewrite it here.
            if proposed != placement.placement_date:
                raise ValidationError('契約開始の根拠となる就職日はこの画面から変更できません。')
        if 'employment_type' in data:
            value = text_value(data['employment_type'])
            if value and len(value) > 50:
                raise ValidationError('雇用形態は50文字以内で指定してください。')
            placement.employment_status = value
        cls.audit(plan,actor_id,'UPDATE_RETENTION_EMPLOYMENT',before,data,'共通就労情報の編集',**context)

    @classmethod
    @transaction
    def evaluate(cls, plan_id, actor_id, data, **context):
        plan = cls.get_plan(plan_id, actor_id, 'EDIT', edit=True, evaluation=True)
        detail = cls.get_detail(plan, data.get('version'))
        if not detail:
            raise ValidationError('評価対象の計画詳細がありません。')
        if set(data) - {'version','evaluation_date','overall_evaluation','items','goals','assessor_type_id'}:
            raise ValidationError('評価項目のみ入力してください。')
        evaluated_on = parse_date(data.get('evaluation_date'))
        from backend.app.utils.timezone import get_jst_today
        if not plan.plan_start_date <= evaluated_on <= min(plan.plan_end_date, get_jst_today()):
            raise ValidationError('評価日は計画期間内かつ本日以前に指定してください。')
        if not isinstance(data.get('items',[]), list) or not isinstance(data.get('goals',[]), list):
            raise ValidationError()
        before = dict(overall_evaluation=detail.overall_evaluation,
            items=[cls.item_dict(i) for i in detail.support_items if not i.deleted_at])
        seen = set()
        for patch in data.get('items',[]):
            if not isinstance(patch,dict) or set(patch)-set(EVALUATION_FIELDS)-{'id'}:
                raise ValidationError()
            if type(patch.get('id')) is not int:
                raise ValidationError('評価対象を指定してください。')
            item = db.session.get(JobRetentionPlanSupportItem, patch.get('id'))
            if not item or item.plan_detail_id != detail.id or item.deleted_at or item.id in seen:
                raise ValidationError('評価対象の支援項目を確認してください。')
            seen.add(item.id)
            for key in EVALUATION_FIELDS:
                if key not in patch:
                    continue
                value = text_value(patch[key])
                if key.endswith('_status') and value is not None:
                    allowed = ACHIEVEMENT if key == 'achievement_status' else ('DONE','PARTIAL','NOT_DONE')
                    if value not in allowed:
                        raise ValidationError('評価区分を確認してください。')
                setattr(item,key,value)
        allowed_goals = {('LONG',lt.id) for lt in plan.long_term_goals} | {('SHORT',st.id) for lt in plan.long_term_goals for st in lt.short_term_goals}
        for patch in data.get('goals',[]):
            if not isinstance(patch,dict) or set(patch)-{'goal_type','goal_id','achievement_status'} or 'achievement_status' not in patch:
                raise ValidationError()
            if type(patch.get('goal_id')) is not int or not isinstance(patch.get('goal_type'),str):
                raise ValidationError('目標を指定してください。')
            if (patch.get('goal_type'),patch.get('goal_id')) not in allowed_goals or patch.get('achievement_status') not in (None,) + ACHIEVEMENT:
                raise ValidationError('目標と達成度を確認してください。')
            assessor = db.session.get(AssessorType,data.get('assessor_type_id')) if type(data.get('assessor_type_id')) is int else None
            if not data.get('assessor_type_id'):
                assessor = AssessorType.query.filter_by(name='支援員').first()
                if not assessor:
                    try:
                        with db.session.begin_nested():
                            assessor = AssessorType(name='支援員')
                            db.session.add(assessor)
                            db.session.flush()
                    except IntegrityError:
                        assessor = AssessorType.query.filter_by(name='支援員').one()
            if not assessor:
                raise ValidationError('評価主体を選択してください。')
            db.session.add(GoalAssessment(assessor_type_id=assessor.id, supporter_id=actor_id,
                goal_type=patch['goal_type'], goal_id=patch['goal_id'], assessment_date=evaluated_on,
                achievement_status=patch['achievement_status']))
        if 'overall_evaluation' in data:
            detail.overall_evaluation = text_value(data['overall_evaluation'])
        detail.evaluation_date = evaluated_on
        detail.evaluation_author_id = actor_id
        detail.version += 1
        db.session.flush()
        cls.audit(plan,actor_id,'EVALUATE_RETENTION_PLAN',before,data,'定着支援計画の評価',**context)
        return cls.read(plan.id,actor_id)

    @classmethod
    def validate_approval(cls, plan, actor_id):
        if not cls.is_retention(plan):
            return
        plan = cls.get_plan(plan.id,actor_id,'APPROVE',edit=True)
        detail = plan.retention_detail
        if not detail or not detail.job_placement or detail.job_placement.user_id != plan.user_id:
            raise ValidationError('定着支援計画の就職記録を入力してください。')
        placement = JobPlacementLog.query.filter_by(id=detail.job_placement_id).with_for_update().populate_existing().one()
        EmployerMaster.query.filter_by(id=placement.employer_id).with_for_update().populate_existing().one()
        if not detail.job_placement.employer.company_name.strip() or not detail.job_placement.placement_date or not detail.user_needs or not detail.job_description:
            raise ValidationError('勤務先・就職日・本人ニーズ・業務内容を入力してください。')
        if not plan.long_term_goals or any(not lt.description.strip() or not lt.challenges or not lt.challenges.strip()
                or not lt.short_term_goals or any(not st.description.strip() for st in lt.short_term_goals) for lt in plan.long_term_goals):
            raise ValidationError('長期目標・課題・短期目標を入力してください。')
        if not any(not item.deleted_at for item in detail.support_items):
            raise ValidationError('支援項目を1件以上入力してください。')
        cls.validate_items_period(plan,plan.plan_start_date,plan.plan_end_date)
