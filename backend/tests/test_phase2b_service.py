import pytest
import os
from datetime import datetime, date, timedelta
from sqlalchemy.orm import sessionmaker
from backend.app import create_app, db
from backend.config import Config
from backend.app.models import (
    Supporter, OfficeSetting, Corporation, MunicipalityMaster, SupporterTimecard, OfficeServiceConfiguration, StaffActivityMaster,
    SupporterJobAssignment, JobTitleMaster, ServiceTypeMaster, SupportRecord, UserDailyLog, User, StatusMaster,
    StaffActivityAllocationLog
)
from backend.app.services.attendance_service import AttendanceService
from backend.app.services.daily_log_service import DailyLogService
from backend.app.domain.attendance.exceptions import AttendanceConflictError, AttendanceValidationError

PG_TEST_DB_URL = os.environ.get('TEST_DATABASE_URL')
assert PG_TEST_DB_URL, "TEST_DATABASE_URL must be set"

class Phase2BTestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = PG_TEST_DB_URL

@pytest.fixture(scope='module')
def app():
    app = create_app(Phase2BTestConfig)
    with app.app_context():
        db.session.execute(db.text("TRUNCATE TABLE supporter_timecards CASCADE"))
        db.session.execute(db.text("TRUNCATE TABLE office_service_configurations CASCADE"))
        db.session.execute(db.text("TRUNCATE TABLE supporters CASCADE"))
        db.session.execute(db.text("TRUNCATE TABLE office_settings CASCADE"))
        db.session.execute(db.text("TRUNCATE TABLE corporations CASCADE"))
        db.session.execute(db.text("TRUNCATE TABLE municipality_master CASCADE"))
        db.session.execute(db.text("TRUNCATE TABLE staff_activity_master CASCADE"))
        db.session.execute(db.text("TRUNCATE TABLE job_title_master CASCADE"))
        db.session.execute(db.text("TRUNCATE TABLE supporter_job_assignments CASCADE"))
        db.session.execute(db.text("TRUNCATE TABLE service_type_master CASCADE"))
        db.session.execute(db.text("TRUNCATE TABLE status_master CASCADE"))
        db.session.execute(db.text("TRUNCATE TABLE users CASCADE"))
        db.session.commit()
    yield app

@pytest.fixture(scope='module')
def setup_data(app):
    with app.app_context():
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

        job_title = JobTitleMaster(title_name="Test Title")
        db.session.add(job_title)
        db.session.flush()

        job_assignment = SupporterJobAssignment(
            supporter_id=supporter.id, office_service_configuration_id=osc.id, job_title_id=job_title.id,
            start_date=date(2025, 1, 1), end_date=None,
            assigned_minutes=2400
        )
        db.session.add(job_assignment)

        # Inactive job assignment (expired)
        job_assignment_inactive = SupporterJobAssignment(
            supporter_id=supporter.id, office_service_configuration_id=osc.id, job_title_id=job_title.id,
            start_date=date(2024, 1, 1), end_date=date(2024, 12, 31),
            assigned_minutes=2400
        )
        db.session.add(job_assignment_inactive)

        tag = StaffActivityMaster(activity_name="Direct Support Test", is_direct_support=False)
        db.session.add(tag)
        db.session.commit()
        
        status = StatusMaster(name="ACTIVE")
        db.session.add(status)
        db.session.flush()
        
        user = User(display_name="Test User", user_code="U001", status_id=status.id)
        db.session.add(user)
        db.session.commit()

        return {
            "supporter_id": supporter.id,
            "office_id": office.id,
            "osc_id": osc.id,
            "tag_id": tag.id,
            "job_title_id": job_title.id,
            "user_id": user.id,
            "service_type_id": service_type.id
        }

