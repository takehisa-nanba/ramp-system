# backend/tests/test_job_retention_auth.py

import pytest
import datetime
import uuid
from flask_jwt_extended import create_access_token
from backend.app.extensions import db
from backend.app.models import (
    User, Supporter, StatusMaster, OfficeSetting, Corporation,
    OfficeServiceConfiguration, JobRetentionContract, RetentionUserVoiceLog,
    RetentionSupportActionLog, RoleMaster, PermissionMaster, ServiceTypeMaster,
    MunicipalityMaster
)
from backend.app.services.job_retention_service import JobRetentionService

@pytest.fixture
def auth_setup(app):
    with app.app_context():
        # 自治体マスタ
        muni = MunicipalityMaster.query.first()
        if not muni:
            muni = MunicipalityMaster(municipality_code="131016", name="東京都千代田区")
            db.session.add(muni)
            db.session.flush()

        # 法人1 & 法人2 (別法人)
        corp1 = Corporation(corporation_name=f"法人1_{uuid.uuid4().hex[:4]}", corporation_type="株式会社")
        corp2 = Corporation(corporation_name=f"法人2_{uuid.uuid4().hex[:4]}", corporation_type="株式会社")
        db.session.add_all([corp1, corp2])
        db.session.flush()

        # 事業所A (法人1)
        office_a = OfficeSetting(
            office_name="事業所A",
            corporation_id=corp1.id,
            municipality_id=muni.id,
            full_time_weekly_minutes=2400
        )
        # 事業所B (法人1 - 同一法人・他事業所)
        office_b = OfficeSetting(
            office_name="事業所B",
            corporation_id=corp1.id,
            municipality_id=muni.id,
            full_time_weekly_minutes=2400
        )
        # 事業所C (法人2 - 別法人事業所)
        office_c = OfficeSetting(
            office_name="事業所C",
            corporation_id=corp2.id,
            municipality_id=muni.id,
            full_time_weekly_minutes=2400
        )
        db.session.add_all([office_a, office_b, office_c])
        db.session.flush()

        # サービス種別マスタ
        st = ServiceTypeMaster.query.first()
        if not st:
            st = ServiceTypeMaster(name="就労定着支援", service_code="RET")
            db.session.add(st)
            db.session.flush()

        # サービス設定
        osc_a = OfficeServiceConfiguration(
            office_id=office_a.id,
            service_type_master_id=st.id,
            jigyosho_bango=f"13{uuid.uuid4().hex[:8]}",
            capacity=20
        )
        osc_b = OfficeServiceConfiguration(
            office_id=office_b.id,
            service_type_master_id=st.id,
            jigyosho_bango=f"13{uuid.uuid4().hex[:8]}",
            capacity=20
        )
        osc_c = OfficeServiceConfiguration(
            office_id=office_c.id,
            service_type_master_id=st.id,
            jigyosho_bango=f"13{uuid.uuid4().hex[:8]}",
            capacity=20
        )
        db.session.add_all([osc_a, osc_b, osc_c])
        db.session.flush()

        # RBAC パーミッション
        perm_view = PermissionMaster.query.filter_by(name='JOB_RETENTION_VIEW').first()
        if not perm_view:
            perm_view = PermissionMaster(name='JOB_RETENTION_VIEW')
            db.session.add(perm_view)
        perm_edit = PermissionMaster.query.filter_by(name='JOB_RETENTION_EDIT').first()
        if not perm_edit:
            perm_edit = PermissionMaster(name='JOB_RETENTION_EDIT')
            db.session.add(perm_edit)
        perm_approve = PermissionMaster.query.filter_by(name='JOB_RETENTION_APPROVE').first()
        if not perm_approve:
            perm_approve = PermissionMaster(name='JOB_RETENTION_APPROVE')
            db.session.add(perm_approve)
        db.session.flush()

        # ロール1: 定着支援フル権限ロール (VIEW + EDIT + APPROVE)
        role_full = RoleMaster(name=f"RETENTION_FULL_{uuid.uuid4().hex[:4]}", role_scope="OFFICE")
        role_full.permissions.extend([perm_view, perm_edit, perm_approve])

        # ロール2: 閲覧限定ロール (VIEW のみ)
        role_view_only = RoleMaster(name=f"RETENTION_VIEW_ONLY_{uuid.uuid4().hex[:4]}", role_scope="OFFICE")
        role_view_only.permissions.append(perm_view)

        # ロール3: 権限なしロール
        role_none = RoleMaster(name=f"RETENTION_NONE_{uuid.uuid4().hex[:4]}", role_scope="OFFICE")

        # ロール4: CORPORATE権限ロール (法人スコープ)
        role_corporate = RoleMaster(name=f"RETENTION_CORP_{uuid.uuid4().hex[:4]}", role_scope="CORPORATE")
        role_corporate.permissions.extend([perm_view, perm_edit, perm_approve])

        db.session.add_all([role_full, role_view_only, role_none, role_corporate])
        db.session.flush()

        uid = uuid.uuid4().hex[:6]
        # 支援員A (事業所A所属、フル権限)
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
        staff_a.roles.append(role_full)

        # 支援員A2 (事業所A所属、権限なし)
        staff_no_perm = Supporter(
            staff_code=f"STAFF_NOP_{uid}",
            last_name="無権",
            first_name="限男",
            last_name_kana="ムケン",
            first_name_kana="ゲンオ",
            office_id=office_a.id,
            hire_date=datetime.date(2025, 4, 1),
            employment_type="FULL_TIME",
            weekly_scheduled_minutes=2400
        )
        staff_no_perm.roles.append(role_none)

        # 支援員A_view (事業所A所属、VIEWのみ)
        staff_view_only = Supporter(
            staff_code=f"STAFF_VIEW_{uid}",
            last_name="閲覧",
            first_name="専子",
            last_name_kana="エツラン",
            first_name_kana="センコ",
            office_id=office_a.id,
            hire_date=datetime.date(2025, 4, 1),
            employment_type="FULL_TIME",
            weekly_scheduled_minutes=2400
        )
        staff_view_only.roles.append(role_view_only)

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
        staff_b.roles.append(role_full)

        # 支援員CORP (事業所A所属だがCORPORATEスコープ)
        staff_corp = Supporter(
            staff_code=f"STAFF_CORP_{uid}",
            last_name="法人",
            first_name="統轄",
            last_name_kana="ホウジン",
            first_name_kana="トウカツ",
            office_id=office_a.id,
            hire_date=datetime.date(2025, 4, 1),
            employment_type="FULL_TIME",
            weekly_scheduled_minutes=2400
        )
        staff_corp.roles.append(role_corporate)

        db.session.add_all([staff_a, staff_no_perm, staff_view_only, staff_b, staff_corp])
        db.session.flush()

        status = StatusMaster.query.filter_by(name="定着支援中").first()
        if not status:
            status = StatusMaster(name="定着支援中")
            db.session.add(status)
            db.session.flush()

        # 本人A (利用者A)
        user_a = User(
            display_name="利用者A",
            user_code=f"USER_A_{uid}",
            status_id=status.id,
            primary_supporter_id=staff_a.id
        )
        # 本人B (利用者B)
        user_b = User(
            display_name="利用者B",
            user_code=f"USER_B_{uid}",
            status_id=status.id,
            primary_supporter_id=staff_b.id
        )
        db.session.add_all([user_a, user_b])
        db.session.flush()

        # 契約A (事業所Aの定着支援契約、初期同意未設定NOT_SET)
        contract_a = JobRetentionContract(
            user_id=user_a.id,
            office_service_configuration_id=osc_a.id,
            contract_start_date=datetime.date(2026, 9, 1),
            contract_end_date=datetime.date(2029, 8, 31),
            status="ACTIVE",
            is_company_involved=False,
            consent_status="NOT_SET"
        )
        # 契約B (事業所Bの定着支援契約)
        contract_b = JobRetentionContract(
            user_id=user_b.id,
            office_service_configuration_id=osc_b.id,
            contract_start_date=datetime.date(2026, 9, 1),
            contract_end_date=datetime.date(2029, 8, 31),
            status="ACTIVE",
            is_company_involved=False,
            consent_status="NOT_SET"
        )
        # 契約C (別法人・事業所Cの定着支援契約)
        contract_c = JobRetentionContract(
            user_id=user_b.id,
            office_service_configuration_id=osc_c.id,
            contract_start_date=datetime.date(2026, 9, 1),
            contract_end_date=datetime.date(2029, 8, 31),
            status="ACTIVE",
            is_company_involved=False,
            consent_status="NOT_SET"
        )
        db.session.add_all([contract_a, contract_b, contract_c])
        db.session.commit()

        yield {
            "staff_a": staff_a,
            "staff_b": staff_b,
            "staff_corp": staff_corp,
            "staff_no_perm": staff_no_perm,
            "staff_view_only": staff_view_only,
            "user_a": user_a,
            "user_b": user_b,
            "contract_a": contract_a,
            "contract_b": contract_b,
            "contract_c": contract_c,
            "osc_a": osc_a,
            "osc_b": osc_b,
            "osc_c": osc_c,
            "corp1": corp1,
            "corp2": corp2
        }

