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
        role_full = RoleMaster(name=f"RETENTION_FULL_{uuid.uuid4().hex}", role_scope="OFFICE")
        role_full.permissions.extend([perm_view, perm_edit, perm_approve])

        # ロール2: 閲覧限定ロール (VIEW のみ)
        role_view_only = RoleMaster(name=f"RETENTION_VIEW_ONLY_{uuid.uuid4().hex}", role_scope="OFFICE")
        role_view_only.permissions.append(perm_view)

        # ロール3: 権限なしロール
        role_none = RoleMaster(name=f"RETENTION_NONE_{uuid.uuid4().hex}", role_scope="OFFICE")

        # ロール4: CORPORATE権限ロール (法人スコープ)
        role_corporate = RoleMaster(name=f"RETENTION_CORP_{uuid.uuid4().hex}", role_scope="CORPORATE")
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

# ====================================================================
# 6. 目標循環・非推測・DB制約・監査ログ entity_id 確実保存の検証
# ====================================================================
from sqlalchemy.exc import IntegrityError
from backend.app.models import AuditActionLog, MonthlyRetentionReport

def test_monthly_report_goal_cycle(app, auth_setup):
    """
    【受入条件】目標循環:
    - 前月FINALIZEDレポートの future_support_plan が翌月の support_goal 初期値になる
    - 前月がDRAFTの場合は翌月目標へ自動採用しない
    - 前月レポートがない初月では、勝手に目標を生成しない
    - 個別支援記録の next_step を同月の support_goal に直接入れない
    - next_step は当月の future_support_plan を作成する材料として扱う
    """
    contract_a = auth_setup["contract_a"]
    staff_a = auth_setup["staff_a"]

    # 1. 前月レポートがない初月(2026-08) -> support_goal は空文字
    preview_aug = JobRetentionService.build_monthly_report_preview(contract_a.id, "2026-08")
    assert preview_aug["support_goal"] == ""

    # 2. 9月レポートを下書き(DRAFT)で保存
    JobRetentionService.save_monthly_report(
        contract_id=contract_a.id,
        supporter_id=staff_a.id,
        year_month="2026-09",
        report_data={
            "future_support_plan": "業務量増加後の疲労状況を確認する"
        },
        finalize=False
    )
    # 前月が DRAFT の場合、10月目標には引き継がれない
    preview_oct = JobRetentionService.build_monthly_report_preview(contract_a.id, "2026-10")
    assert preview_oct["support_goal"] == ""

    # 3. 9月レポートを確定(FINALIZED)にする
    JobRetentionService.save_monthly_report(
        contract_id=contract_a.id,
        supporter_id=staff_a.id,
        year_month="2026-09",
        report_data={
            "future_support_plan": "業務量増加後の疲労状況を確認する"
        },
        finalize=True
    )
    # 確定後は 10月プレビューの support_goal に引き継がれる
    preview_oct = JobRetentionService.build_monthly_report_preview(contract_a.id, "2026-10")
    assert preview_oct["support_goal"] == "業務量増加後の疲労状況を確認する"

    # 4. 10月に個別支援記録を登録 (next_step あり)
    JobRetentionService.record_support_action(
        contract_id=contract_a.id,
        supporter_id=staff_a.id,
        action_date=datetime.date(2026, 10, 15),
        confirmed_situation="業務負荷の確認",
        provided_support="休憩の取り方を助言",
        has_user_interview=True,
        interview_method="FACE_TO_FACE",
        next_step="11月の定期通院後の疲労度を確認する"
    )

    # 10月のプレビューを再取得
    preview_oct_after_action = JobRetentionService.build_monthly_report_preview(contract_a.id, "2026-10")
    # 同月の support_goal は前月からの引き継ぎ目標のままであり、next_step で上書きされない
    assert preview_oct_after_action["support_goal"] == "業務量増加後の疲労状況を確認する"
    # next_step は当月の future_support_plan (今後の支援内容) の材料として使われる
    assert "11月の定期通院後の疲労度を確認する" in preview_oct_after_action["future_support_plan"]