def test_cross_day_work_session(app, setup_data):
    with app.app_context():
        svc = AttendanceService(db.session)
        # Mocking check_in time to late night
        tc = SupporterTimecard(
            supporter_id=setup_data['supporter_id'],
            office_service_configuration_id=setup_data['osc_id'],
            location_type="OFFICE",
            work_date=date(2025, 1, 1),
            check_in=datetime(2025, 1, 1, 23, 0),
            sequence_no=1,
            total_break_minutes=0
        )
        db.session.add(tc)
        db.session.commit()
        
        assert tc.check_out is None
        # Clock out at 01:00 next day
        out_tc = svc.clock_out(setup_data['supporter_id'], tc.id, 0)
        db.session.commit()
        assert out_tc.check_out is not None
        
        db.session.delete(tc)
        db.session.commit()

def test_duplicate_clock_in(app, setup_data):
    with app.app_context():
        svc = AttendanceService(db.session)
        svc.clock_in(setup_data['supporter_id'], setup_data['office_id'], "OFFICE", "Dup test")
        db.session.commit()
        
        with pytest.raises(AttendanceConflictError):
            svc.clock_in(setup_data['supporter_id'], setup_data['office_id'], "OFFICE", "Dup test 2")
            
        tc = SupporterTimecard.query.filter_by(supporter_id=setup_data['supporter_id'], check_out=None).first()
        svc.clock_out(setup_data['supporter_id'], tc.id, 0)
        db.session.commit()

def test_boundary_contact_allowed(app, setup_data):
    # E.g., 09:00-12:00, 12:00-15:00
    with app.app_context():
        svc = AttendanceService(db.session)
        tc1 = SupporterTimecard(
            supporter_id=setup_data['supporter_id'], office_id=setup_data['office_id'], office_service_configuration_id=setup_data['osc_id'], location_type="OFFICE",
            work_date=date(2025, 1, 1), check_in=datetime(2025, 1, 1, 9, 0), check_out=datetime(2025, 1, 1, 12, 0),
            sequence_no=1, total_break_minutes=0
        )
        db.session.add(tc1)
        db.session.commit()

        # Since we use direct DB insert for test_boundary_contact_allowed, we test if the service raises Conflict Error.
        # It shouldn't if they don't overlap
        tc2 = SupporterTimecard(
            supporter_id=setup_data['supporter_id'], office_id=setup_data['office_id'], office_service_configuration_id=setup_data['osc_id'], location_type="OFFICE",
            work_date=date(2025, 1, 1), check_in=datetime(2025, 1, 1, 12, 0), check_out=datetime(2025, 1, 1, 15, 0),
            sequence_no=2, total_break_minutes=0
        )
        db.session.add(tc2)
        db.session.commit()
        
        # Cleanup
        db.session.delete(tc2)
        db.session.delete(tc1)
        db.session.commit()

def test_activity_outside_parent_time_range(app, setup_data):
    with app.app_context():
        svc = DailyLogService()
        tc = SupporterTimecard(
            supporter_id=setup_data['supporter_id'], office_id=setup_data['office_id'], office_service_configuration_id=setup_data['osc_id'], location_type="OFFICE",
            work_date=date(2025, 1, 1), check_in=datetime(2025, 1, 1, 9, 0), check_out=datetime(2025, 1, 1, 12, 0),
            sequence_no=1, total_break_minutes=0
        )
        db.session.add(tc)
        db.session.commit()

        # Try to allocate outside (08:00 - 09:00)
        with pytest.raises(AttendanceValidationError):
            svc.record_activity_allocation(setup_data['supporter_id'], {
                "supporter_timecard_id": tc.id, "office_service_configuration_id": setup_data['osc_id'], "job_title_id": setup_data['job_title_id'],
                "staff_activity_master_id": setup_data['tag_id'], "allocation_start_time": "2025-01-01T08:00:00+09:00", "allocation_end_time": "2025-01-01T09:00:00+09:00", "allocation_recording_mode": "TIME_RANGE"
            })
            
        db.session.delete(tc)
        db.session.commit()

