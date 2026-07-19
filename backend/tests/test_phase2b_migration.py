import pytest
import os
import subprocess
from sqlalchemy import create_engine, text

PG_MIGRATION_DB_URL = os.environ.get('MIGRATION_TEST_DATABASE_URL')
assert PG_MIGRATION_DB_URL, "MIGRATION_TEST_DATABASE_URL must be set"
assert PG_MIGRATION_DB_URL.startswith("postgresql"), "Must be PostgreSQL"
assert "test" in PG_MIGRATION_DB_URL.lower() and "phase2b_migration_isolated" in PG_MIGRATION_DB_URL.lower(), "Must use isolated test phase 2b migration DB"

ALEMBIC_INI = "backend/alembic.ini"
MIGRATIONS_DIR = "backend/migrations"
PHASE_2A_REV = "26b7aa0c1fd1"
PHASE_2B_REV = "b01649029bec"

@pytest.fixture(scope="function", autouse=True)
def setup_teardown_migration_db():
    default_db = "/".join(PG_MIGRATION_DB_URL.split("/")[:-1]) + "/postgres"
    engine = create_engine(default_db, isolation_level="AUTOCOMMIT")
    db_name = PG_MIGRATION_DB_URL.split("/")[-1]
    
    with engine.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {db_name}"))
        conn.execute(text(f"CREATE DATABASE {db_name}"))
    
    yield
    
    with engine.connect() as conn:
        conn.execute(text(f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{db_name}' AND pid <> pg_backend_pid()"))
        conn.execute(text(f"DROP DATABASE IF EXISTS {db_name}"))

def run_alembic(command, target=None):
    from pathlib import Path
    root_dir = str(Path(__file__).parent.parent.parent.resolve())
    cmd = ["flask", "db", command, "-d", MIGRATIONS_DIR]
    if target:
        cmd.append(target)
    env = os.environ.copy()
    env["DATABASE_URL"] = PG_MIGRATION_DB_URL
    env["FLASK_APP"] = "backend.app:create_app"
    result = subprocess.run(cmd, env=env, capture_output=True, text=True, cwd=root_dir)
    return result

def get_current_revision():
    engine = create_engine(PG_MIGRATION_DB_URL)
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            row = result.fetchone()
            return row[0] if row else None
    except:
        return None

def insert_phase2a_parent_records(conn):
    conn.execute(text("INSERT INTO corporations (id, corporation_name, corporation_type, is_active) VALUES (1, 'Test Corp', 'KK', true)"))
    conn.execute(text("INSERT INTO municipality_master (id, municipality_code, name) VALUES (1, '111111', 'Test City')"))
    conn.execute(text("INSERT INTO office_settings (id, corporation_id, office_name, municipality_id, full_time_weekly_minutes, is_active) VALUES (1, 1, 'Test Office', 1, 2400, true)"))
    conn.execute(text("INSERT INTO service_type_master (id, name, service_code, required_review_months) VALUES (1, 'TEST', 'T01', 6)"))
    conn.execute(text("INSERT INTO office_service_configurations (id, office_id, service_type_master_id, jigyosho_bango, capacity, default_start_time, default_end_time) VALUES (1, 1, 1, '1234567890', 20, '09:00', '18:00')"))
    conn.execute(text("INSERT INTO supporters (id, staff_code, last_name, first_name, last_name_kana, first_name_kana, office_id, employment_type, weekly_scheduled_minutes, hire_date, is_active, allow_overlap_calculation) VALUES (1, 'T01', 'Test', 'Staff', 'test', 'staff', 1, 'FULL_TIME', 2400, '2025-01-01', true, false)"))

def test_upgrade_rejects_multiple_open_timecards():
    run_alembic("upgrade", PHASE_2A_REV)
    
    engine = create_engine(PG_MIGRATION_DB_URL)
    with engine.connect() as conn:
        insert_phase2a_parent_records(conn)
        conn.execute(text("""
            INSERT INTO supporter_timecards (supporter_id, office_id, office_service_configuration_id, location_type, work_date, check_in, check_out, total_break_minutes, scheduled_work_minutes)
            VALUES 
            (1, 1, 1, 'OFFICE', '2025-01-01', '2025-01-01 09:00:00', NULL, 0, 480),
            (1, 1, 1, 'OFFICE', '2025-01-01', '2025-01-01 10:00:00', NULL, 0, 480)
        """))
        conn.commit()

    result = run_alembic("upgrade", PHASE_2B_REV)
    
    assert result.returncode != 0
    assert "Migration failed: Multiple ongoing timecards found for supporters" in result.stderr
    assert get_current_revision() == PHASE_2A_REV
    
    with engine.connect() as conn:
        res = conn.execute(text("SELECT COUNT(*) FROM supporter_timecards WHERE check_out IS NULL"))
        assert res.scalar() == 2

def test_upgrade_rejects_invalid_time_range():
    run_alembic("upgrade", PHASE_2A_REV)
    engine = create_engine(PG_MIGRATION_DB_URL)
    with engine.connect() as conn:
        insert_phase2a_parent_records(conn)
        conn.execute(text("""
            INSERT INTO supporter_timecards (supporter_id, office_id, office_service_configuration_id, location_type, work_date, check_in, check_out, total_break_minutes, scheduled_work_minutes)
            VALUES 
            (1, 1, 1, 'OFFICE', '2025-01-01', '2025-01-01 10:00:00', '2025-01-01 09:00:00', 0, 480)
        """))
        conn.commit()

    result = run_alembic("upgrade", PHASE_2B_REV)
    assert result.returncode != 0
    assert "Migration failed: check_out <= check_in found in timecards" in result.stderr
    assert get_current_revision() == PHASE_2A_REV
    
    with engine.connect() as conn:
        res = conn.execute(text("SELECT check_in, check_out FROM supporter_timecards LIMIT 1"))
        row = res.fetchone()
        assert str(row[0]) == '2025-01-01 10:00:00'
        assert str(row[1]) == '2025-01-01 09:00:00'

def test_upgrade_backfills_sequence_numbers():
    run_alembic("upgrade", PHASE_2A_REV)
    engine = create_engine(PG_MIGRATION_DB_URL)
    with engine.connect() as conn:
        insert_phase2a_parent_records(conn)
        conn.execute(text("""
            INSERT INTO supporter_timecards (supporter_id, office_id, office_service_configuration_id, location_type, work_date, check_in, check_out, total_break_minutes, scheduled_work_minutes)
            VALUES 
            (1, 1, 1, 'OFFICE', '2025-01-01', '2025-01-01 12:00:00', '2025-01-01 13:00:00', 0, 480),
            (1, 1, 1, 'OFFICE', '2025-01-01', '2025-01-01 09:00:00', '2025-01-01 10:00:00', 0, 480),
            (1, 1, 1, 'OFFICE', '2025-01-01', NULL, NULL, 0, 480)
        """))
        conn.commit()

    result = run_alembic("upgrade", PHASE_2B_REV)
    assert result.returncode == 0
    assert get_current_revision() == PHASE_2B_REV
    
    with engine.connect() as conn:
        res = conn.execute(text("SELECT COUNT(*) FROM supporter_timecards WHERE sequence_no IS NULL"))
        assert res.scalar() == 0
        
        res = conn.execute(text("SELECT sequence_no, check_in FROM supporter_timecards ORDER BY sequence_no"))
        rows = res.fetchall()
        assert rows[0][0] == 1 and rows[0][1] is not None
        assert rows[1][0] == 2 and rows[1][1] is not None
        assert rows[2][0] == 3 and rows[2][1] is None

def test_downgrade_removes_only_phase2b_constraints():
    run_alembic("upgrade", PHASE_2B_REV)
    assert get_current_revision() == PHASE_2B_REV
    
    result = run_alembic("downgrade", PHASE_2A_REV)
    assert result.returncode == 0
    assert get_current_revision() == PHASE_2A_REV
    
    engine = create_engine(PG_MIGRATION_DB_URL)
    with engine.connect() as conn:
        res = conn.execute(text("""
            SELECT constraint_name FROM information_schema.table_constraints 
            WHERE table_name='supporter_timecards' AND constraint_name='uq_supporter_timecards_supporter_date_seq'
        """))
        assert res.fetchone() is None
        
        res = conn.execute(text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name='supporter_timecards' AND column_name='check_in'
        """))
        assert res.fetchone() is not None