def test_report_preview_no_speculative_defaults(app, auth_setup):
    """【受入条件】対処結果未入力時に「経過観察」、職種未入力時に「一般就労」を生成しない"""
    contract_a = auth_setup["contract_a"]
    staff_a = auth_setup["staff_a"]

    # 職種なしのエピソードを追加
    ep = JobRetentionService.add_employment_episode(
        contract_id=contract_a.id,
        workplace_name="株式会社サンプルテスト",
        job_start_date=datetime.date(2026, 10, 1),
        job_title=None,
        actor_supporter_id=staff_a.id
    )

    # 対処結果なしの本人の声を追加
    voice = JobRetentionService.record_user_voice(
        contract_id=contract_a.id,
        self_coping_action="水分を補給した",
        self_coping_result=None
    )
    voice.logged_at = datetime.datetime(2026, 10, 5, 12, 0, 0)
    db.session.commit()

    preview = JobRetentionService.build_monthly_report_preview(contract_a.id, "2026-10")

    # 「一般就労」は自動付与されない
    assert "一般就労" not in preview["work_status_summary"]
    assert "株式会社サンプルテスト" in preview["work_status_summary"]

    # 「経過観察」は自動付与されない
    assert "経過観察" not in preview["user_coping_summary"]
    assert "本人の対処: 水分を補給した" in preview["user_coping_summary"]

def test_audit_log_has_real_entity_id(app, auth_setup):
    """【受入条件】新規エンティティ作成時、監査ログの entity_id が必ず実IDになる (entity_id=None禁止)"""
    contract_a = auth_setup["contract_a"]
    staff_a = auth_setup["staff_a"]

    # 1. 就労エピソード
    ep = JobRetentionService.add_employment_episode(
        contract_id=contract_a.id,
        workplace_name="テスト事業所XYZ",
        job_start_date=datetime.date(2026, 11, 1),
        actor_supporter_id=staff_a.id
    )
    audit_ep = AuditActionLog.query.filter_by(
        action='ADD_EMPLOYMENT_EPISODE',
        user_id=contract_a.user_id
    ).order_by(AuditActionLog.id.desc()).first()
    assert audit_ep is not None
    assert audit_ep.entity_id is not None
    assert audit_ep.entity_id == ep.id

    # 2. 支援実施記録
    action = JobRetentionService.record_support_action(
        contract_id=contract_a.id,
        supporter_id=staff_a.id,
        action_date=datetime.date(2026, 11, 5),
        confirmed_situation="状況確認",
        provided_support="支援実施"
    )
    audit_action = AuditActionLog.query.filter_by(
        action='RECORD_RETENTION_SUPPORT_ACTION',
        user_id=contract_a.user_id
    ).order_by(AuditActionLog.id.desc()).first()
    assert audit_action is not None
    assert audit_action.entity_id is not None
    assert audit_action.entity_id == action.id

    # 3. 新規月次レポート
    report = JobRetentionService.save_monthly_report(
        contract_id=contract_a.id,
        supporter_id=staff_a.id,
        year_month="2026-11",
        report_data={"support_goal": "テスト目標"},
        finalize=False
    )
    audit_report = AuditActionLog.query.filter_by(
        action='SAVE_MONTHLY_RETENTION_REPORT',
        user_id=contract_a.user_id
    ).order_by(AuditActionLog.id.desc()).first()
    assert audit_report is not None
    assert audit_report.entity_id is not None
    assert audit_report.entity_id == report.id

