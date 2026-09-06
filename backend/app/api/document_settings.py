# backend/app/api/document_settings.py
"""Electronic document pathway settings.

OfficeSetting defines the default policy. User stores only an opt-out exception.
The document delivery service still re-evaluates both settings and actual login
capability at delivery time; these endpoints only manage the policy inputs.
"""

from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from backend.app.extensions import db
from backend.app.models import (
    AuditActionLog,
    JobRetentionContract,
    OfficeServiceConfiguration,
    SupportPlan,
    Supporter,
    User,
)
from backend.app.services.core_service import check_permission, parse_jwt_identity
from backend.app.api.consents import consents_bp
from backend.app.api.job_retention import validate_supporter_access_to_service_config


def _staff_actor():
    role, supporter_id = parse_jwt_identity(get_jwt_identity())
    if role != "staff":
        return None
    return db.session.get(Supporter, supporter_id)


def _office_policy_admin(staff: Supporter) -> bool:
    """Office policy is writable only by an administrative role."""
    if not staff or not staff.is_active or not staff.office_id:
        return False
    return any(
        role.is_admin and role.role_scope in ("JOB", "CORPORATE", "SYSTEM")
        for role in staff.roles
    )


def _user_service_config_for_staff(user_id: int, staff: Supporter):
    """Resolve one real service-config anchor visible to the current staff.

    Fail closed when the user is not actually connected to any service context.
    The user opt-out is global, but only a staff member with a real service link to
    the user may read or change it.
    """
    if not staff:
        return None

    candidate_ids = []
    for (service_config_id,) in (
        db.session.query(SupportPlan.office_service_configuration_id)
        .filter(
            SupportPlan.user_id == user_id,
            SupportPlan.office_service_configuration_id.isnot(None),
        )
        .distinct()
        .all()
    ):
        candidate_ids.append(service_config_id)

    for (service_config_id,) in (
        db.session.query(JobRetentionContract.office_service_configuration_id)
        .filter(JobRetentionContract.user_id == user_id)
        .distinct()
        .all()
    ):
        if service_config_id not in candidate_ids:
            candidate_ids.append(service_config_id)

    for service_config_id in candidate_ids:
        try:
            validate_supporter_access_to_service_config(staff.id, service_config_id)
            return db.session.get(OfficeServiceConfiguration, service_config_id)
        except PermissionError:
            continue
    return None


@consents_bp.route('/settings/office', methods=['GET'])
@jwt_required()
def get_electronic_document_office_setting():
    staff = _staff_actor()
    if not staff or not staff.office:
        return jsonify({"msg": "Forbidden: 事業所所属職員のみ参照できます。"}), 403

    return jsonify({
        "office_id": staff.office.id,
        "office_name": staff.office.office_name,
        "electronic_document_enabled": bool(staff.office.electronic_document_enabled),
        "can_edit": _office_policy_admin(staff),
    }), 200


@consents_bp.route('/settings/office', methods=['PUT'])
@jwt_required()
def update_electronic_document_office_setting():
    staff = _staff_actor()
    if not _office_policy_admin(staff):
        return jsonify({"msg": "Forbidden: 事業所の電子文書方針を変更する管理権限がありません。"}), 403

    data = request.get_json(silent=True) or {}
    enabled = data.get("electronic_document_enabled")
    if not isinstance(enabled, bool):
        return jsonify({"msg": "electronic_document_enabled は boolean で指定してください。"}), 400

    office = staff.office
    before = bool(office.electronic_document_enabled)
    office.electronic_document_enabled = enabled
    db.session.add(office)
    db.session.flush()
    db.session.add(AuditActionLog(
        actor_supporter_id=staff.id,
        action="UPDATE_ELECTRONIC_DOCUMENT_POLICY",
        entity_type="OfficeSetting",
        entity_id=office.id,
        before_value=f"electronic_document_enabled={before}",
        after_value=f"electronic_document_enabled={enabled}",
        reason="事業所の電子交付・電子署名運用方針を変更",
    ))
    db.session.commit()

    return jsonify({
        "office_id": office.id,
        "office_name": office.office_name,
        "electronic_document_enabled": bool(office.electronic_document_enabled),
        "can_edit": True,
    }), 200


@consents_bp.route('/settings/users/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user_electronic_document_setting(user_id: int):
    staff = _staff_actor()
    if not staff or not check_permission(f"staff:{staff.id}", "VIEW_PII"):
        return jsonify({"msg": "Forbidden: 利用者設定の参照権限がありません。"}), 403

    user = db.session.get(User, user_id)
    if not user or user.deleted_at is not None:
        return jsonify({"msg": "利用者が見つかりません。"}), 404

    service_config = _user_service_config_for_staff(user_id, staff)
    if not service_config:
        return jsonify({"msg": "Forbidden: この利用者へのサービス接続を確認できません。"}), 403

    return jsonify({
        "user_id": user.id,
        "electronic_document_opt_out": bool(user.electronic_document_opt_out),
        "office_id": service_config.office_id,
        "office_electronic_document_enabled": bool(service_config.office.electronic_document_enabled),
        "effective_policy": (
            "PAPER"
            if not service_config.office.electronic_document_enabled or user.electronic_document_opt_out
            else "ELECTRONIC_IF_LOGIN_AVAILABLE"
        ),
        "can_edit": check_permission(f"staff:{staff.id}", "EDIT_PII"),
    }), 200


@consents_bp.route('/settings/users/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user_electronic_document_setting(user_id: int):
    staff = _staff_actor()
    if not staff or not check_permission(f"staff:{staff.id}", "EDIT_PII"):
        return jsonify({"msg": "Forbidden: 利用者設定の変更権限がありません。"}), 403

    user = db.session.get(User, user_id)
    if not user or user.deleted_at is not None:
        return jsonify({"msg": "利用者が見つかりません。"}), 404

    service_config = _user_service_config_for_staff(user_id, staff)
    if not service_config:
        return jsonify({"msg": "Forbidden: この利用者へのサービス接続を確認できません。"}), 403

    data = request.get_json(silent=True) or {}
    opt_out = data.get("electronic_document_opt_out")
    if not isinstance(opt_out, bool):
        return jsonify({"msg": "electronic_document_opt_out は boolean で指定してください。"}), 400

    before = bool(user.electronic_document_opt_out)
    user.electronic_document_opt_out = opt_out
    db.session.add(user)
    db.session.flush()
    db.session.add(AuditActionLog(
        actor_supporter_id=staff.id,
        user_id=user.id,
        action="UPDATE_USER_ELECTRONIC_DOCUMENT_EXCEPTION",
        entity_type="User",
        entity_id=user.id,
        before_value=f"electronic_document_opt_out={before}",
        after_value=f"electronic_document_opt_out={opt_out}",
        reason="利用者の電子交付・電子署名例外設定を変更",
    ))
    db.session.commit()

    return jsonify({
        "user_id": user.id,
        "electronic_document_opt_out": bool(user.electronic_document_opt_out),
        "office_id": service_config.office_id,
        "office_electronic_document_enabled": bool(service_config.office.electronic_document_enabled),
        "effective_policy": (
            "PAPER"
            if not service_config.office.electronic_document_enabled or user.electronic_document_opt_out
            else "ELECTRONIC_IF_LOGIN_AVAILABLE"
        ),
        "can_edit": True,
    }), 200
