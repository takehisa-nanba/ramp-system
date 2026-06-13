"""Add default_start_time and default_end_time columns to office_service_configurations"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "3c8f9a1b2c34"
down_revision = "6fe30bb410e4"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('office_service_configurations', sa.Column('default_start_time', sa.String(length=5), nullable=True))
    op.add_column('office_service_configurations', sa.Column('default_end_time', sa.String(length=5), nullable=True))

def downgrade():
    op.drop_column('office_service_configurations', 'default_end_time')
    op.drop_column('office_service_configurations', 'default_start_time')
