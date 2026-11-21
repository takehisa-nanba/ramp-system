from datetime import date, datetime
import pytest
from flask_jwt_extended import create_access_token
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from backend.tests.test_retention_core_phase1 import retention, start
from backend.app.extensions import db
from backend.app.models import (SupportPlan, JobRetentionPlanDetail, JobRetentionPlanSupportItem,
    PermissionMaster, LongTermGoal, ShortTermGoal, GoalAssessment, AssessorType, AuditActionLog,
    JobRetentionContract, JobTitleMaster, SupporterJobAssignment, CaseConferenceLog)
from backend.app.services.job_retention_plan_service import JobRetentionPlanService as Service
from backend.app.services.support_plan_service import SupportPlanService
from backend.app.services.job_retention_service import JobRetentionService
from backend.app.utils.errors import AppError


@pytest.fixture
def plan_setup(retention):
    app,user,staff,config,*_ = retention
    app.config['JWT_SECRET_KEY']='phase2-isolated-test-signing-key-not-for-application-use'
    start(retention)
    staff.roles[0].permissions.extend([PermissionMaster(name=p) for p in ('APPROVE','DELETE','VIEW_PII','EDIT_PII')])
    plan = SupportPlan(user_id=user.id,office_service_configuration_id=config.id,
        plan_status='DRAFT',plan_start_date=date(2026,9,30),plan_end_date=date(2026,12,31))
    db.session.add(plan);db.session.flush()
    lt=LongTermGoal(plan_id=plan.id,description='安定就労',challenges='相談のタイミング',target_period_start=plan.plan_start_date,target_period_end=plan.plan_end_date)
    db.session.add(lt);db.session.flush()
    db.session.add(ShortTermGoal(long_term_goal_id=lt.id,description='相談する'))
    title=JobTitleMaster(title_name='サービス管理責任者',is_qualified_role=True)
    db.session.add(title);db.session.flush()
    db.session.add(SupporterJobAssignment(supporter_id=staff.id,job_title_id=title.id,office_service_configuration_id=config.id,start_date=date(2020,1,1),assigned_minutes=2400))
    db.session.add(AssessorType(name='支援員'))
    db.session.commit()
    return retention,plan


def detail_payload(retention,version=0):
    return dict(version=version,job_placement_id=retention[6].id,user_needs='働き続けたい',job_description='書類整理')


def prepare(plan_setup):
    r,plan=plan_setup
    result=Service.save_detail(plan.id,r[2].id,detail_payload(r))
    result=Service.save_item(plan.id,r[2].id,dict(version=result['version'],support_policy_content='月次面談',frequency='月1回',start_date='2026-09-30',end_date='2026-12-31'))
    return result


def test_detail_items_and_null_evaluation(plan_setup):
    r,plan=plan_setup
    result=prepare(plan_setup)
    assert len(result['detail']['support_items'])==1
    assert result['detail']['evaluation_date'] is None
    assert result['detail']['support_items'][0]['achievement_status'] is None
    for index in range(2,6):
        result=Service.save_item(plan.id,r[2].id,dict(version=result['version'],sequence_no=index,support_policy_content='企業面談',frequency='月1回',start_date='2026-09-30',end_date='2026-12-31'))
    assert [i['sequence_no'] for i in result['detail']['support_items']]==[1,2,3,4,5]
    with pytest.raises(IntegrityError):
        db.session.add(JobRetentionPlanDetail(support_plan_id=plan.id,created_by_id=r[2].id));db.session.commit()
    db.session.rollback()
    assert JobRetentionPlanDetail.query.count()==1


@pytest.mark.parametrize('start_date,end_date',[('2026-09-29','2026-10-01'),('2026-10-01','2027-01-01'),('2026-10-02','2026-10-01'),('bad','2026-10-01')])
def test_item_period_rejected(plan_setup,start_date,end_date):
    r,plan=plan_setup
    result=prepare(plan_setup)
    with pytest.raises(AppError):
        Service.save_item(plan.id,r[2].id,dict(version=result['version'],support_policy_content='面談',frequency='月1回',start_date=start_date,end_date=end_date))
    assert JobRetentionPlanSupportItem.query.count()==1


