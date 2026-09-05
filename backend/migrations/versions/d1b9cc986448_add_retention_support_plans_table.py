"""add_retention_support_plans_table

Revision ID: d1b9cc986448
Revises: 84c9effb5337
Create Date: 2026-09-05 11:15:22.232367

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd1b9cc986448'
down_revision = '84c9effb5337'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    if 'retention_support_plans' not in existing_tables:
        op.create_table(
            'retention_support_plans',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('contract_id', sa.Integer(), nullable=False),
            sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('overall_support_goal', sa.Text(), nullable=False),
            sa.Column('start_date', sa.Date(), nullable=False),
            sa.Column('review_date', sa.Date(), nullable=True),
            sa.Column('review_reason', sa.Text(), nullable=True),
            sa.Column('next_review_deadline', sa.Date(), nullable=False),
            sa.Column('status', sa.String(length=20), nullable=False, server_default='ACTIVE'),
            sa.Column('created_by_id', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(['contract_id'], ['job_retention_contracts.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['created_by_id'], ['supporters.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('contract_id', 'version', name='uq_retention_plan_contract_version')
        )
        op.create_index('ix_retention_support_plans_contract_id', 'retention_support_plans', ['contract_id'], unique=False)
        op.create_index('ix_retention_support_plans_status', 'retention_support_plans', ['status'], unique=False)
        # PostgreSQL 部分一意インデックス: ACTIVE な計画は1契約につき1件のみ
        op.create_index(
            'uq_active_retention_plan',
            'retention_support_plans',
            ['contract_id'],
            unique=True,
            postgresql_where=sa.text("status = 'ACTIVE'")
        )

    # retention_support_action_logs に updated_at が欠落していた場合の安全な補完
    if 'retention_support_action_logs' in existing_tables:
        cols = {c['name'] for c in insp.get_columns('retention_support_action_logs')}
        if 'updated_at' not in cols:
            op.add_column(
                'retention_support_action_logs',
                sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now())
            )


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    if 'retention_support_plans' in existing_tables:
        op.drop_index('uq_active_retention_plan', table_name='retention_support_plans')
        op.drop_index('ix_retention_support_plans_status', table_name='retention_support_plans')
        op.drop_index('ix_retention_support_plans_contract_id', table_name='retention_support_plans')
        op.drop_table('retention_support_plans')
