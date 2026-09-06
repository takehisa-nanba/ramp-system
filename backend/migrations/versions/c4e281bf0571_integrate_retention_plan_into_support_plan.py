"""integrate retention plan into support plan

Revision ID: c4e281bf0571
Revises: 719c050efff3
Create Date: 2026-09-06 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'c4e281bf0571'
down_revision = '719c050efff3'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    # 1. support_plans への共通カラム追加
    if 'support_plans' in existing_tables:
        cols = {c['name'] for c in insp.get_columns('support_plans')}
        with op.batch_alter_table('support_plans', schema=None) as batch_op:
            if 'office_service_configuration_id' not in cols:
                batch_op.add_column(sa.Column('office_service_configuration_id', sa.Integer(), nullable=True))
                batch_op.create_foreign_key(
                    'fk_support_plans_office_service_config',
                    'office_service_configurations',
                    ['office_service_configuration_id'],
                    ['id']
                )
                batch_op.create_index('ix_support_plans_office_service_config_id', ['office_service_configuration_id'])
            if 'created_by_id' not in cols:
                batch_op.add_column(sa.Column('created_by_id', sa.Integer(), nullable=True))
                batch_op.create_foreign_key(
                    'fk_support_plans_created_by',
                    'supporters',
                    ['created_by_id'],
                    ['id']
                )
            if 'updated_at' not in cols:
                batch_op.add_column(sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=True))

    # 2. long_term_goals / short_term_goals への様式2共通カラム追加
    if 'long_term_goals' in existing_tables:
        cols = {c['name'] for c in insp.get_columns('long_term_goals')}
        with op.batch_alter_table('long_term_goals', schema=None) as batch_op:
            if 'set_year_month' not in cols:
                batch_op.add_column(sa.Column('set_year_month', sa.String(length=7), nullable=True))
            if 'target_year_month' not in cols:
                batch_op.add_column(sa.Column('target_year_month', sa.String(length=7), nullable=True))
            if 'achievement_status' not in cols:
                batch_op.add_column(sa.Column('achievement_status', sa.String(length=20), nullable=True))

    if 'short_term_goals' in existing_tables:
        cols = {c['name'] for c in insp.get_columns('short_term_goals')}
        with op.batch_alter_table('short_term_goals', schema=None) as batch_op:
            if 'set_year_month' not in cols:
                batch_op.add_column(sa.Column('set_year_month', sa.String(length=7), nullable=True))
            if 'target_year_month' not in cols:
                batch_op.add_column(sa.Column('target_year_month', sa.String(length=7), nullable=True))
            if 'achievement_status' not in cols:
                batch_op.add_column(sa.Column('achievement_status', sa.String(length=20), nullable=True))

    # 3. retention_support_plan_details テーブル新規作成
    if 'retention_support_plan_details' not in existing_tables:
        op.create_table(
            'retention_support_plan_details',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('support_plan_id', sa.Integer(), sa.ForeignKey('support_plans.id', ondelete='CASCADE'), nullable=False, unique=True),
            sa.Column('retention_contract_id', sa.Integer(), sa.ForeignKey('job_retention_contracts.id', ondelete='CASCADE'), nullable=False),
            sa.Column('overall_support_goal', sa.Text(), nullable=False),
            sa.Column('review_date', sa.Date(), nullable=True),
            sa.Column('review_reason', sa.Text(), nullable=True),
            sa.Column('user_name', sa.String(length=100), nullable=True),
            sa.Column('user_name_kana', sa.String(length=100), nullable=True),
            sa.Column('gender', sa.String(length=20), nullable=True),
            sa.Column('birth_date', sa.Date(), nullable=True),
            sa.Column('age_at_planning', sa.Integer(), nullable=True),
            sa.Column('support_level', sa.String(length=50), nullable=True),
            sa.Column('disability_handbook_type', sa.String(length=50), nullable=True),
            sa.Column('employer_name', sa.String(length=200), nullable=True),
            sa.Column('employer_industry', sa.String(length=100), nullable=True),
            sa.Column('employer_address', sa.String(length=300), nullable=True),
            sa.Column('employer_tel', sa.String(length=50), nullable=True),
            sa.Column('employer_contact_person', sa.String(length=100), nullable=True),
            sa.Column('job_start_date', sa.Date(), nullable=True),
            sa.Column('work_content', sa.Text(), nullable=True),
            sa.Column('employment_type', sa.String(length=100), nullable=True),
            sa.Column('wage_condition', sa.String(length=200), nullable=True),
            sa.Column('holiday_condition', sa.String(length=200), nullable=True),
            sa.Column('working_hours_and_break', sa.Text(), nullable=True),
            sa.Column('physical_work_environment', sa.Text(), nullable=True),
            sa.Column('human_work_environment', sa.Text(), nullable=True),
            sa.Column('related_support_organizations', sa.Text(), nullable=True),
            sa.Column('pre_employment_handover', sa.Text(), nullable=True),
            sa.Column('user_wishes', sa.Text(), nullable=True),
            sa.Column('health_condition', sa.Text(), nullable=True),
            sa.Column('living_environment_support', sa.Text(), nullable=True),
            sa.Column('retention_challenges', sa.Text(), nullable=True),
            sa.Column('office_name', sa.String(length=200), nullable=True),
            sa.Column('office_number', sa.String(length=50), nullable=True),
            sa.Column('office_address', sa.String(length=300), nullable=True),
            sa.Column('office_tel', sa.String(length=50), nullable=True),
            sa.Column('office_fax', sa.String(length=50), nullable=True),
            sa.Column('staff_creator_name', sa.String(length=100), nullable=True),
            sa.Column('staff_evaluator_name', sa.String(length=100), nullable=True),
            sa.Column('staff_manager_name', sa.String(length=100), nullable=True),
            sa.Column('staff_service_manager_name', sa.String(length=100), nullable=True),
            sa.Column('staff_job_supporter_name', sa.String(length=100), nullable=True),
            sa.Column('staff_explainer_name', sa.String(length=100), nullable=True),
            sa.Column('explained_date', sa.Date(), nullable=True),
            sa.Column('agreed_date', sa.Date(), nullable=True),
            sa.Column('consent_confirmed', sa.Boolean(), default=False),
            sa.Column('consent_notes', sa.String(length=200), nullable=True),
            sa.Column('evaluation_date', sa.Date(), nullable=True),
            sa.Column('overall_evaluation', sa.Text(), nullable=True),
            sa.Column('special_notes', sa.Text(), nullable=True),
            sa.Column('internal_employer_wishes', sa.Text(), nullable=True),
            sa.Column('internal_overall_policy', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        )
        op.create_index('ix_retention_plan_details_contract_id', 'retention_support_plan_details', ['retention_contract_id'])
        op.create_index('ix_retention_plan_details_support_plan_id', 'retention_support_plan_details', ['support_plan_id'])

    # 4. retention_support_plan_items テーブル新規作成
    if 'retention_support_plan_items' not in existing_tables:
        op.create_table(
            'retention_support_plan_items',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('detail_id', sa.Integer(), sa.ForeignKey('retention_support_plan_details.id', ondelete='CASCADE'), nullable=False),
            sa.Column('short_term_goal_id', sa.Integer(), sa.ForeignKey('short_term_goals.id', ondelete='SET NULL'), nullable=True),
            sa.Column('item_number', sa.Integer(), nullable=False),
            sa.Column('challenge_topic', sa.String(length=200), nullable=True),
            sa.Column('support_policy', sa.Text(), nullable=True),
            sa.Column('support_content', sa.Text(), nullable=True),
            sa.Column('support_period_start', sa.Date(), nullable=True),
            sa.Column('support_period_end', sa.Date(), nullable=True),
            sa.Column('support_frequency', sa.String(length=100), nullable=True),
            sa.Column('role_sharing', sa.Text(), nullable=True),
            sa.Column('implementation_status', sa.String(length=20), nullable=True),
            sa.Column('achievement_status', sa.String(length=20), nullable=True),
            sa.Column('effectiveness_satisfaction', sa.Text(), nullable=True),
            sa.Column('remaining_challenges', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
            sa.UniqueConstraint('detail_id', 'item_number', name='uq_retention_detail_item_number')
        )
        op.create_index('ix_retention_plan_items_detail_id', 'retention_support_plan_items', ['detail_id'])
        op.create_index('ix_retention_plan_items_stg_id', 'retention_support_plan_items', ['short_term_goal_id'])

    # 5. retention_support_plan_source_links テーブル新規作成
    if 'retention_support_plan_source_links' not in existing_tables:
        op.create_table(
            'retention_support_plan_source_links',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('detail_id', sa.Integer(), sa.ForeignKey('retention_support_plan_details.id', ondelete='CASCADE'), nullable=False),
            sa.Column('plan_item_id', sa.Integer(), sa.ForeignKey('retention_support_plan_items.id', ondelete='CASCADE'), nullable=True),
            sa.Column('target_field', sa.String(length=100), nullable=False),
            sa.Column('source_type', sa.String(length=50), nullable=False),
            sa.Column('source_id', sa.Integer(), nullable=True),
            sa.Column('excerpt_text', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )
        op.create_index('ix_retention_plan_source_links_detail_id', 'retention_support_plan_source_links', ['detail_id'])
        op.create_index('ix_retention_plan_source_links_item_id', 'retention_support_plan_source_links', ['plan_item_id'])

    # 6. 第1段階 データ移行 (旧 retention_support_plans -> SupportPlan + RetentionSupportPlanDetail + Goals)
    if 'retention_support_plans' in existing_tables:
        old_plans = bind.execute(
            sa.text("SELECT id, contract_id, version, overall_support_goal, start_date, review_date, review_reason, plan_end_date, status, created_by_id, created_at, updated_at FROM retention_support_plans ORDER BY id ASC")
        ).fetchall()

        for old in old_plans:
            old_id = old[0]
            contract_id = old[1]
            version = old[2]
            goal = old[3]
            start_date = old[4]
            review_date = old[5]
            review_reason = old[6]
            plan_end_date = old[7]
            status = old[8] # 'ACTIVE' or 'ARCHIVED'
            created_by_id = old[9]
            created_at = old[10] or datetime.now()
            updated_at = old[11] or datetime.now()

            # 契約から user_id と office_service_configuration_id を取得
            contract_row = bind.execute(
                sa.text("SELECT user_id, office_service_configuration_id FROM job_retention_contracts WHERE id = :cid"),
                {"cid": contract_id}
            ).fetchone()

            if not contract_row:
                continue

            user_id = contract_row[0]
            office_service_config_id = contract_row[1]

            # SupportPlan へ移行 (plan_status は既存体系: 'ACTIVE' or 'ARCHIVED')
            res = bind.execute(
                sa.text(
                    "INSERT INTO support_plans (user_id, plan_version, plan_status, plan_start_date, plan_end_date, created_by_id, office_service_configuration_id, created_at, updated_at) "
                    "VALUES (:user_id, :version, :status, :start_date, :end_date, :created_by_id, :config_id, :created_at, :updated_at)"
                ),
                {
                    "user_id": user_id,
                    "version": version,
                    "status": status,
                    "start_date": start_date,
                    "end_date": plan_end_date,
                    "created_by_id": created_by_id,
                    "config_id": office_service_config_id,
                    "created_at": created_at,
                    "updated_at": updated_at
                }
            )
            # 最後に挿入された support_plan_id を取得
            support_plan_id = bind.execute(sa.text("SELECT id FROM support_plans WHERE user_id = :uid AND plan_version = :ver AND office_service_configuration_id = :cid ORDER BY id DESC LIMIT 1"),
                {"uid": user_id, "ver": version, "cid": office_service_config_id}
            ).scalar()

            # RetentionSupportPlanDetail 作成 (overall_support_goal のみ事実として移行、架空のGoalやItemは作成しない)
            bind.execute(
                sa.text(
                    "INSERT INTO retention_support_plan_details (support_plan_id, retention_contract_id, overall_support_goal, review_date, review_reason, created_at, updated_at) "
                    "VALUES (:sp_id, :rc_id, :goal, :rdate, :rreason, :created_at, :updated_at)"
                ),
                {
                    "sp_id": support_plan_id,
                    "rc_id": contract_id,
                    "goal": goal,
                    "rdate": review_date,
                    "rreason": review_reason,
                    "created_at": created_at,
                    "updated_at": updated_at
                }
            )


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    if 'retention_support_plan_details' in existing_tables and 'support_plans' in existing_tables:
        # 移行された support_plans (およびcascadeする目標) をクリーンアップ
        sp_ids = bind.execute(sa.text("SELECT support_plan_id FROM retention_support_plan_details")).fetchall()
        if sp_ids:
            ids = [str(r[0]) for r in sp_ids]
            bind.execute(sa.text(f"DELETE FROM long_term_goals WHERE plan_id IN ({','.join(ids)})"))
            bind.execute(sa.text(f"DELETE FROM support_plans WHERE id IN ({','.join(ids)})"))

    if 'retention_support_plan_source_links' in existing_tables:
        op.drop_table('retention_support_plan_source_links')

    if 'retention_support_plan_items' in existing_tables:
        op.drop_table('retention_support_plan_items')

    if 'retention_support_plan_details' in existing_tables:
        op.drop_table('retention_support_plan_details')

    if 'short_term_goals' in existing_tables:
        with op.batch_alter_table('short_term_goals', schema=None) as batch_op:
            batch_op.drop_column('achievement_status')
            batch_op.drop_column('target_year_month')
            batch_op.drop_column('set_year_month')

    if 'long_term_goals' in existing_tables:
        with op.batch_alter_table('long_term_goals', schema=None) as batch_op:
            batch_op.drop_column('achievement_status')
            batch_op.drop_column('target_year_month')
            batch_op.drop_column('set_year_month')

    if 'support_plans' in existing_tables:
        indexes = {idx['name'] for idx in insp.get_indexes('support_plans')}
        with op.batch_alter_table('support_plans', schema=None) as batch_op:
            for idx_name in [
                'ix_support_plans_office_service_config_id',
                'ix_support_plans_office_service_configuration_id'
            ]:
                if idx_name in indexes:
                    try:
                        batch_op.drop_index(idx_name)
                    except Exception:
                        pass
            batch_op.drop_column('updated_at')
            batch_op.drop_column('created_by_id')
            batch_op.drop_column('office_service_configuration_id')
