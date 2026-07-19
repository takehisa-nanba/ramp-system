from unittest.mock import patch
import pytest
import os
from datetime import datetime, date, timedelta
from backend.app import create_app, db
from backend.config import Config
from backend.app.models import (
    Supporter, OfficeSetting, Corporation, MunicipalityMaster, SupporterTimecard, OfficeServiceConfiguration
)
from flask_jwt_extended import create_access_token

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
        
        # Another office for permission tests
        office2 = OfficeSetting(
            corporation_id=corp.id, office_name="Other Office", 
            municipality_id=muni.id, full_time_weekly_minutes=2400
        )
        db.session.add(office2)
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

        supporter = Supporter(
            staff_code="T001", last_name="Test", first_name="Staff",
            last_name_kana="test", first_name_kana="staff",
            office_id=office.id, employment_type="FULL_TIME", 
            weekly_scheduled_minutes=2400, hire_date=date(2025, 1, 1)
        )
        db.session.add(supporter)
        
        supporter2 = Supporter(
            staff_code="T002", last_name="Other", first_name="Staff",
            last_name_kana="XXXXXX", first_name_kana="XXXXXXX",
            office_id=office.id, employment_type="FULL_TIME", 
            weekly_scheduled_minutes=2400, hire_date=date(2025, 1, 1)
        )
        db.session.add(supporter2)

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

        assignment2 = SupporterJobAssignment(
            supporter_id=supporter2.id,
            job_title_id=job_title.id,
            office_service_configuration_id=osc.id,
            start_date=date(2025, 1, 1),
            assigned_minutes=2400
        )
        db.session.add(assignment2)

        db.session.commit()

        return {
            "supporter_id": supporter.id,
            "other_supporter_id": supporter2.id,
            "office_id": office.id,
            "other_office_id": office2.id,
            "osc_id": osc.id
        }

@pytest.fixture
def auth_headers(app, setup_data):
    with app.app_context():
        token = create_access_token(identity=f"staff:{setup_data['supporter_id']}")
        return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def auth_headers_other(app, setup_data):
    with app.app_context():
        token = create_access_token(identity=f"staff:{setup_data['other_supporter_id']}")
        return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def auth_headers_manager(app, setup_data):
    with app.app_context():
        token = create_access_token(identity="manager:1")
        return {"Authorization": f"Bearer {token}"}

def test_clock_in_invalid_location_type(app, auth_headers, setup_data):
    client = app.test_client()
    resp = client.post('/api/attendance/clock-in', headers=auth_headers, json={
        "office_id": setup_data['office_id'],
        "location_type": "INVALID_LOCATION"
    })
    assert resp.status_code == 400
    data = resp.get_json()
    assert "Invalid location_type" in data.get("msg", "")

def test_clock_in_unauthorized_office(app, auth_headers, setup_data):
    client = app.test_client()
    with app.app_context():
        from backend.app.models import SupporterJobAssignment
        assignments = db.session.query(SupporterJobAssignment).all()
        print(f"\nALL ASSIGNMENTS: {[(a.id, a.supporter_id, a.office_service_configuration_id, a.start_date, a.end_date) for a in assignments]}")
        from backend.app.models.core.office import OfficeServiceConfiguration
        oscs = db.session.query(OfficeServiceConfiguration).all()
        print(f"ALL OSCS: {[(o.id, o.office_id) for o in oscs]}")
        from datetime import datetime
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo("Asia/Tokyo")).replace(tzinfo=None)
        today = now.date()
        print(f"TODAY: {today}")

    resp = client.post('/api/attendance/clock-in', headers=auth_headers, json={
        "office_id": setup_data['other_office_id'],
        "location_type": "OFFICE"
    })
    
    assert resp.status_code == 403

def test_old_dashboard_clock_in_success(app, auth_headers):
    client = app.test_client()
    resp = client.post('/api/dashboard/staff/clock-in', headers=auth_headers, json={
        "latitude": 35.0,
        "longitude": 135.0,
        "location_accuracy": 10.0
    })
    assert resp.status_code == 201
    assert "timecard_id" in resp.get_json()

