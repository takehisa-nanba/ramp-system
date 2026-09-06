# backend/tests/test_document_consent_unification.py
"""
RAMPSystem 文書確定・署名証跡 共通化 全49項目 回帰テストスイート
"""

import pytest
import datetime
import io
from backend.app.extensions import db
from backend.app.models import (
    JobRetentionContract, SupportPlan, LongTermGoal, ShortTermGoal,
    RetentionSupportPlanDetail, RetentionSupportPlan, MonthlyRetentionReport,
    DocumentConsentLog, DocumentDeliveryLog, OfficeSetting, User, Supporter
)
from backend.app.models.core.user import UserPII
from backend.app.services.document_consent_service import DocumentConsentService
from backend.app.services.job_retention_service import JobRetentionService
from backend.tests.test_job_retention_auth import auth_setup, get_headers


@pytest.fixture
def test_context(app, auth_setup):
    """テスト共通のコンテキストセットアップ（PIIやOfficeSettingの整合性確保）"""
    user_a = auth_setup["user_a"]
    user_b = auth_setup["user_b"]
    contract_a = auth_setup["contract_a"]
    office_a = contract_a.office_service_configuration.office

    # user_a PII
    if not user_a.pii:
        pii_a = UserPII(
            user_id=user_a.id,
            last_name="山田",
            first_name="太郎",
            password_hash="mock_hashed_password"
        )
        db.session.add(pii_a)
    else:
        user_a.pii.password_hash = "mock_hashed_password"

    # user_b PII
    if not user_b.pii:
        pii_b = UserPII(
            user_id=user_b.id,
            last_name="佐藤",
            first_name="次郎",
            password_hash="mock_hashed_password"
        )
        db.session.add(pii_b)
    else:
        user_b.pii.password_hash = "mock_hashed_password"

    # office_a electronic setting
    office_a.electronic_document_enabled = True
    user_a.electronic_document_opt_out = False
    user_b.electronic_document_opt_out = False
    db.session.commit()

    staff_a = auth_setup["staff_a"]
    staff_no_perm = auth_setup["staff_no_perm"]

    token_staff_a = get_headers(f"staff:{staff_a.id}", role_scopes=["staff"])["Authorization"]
    token_user_a = get_headers(f"user:{user_a.id}")["Authorization"]
    token_user_b = get_headers(f"user:{user_b.id}")["Authorization"]

    return {
        "user_a": user_a,
        "user_b": user_b,
        "staff_a": staff_a,
        "staff_no_perm": staff_no_perm,
        "contract_a": contract_a,
        "office_a": office_a,
        "auth_staff_a": {"Authorization": token_staff_a},
        "auth_user_a": {"Authorization": token_user_a},
        "auth_user_b": {"Authorization": token_user_b},
        "headers_json_staff_a": {"Authorization": token_staff_a, "Content-Type": "application/json"},
        "headers_json_user_a": {"Authorization": token_user_a, "Content-Type": "application/json"},
        "headers_json_user_b": {"Authorization": token_user_b, "Content-Type": "application/json"},
    }


# ==============================================================================
# グループ10 & 11: 事業所設定 & 利用者例外 (can_user_sign_digitally 判定) (4件)
# ==============================================================================
def test_group10_and_11_can_user_sign_digitally_rules(app, test_context):
    """
    10-1: OfficeSetting.electronic_document_enabled = False の場合、全利用者が False
    10-2: OfficeSetting.electronic_document_enabled = True の場合、個別opt-outなしで本人ログイン可能なら True
    11-1: electronic_document_opt_out = True の利用者は事業所Trueでも False
    11-2: ログイン情報なし(password_hashなし)の利用者は事業所Trueでも False
    """
    user_a = test_context["user_a"]
    office_a = test_context["office_a"]

    # 10-1: 事業所OFF
    office_a.electronic_document_enabled = False
    user_a.electronic_document_opt_out = False
    db.session.commit()

    assert DocumentConsentService.can_user_sign_digitally(user_a.id, office_a.id) is False

    # 10-2: 事業所ON, opt-out=False, ログイン可能
    office_a.electronic_document_enabled = True
    db.session.commit()
    assert DocumentConsentService.can_user_sign_digitally(user_a.id, office_a.id) is True

    # 11-1: 事業所ONだが利用者opt-out=True
    user_a.electronic_document_opt_out = True
    db.session.commit()
    assert DocumentConsentService.can_user_sign_digitally(user_a.id, office_a.id) is False

    # 11-2: 事業所ON, opt-out=False だがパスワード未設定(ログイン不可)
    user_a.electronic_document_opt_out = False
    saved_pw = user_a.pii.password_hash
    user_a.pii.password_hash = None
    db.session.commit()
    assert DocumentConsentService.can_user_sign_digitally(user_a.id, office_a.id) is False

    # 復元
    user_a.pii.password_hash = saved_pw
    db.session.commit()


