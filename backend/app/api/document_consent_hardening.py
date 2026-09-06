# backend/app/api/document_consent_hardening.py
"""Fail-closed hardening for the finalized-document / delivery / consent foundation.

This module is imported after the document blueprints are defined. It attaches
central access guards to those blueprints and tightens the service methods used
by the approved Slice 2 document flow without creating a second document model.
"""

import datetime
import json
import os
import uuid
from typing import Optional

from flask import request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from sqlalchemy import event, inspect as sa_inspect

from backend.app.extensions import db
from backend.app.models import (
    AuditActionLog,
    DocumentConsentLog,
    DocumentDeliveryLog,
    LongTermGoal,
    MonthlyRetentionReport,
    OfficeServiceConfiguration,
    ShortTermGoal,
    SupportPlan,
    User,
)
from backend.app.models.support.job_retention import (
    JobRetentionContract,
    RetentionSupportPlan,
    RetentionSupportPlanDetail,
    RetentionSupportPlanItem,
    RetentionSupportPlanSourceLink,
    calculate_plan_end_date,
)
from backend.app.services.core_service import check_permission, parse_jwt_identity
from backend.app.services.document_consent_service import DocumentConsentService, allowed_file
from backend.app.services.job_retention_service import JobRetentionService
from backend.app.api.consents import consents_bp, user_documents_bp
from backend.app.api.plans import plans_bp
from backend.app.api.job_retention import (
    validate_supporter_access_to_contract,
    validate_supporter_access_to_service_config,
)


@event.listens_for(DocumentConsentLog, "before_update")
def _block_signature_method_update(_mapper, _connection, target):
    """Once established, the signature method is immutable."""
    if sa_inspect(target).attrs.signature_method.history.has_changes():
        raise ValueError("確定済みの署名方法は変更できません。")


def _formal_name(user) -> Optional[str]:
    """Formal document names come only from UserPII, never display_name."""
    if not user or not user.pii:
        return None
    value = f"{user.pii.last_name or ''} {user.pii.first_name or ''}".strip()
    return value or None


def _document_context(document_type: str, document_id: int):
    """Return document, recipient user, version, and strict service-config anchor."""
    if document_type == "SUPPORT_PLAN":
        plan = db.session.get(SupportPlan, document_id)
        if not plan:
            raise ValueError("個別支援計画が見つかりません。")
        if not plan.office_service_configuration_id:
            raise ValueError("計画の事業所サービス構成が確認できません。")
        return plan, plan.user_id, plan.plan_version, plan.office_service_configuration_id

    if document_type == "RETENTION_SUPPORT_REPORT":
        report = db.session.get(MonthlyRetentionReport, document_id)
        if not report or not report.contract:
            raise ValueError("就労定着支援レポートが見つかりません。")
        if not report.contract.office_service_configuration_id:
            raise ValueError("レポートの事業所サービス構成が確認できません。")
        return report, report.contract.user_id, 1, report.contract.office_service_configuration_id

    raise ValueError(f"未対応の文書種別です: {document_type}")


def _delivery(document_type, document_id, version, user_id, method):
    return DocumentDeliveryLog.query.filter_by(
        document_type=document_type,
        document_id=document_id,
        document_version=version,
        recipient_user_id=user_id,
        delivery_method=method,
    ).first()


def _consent(document_type, document_id, version, user_id):
    return DocumentConsentLog.query.filter_by(
        document_type=document_type,
        document_id=document_id,
        document_version=version,
        user_id=user_id,
    ).first()


def _document_url(document_type: str, document_id: int, version: int) -> str:
    return f"/api/user-mypage/documents/{document_type}/{document_id}/rendered?version={version}"


def _is_retention_document(document_type: str, document) -> bool:
    return document_type == "RETENTION_SUPPORT_REPORT" or (
        document_type == "SUPPORT_PLAN" and document.retention_detail is not None
    )


def _authorize_staff_document(supporter_id: int, document_type: str, document_id: int, permission: str):
    document, _user_id, _version, service_config_id = _document_context(document_type, document_id)
    needed = f"JOB_RETENTION_{permission}" if _is_retention_document(document_type, document) else permission
    if not check_permission(f"staff:{supporter_id}", needed):
        raise PermissionError(f"必要な権限 ({needed}) がありません。")

    if _is_retention_document(document_type, document):
        contract = document.contract if document_type == "RETENTION_SUPPORT_REPORT" else document.retention_detail.contract
        validate_supporter_access_to_contract(supporter_id, contract)
    else:
        validate_supporter_access_to_service_config(supporter_id, service_config_id)


