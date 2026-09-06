# backend/app/api/document_consent_runtime_fixes.py
"""Final runtime alignment for the approved document workflow.

Loaded after document_consent_hardening. It keeps delivery evidence separate from
consent evidence, fixes report snapshot timing, and normalizes the status payload
consumed by the document UI.
"""

import datetime
import json
import uuid

from flask import request

from backend.app.extensions import db
from backend.app.models import AuditActionLog, DocumentConsentLog, MonthlyRetentionReport, OfficeServiceConfiguration
from backend.app.services.document_consent_service import DocumentConsentService
from backend.app.api.consents import consents_bp
from backend.app.api.document_consent_hardening import (
    _consent,
    _delivery,
    _document_context,
    _document_url,
)


_previous_finalize = DocumentConsentService.finalize_document


def _finalize_with_final_report_snapshot(document_type: str, document_id: int, supporter_id: int):
    """Freeze report snapshots after status becomes FINALIZED, so the snapshot is truthful."""
    if document_type != "RETENTION_SUPPORT_REPORT":
        return _previous_finalize(document_type, document_id, supporter_id)

    report = db.session.get(MonthlyRetentionReport, document_id)
    if not report:
        raise ValueError("就労定着支援レポートが見つかりません。")
    if report.status != "DRAFT":
        raise ValueError(f"DRAFT以外のレポートは確定できません（現在: {report.status}）")
    if report.document_snapshot is not None:
        raise ValueError("確定済みの文書は再確定できません。")

    report.status = "FINALIZED"
    db.session.flush()
    report.document_snapshot = DocumentConsentService.generate_document_snapshot(document_type, document_id)
    report.document_snapshot["status"] = "FINALIZED"
    db.session.add(report)
    db.session.add(AuditActionLog(
        action="DOCUMENT_FINALIZED",
        user_id=report.contract.user_id if report.contract else None,
        actor_supporter_id=supporter_id,
        entity_type="MonthlyRetentionReport",
        entity_id=report.id,
        reason=f"Report {report.id} ({report.report_year_month}) finalized and snapshot frozen.",
    ))
    db.session.commit()
    return {
        "document_type": "RETENTION_SUPPORT_REPORT",
        "document_id": report.id,
        "status": report.status,
    }


def _sign_after_delivery(document_type: str, document_id: int, auth_user_id: int):
    """Digital consent requires exact delivery; viewing remains separately evidenced.

    The normal UI records viewed_at when the rendered A4 document is opened. The
    signature endpoint does not fabricate a view event and does not overwrite it.
    """
    document, user_id, version, service_config_id = _document_context(document_type, document_id)
    if user_id != auth_user_id:
        raise PermissionError("Forbidden: 他の利用者の文書には署名・確認できません。")

    service_config = db.session.get(OfficeServiceConfiguration, service_config_id)
    if not service_config or not DocumentConsentService.can_user_sign_digitally(user_id, service_config.office_id):
        raise ValueError("現在は電子署名経路を利用できません。紙署名経路を使用してください。")

    delivery = _delivery(document_type, document_id, version, user_id, "DIGITAL")
    if not delivery:
        raise ValueError("電子交付されていない文書には電子署名できません。")

    if _consent(document_type, document_id, version, user_id):
        raise ValueError("この文書Versionには既に同意・確認証跡が存在します。")

    if document_type == "SUPPORT_PLAN":
        if document.plan_status != "PENDING_CONSENT" or not document.document_snapshot:
            raise ValueError("署名対象の計画が同意待ちの確定状態ではありません。")
        action = "CONSENT"
        proof = "USER_DIGITAL_SIGNATURE"
    else:
        if document.status != "FINALIZED" or not document.document_snapshot:
            raise ValueError("確認対象のレポートが確定状態ではありません。")
        action = "ACKNOWLEDGEMENT"
        proof = "USER_DIGITAL_ACK"

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


DocumentConsentService.finalize_document = staticmethod(_finalize_with_final_report_snapshot)
DocumentConsentService.sign_digitally = staticmethod(_sign_after_delivery)


@consents_bp.after_request
def _normalize_document_status_response(response):
    """Expose one stable payload for the existing SignatureModal/A4 consumers."""
    if not (request.endpoint or "").endswith("get_document_status_api") or response.status_code != 200:
        return response

    payload = response.get_json(silent=True)
    if not isinstance(payload, dict):
        return response

    doc_type = (request.view_args or {}).get("doc_type")
    doc_id = (request.view_args or {}).get("doc_id")
    try:
        document, _user_id, _version, _service_config_id = _document_context(doc_type, doc_id)
    except ValueError:
        return response

    payload["doc_status"] = payload.get("status")
    payload["document_snapshot"] = getattr(document, "document_snapshot", None)

    consent_rows = payload.get("consents") or []
    if consent_rows:
        latest = consent_rows[0]
        payload["consent"] = {
            "id": latest.get("id"),
            "signature_method": latest.get("signature_method"),
            "action": latest.get("action"),
            "signed_at": latest.get("consent_timestamp"),
            "evidence_file_url": latest.get("evidence_file_url"),
            "recorded_by_name": latest.get("recorded_by_name"),
        }
    else:
        payload["consent"] = None

    response.set_data(json.dumps(payload, ensure_ascii=False, default=str))
    response.content_type = "application/json; charset=utf-8"
    return response