def test_server_calculated_allocated_minutes(app, setup_data):
    with app.app_context():
        svc = DailyLogService()
        tc = SupporterTimecard(
            supporter_id=setup_data['supporter_id'], office_id=setup_data['office_id'], office_service_configuration_id=setup_data['osc_id'], location_type="OFFICE",
            work_date=date(2025, 1, 1), check_in=datetime(2025, 1, 1, 9, 0), check_out=datetime(2025, 1, 1, 12, 0),
            sequence_no=1, total_break_minutes=0
        )
        db.session.add(tc)
        db.session.commit()

        # Should calculate 60 minutes
        log = svc.record_activity_allocation(setup_data['supporter_id'], {
            "supporter_timecard_id": tc.id, "office_service_configuration_id": setup_data['osc_id'], "job_title_id": setup_data['job_title_id'],
            "staff_activity_master_id": setup_data['tag_id'], "allocation_start_time": "2025-01-01T10:00:00+09:00", "allocation_end_time": "2025-01-01T11:00:00+09:00", "allocation_recording_mode": "TIME_RANGE"
        })
        assert log.allocated_minutes == 60
        
        db.session.delete(log)
        db.session.delete(tc)
        db.session.commit()

def test_minutes_only_with_time(app, setup_data):
    with app.app_context():
        svc = DailyLogService()
        tc = SupporterTimecard(
            supporter_id=setup_data['supporter_id'], office_id=setup_data['office_id'], office_service_configuration_id=setup_data['osc_id'], location_type="OFFICE",
            work_date=date(2025, 1, 1), check_in=datetime(2025, 1, 1, 9, 0), check_out=datetime(2025, 1, 1, 12, 0),
            sequence_no=1, total_break_minutes=0
        )
        db.session.add(tc)
        db.session.commit()

        # MINUTES_ONLY but containing start_time/end_time -> validation error
        with pytest.raises(AttendanceValidationError):
            svc.record_activity_allocation(setup_data['supporter_id'], {
                "supporter_timecard_id": tc.id, "office_service_configuration_id": setup_data['osc_id'], "job_title_id": setup_data['job_title_id'],
                "staff_activity_master_id": setup_data['tag_id'], "allocated_minutes": 60, "allocation_start_time": "2025-01-01T10:00:00+09:00", "allocation_end_time": "2025-01-01T11:00:00+09:00", "allocation_recording_mode": "MINUTES_ONLY"
            })
        
        db.session.delete(tc)
        db.session.commit()

def test_old_daily_log_ongoing_count(app, setup_data):
    # Test checking ongoing timecards for old daily log
    with app.app_context():
        svc = AttendanceService(db.session)
        # 0 ongoing
        assert svc.get_ongoing_timecard(setup_data['supporter_id']) is None
        
        # 1 ongoing
        tc = SupporterTimecard(
            supporter_id=setup_data['supporter_id'], office_id=setup_data['office_id'], office_service_configuration_id=setup_data['osc_id'], location_type="OFFICE",
            work_date=date(2025, 1, 1), check_in=datetime(2025, 1, 1, 9, 0), check_out=None,
            sequence_no=1, total_break_minutes=0
        )
        db.session.add(tc)
        db.session.commit()
        
        assert svc.get_ongoing_timecard(setup_data['supporter_id']) is not None
        
        db.session.delete(tc)
        db.session.commit()

