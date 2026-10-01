"""PostgreSQL race scenarios on a migrated disposable DB, preserving legacy rows."""
import uuid
import threading
import time
from datetime import date
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from sqlalchemy import text


def exercise(app, engine):
    results = []
    from backend.app import db
    from backend.app.models import (User, StatusMaster, Corporation, MunicipalityMaster, OfficeSetting,
        OfficeServiceConfiguration, ServiceTypeMaster, Supporter, RoleMaster, PermissionMaster,
        ServiceCertificate, GrantedService, EmployerMaster, JobPlacementLog, JobRetentionContract,
        AuditActionLog, SupportPlan, DocumentConsentLog)
    from backend.app.services.job_retention_service import JobRetentionService
    from backend.app.services.support_plan_service import SupportPlanService

    def setup():
        with app.app_context():
            suffix = uuid.uuid4().hex[:8]
            status = StatusMaster(name='validation-' + suffix)
            corp = Corporation(corporation_name='test', corporation_type='test')
            muni = MunicipalityMaster(name='test', municipality_code='V' + suffix[:5])
            service = ServiceTypeMaster.query.filter_by(service_code='RETENTION').first()
            if service is None: service = ServiceTypeMaster(name='Retention', service_code='RETENTION')
            role = RoleMaster(name='validation-' + suffix, role_scope='JOB', permissions=[PermissionMaster.query.filter_by(name=p).first() or PermissionMaster(name=p) for p in ['VIEW', 'CREATE', 'EDIT']])
            db.session.add_all([status, corp, muni, service, role]); db.session.flush()
            office = OfficeSetting(corporation_id=corp.id, municipality_id=muni.id, office_name='office')
            db.session.add(office); db.session.flush()
            config = OfficeServiceConfiguration(office_id=office.id, service_type_master_id=service.id,
                jigyosho_bango=str(int(suffix,16)).zfill(10), capacity=10, initial_designation_date=date(2020,1,1), designation_expiry_date=date(2030,1,1))
            user = User(display_name='test', status_id=status.id)
            staff = Supporter(staff_code='V' + suffix, last_name='a', first_name='b', last_name_kana='a', first_name_kana='b',
                employment_type='FULL_TIME', weekly_scheduled_minutes=2400, hire_date=date(2020,1,1), office_id=office.id, roles=[role])
            employer = EmployerMaster(company_name='test')
            db.session.add_all([config, user, staff, employer]); db.session.flush()
            cert = ServiceCertificate(user_id=user.id, office_service_configuration_id=config.id, municipality_master_id=muni.id,
                certificate_issue_date=date(2026,1,1), status='ACTIVE')
            placement = JobPlacementLog(user_id=user.id, employer_id=employer.id, placement_date=date(2026,3,31), support_scenario='NEW_PLACEMENT')
            db.session.add_all([cert, placement]); db.session.flush()
            db.session.add(GrantedService(certificate_id=cert.id, service_type_master_id=service.id,
                granted_start_date=date(2026,1,1), granted_end_date=date(2027,12,31)))
            db.session.commit()
            return user.id, staff.id, config.id

    ids = None
    def start():
        return JobRetentionService.start_retention_support(ids[0], ids[2], date(2026,9,30), date(2027,9,29), ids[1], 'test')

    def pending_plan():
        plan = SupportPlan(user_id=ids[0], office_service_configuration_id=ids[2], plan_status='PENDING_CONSENT',
            plan_start_date=date(2026,9,30), plan_end_date=date(2027,9,29))
        db.session.add(plan); db.session.flush()
        consent = DocumentConsentLog(user_id=ids[0], document_type='SUPPORT_PLAN', document_id=plan.id, consent_proof='DIGITAL_SIGNATURE')
        db.session.add(consent); db.session.commit()
        return plan.id, consent.id

    def race(first, second, hold_in_audit=False):
        held, release, entered = threading.Event(), threading.Event(), threading.Event()
        follower_pid = []
        leader_thread = []
        original_audit = JobRetentionService.audit
        def hold():
            held.set()
            assert release.wait(12), 'leader timeout'
        def audit(*args, **kwargs):
            original_audit(*args, **kwargs)
            if threading.get_ident() == leader_thread[0]:
                db.session.flush()
                hold()
        def worker(action, leader):
            with app.app_context():
                try:
                    pid = db.session.execute(text('SELECT pg_backend_pid()')).scalar()
                    if leader: leader_thread.append(threading.get_ident())
                    else: follower_pid.append(pid); entered.set()
                    action()
                    if leader and not hold_in_audit: hold()
                    db.session.commit()
                    return 'OK'
                except Exception as exc:
                    db.session.rollback()
                    return type(exc).__name__
        with patch.object(JobRetentionService, 'audit', side_effect=audit), ThreadPoolExecutor(max_workers=2) as pool:
            lead = pool.submit(worker, first, True)
            try:
                assert held.wait(8), 'leader did not reach lock point'
                follow = pool.submit(worker, second, False)
                assert entered.wait(3)
                blocked = False
                deadline = time.monotonic() + 6
                while time.monotonic() < deadline:
                    with engine.connect() as conn:
                        blocked = conn.execute(text('SELECT cardinality(pg_blocking_pids(:pid))>0'), {'pid': follower_pid[0]}).scalar()
                    if blocked: break
                    time.sleep(.05)
                assert blocked, 'PostgreSQL lock wait not observed'
            finally:
                release.set()
            return lead.result(timeout=10), follow.result(timeout=10)

    with patch('backend.app.services.job_retention_service.get_jst_today', return_value=date(2026,10,1)):
        ids = setup()
        assert race(start, start, True) == ('OK', 'ConflictError')
        with app.app_context():
            assert JobRetentionContract.query.filter_by(user_id=ids[0]).count() == 1
            assert AuditActionLog.query.filter_by(action='START_RETENTION_SUPPORT', user_id=ids[0]).count() == 1
        results.append('simultaneous_start_one_contract_one_audit')

        for finish_first in (True, False):
            ids = setup()
            with app.app_context():
                contract_id = start().id
                plan_id, consent_id = pending_plan()
            finish = lambda: JobRetentionService.finish_retention_support(contract_id,date(2026,10,1),ids[1],'test')
            activate = lambda: SupportPlanService().finalize_and_activate_plan(plan_id,consent_id)
            if finish_first:
                assert race(finish, activate, True) == ('OK','ValidationError')
            else:
                assert race(activate, finish) == ('OK','OK')
            with app.app_context():
                assert db.session.get(JobRetentionContract, contract_id).status == 'FINISHED'
                plan = db.session.get(SupportPlan,plan_id)
                assert plan.plan_status == ('PENDING_CONSENT' if finish_first else 'ARCHIVED')
                assert plan.plan_end_date == date(2027,9,29)
            results.append('finish_before_activate' if finish_first else 'activate_before_finish')

        ids = setup()
        def raw_insert():
            db.session.add(JobRetentionContract(user_id=ids[0],office_service_configuration_id=ids[2],
                contract_start_date=date(2026,9,30),contract_end_date=date(2027,9,29),status='ACTIVE'))
            db.session.flush()
        assert race(raw_insert,raw_insert) == ('OK','IntegrityError')
        with app.app_context(): assert JobRetentionContract.query.filter_by(user_id=ids[0]).count() == 1
        results.append('partial_unique_index_concurrent_conflict')

        ids = setup()
        with app.app_context():
            contract_id=start().id
            plan_id,consent_id=pending_plan()
            SupportPlanService().finalize_and_activate_plan(plan_id,consent_id);db.session.commit()
            audits=AuditActionLog.query.count()
            def fail(*args):
                db.session.flush()
                raise RuntimeError('injected')
            with patch.object(JobRetentionService,'audit',side_effect=fail):
                try: JobRetentionService.finish_retention_support(contract_id,date(2026,10,1),ids[1],'test')
                except RuntimeError: pass
                else: raise AssertionError('failure not injected')
            db.session.expire_all()
            assert db.session.get(JobRetentionContract,contract_id).status=='ACTIVE'
            assert db.session.get(JobRetentionContract,contract_id).contract_end_date==date(2027,9,29)
            assert db.session.get(SupportPlan,plan_id).plan_status=='ACTIVE'
            assert AuditActionLog.query.count()==audits
        results.append('finish_rollback_after_flush')

        ids = setup()
        with app.app_context():
            contract_id=start().id
            old_id,old_consent=pending_plan()
            SupportPlanService().finalize_and_activate_plan(old_id,old_consent);db.session.commit()
            new_id,new_consent=pending_plan()
            audits=AuditActionLog.query.count()
            original_add=db.session.add
            def fail_activation(entity,*args,**kwargs):
                if isinstance(entity,AuditActionLog) and entity.action=='ACTIVATE_SUPPORT_PLAN':
                    db.session.flush()
                    raise RuntimeError('injected')
                return original_add(entity,*args,**kwargs)
            with patch.object(db.session,'add',side_effect=fail_activation):
                try:
                    SupportPlanService().finalize_and_activate_plan(new_id,new_consent)
                    db.session.commit()
                except RuntimeError:
                    db.session.rollback()
                else: raise AssertionError('failure not injected')
            db.session.expire_all()
            assert db.session.get(SupportPlan,old_id).plan_status=='ACTIVE'
            assert db.session.get(SupportPlan,new_id).plan_status=='PENDING_CONSENT'
            assert db.session.get(SupportPlan,new_id).plan_end_date==date(2027,9,29)
            assert AuditActionLog.query.count()==audits
        results.append('activation_rollback_after_flush')
    from backend.tests.retention_migrated_api_scenarios import exercise_update_api
    with patch('backend.app.services.job_retention_service.get_jst_today', return_value=date(2026,10,1)):
        results.extend(exercise_update_api(app, setup()))
    return results
