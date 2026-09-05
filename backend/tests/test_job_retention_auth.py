# backend/tests/test_job_retention_auth.py

import pytest
import datetime
from flask_jwt_extended import create_access_token
from backend.app.extensions import db
from backend.app.models import (
    User, Supporter, StatusMaster, OfficeSetting, Corporation,
    OfficeServiceConfiguration, JobRetentionContract, RetentionUserVoiceLog,
    RetentionSupportActionLog
)

@pytest.fixture
def auth_setup(app):
    with app.app_context():
        # 自治体マスタ
        from backend.app.models import MunicipalityMaster
        muni = MunicipalityMaster.query.first()
        if not muni:
            muni = MunicipalityMaster(municipality_code="131016", name="東京都千代田区")
            db.session.add(muni)
            db.session.flush()

        # 法人
        corp = Corporation(corporation_name="テスト法人", corporation_type="株式会社")
        db.session.add(corp)
        db.session.flush()

        # 事業所A
        office_a = OfficeSetting(
            office_name="事業所A",
            corporation_id=corp.id,
            municipality_id=muni.id,
            full_time_weekly_minutes=2400
        )
        # 事業所B (他事業所)
        office_b = OfficeSetting(
            office_name="事業所B",
            corporation_id=corp.id,
            municipality_id=muni.id,
            full_time_weekly_minutes=2400
        )
        db.session.add_all([office_a, office_b])
        db.session.flush()

        # サービス種別マスタ
        from backend.app.models import ServiceTypeMaster
        st = ServiceTypeMaster.query.first()
        if not st:
            st = ServiceTypeMaster(name="就労定着支援", service_code="RET")
            db.session.add(st)
            db.session.flush()

        # サービス設定
        import uuid
        bango_a = f"13{uuid.uuid4().hex[:8]}"
        bango_b = f"13{uuid.uuid4().hex[:8]}"
        osc_a = OfficeServiceConfiguration(
            office_id=office_a.id,
            service_type_master_id=st.id,
            jigyosho_bango=bango_a,
            capacity=20
        )
        osc_b = OfficeServiceConfiguration(
            office_id=office_b.id,
            service_type_master_id=st.id,
            jigyosho_bango=bango_b,
            capacity=20
        )
        db.session.add_all([osc_a, osc_b])
        db.session.flush()

        status = StatusMaster.query.filter_by(name="定着支援中").first()
        if not status:
            status = StatusMaster(name="定着支援中")
            db.session.add(status)
            db.session.flush()

        uid = uuid.uuid4().hex[:6]
        # 支援員A (事業所A所属)
        staff_a = Supporter(
            staff_code=f"STAFF_A_{uid}",
            last_name="佐藤",
            first_name="一郎",
            last_name_kana="サトウ",
            first_name_kana="イチロウ",
            office_id=office_a.id,
            hire_date=datetime.date(2025, 4, 1),
            employment_type="FULL_TIME",
            weekly_scheduled_minutes=2400
        )
        # 支援員B (事業所B所属 - 他事業所)
        staff_b = Supporter(
            staff_code=f"STAFF_B_{uid}",
            last_name="鈴木",
            first_name="二郎",
            last_name_kana="スズキ",
            first_name_kana="ジロウ",
            office_id=office_b.id,
            hire_date=datetime.date(2025, 4, 1),
            employment_type="FULL_TIME",
            weekly_scheduled_minutes=2400
        )
        db.session.add_all([staff_a, staff_b])
        db.session.flush()

        # 本人A (事業所Aの利用者、担当: staff_a)
        user_a = User(
            display_name="利用者A",
            user_code=f"USER_A_{uid}",
            status_id=status.id,
            primary_supporter_id=staff_a.id
        )
        # 本人B (別の利用者)
        user_b = User(
            display_name="利用者B",
            user_code=f"USER_B_{uid}",
            status_id=status.id,
            primary_supporter_id=staff_a.id
        )
        db.session.add_all([user_a, user_b])
        db.session.flush()

        # 契約A (本人Aの定着支援契約)
        contract_a = JobRetentionContract(
            user_id=user_a.id,
            office_service_configuration_id=osc_a.id,
            contract_start_date=datetime.date(2026, 9, 1),
            contract_end_date=datetime.date(2029, 8, 31),
            status="ACTIVE",
            is_company_involved=True
        )
        # 契約B (本人Bの定着支援契約)
        contract_b = JobRetentionContract(
            user_id=user_b.id,
            office_service_configuration_id=osc_a.id,
            contract_start_date=datetime.date(2026, 9, 1),
            contract_end_date=datetime.date(2029, 8, 31),
            status="ACTIVE",
            is_company_involved=False
        )
        db.session.add_all([contract_a, contract_b])
        db.session.commit()

        yield {
            "staff_a": staff_a,
            "staff_b": staff_b,
            "user_a": user_a,
            "user_b": user_b,
            "contract_a": contract_a,
            "contract_b": contract_b
        }

def get_headers(identity: str, role_scopes=None):
    claims = {"role_scopes": role_scopes or []}
    token = create_access_token(identity=identity, additional_claims=claims)
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

