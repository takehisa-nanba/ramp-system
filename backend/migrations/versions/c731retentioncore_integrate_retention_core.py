"""Add service ownership without guessing historical service assignments.

Existing contracts remain LEGACY_REVIEW, with their original dates and records.
"""
from alembic import op
import sqlalchemy as sa
revision = 'c731retentioncore'
down_revision = 'b01649029bec'
branch_labels = None
depends_on = None


def upgrade():
    for table in ('job_retention_contracts', 'support_plans', 'support_records'):
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column('office_service_configuration_id', sa.Integer(), nullable=True))
            batch.create_foreign_key('fk_' + table + '_service_config', 'office_service_configurations', ['office_service_configuration_id'], ['id'])
            batch.create_index('ix_' + table + '_office_service_configuration_id', ['office_service_configuration_id'])
    with op.batch_alter_table('job_retention_contracts') as batch:
        batch.add_column(sa.Column('status', sa.String(30), nullable=False, server_default='LEGACY_REVIEW'))
        batch.add_column(sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))
        batch.add_column(sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))
        batch.add_column(sa.Column('deleted_at', sa.DateTime(), nullable=True))
        batch.add_column(sa.Column('deleted_by_id', sa.Integer(), nullable=True))
        batch.add_column(sa.Column('delete_reason', sa.Text(), nullable=True))
        batch.create_foreign_key('fk_retention_deleted_by', 'supporters', ['deleted_by_id'], ['id'])
        batch.create_check_constraint('ck_retention_active_service', "status != 'ACTIVE' OR office_service_configuration_id IS NOT NULL")
    op.create_index('uq_retention_active_user', 'job_retention_contracts', ['user_id'], unique=True,
                    postgresql_where=sa.text("status = 'ACTIVE' AND deleted_at IS NULL"),
                    sqlite_where=sa.text("status = 'ACTIVE' AND deleted_at IS NULL"))


def downgrade():
    raise RuntimeError('Retention history must be preserved; use a reviewed forward migration.')