def _current_identity():
    verify_jwt_in_request()
    return parse_jwt_identity(get_jwt_identity())


# ---------------------------------------------------------------------------
# Snapshot hardening: real goal fields + formal PII name + retained fields
# ---------------------------------------------------------------------------
_original_generate_snapshot = DocumentConsentService.generate_document_snapshot


def _hardened_generate_snapshot(document_type: str, document_id: int):
    # Serializer compatibility aliases only. Persisted source remains `description`.
    if not hasattr(LongTermGoal, "goal_text"):
        LongTermGoal.goal_text = property(lambda self: self.description)
    if not hasattr(ShortTermGoal, "goal_text"):
        ShortTermGoal.goal_text = property(lambda self: self.description)

    snapshot = _original_generate_snapshot(document_type, document_id)
    document, user_id, version, _service_config_id = _document_context(document_type, document_id)
    user = db.session.get(User, user_id)
    formal = _formal_name(user)

    snapshot.setdefault("user", {})
    # Backward-compatible key, but its value is PII-only.
    snapshot["user"]["display_name"] = formal or ""
    snapshot["user"]["formal_name"] = formal or ""
    snapshot["document_version"] = version

    if document_type == "SUPPORT_PLAN" and document.retention_detail:
        rd = document.retention_detail
        r = snapshot.setdefault("retention_detail", {})
        r["user_name"] = formal
        for name in (
            "user_name_kana", "gender", "age_at_planning", "support_level",
            "disability_handbook_type", "employer_name", "employer_industry",
            "employer_address", "employer_tel", "employer_contact_person",
            "work_content", "employment_type", "wage_condition", "holiday_condition",
            "working_hours_and_break", "physical_work_environment", "human_work_environment",
            "related_support_organizations", "pre_employment_handover", "user_wishes",
            "health_condition", "living_environment_support", "retention_challenges",
            "office_name", "office_number", "office_address", "office_tel", "office_fax",
            "staff_creator_name", "staff_evaluator_name", "staff_manager_name",
            "staff_service_manager_name", "staff_job_supporter_name", "staff_explainer_name",
            "consent_confirmed", "consent_notes", "overall_evaluation", "special_notes",
            "internal_employer_wishes", "internal_overall_policy",
        ):
            r[name] = getattr(rd, name, None)
        for name in ("birth_date", "job_start_date", "explained_date", "agreed_date", "evaluation_date"):
            value = getattr(rd, name, None)
            r[name] = value.isoformat() if value else None
        r["items"] = [
            {
                "item_number": item.item_number,
                "challenge_topic": item.challenge_topic,
                "support_policy": item.support_policy,
                "support_content": item.support_content,
                "support_period_start": item.support_period_start.isoformat() if item.support_period_start else None,
                "support_period_end": item.support_period_end.isoformat() if item.support_period_end else None,
                "support_frequency": item.support_frequency,
                "role_sharing": item.role_sharing,
                "implementation_status": item.implementation_status,
                "achievement_status": item.achievement_status,
                "effectiveness_satisfaction": item.effectiveness_satisfaction,
                "remaining_challenges": item.remaining_challenges,
            }
            for item in rd.items
        ]

    return snapshot


DocumentConsentService.generate_document_snapshot = staticmethod(_hardened_generate_snapshot)


# ---------------------------------------------------------------------------
# Formal input-assistance name: PII only
# ---------------------------------------------------------------------------
_original_input_assistance = JobRetentionService.get_plan_input_assistance_data


def _hardened_input_assistance(contract_id: int):
    result = _original_input_assistance(contract_id)
    contract = db.session.get(JobRetentionContract, contract_id)
    result.setdefault("user_info_snapshot", {})["user_name"] = _formal_name(contract.user if contract else None)
    return result


JobRetentionService.get_plan_input_assistance_data = staticmethod(_hardened_input_assistance)


# ---------------------------------------------------------------------------
# Review creation: predecessor stays ACTIVE and unchanged until replacement consent
# ---------------------------------------------------------------------------
_original_create_or_review = JobRetentionService.create_or_review_support_plan