def test_user_cannot_access_staff_endpoints(app, auth_setup):
    """【受入条件】本人が支援員APIへアクセスすると403を返す"""
    client = app.test_client()
    user_a = auth_setup["user_a"]
    headers = get_headers(f"user:{user_a.id}")

    # 1. 支援員用契約一覧API
    res = client.get("/api/job-retention/contracts", headers=headers)
    assert res.status_code == 403

    # 2. 支援員用契約作成API
    res = client.post("/api/job-retention/contracts", headers=headers, json={
        "user_id": user_a.id,
        "contract_start_date": "2026-09-01",
        "contract_end_date": "2029-08-31"
    })
    assert res.status_code == 403

    # 3. 支援員用支援記録登録API
    contract_a = auth_setup["contract_a"]
    res = client.post(f"/api/job-retention/contracts/{contract_a.id}/actions", headers=headers, json={
        "action_date": "2026-09-05",
        "confirmed_situation": "面談",
        "provided_support": "支援"
    })
    assert res.status_code == 403

    # 4. 支援員用レポートプレビューAPI
    res = client.get(f"/api/job-retention/contracts/{contract_a.id}/monthly-reports/2026-09/preview", headers=headers)
    assert res.status_code == 403

def test_user_cannot_access_other_user_data(app, auth_setup):
    """【受入条件】本人Aが本人Bの記録へアクセスすると403を返す"""
    client = app.test_client()
    user_a = auth_setup["user_a"]
    contract_b = auth_setup["contract_b"]
    headers = get_headers(f"user:{user_a.id}")

    # 本人Aが本人Bの契約詳細を取得しようとする
    res = client.get(f"/api/job-retention/contracts/{contract_b.id}", headers=headers)
    assert res.status_code == 403

    # 本人Aが本人Bの契約に声を投稿しようとする
    res = client.post(f"/api/job-retention/contracts/{contract_b.id}/voices", headers=headers, json={
        "raw_voice": "不正アクセス試行"
    })
    assert res.status_code == 403

    # 本人Aが本人Bの声一覧を取得しようとする
    res = client.get(f"/api/job-retention/contracts/{contract_b.id}/voices", headers=headers)
    assert res.status_code == 403

def test_other_office_staff_cannot_access_contract(app, auth_setup):
    """【受入条件】他事業所の支援員Bが事業所Aの契約Aへアクセスすると403を返す"""
    client = app.test_client()
    staff_b = auth_setup["staff_b"] # 事業所B
    contract_a = auth_setup["contract_a"] # 事業所A
    headers = get_headers(f"staff:{staff_b.id}")

    # 支援員Bが契約Aの支援記録を登録しようとする
    res = client.post(f"/api/job-retention/contracts/{contract_a.id}/actions", headers=headers, json={
        "action_date": "2026-09-05",
        "confirmed_situation": "事業所外アクセス",
        "provided_support": "支援"
    })
    assert res.status_code == 403

    # 支援員Bが契約Aのレポートプレビューを取得しようとする
    res = client.get(f"/api/job-retention/contracts/{contract_a.id}/monthly-reports/2026-09/preview", headers=headers)
    assert res.status_code == 403

def test_authorized_user_access_succeeds(app, auth_setup):
    """【受入条件】正常な本人アクセスは成功する"""
    client = app.test_client()
    user_a = auth_setup["user_a"]
    contract_a = auth_setup["contract_a"]
    headers = get_headers(f"user:{user_a.id}")

    # 1. 自分の定着支援契約情報の取得
    res = client.get("/api/job-retention/my-contract", headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["id"] == contract_a.id
    assert data["user_id"] == user_a.id

    # 2. 自分の契約に対するできごと（声）の登録
    res = client.post(f"/api/job-retention/contracts/{contract_a.id}/voices", headers=headers, json={
        "raw_voice": "今日はお弁当を自分で作って持参できた。",
        "self_coping_action": "前日の夜に下ごしらえをした。"
    })
    assert res.status_code == 201

    # 3. 自分の声一覧の取得
    res = client.get(f"/api/job-retention/contracts/{contract_a.id}/voices", headers=headers)
    assert res.status_code == 200
    voices = res.get_json()
    assert len(voices) >= 1
    assert "お弁当" in voices[0]["raw_voice"]

def test_authorized_staff_access_succeeds(app, auth_setup):
    """【受入条件】正常な支援員アクセスは成功する"""
    client = app.test_client()
    staff_a = auth_setup["staff_a"]
    contract_a = auth_setup["contract_a"]
    headers = get_headers(f"staff:{staff_a.id}")

    # 1. 支援員契約一覧取得
    res = client.get("/api/job-retention/contracts", headers=headers)
    assert res.status_code == 200
    contracts = res.get_json()
    assert any(c["id"] == contract_a.id for c in contracts)

    # 2. 支援記録の登録
    res = client.post(f"/api/job-retention/contracts/{contract_a.id}/actions", headers=headers, json={
        "action_date": "2026-09-05",
        "has_user_interview": True,
        "interview_method": "FACE_TO_FACE",
        "has_company_visit": True,
        "has_coordination": False,
        "has_other_support": False,
        "confirmed_situation": "勤務継続中、課題なし",
        "provided_support": "定期状況確認",
        "user_action_observed": "挨拶が良好",
        "staff_intervention_boundary": "定期見守り",
        "next_step": "次回2週間後"
    })
    assert res.status_code == 201

    # 3. レポートプレビュー取得
    res = client.get(f"/api/job-retention/contracts/{contract_a.id}/monthly-reports/2026-09/preview", headers=headers)
    assert res.status_code == 200
    report = res.get_json()
    assert "2026/09/05" in report["interview_records"]

    # 4. レポート保存
    res = client.post(f"/api/job-retention/contracts/{contract_a.id}/monthly-reports/2026-09", headers=headers, json=report)
    assert res.status_code == 200