def get_headers(identity: str, role_scopes=None):
    claims = {"role_scopes": role_scopes or []}
    token = create_access_token(identity=identity, additional_claims=claims)
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# ====================================================================
# 1. アクター分離・「本人の声」作成権限テスト
# ====================================================================
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
        "office_service_configuration_id": auth_setup["osc_a"].id,
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

def test_staff_cannot_post_user_voice(app, auth_setup):
    """【受入条件】支援員が本人の声POST APIを使用すると403"""
    client = app.test_client()
    staff_a = auth_setup["staff_a"]
    contract_a = auth_setup["contract_a"]
    headers = get_headers(f"staff:{staff_a.id}")

    res = client.post(f"/api/job-retention/contracts/{contract_a.id}/voices", headers=headers, json={
        "raw_voice": "支援員が代理で本人として投稿しようとする"
    })
    assert res.status_code == 403

def test_user_can_post_own_voice(app, auth_setup):
    """【受入条件】本人自身の声POSTは201成功"""
    client = app.test_client()
    user_a = auth_setup["user_a"]
    contract_a = auth_setup["contract_a"]
    headers = get_headers(f"user:{user_a.id}")

    res = client.post(f"/api/job-retention/contracts/{contract_a.id}/voices", headers=headers, json={
        "raw_voice": "自分で投稿した日記",
        "self_coping_action": "深呼吸した"
    })
    assert res.status_code == 201
    data = res.get_json()
    assert "id" in data