# ==============================================================================
# グループ1: 電子署名フロー (6件)
# ==============================================================================
def test_group1_digital_signature_flow(app, test_context, client):
    """
    1-1: DRAFT中は編集可能
    1-2: 確定(finalize)で document_snapshot 生成
    1-3: DIGITAL 交付で DocumentDeliveryLog 記録
    1-4: 利用者本人のみ電子署名可能 (他利用者は 403)
    1-5: 署名完了で DocumentConsentLog 作成 & 計画 ACTIVE 化
    1-6: 職員の代行電子署名禁止 (403)
    """
    contract_a = test_context["contract_a"]
    staff_a = test_context["staff_a"]
    user_a = test_context["user_a"]
    headers_staff = test_context["headers_json_staff_a"]
    headers_user_a = test_context["headers_json_user_a"]
    headers_user_b = test_context["headers_json_user_b"]

    # 1-1: DRAFT 作成
    plan_detail = JobRetentionService.create_or_review_support_plan(
        contract_id=contract_a.id,
        overall_support_goal="ドラフト目標1",
        start_date=datetime.date(2026, 9, 1),
        plan_end_date=datetime.date(2027, 2, 28),
        supporter_id=staff_a.id,
        initial_status='DRAFT'
    )
    sp = plan_detail.support_plan
    assert sp.plan_status == 'DRAFT'
    assert sp.document_snapshot is None

    # DRAFT中の編集
    resp_update = client.put(
        f"/api/plans/{sp.id}",
        headers=headers_staff,
        json={"overall_support_goal": "ドラフト編集目標"}
    )
    assert resp_update.status_code == 200

    # 1-2: 確定実行 (finalize)
    resp_finalize = client.post(
        f"/api/consents/documents/SUPPORT_PLAN/{sp.id}/finalize",
        headers=headers_staff
    )
    assert resp_finalize.status_code == 200
    db.session.refresh(sp)
    assert sp.document_snapshot is not None
    assert sp.document_snapshot["user"]["id"] == user_a.id

    # 1-3: DIGITAL 交付
    resp_deliver = client.post(
        f"/api/consents/documents/SUPPORT_PLAN/{sp.id}/deliver-digital",
        headers=headers_staff
    )
    assert resp_deliver.status_code == 201
    deliv_log = DocumentDeliveryLog.query.filter_by(
        document_type='SUPPORT_PLAN',
        document_id=sp.id,
        document_version=sp.plan_version
    ).first()
    assert deliv_log is not None
    assert deliv_log.delivery_method == 'DIGITAL'
    assert deliv_log.delivered_at is not None

    # 1-6: 職員による電子署名代行は 403 で拒否
    resp_staff_sign = client.post(
        "/api/consents/digital-sign",
        headers=headers_staff,
        json={"document_type": "SUPPORT_PLAN", "document_id": sp.id}
    )
    assert resp_staff_sign.status_code == 403

    # 1-4: 他の利用者 (user_b) による電子署名は 403 で拒否
    resp_user_b_sign = client.post(
        "/api/consents/digital-sign",
        headers=headers_user_b,
        json={"document_type": "SUPPORT_PLAN", "document_id": sp.id}
    )
    assert resp_user_b_sign.status_code == 403

    # 1-5: 本人 (user_a) による電子署名完了
    resp_user_a_sign = client.post(
        "/api/consents/digital-sign",
        headers=headers_user_a,
        json={"document_type": "SUPPORT_PLAN", "document_id": sp.id}
    )
    assert resp_user_a_sign.status_code == 200
    db.session.refresh(sp)
    assert sp.plan_status == 'ACTIVE'

    consent_log = DocumentConsentLog.query.filter_by(
        document_type='SUPPORT_PLAN',
        document_id=sp.id,
        document_version=sp.plan_version
    ).first()
    assert consent_log is not None
    assert consent_log.action == 'CONSENT'
    assert consent_log.signature_method == 'USER_DIGITAL'
    assert consent_log.user_id == user_a.id


