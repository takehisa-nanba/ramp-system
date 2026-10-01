"""Frozen PostgreSQL schema contracts; contains no application data or secrets."""
import json
from pathlib import Path

import sqlalchemy as sa


def normalize(value):
    if isinstance(value, dict):
        return {k: normalize(v) for k, v in sorted(value.items()) if k != 'comment'}
    if isinstance(value, list):
        items = [normalize(v) for v in value]
        # Object collections have no order; FK column pairs / enum labels do.
        return sorted(items, key=lambda v: json.dumps(v, sort_keys=True)) if all(isinstance(v, dict) for v in value) else items
    return value


def read_schema(connection):
    inspector = sa.inspect(connection)
    tables = {}
    for table in inspector.get_table_names(schema='public'):
        tables[table] = {
            'columns': [{k: str(c[k]) if k == 'type' else c[k]
                         for k in ('name', 'type', 'nullable', 'default')}
                        for c in inspector.get_columns(table, schema='public')],
            'pk': inspector.get_pk_constraint(table, schema='public'),
            'fks': inspector.get_foreign_keys(table, schema='public'),
            'checks': inspector.get_check_constraints(table, schema='public'),
            'indexes': inspector.get_indexes(table, schema='public'),
            'unique': inspector.get_unique_constraints(table, schema='public'),
        }
    return normalize({'schema': tables, 'enums': inspector.get_enums(schema='public')})


def assert_schema(connection, name):
    expected = json.loads(Path(__file__).with_name(name + '.json').read_text(encoding='utf-8'))
    if name == 'target_schema':
        # The target file lists complete definitions only for changed tables.
        # All other tables and enum definitions must still match the frozen source.
        source = json.loads(Path(__file__).with_name('source_schema.json').read_text(encoding='utf-8'))
        source['schema'].update(expected['schema'])
        expected = source
    if read_schema(connection) != expected:
        # Do not expose unexpected defaults, SQL statements, credentials or row values.
        raise RuntimeError('Slice2 compatibility schema contract mismatch: ' + name)
    invalid = connection.execute(sa.text("""
        SELECT EXISTS(SELECT 1 FROM pg_constraint c JOIN pg_namespace n ON n.oid=c.connamespace
                      WHERE n.nspname='public' AND NOT c.convalidated)
            OR EXISTS(SELECT 1 FROM pg_index i JOIN pg_class t ON t.oid=i.indrelid
                      JOIN pg_namespace n ON n.oid=t.relnamespace
                      WHERE n.nspname='public' AND (NOT i.indisvalid OR NOT i.indisready))
    """)).scalar()
    if invalid:
        raise RuntimeError('Unvalidated constraints or invalid indexes require review.')
