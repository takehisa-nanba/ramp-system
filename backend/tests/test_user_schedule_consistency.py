# backend/tests/test_user_schedule_consistency.py
import pytest
from datetime import date, datetime, timedelta
from backend.app import db
from backend.app.models import (
    UserScheduleTemplate, UserDailySchedule, UserScheduleRequest,
    SupportRecord, AttendanceRecord
)
from backend.app.services.user_schedule_service import UserScheduleService
from backend.app.utils.errors import ValidationError
from flask_jwt_extended import create_access_token

def test_create_schedule_request_and_guardrail(app, setup_active_user):
    """申請の作成と重複申請防止ガードレールのテスト"""
    user, staff, manager = setup_active_user
    service = UserScheduleService()
    
    target_date = date(2026, 6, 10)
    
    # 既存の PENDING 申請がないことを保証
    UserScheduleRequest.query.filter_by(user_id=user.id, target_date=target_date).delete()
    db.session.commit()
    
    # 申請理由は10文字以上必要
    with pytest.raises(ValidationError) as excinfo:
        service.create_schedule_request(
            user_id=user.id,
            target_date=target_date,
            request_type='ABSENCE',
            request_reason='体調不良'  # 短すぎる
        )
    assert "10文字以上" in str(excinfo.value)
    
    # 正常な申請
    req1 = service.create_schedule_request(
        user_id=user.id,
        target_date=target_date,
        request_type='ABSENCE',
        request_reason='風邪のため、本日は自宅で安静にします。'
    )
    assert req1.id is not None
    assert req1.request_status == 'PENDING'
    
    # 重複するPENDING申請のガードレール
    with pytest.raises(ValidationError) as excinfo:
        service.create_schedule_request(
            user_id=user.id,
            target_date=target_date,
            request_type='ABSENCE',
            request_reason='風邪のため、本日は自宅で安静にします。'
        )
    assert "未決の申請がすでに存在します" in str(excinfo.value)

def test_decide_schedule_request_absence(app, setup_active_user):
    """欠席申請の承認時の動作検証（確定予定のキャンセルとABSENCE_CONTACT自動生成）"""
    user, staff, manager = setup_active_user
    service = UserScheduleService()
    
    target_date = date(2026, 6, 11)
    
    # 既存の予定・申請・記録をクリア
    UserDailySchedule.query.filter_by(user_id=user.id, date=target_date).delete()
    UserScheduleRequest.query.filter_by(user_id=user.id, target_date=target_date).delete()
    SupportRecord.query.filter_by(user_id=user.id, log_date=target_date).delete()
    db.session.commit()
    
    # まず通常予定が存在することを確認
    daily = UserDailySchedule(
        user_id=user.id,
        date=target_date,
        start_time="09:00",
        end_time="15:00",
        is_scheduled=True,
        schedule_status='NORMAL'
    )
    db.session.add(daily)
    db.session.commit()
    
    # 欠席申請を作成
    req = service.create_schedule_request(
        user_id=user.id,
        target_date=target_date,
        request_type='ABSENCE',
        request_reason='熱発のため、本日のお休みを希望します。'
    )
    
    # 承認判断理由は10文字以上必要
    with pytest.raises(ValidationError) as excinfo:
        service.decide_schedule_request(
            request_id=req.id,
            supporter_id=staff.id,
            status='APPROVED',
            decision_reason='了解です。'
        )
    assert "10文字以上" in str(excinfo.value)
    
    # 承認
    service.decide_schedule_request(
        request_id=req.id,
        supporter_id=staff.id,
        status='APPROVED',
        decision_reason='体調不良による欠席のため、本日のお休みを了解いたしました。'
    )
    
    # 状態の確認
    assert req.request_status == 'APPROVED'
    
    # 確定予定がCANCELLEDに更新されていること
    daily_updated = UserDailySchedule.query.filter_by(user_id=user.id, date=target_date).first()
    assert daily_updated.is_scheduled is False
    assert daily_updated.schedule_status == 'CANCELLED'
    assert daily_updated.start_time is None
    
    # 欠席対応記録が自動生成されていること
    record = SupportRecord.query.filter_by(
        user_id=user.id,
        log_date=target_date,
        support_record_type='ABSENCE_CONTACT'
    ).first()
    assert record is not None
    assert "熱発のため" in record.support_content
    assert "体調不良による欠席のため" in record.decision_reason