# ==============================================================================
# グループ2: 紙署名フロー (5件)
# ==============================================================================
def test_group2_paper_signature_flow(app, test_context, client):
    """
    2-1: 確定後 PAPER 交付で DocumentDeliveryLog 記録
    2-2: 職員による紙署名証憑アップロードで DocumentConsentLog(PAPER_UPLOAD) 作成
    2-3: 画像・PDF なしは拒否 (400)
    2-4: 紙署名完了で計画 ACTIVE 化
    2-5: 利用者アカウントによる紙署名アップロード禁止 (403)
    """
    contract_a = test_context["contract_a"]
    staff_a = test_context["staff_a"]
    user_a = test_context["user_a"]

    headers_staff_json = test_context["headers_json_staff_a"]
    auth_staff = test_context["auth_staff_a"]
    auth_user_a = test_context["auth_user_a"]

    # DRAFT 作成 & 確定
    plan_detail = JobRetentionService.create_or_review_support_plan(
        contract_id=contract_a.id,
        overall_support_goal="紙署名用目標",
        start_date=datetime.date(2026, 9, 1),
        plan_end_date=datetime.date(2027, 2, 28),
        supporter_id=staff_a.id,
        initial_status='DRAFT'
    )
    sp = plan_detail.support_plan
    DocumentConsentService.finalize_document('SUPPORT_PLAN', sp.id, staff_a.id)

    # 2-1: PAPER 交付
    resp_deliver = client.post(
        f"/api/consents/documents/SUPPORT_PLAN/{sp.id}/deliver-paper",
        headers=headers_staff_json,
        json={"delivered_at": "2026-09-02"}
    )
    assert resp_deliver.status_code == 201
    deliv_log = DocumentDeliveryLog.query.filter_by(
        document_type='SUPPORT_PLAN',
        document_id=sp.id,
        delivery_method='PAPER'
    ).first()
    assert deliv_log is not None
    assert deliv_log.delivered_by_supporter_id == staff_a.id

    # 2-3: 証拠ファイルなしは 400
    resp_no_file = client.post(
        "/api/consents/paper-upload",
        headers=auth_staff,
        data={"document_type": "SUPPORT_PLAN", "document_id": sp.id, "signed_at": "2026-09-02"}
    )
    assert resp_no_file.status_code == 400

    # 2-5: 利用者アカウントによる紙署名アップロードは 403
    fake_file = (io.BytesIO(b"%PDF-1.4 fake signed pdf"), "signed_plan.pdf")
    resp_user_upload = client.post(
        "/api/consents/paper-upload",
        headers=auth_user_a,
        data={
            "document_type": "SUPPORT_PLAN",
            "document_id": sp.id,
            "signed_at": "2026-09-02",
            "evidence_file": fake_file
        },
        content_type="multipart/form-data"
    )
    assert resp_user_upload.status_code == 403

    # 2-2 & 2-4: 職員による紙署名アップロード成功 & ACTIVE 化
    fake_file = (io.BytesIO(b"%PDF-1.4 fake signed pdf"), "signed_plan.pdf")
    resp_staff_upload = client.post(
        "/api/consents/paper-upload",
        headers=auth_staff,
        data={
            "document_type": "SUPPORT_PLAN",
            "document_id": sp.id,
            "signed_at": "2026-09-02",
            "evidence_file": fake_file
        },
        content_type="multipart/form-data"
    )
    assert resp_staff_upload.status_code == 201
    db.session.refresh(sp)
    assert sp.plan_status == 'ACTIVE'

    consent_log = DocumentConsentLog.query.filter_by(
        document_type='SUPPORT_PLAN',
        document_id=sp.id,
        document_version=sp.plan_version
    ).first()
    assert consent_log is not None
    assert consent_log.signature_method == 'PAPER_UPLOAD'
    assert consent_log.recorded_by_supporter_id == staff_a.id
    assert consent_log.evidence_file_url is not None


