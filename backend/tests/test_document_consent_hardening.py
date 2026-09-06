# backend/tests/test_document_consent_hardening.py
"""Additional regression tests for the approved document delivery/consent design.

These tests intentionally cover security and lifecycle conditions that the original
49-case suite did not exercise.
"""

import datetime
import io

import pytest
from werkzeug.datastructures import FileStorage

from backend.app.extensions import db
from backend.app.models import (
    DocumentConsentLog,
    DocumentDeliveryLog,
    LongTermGoal,
    UserPII,
)
from backend.app.services.document_consent_service import DocumentConsentService
from backend.app.services.job_retention_service import JobRetentionService
from backend.tests.test_job_retention_auth import auth_setup, get_headers


def _ensure_login(user, *, last_name="山田", first_name="太郎"):
    if not user.pii:
        db.session.add(UserPII(
            user_id=user.id,
            last_name=last_name,
            first_name=first_name,
            password_hash="mock_hashed_password",
        ))
        db.session.flush()
    else:
        user.pii.last_name = last_name
        user.pii.first_name = first_name
        user.pii.password_hash = "mock_hashed_password"
    db.session.flush()


def _draft_plan(auth_setup, *, with_goal=False):
    contract = auth_setup["contract_a"]
    staff = auth_setup["staff_a"]
    kwargs = {}
    if with_goal:
        kwargs["long_term_goal_data"] = {"description": "長期目標の本文"}
        kwargs["short_term_goal_data"] = {"description": "短期目標の本文"}
    detail = JobRetentionService.create_or_review_support_plan(
        contract_id=contract.id,
        overall_support_goal="就労を安定して継続する",
        start_date=datetime.date(2026, 9, 1),
        plan_end_date=datetime.date(2027, 2, 28),
        supporter_id=staff.id,
        initial_status="DRAFT",
        **kwargs,
    )
    return detail.support_plan


def test_snapshot_uses_real_goal_description_fields(app, auth_setup):
    user = auth_setup["user_a"]
    _ensure_login(user)
    db.session.commit()

    plan = _draft_plan(auth_setup, with_goal=True)
    snapshot = DocumentConsentService.generate_document_snapshot("SUPPORT_PLAN", plan.id)

    assert snapshot["long_term_goals"][0]["goal_text"] == "長期目標の本文"
    short_texts = [
        goal["goal_text"]
        for goal in snapshot["long_term_goals"][0]["short_term_goals"]
    ]
    assert "短期目標の本文" in short_texts


def test_digital_delivery_requires_current_electronic_eligibility(app, auth_setup):
    user = auth_setup["user_a"]
    office = auth_setup["osc_a"].office
    _ensure_login(user)
    office.electronic_document_enabled = False
    db.session.commit()

    plan = _draft_plan(auth_setup)
    DocumentConsentService.finalize_document("SUPPORT_PLAN", plan.id, auth_setup["staff_a"].id)

    with pytest.raises(ValueError):
        DocumentConsentService.deliver_digital("SUPPORT_PLAN", plan.id, auth_setup["staff_a"].id)

    assert DocumentDeliveryLog.query.filter_by(
        document_type="SUPPORT_PLAN", document_id=plan.id, delivery_method="DIGITAL"
    ).count() == 0


def test_digital_signature_requires_exact_delivery(app, auth_setup):
    user = auth_setup["user_a"]
    office = auth_setup["osc_a"].office
    _ensure_login(user)
    office.electronic_document_enabled = True
    user.electronic_document_opt_out = False
    db.session.commit()

    plan = _draft_plan(auth_setup)
    DocumentConsentService.finalize_document("SUPPORT_PLAN", plan.id, auth_setup["staff_a"].id)

    with pytest.raises(ValueError):
        DocumentConsentService.sign_digitally("SUPPORT_PLAN", plan.id, user.id)

    delivery = DocumentConsentService.deliver_digital("SUPPORT_PLAN", plan.id, auth_setup["staff_a"].id)
    assert delivery.viewed_at is None

    log = DocumentConsentService.sign_digitally("SUPPORT_PLAN", plan.id, user.id)
    assert log.signature_method == "USER_DIGITAL"
    assert log.generated_document_url


