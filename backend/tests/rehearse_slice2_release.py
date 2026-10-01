"""Release rehearsal exclusively in generated disposable PostgreSQL databases.

No connection URL, record value, dump content or raw exception is printed.
The supplied output directory must be outside Git and access restricted.
"""
import argparse
import contextlib
from datetime import datetime, timezone
import hashlib
import io
import json
import logging
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

from dotenv import dotenv_values
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend.migrations.slice2_compat.schema_contract import assert_schema, read_schema
from backend.tests.postgres_validation_snapshot import snapshot, compare
from backend.tests.slice2_bridge_checks import assert_unchanged


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').digest()


@contextlib.contextmanager
def quiet():
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        yield


def pg_environment(url):
    env = os.environ.copy()
    for key in ('PGSERVICE', 'PGSERVICEFILE', 'PGOPTIONS', 'PGHOSTADDR', 'PGSSLMODE',
                'PGSSLROOTCERT', 'PGSSLCERT', 'PGSSLKEY'):
        env.pop(key, None)
    env.update(PGHOST=url.host or '', PGPORT=str(url.port or 5432), PGDATABASE=url.database,
               PGUSER=url.username or '', PGPASSWORD=url.password or '', PGCONNECT_TIMEOUT='10')
    for key in ('sslmode', 'sslrootcert', 'sslcert', 'sslkey'):
        if key in url.query:
            env['PG' + key.upper()] = url.query[key]
    return env


def pg_run(command, url):
    result = subprocess.run(command, env=pg_environment(url), capture_output=True)
    if result.returncode:
        raise RuntimeError('PostgreSQL utility failed; output suppressed')
    return result.stdout


def data_checks(engine, state):
    has_soft_delete = any(c['name'] == 'deleted_at' for c in state['schema']['job_retention_contracts']['columns'])
    queries = {
        'active_contract_duplicates': "SELECT count(*) FROM (SELECT user_id FROM job_retention_contracts WHERE status='ACTIVE' GROUP BY user_id HAVING count(*)>1) q",
        'daily_log_duplicates': 'SELECT count(*) FROM (SELECT user_id,log_date FROM user_daily_logs GROUP BY user_id,log_date HAVING count(*)>1) q',
        'null_timecard_sequence_no': 'SELECT count(*) FROM supporter_timecards WHERE sequence_no IS NULL',
        'retention_record_orphans': 'SELECT count(*) FROM job_retention_records r LEFT JOIN job_retention_contracts c ON c.id=r.contract_id WHERE c.id IS NULL',
    }
    if has_soft_delete:
        queries['active_contract_duplicates'] = queries['active_contract_duplicates'].replace("status='ACTIVE'", "status='ACTIVE' AND deleted_at IS NULL")
    result = {'fk_orphans': sum(state['foreign_key_orphans'].values()), 'sequence_anomalies': []}
    with engine.connect() as conn:
        conn.execute(text('SET TRANSACTION READ ONLY'))
        result.update({name: conn.execute(text(sql)).scalar() for name, sql in queries.items()})
        quote = engine.dialect.identifier_preparer.quote
        for name, seq in state['sequences'].items():
            definition = seq['definition']
            if definition['increment_by'] != 1 or definition['cycle'] or len(seq['ownership']) != 1:
                result['sequence_anomalies'].append(name)
                continue
            owner = seq['ownership'][0]
            maximum = conn.execute(text('SELECT max(' + quote(owner['column_name']) + ') FROM public.' + quote(owner['table_name']))).scalar()
            next_value = seq['state'][0] + (definition['increment_by'] if seq['state'][1] else 0)
            if (maximum is not None and next_value <= maximum) or next_value > definition['max_value']:
                result['sequence_anomalies'].append(name)
    return result