def test_user_cannot_access_other_user_data(app, auth_setup):
    """【受入条件】本人Aが本人Bの記録へアクセスすると403を返す"""
    client = app.test_client()
    user_a = auth_setup["user_a"]
    contract_b = auth_setup["contract_b"]
    headers = get_headers(f"user:{user_a.id}")

    # 本人Aが本人Bの契約詳細を取得しようとする
    res = client.get(f"/api/job-retention/contracts/{contract_b.id}", headers=headers)
    assert res.status_code == 403

    # 本人Aが本人Bの契約にできごとを投稿しようとする
    res = client.post(f"/api/job-retention/contracts/{contract_b.id}/voices", headers=headers, json={
        "raw_voice": "他人の契約に投稿"
    })
    assert res.status_code == 403

# ====================================================================
# 2. テナント判定 (契約所属事業所基準) & CORPORATE別法人検証
# ====================================================================
def test_other_office_staff_cannot_access_contract(app, auth_setup):
    """【受入条件】契約所属事業所外の支援員は403（単に同じ利用者が他サービス利用中でも不可）"""
    client = app.test_client()
    staff_b = auth_setup["staff_b"] # 事業所B
    contract_a = auth_setup["contract_a"] # 事業所Aの契約
    headers = get_headers(f"staff:{staff_b.id}")

    res = client.get(f"/api/job-retention/contracts/{contract_a.id}", headers=headers)
    assert res.status_code == 403

def test_corporate_staff_cannot_access_different_corp_contract(app, auth_setup):
    """【受入条件】CORPORATE権限でも別法人契約は403"""
    client = app.test_client()
    staff_corp = auth_setup["staff_corp"] # 法人1所属
    contract_c = auth_setup["contract_c"] # 法人2所属事業所Cの契約
    headers = get_headers(f"staff:{staff_corp.id}", role_scopes=["CORPORATE"])

    # 法人1のCORPORATE支援員が、法人2の契約Cへアクセス
    res = client.get(f"/api/job-retention/contracts/{contract_c.id}", headers=headers)
    assert res.status_code == 403

def test_corporate_staff_can_access_same_corp_different_office_contract(app, auth_setup):
    """【受入条件】CORPORATE権限であれば同一法人内の他事業所契約はアクセス成功"""
    client = app.test_client()
    staff_corp = auth_setup["staff_corp"] # 法人1所属 (事業所A)
    contract_b = auth_setup["contract_b"] # 法人1所属 (事業所B)
    headers = get_headers(f"staff:{staff_corp.id}", role_scopes=["CORPORATE"])

    res = client.get(f"/api/job-retention/contracts/{contract_b.id}", headers=headers)
    assert res.status_code == 200