@pytest.mark.parametrize('failure',['non_retention','other_office','no_view','no_create','finished','deleted_contract','ARCHIVED','PENDING_CONSENT','ACTIVE'])
def test_write_guards(plan_setup,failure):
    r,plan=plan_setup
    if failure=='non_retention': plan.office_service_configuration_id=None
    elif failure=='other_office': r[2].office_id=None
    elif failure in ('no_view','no_create'):
        r[2].roles[0].permissions=[p for p in r[2].roles[0].permissions if p.name != ('VIEW' if failure=='no_view' else 'CREATE')]
    elif failure=='finished': JobRetentionContract.query.one().status='FINISHED'
    elif failure=='deleted_contract': JobRetentionContract.query.one().deleted_at=datetime(2026,10,1)
    else: plan.plan_status=failure
    db.session.commit()
    with pytest.raises(AppError): Service.save_detail(plan.id,r[2].id,detail_payload(r))
    assert JobRetentionPlanDetail.query.count()==0


def test_version_conflict_and_audit_rollback(plan_setup,monkeypatch):
    r,plan=plan_setup
    result=prepare(plan_setup)
    with pytest.raises(AppError): Service.save_detail(plan.id,r[2].id,detail_payload(r,0))
    count=AuditActionLog.query.count()
    def fail(*args,**kwargs): raise RuntimeError('audit unavailable')
    monkeypatch.setattr(Service,'audit',fail)
    with pytest.raises(RuntimeError): Service.save_detail(plan.id,r[2].id,dict(version=result['version'],user_needs='変更'))
    assert JobRetentionPlanDetail.query.one().user_needs=='働き続けたい'
    assert JobRetentionPlanDetail.query.one().version==result['version']
    assert AuditActionLog.query.count()==count


def test_evaluation_and_content_freeze(plan_setup):
    r,plan=plan_setup
    result=prepare(plan_setup)
    plan.plan_status='ACTIVE';db.session.commit()
    with pytest.raises(AppError): Service.save_detail(plan.id,r[2].id,dict(version=result['version'],user_needs='変更'))
    goal=plan.long_term_goals[0]
    result=Service.evaluate(plan.id,r[2].id,dict(version=result['version'],evaluation_date='2026-10-01',overall_evaluation='継続',
        assessor_type_id=AssessorType.query.one().id,goals=[dict(goal_type='LONG',goal_id=goal.id,achievement_status='PARTIAL')],
        items=[dict(id=result['detail']['support_items'][0]['id'],implementation_status='DONE',achievement_status='PARTIAL',effect_satisfaction_notes='満足',remaining_issues_and_actions='継続相談')]))
    assert GoalAssessment.query.one().achievement_status=='PARTIAL'
    assert result['detail']['evaluation_author_id']==r[2].id
    assert result['detail']['support_items'][0]['implementation_status']=='DONE'
    assert plan.plan_end_date==date(2026,12,31)
    JobRetentionService.finish_retention_support(JobRetentionContract.query.one().id,date(2026,10,1),r[2].id,'支援終了')
    with pytest.raises(AppError): Service.evaluate(plan.id,r[2].id,dict(version=result['version'],evaluation_date='2026-10-01'))


def test_approval_required_and_existing_guards(plan_setup):
    r,plan=plan_setup
    client=r[0].test_client();headers={'Authorization':'Bearer '+create_access_token(identity=f'staff:{r[2].id}')}
    url=f'/api/plans/{plan.id}/approve'
    assert client.post(url,headers=headers).status_code==400 # existing meeting requirement
    db.session.add(CaseConferenceLog(initiator_supporter_id=r[2].id,user_id=r[1].id,support_plan_id=plan.id,
        conference_type='PERSON_CENTERED_MEETING',user_participated=True,concern_summary='相談',agreed_action='支援継続'))
    db.session.commit()
    assert client.post(url,headers=headers).status_code==400 # detail absent
    result=prepare(plan_setup)
    from backend.app.models import PlanAssessment
    db.session.add(PlanAssessment(plan_id=plan.id, user_id=plan.user_id, supporter_id=r[2].id,
        office_service_configuration_id=r[3].id, interview_date=plan.plan_start_date, method="IN_PERSON", summary="本人面談"))
    db.session.commit()
    assert client.post(url,headers=headers).status_code==200
    assert db.session.get(SupportPlan,plan.id).plan_status=='PENDING_CONSENT'
    assert client.put(f'/api/plans/{plan.id}/retention-detail',headers=headers,json={'version':result['version'],'user_needs':'変更'}).status_code==409


