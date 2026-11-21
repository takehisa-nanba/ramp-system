"""Phase 2 validation: ordinary Alembic upgrades in disposable databases only.

python -B backend/tests/validate_retention_plan_postgres.py --env-file .env
Connection values, SQL exception parameters and record bodies are never printed.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import date
import json
import logging
import os
from pathlib import Path
import sys
import threading
import time
from unittest.mock import patch
import uuid
from dotenv import dotenv_values
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))


def seed():
    from backend.app.extensions import db
    from backend.app.models import (StatusMaster,Corporation,MunicipalityMaster,ServiceTypeMaster,
        RoleMaster,PermissionMaster,OfficeSetting,OfficeServiceConfiguration,User,Supporter,
        EmployerMaster,JobPlacementLog,JobRetentionContract,SupportPlan,ServiceCertificate,GrantedService)
    status=StatusMaster(name='test');corp=Corporation(corporation_name='test',corporation_type='test')
    muni=MunicipalityMaster(name='test',municipality_code='999999')
    service=ServiceTypeMaster(name='retention',service_code='RETENTION')
    role=RoleMaster(name='test',role_scope='JOB',permissions=[PermissionMaster(name=p) for p in ['VIEW','CREATE','EDIT','APPROVE','DELETE']])
    db.session.add_all([status,corp,muni,service,role]);db.session.flush()
    office=OfficeSetting(corporation_id=corp.id,municipality_id=muni.id,office_name='test')
    db.session.add(office);db.session.flush()
    config=OfficeServiceConfiguration(office_id=office.id,service_type_master_id=service.id,jigyosho_bango='9999999999',capacity=10,
        initial_designation_date=date(2020,1,1),designation_expiry_date=date(2030,1,1))
    user=User(display_name='test',status_id=status.id)
    staff=Supporter(staff_code='TEST',last_name='test',first_name='test',last_name_kana='test',first_name_kana='test',
        employment_type='FULL_TIME',weekly_scheduled_minutes=2400,hire_date=date(2020,1,1),office_id=office.id,roles=[role])
    employer=EmployerMaster(company_name='test')
    db.session.add_all([config,user,staff,employer]);db.session.flush()
    placement=JobPlacementLog(user_id=user.id,employer_id=employer.id,placement_date=date(2026,3,31),support_scenario='NEW_PLACEMENT')
    contract=JobRetentionContract(user_id=user.id,office_service_configuration_id=config.id,status='ACTIVE',
        contract_start_date=date(2026,9,30),contract_end_date=date(2027,9,29))
    plan=SupportPlan(user_id=user.id,office_service_configuration_id=config.id,plan_status='DRAFT',
        plan_start_date=date(2026,9,30),plan_end_date=date(2026,12,31))
    db.session.add_all([placement,contract,plan]);db.session.commit()
    cert=ServiceCertificate(user_id=user.id,office_service_configuration_id=config.id,municipality_master_id=muni.id,
        certificate_issue_date=date(2026,1,1),status='ACTIVE')
    db.session.add(cert);db.session.flush()
    db.session.add(GrantedService(certificate_id=cert.id,service_type_master_id=service.id,
        granted_start_date=date(2026,1,1),granted_end_date=date(2027,12,31)))
    db.session.commit()
    return plan.id,staff.id,placement.id


def snapshot(engine):
    """Exact values remain in memory; never serialize them to disk/logs."""
    result={}
    with engine.connect() as conn:
        for table in inspect(conn).get_table_names(schema='public'):
            if table=='alembic_version': continue
            quoted=conn.dialect.identifier_preparer.quote(table)
            result[table]=[dict(row) for row in conn.execute(text('SELECT * FROM '+quoted)).mappings()]
    return result


def exercise(app,engine,ids):
    from backend.app.extensions import db
    from backend.app.models import JobRetentionPlanDetail,JobRetentionPlanSupportItem,AuditActionLog
    from backend.app.services.job_retention_plan_service import JobRetentionPlanService as Service
    plan_id,staff_id,placement_id=ids
    results=[]
    with app.app_context():
        initial=Service.save_detail(plan_id,staff_id,dict(version=0,job_placement_id=placement_id,user_needs='initial',job_description='test'))
        detail_id=initial['detail']['id']
        checks=[
            "INSERT INTO job_retention_plan_details(support_plan_id,created_by_id,version) VALUES (:plan,:staff,1)",
            "INSERT INTO job_retention_plan_details(support_plan_id,created_by_id,version) VALUES (999999,:staff,1)",
            "INSERT INTO job_retention_plan_support_items(plan_detail_id,sequence_no,support_policy_content,start_date,end_date,frequency) VALUES (:detail,1,'test','2026-12-31','2026-09-30','test')",
            "INSERT INTO job_retention_plan_support_items(plan_detail_id,sequence_no,support_policy_content,start_date,end_date,frequency,achievement_status) VALUES (:detail,1,'test','2026-09-30','2026-12-31','test','BAD')",
        ]
        for sql in checks:
            try:
                db.session.execute(text(sql),dict(plan=plan_id,staff=staff_id,detail=detail_id));db.session.commit()
            except IntegrityError:
                db.session.rollback()
            else:
                raise AssertionError('expected DB constraint rejection')
        results.append('postgres_fk_unique_period_status_constraints')
        def fail(*args,**kwargs):
            db.session.flush()
            raise RuntimeError('injected audit failure')
        with patch.object(Service,'audit',side_effect=fail):
            try: Service.save_detail(plan_id,staff_id,dict(version=1,user_needs='rollback'))
            except RuntimeError: db.session.rollback()
            else: raise AssertionError('audit injection failed')
        assert db.session.get(JobRetentionPlanDetail,detail_id).user_needs=='initial'
        assert db.session.get(JobRetentionPlanDetail,detail_id).version==1
        results.append('detail_audit_failure_rollback')

    held=threading.Event();release=threading.Event();entered=threading.Event()
    leader_thread=[];follower_pid=[]
    original_audit=Service.audit
    def delayed_audit(*args,**kwargs):
        original_audit(*args,**kwargs)
        if threading.get_ident()==leader_thread[0]:
            db.session.flush();held.set()
            assert release.wait(10)
    def update(leader):
        with app.app_context():
            if leader: leader_thread.append(threading.get_ident())
            else:
                follower_pid.append(db.session.execute(text('SELECT pg_backend_pid()')).scalar());entered.set()
            try:
                Service.save_detail(plan_id,staff_id,dict(version=1,user_needs='winner' if leader else 'stale'))
                return 'OK'
            except Exception as exc:
                db.session.rollback();return type(exc).__name__
    with patch.object(Service,'audit',side_effect=delayed_audit),ThreadPoolExecutor(max_workers=2) as pool:
        first=pool.submit(update,True)
        try:
            assert held.wait(5)
            second=pool.submit(update,False)
            assert entered.wait(5)
            deadline=time.monotonic()+5
            blocked=False
            while time.monotonic()<deadline:
                with engine.connect() as conn:
                    blocked=bool(conn.execute(text('SELECT cardinality(pg_blocking_pids(:pid))>0'),dict(pid=follower_pid[0])).scalar())
                if blocked: break
                time.sleep(.02)
            assert blocked
        finally:
            release.set()
        assert first.result(timeout=10)=='OK'
        assert second.result(timeout=10)=='ConflictError'
    with app.app_context():
        assert db.session.get(JobRetentionPlanDetail,detail_id).user_needs=='winner'
        assert db.session.get(JobRetentionPlanDetail,detail_id).version==2
        assert AuditActionLog.query.filter_by(action='SAVE_RETENTION_PLAN_DETAIL').count()==2
    results.append('concurrent_update_lock_wait_and_stale_version_rejected')
    with app.app_context():
        from flask_jwt_extended import create_access_token
        from backend.app.models import SupportPlan,JobTitleMaster,SupporterJobAssignment
        plan=db.session.get(SupportPlan,plan_id)
        user_id=plan.user_id;config_id=plan.office_service_configuration_id
        from backend.app.models import PlanAssessment
        db.session.add(PlanAssessment(user_id=user_id, plan_id=plan_id, supporter_id=staff_id,
            office_service_configuration_id=config_id, interview_date=date(2026,9,30),
            method="IN_PERSON", summary="test"))
        title=JobTitleMaster(title_name='サービス管理責任者',is_qualified_role=True)
        db.session.add(title);db.session.flush()
        db.session.add(SupporterJobAssignment(supporter_id=staff_id,job_title_id=title.id,
            office_service_configuration_id=config_id,start_date=date(2020,1,1),assigned_minutes=2400))
        db.session.commit()
        headers={'Authorization':'Bearer '+create_access_token(identity=f'staff:{staff_id}')}
    client=app.test_client()
    def call(method,path,payload,expected):
        response=getattr(client,method)(path,json=payload,headers=headers)
        assert response.status_code==expected, path
        return response.get_json()
    call('put',f'/api/plans/{plan_id}/goals',dict(long_term_goals=[dict(description='test',challenges='test',short_term_goals=[dict(description='test',individual_goals=[])])]),200)
    current=call('get',f'/api/plans/{plan_id}/retention-detail',None,200)
    current=call('post',f'/api/plans/{plan_id}/retention-support-items',dict(version=current['version'],support_policy_content='test',frequency='monthly',start_date='2026-09-30',end_date='2026-12-31'),201)
    call('post','/api/case-conferences',dict(user_id=user_id,support_plan_id=plan_id,conference_type='PERSON_CENTERED_MEETING',user_participated=True,
        concern_summary='test',agreed_action='test',participant_ids=[staff_id],conference_datetime='2026-10-01T10:00:00'),201)
    call('post',f'/api/plans/{plan_id}/approve',{},200)
    consent=call('post',f'/api/plans/{plan_id}/consent',dict(user_id=user_id,consent_proof='DIGITAL_SIGNATURE'),201)
    call('post',f'/api/plans/{plan_id}/activate',dict(consent_log_id=consent['consent_log_id']),200)
    current=call('post',f'/api/plans/{plan_id}/retention-evaluation',dict(version=current['version'],evaluation_date='2026-10-01',overall_evaluation='test',
        items=[dict(id=current['detail']['support_items'][0]['id'],implementation_status='DONE',achievement_status='PARTIAL')]),200)
    call('post','/api/records',dict(user_id=user_id,office_service_configuration_id=config_id,support_plan_id=plan_id,
        log_date='2026-10-01',support_content='test',support_duration_seconds=60),201)
    with app.app_context():
        from backend.app.models import JobRetentionContract
        contract_id=JobRetentionContract.query.filter_by(user_id=user_id).one().id
    call('post',f'/api/job-retention/contracts/{contract_id}/finish',dict(contract_end_date='2026-10-01',reason='test'),200)
    call('put',f'/api/plans/{plan_id}/retention-detail',dict(version=current['version'],user_needs='no'),400)
    results.append('postgres_api_detail_items_approve_consent_activate_evaluate_record_finish')
    return results


def run(env_file):
    values=dotenv_values(env_file)
    source=make_url(values['DATABASE_URL'])
    assert source.get_backend_name()=='postgresql'
    for key,value in values.items():
        if value is not None: os.environ[key]=value
    logging.disable(logging.CRITICAL)
    from backend.app import create_app
    from backend.app.extensions import db
    from backend.config import Config
    from flask_migrate import upgrade
    admin=create_engine(source.set(database='postgres'),isolation_level='AUTOCOMMIT')
    results=[]
    try:
        for mode in ('existing','empty'):
            name='ramp_phase2_validation_'+uuid.uuid4().hex
            target=source.set(database=name)
            assert target.database!=source.database and name.startswith('ramp_phase2_validation_')
            class ValidationConfig(Config):
                TESTING=True
                JWT_SECRET_KEY='phase2-isolated-test-signing-key-not-for-application-use'
                SQLALCHEMY_DATABASE_URI=target.render_as_string(hide_password=False)
                SQLALCHEMY_ENGINE_OPTIONS={'connect_args':{'options':'-c lock_timeout=12000 -c statement_timeout=15000'},'hide_parameters':True}
            app=None;created=False
            try:
                with admin.connect() as conn:
                    conn.execute(text('CREATE DATABASE '+name));created=True
                app=create_app(ValidationConfig)
                with app.app_context():
                    if mode=='existing':
                        upgrade(directory=str(ROOT/'backend/migrations'),revision='c731retentioncore')
                        assert db.session.execute(text('SELECT version_num FROM alembic_version')).scalar()=='c731retentioncore'
                        ids=seed()
                        before=snapshot(db.engine)
                    upgrade(directory=str(ROOT/'backend/migrations'),revision='head')
                    assert db.session.execute(text('SELECT version_num FROM alembic_version')).scalar()=='e927merge'
                    if mode=='existing':
                        after=snapshot(db.engine)
                        for table,rows in before.items():
                            columns=list(rows[0]) if rows else []
                            normalized=[{k:row[k] for k in columns} for row in after[table]]
                            assert sorted(rows,key=repr)==sorted(normalized,key=repr), table
                        results.append('c731_upgrade_preserves_all_existing_values')
                        # End the inspection transaction before threaded updates.
                        db.session.remove()
                        results.extend(exercise(app,db.engine,ids))
                    else:
                        results.append('empty_database_normal_alembic_upgrade_head')
            finally:
                if app:
                    with app.app_context(): db.session.remove();db.engine.dispose()
                if created:
                    with admin.connect() as conn:
                        conn.execute(text('DROP DATABASE '+name+' WITH (FORCE)'))
                        assert not conn.execute(text('SELECT 1 FROM pg_database WHERE datname=:name'),dict(name=name)).scalar()
                    results.append(mode+'_disposable_database_removed')
    finally:
        admin.dispose()
    return results


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--env-file',required=True)
    args=parser.parse_args()
    try:
        print(json.dumps({'passed':run(args.env_file)}))
    except Exception as exc:
        # Show code location only, never exception text containing SQL parameters.
        import traceback
        frames=traceback.extract_tb(exc.__traceback__)
        print(json.dumps({'failed':type(exc).__name__,
            'sqlstate':getattr(getattr(exc,'orig',None),'pgcode',None),
            'previous_error':type(exc.__context__).__name__ if exc.__context__ else None,
            'locations':[f'{Path(f.filename).name}:{f.lineno}' for f in frames]}))
        sys.exit(1)
