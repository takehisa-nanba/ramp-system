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

def test_attendance_shifts(app, auth_headers, setup_data):
    from backend.app.models import SupporterTimecard
    from backend.app import db
    from datetime import datetime, date

    with app.app_context():
        # Clear existing
        db.session.query(SupporterTimecard).filter_by(
            supporter_id=setup_data['supporter_id'],
            work_date=date(2025, 1, 15)
        ).delete()
        db.session.commit()

        tc1 = SupporterTimecard(
            supporter_id=setup_data['supporter_id'],
            office_id=setup_data['office_id'],
            office_service_configuration_id=setup_data['osc_id'],
            location_type='OFFICE',
            sequence_no=1,
            work_date=date(2025, 1, 15),
            check_in=datetime(2025, 1, 15, 9, 0),
            check_out=datetime(2025, 1, 15, 12, 0),
            total_break_minutes=0
        )
        tc2 = SupporterTimecard(
            supporter_id=setup_data['supporter_id'],
            office_id=setup_data['office_id'],
            office_service_configuration_id=setup_data['osc_id'],
            location_type='OFFICE',
            sequence_no=2,
            work_date=date(2025, 1, 15),
            check_in=datetime(2025, 1, 15, 13, 0),
            check_out=datetime(2025, 1, 15, 17, 0),
            total_break_minutes=45
        )
        db.session.add_all([tc1, tc2])
        db.session.commit()

    client = app.test_client()
    resp = client.get('/api/attendance/shifts?year=2025&month=1', headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    if isinstance(data, dict) and "items" in data:
        data = data["items"]
    assert isinstance(data, list)

    # 2025-01-15 の要素を取得
    items_0115 = [item for item in data if item.get("target_date") == "2025-01-15"]
    assert len(items_0115) == 1, "同日2区間が1日1要素に集約されること"

    item = items_0115[0]
    assert len(item["timecards"]) == 2, "2つのtimecardが含まれること"
    assert [tc["sequence_no"] for tc in item["timecards"]] == [1, 2], "timecards が sequence 順であること"

    assert item["actual_check_in"] == "2025-01-15T09:00:00+09:00", "最早check-in"
    assert item["actual_check_out"] == "2025-01-15T17:00:00+09:00", "最終check-out"
    assert item["total_worked_seconds"] == 22500, "休憩控除後22500秒"


def test_dashboard_today_users_is_isolated_by_corporation(app, setup_data):
    from backend.app import db
    from backend.app.models import (
        Corporation,
        OfficeSetting,
        OfficeServiceConfiguration,
        ServiceCertificate,
        StatusMaster,
        User,
    )
    from backend.app.models.support.attendance_workflow import AttendanceRecord
    from backend.app.utils.timezone import get_jst_today
    from datetime import datetime, time
    from flask_jwt_extended import create_access_token

    with app.app_context():
        today = get_jst_today()
        admin_office = db.session.get(
            OfficeSetting, setup_data["office_id"]
        )
        admin_osc = db.session.get(
            OfficeServiceConfiguration, setup_data["osc_id"]
        )
        status = db.session.query(StatusMaster).first()

        own_user = User(
            display_name="Own Corporation User",
            status_id=status.id,
        )
        other_user = User(
            display_name="Other Corporation User",
            status_id=status.id,
        )
        db.session.add_all([own_user, other_user])
        db.session.flush()

        other_corp = Corporation(
            corporation_name="Today Users Isolation Corp",
            corporation_type="KK",
        )
        db.session.add(other_corp)
        db.session.flush()

        other_office = OfficeSetting(
            corporation_id=other_corp.id,
            office_name="Today Users Isolation Office",
            municipality_id=admin_office.municipality_id,
            full_time_weekly_minutes=2400,
        )
        db.session.add(other_office)
        db.session.flush()

        other_osc = OfficeServiceConfiguration(
            office_id=other_office.id,
            service_type_master_id=admin_osc.service_type_master_id,
            jigyosho_bango="9999999996",
            capacity=20,
            default_start_time="09:00",
            default_end_time="18:00",
        )
        db.session.add(other_osc)
        db.session.flush()

        own_certificate = ServiceCertificate(
            user_id=own_user.id,
            certificate_issue_date=today,
            municipality_master_id=admin_office.municipality_id,
            office_service_configuration_id=admin_osc.id,
            status="ACTIVE",
        )
        other_certificate = ServiceCertificate(
            user_id=other_user.id,
            certificate_issue_date=today,
            municipality_master_id=admin_office.municipality_id,
            office_service_configuration_id=other_osc.id,
            status="ACTIVE",
        )
        db.session.add_all([own_certificate, other_certificate])

        own_check_in = AttendanceRecord(
            user_id=own_user.id,
            record_type="CHECK_IN",
            timestamp=datetime.combine(today, time(9, 0)),
        )
        other_check_in = AttendanceRecord(
            user_id=other_user.id,
            record_type="CHECK_IN",
            timestamp=datetime.combine(today, time(9, 30)),
        )
        db.session.add_all([own_check_in, other_check_in])
        db.session.commit()

        own_user_id = own_user.id
        other_user_id = other_user.id

        token = create_access_token(
            identity=f"staff:{setup_data['supporter_id']}",
            additional_claims={"role_scopes": ["CORPORATE"]},
        )
        headers = {"Authorization": f"Bearer {token}"}

    client = app.test_client()
    response = client.get(
        "/api/dashboard/today-users",
        headers=headers,
    )

    assert response.status_code == 200
    data = response.get_json()
    returned_user_ids = {
        item["user_id"] for item in data["items"]
    }

    assert own_user_id in returned_user_ids
    assert other_user_id not in returned_user_ids

def test_dashboard_summary_is_isolated_by_corporation(app, setup_data):
    from backend.app import db
    from backend.app.models import (
        Corporation,
        OfficeSetting,
        OfficeServiceConfiguration,
        ServiceCertificate,
        StatusMaster,
        User,
    )
    from backend.app.models.support.attendance_workflow import AttendanceRecord
    from backend.app.utils.timezone import get_jst_today
    from datetime import datetime, time
    from flask_jwt_extended import create_access_token

    with app.app_context():
        token = create_access_token(
            identity=f"staff:{setup_data['supporter_id']}",
            additional_claims={"role_scopes": ["CORPORATE"]},
        )
        headers = {"Authorization": f"Bearer {token}"}

    client = app.test_client()
    baseline_response = client.get(
        "/api/dashboard/summary",
        headers=headers,
    )
    assert baseline_response.status_code == 200
    baseline_today_users = baseline_response.get_json()["today_users"]

    with app.app_context():
        today = get_jst_today()
        admin_office = db.session.get(
            OfficeSetting, setup_data["office_id"]
        )
        admin_osc = db.session.get(
            OfficeServiceConfiguration, setup_data["osc_id"]
        )
        status = db.session.query(StatusMaster).first()

        own_user = User(
            display_name="Summary Own Corporation User",
            status_id=status.id,
        )
        other_user = User(
            display_name="Summary Other Corporation User",
            status_id=status.id,
        )
        db.session.add_all([own_user, other_user])
        db.session.flush()

        other_corp = Corporation(
            corporation_name="Summary Isolation Corp",
            corporation_type="KK",
        )
        db.session.add(other_corp)
        db.session.flush()

        other_office = OfficeSetting(
            corporation_id=other_corp.id,
            office_name="Summary Isolation Office",
            municipality_id=admin_office.municipality_id,
            full_time_weekly_minutes=2400,
        )
        db.session.add(other_office)
        db.session.flush()

        other_osc = OfficeServiceConfiguration(
            office_id=other_office.id,
            service_type_master_id=admin_osc.service_type_master_id,
            jigyosho_bango="9999999995",
            capacity=20,
            default_start_time="09:00",
            default_end_time="18:00",
        )
        db.session.add(other_osc)
        db.session.flush()

        db.session.add_all([
            ServiceCertificate(
                user_id=own_user.id,
                certificate_issue_date=today,
                municipality_master_id=admin_office.municipality_id,
                office_service_configuration_id=admin_osc.id,
                status="ACTIVE",
            ),
            ServiceCertificate(
                user_id=other_user.id,
                certificate_issue_date=today,
                municipality_master_id=admin_office.municipality_id,
                office_service_configuration_id=other_osc.id,
                status="ACTIVE",
            ),
            AttendanceRecord(
                user_id=own_user.id,
                record_type="CHECK_IN",
                timestamp=datetime.combine(today, time(10, 0)),
            ),
            AttendanceRecord(
                user_id=other_user.id,
                record_type="CHECK_IN",
                timestamp=datetime.combine(today, time(10, 30)),
            ),
        ])
        db.session.commit()

    response = client.get(
        "/api/dashboard/summary",
        headers=headers,
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["today_users"] == baseline_today_users + 1

@pytest.mark.parametrize("invalid_identity", [
    "manager:1",
    "staff:01",
    "staff:１",
    "staff-1",
    "staff:1:2",
])
def test_attendance_shifts_rejects_invalid_jwt_identity(app, invalid_identity):
    from flask_jwt_extended import create_access_token

    with app.app_context():
        token = create_access_token(
            identity=invalid_identity,
            additional_claims={"role_scopes": ["CORPORATE"]},
        )
        headers = {"Authorization": f"Bearer {token}"}

    client = app.test_client()
    response = client.get(
        "/api/attendance/shifts",
        headers=headers,
    )

    assert response.status_code == 403

def test_corporate_admin_cannot_view_other_corporation_shifts(app, setup_data):
    from backend.app.models import SupporterTimecard, Corporation, OfficeSetting, OfficeServiceConfiguration, Supporter
    from backend.app import db
    from datetime import datetime, date
    from flask_jwt_extended import create_access_token

    with app.app_context():
        # setup_dataのsupporterをCORPORATE管理者として使用
        admin_supporter_id = setup_data['supporter_id']
        admin_office_id = setup_data['office_id']
        admin_osc_id = setup_data['osc_id']

        admin_office = db.session.get(OfficeSetting, admin_office_id)
        admin_osc = db.session.get(OfficeServiceConfiguration, admin_osc_id)

        # 既存法人とは別のCorporation、OfficeSetting、OfficeServiceConfiguration、Supporterを作成
        other_corp = Corporation(corporation_name="Other Test Corp 2", corporation_type="KK")
        db.session.add(other_corp)
        db.session.flush()

        other_office = OfficeSetting(
            corporation_id=other_corp.id, office_name="Other Test Office 2",
            municipality_id=admin_office.municipality_id, full_time_weekly_minutes=2400
        )
        db.session.add(other_office)
        db.session.flush()

        other_osc = OfficeServiceConfiguration(
            office_id=other_office.id,
            service_type_master_id=admin_osc.service_type_master_id,
            jigyosho_bango="9999999998",
            capacity=20,
            default_start_time="09:00",
            default_end_time="18:00"
        )
        db.session.add(other_osc)
        db.session.flush()

        other_supporter = Supporter(
            staff_code="T009_OTHER", last_name="Other", first_name="Staff",
            last_name_kana="アザー", first_name_kana="スタッフ",
            office_id=other_office.id, employment_type="FULL_TIME",
            weekly_scheduled_minutes=2400, hire_date=date(2025, 1, 1)
        )
        db.session.add(other_supporter)
        db.session.flush()
        other_supporter_id = other_supporter.id

        # 2025-02-15にTimecardを1件ずつ作成
        target_date = date(2025, 2, 15)

        tc_admin = SupporterTimecard(
            supporter_id=admin_supporter_id,
            office_id=admin_office_id,
            office_service_configuration_id=admin_osc_id,
            location_type='OFFICE',
            sequence_no=1,
            work_date=target_date,
            check_in=datetime(2025, 2, 15, 9, 0),
            check_out=datetime(2025, 2, 15, 12, 0)
        )

        tc_other = SupporterTimecard(
            supporter_id=other_supporter_id,
            office_id=other_office.id,
            office_service_configuration_id=other_osc.id,
            location_type='OFFICE',
            sequence_no=1,
            work_date=target_date,
            check_in=datetime(2025, 2, 15, 10, 0),
            check_out=datetime(2025, 2, 15, 15, 0)
        )

        db.session.add_all([tc_admin, tc_other])
        db.session.commit()

        # CORPORATE管理者のJWTを作成
        token = create_access_token(
            identity=f"staff:{admin_supporter_id}",
            additional_claims={"role_scopes": ["CORPORATE"]}
        )
        auth_headers = {"Authorization": f"Bearer {token}"}

    client = app.test_client()
    resp = client.get('/api/attendance/shifts?year=2025&month=2', headers=auth_headers)

    assert resp.status_code == 200
    data = resp.get_json()
    if isinstance(data, dict) and "items" in data:
        items = data["items"]
    else:
        items = data

    supporter_ids = [item.get("supporter_id") for item in items if "supporter_id" in item]

    assert admin_supporter_id in supporter_ids, "Admin's own timecard should be returned"
    assert other_supporter_id not in supporter_ids, "Other corporation's timecard should NOT be returned"


def test_corporate_admin_without_office_is_forbidden(app):
    from backend.app.models import Supporter
    from backend.app import db
    from datetime import date
    from flask_jwt_extended import create_access_token

    with app.app_context():
        supporter = Supporter(
            staff_code="T_NO_OFC_CLOSED", last_name="No", first_name="Office",
            last_name_kana="ノー", first_name_kana="オフィス",
            office_id=None, employment_type="FULL_TIME",
            weekly_scheduled_minutes=2400, hire_date=date(2025, 1, 1)
        )
        db.session.add(supporter)
        db.session.flush()
        supporter_id = supporter.id
        db.session.commit()

        token = create_access_token(
            identity=f"staff:{supporter_id}",
            additional_claims={"role_scopes": ["CORPORATE"]}
        )
        auth_headers = {"Authorization": f"Bearer {token}"}

    client = app.test_client()
    resp = client.get('/api/attendance/shifts?year=2025&month=2', headers=auth_headers)

    assert resp.status_code == 403
    data = resp.get_json()
    assert data is not None, "Response JSON should not be None"
    assert "Supporter or office not found for corporate admin" in data.get("msg", ""), "Expected error message not found in msg field"


def test_system_scope_does_not_expand_corporate_tenant_access(app, setup_data):
    from backend.app.models import SupporterTimecard, Corporation, OfficeSetting, OfficeServiceConfiguration, Supporter
    from backend.app import db
    from datetime import datetime, date
    from flask_jwt_extended import create_access_token

    with app.app_context():
        # setup_dataのsupporterを管理者として使用
        admin_supporter_id = setup_data['supporter_id']
        admin_office_id = setup_data['office_id']
        admin_osc_id = setup_data['osc_id']

        # 既存のOfficeSettingとOfficeServiceConfigurationを取得
        admin_office = db.session.get(OfficeSetting, admin_office_id)
        admin_osc = db.session.get(OfficeServiceConfiguration, admin_osc_id)

        # 既存法人とは別のCorporation、OfficeSetting、OfficeServiceConfiguration、Supporterを作成
        other_corp = Corporation(corporation_name="Other Test Corp 3", corporation_type="KK")
        db.session.add(other_corp)
        db.session.flush()

        other_office = OfficeSetting(
            corporation_id=other_corp.id, office_name="Other Test Office 3",
            municipality_id=admin_office.municipality_id, full_time_weekly_minutes=2400
        )
        db.session.add(other_office)
        db.session.flush()

        other_osc = OfficeServiceConfiguration(
            office_id=other_office.id,
            service_type_master_id=admin_osc.service_type_master_id,
            jigyosho_bango="9999999997",
            capacity=20,
            default_start_time="09:00",
            default_end_time="18:00"
        )
        db.session.add(other_osc)
        db.session.flush()

        other_supporter = Supporter(
            staff_code="T010_OTHER", last_name="Other2", first_name="Staff2",
            last_name_kana="アザーニ", first_name_kana="スタッフニ",
            office_id=other_office.id, employment_type="FULL_TIME",
            weekly_scheduled_minutes=2400, hire_date=date(2025, 1, 1)
        )
        db.session.add(other_supporter)
        db.session.flush()
        other_supporter_id = other_supporter.id

        # 2025-04-15にTimecardを1件ずつ作成
        target_date = date(2025, 4, 15)

        tc_admin = SupporterTimecard(
            supporter_id=admin_supporter_id,
            office_id=admin_office_id,
            office_service_configuration_id=admin_osc_id,
            location_type='OFFICE',
            sequence_no=1,
            work_date=target_date,
            check_in=datetime(2025, 4, 15, 9, 0),
            check_out=datetime(2025, 4, 15, 12, 0)
        )

        tc_other = SupporterTimecard(
            supporter_id=other_supporter_id,
            office_id=other_office.id,
            office_service_configuration_id=other_osc.id,
            location_type='OFFICE',
            sequence_no=1,
            work_date=target_date,
            check_in=datetime(2025, 4, 15, 10, 0),
            check_out=datetime(2025, 4, 15, 15, 0)
        )

        db.session.add_all([tc_admin, tc_other])
        db.session.commit()

        # SYSTEM と CORPORATE の両方を持つJWTを作成
        token = create_access_token(
            identity=f"staff:{admin_supporter_id}",
            additional_claims={"role_scopes": ["SYSTEM", "CORPORATE"]}
        )
        auth_headers = {"Authorization": f"Bearer {token}"}

    client = app.test_client()
    resp = client.get('/api/attendance/shifts?year=2025&month=4', headers=auth_headers)

    assert resp.status_code == 200
    data = resp.get_json()
    if isinstance(data, dict) and "items" in data:
        items = data["items"]
    else:
        items = data

    supporter_ids = [item.get("supporter_id") for item in items if "supporter_id" in item]

    assert admin_supporter_id in supporter_ids, "Admin's own timecard should be returned"
    assert other_supporter_id not in supporter_ids, "Other corporation's timecard should NOT be returned"


def test_attendance_shifts_with_ongoing_segment(app, auth_headers, setup_data):
    from backend.app.models import SupporterTimecard
    from backend.app import db
    from datetime import datetime, date

    with app.app_context():
        # テスト開始時に既存の該当日のtimecardを削除
        db.session.query(SupporterTimecard).filter_by(
            supporter_id=setup_data['supporter_id'],
            work_date=date(2025, 5, 15)
        ).delete()
        db.session.commit()

        tc1 = SupporterTimecard(
            supporter_id=setup_data['supporter_id'],
            office_id=setup_data['office_id'],
            office_service_configuration_id=setup_data['osc_id'],
            location_type='OFFICE',
            sequence_no=1,
            work_date=date(2025, 5, 15),
            check_in=datetime(2025, 5, 15, 9, 0),
            check_out=datetime(2025, 5, 15, 12, 0),
            total_break_minutes=30
        )
        tc2 = SupporterTimecard(
            supporter_id=setup_data['supporter_id'],
            office_id=setup_data['office_id'],
            office_service_configuration_id=setup_data['osc_id'],
            location_type='OFFICE',
            sequence_no=2,
            work_date=date(2025, 5, 15),
            check_in=datetime(2025, 5, 15, 13, 0),
            check_out=None,
            total_break_minutes=0
        )
        db.session.add_all([tc1, tc2])
        db.session.commit()

    client = app.test_client()
    resp = client.get('/api/attendance/shifts?year=2025&month=5', headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()

    if isinstance(data, dict) and "items" in data:
        data = data["items"]

    items = [item for item in data if item["target_date"] == "2025-05-15"]
    assert len(items) == 1

    item = items[0]
    assert len(item["timecards"]) == 2
    assert [tc["sequence_no"] for tc in item["timecards"]] == [1, 2]
    assert item["actual_check_in"] == "2025-05-15T09:00:00+09:00"
    assert item["actual_check_out"] is None
    assert item["total_worked_seconds"] == 9000


def test_dashboard_staff_status_is_isolated_by_corporation(app, setup_data):
    from backend.app.models import Corporation, OfficeSetting, Supporter
    from backend.app import db
    from datetime import date
    from flask_jwt_extended import create_access_token

    with app.app_context():
        admin_office = db.session.get(
            OfficeSetting, setup_data["office_id"]
        )

        other_corp = Corporation(
            corporation_name="Dashboard Isolation Corp",
            corporation_type="KK",
        )
        db.session.add(other_corp)
        db.session.flush()

        other_office = OfficeSetting(
            corporation_id=other_corp.id,
            office_name="Dashboard Isolation Office",
            municipality_id=admin_office.municipality_id,
            full_time_weekly_minutes=2400,
        )
        db.session.add(other_office)
        db.session.flush()

        other_supporter = Supporter(
            staff_code="T_DASH_OTHER",
            last_name="Other",
            first_name="Corporation",
            last_name_kana="アザー",
            first_name_kana="コーポレーション",
            office_id=other_office.id,
            employment_type="FULL_TIME",
            weekly_scheduled_minutes=2400,
            hire_date=date(2025, 1, 1),
            is_active=True,
        )
        db.session.add(other_supporter)
        db.session.commit()

        other_supporter_id = other_supporter.id
        token = create_access_token(
            identity=f"staff:{setup_data['supporter_id']}",
            additional_claims={"role_scopes": ["CORPORATE"]},
        )
        headers = {"Authorization": f"Bearer {token}"}

    client = app.test_client()
    response = client.get(
        "/api/dashboard/staff/status",
        headers=headers,
    )

    assert response.status_code == 200
    data = response.get_json()
    supporter_ids = {
        staff["supporter_id"] for staff in data["staff_list"]
    }

    assert setup_data["supporter_id"] in supporter_ids
    assert setup_data["other_supporter_id"] in supporter_ids
    assert other_supporter_id not in supporter_ids




def test_allocate_activity_invalid_identity(app):
    from flask_jwt_extended import create_access_token
    from backend.app.models.core.supporter import StaffActivityAllocationLog
    from backend.app.extensions import db
    
    with app.app_context():
        token = create_access_token(identity="invalid:123", additional_claims={"role_scopes": ["JOB"]})
        client = app.test_client()
        
        initial_count = db.session.query(StaffActivityAllocationLog).count()
        
        payload = {
            "supporter_timecard_id": 1,
            "office_service_configuration_id": 1,
            "job_title_id": 1,
            "staff_activity_master_id": 1,
            "allocation_recording_mode": "MANUAL"
        }
        
        res = client.post('/api/activities/allocations', json=payload, headers={'Authorization': f'Bearer {token}'})
        assert res.status_code == 403
        
        final_count = db.session.query(StaffActivityAllocationLog).count()
        assert initial_count == final_count

def test_allocate_activity_null_ids(app, setup_data):
    from flask_jwt_extended import create_access_token
    from backend.app.models.core.supporter import StaffActivityAllocationLog
    from backend.app.extensions import db
    
    creator_id = setup_data['supporter_id']
    
    with app.app_context():
        token = create_access_token(identity=f"staff:{creator_id}", additional_claims={"role_scopes": ["SYSTEM_SELF"]})
        client = app.test_client()
        
        initial_count = db.session.query(StaffActivityAllocationLog).count()
        
        payload1 = {
            "supporter_timecard_id": 1,
            "office_service_configuration_id": None,
            "job_title_id": 1,
            "staff_activity_master_id": 1,
            "allocation_recording_mode": "MINUTES_ONLY",
            "allocated_minutes": 30
        }
        
        res1 = client.post('/api/activities/allocations', json=payload1, headers={'Authorization': f'Bearer {token}'})
        assert res1.status_code == 400
        assert "Invalid value for field: office_service_configuration_id" in str(res1.get_json())
        
        payload2 = {
            "supporter_timecard_id": 1,
            "office_service_configuration_id": 1,
            "job_title_id": None,
            "staff_activity_master_id": 1,
            "allocation_recording_mode": "MINUTES_ONLY",
            "allocated_minutes": 30
        }
        
        res2 = client.post('/api/activities/allocations', json=payload2, headers={'Authorization': f'Bearer {token}'})
        assert res2.status_code == 400
        assert "Invalid value for field: job_title_id" in str(res2.get_json())
        
        final_count = db.session.query(StaffActivityAllocationLog).count()
        assert initial_count == final_count