@pytest.mark.parametrize('field',['user_needs','job_description'])
def test_approval_missing_fields(plan_setup,field):
    r,plan=plan_setup
    result=prepare(plan_setup)
    Service.save_detail(plan.id,r[2].id,dict(version=result['version'],**{field:' '}))
    with pytest.raises(AppError): SupportPlanService().log_support_conference_and_approve(plan.id,r[2].id,datetime(2026,10,1),'会議',True)
    db.session.rollback()
    assert plan.plan_status=='DRAFT'


def test_pii_permissions_ciphertext_and_audit(plan_setup):
    r,plan=plan_setup
    result=prepare(plan_setup)
    result=Service.save_detail(plan.id,r[2].id,dict(version=result['version'],health_status_notes='PRIVATE_TEST_HEALTH'))
    ciphertext=db.session.execute(text('SELECT health_status_notes FROM job_retention_plan_details')).scalar()
    assert ciphertext and 'PRIVATE_TEST_HEALTH' not in ciphertext
    assert result['detail']['health_status_notes']=='PRIVATE_TEST_HEALTH'
    assert all('PRIVATE_TEST_HEALTH' not in (a.after_value or '') for a in AuditActionLog.query.all())
    r[2].roles[0].permissions=[p for p in r[2].roles[0].permissions if p.name not in ('VIEW_PII','EDIT_PII')];db.session.commit()
    assert 'health_status_notes' not in Service.read(plan.id,r[2].id)['detail']
    with pytest.raises(AppError): Service.save_detail(plan.id,r[2].id,dict(version=result['version'],health_status_notes='変更'))


def test_item_soft_delete_and_plan_shrink(plan_setup):
    r,plan=plan_setup
    result=prepare(plan_setup)
    with pytest.raises(AppError): SupportPlanService().set_plan_period(plan,end_date='2026-10-01')
    db.session.rollback()
    item_id=result['detail']['support_items'][0]['id']
    result=Service.save_item(plan.id,r[2].id,dict(version=result['version'],reason='本人の希望により内容を見直します'),item_id=item_id,delete=True)
    assert result['detail']['support_items']==[]
    assert db.session.get(JobRetentionPlanSupportItem,item_id).deleted_at is not None


def test_api_identity_and_cross_plan_item(plan_setup):
    r,plan=plan_setup
    result=prepare(plan_setup)
    client=r[0].test_client();url=f'/api/plans/{plan.id}/retention-detail'
    assert client.get(url).status_code==401
    assert client.get(url,headers={'Authorization':'Bearer '+create_access_token(identity=f'user:{r[1].id}')}).status_code==403
    other=SupportPlan(user_id=r[1].id,office_service_configuration_id=r[3].id,plan_status='DRAFT',plan_start_date=plan.plan_start_date,plan_end_date=plan.plan_end_date)
    db.session.add(other);db.session.commit()
    second=Service.save_detail(other.id,r[2].id,detail_payload(r))
    with pytest.raises(AppError): Service.save_item(other.id,r[2].id,dict(version=second['version'],frequency='毎週'),item_id=result['detail']['support_items'][0]['id'])


@pytest.mark.parametrize('failure',['no_short_goal','no_items','no_challenges','no_approve_permission'])
def test_approval_other_requirements(plan_setup,failure):
    r,plan=plan_setup
    prepare(plan_setup)
    if failure=='no_short_goal': plan.long_term_goals[0].short_term_goals=[]
    elif failure=='no_items': JobRetentionPlanSupportItem.query.one().deleted_at=datetime(2026,10,1)
    elif failure=='no_challenges': plan.long_term_goals[0].challenges=' '
    else: r[2].roles[0].permissions=[p for p in r[2].roles[0].permissions if p.name!='APPROVE']
    db.session.commit()
    with pytest.raises(AppError): SupportPlanService().log_support_conference_and_approve(plan.id,r[2].id,datetime(2026,10,1),'会議',True)
    db.session.rollback()
    assert plan.plan_status=='DRAFT'