def preflight(engine, state):
    expected = json.loads((ROOT / 'backend/migrations/slice2_compat/source_schema.json').read_text(encoding='utf-8'))
    with engine.connect() as conn:
        conn.execute(text('SET TRANSACTION READ ONLY'))
        actual = read_schema(conn)
        differences = {}
        for table in sorted(set(expected['schema']) | set(actual['schema'])):
            old, new = expected['schema'].get(table), actual['schema'].get(table)
            if old != new:
                differences[table] = ['table_presence'] if old is None or new is None else [key for key in old if old[key] != new[key]]
        result = {'schema_differences': differences, 'enum_match': expected['enums'] == actual['enums'],
                  'revision_match': state['revision'] == ['f8e31a7c49b2'],
                  'sequence_manifest_defined': False}
        try:
            assert_schema(conn, 'source_schema')
            result['manifest_match'] = True
        except RuntimeError:
            result['manifest_match'] = False
    try:
        result['data_checks'] = data_checks(engine, state)
    except Exception as exc:
        # Unexpected input may lack columns needed for data checks. Still report
        # the schema differences and fail closed; never try to repair it.
        result['data_checks'] = {'not_evaluable': type(exc).__name__}
    result['passed'] = result['manifest_match'] and result['revision_match'] and not any(result['data_checks'].values())
    return result


def get_apis(app):
    from backend.app import db
    from backend.app.models import Supporter, User
    from flask_jwt_extended import create_access_token
    with app.app_context(), quiet():
        staff = Supporter.query.filter_by(is_active=True).first()
        user = User.query.first()
        assert staff and user
        headers = {'Authorization': 'Bearer ' + create_access_token(identity=f'staff:{staff.id}')}
        paths = [(p, p) for p in ('/api/users', '/api/records', '/api/job-retention/users')]
        paths += [(f'/api/users/{{id}}/{suffix}', f'/api/users/{user.id}/{suffix}')
                  for suffix in ('support-plans', 'monitoring-reports', 'case-conferences')]
        result = {label: app.test_client().get(url, headers=headers).status_code for label, url in paths}
        db.session.rollback()
    return result


LEGACY_PROBE = r'''
import contextlib,io,json,logging,os
logging.disable(logging.CRITICAL)
with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
    from backend.app import create_app,db
    from backend.config import Config
    from backend.app.models import Supporter,User
    from backend.app.services.core_service import check_permission
    from flask_jwt_extended import create_access_token
    class C(Config):
        TESTING=True
        SQLALCHEMY_DATABASE_URI=os.environ['RAMP_REHEARSAL_TARGET_URL']
    app=create_app(C)
    with app.app_context():
        staff=next(s for s in Supporter.query.filter_by(is_active=True).all() if check_permission(f'staff:{s.id}','JOB_RETENTION_VIEW'))
        user=User.query.first()
        headers={'Authorization':'Bearer '+create_access_token(identity=f'staff:{staff.id}')}
        paths=[(p,p) for p in ['/api/users','/api/records','/api/job-retention/contracts']]
        paths += [(f'/api/users/{{id}}/{s}',f'/api/users/{user.id}/{s}') for s in ['support-plans','monitoring-reports','case-conferences']]
        result={label:app.test_client().get(url,headers=headers).status_code for label,url in paths}
        db.session.remove();db.engine.dispose()
print(json.dumps(result))
'''


