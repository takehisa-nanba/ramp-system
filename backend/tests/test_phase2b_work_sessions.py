# backend/tests/test_phase2b_work_sessions.py

import pytest
import os
import threading
from datetime import datetime, date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from backend.app import create_app, db
from backend.config import Config
from backend.app.models import (
    Supporter, OfficeSetting, Corporation, MunicipalityMaster, StatusMaster, User,
    SupporterTimecard, StaffActivityMaster, StaffActivityAllocationLog, OfficeServiceConfiguration
)
from backend.app.services.attendance_service import AttendanceService
from backend.app.services.daily_log_service import DailyLogService
from backend.app.domain.attendance.exceptions import AttendanceConflictError

# PostgreSQL test DB URL
PG_TEST_DB_URL = os.environ.get('SQLALCHEMY_DATABASE_URI', 'postgresql://postgres:postgres@localhost:5432/ramp_db_test_phase2b')

class Phase2BTestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = PG_TEST_DB_URL

@pytest.fixture(scope='module')
def app():
    app = create_app(Phase2BTestConfig)
    with app.app_context():
        # Clean up data before testing
        db.session.execute(db.text("TRUNCATE TABLE staff_activity_allocation_logs CASCADE"))
        db.session.execute(db.text("TRUNCATE TABLE supporter_timecards CASCADE"))
        db.session.execute(db.text("TRUNCATE TABLE staff_activity_master CASCADE"))
        db.session.execute(db.text("TRUNCATE TABLE office_service_configurations CASCADE"))
        db.session.execute(db.text("TRUNCATE TABLE supporters CASCADE"))
        db.session.execute(db.text("TRUNCATE TABLE office_settings CASCADE"))
        db.session.execute(db.text("TRUNCATE TABLE corporations CASCADE"))
        db.session.execute(db.text("TRUNCATE TABLE municipality_master CASCADE"))
        db.session.commit()
        yield app

@pytest.fixture(scope='module')
def engine():
    engine = create_engine(PG_TEST_DB_URL, pool_size=10, max_overflow=20)
    yield engine
    engine.dispose()

@pytest.fixture(scope='module')
def setup_data(app):
    with app.app_context():
        # Setup basic masters
        corp = Corporation(corporation_name="Test Corp", corporation_type="KK")
        db.session.add(corp)
        db.session.flush()

        muni = MunicipalityMaster(municipality_code="111111", name="Test City")
        db.session.add(muni)
        db.session.flush()

        office = OfficeSetting(
            corporation_id=corp.id, office_name="Test Office", 
            municipality_id=muni.id, full_time_weekly_minutes=2400
        )
        db.session.add(office)
        db.session.flush()
        
        from backend.app.models import ServiceTypeMaster
        service_type = db.session.query(ServiceTypeMaster).filter_by(service_code="TEST-001").first()
        if not service_type:
            service_type = ServiceTypeMaster(name="TEST Service", service_code="TEST-001", required_review_months=6)
            db.session.add(service_type)
            db.session.flush()

        osc = OfficeServiceConfiguration(
            office_id=office.id, 
            service_type_master_id=service_type.id, 
            jigyosho_bango="1234567890",
            capacity=20,
            default_start_time="09:00", 
            default_end_time="18:00"
        )
        db.session.add(osc)
        db.session.flush()

        supporter = Supporter(
            staff_code="T001", last_name="Test", first_name="Staff",
            last_name_kana="テスト", first_name_kana="スタッフ",
            office_id=office.id, employment_type="FULL_TIME", 
            weekly_scheduled_minutes=2400, hire_date=date(2025, 1, 1)
        )
        db.session.add(supporter)
        db.session.flush()

        tag = StaffActivityMaster(activity_name="Direct Support Test", is_direct_support=False)
        db.session.add(tag)

        from backend.app.models import JobTitleMaster, SupporterJobAssignment
        job_title = db.session.query(JobTitleMaster).filter_by(title_name="Test Job").first()
        if not job_title:
            job_title = JobTitleMaster(title_name="Test Job")
            db.session.add(job_title)
            db.session.flush()

        assignment1 = SupporterJobAssignment(
            supporter_id=supporter.id,
            job_title_id=job_title.id,
            office_service_configuration_id=osc.id,
            start_date=date(2025, 1, 1),
            assigned_minutes=2400
        )
        db.session.add(assignment1)



        db.session.commit()
        return {
            "supporter_id": supporter.id,
            "office_id": office.id,
            "tag_id": tag.id,
            "osc_id": osc.id
        }