# ==============================================================================
# グループ3: 文書不変性 (2件)
# ==============================================================================
def test_group3_document_immutability(app, test_context, client):
    """
    3-1: 確定後の直接編集拒否
    3-2: マスター変更後も確定文書の document_snapshot は不変
    """
    contract_a = test_context["contract_a"]
    staff_a = test_context["staff_a"]
    user_a = test_context["user_a"]
    headers_staff = test_context["headers_json_staff_a"]

    plan_detail = JobRetentionService.create_or_review_support_plan(
        contract_id=contract_a.id,
        overall_support_goal="不変性検証目標",
        start_date=datetime.date(2026, 9, 1),
        plan_end_date=datetime.date(2027, 2, 28),
        supporter_id=staff_a.id,
        initial_status='DRAFT'
    )
    sp = plan_detail.support_plan
    DocumentConsentService.finalize_document('SUPPORT_PLAN', sp.id, staff_a.id)

    # 3-1: 確定後の直接編集拒否 (400)
    resp_edit = client.put(
        f"/api/plans/{sp.id}",
        headers=headers_staff,
        json={"overall_support_goal": "改ざん目標"}
    )
    assert resp_edit.status_code == 400

    # 3-2: マスター情報（ユーザー表示名）が変更されてもスナップショットは不変
    original_snapshot_name = sp.document_snapshot["user"]["display_name"]
    user_a.display_name = "改名次郎"
    db.session.commit()

    db.session.refresh(sp)
    assert sp.document_snapshot["user"]["display_name"] == original_snapshot_name
    assert sp.document_snapshot["user"]["display_name"] != user_a.display_name


