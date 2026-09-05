"""add_job_retention_domain_tables_and_alter_contracts

Revision ID: 2fc9a9dc480c
Revises: b01649029bec
Create Date: 2026-09-05 09:50:24.502331

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision = '2fc9a9dc480c'
down_revision = 'b01649029bec'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    # ------------------------------------------------------------------
    # 1. 既存 job_retention_contracts テーブルの ALTER (新規作成はしない)
    # ------------------------------------------------------------------
    if 'job_retention_contracts' in existing_tables:
        existing_cols = {c['name'] for c in insp.get_columns('job_retention_contracts')}
        with op.batch_alter_table('job_retention_contracts', schema=None) as batch_op:
            if 'office_service_configuration_id' not in existing_cols:
                batch_op.add_column(sa.Column('office_service_configuration_id', sa.Integer(), nullable=True))
                batch_op.create_foreign_key('fk_job_retention_contracts_office_service_config', 'office_service_configurations', ['office_service_configuration_id'], ['id'])
                batch_op.create_index('ix_job_retention_contracts_office_service_configuration_id', ['office_service_configuration_id'], unique=False)
            
            if 'status' not in existing_cols:
                batch_op.add_column(sa.Column('status', sa.String(length=30), nullable=False, server_default='ACTIVE'))
                batch_op.create_index('ix_job_retention_contracts_status', ['status'], unique=False)
            
            if 'is_company_involved' not in existing_cols:
                batch_op.add_column(sa.Column('is_company_involved', sa.Boolean(), nullable=False, server_default=sa.text('false')))
            
            if 'consent_status' not in existing_cols:
                batch_op.add_column(sa.Column('consent_status', sa.String(length=50), nullable=False, server_default='NOT_SET'))
            
            if 'created_at' not in existing_cols:
                batch_op.add_column(sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))
            
            if 'updated_at' not in existing_cols:
                batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))

    # ------------------------------------------------------------------
    # 2. 新規テーブル作成 (存在しない場合のみ)
    # ------------------------------------------------------------------
    # (1) retention_employment_episodes
    if 'retention_employment_episodes' not in existing_tables:
        op.create_table(
            'retention_employment_episodes',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('contract_id', sa.Integer(), nullable=False),
            sa.Column('episode_number', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('employer_id', sa.Integer(), nullable=True),
            sa.Column('workplace_name', sa.String(length=200), nullable=False),
            sa.Column('department_name', sa.String(length=100), nullable=True),
            sa.Column('job_title', sa.String(length=100), nullable=True),
            sa.Column('job_start_date', sa.Date(), nullable=False),
            sa.Column('job_end_date', sa.Date(), nullable=True),
            sa.Column('work_conditions', sa.Text(), nullable=True),
            sa.Column('resignation_reason', sa.Text(), nullable=True),
            sa.Column('previous_episode_id', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(['contract_id'], ['job_retention_contracts.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['employer_id'], ['employer_master.id']),
            sa.ForeignKeyConstraint(['previous_episode_id'], ['retention_employment_episodes.id']),
            sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('retention_employment_episodes', schema=None) as batch_op:
            batch_op.create_index('ix_retention_employment_episodes_contract_id', ['contract_id'], unique=False)
            batch_op.create_index('ix_retention_employment_episodes_employer_id', ['employer_id'], unique=False)

    # (2) retention_user_voice_logs
    if 'retention_user_voice_logs' not in existing_tables:
        op.create_table(
            'retention_user_voice_logs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('contract_id', sa.Integer(), nullable=False),
            sa.Column('logged_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('raw_voice', sa.Text(), nullable=True),
            sa.Column('trouble_point', sa.Text(), nullable=True),
            sa.Column('success_point', sa.Text(), nullable=True),
            sa.Column('self_coping_action', sa.Text(), nullable=True),
            sa.Column('self_coping_result', sa.Text(), nullable=True),
            sa.Column('needs_help', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('help_topic', sa.String(length=200), nullable=True),
            sa.Column('input_channel', sa.String(length=30), nullable=False, server_default='USER_DIRECT'),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(['contract_id'], ['job_retention_contracts.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('retention_user_voice_logs', schema=None) as batch_op:
            batch_op.create_index('ix_retention_user_voice_logs_contract_id', ['contract_id'], unique=False)
            batch_op.create_index('ix_retention_user_voice_logs_logged_at', ['logged_at'], unique=False)
    else:
        existing_cols = {c['name'] for c in insp.get_columns('retention_user_voice_logs')}
        if 'input_channel' not in existing_cols:
            with op.batch_alter_table('retention_user_voice_logs', schema=None) as batch_op:
                batch_op.add_column(sa.Column('input_channel', sa.String(length=30), nullable=False, server_default='USER_DIRECT'))

    # (3) retention_employer_feedback_logs
    if 'retention_employer_feedback_logs' not in existing_tables:
        op.create_table(
            'retention_employer_feedback_logs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('contract_id', sa.Integer(), nullable=False),
            sa.Column('logged_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('contact_person', sa.String(length=100), nullable=True),
            sa.Column('workplace_observation', sa.Text(), nullable=True),
            sa.Column('positive_changes', sa.Text(), nullable=True),
            sa.Column('direct_coordination_status', sa.Text(), nullable=True),
            sa.Column('consultation_topic', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(['contract_id'], ['job_retention_contracts.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('retention_employer_feedback_logs', schema=None) as batch_op:
            batch_op.create_index('ix_retention_employer_feedback_logs_contract_id', ['contract_id'], unique=False)
            batch_op.create_index('ix_retention_employer_feedback_logs_logged_at', ['logged_at'], unique=False)

    # (4) retention_support_action_logs
    if 'retention_support_action_logs' not in existing_tables:
        op.create_table(
            'retention_support_action_logs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('contract_id', sa.Integer(), nullable=False),
            sa.Column('supporter_id', sa.Integer(), nullable=False),
            sa.Column('action_date', sa.Date(), nullable=False),
            sa.Column('has_user_interview', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('interview_method', sa.String(length=30), nullable=True),
            sa.Column('has_company_visit', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('has_coordination', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('has_other_support', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('confirmed_situation', sa.Text(), nullable=False),
            sa.Column('provided_support', sa.Text(), nullable=False),
            sa.Column('user_action_observed', sa.Text(), nullable=True),
            sa.Column('staff_intervention_boundary', sa.Text(), nullable=True),
            sa.Column('next_step', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(['contract_id'], ['job_retention_contracts.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['supporter_id'], ['supporters.id']),
            sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('retention_support_action_logs', schema=None) as batch_op:
            batch_op.create_index('ix_retention_support_action_logs_contract_id', ['contract_id'], unique=False)
            batch_op.create_index('ix_retention_support_action_logs_supporter_id', ['supporter_id'], unique=False)
            batch_op.create_index('ix_retention_support_action_logs_action_date', ['action_date'], unique=False)

    # (5) monthly_retention_reports
    if 'monthly_retention_reports' not in existing_tables:
        op.create_table(
            'monthly_retention_reports',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('contract_id', sa.Integer(), nullable=False),
            sa.Column('report_year_month', sa.String(length=7), nullable=False),
            sa.Column('status', sa.String(length=20), nullable=False, server_default='DRAFT'),
            # 内部整理項目
            sa.Column('interview_records', sa.Text(), nullable=True),
            sa.Column('company_visit_records', sa.Text(), nullable=True),
            sa.Column('work_status_summary', sa.Text(), nullable=True),
            sa.Column('life_status_summary', sa.Text(), nullable=True),
            sa.Column('user_coping_summary', sa.Text(), nullable=True),
            sa.Column('employer_feedback_summary', sa.Text(), nullable=True),
            sa.Column('support_details', sa.Text(), nullable=True),
            sa.Column('future_support_policy', sa.Text(), nullable=True),
            # 公式帳票標準項目
            sa.Column('support_goal', sa.Text(), nullable=True),
            sa.Column('support_content', sa.Text(), nullable=True),
            sa.Column('support_result', sa.Text(), nullable=True),
            sa.Column('future_support_plan', sa.Text(), nullable=True),
            sa.Column('stakeholder_efforts', sa.Text(), nullable=True),
            sa.Column('sharing_notes', sa.Text(), nullable=True),
            sa.Column('created_by_id', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(['contract_id'], ['job_retention_contracts.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['created_by_id'], ['supporters.id']),
            sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('monthly_retention_reports', schema=None) as batch_op:
            batch_op.create_index('ix_monthly_retention_reports_contract_id', ['contract_id'], unique=False)
            batch_op.create_index('ix_monthly_retention_reports_report_year_month', ['report_year_month'], unique=False)
    else:
        existing_cols = {c['name'] for c in insp.get_columns('monthly_retention_reports')}
        official_cols = [
            ('support_goal', sa.Text()),
            ('support_content', sa.Text()),
            ('support_result', sa.Text()),
            ('future_support_plan', sa.Text()),
            ('stakeholder_efforts', sa.Text()),
            ('sharing_notes', sa.Text())
        ]
        with op.batch_alter_table('monthly_retention_reports', schema=None) as batch_op:
            for cname, ctype in official_cols:
                if cname not in existing_cols:
                    batch_op.add_column(sa.Column(cname, ctype, nullable=True))

    # ------------------------------------------------------------------
    # 3. 定着支援専用RBACパーミッションの初期投入
    # ------------------------------------------------------------------
    permissions = [
        ('JOB_RETENTION_VIEW',),
        ('JOB_RETENTION_EDIT',),
        ('JOB_RETENTION_APPROVE',),
    ]
    for (pname,) in permissions:
        exists = bind.execute(sa.text("SELECT id FROM permission_master WHERE name = :name"), {"name": pname}).fetchone()
        if not exists:
            bind.execute(sa.text("INSERT INTO permission_master (name) VALUES (:name)"), {"name": pname})

    # 管理者ロールへの紐付け
    admin_roles = bind.execute(sa.text("SELECT id FROM role_master WHERE is_admin IS TRUE")).fetchall()
    for (role_id,) in admin_roles:
        for (pname,) in permissions:
            perm = bind.execute(sa.text("SELECT id FROM permission_master WHERE name = :name"), {"name": pname}).fetchone()
            if perm:
                link_exists = bind.execute(
                    sa.text("SELECT 1 FROM role_permission_link WHERE role_id = :r AND permission_id = :p"),
                    {"r": role_id, "p": perm[0]}
                ).fetchone()
                if not link_exists:
                    bind.execute(
                        sa.text("INSERT INTO role_permission_link (role_id, permission_id) VALUES (:r, :p)"),
                        {"r": role_id, "p": perm[0]}
                    )


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    # 1. 新規テーブルの削除
    if 'monthly_retention_reports' in existing_tables:
        with op.batch_alter_table('monthly_retention_reports', schema=None) as batch_op:
            batch_op.drop_index('ix_monthly_retention_reports_report_year_month')
            batch_op.drop_index('ix_monthly_retention_reports_contract_id')
        op.drop_table('monthly_retention_reports')

    if 'retention_support_action_logs' in existing_tables:
        with op.batch_alter_table('retention_support_action_logs', schema=None) as batch_op:
            batch_op.drop_index('ix_retention_support_action_logs_action_date')
            batch_op.drop_index('ix_retention_support_action_logs_supporter_id')
            batch_op.drop_index('ix_retention_support_action_logs_contract_id')
        op.drop_table('retention_support_action_logs')

    if 'retention_employer_feedback_logs' in existing_tables:
        with op.batch_alter_table('retention_employer_feedback_logs', schema=None) as batch_op:
            batch_op.drop_index('ix_retention_employer_feedback_logs_logged_at')
            batch_op.drop_index('ix_retention_employer_feedback_logs_contract_id')
        op.drop_table('retention_employer_feedback_logs')

    if 'retention_user_voice_logs' in existing_tables:
        with op.batch_alter_table('retention_user_voice_logs', schema=None) as batch_op:
            batch_op.drop_index('ix_retention_user_voice_logs_logged_at')
            batch_op.drop_index('ix_retention_user_voice_logs_contract_id')
        op.drop_table('retention_user_voice_logs')

    if 'retention_employment_episodes' in existing_tables:
        with op.batch_alter_table('retention_employment_episodes', schema=None) as batch_op:
            batch_op.drop_index('ix_retention_employment_episodes_employer_id')
            batch_op.drop_index('ix_retention_employment_episodes_contract_id')
        op.drop_table('retention_employment_episodes')

    # 2. job_retention_contracts 追加カラムの削除
    if 'job_retention_contracts' in existing_tables:
        existing_cols = {c['name'] for c in insp.get_columns('job_retention_contracts')}
        with op.batch_alter_table('job_retention_contracts', schema=None) as batch_op:
            if 'updated_at' in existing_cols:
                batch_op.drop_column('updated_at')
            if 'created_at' in existing_cols:
                batch_op.drop_column('created_at')
            if 'consent_status' in existing_cols:
                batch_op.drop_column('consent_status')
            if 'is_company_involved' in existing_cols:
                batch_op.drop_column('is_company_involved')
            if 'status' in existing_cols:
                batch_op.drop_index('ix_job_retention_contracts_status')
                batch_op.drop_column('status')
            if 'office_service_configuration_id' in existing_cols:
                # 外部キー制約を動的に特定して削除
                fks = insp.get_foreign_keys('job_retention_contracts')
                for fk in fks:
                    if 'office_service_configuration_id' in fk.get('constrained_columns', []):
                        if fk.get('name'):
                            batch_op.drop_constraint(fk['name'], type_='foreignkey')
                # インデックスの存在確認をして削除
                indexes = {ix['name'] for ix in insp.get_indexes('job_retention_contracts')}
                if 'ix_job_retention_contracts_office_service_configuration_id' in indexes:
                    batch_op.drop_index('ix_job_retention_contracts_office_service_configuration_id')
                batch_op.drop_column('office_service_configuration_id')

    # 3. パーミッション削除
    perm_ids = bind.execute(sa.text("SELECT id FROM permission_master WHERE name LIKE 'JOB_RETENTION_%'")).fetchall()
    for (pid,) in perm_ids:
        bind.execute(sa.text("DELETE FROM role_permission_link WHERE permission_id = :p"), {"p": pid})
    bind.execute(sa.text("DELETE FROM permission_master WHERE name LIKE 'JOB_RETENTION_%'"))