def _hardened_create_or_review_support_plan(
    contract_id: int,
    overall_support_goal: str,
    plan_end_date=None,
    next_review_deadline=None,
    review_date=None,
    review_reason=None,
    start_date=None,
    supporter_id=None,
    items_data=None,
    source_links_data=None,
    detail_fields=None,
    long_term_goal_data=None,
    short_term_goal_data=None,
    initial_status="DRAFT",
):
    contract = db.session.get(JobRetentionContract, contract_id)
    if not contract:
        raise ValueError("契約が見つかりません。")

    safe_detail = dict(detail_fields or {})
    safe_detail["user_name"] = _formal_name(contract.user)
    active_detail = JobRetentionService.get_active_support_plan(contract_id)

    # Initial creation and explicit immediate-ACTIVE compatibility flow use existing logic.
    if not active_detail or initial_status == "ACTIVE":
        return _original_create_or_review(
            contract_id=contract_id,
            overall_support_goal=overall_support_goal,
            plan_end_date=plan_end_date,
            next_review_deadline=next_review_deadline,
            review_date=review_date,
            review_reason=review_reason,
            start_date=start_date,
            supporter_id=supporter_id,
            items_data=items_data,
            source_links_data=source_links_data,
            detail_fields=safe_detail,
            long_term_goal_data=long_term_goal_data,
            short_term_goal_data=short_term_goal_data,
            initial_status=initial_status,
        )

    if not overall_support_goal or not overall_support_goal.strip():
        raise ValueError("大まかな支援目標の入力は必須です。")
    if not review_reason or not review_reason.strip():
        raise ValueError("計画見直し時は見直し理由の入力が必須です。")

    old_sp = active_detail.support_plan
    old_end = old_sp.plan_end_date
    review_d = review_date or datetime.date.today()
    new_start = review_d if review_d <= old_end else old_end + datetime.timedelta(days=1)

    target_end = plan_end_date or next_review_deadline
    max_allowed = calculate_plan_end_date(new_start)
    if target_end is None:
        target_end = max_allowed
    elif target_end > max_allowed:
        raise ValueError(
            f"計画終了予定日は計画開始日（{new_start.strftime('%Y/%m/%d')}）から暦上の6か月以内（{max_allowed.strftime('%Y/%m/%d')}まで）に設定してください。"
        )
    if target_end < new_start:
        raise ValueError("計画終了予定日は計画開始日以降の日付を設定してください。")

    new_version = old_sp.plan_version + 1
    new_sp = SupportPlan(
        user_id=contract.user_id,
        plan_version=new_version,
        plan_status=initial_status,
        plan_start_date=new_start,
        plan_end_date=target_end,
        activated_at=None,
        office_service_configuration_id=contract.office_service_configuration_id,
        created_by_id=supporter_id,
        based_on_plan_id=old_sp.id,
    )
    db.session.add(new_sp)
    db.session.flush()

    new_ltg = None
    if long_term_goal_data and (long_term_goal_data.get("description") or "").strip():
        new_ltg = LongTermGoal(
            plan_id=new_sp.id,
            description=long_term_goal_data["description"].strip(),
            challenges=long_term_goal_data.get("challenges"),
            target_period_start=new_start,
            target_period_end=target_end,
            set_year_month=long_term_goal_data.get("set_year_month"),
            target_year_month=long_term_goal_data.get("target_year_month"),
            achievement_status=long_term_goal_data.get("achievement_status"),
        )
        db.session.add(new_ltg)
        db.session.flush()

    new_stg = None
    if new_ltg and short_term_goal_data and (short_term_goal_data.get("description") or "").strip():
        new_stg = ShortTermGoal(
            long_term_goal_id=new_ltg.id,
            description=short_term_goal_data["description"].strip(),
            target_period_start=new_start,
            target_period_end=target_end,
            next_review_date=target_end,
            set_year_month=short_term_goal_data.get("set_year_month"),
            target_year_month=short_term_goal_data.get("target_year_month"),
            achievement_status=short_term_goal_data.get("achievement_status"),
        )
        db.session.add(new_stg)
        db.session.flush()

    # Inherit factual fields from the active version, then supplement only missing facts.
    for col in (
        "user_name_kana", "gender", "birth_date", "age_at_planning", "support_level",
        "disability_handbook_type", "employer_name", "employer_industry", "employer_address",
        "employer_tel", "employer_contact_person", "job_start_date", "work_content",
        "employment_type", "wage_condition", "holiday_condition", "working_hours_and_break",
        "physical_work_environment", "human_work_environment", "related_support_organizations",
        "pre_employment_handover", "user_wishes", "health_condition", "living_environment_support",
        "retention_challenges", "office_name", "office_number", "office_address", "office_tel", "office_fax",
    ):
        if col not in safe_detail:
            value = getattr(active_detail, col, None)
            if value is not None:
                safe_detail[col] = value

    assist = JobRetentionService.get_plan_input_assistance_data(contract_id)
    u = assist.get("user_info_snapshot", {})
    e = assist.get("employment_info_snapshot", {})
    o = assist.get("office_info_snapshot", {})
    safe_detail.setdefault("user_name_kana", u.get("user_name_kana"))
    safe_detail.setdefault("gender", u.get("gender"))
    if "birth_date" not in safe_detail and u.get("birth_date"):
        safe_detail["birth_date"] = datetime.date.fromisoformat(u["birth_date"])
    safe_detail.setdefault("age_at_planning", u.get("age_at_planning"))
    safe_detail.setdefault("support_level", u.get("support_level"))
    safe_detail.setdefault("disability_handbook_type", u.get("disability_handbook_type"))
    for key in ("employer_name", "employer_industry", "employer_address", "employer_tel", "employer_contact_person", "work_content"):
        safe_detail.setdefault(key, e.get(key))
    if "job_start_date" not in safe_detail and e.get("job_start_date"):
        safe_detail["job_start_date"] = datetime.date.fromisoformat(e["job_start_date"])
    for key in ("office_name", "office_number", "office_address", "office_tel", "office_fax"):
        safe_detail.setdefault(key, o.get(key))

    new_detail = RetentionSupportPlanDetail(
        support_plan_id=new_sp.id,
        retention_contract_id=contract_id,
        overall_support_goal=overall_support_goal.strip(),
        review_date=review_d,
        review_reason=review_reason.strip(),
        **{
            k: v for k, v in safe_detail.items()
            if hasattr(RetentionSupportPlanDetail, k)
            and k not in {"id", "support_plan_id", "retention_contract_id", "overall_support_goal", "review_date", "review_reason"}
        },
    )
    db.session.add(new_detail)
    db.session.flush()

    for idx, item in enumerate(items_data or []):
        p_start = item.get("support_period_start")
        p_end = item.get("support_period_end")
        if isinstance(p_start, str):
            p_start = datetime.date.fromisoformat(p_start) if p_start.strip() else None
        if isinstance(p_end, str):
            p_end = datetime.date.fromisoformat(p_end) if p_end.strip() else None
        db.session.add(RetentionSupportPlanItem(
            detail_id=new_detail.id,
            short_term_goal_id=new_stg.id if new_stg else None,
            item_number=item.get("item_number", idx + 1),
            challenge_topic=item.get("challenge_topic"),
            support_policy=item.get("support_policy"),
            support_content=item.get("support_content"),
            support_period_start=p_start,
            support_period_end=p_end,
            support_frequency=item.get("support_frequency"),
            role_sharing=item.get("role_sharing"),
            implementation_status=item.get("implementation_status"),
            achievement_status=item.get("achievement_status"),
            effectiveness_satisfaction=item.get("effectiveness_satisfaction"),
            remaining_challenges=item.get("remaining_challenges"),
        ))

    for source in source_links_data or []:
        db.session.add(RetentionSupportPlanSourceLink(
            detail_id=new_detail.id,
            target_field=source.get("target_field", "overall_support_goal"),
            source_type=source.get("source_type", "USER_VOICE"),
            source_id=source.get("source_id"),
            excerpt_text=source.get("excerpt_text"),
        ))

    db.session.add(RetentionSupportPlan(
        contract_id=contract_id,
        version=new_version,
        overall_support_goal=overall_support_goal.strip(),
        start_date=new_start,
        review_date=review_d,
        review_reason=review_reason.strip(),
        plan_end_date=target_end,
        status=initial_status,
        created_by_id=supporter_id,
    ))
    db.session.add(AuditActionLog(
        actor_supporter_id=supporter_id,
        user_id=contract.user_id,
        action="REVIEW_RETENTION_SUPPORT_PLAN",
        entity_type="SupportPlan",
        entity_id=new_sp.id,
        after_value=f"Version: {new_version} (from {old_sp.plan_version}), Goal: {overall_support_goal[:30]}, PlanEndDate: {target_end}",
        reason=f"就労定着支援計画の随時見直し（理由: {review_reason.strip()[:50]}）",
    ))
    # Old plan remains ACTIVE with its original end date until the replacement is consented.
    db.session.commit()
    return new_detail