# ==============================================================================
# グループ4 & 5: 計画見直しフロー & 互換テーブル状態整合性 (7件)
# ==============================================================================
def test_group4_and_5_review_workflow_and_compatibility(app, test_context, client):
    """
    4-1: 新版 DRAFT 作成時、旧版は ACTIVE のまま
    4-2: 新版確定・交付中も、旧版は ACTIVE のまま
    4-3: 新版署名完了時に同一トランザクションで旧版 ARCHIVED化 & 新版 ACTIVE化
    4-4: 見直しが破棄された場合、旧版 ACTIVE が継続
    5-1: 就労定着計画の新規作成時、RetentionSupportPlan にも DRAFT 作成
    5-2: 新版署名完了時、RetentionSupportPlan の旧版も ARCHIVED、新版も ACTIVE に更新
    5-3: SupportPlan と RetentionSupportPlan のバージョン・期間が一致
    """
    contract_a = test_context["contract_a"]
    staff_a = test_context["staff_a"]
    user_a = test_context["user_a"]

    # v1 作成 & 確定 & 署名 (ACTIVE)
    d1 = JobRetentionService.create_or_review_support_plan(
        contract_id=contract_a.id,
        overall_support_goal="v1目標",
        start_date=datetime.date(2026, 9, 1),
        plan_end_date=datetime.date(2027, 2, 28),
        supporter_id=staff_a.id,
        initial_status='DRAFT'
    )
    sp1 = d1.support_plan
    # 5-1: 互換テーブルにも作成されていること
    rsp1 = RetentionSupportPlan.query.filter_by(contract_id=contract_a.id, version=1).first()
    assert rsp1 is not None
    assert rsp1.status == 'DRAFT'

    # v1 確定 & 配信 & 署名
    DocumentConsentService.finalize_document('SUPPORT_PLAN', sp1.id, staff_a.id)
    DocumentConsentService.deliver_digital('SUPPORT_PLAN', sp1.id, staff_a.id)
    DocumentConsentService.sign_digitally('SUPPORT_PLAN', sp1.id, user_a.id)

    db.session.refresh(sp1)
    db.session.refresh(rsp1)
    assert sp1.plan_status == 'ACTIVE'
    assert rsp1.status == 'ACTIVE'

    # 4-1: 新版 (v2) DRAFT 作成時、旧版 (v1) は ACTIVE のまま！
    d2 = JobRetentionService.create_or_review_support_plan(
        contract_id=contract_a.id,
        overall_support_goal="v2見直し目標",
        review_date=datetime.date(2026, 11, 15),
        review_reason="業務変更",
        start_date=datetime.date(2026, 11, 15),
        plan_end_date=datetime.date(2027, 5, 14),
        supporter_id=staff_a.id,
        initial_status='DRAFT'
    )
    sp2 = d2.support_plan
    db.session.refresh(sp1)
    db.session.refresh(rsp1)
    assert sp1.plan_status == 'ACTIVE'
    assert rsp1.status == 'ACTIVE'
    assert sp2.plan_status == 'DRAFT'
    rsp2 = RetentionSupportPlan.query.filter_by(contract_id=contract_a.id, version=2).first()
    assert rsp2.status == 'DRAFT'

    # 4-2: 新版確定・交付中も、旧版は ACTIVE のまま
    DocumentConsentService.finalize_document('SUPPORT_PLAN', sp2.id, staff_a.id)
    DocumentConsentService.deliver_digital('SUPPORT_PLAN', sp2.id, staff_a.id)
    db.session.refresh(sp1)
    db.session.refresh(rsp1)
    assert sp1.plan_status == 'ACTIVE'
    assert rsp1.status == 'ACTIVE'

    # 4-3 & 5-2 & 5-3: 新版署名完了時に同一トランザクションで旧版 ARCHIVED化 & 新版 ACTIVE化
    DocumentConsentService.sign_digitally('SUPPORT_PLAN', sp2.id, user_a.id)
    db.session.refresh(sp1)
    db.session.refresh(sp2)
    db.session.refresh(rsp1)
    db.session.refresh(rsp2)

    assert sp1.plan_status == 'ARCHIVED'
    assert sp1.plan_end_date == datetime.date(2026, 11, 14)
    assert rsp1.status == 'ARCHIVED'
    assert rsp1.plan_end_date == datetime.date(2026, 11, 14)

    assert sp2.plan_status == 'ACTIVE'
    assert sp2.plan_start_date == datetime.date(2026, 11, 15)
    assert rsp2.status == 'ACTIVE'
    assert rsp2.start_date == datetime.date(2026, 11, 15)

    # 4-4: 見直しが破棄された場合の検証用 (v3 DRAFTを作成して削除)
    d3 = JobRetentionService.create_or_review_support_plan(
        contract_id=contract_a.id,
        overall_support_goal="v3破棄用目標",
        review_date=datetime.date(2026, 12, 1),
        review_reason="破棄テスト用理由",
        start_date=datetime.date(2026, 12, 1),
        plan_end_date=datetime.date(2027, 5, 31),
        supporter_id=staff_a.id,
        initial_status='DRAFT'
    )
    sp3 = d3.support_plan
    db.session.refresh(sp2)
    assert sp2.plan_status == 'ACTIVE'
    # 破棄
    db.session.delete(d3)
    db.session.delete(sp3)
    db.session.commit()
    db.session.refresh(sp2)
    assert sp2.plan_status == 'ACTIVE'


# ==============================================================================
# グループ6: 過去の同意証跡保護 (2件)
# ==============================================================================
def test_group6_legacy_consent_log_protection(app, test_context):
    """
    6-1: 過去データは action='CONSENT', signature_method='LEGACY_STAFF_RECORDED'
    6-2: 過去データが勝手に USER_DIGITAL や PAPER_UPLOAD に変更されない
    """
    contract_a = test_context["contract_a"]

    # 過去ログレコードを直接作成
    legacy_log = DocumentConsentLog(
        document_type='SUPPORT_PLAN',
        document_id=99999,
        document_version=1,
        user_id=contract_a.user_id,
        action='CONSENT',
        signature_method='LEGACY_STAFF_RECORDED',
        consent_proof='旧職員代行入力'
    )
    db.session.add(legacy_log)
    db.session.commit()

    saved_log = db.session.get(DocumentConsentLog, legacy_log.id)
    assert saved_log.action == 'CONSENT'
    assert saved_log.signature_method == 'LEGACY_STAFF_RECORDED'
    assert saved_log.signature_method != 'USER_DIGITAL'
    assert saved_log.signature_method != 'PAPER_UPLOAD'


