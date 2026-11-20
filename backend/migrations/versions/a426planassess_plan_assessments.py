"""Keep interviews independently of draft creation and retain legacy plans."""
from alembic import op
import sqlalchemy as sa

revision = "a426planassess"
down_revision = "c731retentioncore"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("plan_assessments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("office_service_configuration_id", sa.Integer(), sa.ForeignKey("office_service_configurations.id")),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("support_plans.id"), unique=True),
        sa.Column("supporter_id", sa.Integer(), sa.ForeignKey("supporters.id"), nullable=False),
        sa.Column("interview_date", sa.Date(), nullable=False),
        sa.Column("method", sa.String(20), nullable=False),
        sa.Column("exception_reason", sa.Text()),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_plan_assessments_user_id", "plan_assessments", ["user_id"])


def downgrade():
    if op.get_bind().execute(sa.text("SELECT 1 FROM plan_assessments LIMIT 1")).first():
        raise RuntimeError("保存済みの面談記録があります。")
    op.drop_table("plan_assessments")
