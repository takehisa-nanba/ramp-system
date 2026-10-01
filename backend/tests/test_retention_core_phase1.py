from datetime import date, timedelta
import pytest
from flask import Flask
from flask_jwt_extended import create_access_token
from backend.app import create_app
from backend.app.extensions import db
from backend.config import Config
from backend.app.models import (User, StatusMaster, Corporation, MunicipalityMaster, OfficeSetting,
    OfficeServiceConfiguration, ServiceTypeMaster, Supporter, RoleMaster, PermissionMaster,
    ServiceCertificate, GrantedService, EmployerMaster, JobPlacementLog, JobRetentionContract,
    AuditActionLog, SupportRecord, SupportPlan, HolisticSupportPolicy)
from backend.app.services.job_retention_service import JobRetentionService, valid_retention_designation
from backend.app.domain.employment.retention_eligibility import retention_eligible_date, is_retention_eligible
from backend.app.utils.errors import AppError


@pytest.fixture
def retention(monkeypatch):
    class TestConfig(Config):
        TESTING = True
        SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    app = create_app(TestConfig)
    monkeypatch.setattr('backend.app.services.job_retention_service.get_jst_today', lambda: date(2026, 10, 1))
    with app.app_context():
        db.create_all()
        status = StatusMaster(name='利用中')
        corp = Corporation(corporation_name='test', corporation_type='test')
        muni = MunicipalityMaster(name='test', municipality_code='123456')
        service = ServiceTypeMaster(name='定着', service_code='RETENTION')
        role = RoleMaster(name='staff', role_scope='JOB', permissions=[PermissionMaster(name=p) for p in ['VIEW', 'CREATE', 'EDIT']])
        db.session.add_all([status, corp, muni, service, role]); db.session.flush()
        office = OfficeSetting(corporation_id=corp.id, municipality_id=muni.id, office_name='office')
        db.session.add(office); db.session.flush()
        config = OfficeServiceConfiguration(office_id=office.id, service_type_master_id=service.id,
            jigyosho_bango='1234567890', capacity=10, initial_designation_date=date(2020,1,1), designation_expiry_date=date(2030,1,1))
        user = User(display_name='匿名A', status_id=status.id)
        staff = Supporter(staff_code='S1', last_name='a', first_name='b', last_name_kana='a', first_name_kana='b',
            employment_type='FULL_TIME', weekly_scheduled_minutes=2400, hire_date=date(2020,1,1), office_id=office.id, roles=[role])
        employer = EmployerMaster(company_name='test')
        db.session.add_all([config, user, staff, employer]); db.session.flush()
        cert = ServiceCertificate(user_id=user.id, office_service_configuration_id=config.id, municipality_master_id=muni.id,
            certificate_issue_date=date(2026,1,1), status='ACTIVE')
        placement = JobPlacementLog(user_id=user.id, employer_id=employer.id, placement_date=date(2026,3,31), support_scenario='NEW_PLACEMENT')
        db.session.add_all([cert, placement]); db.session.flush()
        grant = GrantedService(certificate_id=cert.id, service_type_master_id=service.id, granted_start_date=date(2026,1,1), granted_end_date=date(2027,12,31))
        db.session.add(grant); db.session.commit()
        yield app, user, staff, config, cert, grant, placement
        db.session.remove(); db.drop_all()


def start(retention):
    _, user, staff, config, *_ = retention
    return JobRetentionService.start_retention_support(user.id, config.id, date(2026,9,30), date(2027,9,29), staff.id, '本人の利用希望による開始')


@pytest.mark.parametrize('placed,expected', [(date(2026,8,31), date(2027,2,28)), (date(2023,8,31),date(2024,2,29)), (date(2026,3,31),date(2026,9,30))])
def test_calendar_boundary(placed,expected):
    assert retention_eligible_date(placed) == expected
    assert not is_retention_eligible(placed, on_date=expected-timedelta(days=1))
    assert is_retention_eligible(placed, on_date=expected)
    assert not is_retention_eligible(placed, expected, expected)