def run(args):
    started = time.perf_counter()
    logging.disable(logging.CRITICAL)
    dump, output = Path(args.dump).resolve(), Path(args.output_dir).resolve()
    for path in (dump, output):
        if any((p / '.git').exists() for p in [path, *path.parents]):
            raise RuntimeError('Private artifacts must be outside Git')
    if not output.is_dir() or not dump.is_file():
        raise RuntimeError('Existing private output directory and custom dump required')
    values = dotenv_values(args.env_file)
    source = make_url(values['DATABASE_URL'])
    if source.get_backend_name() != 'postgresql':
        raise RuntimeError('PostgreSQL required')
    for key, value in values.items():
        if value is not None:
            os.environ[key] = value
    original_digest = digest(dump)
    salt = os.urandom(32)
    report = {'started_utc': datetime.now(timezone.utc).isoformat(), 'timings_seconds': {},
              'production_migrated': False, 'development_migrated': False, 'migration_executed': False}
    admin = create_engine(source, isolation_level='AUTOCOMMIT')
    source_engine = create_engine(source)
    source_before = snapshot(source_engine, salt)
    created = set()
    engines = []
    app = None

    def timed(name, operation):
        begin = time.perf_counter()
        try:
            return operation()
        finally:
            report['timings_seconds'][name] = round(time.perf_counter() - begin, 6)

    def new_database():
        name = 'ramp_release_rehearsal_' + uuid.uuid4().hex
        if name == source.database:
            raise RuntimeError('Unsafe destination')
        with admin.connect() as conn:
            conn.execute(text('CREATE DATABASE ' + name))
        created.add(name)
        url = source.set(database=name)
        engine = create_engine(url)
        engines.append(engine)
        return name, url, engine

    def drop_database(name):
        if name not in created or name == source.database or not re.fullmatch(r'ramp_release_rehearsal_[0-9a-f]{32}', name):
            raise RuntimeError('Unsafe drop target')
        with admin.connect() as conn:
            conn.execute(text('DROP DATABASE ' + name + ' WITH (FORCE)'))
            if conn.execute(text('SELECT EXISTS(SELECT 1 FROM pg_database WHERE datname=:name)'), {'name': name}).scalar():
                raise RuntimeError('Disposable database still exists')
        created.remove(name)

    try:
        catalog = pg_run(['pg_restore', '--list', str(dump)], source).decode(errors='replace')
        report['archive_created_at'] = next((line.split('at ', 1)[1] for line in catalog.splitlines() if 'Archive created at ' in line), 'unknown')
        name, target, engine = new_database()
        timed('candidate_restore', lambda: pg_run(['pg_restore', '--no-owner', '--no-privileges', '--exit-on-error', '--single-transaction', '--dbname', name, str(dump)], target))
        before = timed('candidate_snapshot', lambda: snapshot(engine, salt))
        report['source_preflight'] = timed('source_preflight', lambda: preflight(engine, before))
        if not report['source_preflight']['passed']:
            report['result'] = 'NO_GO_SOURCE_PREFLIGHT'
            return report

        # Simulate the maintenance backup against the restored isolated source.
        maintenance_start = time.perf_counter()
        rehearsal_backup = output / 'rehearsal-before-migration.dump'
        if rehearsal_backup.exists():
            raise RuntimeError('Refusing to overwrite a rehearsal backup')
        timed('backup_acquisition', lambda: pg_run(['pg_dump', '--format=custom', '--file', str(rehearsal_backup)], target))
        timed('backup_catalog_validation', lambda: pg_run(['pg_restore', '--list', str(rehearsal_backup)], target))
        verify_name, verify_url, verify_engine = new_database()
        timed('backup_verification_restore', lambda: pg_run(['pg_restore', '--no-owner', '--no-privileges', '--exit-on-error', '--single-transaction', '--dbname', verify_name, str(rehearsal_backup)], verify_url))
        backup_state = timed('backup_verification_snapshot', lambda: snapshot(verify_engine, salt))
        assert_unchanged(before, backup_state)
        report['fresh_backup_restore_verified_before_migration'] = True
        verify_engine.dispose()
        drop_database(verify_name)
        report['maintenance_source_preflight'] = timed('maintenance_source_preflight', lambda: preflight(engine, before))
        if not report['maintenance_source_preflight']['passed']:
            raise RuntimeError('Maintenance preflight failed')

        from backend.app import create_app, db
        from backend.config import Config
        from flask_migrate import upgrade
        class C(Config):
            TESTING = True
            SQLALCHEMY_DATABASE_URI = target.render_as_string(hide_password=False)
        with quiet():
            app = create_app(C)
        sql_timings, locks = [], {}
        migration_origin = time.perf_counter()
        def before_sql(conn, cursor, statement, parameters, context, executemany):
            context._rehearsal_start = time.perf_counter()
        def after_sql(conn, cursor, statement, parameters, context, executemany):
            ended = time.perf_counter()
            verb = statement.lstrip().split(None, 1)[0].upper()
            if verb in ('ALTER', 'CREATE', 'DROP', 'LOCK') or (verb == 'UPDATE' and 'alembic_version' in statement):
                sql_timings.append({'operation': verb, 'sequence': len(sql_timings) + 1,
                    'start_offset': round(context._rehearsal_start - migration_origin, 6),
                    'seconds': round(ended - context._rehearsal_start, 6)})
                matched = re.match(r'\s*(?:ALTER|CREATE|DROP)\s+(?:UNIQUE\s+)?(?:TABLE|INDEX)\s+"?([a-zA-Z0-9_]+)', statement)
                if matched:
                    sql_timings[-1]['object'] = matched.group(1)
            if verb == 'LOCK':
                locks['acquisition_started_offset'] = context._rehearsal_start - migration_origin
                locks['acquired_offset'] = ended - migration_origin
                locks['acquisition_seconds'] = ended - context._rehearsal_start
                pid = conn.connection.driver_connection.get_backend_pid()
                with engine.connect() as observer:
                    locks['tables'] = observer.execute(text("""SELECT c.relname FROM pg_locks l
                        JOIN pg_class c ON c.oid=l.relation JOIN pg_namespace n ON n.oid=c.relnamespace
                        WHERE l.pid=:pid AND l.granted AND l.mode='AccessExclusiveLock'
                        AND n.nspname='public' AND c.relkind='r' ORDER BY c.relname"""), {'pid': pid}).scalars().all()
        with app.app_context(), quiet():
            if db.engine.url.database != name:
                raise RuntimeError('Application destination mismatch')
            event.listen(db.engine, 'before_cursor_execute', before_sql)
            event.listen(db.engine, 'after_cursor_execute', after_sql)
            try:
                migration_origin = time.perf_counter()
                report['migration_executed'] = True
                timed('migration_until_committed', lambda: upgrade(directory=str(ROOT / 'backend/migrations/slice2_compat'), revision='head'))
                committed = time.perf_counter() - migration_origin
            finally:
                event.remove(db.engine, 'before_cursor_execute', before_sql)
                event.remove(db.engine, 'after_cursor_execute', after_sql)
            timed('normal_main_upgrade_noop', lambda: upgrade(directory=str(ROOT / 'backend/migrations'), revision='head'))
        report['sql_timings'] = sql_timings
        report['locks'] = locks
        locks['held_until_upgrade_return_upper_bound_seconds'] = round(committed - locks['acquisition_started_offset'], 6)
        locks['all_source_tables_locked'] = locks['tables'] == sorted(before['tables'])
        with engine.connect() as observer:
            locks['remaining_access_exclusive_locks'] = observer.execute(text("""SELECT count(*) FROM pg_locks l
                JOIN pg_class c ON c.oid=l.relation JOIN pg_namespace n ON n.oid=c.relnamespace
                WHERE l.database=(SELECT oid FROM pg_database WHERE datname=current_database())
                AND l.granted AND l.mode='AccessExclusiveLock' AND n.nspname='public'""")).scalar()
        assert locks['all_source_tables_locked'] and locks['remaining_access_exclusive_locks'] == 0
        report['timings_seconds']['ddl_execution_sum'] = round(sum(t['seconds'] for t in sql_timings if t['operation'] in ('ALTER', 'CREATE', 'DROP')), 6)
        report['timings_seconds']['revision_update_offset'] = next(t['start_offset'] + t['seconds'] for t in sql_timings if t['operation'] == 'UPDATE')
        validation_started = time.perf_counter()
        after = timed('post_migration_snapshot', lambda: snapshot(engine, salt))
        report['migration_comparison'] = compare(before, after)
        changes = report['migration_comparison']
        assert after['revision'] == ['c731retentioncore']
        for table, change in changes['tables'].items():
            if table != 'alembic_version':
                assert change['before'] == change['after'] and not change['removed_keys'] and not change['added_keys'] and not change['changed_columns']
        assert changes['sequences_unchanged'] and changes['enums_unchanged']
        for table, columns in before['null_counts'].items():
            for column, count in columns.items():
                assert after['null_counts'][table][column] == count
        with engine.connect() as conn:
            assert_schema(conn, 'target_schema')
        report['db_smoke'] = timed('db_smoke', lambda: data_checks(engine, after))
        assert not any(report['db_smoke'].values())
        report['timings_seconds']['post_migration_validation_total'] = round(time.perf_counter() - validation_started, 6)
        report['get_api_smoke'] = timed('get_api_smoke', lambda: get_apis(app))
        assert all(code == 200 for code in report['get_api_smoke'].values())
        from backend.tests.retention_postgres_scenarios import exercise
        with quiet():
            report['business_smoke'] = timed('business_smoke', lambda: exercise(app, engine, full=False))
        report['timings_seconds']['simulated_maintenance_to_smoke_complete'] = round(time.perf_counter() - maintenance_start, 6)
        with quiet():
            report['complete_checks'] = timed('complete_checks', lambda: exercise(app, engine))
        tested = timed('post_complete_snapshot', lambda: snapshot(engine, salt))
        for table, original in before['tables'].items():
            if table == 'alembic_version':
                continue
            for key, record in original['records'].items():
                assert key in tested['tables'][table]['records']
                assert all(tested['tables'][table]['records'][key][column] == value for column, value in record.items())
        report['legacy_data_unchanged_after_tests'] = True
        with app.app_context():
            db.session.remove()
            db.engine.dispose()
        app = None
        engine.dispose()
        timed('destroy_migrated_database', lambda: drop_database(name))

        recovery_start = time.perf_counter()
        recovery_name, recovery_url, recovery = new_database()
        timed('recovery_restore', lambda: pg_run(['pg_restore', '--no-owner', '--no-privileges', '--exit-on-error', '--single-transaction', '--dbname', recovery_name, str(rehearsal_backup)], recovery_url))
        recovered = timed('recovery_snapshot', lambda: snapshot(recovery, salt))
        assert_unchanged(before, recovered)
        report['recovery_comparison'] = compare(before, recovered)
        report['recovery_data_equal'] = True
        # Failure injection is separate from the successful timed migration.
        class RecoveryConfig(Config):
            TESTING = True
            SQLALCHEMY_DATABASE_URI = recovery_url.render_as_string(hide_password=False)
        with quiet():
            app = create_app(RecoveryConfig)
            from backend.tests.slice2_bridge_checks import exercise_failures
            report['failure_checks'] = timed('failure_checks', lambda: exercise_failures(app, recovery, recovered, salt))
        legacy_env = os.environ.copy()
        legacy_env['RAMP_REHEARSAL_TARGET_URL'] = recovery_url.render_as_string(hide_password=False)
        legacy_env['PYTHONPATH'] = str(Path(args.legacy_code_root).resolve())
        def legacy_probe():
            result = subprocess.run([sys.executable, '-B', '-c', LEGACY_PROBE], cwd=args.legacy_code_root,
                                    env=legacy_env, capture_output=True, text=True)
            if result.returncode:
                raise RuntimeError('Legacy application probe failed; details suppressed')
            return json.loads(result.stdout)
        report['legacy_api_recovery'] = timed('legacy_api_recovery', legacy_probe)
        report['legacy_application_commit'] = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=args.legacy_code_root, capture_output=True, text=True, check=True).stdout.strip()
        report['timings_seconds']['recovery_total_including_failure_tests'] = round(time.perf_counter() - recovery_start, 6)
        assert all(code == 200 for code in report['legacy_api_recovery'].values())
        report['result'] = 'REHEARSAL_PASSED_PENDING_MAINTENANCE_BUDGET'
        return report
    finally:
        report.setdefault('result', 'FAILED_OR_INTERRUPTED')
        if app:
            from backend.app import db
            with app.app_context():
                db.session.remove()
                db.engine.dispose()
        for engine in engines:
            engine.dispose()
        for name in list(created):
            drop_database(name)
        report['disposable_databases_removed'] = not created
        source_after = snapshot(source_engine, salt)
        source_engine.dispose()
        admin.dispose()
        report['source_database_unchanged'] = compare(source_before, source_after)
        report['candidate_backup_unchanged'] = digest(dump) == original_digest
        report['timings_seconds']['all_stages'] = round(time.perf_counter() - started, 6)
        (output / 'rehearsal-summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
        assert_unchanged(source_before, source_after)
        assert report['candidate_backup_unchanged']


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for flag in ('env-file', 'dump', 'output-dir', 'legacy-code-root'):
        parser.add_argument('--' + flag, required=True)
    try:
        result = run(parser.parse_args())
        print(json.dumps({k: result.get(k) for k in ('result', 'archive_created_at', 'timings_seconds', 'legacy_api_recovery', 'disposable_databases_removed')}, ensure_ascii=False))
        sys.exit(0 if result.get('result') == 'REHEARSAL_PASSED_PENDING_MAINTENANCE_BUDGET' else 2)
    except (Exception, SystemExit) as exc:
        if isinstance(exc, SystemExit):
            raise
        import traceback
        frame = traceback.extract_tb(exc.__traceback__)[-1]
        print('REHEARSAL_FAILED:' + type(exc).__name__ + ':' + Path(frame.filename).name + ':' + str(frame.lineno))
        sys.exit(1)
