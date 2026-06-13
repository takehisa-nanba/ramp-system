"""rename status to approval_status in user daily schedules

Revision ID: 3676eb9031ab
Revises: 402734b2ff7b
Create Date: 2026-06-13 11:04:56.105358

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3676eb9031ab'
down_revision = '402734b2ff7b'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user_daily_schedules', schema=None) as batch_op:
        batch_op.alter_column('status', new_column_name='approval_status', existing_type=sa.String(length=30))
    op.execute("UPDATE user_daily_schedules SET approval_status = 'APPROVED' WHERE approval_status = 'CONFIRMED'")


def downgrade():
    op.execute("UPDATE user_daily_schedules SET approval_status = 'CONFIRMED' WHERE approval_status = 'APPROVED'")
    with op.batch_alter_table('user_daily_schedules', schema=None) as batch_op:
        batch_op.alter_column('approval_status', new_column_name='status', existing_type=sa.String(length=30))
