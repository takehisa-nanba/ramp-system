"""Explicitly authorized local development upgrade and additive demo seed.

Run only while the local application is stopped. Backup/credentials stay outside Git.
"""
import json
import logging
import os
from pathlib import Path
import secrets
import subprocess
import sys
from datetime import date, datetime
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
STORE = Path(os.environ['LOCALAPPDATA']) / 'RAMP' / 'retention-development'


def main():
    if '--apply-development' not in sys.argv:
        raise RuntimeError('Explicit --apply-development required')
    logging.disable(logging.CRITICAL)
    from backend.config import Config
    from backend.app import create_app
    from backend.app.extensions import db
    from sqlalchemy.engine import make_url
    from sqlalchemy import text
    from flask_migrate import upgrade
    from backend.tests.validate_retention_plan_postgres import snapshot
    from backend.app.models import (User, UserPII, Supporter, SupporterPII, PermissionMaster,
        RoleMaster, StatusMaster, MunicipalityMaster, ServiceTypeMaster, OfficeSetting,
        OfficeServiceConfiguration, EmployerMaster, JobPlacementLog, ServiceCertificate,
        GrantedService, SupportPlan, JobTitleMaster, SupporterJobAssignment,
        JobRetentionPlanDetail, JobRetentionPlanSupportItem, AuditActionLog)
    from backend.app.services.job_retention_service import JobRetentionService
    url = make_url(Config.SQLALCHEMY_DATABASE_URI)
    assert url.get_backend_name() == 'postgresql' and url.host in ('localhost', '127.0.0.1')
    assert not url.database.startswith('ramp_retention_demo_')
    assert STORE.is_dir() and not (STORE / 'state.json').exists()
    app = create_app(Config)
    with app.app_context():
        assert db.session.execute(text('SELECT version_num FROM alembic_version')).scalar() == 'c731retentioncore'
        assert not Supporter.query.filter_by(staff_code='demo-staff').first()
        db.session.remove()
        before = snapshot(db.engine)
        pg_env = dict(os.environ, PGHOST=url.host, PGPORT=str(url.port or 5432),
                      PGDATABASE=url.database, PGUSER=url.username, PGPASSWORD=url.password or '')
        bin_dir = Path('C:/Program Files/PostgreSQL/17/bin')
        backup = STORE / ('before-phase2-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.dump')
        result = subprocess.run([str(bin_dir/'pg_dump.exe'), '-Fc', '-f', str(backup)],
                                env=pg_env, capture_output=True)
        assert result.returncode == 0 and backup.stat().st_size > 0, 'backup failed'
        result = subprocess.run([str(bin_dir/'pg_restore.exe'), '--list', str(backup)], capture_output=True)
        assert result.returncode == 0, 'backup TOC verification failed'
        print('Backup created and archive list verified.')
        upgrade(directory=str(ROOT/'backend/migrations'), revision='d842retentionplan')
        after = snapshot(db.engine)
        for table, rows in before.items():
            cols = list(rows[0]) if rows else []
            assert sorted(rows, key=repr) == sorted([{k:r[k] for k in cols} for r in after[table]], key=repr), table
        print('Migration c731retentioncore -> d842retentionplan; all existing column values preserved.')

        def get_or_add(model, keys, **extra):
            obj = model.query.filter_by(**keys).first()
            if obj is None:
                obj = model(**keys, **extra); db.session.add(obj); db.session.flush()
            return obj
        office = OfficeSetting.query.filter_by(is_active=True).order_by(OfficeSetting.id).first()
        assert office is not None
        municipality = db.session.get(MunicipalityMaster, office.municipality_id)
        assert municipality is not None
        status = get_or_add(StatusMaster, dict(name='利用中'))
        service = get_or_add(ServiceTypeMaster, dict(service_code='RETENTION'), name='就労定着支援')
        permissions = [get_or_add(PermissionMaster, dict(name=n)) for n in
                       ['VIEW','CREATE','EDIT','APPROVE','DELETE','VIEW_PII','EDIT_PII']]
        role = RoleMaster(name='定着支援デモ職員', role_scope='JOB', permissions=permissions)
        config = OfficeServiceConfiguration(office_id=office.id, service_type_master_id=service.id,
            jigyosho_bango='9999999988', capacity=10, initial_designation_date=date(2020,1,1),
            designation_expiry_date=date(2030,1,1))
        user = User(display_name='定着デモ利用者', status_id=status.id)
        staff = Supporter(staff_code='demo-staff', last_name='デモ',first_name='支援員',
            last_name_kana='デモ',first_name_kana='シエンイン', office_id=office.id,
            employment_type='FULL_TIME',weekly_scheduled_minutes=2400,hire_date=date(2020,1,1),roles=[role])
        employer = EmployerMaster(company_name='デモ事務サービス株式会社')
        db.session.add_all([config,user,staff,employer]); db.session.flush()
        old_state = Path(os.environ['LOCALAPPDATA'])/'RAMP/retention-demo/state.json'
        password = json.loads(old_state.read_text(encoding='utf-8'))['password'] if old_state.exists() else secrets.token_urlsafe(18)
        pii = SupporterPII(supporter_id=staff.id,email='demo@example.invalid'); pii.set_password(password)
        db.session.add(pii)
        db.session.add(UserPII(user_id=user.id,last_name='デモ',first_name='太郎',last_name_kana='デモ',
                              first_name_kana='タロウ',birth_date=date(1995,4,1)))
        placement = JobPlacementLog(user_id=user.id,employer_id=employer.id,
            placement_date=date(2026,3,31),support_scenario='NEW_PLACEMENT')
        cert = ServiceCertificate(user_id=user.id,office_service_configuration_id=config.id,
            municipality_master_id=municipality.id,certificate_issue_date=date(2026,1,1),status='ACTIVE')
        db.session.add_all([placement,cert]); db.session.flush()
        db.session.add(GrantedService(certificate_id=cert.id,service_type_master_id=service.id,
            granted_start_date=date(2026,1,1),granted_end_date=date(2027,12,31)))
        title = get_or_add(JobTitleMaster,dict(title_name='サービス管理責任者'),is_qualified_role=True)
        db.session.add(SupporterJobAssignment(supporter_id=staff.id,job_title_id=title.id,
            office_service_configuration_id=config.id,start_date=date(2020,1,1),assigned_minutes=2400))
        # Domain validations and audit are retained for contract creation.
        contract = JobRetentionService.start_retention_support(user.id,config.id,date(2026,9,30),
            date(2027,9,29),staff.id,'開発環境の合成デモデータを追加')
        plan = SupportPlan(user_id=user.id,office_service_configuration_id=config.id,plan_status='DRAFT',
            plan_start_date=date(2026,9,30),plan_end_date=date(2026,12,31))
        db.session.add(plan); db.session.flush()
        detail = JobRetentionPlanDetail(support_plan_id=plan.id,job_placement_id=placement.id,
            created_by_id=staff.id,version=1,user_needs='安心して長く働きたい',job_description='書類整理とデータ入力')
        db.session.add(detail); db.session.flush()
        db.session.add(JobRetentionPlanSupportItem(plan_detail_id=detail.id,sequence_no=1,
            support_policy_content='月1回の面談で業務と体調を確認する',frequency='月1回',
            start_date=plan.plan_start_date,end_date=plan.plan_end_date))
        db.session.add(AuditActionLog(actor_supporter_id=staff.id,user_id=user.id,action='CREATE',
            entity_type='SupportPlan',entity_id=plan.id,reason='開発環境デモ初期データ追加'))
        db.session.commit()
        state = dict(user_id=user.id,staff_id=staff.id,plan_id=plan.id,config_id=config.id,password=password)
        (STORE/'state.json').write_text(json.dumps(state),encoding='utf-8')
        (STORE/'ログイン情報.txt').write_text('URL: http://localhost:5173\n職員コード: demo-staff\nパスワード: '+password+'\n',encoding='utf-8')
        final = snapshot(db.engine)
        for table,rows in before.items():
            cols = list(rows[0]) if rows else []
            original = Counter(repr(r) for r in rows)
            current = Counter(repr({k:r[k] for k in cols}) for r in final[table])
            assert not original-current, table
        print('Synthetic demo added; all pre-existing rows/values preserved.')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        import traceback
        print('Stopped: '+type(exc).__name__)
        for frame in traceback.extract_tb(exc.__traceback__):
            print(Path(frame.filename).name+':'+str(frame.lineno))
        sys.exit(1)
