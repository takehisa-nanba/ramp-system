"""Keep participant activities distinct from staff interventions."""
from alembic import op
import sqlalchemy as sa

revision = "f217activities"
down_revision = "e927merge"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("participant_activities",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("log_date", sa.Date, nullable=False),
        sa.Column("request_id", sa.String(36), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.UniqueConstraint("user_id", "request_id"))
    op.create_index("ix_participant_activities_user_id", "participant_activities", ["user_id"])
    with op.batch_alter_table("support_records") as table:
        table.add_column(sa.Column("participant_activity_id", sa.Integer))
        table.create_foreign_key("fk_support_record_activity", "participant_activities", ["participant_activity_id"], ["id"])


def downgrade():
    if op.get_bind().execute(sa.text("SELECT 1 FROM participant_activities LIMIT 1")).first():
        raise RuntimeError("活動履歴があるため取り消せません。")
    with op.batch_alter_table("support_records") as table:
        table.drop_constraint("fk_support_record_activity", type_="foreignkey")
        table.drop_column("participant_activity_id")
    op.drop_table("participant_activities")