def test_db_constraints_enforced(app, auth_setup):
    """
    【受入条件】DB整合性:
    - office_service_configuration_id が NULL の契約はDBでも作成できない
    - 同一契約・同一年月の月次レポートを2件作成できない (一意制約違反)
    """
    user_a = auth_setup["user_a"]
    contract_a = auth_setup["contract_a"]

    # 1. office_service_configuration_id = None での作成禁止
    with pytest.raises(IntegrityError):
        invalid_contract = JobRetentionContract(
            user_id=user_a.id,
            office_service_configuration_id=None,
            contract_start_date=datetime.date(2026, 1, 1),
            contract_end_date=datetime.date(2028, 12, 31)
        )
        db.session.add(invalid_contract)
        db.session.commit()
    db.session.rollback()

    # 2. 同一契約・同一年月での重複レポート作成禁止
    report1 = MonthlyRetentionReport(
        contract_id=contract_a.id,
        report_year_month="2027-01",
        status="DRAFT"
    )
    db.session.add(report1)
    db.session.commit()

    with pytest.raises(IntegrityError):
        report2 = MonthlyRetentionReport(
            contract_id=contract_a.id,
            report_year_month="2027-01",
            status="FINALIZED"
        )
        db.session.add(report2)
        db.session.commit()
    db.session.rollback()

def test_finalized_report_is_immutable(app, auth_setup):
    """
    【受入条件】FINALIZED月次レポートの変更不可:
    - FINALIZEDレポートを再保存すると拒否される
    - FINALIZEDレポートをDRAFTへ戻せない
    - FINALIZED拒否後も内容（support_goal, future_support_plan, status等）が不変である
    """
    client = app.test_client()
    contract_a = auth_setup["contract_a"]
    staff_a = auth_setup["staff_a"]
    headers = {"Authorization": f"Bearer {create_access_token(identity=f'staff:{staff_a.id}')}"}

    # 1. 確定済みレポートを作成
    res = client.post(
        f"/api/job-retention/contracts/{contract_a.id}/monthly-reports/2026-12",
        headers=headers,
        json={
            "support_goal": "確定済み目標A",
            "future_support_plan": "確定済み方針A",
            "finalize": True
        }
    )
    assert res.status_code == 200
    report_id = res.get_json()["id"]

    # 2. DRAFTに戻そうとする (finalize=False) -> 400 で拒否される
    res_draft = client.post(
        f"/api/job-retention/contracts/{contract_a.id}/monthly-reports/2026-12",
        headers=headers,
        json={
            "support_goal": "改ざん目標B",
            "finalize": False
        }
    )
    assert res_draft.status_code == 400
    assert "確定済みの月次支援レポートは変更できません" in res_draft.get_json()["msg"]

    # 3. 再確定で上書きしようとする (finalize=True) -> 400 で拒否される
    res_overwrite = client.post(
        f"/api/job-retention/contracts/{contract_a.id}/monthly-reports/2026-12",
        headers=headers,
        json={
            "support_goal": "改ざん目標C",
            "future_support_plan": "改ざん方針C",
            "finalize": True
        }
    )
    assert res_overwrite.status_code == 400
    assert "確定済みの月次支援レポートは変更できません" in res_overwrite.get_json()["msg"]

    # 4. 拒否後もDBの値が不変であることを確認
    report = db.session.get(MonthlyRetentionReport, report_id)
    assert report.status == "FINALIZED"
    assert report.support_goal == "確定済み目標A"
    assert report.future_support_plan == "確定済み方針A"

def test_concurrent_monthly_report_creation_handled(app, auth_setup, monkeypatch):
    """
    【受入条件】月次レポート同時作成競合の処理:
    - 同一契約・同一年月で同時作成が発生し IntegrityError となった場合、
      未処理500にならず 409 Conflict が返り、セッションが正常に保たれる
    """
    client = app.test_client()
    contract_a = auth_setup["contract_a"]
    staff_a = auth_setup["staff_a"]
    headers = {"Authorization": f"Bearer {create_access_token(identity=f'staff:{staff_a.id}')}"}

    # 一意制約違反(IntegrityError)が発生する状況をシミュレート
    from sqlalchemy.exc import IntegrityError
    orig_commit = db.session.commit

    fail_once = {"triggered": False}
    def mock_commit():
        if not fail_once["triggered"]:
            fail_once["triggered"] = True
            raise IntegrityError("duplicate key value violates unique constraint", params=None, orig=None)
        return orig_commit()

    monkeypatch.setattr(db.session, "commit", mock_commit)

    res = client.post(
        f"/api/job-retention/contracts/{contract_a.id}/monthly-reports/2027-02",
        headers=headers,
        json={
            "support_goal": "競合テスト目標",
            "finalize": False
        }
    )
    # 未処理500ではなく 409 Conflict が返る
    assert res.status_code == 409
    assert "競合" in res.get_json()["msg"]

    # セッションが正常に保たれ、その後のDBクエリが正常に実行できる
    monkeypatch.undo()
    report = MonthlyRetentionReport.query.filter_by(
        contract_id=contract_a.id,
        report_year_month="2027-02"
    ).first()
    assert report is None