def test_old_dashboard_clock_in_no_office_candidate(app, auth_headers):
    # Create a supporter with NO valid offices
    from backend.app.models import Supporter
    from backend.app import db
    from flask_jwt_extended import create_access_token
    from datetime import date
    
    with app.app_context():
        # Get corp and office from setup but don't link them
        supporter = Supporter(
            staff_code="T_NO_OFFICE", last_name="No", first_name="Office",
            last_name_kana="test", first_name_kana="staff",
            office_id=None, employment_type="FULL_TIME", 
            weekly_scheduled_minutes=2400, hire_date=date(2025, 1, 1)
        )
        db.session.add(supporter)
        db.session.commit()
        token = create_access_token(identity=f"staff:{supporter.id}")
        
    client = app.test_client()
    resp = client.post('/api/dashboard/staff/clock-in', headers={"Authorization": f"Bearer {token}"}, json={})
    assert resp.status_code == 400
    assert "office_id is required or ambiguous" in resp.get_json().get("msg", "")

def test_old_dashboard_clock_in_multiple_office_candidates(app, auth_headers, setup_data):
    from backend.app.models import Supporter, SupporterJobAssignment
    from backend.app import db
    from flask_jwt_extended import create_access_token
    from datetime import date
    
    with app.app_context():
        # Create a supporter with multiple valid offices
        supporter = Supporter(
            staff_code="T_MULTIPLE", last_name="Multi", first_name="Office",
            last_name_kana="multi", first_name_kana="office",
            office_id=setup_data['office_id'], employment_type="FULL_TIME", 
            weekly_scheduled_minutes=2400, hire_date=date(2025, 1, 1)
        )
        db.session.add(supporter)
        db.session.flush()
        
        # Add assignment in other_office_id
        # Wait, assignment needs office_service_configuration_id. Let's assume one exists for other_office_id.
        # But we need an OSC for other_office_id.
        from backend.app.models import OfficeServiceConfiguration, ServiceTypeMaster
        svc_type = ServiceTypeMaster.query.first()
        osc2 = OfficeServiceConfiguration(
            office_id=setup_data['other_office_id'], 
            service_type_master_id=svc_type.id, 
            jigyosho_bango="99999", capacity=20, default_start_time="09:00", default_end_time="18:00"
        )
        db.session.add(osc2)
        db.session.flush()
        
        from backend.app.models import JobTitleMaster
        jt = JobTitleMaster.query.first()
        if not jt:
            jt = JobTitleMaster(title_name="Test")
            db.session.add(jt)
            db.session.flush()
            
        assignment = SupporterJobAssignment(
            supporter_id=supporter.id, office_service_configuration_id=osc2.id, job_title_id=jt.id,
            start_date=date(2025,1,1), end_date=date(2025,12,31), assigned_minutes=2400
        )
        db.session.add(assignment)
        db.session.commit()
        token = create_access_token(identity=f"staff:{supporter.id}")
        
    client = app.test_client()
    resp = client.post('/api/dashboard/staff/clock-in', headers={"Authorization": f"Bearer {token}"}, json={})
    assert resp.status_code == 400
    assert "office_id is required or ambiguous" in resp.get_json().get("msg", "")

@patch('backend.app.services.attendance_service.AttendanceService.get_ongoing_timecard')
def test_old_dashboard_clock_out_no_open_timecard(mock_get, app, auth_headers):
    mock_get.return_value = None
    client = app.test_client()
    resp = client.post('/api/dashboard/staff/clock-out', headers=auth_headers, json={
        "break_minutes": 0
    })
    assert resp.status_code == 404
    assert "Timecard not found" in resp.get_json().get("msg", "")

@patch('backend.app.services.attendance_service.AttendanceService.get_ongoing_timecard')
def test_old_dashboard_clock_out_multiple_open_timecards(mock_get, app, auth_headers, setup_data):
    from backend.app.domain.attendance.exceptions import AttendanceValidationError
    mock_get.side_effect = AttendanceValidationError("Multiple ongoing timecards found")
    client = app.test_client()
    resp = client.post('/api/dashboard/staff/clock-out', headers=auth_headers, json={
        "break_minutes": 0
    })
    assert resp.status_code == 400
    assert "Multiple ongoing timecards found" in resp.get_json().get("msg", "")

def test_clock_out_then_clock_in_increments_sequence(app, auth_headers, setup_data):
    client = app.test_client()
    
    # First get the open timecard from previous test
    # Check current sequence_no
    with app.app_context():
        tc = SupporterTimecard.query.filter_by(supporter_id=setup_data['supporter_id'], check_out=None).first()
        timecard_id = tc.id
        assert tc.sequence_no == 1
    
    # Clock out
    resp = client.post(f'/api/attendance/timecards/{timecard_id}/clock-out', headers=auth_headers, json={
        "break_minutes": 0
    })
    assert resp.status_code == 200

    # Clock in again
    resp = client.post('/api/attendance/clock-in', headers=auth_headers, json={
        "office_id": setup_data['office_id'],
        "location_type": "OFFICE",
        "notes": "Second session"
    })
    assert resp.status_code == 201
    new_tc_id = resp.get_json()['timecard_id']
    
    # Assert sequence_no incremented to 2 explicitly
    with app.app_context():
        tc2 = db.session.get(SupporterTimecard, new_tc_id)
        assert tc2.sequence_no == 2
        