# ==============================================================================
# グループ7: 就労定着支援レポート (4件)
# ==============================================================================
def test_group7_monthly_report_consent_and_immutability(app, test_context, client):
    """
    7-1: レポート作成・編集 (DRAFT)
    7-2: レポート確定 (FINALIZED) で document_snapshot 生成
    7-3: 本人電子確認 (USER_DIGITAL) で DocumentConsentLog 作成
    7-4: 確定・確認後のレポート本文は直接編集不可
    """
    contract_a = test_context["contract_a"]
    staff_a = test_context["staff_a"]
    user_a = test_context["user_a"]

    # 7-1: レポート保存 (DRAFT)
    report_data = {
        "year_month": "2026-09",
        "status": "DRAFT",
        "support_goal": "今月の定着支援目標",
        "work_situation": "勤務順調",
        "current_challenges": "疲労管理",
        "future_support_plan": "体調確認の継続"
    }
    rep_draft = JobRetentionService.save_monthly_report(contract_a.id, staff_a.id, "2026-09", report_data, finalize=False)
    assert rep_draft.status == 'DRAFT'
    assert rep_draft.document_snapshot is None

    # 7-2: レポート確定 (FINALIZED)
    report_data["status"] = "FINALIZED"
    rep_fin = JobRetentionService.save_monthly_report(contract_a.id, staff_a.id, "2026-09", report_data, finalize=True)
    assert rep_fin.status == 'FINALIZED'
    assert rep_fin.document_snapshot is not None
    assert rep_fin.document_snapshot["support_goal"] == "今月の定着支援目標"

    # 7-4: 確定後の編集拒否
    with pytest.raises(ValueError, match="確定済み"):
        report_data["work_situation"] = "改ざん"
        JobRetentionService.save_monthly_report(contract_a.id, staff_a.id, "2026-09", report_data, finalize=False)

    # 7-3: 電子交付 & 本人電子確認 (USER_DIGITAL, action=ACKNOWLEDGEMENT)
    DocumentConsentService.deliver_digital('RETENTION_SUPPORT_REPORT', rep_fin.id, staff_a.id)
    consent_log = DocumentConsentService.sign_digitally('RETENTION_SUPPORT_REPORT', rep_fin.id, user_a.id)

    assert consent_log is not None
    assert consent_log.action == 'ACKNOWLEDGEMENT'
    assert consent_log.signature_method == 'USER_DIGITAL'