def test_concurrent_clock_in(app, engine, setup_data):
    """
    Test concurrent clock_in requests to ensure safe sequence_no generation 
    and no multiple ongoing timecards.
    """
    supporter_id = setup_data['supporter_id']
    office_id = setup_data['office_id']

    Session = scoped_session(sessionmaker(bind=engine))
    
    results = []
    def worker():
        session = Session()
        try:
            svc = AttendanceService(session)
            timecard = svc.clock_in(supporter_id, office_id, "OFFICE", "Concurrent Test")
            session.commit()
            results.append("SUCCESS")
        except Exception as e:
            session.rollback()
            results.append(f"ERROR: {str(e)}")
        finally:
            Session.remove()

    threads = []
    for _ in range(5):
        t = threading.Thread(target=worker)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Verify results: Only 1 SUCCESS, others should be 409 Conflict
    successes = [r for r in results if r == "SUCCESS"]
    assert len(successes) == 1, f"Expected 1 success, got: {results}"
    
    with app.app_context():
        ongoing = SupporterTimecard.query.filter_by(supporter_id=supporter_id, check_out=None).all()
        assert len(ongoing) == 1, "There should be exactly 1 ongoing timecard"
        
        # Clock out to clean up
        svc = AttendanceService(db.session)
        svc.clock_out(supporter_id, timecard_id=ongoing[0].id, break_minutes=0)
        db.session.commit()

def test_overlapping_time_range_allocations(app, setup_data):
    """
    Test activity allocation overlap validation.
    """
    supporter_id = setup_data['supporter_id']
    office_id = setup_data['office_id']
    tag_id = setup_data['tag_id']

    with app.app_context():
        svc_att = AttendanceService(db.session)
        svc_dl = DailyLogService()
        
        now = datetime.now()
        
        # Clock in manually (simulating a bit in the past)
        tc = SupporterTimecard(
            supporter_id=supporter_id,
            work_date=now.date(),
            office_id=office_id,
            office_service_configuration_id=setup_data['osc_id'],
            location_type="OFFICE",
            sequence_no=100,
            check_in=now - timedelta(hours=2),
            check_out=now
        )
        db.session.add(tc)
        db.session.commit()
        
        # Add first allocation: 1 hour ago to 30 mins ago
        start1 = now - timedelta(hours=1)
        end1 = now - timedelta(minutes=30)
        
        alloc1 = svc_dl.record_activity_allocation(supporter_id, {
            "allocation_recording_mode": "TIME_RANGE",
            "supporter_timecard_id": tc.id,
            "staff_activity_master_id": tag_id,
            "allocation_start_time": start1.isoformat() + "+09:00",
            "allocation_end_time": end1.isoformat() + "+09:00"
        })
        db.session.commit()
        
        # Attempt to add overlapping allocation: 45 mins ago to 15 mins ago
        start2 = now - timedelta(minutes=45)
        end2 = now - timedelta(minutes=15)
        
        with pytest.raises(AttendanceConflictError) as excinfo:
            svc_dl.record_activity_allocation(supporter_id, {
                "allocation_recording_mode": "TIME_RANGE",
                "supporter_timecard_id": tc.id,
                "staff_activity_master_id": tag_id,
                "allocation_start_time": start2.isoformat() + "+09:00",
                "allocation_end_time": end2.isoformat() + "+09:00"
            })
        assert "overlaps" in str(excinfo.value), "Should raise overlap error"
        
        db.session.rollback()

def test_minutes_only_allocation(app, setup_data):
    """
    Test MINUTES_ONLY allocation.
    """
    supporter_id = setup_data['supporter_id']
    office_id = setup_data['office_id']
    tag_id = setup_data['tag_id']

    with app.app_context():
        svc_dl = DailyLogService()
        
        now = datetime.now()
        tc = SupporterTimecard(
            supporter_id=supporter_id,
            work_date=now.date(),
            office_id=office_id,
            office_service_configuration_id=setup_data['osc_id'],
            location_type="OFFICE",
            sequence_no=200,
            check_in=now - timedelta(hours=2),
            check_out=now
        )
        db.session.add(tc)
        db.session.commit()
        alloc = svc_dl.record_activity_allocation(supporter_id, {
            "allocation_recording_mode": "MINUTES_ONLY",
            "supporter_timecard_id": tc.id,
            "staff_activity_master_id": tag_id,
            "allocated_minutes": 15
        })
        db.session.commit()
        
        assert alloc.allocated_minutes == 15
        assert alloc.allocated_duration_seconds == 900
        assert alloc.allocation_start_time is None
        assert alloc.allocation_end_time is None