JobRetentionService.create_or_review_support_plan = staticmethod(_hardened_create_or_review_support_plan)


# ---------------------------------------------------------------------------
# Document service hardening
# ---------------------------------------------------------------------------
_original_finalize = DocumentConsentService.finalize_document


def _hardened_finalize(document_type: str, document_id: int, supporter_id: int):
    if document_type == "SUPPORT_PLAN":
        plan = db.session.get(SupportPlan, document_id)
        if not plan:
            raise ValueError("個別支援計画が見つかりません。")
        if plan.document_snapshot is not None:
            raise ValueError("確定済みの文書は再確定できません。")
        if plan.plan_status == "PENDING_CONSENT":
            if not plan.sabikan_approved_by_id or not plan.sabikan_approved_at:
                raise ValueError("サビ管承認証跡が確認できないため確定できません。")
            plan.document_snapshot = DocumentConsentService.generate_document_snapshot(document_type, document_id)
            db.session.add(plan)
            db.session.add(AuditActionLog(
                action="DOCUMENT_FINALIZED",
                user_id=plan.user_id,
                actor_supporter_id=supporter_id,
                entity_type="SupportPlan",
                entity_id=plan.id,
                reason=f"Plan {plan.id} (v{plan.plan_version}) snapshot frozen after existing approval.",
            ))
            db.session.commit()
            return {
                "document_type": document_type,
                "document_id": plan.id,
                "plan_version": plan.plan_version,
                "status": plan.plan_status,
            }
    return _original_finalize(document_type, document_id, supporter_id)