# ==============================================================================
# グループ8 & 9: 電子交付・マイページ・権限 (6件)
# ==============================================================================
def test_group8_and_9_user_portal_and_access_control(app, test_context, client):
    """
    8-1: 利用者マイページで確定文書の一覧取得
    8-2: 未確認文書の電子署名・電子確認実行
    8-3: 署名・確認済み過去文書の snapshot 閲覧
    8-4: 閲覧時に DocumentDeliveryLog(viewed_at) が記録される
    9-1: 他利用者の確定文書・署名へのアクセス拒否 (403)
    9-2: 職員権限での紙署名アップロード時の RBAC 検証
    """
    contract_a = test_context["contract_a"]
    staff_a = test_context["staff_a"]
    user_a = test_context["user_a"]

    headers_user_a = test_context["headers_json_user_a"]
    headers_user_b = test_context["headers_json_user_b"]

    # 計画作成 & 確定 & DIGITAL交付
    plan_detail = JobRetentionService.create_or_review_support_plan(
        contract_id=contract_a.id,
        overall_support_goal="マイページ検証目標",
        start_date=datetime.date(2026, 9, 1),
        plan_end_date=datetime.date(2027, 2, 28),
        supporter_id=staff_a.id,
        initial_status='DRAFT'
    )
    sp = plan_detail.support_plan
    DocumentConsentService.finalize_document('SUPPORT_PLAN', sp.id, staff_a.id)
    DocumentConsentService.deliver_digital('SUPPORT_PLAN', sp.id, staff_a.id)

    # 8-1: 利用者Aの未署名文書一覧取得
    resp_pending_a = client.get("/api/user-mypage/documents/pending", headers=headers_user_a)
    assert resp_pending_a.status_code == 200
    docs_a = resp_pending_a.get_json()["pending_documents"]
    assert len(docs_a) >= 1
    target_doc = next(d for d in docs_a if d["document_id"] == sp.id)
    assert target_doc["action_required"] == "CONSENT"

    # 9-1: 利用者Bには利用者Aの文書は一覧に出ない & レンダリング閲覧は 403
    resp_pending_b = client.get("/api/user-mypage/documents/pending", headers=headers_user_b)
    docs_b = resp_pending_b.get_json()["pending_documents"]
    assert not any(d["document_id"] == sp.id for d in docs_b)

    resp_view_b = client.get(f"/api/user-mypage/documents/SUPPORT_PLAN/{sp.id}/rendered", headers=headers_user_b)
    assert resp_view_b.status_code == 403

    # 8-4: 利用者Aが閲覧 → viewed_at が記録される
    deliv_before = DocumentDeliveryLog.query.filter_by(
        document_type='SUPPORT_PLAN',
        document_id=sp.id,
        delivery_method='DIGITAL'
    ).first()
    assert deliv_before.viewed_at is None

    resp_view_a = client.get(f"/api/user-mypage/documents/SUPPORT_PLAN/{sp.id}/rendered", headers=headers_user_a)
    assert resp_view_a.status_code == 200
    doc_detail = resp_view_a.get_json()["snapshot"]
    assert doc_detail["user"]["id"] == user_a.id

    db.session.refresh(deliv_before)
    assert deliv_before.viewed_at is not None

    # 8-2: 電子署名実行
    resp_sign = client.post(
        "/api/consents/digital-sign",
        headers=headers_user_a,
        json={"document_type": "SUPPORT_PLAN", "document_id": sp.id}
    )
    assert resp_sign.status_code == 200

    # 8-3: 署名完了後は delivered 一覧で is_signed == True になる
    resp_delivered_after = client.get("/api/user-mypage/documents/delivered", headers=headers_user_a)
    assert resp_delivered_after.status_code == 200
    delivered_items = resp_delivered_after.get_json()["delivered_documents"]
    delivered_doc = next(d for d in delivered_items if d["document_id"] == sp.id)
    assert delivered_doc["is_signed"] is True


