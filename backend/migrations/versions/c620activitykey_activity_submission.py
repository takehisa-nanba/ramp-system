"""Deduplicate timed activity submissions when a save is retried."""
from alembic import op
import sqlalchemy as sa

revision = "c620activitykey"
down_revision = "b510timecardreq"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("audit_action_logs") as table:
        table.add_column(sa.Column("activity_request_id", sa.String(36)))
        table.create_unique_constraint("uq_activity_request", ["actor_supporter_id", "activity_request_id"])


def downgrade():
    with op.batch_alter_table("audit_action_logs") as table:
        table.drop_constraint("uq_activity_request", type_="unique")
        table.drop_column("activity_request_id")