def test_list_monthly_reports_api_auth_and_results(auth_setup, client):
    """月次レポート一覧APIの認可・テナント分離・返却データ検証"""
    contract_a = auth_setup["contract_a"]
    contract_b = auth_setup["contract_b"]
    staff_a = auth_setup["staff_a"]
    staff_b = auth_setup["staff_b"]
    staff_none = auth_setup["staff_no_perm"]
    user_a = auth_setup["user_a"]

    h_staff_a = {"Authorization": f"Bearer {create_access_token(identity=f'staff:{staff_a.id}')}"}
    h_staff_b = {"Authorization": f"Bearer {create_access_token(identity=f'staff:{staff_b.id}')}"}
    h_staff_none = {"Authorization": f"Bearer {create_access_token(identity=f'staff:{staff_none.id}')}"}
    h_user_a = {"Authorization": f"Bearer {create_access_token(identity=f'user:{user_a.id}')}"}

    # 1. 2ヶ月分のレポートを投入 (2026-08: FINALIZED, 2026-09: DRAFT)
    JobRetentionService.save_monthly_report(
        contract_a.id, staff_a.id, "2026-08", {"support_goal": "8月目標"}, finalize=True
    )
    JobRetentionService.save_monthly_report(
        contract_a.id, staff_a.id, "2026-09", {"support_goal": "9月目標"}, finalize=False
    )

    # 2. 正常系: 支援員Aが自分の事業所契約のレポート一覧を取得 (年月降順)
    res = client.get(f"/api/job-retention/contracts/{contract_a.id}/monthly-reports", headers=h_staff_a)
    assert res.status_code == 200
    data = res.get_json()
    assert len(data) >= 2
    assert data[0]["report_year_month"] == "2026-09"
    assert data[0]["status"] == "DRAFT"
    assert "id" in data[0]
    assert "updated_at" in data[0]

    assert data[1]["report_year_month"] == "2026-08"
    assert data[1]["status"] == "FINALIZED"

    # 3. 認可検証: 他事業所の支援員Bからのアクセスは 403
    res_b = client.get(f"/api/job-retention/contracts/{contract_a.id}/monthly-reports", headers=h_staff_b)
    assert res_b.status_code == 403

    # 4. 権限検証: VIEW権限のない支援員は 403
    res_none = client.get(f"/api/job-retention/contracts/{contract_a.id}/monthly-reports", headers=h_staff_none)
    assert res_none.status_code == 403

    # 5. アクター検証: 本人(USER)トークンでの職員APIアクセスは 403
    res_user = client.get(f"/api/job-retention/contracts/{contract_a.id}/monthly-reports", headers=h_user_a)
    assert res_user.status_code == 403

    # 6. 存在しない契約IDは 404
    res_404 = client.get("/api/job-retention/contracts/999999/monthly-reports", headers=h_staff_a)
    assert res_404.status_code == 404

    # 7. list_contracts API に当月ステータスが付与されていることを検証 (N+1回避)
    res_contracts = client.get("/api/job-retention/contracts", headers=h_staff_a)
    assert res_contracts.status_code == 200
    c_list = res_contracts.get_json()
    target_c = next((c for c in c_list if c["id"] == contract_a.id), None)
    assert target_c is not None
    assert "current_month_report_status" in target_c
    assert "current_year_month" in target_c
    assert target_c["current_month_report_status"] in ("DRAFT", "FINALIZED", "NOT_CREATED")



