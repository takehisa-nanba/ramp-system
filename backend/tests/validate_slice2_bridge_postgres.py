"""Restore a historical dump into a disposable DB and verify migration safety.
Only aggregate comparisons are written; row contents, IDs and credentials stay in memory.
"""
import argparse
import contextlib
import hashlib
import hmac
import io
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import uuid

from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from alembic.script import ScriptDirectory

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


from backend.tests.postgres_validation_snapshot import snapshot, compare


def run(args):
    logging.disable(logging.CRITICAL)
    values=dotenv_values(args.env_file)
    source=make_url(values['DATABASE_URL'])
    assert source.get_backend_name()=='postgresql'
    dump=Path(args.dump).resolve()
    assert dump.is_file() and not dump.is_relative_to(ROOT)
    report_path = Path(args.report).resolve()
    for artifact in (dump, report_path):
        assert not any((parent / '.git').exists() for parent in artifact.parents), 'Private artifacts must be outside Git checkouts'
    with dump.open('rb') as stream: backup_digest=hashlib.file_digest(stream,'sha256').digest()
    salt=os.urandom(32)
    target_name='ramp_slice2_validation_'+uuid.uuid4().hex
    target=source.set(database=target_name)
    assert source.database!=target.database
    admin=create_engine(source,isolation_level='AUTOCOMMIT')
    engine=create_engine(target)
    report={'source':'pre-reset slice2 backup','migration_target':'c731retentioncore','migration_success':False}
    created=False
    app=None
    source_engine=create_engine(source)
    try:source_before=snapshot(source_engine,salt)
    finally:source_engine.dispose()
    try:
        with admin.connect() as conn:
            conn.execute(text('CREATE DATABASE '+target_name));created=True
        env=os.environ.copy()
        for key,val in {'PGHOST':target.host,'PGPORT':str(target.port or 5432),'PGDATABASE':target.database,
                        'PGUSER':target.username,'PGPASSWORD':target.password,'PGCONNECT_TIMEOUT':'10'}.items():
            if val is not None:env[key]=val
        for key,value in target.query.items():
            if key in ('sslmode','sslrootcert','sslcert','sslkey'):env['PG'+key.upper()]=value
        restored=subprocess.run(['pg_restore','--no-owner','--no-privileges','--exit-on-error','--single-transaction',
                                 '--dbname',target_name,str(dump)],env=env,capture_output=True)
        assert restored.returncode==0, 'restore failed (details suppressed)'
        report['restore']='success'
        before=snapshot(engine,salt)
        report['restored_revision']=before['revision']
        script=ScriptDirectory(str(ROOT/'backend/migrations'))
        report['source_revisions_known_to_main']={}
        for revision in before['revision']:
            try:
                script.get_revision(revision)
                report['source_revisions_known_to_main'][revision]=True
            except Exception:
                report['source_revisions_known_to_main'][revision]=False
        for key,value in values.items():
            if value is not None:os.environ[key]=value
        from backend.app import create_app, db
        from backend.config import Config
        class ValidationConfig(Config):
            TESTING=True
            SQLALCHEMY_DATABASE_URI=target.render_as_string(hide_password=False)
            SQLALCHEMY_ENGINE_OPTIONS={'connect_args':{'options':'-c lock_timeout=10000 -c statement_timeout=30000'}}
        app=create_app(ValidationConfig)
        from backend.tests.slice2_bridge_checks import exercise_failures
        report['failure_checks']=exercise_failures(app,engine,before,salt)
        with app.app_context():
            assert db.engine.url.database==target_name
            from flask_migrate import upgrade
            try:
                with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
                    upgrade(directory=str(ROOT/'backend/migrations/slice2_compat'),revision='head')
                report['normal_upgrade']='success'
            except (Exception,SystemExit) as exc:
                report['normal_upgrade']={'result':'failed','exception_class':type(exc).__name__}
            finally:db.session.remove()
        assert report['normal_upgrade']=='success', 'bridge failed'
        with app.app_context():
            with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
                upgrade(directory=str(ROOT/'backend/migrations'),revision='head')
        after=snapshot(engine,salt)
        report['normal_upgrade_comparison']=compare(before,after)
        final=after
        # Report only schema metadata, never table contents or record identifiers.
        selected=('job_retention_contracts','support_plans','support_records')
        report['relevant_schema']={t:final['schema'][t] for t in selected}
        report['relevant_null_counts']={t:{'before':before['null_counts'][t],'after':final['null_counts'][t]} for t in selected}
        report['relevant_states']={t:{'before':before['states'][t],'after':final['states'][t]} for t in selected}
        report['api_checks_after_upgrade']={}
        with app.app_context():
            from flask_jwt_extended import create_access_token
            from backend.app.models import Supporter,User
            staff=Supporter.query.filter_by(is_active=True).first()
            user=User.query.first()
            if staff:
                token=create_access_token(identity=f'staff:{staff.id}')
                headers={'Authorization':'Bearer '+token}
                paths=[('/api/users','/api/users'),('/api/records','/api/records'),('/api/job-retention/users','/api/job-retention/users')]
                if user:
                    for suffix in ('support-plans','monitoring-reports','case-conferences'):
                        paths.append((f'/api/users/{{id}}/{suffix}',f'/api/users/{user.id}/{suffix}'))
                for label,url in paths:
                    db.session.rollback()
                    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
                        response=app.test_client().get(url,headers=headers)
                    report['api_checks_after_upgrade'][label]=response.status_code
            db.session.rollback()
        assert len(report['api_checks_after_upgrade'])==6 and all(v==200 for v in report['api_checks_after_upgrade'].values()), 'GET failed'
        comparison=report['normal_upgrade_comparison']
        assert comparison['revision_after']==['c731retentioncore']
        for table, change in comparison['tables'].items():
            if table=='alembic_version':
                assert change['before']==change['after']==1 and change['removed_keys']==change['added_keys']==1
                continue
            assert change['before']==change['after'] and change['removed_keys']==0, 'row loss'
            assert change['added_keys']==0 and not change['changed_columns'], 'unexpected data change'
        assert comparison['sequences_unchanged'] and comparison['enums_unchanged']
        assert comparison['fk_orphans_after']==0
        for table, cols in before['null_counts'].items():
            for column, count in cols.items():assert after['null_counts'][table][column]==count
        for table,cols in after['null_counts'].items():
            for column,count in cols.items():
                if column not in before['null_counts'][table]:assert count==after['tables'][table]['count']
        report['new_columns_all_null']=True
        report['allowed_differences_only']=True
        from backend.tests.retention_postgres_scenarios import exercise
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            report['concurrency_checks']=exercise(app,engine)
        post_scenarios=snapshot(engine,salt)
        # Added synthetic fixtures are allowed only after migration preservation checks.
        for table, state in before['tables'].items():
            if table=='alembic_version':continue
            for key, record in state['records'].items():
                assert key in post_scenarios['tables'][table]['records'], 'legacy record missing'
                for column,value in record.items():assert post_scenarios['tables'][table]['records'][key][column]==value, 'legacy value changed by tests'
        report['legacy_rows_unchanged_after_scenarios']=True
        report['migration_success']=True
    finally:
        if app:
            with app.app_context():db.session.remove();db.engine.dispose()
        engine.dispose()
        if created:
            with admin.connect() as conn:conn.execute(text('DROP DATABASE '+target_name+' WITH (FORCE)'))
        with admin.connect() as conn:
            report['validation_database_removed']=not conn.execute(text('SELECT EXISTS(SELECT 1 FROM pg_database WHERE datname=:n)'),{'n':target_name}).scalar()
        admin.dispose()
        source_engine=create_engine(source)
        try:
            snapshot_after_source=snapshot(source_engine,salt)
            report['development_db_comparison']=compare(source_before,snapshot_after_source)
        finally:source_engine.dispose()
        with dump.open('rb') as stream: report['backup_unchanged']=hashlib.file_digest(stream,'sha256').digest()==backup_digest
        Path(args.report).write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    from backend.tests.slice2_bridge_checks import assert_unchanged
    assert_unchanged(source_before,snapshot_after_source)
    assert report['backup_unchanged'] and report['validation_database_removed']
    print(json.dumps({'restore':report.get('restore'),'normal_upgrade':report.get('normal_upgrade'), 'concurrency_checks':report.get('concurrency_checks'),
        'failure_checks':report.get('failure_checks'),'validation_database_removed':report.get('validation_database_removed')},ensure_ascii=False))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for flag in ('env-file','dump','report'):p.add_argument('--'+flag,required=True)
    try:run(p.parse_args())
    except Exception as exc:
        import traceback
        for item in traceback.extract_tb(exc.__traceback__):
            if 'backend' in item.filename: print(Path(item.filename).name+':'+str(item.lineno))
        original=getattr(exc,'orig',None)
        if isinstance(exc,AssertionError): print(str(exc))
        print('SQLSTATE',getattr(original,'pgcode',None),'CONSTRAINT',getattr(getattr(original,'diag',None),'constraint_name',None))
        frame=traceback.extract_tb(exc.__traceback__)[-1]
        print('VALIDATION_RUN_FAILED:'+type(exc).__name__+' at '+Path(frame.filename).name+':'+str(frame.lineno))
        sys.exit(1)