def test_start_finish_and_duplicate(retention):
    contract = start(retention)
    contract_id = contract.id
    assert contract.status == 'ACTIVE'
    assert AuditActionLog.query.count() == 1
    with pytest.raises(AppError): start(retention)
    assert JobRetentionContract.query.count() == 1
    assert AuditActionLog.query.count() == 1
    JobRetentionService.finish_retention_support(contract_id,date(2026,10,1),retention[2].id,'支援終了')
    assert contract.status == 'FINISHED'
    assert AuditActionLog.query.count() == 2
    with pytest.raises(AppError):
        JobRetentionService.finish_retention_support(contract_id,date(2026,10,1),retention[2].id,'再終了')


@pytest.mark.parametrize('failure', ['inactive', 'missing_start', 'expired', 'wrong_service', 'draft', 'void', 'tentative', 'grant_expired', 'early', 'separated', 'no_permission', 'other_office', 'deleted_user'])
def test_fail_closed(retention, failure):
    _, user, staff, config, cert, grant, placement = retention
    if failure == 'inactive': config.office.is_active = False
    elif failure == 'missing_start': config.initial_designation_date = None
    elif failure == 'expired': config.designation_expiry_date = date(2026,9,29)
    elif failure == 'wrong_service': db.session.get(ServiceTypeMaster,config.service_type_master_id).service_code = 'TRANSITION'
    elif failure == 'draft': cert.status = 'DRAFT'
    elif failure == 'void': cert.voided_at = date(2026,1,1)
    elif failure == 'tentative': grant.is_tentative = True
    elif failure == 'grant_expired': grant.granted_end_date = date(2026,9,29)
    elif failure == 'early': placement.placement_date = date(2026,4,1)
    elif failure == 'separated': placement.separation_date = date(2026,9,30)
    elif failure == 'no_permission': staff.roles = []
    elif failure == 'other_office': staff.office_id = None
    elif failure == 'deleted_user': user.deleted_at = date(2026,1,1)
    db.session.commit()
    with pytest.raises(AppError): start(retention)
    assert JobRetentionContract.query.count() == 0
    assert AuditActionLog.query.count() == 0


def test_audit_failure_rolls_back(retention, monkeypatch):
    def fail(*args): raise RuntimeError('audit unavailable')
    monkeypatch.setattr(JobRetentionService,'audit',fail)
    with pytest.raises(RuntimeError): start(retention)
    assert JobRetentionContract.query.count() == 0


def test_api_and_shared_records(retention):
    app,user,staff,config,*_ = retention
    client = app.test_client()
    assert client.get('/api/job-retention/users').status_code == 401
    headers={'Authorization': 'Bearer '+create_access_token(identity=f'staff:{staff.id}')}
    contract = start(retention)
    response = client.get('/api/job-retention/users',headers=headers)
    assert response.status_code == 200
    assert response.json['items'][0]['user_id'] == user.id
    response = client.post('/api/records',headers=headers,json={'user_id':user.id,
        'office_service_configuration_id':config.id,'log_date':'2026-09-30',
        'support_content':'企業面談','support_duration_seconds':0})
    assert response.status_code == 201
    assert SupportRecord.query.one().office_service_configuration_id == config.id
    user_headers={'Authorization':'Bearer '+create_access_token(identity=f'user:{user.id}')}
    assert client.get(f'/api/job-retention/contracts/{contract.id}',headers=user_headers).status_code == 403
    assert client.post(f'/api/job-retention/users/{user.id}/start',headers=headers,json={'office_service_configuration_id':config.id,'contract_start_date':'bad'}).status_code == 400
    staff.office_id = None; db.session.commit()
    assert client.get('/api/job-retention/users',headers=headers).json['items'] == []
    assert client.get(f'/api/job-retention/contracts/{contract.id}',headers=headers).status_code == 404


