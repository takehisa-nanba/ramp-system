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
    assert daily_updated.approval_status == 'CANCELLED'
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

def test_apply_schedule_template_and_usage_summary(app, setup_active_user, client):
    """基本曜日予定の一括適用、および支給量チェックAPIのテスト"""
    user, staff, manager = setup_active_user
    
    # テストデータをクリア
    UserScheduleTemplate.query.filter_by(user_id=user.id).delete()
    UserDailySchedule.query.filter_by(user_id=user.id).delete()
    from backend.app.models.core.service_certificate import ServiceCertificate, GrantedService
    g_services = GrantedService.query.join(ServiceCertificate).filter(ServiceCertificate.user_id == user.id).all()
    for gs in g_services:
        db.session.delete(gs)
    db.session.commit()
    ServiceCertificate.query.filter_by(user_id=user.id).delete()
    db.session.commit()
    
    # JWT トークン生成
    token = create_access_token(identity=f"staff:{staff.id}", additional_claims={
        "role_name": "STAFF",
        "full_name": f"{staff.last_name} {staff.first_name}",
        "role_scopes": []
    })
    headers = {'Authorization': f'Bearer {token}'}
    
    # 1. テンプレートの保存 (月・水・金を通所とする)
    template_data = [
        {"day_of_week": "Monday", "is_scheduled": True, "start_time": "10:00", "end_time": "16:00", "location_type": "ON_SITE"},
        {"day_of_week": "Wednesday", "is_scheduled": True, "start_time": "10:00", "end_time": "16:00", "location_type": "AT_HOME"},
        {"day_of_week": "Friday", "is_scheduled": True, "start_time": "10:00", "end_time": "16:00", "location_type": "OFF_SITE_SUPPORT"},
    ]
    client.post(f'/api/users/{user.id}/schedule-templates', json=template_data, headers=headers)
    
    # 2. 受給者証・支給量のシード (上限を5日に設定)
    from backend.app.models import OfficeServiceConfiguration, ServiceTypeMaster, OfficeSetting
    service_type = ServiceTypeMaster.query.filter_by(service_code='TRANSITION').first()
    if not service_type:
        service_type = ServiceTypeMaster(
            name="就労移行支援",
            service_code="TRANSITION",
            required_review_months=6
        )
        db.session.add(service_type)
        db.session.flush()
        
    office_config = OfficeServiceConfiguration.query.first()
    if not office_config:
        office = OfficeSetting.query.first()
        office_config = OfficeServiceConfiguration(
            office_id=office.id,
            service_type_master_id=service_type.id,
            jigyosho_bango='1310100001',
            capacity=20,
            initial_designation_date=date(2023, 4, 1)
        )
        db.session.add(office_config)
        db.session.flush()
    cert = ServiceCertificate(
        user_id=user.id,
        office_service_configuration_id=office_config.id,
        certificate_issue_date=date(2026, 6, 1),
        municipality_master_id=1, # デフォルト
        certificate_type="受給者証",
        status='ACTIVE'
    )
    db.session.add(cert)
    db.session.flush()
    
    gs = GrantedService(
        certificate_id=cert.id,
        granted_start_date=date(2026, 6, 1),
        granted_end_date=date(2026, 6, 30),
        max_service_days=5,
        service_type_master_id=office_config.service_type_master_id
    )
    db.session.add(gs)
    db.session.commit()
    
    # 3. 2026年6月の予定を一括適用する (POST)
    apply_payload = {"year": 2026, "month": 6}
    res = client.post(f'/api/users/{user.id}/schedule-templates/apply', json=apply_payload, headers=headers)
    assert res.status_code == 200
    assert res.json.get('success') is True
    
    schedules = UserDailySchedule.query.filter_by(user_id=user.id).filter(
        UserDailySchedule.date >= date(2026, 6, 1),
        UserDailySchedule.date <= date(2026, 6, 30)
    ).all()
    assert len(schedules) == 30 # 6月は30日
    # 月曜日は予定あり、水曜日は在宅予定
    mon_sched = next(s for s in schedules if s.date == date(2026, 6, 1)) # 2026/06/01 は月曜日
    assert mon_sched.is_scheduled is True
    assert mon_sched.location_type == 'ON_SITE'
    assert mon_sched.approval_status == 'APPROVED'
    
    wed_sched = next(s for s in schedules if s.date == date(2026, 6, 3)) # 2026/06/03 は水曜日
    assert wed_sched.is_scheduled is True
    assert wed_sched.location_type == 'AT_HOME'
    
    # 4. 支給量チェックの確認 (GET /api/users/<user_id>/monthly-usage-summary)
    # 2026年6月の予定日数は 13日間 (月・水・金が30日中13日ある)
    # 支給量が5日なので、超過しているはず
    res = client.get(f'/api/users/{user.id}/monthly-usage-summary?year=2026&month=6', headers=headers)
    assert res.status_code == 200
    summary = res.json.get('items', [])[0]
    assert summary['max_service_days'] == 5
    assert summary['scheduled_days_count'] == 13
    assert summary['total_days_count'] == 13 # 打刻がないので予定日数と同じ
    assert summary['is_exceeded'] is True
    assert summary['exceeded_days'] == 8
    
    # 5. 実績優先カウントの確認
    # 予定がない日 (2026/06/02 火曜日) に打刻 (CHECK_IN) を追加する
    from backend.app.models.support.attendance_workflow import AttendanceRecord
    db.session.add(AttendanceRecord(
        user_id=user.id,
        record_type='CHECK_IN',
        timestamp=datetime(2026, 6, 2, 10, 0)
    ))
    db.session.commit()
    
    # 火曜日は予定なしだが、打刻があるため合計利用日数（実績優先）が14日になるはず
    res = client.get(f'/api/users/{user.id}/monthly-usage-summary?year=2026&month=6', headers=headers)
    summary = res.json.get('items', [])[0]
    assert summary['total_days_count'] == 14
    assert summary['actual_days_count'] == 1
    
    # 6. auto_created の UserDailyLog がカウントから除外されることの確認
    from backend.app.models import UserDailyLog
    # 自動生成されただけの日報を登録 (実績としては除外されるはず)
    db.session.add(UserDailyLog(
        user_id=user.id,
        log_date=date(2026, 6, 4), # 木曜日 (予定なし)
        location_type='ON_SITE',
        auto_created=True,
        morning_completed=False,
        evening_completed=False,
        support_content_notes='自動作成日報'
    ))
    db.session.commit()
    
    res = client.get(f'/api/users/{user.id}/monthly-usage-summary?year=2026&month=6', headers=headers)
    summary = res.json.get('items', [])[0]
    assert summary['total_days_count'] == 14 # 変化なし（14日のまま）
    
    # 手動保存された日報 (auto_created=False, completed) の場合は実績としてカウントされる
    db.session.add(UserDailyLog(
        user_id=user.id,
        log_date=date(2026, 6, 4), # 木曜日
        location_type='ON_SITE',
        auto_created=False,
        morning_completed=True,
        evening_completed=True,
        support_content_notes='手動日報'
    ))
    db.session.commit()
    
    res = client.get(f'/api/users/{user.id}/monthly-usage-summary?year=2026&month=6', headers=headers)
    summary = res.json.get('items', [])[0]
    assert summary['total_days_count'] == 15 # 15日に増加する

    # 7. 契約期間が月中の場合（契約サービス単位での集計範囲制限の検証）
    gs.granted_end_date = date(2026, 6, 15)
    db.session.commit()

    res2 = client.get(f'/api/users/{user.id}/monthly-usage-summary?year=2026&month=6', headers=headers)
    summary2 = res2.json.get('items', [])[0]
    # 6/1〜6/15の範囲での集計結果:
    # 予定: 月(6/1, 6/8, 6/15), 水(6/3, 6/10), 金(6/5, 6/12) -> 7日
    # 実績: 6/2(打刻), 6/4(日報) -> 2日
    # 合計: 9日
    assert summary2['scheduled_days_count'] == 7
    assert summary2['actual_days_count'] == 2
    assert summary2['total_days_count'] == 9

