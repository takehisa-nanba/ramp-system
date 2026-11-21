"""Local synthetic demo only. Never upgrades the configured application database."""
import argparse
import json
import logging
import os
from pathlib import Path
import secrets
import sys
import uuid
from datetime import date

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
STATE_DIR = Path(os.environ['LOCALAPPDATA']) / 'RAMP' / 'retention-demo'
STATE = STATE_DIR / 'state.json'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--setup', action='store_true')
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    from backend.config import Config
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import make_url
    from backend.app import create_app
    from backend.app.extensions import db
    source = make_url(Config.SQLALCHEMY_DATABASE_URI)
    assert source.get_backend_name() == 'postgresql'
    if args.setup:
        if STATE.exists():
            raise RuntimeError('Demo already configured; refusing to overwrite')
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        state = dict(database='ramp_retention_demo_' + uuid.uuid4().hex,
                     password=secrets.token_urlsafe(18), jwt_key=secrets.token_urlsafe(48))
    else:
        state = json.loads(STATE.read_text(encoding='utf-8'))
    import re
    assert re.fullmatch(r'ramp_retention_demo_[0-9a-f]{32}', state['database'])
    assert state['database'] != source.database
    target = source.set(database=state['database'])

    class DemoConfig(Config):
        SQLALCHEMY_DATABASE_URI = target.render_as_string(hide_password=False)
        SQLALCHEMY_ENGINE_OPTIONS = {'hide_parameters': True}
        JWT_SECRET_KEY = state['jwt_key']
        JWT_ACCESS_COOKIE_NAME = 'ramp_demo_access'
        JWT_ACCESS_CSRF_COOKIE_NAME = 'csrf_access_token'
        JWT_COOKIE_SECURE = False
        CORS_ORIGINS = ['http://localhost:5178']
        DEBUG = False
        TESTING = False

    if args.setup:
        admin = create_engine(source.set(database='postgres'), isolation_level='AUTOCOMMIT')
        with admin.connect() as connection:
            connection.execute(text('CREATE DATABASE ' + state['database']))
        # Save recovery/connection selector immediately; never store source URL.
        STATE.write_text(json.dumps(state), encoding='utf-8')
        admin.dispose()
    app = create_app(DemoConfig)
    if args.setup:
        from flask_migrate import upgrade
        from backend.tests.validate_retention_plan_postgres import seed
        from backend.app.models import (User, UserPII, Supporter, SupporterPII, PermissionMaster,
            SupportPlan, JobTitleMaster, SupporterJobAssignment, EmployerMaster)
        from backend.app.services.job_retention_plan_service import JobRetentionPlanService
        with app.app_context():
            upgrade(directory=str(ROOT / 'backend/migrations'), revision='head')
            plan_id, staff_id, placement_id = seed()
            plan = db.session.get(SupportPlan, plan_id)
            user = db.session.get(User, plan.user_id)
            user.display_name = '定着デモ利用者'
            db.session.add(UserPII(user_id=user.id, last_name='デモ', first_name='太郎',
                last_name_kana='デモ', first_name_kana='タロウ', birth_date=date(1995,4,1)))
            staff = db.session.get(Supporter, staff_id)
            staff.staff_code = 'demo-staff'
            staff.last_name = 'デモ'; staff.first_name = '支援員'
            pii = SupporterPII(supporter_id=staff_id, email='demo@example.invalid')
            pii.set_password(state['password']); db.session.add(pii)
            for name in ['VIEW_PII', 'EDIT_PII']:
                staff.roles[0].permissions.append(PermissionMaster(name=name))
            title = JobTitleMaster(title_name='サービス管理責任者', is_qualified_role=True)
            db.session.add(title); db.session.flush()
            db.session.add(SupporterJobAssignment(supporter_id=staff_id, job_title_id=title.id,
                office_service_configuration_id=plan.office_service_configuration_id,
                start_date=date(2020,1,1), assigned_minutes=2400))
            db.session.get(EmployerMaster, 1).company_name = 'デモ事務サービス株式会社'
            db.session.commit()
            detail = JobRetentionPlanService.save_detail(plan_id, staff_id, dict(version=0,
                job_placement_id=placement_id, user_needs='安心して長く働きたい',
                job_description='書類整理とデータ入力'))
            JobRetentionPlanService.save_item(plan_id, staff_id, dict(version=detail['version'],
                support_policy_content='月1回の面談で業務と体調を確認する', frequency='月1回',
                start_date='2026-09-30', end_date='2026-12-31'))
            state.update(user_id=user.id, plan_id=plan_id,
                         config_id=plan.office_service_configuration_id)
            STATE.write_text(json.dumps(state), encoding='utf-8')
            client = app.test_client()
            response = client.post('/api/auth/login', json=dict(login_id='demo-staff',
                password=state['password'], user_type='staff'))
            assert response.status_code == 200
            for path in ['/api/users', f'/api/users/{user.id}/pii', '/api/job-retention/users',
                         f'/api/plans/{plan_id}/retention-detail']:
                assert client.get(path).status_code == 200, path
        (STATE_DIR / 'ログイン情報.txt').write_text(
            '職員コード: demo-staff\nパスワード: ' + state['password'] +
            '\nURL: http://localhost:5178\n専用ダミーDBのみ使用\n', encoding='utf-8')
        print('Demo setup and login/API checks passed.')
    else:
        with app.app_context():
            assert db.session.execute(text('SELECT version_num FROM alembic_version')).scalar() == 'd842retentionplan'
        app.run(host='127.0.0.1', port=5001, debug=False, use_reloader=False)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # Do not expose URLs, SQL parameters, passwords or synthetic profile values.
        print('Demo failed: ' + type(exc).__name__, file=sys.stderr)
        sys.exit(1)