def test_plan_history_scoped(retention):
    from backend.app.services.support_plan_service import SupportPlanService
    _,user,staff,config,*_ = retention
    policy=HolisticSupportPolicy(user_id=user.id,effective_date=date(2026,1,1), user_intention_content='希望',support_policy_content='方針')
    db.session.add(policy);db.session.flush()
    old=SupportPlan(user_id=user.id,plan_status='ACTIVE',plan_start_date=date(2025,1,1),plan_end_date=date(2025,12,31))
    db.session.add(old);db.session.commit()
    start(retention)
    plan=SupportPlanService().create_plan_draft(user.id,staff.id,policy.id,config.id)
    assert plan.office_service_configuration_id == config.id
    assert plan.plan_start_date == date(2026,9,30)
    assert old.plan_status == 'ACTIVE'

def test_legacy_migration_preserves_history():
    import importlib.util
    from pathlib import Path
    import sqlalchemy as sa
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    path=Path(__file__).parents[1]/'migrations/versions/c731retentioncore_integrate_retention_core.py'
    spec=importlib.util.spec_from_file_location('retention_migration',path)
    migration=importlib.util.module_from_spec(spec);spec.loader.exec_module(migration)
    engine=sa.create_engine('sqlite:///:memory:')
    with engine.begin() as conn:
        for table in ('office_service_configurations','supporters','support_plans','support_records'):
            conn.execute(sa.text(f'CREATE TABLE {table} (id INTEGER PRIMARY KEY)'))
        conn.execute(sa.text('CREATE TABLE job_retention_contracts (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, contract_start_date DATE NOT NULL, contract_end_date DATE NOT NULL, contract_details TEXT)'))
        conn.execute(sa.text("INSERT INTO job_retention_contracts VALUES (1, 1, '2025-01-01', '2027-12-31', 'historical evidence')"))
        with Operations.context(MigrationContext.configure(conn)):
            migration.upgrade()
        row=conn.execute(sa.text('SELECT * FROM job_retention_contracts')).mappings().one()
        assert row['contract_details']=='historical evidence'
        assert row['contract_start_date']=='2025-01-01'
        assert row['office_service_configuration_id'] is None
        assert row['status']=='LEGACY_REVIEW'
        assert row['created_at'] is not None
        assert 'uq_retention_active_user' in {i['name'] for i in sa.inspect(conn).get_indexes('job_retention_contracts')}


def test_plan_activation_does_not_archive_transition(retention):
    from backend.app.models import DocumentConsentLog
    from backend.app.services.support_plan_service import SupportPlanService
    _,user,staff,config,*_ = retention
    transition=SupportPlan(user_id=user.id,plan_status='ACTIVE')
    retention_plan=SupportPlan(user_id=user.id,plan_status='PENDING_CONSENT',office_service_configuration_id=config.id)
    db.session.add_all([transition,retention_plan]);db.session.flush()
    consent=DocumentConsentLog(user_id=user.id,document_type='SUPPORT_PLAN',document_id=retention_plan.id,consent_proof='DIGITAL_SIGNATURE')
    db.session.add(consent);db.session.flush()
    SupportPlanService().finalize_and_activate_plan(retention_plan.id,consent.id)
    assert transition.plan_status=='ACTIVE'
    assert retention_plan.plan_status=='ACTIVE'


def test_api_lifecycle(retention):
    app,user,staff,config,*_=retention
    client=app.test_client()
    headers={'Authorization':'Bearer '+create_access_token(identity=f'staff:{staff.id}')}
    response=client.post(f'/api/job-retention/users/{user.id}/start',headers=headers,json={
        'office_service_configuration_id':config.id,'contract_start_date':'2026-09-30',
        'contract_end_date':'2027-09-29','reason':'利用開始'})
    assert response.status_code==201
    contract_id=response.json['id']
    assert client.get(f'/api/job-retention/users/{user.id}',headers=headers).json['items'][0]['id']==contract_id
    response=client.post(f'/api/job-retention/contracts/{contract_id}/finish',headers=headers,json={
        'contract_end_date':'2026-10-01','reason':'利用終了'})
    assert response.status_code==200
    assert response.json['status']=='FINISHED'
    assert client.get('/api/job-retention/users',headers=headers).json['items']==[]

