"""Local account confirmation of the exact approved plan shown to its owner."""
import hashlib
import json

from backend.app.extensions import db
from backend.app.models import DocumentConsentLog, SupportPlan, User
from backend.app.services.support_plan_service import SupportPlanService
from backend.app.utils.errors import ConflictError, NotFoundError
from backend.app.utils.timezone import get_jst_today
from backend.app.services.plan_presentation import serialize_plan


def present_user_plan(plan):
    document = serialize_plan(plan)
    encoded = json.dumps(document, ensure_ascii=False, sort_keys=True).encode()
    return {**document, "revision": hashlib.sha256(encoded).hexdigest()}


def confirm_user_plan(user_id, plan_id, revision):
    # Serialize simultaneous confirmations, including two plans for the same person.
    User.query.filter_by(id=user_id).with_for_update().one()
    plan = SupportPlan.query.filter_by(user_id=user_id, id=plan_id).with_for_update().first()
    if plan is None:
        raise NotFoundError()
    proof = f"USER_ACCOUNT:{user_id}:{revision}"
    if plan.plan_status == "ACTIVE" and plan.consent_log.filter_by(consent_proof=proof).first():
        return
    if plan.plan_status != "PENDING_CONSENT" or not plan.sabikan_approved_by_id:
        raise ConflictError("現在、この計画は本人同意を受け付けていません。")
    if revision != present_user_plan(plan)["revision"]:
        raise ConflictError("計画が更新されました。もう一度内容を確認してください。")
    consent = DocumentConsentLog(user_id=user_id, document_type="SUPPORT_PLAN",
                                document_id=plan.id, consent_proof=proof)
    db.session.add(consent)
    db.session.flush()
    SupportPlanService().finalize_and_activate_plan(plan.id, consent.id)
    plan.consented_at = plan.activated_at = get_jst_today()
    db.session.commit()