def _hardened_deliver_digital(document_type: str, document_id: int, supporter_id: Optional[int] = None):
    document, user_id, version, service_config_id = _document_context(document_type, document_id)
    service_config = db.session.get(OfficeServiceConfiguration, service_config_id)
    if not service_config or not DocumentConsentService.can_user_sign_digitally(user_id, service_config.office_id):
        raise ValueError("現在の事業所設定または本人利用状態では電子交付できません。紙経路を使用してください。")
    if document_type == "SUPPORT_PLAN":
        if document.plan_status not in ("PENDING_CONSENT", "ACTIVE", "ARCHIVED") or not document.document_snapshot:
            raise ValueError("確定前の計画は電子交付できません。")
    else:
        if document.status != "FINALIZED" or not document.document_snapshot:
            raise ValueError("確定前のレポートは電子交付できません。")
    existing = _delivery(document_type, document_id, version, user_id, "DIGITAL")
    if existing:
        return existing
    log = DocumentDeliveryLog(
        document_type=document_type,
        document_id=document_id,
        document_version=version,
        recipient_user_id=user_id,
        delivery_method="DIGITAL",
        delivered_at=datetime.datetime.now(),
        delivered_by_supporter_id=supporter_id,
    )
    db.session.add(log)
    db.session.add(AuditActionLog(
        action="DOCUMENT_PRESENTED",
        user_id=user_id,
        actor_supporter_id=supporter_id,
        entity_type=document_type,
        entity_id=document_id,
        reason=f"{document_type} {document_id} (v{version}) delivered digitally to user {user_id}.",
    ))
    db.session.commit()
    return log


def _hardened_record_viewed(document_type: str, document_id: int, user_id: int):
    _document, target_user_id, version, _service_config_id = _document_context(document_type, document_id)
    if user_id != target_user_id:
        raise PermissionError("Forbidden: 他の利用者の文書は閲覧できません。")
    log = _delivery(document_type, document_id, version, user_id, "DIGITAL")
    if not log:
        raise ValueError("本人アカウントへ電子交付されていない文書は閲覧できません。")
    if log.viewed_at is None:
        log.viewed_at = datetime.datetime.now()
        db.session.add(log)
        db.session.commit()
    return log