def test_paper_signature_requires_prior_paper_delivery(app, auth_setup, tmp_path):
    user = auth_setup["user_a"]
    _ensure_login(user)
    db.session.commit()

    plan = _draft_plan(auth_setup)
    DocumentConsentService.finalize_document("SUPPORT_PLAN", plan.id, auth_setup["staff_a"].id)

    file_storage = FileStorage(
        stream=io.BytesIO(b"fake image bytes"),
        filename="signed.png",
        content_type="image/png",
    )
    with pytest.raises(ValueError):
        DocumentConsentService.upload_paper_signature(
            "SUPPORT_PLAN",
            plan.id,
            auth_setup["staff_a"].id,
            datetime.date(2026, 9, 6),
            file_storage,
            str(tmp_path),
        )

    assert DocumentConsentLog.query.filter_by(
        document_type="SUPPORT_PLAN", document_id=plan.id
    ).count() == 0


def test_user_pending_documents_excludes_undelivered_finalized_docs(app, auth_setup):
    user = auth_setup["user_a"]
    _ensure_login(user)
    auth_setup["osc_a"].office.electronic_document_enabled = True
    db.session.commit()

    plan = _draft_plan(auth_setup)
    DocumentConsentService.finalize_document("SUPPORT_PLAN", plan.id, auth_setup["staff_a"].id)

    client = app.test_client()
    res = client.get(
        "/api/user-mypage/documents/pending",
        headers=get_headers(f"user:{user.id}"),
    )
    assert res.status_code == 200
    ids = {(d["document_type"], d["document_id"]) for d in res.get_json()["pending_documents"]}
    assert ("SUPPORT_PLAN", plan.id) not in ids


def test_cross_tenant_staff_cannot_read_document_status(app, auth_setup):
    user = auth_setup["user_a"]
    _ensure_login(user)
    db.session.commit()

    plan = _draft_plan(auth_setup)
    DocumentConsentService.finalize_document("SUPPORT_PLAN", plan.id, auth_setup["staff_a"].id)

    client = app.test_client()
    res = client.get(
        f"/api/consents/documents/SUPPORT_PLAN/{plan.id}/status",
        headers=get_headers(f"staff:{auth_setup['staff_b'].id}"),
    )
    assert res.status_code == 403


def test_review_draft_does_not_shorten_old_active_plan(app, auth_setup):
    contract = auth_setup["contract_a"]
    staff = auth_setup["staff_a"]

    first = JobRetentionService.create_or_review_support_plan(
        contract_id=contract.id,
        overall_support_goal="旧版目標",
        start_date=datetime.date(2026, 9, 1),
        plan_end_date=datetime.date(2027, 2, 28),
        supporter_id=staff.id,
        initial_status="ACTIVE",
    )
    old_plan = first.support_plan
    original_end = old_plan.plan_end_date

    JobRetentionService.create_or_review_support_plan(
        contract_id=contract.id,
        overall_support_goal="新版目標",
        review_date=datetime.date(2026, 12, 1),
        review_reason="状況変化のため",
        supporter_id=staff.id,
        initial_status="DRAFT",
    )

    db.session.refresh(old_plan)
    assert old_plan.plan_status == "ACTIVE"
    assert old_plan.plan_end_date == original_end


def test_formal_plan_input_name_has_no_display_name_fallback(app, auth_setup):
    user = auth_setup["user_a"]
    # Fixture intentionally has no UserPII by default. A display_name must not become
    # the official/formal document name.
    assert user.pii is None

    data = JobRetentionService.get_plan_input_assistance_data(auth_setup["contract_a"].id)
    assert data["user_info_snapshot"]["user_name"] is None