def test_action_items_consistency_detection(app, setup_active_user, client):
    """Action Itemsの不整合検知の検証"""
    user, staff, manager = setup_active_user
    
    # テストデータをクリア
    today = date.today()
    UserDailySchedule.query.filter_by(user_id=user.id, date=today).delete()
    UserScheduleRequest.query.filter_by(user_id=user.id, target_date=today).delete()
    SupportRecord.query.filter_by(user_id=user.id, log_date=today).delete()
    AttendanceRecord.query.filter_by(user_id=user.id).delete()
    db.session.commit()
    
    # JWT トークン生成
    token = create_access_token(identity=f"staff:{staff.id}", additional_claims={
        "role_name": "STAFF",
        "full_name": f"{staff.last_name} {staff.first_name}",
        "role_scopes": []
    })
    headers = {'Authorization': f'Bearer {token}'}
    
    # シナリオ1: 予定があるのに打刻がない (無断欠席)
    sched = UserDailySchedule(
        user_id=user.id,
        date=today,
        start_time="09:00",
        end_time="15:00",
        is_scheduled=True,
        schedule_status='NORMAL'
    )
    db.session.add(sched)
    db.session.commit()
    
    res = client.get('/api/action-items', headers=headers)
    assert res.status_code == 200
    items = res.json.get('items', [])
    unexcused_items = [i for i in items if i.get('type') == 'unexcused_absence' and i.get('user_id') == user.id]
    assert len(unexcused_items) == 1
    assert "無断欠席" in unexcused_items[0].get('title')
    
    # シナリオ2: 打刻があるのに予定がない (予定外来所)
    # 予定を削除
    UserDailySchedule.query.filter_by(user_id=user.id, date=today).delete()
    db.session.commit()
    
    # 打刻を登録 (CHECK_IN)
    check_in_time = datetime.combine(today, datetime.min.time()) + timedelta(hours=9)
    att = AttendanceRecord(
        user_id=user.id,
        record_type='CHECK_IN',
        timestamp=check_in_time
    )
    db.session.add(att)
    db.session.commit()
    
    res = client.get('/api/action-items', headers=headers)
    items = res.json.get('items', [])
    unscheduled_items = [i for i in items if i.get('type') == 'unscheduled_attendance' and i.get('user_id') == user.id]
    assert len(unscheduled_items) == 1
    assert "予定外来所" in unscheduled_items[0].get('title')
    
    # シナリオ3: 打刻があるのに支援記録がない (支援記録漏れ)
    # 予定を再度通常にして、予定外来所警告を消す
    sched = UserDailySchedule(
        user_id=user.id,
        date=today,
        start_time="09:00",
        end_time="15:00",
        is_scheduled=True,
        schedule_status='NORMAL'
    )
    db.session.add(sched)
    db.session.commit()
    
    res = client.get('/api/action-items', headers=headers)
    items = res.json.get('items', [])
    # 支援記録漏れの確認
    missing_record_items = [i for i in items if i.get('type') == 'support_record_missing' and i.get('user_id') == user.id]
    assert len(missing_record_items) == 1
    assert "支援記録漏れ" in missing_record_items[0].get('title')
    
    # 支援記録を作成すると警告が消える
    s_record = SupportRecord(
        user_id=user.id,
        log_date=today,
        supporter_id=staff.id,
        support_record_type='DIRECT_SUPPORT',
        support_content='個別訓練の実施。集中して課題に取り組めていました。',
        observation_note='問題なし。'
    )
    db.session.add(s_record)
    db.session.commit()
    
    res = client.get('/api/action-items', headers=headers)
    items = res.json.get('items', [])
    missing_record_items = [i for i in items if i.get('type') == 'support_record_missing' and i.get('user_id') == user.id]
    assert len(missing_record_items) == 0

def test_api_endpoints_schedule(app, setup_active_user, client):
    """予定管理に関する API エンドポイントのテスト"""
    user, staff, manager = setup_active_user
    
    # テストデータをクリア
    UserScheduleTemplate.query.filter_by(user_id=user.id).delete()
    db.session.commit()
    
    # JWT トークン生成
    token = create_access_token(identity=f"staff:{staff.id}", additional_claims={
        "role_name": "STAFF",
        "full_name": f"{staff.last_name} {staff.first_name}",
        "role_scopes": []
    })
    headers = {'Authorization': f'Bearer {token}'}
    
    # 1. テンプレートの保存 (POST)
    template_data = [
        {"day_of_week": "Monday", "is_scheduled": True, "start_time": "10:00", "end_time": "16:00"},
        {"day_of_week": "Wednesday", "is_scheduled": True, "start_time": "10:00", "end_time": "16:00"},
    ]
    res = client.post(f'/api/users/{user.id}/schedule-templates', json=template_data, headers=headers)
    assert res.status_code == 200
    assert res.json.get('success') is True
    
    # 2. テンプレートの取得 (GET)
    res = client.get(f'/api/users/{user.id}/schedule-templates', headers=headers)
    assert res.status_code == 200
    items = res.json.get('items', [])
    assert len(items) == 7  # 月〜日すべての曜日が返されるはず
    monday = next(i for i in items if i['day_of_week'] == 'Monday')
    assert monday['is_scheduled'] is True
    assert monday['start_time'] == '10:00'
    
    tuesday = next(i for i in items if i['day_of_week'] == 'Tuesday')
    assert tuesday['is_scheduled'] is False
    
    # 3. 申請の作成 (POST)
    req_payload = {
        "target_date": "2026-06-15",
        "request_type": "ABSENCE",
        "request_reason": "家庭都合によりお休みをさせていただきます。"
    }
    res = client.post(f'/api/users/{user.id}/schedule-requests', json=req_payload, headers=headers)
    assert res.status_code == 201
    assert res.json.get('success') is True
    req_id = res.json.get('item', {}).get('id')
    
    # 4. 承認 (POST)
    decide_payload = {
        "status": "APPROVED",
        "decision_reason": "家庭都合の欠席申請を了解いたしました。"
    }
    res = client.post(f'/api/users/schedule-requests/{req_id}/decide', json=decide_payload, headers=headers)
    assert res.status_code == 200
    assert res.json.get('success') is True
    assert res.json.get('item', {}).get('request_status') == 'APPROVED'