def _hardened_sign_digitally(document_type: str, document_id: int, auth_user_id: int):
    document, user_id, version, service_config_id = _document_context(document_type, document_id)
    if user_id != auth_user_id:
        raise PermissionError("Forbidden: 他の利用者の文書には署名・確認できません。")
    service_config = db.session.get(OfficeServiceConfiguration, service_config_id)
    if not service_config or not DocumentConsentService.can_user_sign_digitally(user_id, service_config.office_id):
        raise ValueError("現在は電子署名経路を利用できません。紙署名経路を使用してください。")
    delivery = _delivery(document_type, document_id, version, user_id, "DIGITAL")
    if not delivery:
        raise ValueError("電子交付されていない文書には電子署名できません。")
    if delivery.viewed_at is None:
        raise ValueError("文書本文を確認してから電子署名してください。")
    if _consent(document_type, document_id, version, user_id):
        raise ValueError("この文書Versionには既に同意・確認証跡が存在します。")

    if document_type == "SUPPORT_PLAN":
        if document.plan_status != "PENDING_CONSENT" or not document.document_snapshot:
            raise ValueError("署名対象の計画が同意待ちの確定状態ではありません。")
        action, proof = "CONSENT", "USER_DIGITAL_SIGNATURE"
    else:
        if document.status != "FINALIZED" or not document.document_snapshot:
            raise ValueError("確認対象のレポートが確定状態ではありません。")
        action, proof = "ACKNOWLEDGEMENT", "USER_DIGITAL_ACK"

    now = datetime.datetime.now()
    log = DocumentConsentLog(
        user_id=user_id,
        document_type=document_type,
        document_id=document_id,
        document_version=version,
        action=action,
        signature_method="USER_DIGITAL",
        consent_timestamp=now,
        consent_proof=f"{proof}_USER_{user_id}_{uuid.uuid4().hex[:12]}",
        generated_document_url=_document_url(document_type, document_id, version),
        recorded_at=now,
    )
    db.session.add(log)
    db.session.flush()
    if document_type == "SUPPORT_PLAN":
        DocumentConsentService.activate_plan_with_consent(document, log)
    db.session.add(AuditActionLog(
        action=("DOCUMENT_SIGNED_DIGITALLY" if document_type == "SUPPORT_PLAN" else "DOCUMENT_ACKNOWLEDGED"),
        user_id=user_id,
        entity_type=("SupportPlan" if document_type == "SUPPORT_PLAN" else "MonthlyRetentionReport"),
        entity_id=document_id,
        reason=f"{document_type} {document_id} (v{version}) completed by USER_DIGITAL.",
    ))
    db.session.commit()
    return log


def _hardened_upload_paper_signature(document_type, document_id, supporter_id, signed_at, file_storage, upload_folder):
    if not file_storage or not file_storage.filename or not file_storage.filename.strip():
        raise ValueError("紙署名済みの証拠ファイル（画像またはPDF）は必須です。")
    if not allowed_file(file_storage.filename):
        raise ValueError("証拠ファイルは画像（png, jpg, jpeg）またはPDF形式でアップロードしてください。")
    document, user_id, version, _service_config_id = _document_context(document_type, document_id)
    if not _delivery(document_type, document_id, version, user_id, "PAPER"):
        raise ValueError("紙交付記録がない文書には紙署名証跡を登録できません。")
    if _consent(document_type, document_id, version, user_id):
        raise ValueError("この文書Versionには既に同意・確認証跡が存在します。")
    if document_type == "SUPPORT_PLAN":
        if document.plan_status != "PENDING_CONSENT" or not document.document_snapshot:
            raise ValueError("サビ管承認・文書確定が完了していない計画には紙署名証跡を登録できません。")
        action, proof = "CONSENT", "PAPER_SIGNED_ON"
    else:
        if document.status != "FINALIZED" or not document.document_snapshot:
            raise ValueError("確定していないレポートには紙確認証跡を登録できません。")
        action, proof = "ACKNOWLEDGEMENT", "PAPER_ACK_ON"

    ext = file_storage.filename.rsplit(".", 1)[1].lower()
    name = f"{document_type}_{document_id}_{uuid.uuid4().hex}.{ext}"
    os.makedirs(upload_folder, exist_ok=True)
    path = os.path.join(upload_folder, name)
    file_storage.save(path)
    evidence_url = f"/api/consents/evidence/{name}"
    signed_dt = datetime.datetime.combine(signed_at, datetime.time(12, 0))
    log = DocumentConsentLog(
        user_id=user_id,
        document_type=document_type,
        document_id=document_id,
        document_version=version,
        action=action,
        signature_method="PAPER_UPLOAD",
        consent_timestamp=signed_dt,
        consent_proof=f"{proof}_{signed_at.strftime('%Y%m%d')}",
        generated_document_url=_document_url(document_type, document_id, version),
        evidence_file_url=evidence_url,
        recorded_by_supporter_id=supporter_id,
        recorded_at=datetime.datetime.now(),
    )
    db.session.add(log)
    db.session.flush()
    if document_type == "SUPPORT_PLAN":
        DocumentConsentService.activate_plan_with_consent(document, log)
    db.session.add(AuditActionLog(
        action="PAPER_SIGNATURE_EVIDENCE_UPLOADED",
        user_id=user_id,
        actor_supporter_id=supporter_id,
        entity_type=("SupportPlan" if document_type == "SUPPORT_PLAN" else "MonthlyRetentionReport"),
        entity_id=document_id,
        reason=f"{document_type} {document_id} (v{version}) completed by PAPER_UPLOAD.",
    ))
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        if os.path.exists(path):
            os.remove(path)
        raise
    return log


