"""Explicit slice2 -> c731 schema convergence, preserving every existing value.

This alternate script directory ends at the normal main revision only AFTER
DDL and the complete target schema contract pass in the same transaction.
It is never loaded by the normal main migration graph.
"""
from alembic import op
import sqlalchemy as sa

from backend.migrations.slice2_compat.schema_contract import assert_schema

revision = 'c731retentioncore'
down_revision = 'f8e31a7c49b2'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name != 'postgresql':
        raise RuntimeError('Slice2 compatibility requires PostgreSQL.')
    op.execute("SET LOCAL lock_timeout = '10s'")
    op.execute("SET LOCAL statement_timeout = '120s'")
    op.execute('SET LOCAL search_path = public')
    quote = bind.dialect.identifier_preparer.quote
    tables = sorted(sa.inspect(bind).get_table_names(schema='public'))
    # Maintenance window: freeze writers before inspecting schema and data.
    op.execute('LOCK TABLE ' + ', '.join('public.' + quote(t) for t in tables) + ' IN ACCESS EXCLUSIVE MODE')
    assert_schema(bind, 'source_schema')
    if bind.execute(sa.text('SELECT version_num FROM alembic_version')).scalars().all() != ['f8e31a7c49b2']:
        raise RuntimeError('Unexpected source revision.')
    preconditions = (
        'SELECT 1 FROM supporter_timecards WHERE sequence_no IS NULL LIMIT 1',
        'SELECT 1 FROM user_daily_logs GROUP BY user_id, log_date HAVING count(*) > 1 LIMIT 1',
        "SELECT 1 FROM job_retention_contracts WHERE status = 'ACTIVE' GROUP BY user_id HAVING count(*) > 1 LIMIT 1",
        'SELECT 1 FROM job_retention_records r LEFT JOIN job_retention_contracts c ON c.id=r.contract_id WHERE c.id IS NULL LIMIT 1',
    )
    for check in preconditions:
        if bind.execute(sa.text(check)).first():
            raise RuntimeError('Incompatible slice2 data; manual review required. No automatic data repair.')

    # Reuse existing service assignments, timestamps and statuses.
    op.alter_column('job_retention_contracts', 'office_service_configuration_id', nullable=True)
    op.alter_column('job_retention_contracts', 'status', server_default='LEGACY_REVIEW')
    for column in (sa.Column('deleted_at', sa.DateTime(), nullable=True),
                   sa.Column('deleted_by_id', sa.Integer(), nullable=True),
                   sa.Column('delete_reason', sa.Text(), nullable=True)):
        op.add_column('job_retention_contracts', column)
    op.create_foreign_key('fk_retention_deleted_by', 'job_retention_contracts', 'supporters', ['deleted_by_id'], ['id'])
    op.create_check_constraint('ck_retention_active_service', 'job_retention_contracts', "status != 'ACTIVE' OR office_service_configuration_id IS NOT NULL")
    op.create_index('uq_retention_active_user', 'job_retention_contracts', ['user_id'], unique=True,
                    postgresql_where=sa.text("status = 'ACTIVE' AND deleted_at IS NULL"))
    for column, target, fk, index in (
        ('office_service_configuration_id', 'office_service_configurations', 'fk_support_records_service_config', 'ix_support_records_office_service_configuration_id'),
        ('user_daily_log_id', 'user_daily_logs', 'support_records_user_daily_log_id_fkey', 'ix_support_records_user_daily_log_id'),
    ):
        op.add_column('support_records', sa.Column(column, sa.Integer(), nullable=True))
        op.create_foreign_key(fk, 'support_records', target, [column], ['id'])
        op.create_index(index, 'support_records', [column])
    op.create_foreign_key('job_retention_records_contract_id_fkey', 'job_retention_records', 'job_retention_contracts', ['contract_id'], ['id'])
    op.create_unique_constraint('uq_user_daily_log_user_date', 'user_daily_logs', ['user_id', 'log_date'])
    op.alter_column('supporter_timecards', 'sequence_no', nullable=False)
    op.alter_column('staff_activity_allocation_logs', 'allocated_duration_seconds', server_default='0')
    # Main does not supply legacy consent metadata. Preserve old values; unknown
    # metadata on new rows remains NULL instead of inventing signature/version data.
    for column in ('document_version', 'action', 'signature_method'):
        op.alter_column('document_consent_logs', column, nullable=True)
    renames = (
        ('job_retention_contracts', 'fk_job_retention_contracts_office_service_config', 'fk_job_retention_contracts_service_config'),
        ('support_plans', 'fk_support_plans_office_service_config', 'fk_support_plans_service_config'),
        ('absence_response_logs', 'absence_response_logs_linked_plan_id_fkey', 'fk_absence_response_logs_support_plans'),
        ('staff_activity_allocation_logs', 'staff_activity_allocation_log_office_service_configuration_fkey', 'fk_staff_activity_allocation_logs_office_service_config_id'),
        ('staff_activity_allocation_logs', 'staff_activity_allocation_logs_job_title_id_fkey', 'fk_staff_activity_allocation_logs_job_title_id'),
        ('staff_activity_allocation_logs', 'staff_activity_allocation_logs_supporter_timecard_id_fkey', 'fk_staff_activity_allocation_logs_supporter_timecard_id'),
    )
    for table, old, new in renames:
        op.execute(f'ALTER TABLE {table} RENAME CONSTRAINT {old} TO {new}')
    op.execute('ALTER INDEX ix_support_plans_office_service_config_id RENAME TO ix_support_plans_office_service_configuration_id')
    assert_schema(bind, 'target_schema')


def downgrade():
    raise RuntimeError('Forward-only; restore a reviewed backup instead of discarding history.')