@pytest.mark.parametrize('method', ['POST', 'PUT'])
@pytest.mark.parametrize('dates,accepted', [
    ({'plan_start_date': '2026-09-29'}, False),
    ({'plan_end_date': '2027-09-30'}, False),
    ({'plan_start_date': '2027-02-01', 'plan_end_date': '2027-01-01'}, False),
    ({'plan_start_date': '2026-09-30', 'plan_end_date': '2027-09-29'}, True),
])
def test_plan_api_contract_period(retention, method, dates, accepted):
    app, user, staff, config, *_ = retention
    start(retention)
    headers = {'Authorization': 'Bearer ' + create_access_token(identity=f'staff:{staff.id}')}
    payload = {'user_id': user.id, 'office_service_configuration_id': config.id, **dates}
    if method == 'POST':
        response = app.test_client().post('/api/plans/', headers=headers, json=payload)
        assert response.status_code == (201 if accepted else 400)
        assert SupportPlan.query.count() == (1 if accepted else 0)
        assert HolisticSupportPolicy.query.count() == (1 if accepted else 0)
    else:
        plan = SupportPlan(user_id=user.id, office_service_configuration_id=config.id,
                           plan_status='DRAFT', plan_start_date=date(2026,9,30), plan_end_date=date(2026,12,29))
        db.session.add(plan); db.session.commit()
        plan_id = plan.id
        response = app.test_client().put(f'/api/plans/{plan_id}', headers=headers, json=payload)
        assert response.status_code == (200 if accepted else 400)
        db.session.expire_all()
        saved = db.session.get(SupportPlan, plan_id)
        assert saved.plan_start_date == date(2026,9,30)
        assert saved.plan_end_date == (date(2027,9,29) if accepted else date(2026,12,29))
    if not accepted:
        assert response.json['error']['code'] == 'VALIDATION_ERROR'


def test_service_plan_period_guard_and_clone(retention):
    from backend.app.services.support_plan_service import SupportPlanService
    app, user, staff, config, *_ = retention
    contract = start(retention)
    policy = HolisticSupportPolicy(user_id=user.id, effective_date=date(2026,9,30),
                                   user_intention_content='希望', support_policy_content='方針')
    db.session.add(policy); db.session.commit()
    service = SupportPlanService()
    with pytest.raises(AppError):
        service.create_plan_draft(user.id, staff.id, policy.id, config.id,
                                  requested_start_date=date(2026,9,29))
    assert SupportPlan.query.count() == 0
    plan = service.create_plan_draft(user.id, staff.id, policy.id, config.id)
    db.session.commit()
    original_end = plan.plan_end_date
    with pytest.raises(AppError):
        service.set_plan_period(plan, end_date=contract.contract_end_date + timedelta(days=1))
    assert plan.plan_end_date == original_end
    plan.plan_end_date = contract.contract_end_date
    plan.plan_status = 'ACTIVE'
    db.session.commit()
    headers = {'Authorization': 'Bearer ' + create_access_token(identity=f'staff:{staff.id}')}
    response = app.test_client().post(f'/api/plans/{plan.id}/create-next-draft', headers=headers, json={})
    assert response.status_code == 400
    assert SupportPlan.query.count() == 1


