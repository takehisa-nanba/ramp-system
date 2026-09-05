"""enforce_retention_not_null_and_report_unique

Revision ID: 84c9effb5337
Revises: 2fc9a9dc480c
Create Date: 2026-09-05 10:42:18.021190

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '84c9effb5337'
down_revision = '2fc9a9dc480c'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    # 1. NULL契約チェック (推測backfill禁止・存在時は例外で停止)
    if 'job_retention_contracts' in existing_tables:
        null_contracts = bind.execute(
            sa.text("SELECT id FROM job_retention_contracts WHERE office_service_configuration_id IS NULL")
        ).fetchall()
        if null_contracts:
            ids = [str(r[0]) for r in null_contracts]
            raise RuntimeError(
                f"Migration aborted: job_retention_contracts with NULL office_service_configuration_id exist: {', '.join(ids)}. Manual assignment required."
            )

    # 2. 既存重複月次レポートチェック (自動統合・削除禁止・存在時は例外で停止)
    if 'monthly_retention_reports' in existing_tables:
        duplicates = bind.execute(
            sa.text(
                "SELECT contract_id, report_year_month, count(*) "
                "FROM monthly_retention_reports "
                "GROUP BY contract_id, report_year_month "
                "HAVING count(*) > 1"
            )
        ).fetchall()
        if duplicates:
            dup_info = [f"(contract_id={r[0]}, year_month='{r[1]}', count={r[2]})" for r in duplicates]
            raise RuntimeError(
                f"Migration aborted: duplicate monthly_retention_reports exist: {', '.join(dup_info)}. Manual deduplication required."
            )

    # 3. office_service_configuration_id NOT NULL化
    if 'job_retention_contracts' in existing_tables:
        with op.batch_alter_table('job_retention_contracts', schema=None) as batch_op:
            batch_op.alter_column('office_service_configuration_id', nullable=False)

    # 4. (contract_id, report_year_month) UNIQUE追加
    if 'monthly_retention_reports' in existing_tables:
        with op.batch_alter_table('monthly_retention_reports', schema=None) as batch_op:
            batch_op.create_unique_constraint(
                'uq_monthly_retention_report_contract_month',
                ['contract_id', 'report_year_month']
            )


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    # 1. (contract_id, report_year_month) UNIQUE解除
    if 'monthly_retention_reports' in existing_tables:
        with op.batch_alter_table('monthly_retention_reports', schema=None) as batch_op:
            batch_op.drop_constraint('uq_monthly_retention_report_contract_month', type_='unique')

    # 2. office_service_configuration_id nullableへ戻す
    if 'job_retention_contracts' in existing_tables:
        with op.batch_alter_table('job_retention_contracts', schema=None) as batch_op:
            batch_op.alter_column('office_service_configuration_id', nullable=True)