def test_dynamic_month_minus_8_usage_limit(app, setup_active_user, client):
    """
    DYNAMIC_MONTH_MINUS_8 タイプの支給上限日の動的計算を検証する。
    """
    from flask_jwt_extended import create_access_token
    from backend.app.models.core.service_certificate import ServiceCertificate, GrantedService
    from datetime import date
    
    user, staff, manager = setup_active_user
    token = create_access_token(identity=f"staff:{staff.id}", additional_claims={
        "roles": ['admin']
    })
    headers = {"Authorization": f"Bearer {token}"}
    
    # 既存の受給者証と支給サービスをクリーンアップ
    ServiceCertificate.query.filter_by(user_id=user.id).delete()
    db.session.commit()
    
    # 動的計算方式の受給者証を追加
    cert = ServiceCertificate(
        user_id=user.id,
        office_service_configuration_id=1,
        certificate_issue_date=date(2026, 6, 1),
        municipality_master_id=1,
        certificate_type="就労移行",
        status='ACTIVE'
    )
    db.session.add(cert)
    db.session.flush()
    
    gs = GrantedService(
        certificate_id=cert.id,
        service_type_master_id=1,
        granted_start_date=date(2026, 6, 1),
        granted_end_date=date(2026, 6, 30),
        max_service_days_type='DYNAMIC_MONTH_MINUS_8',
        max_service_days=23
    )
    db.session.add(gs)
    db.session.commit()
    
    # 2026年6月の予定実績サマリーを取得
    # 6月は30日あるので、上限は 30 - 8 = 22日になるはず。
    res = client.get(f'/api/users/{user.id}/monthly-usage-summary?year=2026&month=6', headers=headers)
    assert res.status_code == 200
    summary = res.json.get('items', [])[0]
    assert summary['max_service_days'] == 22

    # 2026年2月の予定実績サマリーを取得 (閏年ではないので 28日)
    # 28 - 8 = 20日
    gs.granted_start_date = date(2026, 2, 1)
    gs.granted_end_date = date(2026, 2, 28)
    db.session.commit()
    
    res = client.get(f'/api/users/{user.id}/monthly-usage-summary?year=2026&month=2', headers=headers)
    assert res.status_code == 200
    summary = res.json.get('items', [])[0]
    assert summary['max_service_days'] == 20

