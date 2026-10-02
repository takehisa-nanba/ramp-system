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
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from alembic.script import ScriptDirectory
from alembic.migration import MigrationContext
from alembic.operations import Operations
import importlib.util

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def snapshot(engine, salt):
    result = {'tables': {}, 'revision': [], 'schema': {}, 'foreign_key_orphans': {}, 'null_counts': {}, 'states': {}}
    def digest(value):
        return hmac.new(salt, json.dumps(value, default=str, sort_keys=True).encode(), hashlib.sha256).hexdigest()
    with engine.connect() as conn:
        conn.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
        inspector = inspect(conn)
        quote = engine.dialect.identifier_preparer.quote
        for table in inspector.get_table_names(schema='public'):
            columns = inspector.get_columns(table, schema='public')
            pk = inspector.get_pk_constraint(table, schema='public')['constrained_columns']
            rows = conn.execute(text('SELECT * FROM public.' + quote(table))).mappings().all()
            by_key = {}
            for index, row in enumerate(rows):
                key = digest([row[c] for c in pk]) if pk else str(index)
                by_key[key] = {name: digest(value) for name, value in row.items()}
            result['tables'][table] = {'count': len(rows), 'records': by_key}
            result['null_counts'][table] = {c['name']:sum(row[c['name']] is None for row in rows) for c in columns}
            allowed_states = {'ACTIVE','FINISHED','LEGACY_REVIEW','DRAFT','ARCHIVED','ARCHIVED_DRAFT',
                              'PENDING_CONSENT','PENDING_CONFERENCE','APPROVED','REQUESTED','CANCELLED',
                              'REJECTED','PENDING','SIGNED','UNSIGNED','CONSENTED','PENDING_REVIEW','VOIDED'}
            result['states'][table] = {}
            for col in ('status','plan_status','approval_status','consent_status'):
                if col in result['null_counts'][table]:
                    counts = {}
                    for row in rows:
                        value = row[col]
                        category = 'NULL' if value is None else value if value in allowed_states else 'OTHER'
                        counts[category] = counts.get(category,0)+1
                    result['states'][table][col]=counts
            result['schema'][table] = {
                'columns': [{'name': c['name'], 'type': str(c['type']), 'nullable': c['nullable'], 'default': c['default']} for c in columns],
                'pk': inspector.get_pk_constraint(table, schema='public'),
                'fks': inspector.get_foreign_keys(table, schema='public'),
                'checks': inspector.get_check_constraints(table, schema='public'),
                'indexes': inspector.get_indexes(table, schema='public'),
                'unique': inspector.get_unique_constraints(table, schema='public')}
            for fk in result['schema'][table]['fks']:
                left = fk['constrained_columns']; right = fk['referred_columns']
                match = ' AND '.join('c.'+quote(a)+'=p.'+quote(b) for a,b in zip(left,right))
                present = ' AND '.join('c.'+quote(a)+' IS NOT NULL' for a in left)
                sql = ('SELECT count(*) FROM public.'+quote(table)+' c WHERE '+present+
                       ' AND NOT EXISTS (SELECT 1 FROM '+quote(fk['referred_schema'] or 'public')+'.'+quote(fk['referred_table'])+' p WHERE '+match+')')
                result['foreign_key_orphans'][table+'.'+str(fk['name'])] = conn.execute(text(sql)).scalar()
        result['sequences'] = {}
        for name in inspector.get_sequence_names(schema='public'):
            state = conn.execute(text('SELECT last_value, is_called FROM public.' + quote(name))).one()
            definition = conn.execute(text("SELECT data_type, start_value, min_value, max_value, increment_by, cycle, cache_size FROM pg_sequences WHERE schemaname='public' AND sequencename=:name"), {'name':name}).mappings().one()
            result['sequences'][name] = {'state':list(state), 'definition':dict(definition)}
        result['revision'] = conn.execute(text('SELECT version_num FROM alembic_version')).scalars().all()
        result['enums'] = inspector.get_enums(schema='public')
    return result


