from flask_jwt_extended import create_access_token
from backend.app import db
from backend.app.models import AttendanceRecord, UserDailyLog


def test_user_day_and_actor_boundaries(app, client, setup_active_user):
    user, staff, _ = setup_active_user
    user_headers = {"Authorization": "Bearer " + create_access_token(identity=f"user:{user.id}")}
    staff_headers = {"Authorization": "Bearer " + create_access_token(identity=f"staff:{staff.id}")}
    assert client.get("/api/user/status").status_code == 401
    assert client.get("/api/user/status", headers=staff_headers).status_code == 403
    assert client.get("/api/records", headers=user_headers).status_code == 403
    assert client.get("/api/records").status_code == 401
    AttendanceRecord.query.filter_by(user_id=user.id).delete()
    UserDailyLog.query.filter_by(user_id=user.id).delete()
    db.session.commit()
    assert client.get("/api/user/status", headers=user_headers).json["attendance_status"] == "IDLE"
    for stamp, expected in [("CHECK_OUT",409), ("CHECK_IN",201), ("CHECK_IN",200), ("CHECK_OUT",201)]:
        assert client.post("/api/user/attendance", json={"type":stamp}, headers=user_headers).status_code == expected
    assert AttendanceRecord.query.filter_by(user_id=user.id).count() == 2
    assert client.post("/api/user/daily-log", json={"physical_condition_score":6}, headers=user_headers).status_code == 400
    assert client.post("/api/user/daily-log", json={"physical_condition_score":4, "user_self_evaluation":"振り返り"}, headers=user_headers).status_code == 200
    status = client.get("/api/user/status", headers=user_headers).json
    assert status["daily_log"]["physical_condition_score"] == 4
    assert status["daily_log"]["user_self_evaluation"] == "振り返り"
    assert status["attendance"]["checked_out"] is True


def test_user_can_only_consent_to_own_approved_revision(app, client, setup_active_user):
    from backend.app.models import SupportPlan, DocumentConsentLog
    from backend.app.utils.timezone import get_jst_today
    user, staff, _ = setup_active_user
    headers = {"Authorization": "Bearer " + create_access_token(identity=f"user:{user.id}")}
    plan = SupportPlan(user_id=user.id, plan_status="PENDING_CONSENT",
                       sabikan_approved_by_id=staff.id, plan_start_date=get_jst_today())
    db.session.add(plan)
    db.session.commit()
    url = f"/api/user/support-plans/{plan.id}/consent"
    document = next(item for item in client.get("/api/user/support-plans", headers=headers).json["items"] if item["id"] == plan.id)
    assert client.post(url, json={"confirmed":False, "revision":document["revision"]}, headers=headers).status_code == 400
    assert client.post(url, json={"confirmed":True, "revision":"0"*64}, headers=headers).status_code == 409
    for _ in range(2):
        assert client.post(url, json={"confirmed":True, "revision":document["revision"]}, headers=headers).status_code == 200
    assert db.session.get(SupportPlan, plan.id).plan_status == "ACTIVE"
    assert DocumentConsentLog.query.filter_by(user_id=user.id, document_type="SUPPORT_PLAN", document_id=plan.id).count() == 1
