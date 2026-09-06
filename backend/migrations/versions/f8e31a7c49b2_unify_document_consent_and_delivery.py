"""unify document consent and delivery logs

Revision ID: f8e31a7c49b2
Revises: c4e281bf0571
Create Date: 2026-09-06 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f8e31a7c49b2'
down_revision = 'c4e281bf0571'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    # 1. office_settings に electronic_document_enabled 追加
    if 'office_settings' in existing_tables:
        cols = {c['name'] for c in insp.get_columns('office_settings')}
        if 'electronic_document_enabled' not in cols:
            with op.batch_alter_table('office_settings', schema=None) as batch_op:
                batch_op.add_column(
                    sa.Column('electronic_document_enabled', sa.Boolean(), nullable=False, server_default=sa.false())
                )

    # 2. users に electronic_document_opt_out 追加
    if 'users' in existing_tables:
        cols = {c['name'] for c in insp.get_columns('users')}
        if 'electronic_document_opt_out' not in cols:
            with op.batch_alter_table('users', schema=None) as batch_op:
                batch_op.add_column(
                    sa.Column('electronic_document_opt_out', sa.Boolean(), nullable=False, server_default=sa.false())
                )

    # 3. support_plans に document_snapshot 追加
    if 'support_plans' in existing_tables:
        cols = {c['name'] for c in insp.get_columns('support_plans')}
        if 'document_snapshot' not in cols:
            with op.batch_alter_table('support_plans', schema=None) as batch_op:
                batch_op.add_column(sa.Column('document_snapshot', sa.JSON(), nullable=True))

    # 4. monthly_retention_reports に document_snapshot 追加
    if 'monthly_retention_reports' in existing_tables:
        cols = {c['name'] for c in insp.get_columns('monthly_retention_reports')}
        if 'document_snapshot' not in cols:
            with op.batch_alter_table('monthly_retention_reports', schema=None) as batch_op:
                batch_op.add_column(sa.Column('document_snapshot', sa.JSON(), nullable=True))

    # 5. document_consent_logs の拡張と backfill
    if 'document_consent_logs' in existing_tables:
        cols = {c['name'] for c in insp.get_columns('document_consent_logs')}
        with op.batch_alter_table('document_consent_logs', schema=None) as batch_op:
            if 'document_version' not in cols:
                batch_op.add_column(sa.Column('document_version', sa.Integer(), nullable=True, server_default='1'))
            if 'action' not in cols:
                batch_op.add_column(sa.Column('action', sa.String(30), nullable=True, server_default='CONSENT'))
            if 'signature_method' not in cols:
                batch_op.add_column(sa.Column('signature_method', sa.String(30), nullable=True, server_default='LEGACY_STAFF_RECORDED'))
            if 'evidence_file_url' not in cols:
                batch_op.add_column(sa.Column('evidence_file_url', sa.String(500), nullable=True))
            if 'recorded_by_supporter_id' not in cols:
                batch_op.add_column(sa.Column('recorded_by_supporter_id', sa.Integer(), sa.ForeignKey('supporters.id', name='fk_doc_consent_logs_recorded_by_supporter_id'), nullable=True))
            if 'recorded_at' not in cols:
                batch_op.add_column(sa.Column('recorded_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))

        # Backfill: SUPPORT_PLAN の実際の plan_version を結合更新
        op.execute("""
            UPDATE document_consent_logs
            SET document_version = (
                SELECT plan_version FROM support_plans WHERE support_plans.id = document_consent_logs.document_id
            )
            WHERE document_type = 'SUPPORT_PLAN'
              AND EXISTS (
                SELECT 1 FROM support_plans WHERE support_plans.id = document_consent_logs.document_id
              )
        """)
        # 結合できなかったもの、またはNULLのものは 1
        op.execute("UPDATE document_consent_logs SET document_version = 1 WHERE document_version IS NULL")
        op.execute("UPDATE document_consent_logs SET action = 'CONSENT' WHERE action IS NULL")
        op.execute("UPDATE document_consent_logs SET signature_method = 'LEGACY_STAFF_RECORDED' WHERE signature_method IS NULL")

        # NOT NULL 化および一時 server_default 削除
        with op.batch_alter_table('document_consent_logs', schema=None) as batch_op:
            batch_op.alter_column('document_version', existing_type=sa.Integer(), nullable=False, server_default=None)
            batch_op.alter_column('action', existing_type=sa.String(30), nullable=False, server_default=None)
            batch_op.alter_column('signature_method', existing_type=sa.String(30), nullable=False, server_default=None)

    # 6. document_delivery_logs テーブル新規作成
    if 'document_delivery_logs' not in existing_tables:
        op.create_table(
            'document_delivery_logs',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('document_type', sa.String(50), nullable=False, index=True),
            sa.Column('document_id', sa.Integer(), nullable=False, index=True),
            sa.Column('document_version', sa.Integer(), nullable=False),
            sa.Column('recipient_user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
            sa.Column('delivery_method', sa.String(20), nullable=False),
            sa.Column('delivered_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('viewed_at', sa.DateTime(), nullable=True),
            sa.Column('delivered_by_supporter_id', sa.Integer(), sa.ForeignKey('supporters.id'), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint(
                'document_type', 'document_id', 'document_version', 'recipient_user_id', 'delivery_method',
                name='uq_doc_delivery_recipient_method'
            )
        )


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    if 'document_delivery_logs' in existing_tables:
        op.drop_table('document_delivery_logs')

    if 'document_consent_logs' in existing_tables:
        with op.batch_alter_table('document_consent_logs', schema=None) as batch_op:
            batch_op.drop_column('recorded_at')
            batch_op.drop_column('recorded_by_supporter_id')
            batch_op.drop_column('evidence_file_url')
            batch_op.drop_column('signature_method')
            batch_op.drop_column('action')
            batch_op.drop_column('document_version')

    if 'monthly_retention_reports' in existing_tables:
        with op.batch_alter_table('monthly_retention_reports', schema=None) as batch_op:
            batch_op.drop_column('document_snapshot')

    if 'support_plans' in existing_tables:
        with op.batch_alter_table('support_plans', schema=None) as batch_op:
            batch_op.drop_column('document_snapshot')

    if 'users' in existing_tables:
        with op.batch_alter_table('users', schema=None) as batch_op:
            batch_op.drop_column('electronic_document_opt_out')

    if 'office_settings' in existing_tables:
        with op.batch_alter_table('office_settings', schema=None) as batch_op:
            batch_op.drop_column('electronic_document_enabled')
