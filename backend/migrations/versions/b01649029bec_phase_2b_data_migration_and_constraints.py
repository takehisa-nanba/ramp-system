"""Phase 2B Data Migration and Constraints

Revision ID: b01649029bec
Revises: 26b7aa0c1fd1
Create Date: 2026-07-19 11:16:55.608543

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b01649029bec'
down_revision = '26b7aa0c1fd1'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # --- 異常データの先行検査 ---
    ongoing_counts = conn.execute(sa.text("""
        SELECT supporter_id FROM supporter_timecards
        WHERE check_in IS NOT NULL AND check_out IS NULL
        GROUP BY supporter_id HAVING COUNT(id) > 1
    """)).fetchall()
    if ongoing_counts:
        bad_ids = [str(r[0]) for r in ongoing_counts]
        raise RuntimeError(f"Migration failed: Multiple ongoing timecards found for supporters: {', '.join(bad_ids)}")

    invalid_times = conn.execute(sa.text("""
        SELECT id, supporter_id FROM supporter_timecards
        WHERE check_in IS NOT NULL AND check_out IS NOT NULL AND check_out <= check_in
    """)).fetchall()
    if invalid_times:
        bad_ids = [str(r[0]) for r in invalid_times]
        raise RuntimeError(f"Migration failed: check_out <= check_in found in timecards: {', '.join(bad_ids)}")

    null_keys = conn.execute(sa.text("""
        SELECT id FROM supporter_timecards
        WHERE supporter_id IS NULL OR work_date IS NULL
    """)).fetchall()
    if null_keys:
        bad_ids = [str(r[0]) for r in null_keys]
        raise RuntimeError(f"Migration failed: supporter_id or work_date IS NULL found in timecards: {', '.join(bad_ids)}")

    dup_seq = conn.execute(sa.text("""
        SELECT supporter_id, work_date, sequence_no
        FROM supporter_timecards WHERE sequence_no IS NOT NULL
        GROUP BY supporter_id, work_date, sequence_no HAVING COUNT(id) > 1
    """)).fetchall()
    if dup_seq:
        raise RuntimeError("Migration failed: Duplicate sequence_no found in existing data.")

    # --- sequence_noのバックフィル ---
    conn.execute(sa.text("""
        WITH numbered AS (
            SELECT id, ROW_NUMBER() OVER(
                PARTITION BY supporter_id, work_date 
                ORDER BY check_in ASC NULLS LAST, id ASC
            ) as row_num
            FROM supporter_timecards
        )
        UPDATE supporter_timecards SET sequence_no = numbered.row_num
        FROM numbered WHERE supporter_timecards.id = numbered.id
    """))

    null_seq = conn.execute(sa.text("SELECT id FROM supporter_timecards WHERE sequence_no IS NULL")).fetchall()
    if null_seq:
        raise RuntimeError("Migration failed: sequence_no is still NULL after backfill.")

    dup_seq_after = conn.execute(sa.text("""
        SELECT supporter_id, work_date, sequence_no
        FROM supporter_timecards GROUP BY supporter_id, work_date, sequence_no
        HAVING COUNT(id) > 1
    """)).fetchall()
    if dup_seq_after:
        raise RuntimeError("Migration failed: Duplicate sequence_no created during backfill.")

    # --- 制約の追加 ---
    with op.batch_alter_table('supporter_timecards', schema=None) as batch_op:
        batch_op.alter_column('sequence_no', existing_type=sa.INTEGER(), nullable=False)
        batch_op.create_unique_constraint(batch_op.f('uq_supporter_timecards_supporter_date_seq'), ['supporter_id', 'work_date', 'sequence_no'])

    if conn.engine.name == 'postgresql':
        op.execute("""
            CREATE UNIQUE INDEX uq_supporter_ongoing_timecard 
            ON supporter_timecards (supporter_id) 
            WHERE check_in IS NOT NULL AND check_out IS NULL
        """)

    pass

def downgrade():
    conn = op.get_bind()

    if conn.engine.name == 'postgresql':
        op.execute("DROP INDEX IF EXISTS uq_supporter_ongoing_timecard")

    with op.batch_alter_table('supporter_timecards', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('uq_supporter_timecards_supporter_date_seq'), type_='unique')
        batch_op.alter_column('sequence_no', existing_type=sa.INTEGER(), nullable=True)
        
    pass