@pytest.mark.parametrize('status,start_date,end_date,log_date,accepted', [
    ('DRAFT', date(2026,10,1), date(2026,10,31), '2026-10-15', False),
    ('ARCHIVED', date(2026,10,1), date(2026,10,31), '2026-10-15', False),
    ('PENDING_CONSENT', date(2026,10,1), date(2026,10,31), '2026-10-15', False),
    ('ACTIVE', date(2026,10,1), date(2026,10,31), '2026-09-30', False),
    ('ACTIVE', date(2026,10,1), date(2026,10,31), '2026-11-01', False),
    ('ACTIVE', None, date(2026,10,31), '2026-10-15', False),
    ('ACTIVE', date(2026,10,1), None, '2026-10-15', False),
    ('ACTIVE', date(2026,10,1), date(2026,10,31), '2026-10-01', True),
    ('ACTIVE', date(2026,10,1), date(2026,10,31), '2026-10-31', True),
])
def test_support_record_plan_state_and_period(retention, status, start_date, end_date, log_date, accepted):
    app, user, staff, config, *_ = retention
    start(retention)
    plan = SupportPlan(user_id=user.id, office_service_configuration_id=config.id,
                       plan_status=status, plan_start_date=start_date, plan_end_date=end_date)
    db.session.add(plan); db.session.commit()
    headers = {'Authorization': 'Bearer ' + create_access_token(identity=f'staff:{staff.id}')}
    response = app.test_client().post('/api/records', headers=headers, json={
        'user_id': user.id, 'office_service_configuration_id': config.id,
        'support_plan_id': plan.id, 'log_date': log_date,
        'support_content': '面談', 'support_duration_seconds': 0})
    assert response.status_code == (201 if accepted else 400)
    assert SupportRecord.query.count() == (1 if accepted else 0)


def test_plan_history_api_keeps_service_boundary(retention):
    app, user, staff, config, *_ = retention
    transition = ServiceTypeMaster(name='移行', service_code='TRANSITION')
    db.session.add(transition); db.session.flush()
    other_config = OfficeServiceConfiguration(office_id=config.office_id,
        service_type_master_id=transition.id, jigyosho_bango='9876543210', capacity=10)
    db.session.add(other_config); db.session.flush()
    plans = []
    for config_id in (None, config.id, other_config.id):
        for status in ('ACTIVE', 'ARCHIVED', 'DRAFT', 'PENDING_CONSENT', 'PENDING_CONFERENCE'):
            plan = SupportPlan(user_id=user.id, office_service_configuration_id=config_id, plan_status=status)
            db.session.add(plan); plans.append(plan)
    db.session.commit()
    headers = {'Authorization': 'Bearer ' + create_access_token(identity=f'staff:{staff.id}')}
    for config_id in (None, config.id, other_config.id):
        suffix = f'?office_service_configuration_id={config_id}' if config_id else ''
        result = app.test_client().get(f'/api/users/{user.id}/support-plans{suffix}', headers=headers)
        assert result.status_code == 200
        assert result.json['active_plan']['office_service_configuration_id'] == config_id
        assert {p['id'] for p in result.json['plan_history']} == {
            p.id for p in plans if p.office_service_configuration_id == config_id and p.plan_status != 'ACTIVE'}


@pytest.mark.parametrize('separation,expected', [
    (None, 'EMPLOYED'), (date(2026,10,2), 'EMPLOYED'),
    (date(2026,10,1), 'NOT_EMPLOYED'), (date(2026,9,30), 'NOT_EMPLOYED'),
])
def test_employment_separation_date_matches_domain(retention, monkeypatch, separation, expected):
    from backend.app.services.employment_service import EmploymentService
    _, user, _, _, _, _, placement = retention
    today = date(2026,10,1)
    monkeypatch.setattr('backend.app.services.employment_service.get_jst_today', lambda: today)
    placement.separation_date = separation
    db.session.commit()
    result = EmploymentService().check_retention_status(user.id)
    assert result['status'] == expected
    assert result['milestone_reached'] == is_retention_eligible(placement.placement_date, separation, today)
