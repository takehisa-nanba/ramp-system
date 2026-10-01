"""Failure-path checks that run exclusively on the disposable restored database."""
import contextlib
import importlib.util
import io
from pathlib import Path
from unittest.mock import patch

from alembic.migration import MigrationContext
from alembic.operations import Operations
from flask_migrate import upgrade
from sqlalchemy import inspect, text

from backend.tests.postgres_validation_snapshot import snapshot, compare


def assert_unchanged(before, after):
    result = compare(before, after)
    assert result['revision_before'] == result['revision_after']
    assert all(result[k] for k in ('schema_unchanged', 'enums_unchanged',
                                  'sequences_unchanged', 'null_counts_unchanged',
                                  'status_counts_unchanged', 'fk_orphan_counts_unchanged'))
    assert all(c['before'] == c['after'] and not c['removed_keys'] and
               not c['added_keys'] and not c['changed_columns'] for c in result['tables'].values())


def exercise_failures(app, engine, before, salt):
    root = Path(__file__).resolve().parents[2]
    path = root / 'backend/migrations/slice2_compat/versions/c731retentioncore_bridge.py'
    spec = importlib.util.spec_from_file_location('bridge_failure_test', path)
    bridge = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bridge)
    cases = {
        'unexpected_column': 'ALTER TABLE support_records ADD COLUMN unexpected_test INTEGER',
        'unexpected_type': 'ALTER TABLE job_retention_contracts ALTER COLUMN status TYPE VARCHAR(60)',
        'unexpected_default': "ALTER TABLE job_retention_contracts ALTER COLUMN status SET DEFAULT 'OTHER'",
        'unexpected_nullability': 'ALTER TABLE job_retention_contracts ALTER COLUMN office_service_configuration_id DROP NOT NULL',
        'missing_index': 'DROP INDEX ix_support_plans_office_service_config_id',
        'wrong_revision': "UPDATE alembic_version SET version_num='unexpected'",
    }
    results = []
    for name, mutation in cases.items():
        with engine.connect() as conn:
            transaction = conn.begin()
            try:
                conn.execute(text(mutation))
                try:
                    with Operations.context(MigrationContext.configure(conn)):
                        bridge.upgrade()
                except RuntimeError:
                    pass
                else:
                    raise AssertionError('Unexpected input was accepted: ' + name)
            finally:
                transaction.rollback()
        assert_unchanged(before, snapshot(engine, salt))
        results.append(name + '_rejected_without_changes')

    # Duplicate an existing ACTIVE contract without consuming a sequence value.
    with engine.connect() as conn:
        transaction = conn.begin()
        try:
            quote = engine.dialect.identifier_preparer.quote
            columns = [c['name'] for c in inspect(conn).get_columns('job_retention_contracts')]
            values = ['(SELECT max(id)+1 FROM job_retention_contracts)' if c == 'id' else quote(c) for c in columns]
            inserted = conn.execute(text('INSERT INTO job_retention_contracts (' + ','.join(map(quote, columns)) +
                ') SELECT ' + ','.join(values) + " FROM job_retention_contracts WHERE status='ACTIVE' LIMIT 1"))
            assert inserted.rowcount == 1
            try:
                with Operations.context(MigrationContext.configure(conn)):
                    bridge.upgrade()
            except RuntimeError:
                pass
            else:
                raise AssertionError('Duplicate ACTIVE contract accepted')
        finally:
            transaction.rollback()
    assert_unchanged(before, snapshot(engine, salt))
    results.append('duplicate_active_contract_rejected_without_changes')

    with engine.connect() as conn:
        transaction = conn.begin()
        try:
            conn.execute(text("""INSERT INTO job_retention_records
                (id, contract_id, record_date, support_method, support_details, supporter_id)
                VALUES (-100, -100, '2026-10-01', 'validation', 'validation',
                        (SELECT min(id) FROM supporters))"""))
            try:
                with Operations.context(MigrationContext.configure(conn)):
                    bridge.upgrade()
            except RuntimeError:
                pass
            else:
                raise AssertionError('Orphan historical retention record accepted')
        finally:
            transaction.rollback()
    assert_unchanged(before, snapshot(engine, salt))
    results.append('orphan_retention_record_rejected_without_changes')

    original = Operations.create_index
    injected = []
    def fail_after_ddl(self, name, *args, **kwargs):
        if name == 'uq_retention_active_user':
            injected.append(True)
            raise RuntimeError('Injected failure after ALTER/ADD/FK/CHECK DDL')
        return original(self, name, *args, **kwargs)
    with app.app_context(), patch.object(Operations, 'create_index', fail_after_ddl):
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                upgrade(directory=str(root / 'backend/migrations/slice2_compat'), revision='head')
        except (RuntimeError, SystemExit):
            assert injected, 'Upgrade failed before the injection point'
        else:
            raise AssertionError('Migration failure injection did not fire')
    assert_unchanged(before, snapshot(engine, salt))
    results.append('alembic_ddl_failure_rolls_back_schema_data_revision_sequences')
    return results
