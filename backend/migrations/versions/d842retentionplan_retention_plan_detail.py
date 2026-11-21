"""Retention plan content and nullable goal evaluation.

Revision ID: d842retentionplan
Revises: c731retentioncore
"""
from alembic import op
import sqlalchemy as sa

revision = 'd842retentionplan'
down_revision = 'c731retentioncore'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('job_retention_plan_details',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('support_plan_id',sa.Integer(),sa.ForeignKey('support_plans.id'),nullable=False,unique=True),
        sa.Column('job_placement_id',sa.Integer(),sa.ForeignKey('job_placement_logs.id'),nullable=True),
        sa.Column('created_by_id',sa.Integer(),sa.ForeignKey('supporters.id'),nullable=False),
        sa.Column('version',sa.Integer(),nullable=False),
        *[sa.Column(key,sa.Text(),nullable=True) for key in (
            'handover_notes','physical_work_environment','human_work_environment','job_description',
            'contract_wage','holidays','daily_work_hours','break_time','user_needs','special_notes','overall_evaluation')],
        # Existing EncryptedString stores ciphertext in unbounded VARCHAR.
        sa.Column('health_status_notes',sa.String(),nullable=True),
        sa.Column('living_environment_notes',sa.String(),nullable=True),
        sa.Column('evaluation_date',sa.Date(),nullable=True),
        sa.Column('evaluation_author_id',sa.Integer(),sa.ForeignKey('supporters.id'),nullable=True),
        sa.Column('created_at',sa.DateTime(),nullable=False,server_default=sa.func.now()),
        sa.Column('updated_at',sa.DateTime(),nullable=False,server_default=sa.func.now()))
    op.create_index('ix_job_retention_plan_details_job_placement_id','job_retention_plan_details',['job_placement_id'])
    op.create_table('retention_plan_organization_links',
        sa.Column('plan_detail_id',sa.Integer(),sa.ForeignKey('job_retention_plan_details.id'),primary_key=True),
        sa.Column('user_organization_link_id',sa.Integer(),sa.ForeignKey('user_organization_links.id'),primary_key=True))
    op.create_table('job_retention_plan_support_items',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('plan_detail_id',sa.Integer(),sa.ForeignKey('job_retention_plan_details.id'),nullable=False),
        sa.Column('sequence_no',sa.Integer(),nullable=False),
        sa.Column('support_policy_content',sa.Text(),nullable=False),
        sa.Column('start_date',sa.Date(),nullable=False),
        sa.Column('end_date',sa.Date(),nullable=False),
        sa.Column('frequency',sa.Text(),nullable=False),
        sa.Column('implementation_status',sa.String(20),nullable=True),
        sa.Column('achievement_status',sa.String(20),nullable=True),
        sa.Column('effect_satisfaction_notes',sa.Text(),nullable=True),
        sa.Column('remaining_issues_and_actions',sa.Text(),nullable=True),
        sa.Column('deleted_at',sa.DateTime(),nullable=True),
        sa.Column('deleted_by_id',sa.Integer(),sa.ForeignKey('supporters.id'),nullable=True),
        sa.Column('delete_reason',sa.Text(),nullable=True),
        sa.UniqueConstraint('plan_detail_id','sequence_no',name='uq_retention_item_sequence'),
        sa.CheckConstraint('sequence_no > 0',name='ck_retention_item_sequence'),
        sa.CheckConstraint('start_date <= end_date',name='ck_retention_item_period'),
        sa.CheckConstraint("implementation_status IN ('DONE','PARTIAL','NOT_DONE')",name='ck_retention_item_implementation'),
        sa.CheckConstraint("achievement_status IN ('ACHIEVED','PARTIAL','NOT_ACHIEVED')",name='ck_retention_item_achievement'))
    op.create_index('ix_job_retention_plan_support_items_plan_detail_id','job_retention_plan_support_items',['plan_detail_id'])
    with op.batch_alter_table('goal_assessments') as batch:
        batch.add_column(sa.Column('achievement_status',sa.String(20),nullable=True))
        batch.create_check_constraint('ck_goal_assessment_achievement',"achievement_status IN ('ACHIEVED','PARTIAL','NOT_ACHIEVED')")


def downgrade():
    # Downgrade would erase signed content and evaluation history.
    raise RuntimeError('Retention content downgrade requires a reviewed data-preservation procedure.')