# ====================================================================
# 3. 定着支援専用RBACパーミッション検証
# ====================================================================
def test_staff_missing_rbac_permissions_gets_403(app, auth_setup):
    """【受入条件】RBAC権限不足は403"""
    client = app.test_client()
    staff_no_perm = auth_setup["staff_no_perm"]
    staff_view_only = auth_setup["staff_view_only"]
    contract_a = auth_setup["contract_a"]

    # 1. 権限なし支援員は閲覧も403
    h_none = get_headers(f"staff:{staff_no_perm.id}")
    res = client.get("/api/job-retention/contracts", headers=h_none)
    assert res.status_code == 403

    res = client.get(f"/api/job-retention/contracts/{contract_a.id}", headers=h_none)
    assert res.status_code == 403

    # 2. VIEW_ONLY 支援員は閲覧できるが、EDIT は403
    h_view = get_headers(f"staff:{staff_view_only.id}")
    res = client.get(f"/api/job-retention/contracts/{contract_a.id}", headers=h_view)
    assert res.status_code == 200

    # 記録作成は EDIT 不足で 403
    res = client.post(f"/api/job-retention/contracts/{contract_a.id}/actions", headers=h_view, json={
        "action_date": "2026-09-05",
        "confirmed_situation": "面談実施",
        "provided_support": "助言"
    })
    assert res.status_code == 403

    # 3. EDIT 権限のみの支援員はレポート確定(APPROVE)で 403
    staff_a = auth_setup["staff_a"]
    h_staff_a = get_headers(f"staff:{staff_a.id}")

    # フル権限スタッフは下書き保存(EDIT)も確定(APPROVE)も可能
    res = client.post(f"/api/job-retention/contracts/{contract_a.id}/monthly-reports/2026-09", headers=h_staff_a, json={
        "finalize": False
    })
    assert res.status_code == 200

    res = client.post(f"/api/job-retention/contracts/{contract_a.id}/monthly-reports/2026-09", headers=h_staff_a, json={
        "finalize": True
    })
    assert res.status_code == 200

# ====================================================================
# 4. 情報共有同意・初期値 Fail Closed 検証
# ====================================================================
def test_contract_creation_defaults_to_not_set_consent(app, auth_setup):
    """【受入条件】新規契約の情報共有同意は初期状態で未同意 (NOT_SET)、is_company_involved=False"""
    client = app.test_client()
    staff_a = auth_setup["staff_a"]
    user_a = auth_setup["user_a"]
    osc_a = auth_setup["osc_a"]
    headers = get_headers(f"staff:{staff_a.id}")

    res = client.post("/api/job-retention/contracts", headers=headers, json={
        "user_id": user_a.id,
        "office_service_configuration_id": osc_a.id,
        "contract_start_date": "2026-10-01",
        "contract_end_date": "2029-09-30"
    })
    assert res.status_code == 201
    contract_id = res.get_json()["id"]

    # 契約詳細を取得して初期値を確認
    res = client.get(f"/api/job-retention/contracts/{contract_id}", headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["consent_status"] == "NOT_SET"
    assert data["is_company_involved"] is False

# ====================================================================
# 5. レポート推測補完禁止・公式帳票マッピング検証
# ====================================================================
def test_report_preview_does_not_infer_non_existent_facts(app, auth_setup):
    """【受入条件】公式帳票へ一次情報に存在しない内容（安定して生活など）を生成しない"""
    contract_a = auth_setup["contract_a"]

    # 一次情報が何もない状態でプレビューを構築
    preview = JobRetentionService.build_monthly_report_preview(contract_a.id, "2026-09")

    # 内部整理項目
    assert "安定して生活を維持できている" not in preview["life_status_summary"]
    assert "企業からの相談・要望特になし" not in preview["employer_feedback_summary"]
    assert "定期確認実施" not in preview["support_details"]
    assert "特記すべき変化なし" not in preview["work_status_summary"]

    # 公式帳票項目
    assert preview["support_goal"] == ""
    assert preview["support_content"] == ""
    assert preview["support_result"] == ""
    assert preview["future_support_plan"] == ""
    assert preview["stakeholder_efforts"] == ""
    assert preview["sharing_notes"] == ""
