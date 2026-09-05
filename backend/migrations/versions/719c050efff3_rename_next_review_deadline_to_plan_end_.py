"""rename next_review_deadline to plan_end_date

Revision ID: 719c050efff3
Revises: d1b9cc986448
Create Date: 2026-09-05 12:33:14.209601

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '719c050efff3'
down_revision = 'd1b9cc986448'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    if 'retention_support_plans' in existing_tables:
        cols = {c['name'] for c in insp.get_columns('retention_support_plans')}
        if 'next_review_deadline' in cols and 'plan_end_date' not in cols:
            with op.batch_alter_table('retention_support_plans', schema=None) as batch_op:
                batch_op.alter_column(
                    'next_review_deadline',
                    new_column_name='plan_end_date',
                    existing_type=sa.Date(),
                    nullable=False
                )


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    if 'retention_support_plans' in existing_tables:
        cols = {c['name'] for c in insp.get_columns('retention_support_plans')}
        if 'plan_end_date' in cols and 'next_review_deadline' not in cols:
            with op.batch_alter_table('retention_support_plans', schema=None) as batch_op:
                batch_op.alter_column(
                    'plan_end_date',
                    new_column_name='next_review_deadline',
                    existing_type=sa.Date(),
                    nullable=False
                )