def compare(before, after):
    tables = {}
    for name in sorted(set(before['tables']) | set(after['tables'])):
        a = before['tables'].get(name, {'count':0, 'records':{}})
        b = after['tables'].get(name, {'count':0, 'records':{}})
        changed = set()
        for key in a['records'].keys() & b['records'].keys():
            for col in a['records'][key].keys() & b['records'][key].keys():
                if a['records'][key][col] != b['records'][key][col]: changed.add(col)
        tables[name] = {'before':a['count'], 'after':b['count'],
                        'removed_keys':len(a['records'].keys()-b['records'].keys()),
                        'added_keys':len(b['records'].keys()-a['records'].keys()),
                        'changed_columns':sorted(changed)}
    return {'revision_before':before['revision'], 'revision_after':after['revision'], 'tables':tables,
            'null_counts_unchanged':before['null_counts']==after['null_counts'],
            'status_counts_unchanged':before['states']==after['states'],
            'schema_unchanged':before['schema']==after['schema'], 'enums_unchanged':before['enums']==after['enums'], 'sequences_unchanged':before['sequences']==after['sequences'],
            'fk_orphans_before':sum(before['foreign_key_orphans'].values()),
            'fk_orphans_after':sum(after['foreign_key_orphans'].values()),
            'fk_orphan_counts_unchanged':before['foreign_key_orphans']==after['foreign_key_orphans']}


def run(args):
    logging.disable(logging.CRITICAL)
    values=dotenv_values(args.env_file)
    source=make_url(values['DATABASE_URL'])
    assert source.get_backend_name()=='postgresql'
    dump=Path(args.dump).resolve()
    assert dump.is_file() and not dump.is_relative_to(ROOT)
    salt=os.urandom(32)
    target_name='ramp_slice2_validation_'+uuid.uuid4().hex
    target=source.set(database=target_name)
    assert source.database!=target.database
    admin=create_engine(source,isolation_level='AUTOCOMMIT')
    engine=create_engine(target)
    report={'source':'pre-reset slice2 backup','migration_target':'c731retentioncore'}
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
        with app.app_context():
            assert db.engine.url.database==target_name
            from flask_migrate import upgrade
            try:
                with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
                    upgrade(directory=str(ROOT/'backend/migrations'),revision='c731retentioncore')
                report['normal_upgrade']='success'
            except (Exception,SystemExit) as exc:
                report['normal_upgrade']={'result':'failed','exception_class':type(exc).__name__}
            finally:db.session.remove()
        after=snapshot(engine,salt)
        report['normal_upgrade_comparison']=compare(before,after)
        # Diagnostic only: run the target revision transactionally, without changing
        # Alembic history, then unconditionally roll back. This is not a migration path.
        path=ROOT/'backend/migrations/versions/c731retentioncore_integrate_retention_core.py'
        spec=importlib.util.spec_from_file_location('phase1_probe',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with engine.connect() as conn:
            tx=conn.begin()
            try:
                with Operations.context(MigrationContext.configure(conn)):module.upgrade()
                report['ddl_probe']={'result':'would_succeed_rolled_back'}
            except Exception as exc:
                original=getattr(exc,'orig',None)
                report['ddl_probe']={'result':'failed_rolled_back','exception_class':type(exc).__name__,
                                     'sqlstate':getattr(original,'pgcode',None)}
            finally:tx.rollback()
        final=snapshot(engine,salt)
        report['probe_comparison']=compare(before,final)
        # Report only schema metadata, never table contents or record identifiers.
        selected=('job_retention_contracts','support_plans','support_records')
        report['relevant_schema']={t:final['schema'][t] for t in selected}
        report['relevant_null_counts']={t:{'before':before['null_counts'][t],'after':final['null_counts'][t]} for t in selected}
        report['relevant_states']={t:{'before':before['states'][t],'after':final['states'][t]} for t in selected}
        report['api_checks_after_failed_upgrade']={}
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
                    report['api_checks_after_failed_upgrade'][label]=response.status_code
            db.session.rollback()
        report['migration_success']=report['normal_upgrade']=='success'
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
        try:report['development_db_comparison']=compare(source_before,snapshot(source_engine,salt))
        finally:source_engine.dispose()
        Path(args.report).write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    print(json.dumps({'restore':report.get('restore'),'normal_upgrade':report.get('normal_upgrade'),
        'ddl_probe':report.get('ddl_probe'),'validation_database_removed':report.get('validation_database_removed')},ensure_ascii=False))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for flag in ('env-file','dump','report'):p.add_argument('--'+flag,required=True)
    try:run(p.parse_args())
    except Exception as exc:
        print('VALIDATION_RUN_FAILED:'+type(exc).__name__)
        sys.exit(1)