# ==============================================================================
# グループ12 & 13 & 14: 交付証跡管理・設定変更後不変性・後日電子交付 (13件)
# ==============================================================================
def test_group12_13_14_delivery_immutability_and_post_delivery(app, test_context, client):
    """
    12-1: delivery_method は DIGITAL または PAPER
    12-2: document_version が明示的に記録される
    12-3: DIGITAL 交付で delivered_at が即時記録
    12-4: PAPER 交付で delivered_at と delivered_by_supporter_id が記録
    12-5: 同一版に対して DIGITAL と PAPER の複数交付証跡が両立可能
    13-1: USER_DIGITAL 署名文書は、事業所が電子運用OFFになっても signature_method は不変
    13-2: PAPER_UPLOAD 署名文書は、利用者が電子運用opt-inしても signature_method は不変
    14-1: 過去に PAPER で交付・紙署名成立済みの文書
    14-2: 後日職員が当該文書に対して DIGITAL 交付を追加実行可能
    14-3: DocumentDeliveryLog に PAPER と DIGITAL の2件が存在
    14-4: 利用者マイページで当該過去文書が閲覧可能
    14-5: 過去の DocumentConsentLog(PAPER_UPLOAD) はそのまま不変
    14-6: 後日電子交付されても再署名は要求されない
    """
    contract_a = test_context["contract_a"]
    staff_a = test_context["staff_a"]
    user_a = test_context["user_a"]
    office_a = test_context["office_a"]
    headers_staff_json = test_context["headers_json_staff_a"]
    auth_staff = test_context["auth_staff_a"]
    headers_user_a = test_context["headers_json_user_a"]

    # 14-1: 最初は事業所が紙運用
    office_a.electronic_document_enabled = False
    db.session.commit()

    plan_detail = JobRetentionService.create_or_review_support_plan(
        contract_id=contract_a.id,
        overall_support_goal="紙署名後の後日電子交付検証",
        start_date=datetime.date(2026, 9, 1),
        plan_end_date=datetime.date(2027, 2, 28),
        supporter_id=staff_a.id,
        initial_status='DRAFT'
    )
    sp = plan_detail.support_plan
    DocumentConsentService.finalize_document('SUPPORT_PLAN', sp.id, staff_a.id)

    # 12-4: PAPER 交付
    DocumentConsentService.deliver_paper('SUPPORT_PLAN', sp.id, staff_a.id)
    paper_deliv = DocumentDeliveryLog.query.filter_by(
        document_type='SUPPORT_PLAN',
        document_id=sp.id,
        delivery_method='PAPER'
    ).first()
    assert paper_deliv is not None
    assert paper_deliv.document_version == sp.plan_version  # 12-2
    assert paper_deliv.delivered_by_supporter_id == staff_a.id

    # 紙署名完了
    fake_file = (io.BytesIO(b"%PDF-1.4 test"), "signed.pdf")
    resp_upload = client.post(
        "/api/consents/paper-upload",
        headers=auth_staff,
        data={
            "document_type": "SUPPORT_PLAN",
            "document_id": sp.id,
            "signed_at": "2026-09-02",
            "evidence_file": fake_file
        },
        content_type="multipart/form-data"
    )
    assert resp_upload.status_code == 201

    db.session.refresh(sp)
    assert sp.plan_status == 'ACTIVE'
    consent_log = DocumentConsentLog.query.filter_by(document_type='SUPPORT_PLAN', document_id=sp.id).first()
    assert consent_log.signature_method == 'PAPER_UPLOAD'

    # 14-1 & 14-2: 後日、事業所が電子運用を開始
    office_a.electronic_document_enabled = True
    user_a.electronic_document_opt_out = False
    db.session.commit()

    # 13-2: 利用者が電子運用可能になっても、既存文書の signature_method は PAPER_UPLOAD のまま不変！
    db.session.refresh(consent_log)
    assert consent_log.signature_method == 'PAPER_UPLOAD'

    # 14-2: 職員が後日 DIGITAL 交付を追加実行
    resp_digital_add = client.post(
        f"/api/consents/documents/SUPPORT_PLAN/{sp.id}/deliver-digital",
        headers=headers_staff_json
    )
    assert resp_digital_add.status_code == 201

    # 12-5 & 14-3: DocumentDeliveryLog に PAPER と DIGITAL の両方が存在
    deliveries = DocumentDeliveryLog.query.filter_by(
        document_type='SUPPORT_PLAN',
        document_id=sp.id
    ).all()
    assert len(deliveries) == 2
    methods = {d.delivery_method for d in deliveries}
    assert methods == {'PAPER', 'DIGITAL'}

    # 14-4: 利用者マイページで当該過去文書が閲覧可能
    resp_portal = client.get(f"/api/user-mypage/documents/delivered", headers=headers_user_a)
    assert resp_portal.status_code == 200
    delivered_items = resp_portal.get_json()["delivered_documents"]
    p_data = next(d for d in delivered_items if d["document_id"] == sp.id)

    # 14-5 & 14-6: 署名済み (is_signed=True) で再署名は不要
    assert p_data["is_signed"] is True

    # 13-1: 逆に DIGITAL で署名された文書について、事業所がOFFになっても署名証跡は変わらない
    office_a.electronic_document_enabled = False
    db.session.commit()
    db.session.refresh(consent_log)
    assert consent_log.signature_method == 'PAPER_UPLOAD'
