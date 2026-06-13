"""Merge heads for user schedule tables and office default times"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "merge_218388db7269_3c8f9a1b2c34"
# tuple of parent revisions
down_revision = ("218388db7269", "3c8f9a1b2c34")
branch_labels = None
depends_on = None

def upgrade():
    # No changes; this migration merges two heads.
    pass

def downgrade():
    # No changes to revert.
    pass
