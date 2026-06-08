"""refactor_to_duration_seconds

Revision ID: 6fe30bb410e4
Revises: 2b9f67e27f16
Create Date: 2026-06-08 12:49:55.743961

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
"""refactor_to_duration_seconds

Revision ID: 6fe30bb410e4
Revises: 2b9f67e27f16
Create Date: 2026-06-08 12:49:55.743961

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6fe30bb410e4'
down_revision = '2b9f67e27f16'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add new columns
    with op.batch_alter_table('break_records', schema=None) as batch_op:
        batch_op.add_column(sa.Column('break_duration_seconds', sa.Integer(), nullable=True))

    with op.batch_alter_table('office_training_events', schema=None) as batch_op:
        batch_op.add_column(sa.Column('duration_seconds', sa.Integer(), nullable=True))

    with op.batch_alter_table('staff_activity_allocation_logs', schema=None) as batch_op:
        # Avoid nullable=False failure on existing rows by providing a server default first
        batch_op.add_column(sa.Column('allocated_duration_seconds', sa.Integer(), nullable=False, server_default='0'))

    with op.batch_alter_table('support_records', schema=None) as batch_op:
        batch_op.add_column(sa.Column('support_duration_seconds', sa.Integer(), nullable=True))

    with op.batch_alter_table('training_logs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('duration_seconds', sa.Integer(), nullable=True))

    # 2. Data Migration: Copy & convert existing minutes to seconds
    op.execute("UPDATE staff_activity_allocation_logs SET allocated_duration_seconds = allocated_minutes * 60")
    op.execute("UPDATE office_training_events SET duration_seconds = duration_minutes * 60")
    op.execute("UPDATE training_logs SET duration_seconds = duration_minutes * 60")

    # Calculate durations from start/end times if they exist
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute("UPDATE support_records SET support_duration_seconds = EXTRACT(EPOCH FROM (support_end_time - support_start_time)) WHERE support_start_time IS NOT NULL AND support_end_time IS NOT NULL")
        op.execute("UPDATE break_records SET break_duration_seconds = EXTRACT(EPOCH FROM (break_end_time - break_start_time)) WHERE break_start_time IS NOT NULL AND break_end_time IS NOT NULL")
    else:
        # SQLite
        op.execute("UPDATE support_records SET support_duration_seconds = CAST((julianday(support_end_time) - julianday(support_start_time)) * 86400 AS INTEGER) WHERE support_start_time IS NOT NULL AND support_end_time IS NOT NULL")
        op.execute("UPDATE break_records SET break_duration_seconds = CAST((julianday(break_end_time) - julianday(break_start_time)) * 86400 AS INTEGER) WHERE break_start_time IS NOT NULL AND break_end_time IS NOT NULL")

    # 3. Drop old columns
    with op.batch_alter_table('office_training_events', schema=None) as batch_op:
        batch_op.drop_column('duration_minutes')

    with op.batch_alter_table('staff_activity_allocation_logs', schema=None) as batch_op:
        batch_op.drop_column('allocated_minutes')

    with op.batch_alter_table('training_logs', schema=None) as batch_op:
        batch_op.drop_column('duration_minutes')


def downgrade():
    # 1. Restore old columns
    with op.batch_alter_table('training_logs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('duration_minutes', sa.Integer(), nullable=True))

    with op.batch_alter_table('staff_activity_allocation_logs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('allocated_minutes', sa.Integer(), nullable=False, server_default='0'))

    with op.batch_alter_table('office_training_events', schema=None) as batch_op:
        batch_op.add_column(sa.Column('duration_minutes', sa.Integer(), nullable=True))

    # 2. Data Migration: Copy & convert seconds back to minutes
    op.execute("UPDATE staff_activity_allocation_logs SET allocated_minutes = CAST(allocated_duration_seconds / 60 AS INTEGER)")
    op.execute("UPDATE office_training_events SET duration_minutes = CAST(duration_seconds / 60 AS INTEGER)")
    op.execute("UPDATE training_logs SET duration_minutes = CAST(duration_seconds / 60 AS INTEGER)")

    # 3. Drop new columns
    with op.batch_alter_table('training_logs', schema=None) as batch_op:
        batch_op.drop_column('duration_seconds')

    with op.batch_alter_table('support_records', schema=None) as batch_op:
        batch_op.drop_column('support_duration_seconds')

    with op.batch_alter_table('staff_activity_allocation_logs', schema=None) as batch_op:
        batch_op.drop_column('allocated_duration_seconds')

    with op.batch_alter_table('office_training_events', schema=None) as batch_op:
        batch_op.drop_column('duration_seconds')

    with op.batch_alter_table('break_records', schema=None) as batch_op:
        batch_op.drop_column('break_duration_seconds')