def test_shared_employment_update_is_atomic_and_signed_reference_frozen(plan_setup):
    r,plan=plan_setup
    result=prepare(plan_setup)
    result=Service.save_detail(plan.id,r[2].id,dict(version=result['version'],job_description='更新',employment={'employer_name':'更新企業','employment_type':'契約社員・嘱託'}))
    assert r[6].employer.company_name=='更新企業'
    assert r[6].employment_status=='契約社員・嘱託'
    other=SupportPlan(user_id=plan.user_id,office_service_configuration_id=r[3].id,plan_status='ARCHIVED',plan_start_date=plan.plan_start_date,plan_end_date=plan.plan_end_date)
    db.session.add(other);db.session.flush()
    db.session.add(JobRetentionPlanDetail(support_plan_id=other.id,created_by_id=r[2].id,job_placement_id=r[6].id))
    db.session.commit()
    with pytest.raises(AppError): Service.save_detail(plan.id,r[2].id,dict(version=result['version'],job_description='保存禁止',employment={'employer_name':'改変'}))
    assert r[6].employer.company_name=='更新企業'
    assert plan.retention_detail.job_description=='更新'


def test_evaluation_rollback_and_draft_denied(plan_setup,monkeypatch):
    r,plan=plan_setup
    result=prepare(plan_setup)
    payload=dict(version=result['version'],evaluation_date='2026-10-01',overall_evaluation='評価',items=[dict(id=result['detail']['support_items'][0]['id'],implementation_status='DONE')])
    with pytest.raises(AppError): Service.evaluate(plan.id,r[2].id,payload)
    plan.plan_status='ACTIVE';db.session.commit()
    def fail(*args,**kwargs): db.session.flush();raise RuntimeError('audit unavailable')
    monkeypatch.setattr(Service,'audit',fail)
    with pytest.raises(RuntimeError): Service.evaluate(plan.id,r[2].id,payload)
    assert plan.retention_detail.overall_evaluation is None
    assert plan.retention_detail.support_items[0].implementation_status is None


@pytest.mark.parametrize('kind',['EDIT','DELETE','EDIT_PII'])
def test_specific_permissions_required(plan_setup,kind):
    r,plan=plan_setup
    result=prepare(plan_setup)
    r[2].roles[0].permissions=[p for p in r[2].roles[0].permissions if p.name!=kind];db.session.commit()
    with pytest.raises(AppError):
        if kind=='DELETE': Service.save_item(plan.id,r[2].id,dict(version=result['version'],reason='本人の希望により内容を見直します'),item_id=result['detail']['support_items'][0]['id'],delete=True)
        else: Service.save_detail(plan.id,r[2].id,dict(version=result['version'],**({'health_status_notes':'秘匿'} if kind=='EDIT_PII' else {'job_description':'変更'})))


def test_legacy_detail_absent_is_readable(plan_setup):
    r,plan=plan_setup
    plan.plan_status='ACTIVE';db.session.commit()
    result=Service.read(plan.id,r[2].id)
    assert result['detail'] is None
    assert not result['permissions']['evaluate']


def test_encryption_failure_rejects_write(plan_setup,monkeypatch):
    from backend.config import Config
    r,plan=plan_setup
    result=prepare(plan_setup)
    monkeypatch.setattr(Config,'PII_ENCRYPTION_KEY',None)
    with pytest.raises(Exception): Service.save_detail(plan.id,r[2].id,dict(version=result['version'],health_status_notes='PRIVATE_TEST_HEALTH'))
    assert plan.retention_detail.health_status_notes is None
    assert plan.retention_detail.version==result['version']


def test_organization_references_reused_and_user_boundary(plan_setup):
    from backend.app.models import Organization,UserOrganizationLink,User
    r,plan=plan_setup
    organization=Organization(organization_name='支援機関',organization_type='CONSULTATION_OFFICE')
    other=User(display_name='other',status_id=r[1].status_id)
    db.session.add_all([organization,other]);db.session.flush()
    own_link=UserOrganizationLink(user_id=r[1].id,organization_id=organization.id,link_start_date=date(2026,9,30))
    other_link=UserOrganizationLink(user_id=other.id,organization_id=organization.id,link_start_date=date(2026,9,30))
    db.session.add_all([own_link,other_link]);db.session.commit()
    result=Service.save_detail(plan.id,r[2].id,dict(detail_payload(r),organization_link_ids=[own_link.id]))
    assert result['related_support_organizations']==[{'id':own_link.id,'name':'支援機関'}]
    with pytest.raises(AppError): Service.save_detail(plan.id,r[2].id,dict(version=result['version'],organization_link_ids=[other_link.id]))
    assert plan.retention_detail.organization_links==[own_link]
    assert Organization.query.count()==1
