"""Identify the exact work interval selected for an attendance correction."""
from alembic import op
import sqlalchemy as sa

revision = "b510timecardreq"
down_revision = "a426planassess"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("supporter_attendance_correction_requests") as table:
        table.add_column(sa.Column("target_timecard_id", sa.Integer()))
        table.create_foreign_key("fk_correction_target_timecard", "supporter_timecards", ["target_timecard_id"], ["id"])


def downgrade():
    if op.get_bind().execute(sa.text("SELECT 1 FROM supporter_attendance_correction_requests WHERE target_timecard_id IS NOT NULL LIMIT 1")).first():
        raise RuntimeError("勤務区間を特定した申請が登録されています。")
    with op.batch_alter_table("supporter_attendance_correction_requests") as table:
        table.drop_constraint("fk_correction_target_timecard", type_="foreignkey")
        table.drop_column("target_timecard_id")
