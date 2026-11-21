from datetime import date, datetime
import pytest
from flask_jwt_extended import create_access_token
from backend.tests.test_retention_core_phase1 import retention
from backend.app.extensions import db
from backend.app.models import UserDailySchedule, UserScheduleRequest, AttendanceRecord, AuditActionLog
from backend.app.services.user_schedule_service import UserScheduleService
from backend.app.utils.errors import ValidationError


def payload():
    return dict(month='2026-10', templates=[dict(day_of_week='Monday', is_scheduled=True,
        start_time='09:00', end_time='15:00')])


def test_preview_and_repeated_create_preserve_existing(retention):
    _, user, staff, *_ = retention
    original = UserDailySchedule(user_id=user.id, date=date(2026,10,5), start_time='10:00',
        end_time='12:00', approval_status='CANCELLED')
    db.session.add(original); db.session.commit()
    service = UserScheduleService()
    result = service.bulk_create_month(user.id, staff.id, payload())
    assert result['created_count'] == 3 and result['skipped_count'] == 1
    assert UserDailySchedule.query.count() == 1
    assert AuditActionLog.query.count() == 0
    result = service.bulk_create_month(user.id, staff.id, payload(), preview=False)
    assert result['created_count'] == 3
    assert original.start_time == '10:00' and original.approval_status == 'CANCELLED'
    assert UserDailySchedule.query.count() == 4
    assert service.bulk_create_month(user.id, staff.id, payload(), preview=False)['created_count'] == 0
    assert UserDailySchedule.query.count() == 4


def test_attendance_and_requests_protected_without_schedule(retention):
    _, user, staff, *_ = retention
    db.session.add(AttendanceRecord(user_id=user.id, record_type='CHECK_OUT', timestamp=datetime(2026,10,5,15)))
    db.session.add(UserScheduleRequest(user_id=user.id,target_date=date(2026,10,12),request_type='ABSENCE',
        request_reason='承認済み欠席申請を保持する',request_status='APPROVED'))
    db.session.commit()
    result = UserScheduleService().bulk_create_month(user.id, staff.id, payload(), preview=False)
    assert result['created_count'] == 2 and result['skipped_count'] == 2
    assert {r.date for r in UserDailySchedule.query.all()} == {date(2026,10,19),date(2026,10,26)}


@pytest.mark.parametrize('change', ['invalid_month','missing_time','reversed','duplicate','no_days'])
def test_invalid_inputs_no_writes(retention, change):
    _, user, staff, *_ = retention
    data = payload()
    if change == 'invalid_month': data['month'] = '2026-13'
    if change == 'missing_time': data['templates'][0]['start_time'] = None
    if change == 'reversed': data['templates'][0]['end_time'] = '08:00'
    if change == 'duplicate': data['templates'] *= 2
    if change == 'no_days': data['templates'] = []
    with pytest.raises(ValidationError):
        UserScheduleService().bulk_create_month(user.id, staff.id, data, preview=False)
    assert UserDailySchedule.query.count() == 0


def test_commit_failure_rolls_back_all_days(retention, monkeypatch):
    _, user, staff, *_ = retention
    def fail():
        db.session.flush()
        raise RuntimeError('injected failure')
    monkeypatch.setattr(db.session, 'commit', fail)
    with pytest.raises(RuntimeError):
        UserScheduleService().bulk_create_month(user.id, staff.id, payload(), preview=False)
    assert UserDailySchedule.query.count() == 0
    assert AuditActionLog.query.count() == 0


def test_api_requires_staff_permission(retention):
    app, user, staff, *_ = retention
    client = app.test_client()
    path = f'/api/users/{user.id}/schedule-templates/bulk-preview'
    assert client.post(path,json=payload()).status_code == 401
    headers = {'Authorization':'Bearer '+create_access_token(identity=f'user:{user.id}')}
    assert client.post(path,json=payload(),headers=headers).status_code == 403
    headers = {'Authorization':'Bearer '+create_access_token(identity=f'staff:{staff.id}')}
    assert client.post(path,json=payload(),headers=headers).status_code == 200
    staff.roles = []; db.session.commit()
    assert client.post(path,json=payload(),headers=headers).status_code == 403