def test_clock_in_conflict(app, auth_headers, setup_data):
    client = app.test_client()
    # Already clocked in from previous test
    resp = client.post('/api/attendance/clock-in', headers=auth_headers, json={
        "office_id": setup_data['office_id'],
        "location_type": "OFFICE"
    })
    assert resp.status_code == 409

def test_clock_out_invalid_break_minutes(app, auth_headers, setup_data):
    client = app.test_client()
    with app.app_context():
        tc = SupporterTimecard.query.filter_by(supporter_id=setup_data['supporter_id'], check_out=None).first()
        tc_id = tc.id
    
    # Negative break minutes
    resp = client.post(f'/api/attendance/timecards/{tc_id}/clock-out', headers=auth_headers, json={
        "break_minutes": -10
    })
    assert resp.status_code == 400

def test_clock_out_other_staff_timecard(app, auth_headers_other, setup_data):
    client = app.test_client()
    # Get timecard of the first staff (via manual DB check)
    with app.app_context():
        tc = SupporterTimecard.query.filter_by(supporter_id=setup_data['supporter_id'], check_out=None).first()
        tc_id = tc.id

    # Try to clock it out using the OTHER staff's token
    resp = client.post(f'/api/attendance/timecards/{tc_id}/clock-out', headers=auth_headers_other, json={
        "break_minutes": 0
    })
    assert resp.status_code == 404

def test_clock_out_already_clocked_out(app, auth_headers, setup_data):
    client = app.test_client()
    with app.app_context():
        tc = SupporterTimecard.query.filter_by(supporter_id=setup_data['supporter_id'], check_out=None).first()
        tc_id = tc.id
    
    # Clock out successfully
    resp = client.post(f'/api/attendance/timecards/{tc_id}/clock-out', headers=auth_headers, json={
        "break_minutes": 0
    })
    assert resp.status_code == 200
    
    # Try again
    resp = client.post(f'/api/attendance/timecards/{tc_id}/clock-out', headers=auth_headers, json={
        "break_minutes": 0
    })
    assert resp.status_code == 409

def test_old_dashboard_clock_out_invalid(app, auth_headers):
    client = app.test_client()
    # Currently 0 ongoing timecards for this supporter
    resp = client.post('/api/dashboard/staff/clock-out', headers=auth_headers, json={
        "latitude": 35.0,
        "longitude": 135.0,
        "location_accuracy": 10.0,
        "break_minutes": 0
    })
    # Should be 404 because there is no open timecard
    assert resp.status_code == 404

def test_get_timecards_auth(app, auth_headers, auth_headers_other, auth_headers_manager, setup_data):
    client = app.test_client()
    
    # Self -> 200
    resp = client.get(f'/api/attendance/timecards?supporter_id={setup_data["supporter_id"]}&date=2025-01-01', headers=auth_headers)
    print("test_get_timecards_auth response:", resp.get_json())
    assert resp.status_code == 200
    
    # Manager -> 403 (because endpoint is staff only)
    resp = client.get(f'/api/attendance/timecards?supporter_id={setup_data["supporter_id"]}&date=2025-01-01', headers=auth_headers_manager)
    assert resp.status_code == 403
    
    # Other staff -> 200 (but returns their own empty list)
    resp = client.get(f'/api/attendance/timecards?supporter_id={setup_data["supporter_id"]}&date=2025-01-01', headers=auth_headers_other)
    assert resp.status_code == 200
    assert resp.get_json() == []

def test_dashboard_status(app, auth_headers):
    client = app.test_client()
    resp = client.get('/api/dashboard/staff/status', headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert "staff_list" in data
    my_status = next(s for s in data["staff_list"] if s["supporter_id"] == data["current_staff_id"])
    assert my_status["status"] in ["NOT_SCHEDULED", "WORKING", "ON_BREAK", "FINISHED"]

def test_attendance_shifts(app, auth_headers):
    client = app.test_client()
    resp = client.get('/api/attendance/shifts?year=2025&month=1', headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    # Should be read-only compatibility and not merge intervals
    if isinstance(data, dict) and "items" in data:
        data = data["items"]
    assert isinstance(data, list)