def _hardened_activate(plan: SupportPlan, consent_log: DocumentConsentLog):
    if (
        consent_log.document_type != "SUPPORT_PLAN"
        or consent_log.document_id != plan.id
        or consent_log.document_version != plan.plan_version
        or consent_log.user_id != plan.user_id
    ):
        raise ValueError("同意証跡と計画Versionが一致しません。")
    if consent_log.signature_method not in ("USER_DIGITAL", "PAPER_UPLOAD"):
        raise ValueError("新規計画の有効化には本人電子署名または紙署名証跡が必要です。")
    if plan.plan_status != "PENDING_CONSENT" or not plan.document_snapshot:
        raise ValueError("確定済み同意待ち計画のみ有効化できます。")

    old = None
    if plan.retention_detail:
        old = (
            SupportPlan.query
            .join(RetentionSupportPlanDetail, RetentionSupportPlanDetail.support_plan_id == SupportPlan.id)
            .filter(
                RetentionSupportPlanDetail.retention_contract_id == plan.retention_detail.retention_contract_id,
                SupportPlan.id != plan.id,
                SupportPlan.plan_status == "ACTIVE",
            )
            .order_by(SupportPlan.plan_version.desc())
            .first()
        )
    elif plan.office_service_configuration_id:
        old = SupportPlan.query.filter(
            SupportPlan.user_id == plan.user_id,
            SupportPlan.office_service_configuration_id == plan.office_service_configuration_id,
            SupportPlan.id != plan.id,
            SupportPlan.plan_status == "ACTIVE",
        ).order_by(SupportPlan.plan_version.desc()).first()

    if old:
        old.plan_status = "ARCHIVED"
        if plan.plan_start_date:
            old.plan_end_date = plan.plan_start_date - datetime.timedelta(days=1)
        db.session.add(old)
        if old.retention_detail:
            legacy_old = RetentionSupportPlan.query.filter_by(
                contract_id=old.retention_detail.retention_contract_id,
                version=old.plan_version,
            ).first()
            if legacy_old:
                legacy_old.status = "ARCHIVED"
                legacy_old.plan_end_date = old.plan_end_date
                db.session.add(legacy_old)

    plan.plan_status = "ACTIVE"
    consent_date = consent_log.consent_timestamp.date()
    plan.consented_at = consent_date
    plan.explained_at = consent_date
    if not plan.activated_at:
        plan.activated_at = plan.plan_start_date or datetime.date.today()
    if plan.retention_detail:
        legacy_new = RetentionSupportPlan.query.filter_by(
            contract_id=plan.retention_detail.retention_contract_id,
            version=plan.plan_version,
        ).first()
        if legacy_new:
            legacy_new.status = "ACTIVE"
            legacy_new.start_date = plan.plan_start_date
            legacy_new.plan_end_date = plan.plan_end_date
            db.session.add(legacy_new)
    db.session.add(plan)


DocumentConsentService.finalize_document = staticmethod(_hardened_finalize)
DocumentConsentService.deliver_digital = staticmethod(_hardened_deliver_digital)
DocumentConsentService.record_document_viewed = staticmethod(_hardened_record_viewed)
DocumentConsentService.sign_digitally = staticmethod(_hardened_sign_digitally)
DocumentConsentService.upload_paper_signature = staticmethod(_hardened_upload_paper_signature)
DocumentConsentService.activate_plan_with_consent = staticmethod(_hardened_activate)