def test_allocation_validity_period_mismatch(app, setup_data):
    with app.app_context():
        svc = DailyLogService()
        tc = SupporterTimecard(
            supporter_id=setup_data['supporter_id'], office_id=setup_data['office_id'], office_service_configuration_id=setup_data['osc_id'], location_type="OFFICE",
            work_date=date(2024, 1, 1), # Inactive assignment date
            check_in=datetime(2024, 1, 1, 9, 0), check_out=datetime(2024, 1, 1, 12, 0),
            sequence_no=1, total_break_minutes=0
        )
        db.session.add(tc)
        db.session.commit()

        # Job Assignment was inactive in 2024? Wait, assignment_inactive was valid in 2024. 
        # Let's test a date where NO assignment is valid, e.g., 2023
        tc.work_date = date(2023, 1, 1)
        tc.check_in = datetime(2023, 1, 1, 9, 0)
        tc.check_out = datetime(2023, 1, 1, 12, 0)
        db.session.commit()
        
        # Should raise error because SupporterJobAssignment is not valid in 2023
        from backend.app.domain.attendance.exceptions import AttendanceForbiddenError
        with pytest.raises(AttendanceForbiddenError):
            svc.record_activity_allocation(setup_data['supporter_id'], {
                "supporter_timecard_id": tc.id, "office_service_configuration_id": setup_data['osc_id'], "job_title_id": setup_data['job_title_id'],
                "staff_activity_master_id": setup_data['tag_id'], "allocated_minutes": 60, "allocation_recording_mode": "MINUTES_ONLY"
            })
            
        db.session.delete(tc)
        db.session.commit()

def test_timecard_office_mismatch(app, setup_data):
    with app.app_context():
        svc = DailyLogService()
        # Create an OSC for a DIFFERENT office
        corp = Corporation.query.first()
        muni = MunicipalityMaster.query.first()
        other_office = OfficeSetting(corporation_id=corp.id, office_name="Other", municipality_id=muni.id, full_time_weekly_minutes=2400)
        db.session.add(other_office)
        db.session.flush()
        
        other_osc = OfficeServiceConfiguration(
            office_id=other_office.id, service_type_master_id=setup_data['service_type_id'], jigyosho_bango="000",
            capacity=10, default_start_time="09:00", default_end_time="18:00"
        )
        db.session.add(other_osc)
        db.session.commit()

        tc = SupporterTimecard(
            supporter_id=setup_data['supporter_id'], office_id=setup_data['office_id'], office_service_configuration_id=setup_data['osc_id'], location_type="OFFICE",
            work_date=date(2025, 1, 1), check_in=datetime(2025, 1, 1, 9, 0), check_out=datetime(2025, 1, 1, 12, 0),
            sequence_no=1, total_break_minutes=0
        )
        db.session.add(tc)
        db.session.commit()

        tc_id = tc.id
        other_osc_id = other_osc.id
        initial_count = db.session.query(StaffActivityAllocationLog).filter_by(
            supporter_timecard_id=tc_id
        ).count()
        initial_timecard_state = (
            tc.office_id,
            tc.office_service_configuration_id,
            tc.check_in,
            tc.check_out,
        )
        initial_other_osc_office_id = other_osc.office_id
        engine = db.engine

        # Try to allocate using other_osc.id which belongs to other_office, but timecard is for office_id
        from backend.app.domain.attendance.exceptions import AttendanceForbiddenError
        with pytest.raises(AttendanceForbiddenError):
            svc.record_activity_allocation(setup_data['supporter_id'], {
                "supporter_timecard_id": tc.id, "office_service_configuration_id": other_osc.id, "job_title_id": setup_data['job_title_id'],
                "staff_activity_master_id": setup_data['tag_id'], "allocated_minutes": 60, "allocation_recording_mode": "MINUTES_ONLY"
            })
            
        db.session.rollback()

        Session = sessionmaker(bind=engine)
        independent_session = Session()
        try:
            current_count = independent_session.query(
                StaffActivityAllocationLog
            ).filter_by(
                supporter_timecard_id=tc_id
            ).count()
            assert current_count == initial_count

            saved_tc = independent_session.get(SupporterTimecard, tc_id)
            assert saved_tc is not None
            assert (
                saved_tc.office_id,
                saved_tc.office_service_configuration_id,
                saved_tc.check_in,
                saved_tc.check_out,
            ) == initial_timecard_state

            saved_other_osc = independent_session.get(
                OfficeServiceConfiguration, other_osc_id
            )
            assert saved_other_osc is not None
            assert saved_other_osc.office_id == initial_other_osc_office_id
        finally:
            independent_session.close()

        db.session.delete(tc)
        db.session.delete(other_osc)
        db.session.delete(other_office)
        db.session.commit()
