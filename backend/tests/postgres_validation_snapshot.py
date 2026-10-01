"""In-memory value comparisons; reports expose counts and metadata, never row values."""
import hashlib
import hmac
import json
from sqlalchemy import inspect, text


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
            occurrences = {}
            for row in rows:
                fingerprint = digest(dict(row))
                occurrences[fingerprint] = occurrences.get(fingerprint, 0) + 1
                key = digest([row[c] for c in pk]) if pk else fingerprint + ':' + str(occurrences[fingerprint])
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
            ownership = conn.execute(text('''SELECT t.relname AS table_name, a.attname AS column_name, d.deptype
                FROM pg_class s JOIN pg_namespace n ON n.oid=s.relnamespace
                JOIN pg_depend d ON d.objid=s.oid AND d.classid='pg_class'::regclass AND d.deptype IN ('a','i')
                JOIN pg_class t ON t.oid=d.refobjid
                JOIN pg_attribute a ON a.attrelid=t.oid AND a.attnum=d.refobjsubid
                WHERE n.nspname='public' AND s.relname=:name'''), {'name':name}).mappings().all()
            result['sequences'][name] = {'state':list(state), 'definition':dict(definition), 'ownership':[dict(v) for v in ownership]}
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