# ---------------------------------------------------------------------------
# Blueprint-level access control: actor, RBAC, tenant anchor, exact delivery
# ---------------------------------------------------------------------------
@consents_bp.before_request
def _guard_consents_blueprint():
    role, actor_id = _current_identity()
    endpoint = request.endpoint or ""
    doc_type = (request.view_args or {}).get("doc_type")
    doc_id = (request.view_args or {}).get("doc_id")

    if endpoint.endswith("digital_sign_api"):
        if role != "user":
            return {"msg": "Forbidden: 本人アカウントのみ電子署名可能です。"}, 403
        return None

    if endpoint.endswith("paper_upload_api"):
        if role != "staff":
            return {"msg": "Forbidden: 職員のみ紙署名証跡を登録可能です。"}, 403
        form_type = request.form.get("document_type")
        form_id = request.form.get("document_id")
        try:
            _authorize_staff_document(actor_id, form_type, int(form_id), "EDIT")
        except Exception as exc:
            return {"msg": str(exc)}, 403
        return None

    if endpoint.endswith("get_evidence_file"):
        filename = (request.view_args or {}).get("filename")
        evidence_url = f"/api/consents/evidence/{filename}"
        consent = DocumentConsentLog.query.filter_by(evidence_file_url=evidence_url).first()
        if not consent:
            return {"msg": "証拠ファイルが見つかりません。"}, 404
        if role == "user":
            if consent.user_id != actor_id:
                return {"msg": "Forbidden"}, 403
        elif role == "staff":
            try:
                _authorize_staff_document(actor_id, consent.document_type, consent.document_id, "VIEW")
            except Exception as exc:
                return {"msg": str(exc)}, 403
        else:
            return {"msg": "Forbidden"}, 403
        return None

    if doc_type and doc_id:
        try:
            document, user_id, version, _service_config_id = _document_context(doc_type, doc_id)
        except ValueError as exc:
            return {"msg": str(exc)}, 400

        if role == "staff":
            permission = "VIEW" if endpoint.endswith("get_document_status_api") else (
                "APPROVE" if endpoint.endswith("finalize_document_api") else "EDIT"
            )
            try:
                _authorize_staff_document(actor_id, doc_type, doc_id, permission)
            except Exception as exc:
                return {"msg": str(exc)}, 403
        elif role == "user":
            if endpoint.endswith("get_document_status_api"):
                if actor_id != user_id or not _delivery(doc_type, doc_id, version, user_id, "DIGITAL"):
                    return {"msg": "Forbidden: 電子交付された本人文書のみ参照できます。"}, 403
            else:
                return {"msg": "Forbidden"}, 403
        else:
            return {"msg": "Forbidden"}, 403
    return None


@user_documents_bp.before_request
def _guard_user_documents_blueprint():
    role, actor_id = _current_identity()
    endpoint = request.endpoint or ""
    if endpoint.endswith("get_user_pending_documents") or endpoint.endswith("get_user_delivered_documents"):
        if role != "user":
            return {"msg": "Forbidden: 本人アカウントのみアクセス可能です。"}, 403
        return None

    if endpoint.endswith("get_rendered_document"):
        doc_type = (request.view_args or {}).get("doc_type")
        doc_id = (request.view_args or {}).get("doc_id")
        try:
            document, user_id, version, _service_config_id = _document_context(doc_type, doc_id)
        except ValueError as exc:
            return {"msg": str(exc)}, 400
        if role == "user":
            if actor_id != user_id:
                return {"msg": "Forbidden: 他の利用者の文書は閲覧できません。"}, 403
            if not _delivery(doc_type, doc_id, version, user_id, "DIGITAL"):
                return {"msg": "Forbidden: 本人アカウントへ電子交付されていません。"}, 403
            if not getattr(document, "document_snapshot", None):
                return {"msg": "確定版スナップショットが存在しません。"}, 409
        elif role == "staff":
            try:
                _authorize_staff_document(actor_id, doc_type, doc_id, "VIEW")
            except Exception as exc:
                return {"msg": str(exc)}, 403
        else:
            return {"msg": "Forbidden"}, 403
    return None


@user_documents_bp.after_request
def _filter_undelivered_pending(response):
    if (request.endpoint or "").endswith("get_user_pending_documents") and response.status_code == 200:
        data = response.get_json(silent=True)
        if isinstance(data, dict) and isinstance(data.get("pending_documents"), list):
            data["pending_documents"] = [d for d in data["pending_documents"] if d.get("delivered_at")]
            response.set_data(json.dumps(data, ensure_ascii=False))
            response.content_type = "application/json; charset=utf-8"
    return response


@plans_bp.before_request
def _disable_legacy_staff_consent_write():
    endpoint = request.endpoint or ""
    if endpoint.endswith("record_consent"):
        return {
            "msg": "この旧同意記録APIは廃止されました。本人電子署名または署名済み紙証跡登録を使用してください。"
        }, 410
    return None
