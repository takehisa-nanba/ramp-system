from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.app import db
from backend.app.models import User, SupportPlan
from backend.app.services.core_service import check_permission, parse_jwt_identity
from backend.app.models.core.audit_log import AuditActionLog
from . import users_bp

@users_bp.route('/<int:user_id>/pii', methods=['GET'])
@jwt_required()
def get_user_pii(user_id):
    """
    指定された利用者のPII（個人特定可能情報）を取得する。
    権限 'VIEW_PII' が必要。
    """
    current_supporter_id = get_jwt_identity()

    can_view_pii = check_permission(current_supporter_id, 'VIEW_PII')

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404

    pii = user.pii
    if not pii:
        return jsonify({
            "id": user.id,
            "display_name": user.display_name,
            "msg": "No PII record found"
        }), 200

    if can_view_pii:
        _, supporter_id_int = parse_jwt_identity(current_supporter_id)
        audit_log = AuditActionLog(
            supporter_id=supporter_id_int,
            action_type='VIEW_PII',
            target_table='user_pii',
            target_id=user_id,
            change_details="User profile and PII decrypted & loaded onto Supporter interface"
        )
        db.session.add(audit_log)
        db.session.commit()

    active_plan = user.support_plans.filter_by(plan_status='ACTIVE').first()
    latest_plan = user.support_plans.order_by(SupportPlan.created_at.desc()).first() if user.support_plans.count() > 0 else None
    
    plan_info = None
    if active_plan:
        plan_info = {
            "id": active_plan.id,
            "status": active_plan.plan_status,
            "start_date": active_plan.plan_start_date.isoformat() if active_plan.plan_start_date else None,
            "end_date": active_plan.plan_end_date.isoformat() if active_plan.plan_end_date else None,
        }
    elif latest_plan:
        plan_info = {
            "id": latest_plan.id,
            "status": latest_plan.plan_status,
            "start_date": latest_plan.plan_start_date.isoformat() if latest_plan.plan_start_date else None,
            "end_date": latest_plan.plan_end_date.isoformat() if latest_plan.plan_end_date else None,
        }

    contacts = [
        {
            "id": c.id,
            "name": c.name if can_view_pii else "********",
            "phone_number": c.phone_number if can_view_pii else "********",
            "relation": c.relation
        } for c in user.emergency_contacts
    ]

    profile_info = {
        "emergency_contact_notes": user.profile.emergency_contact_notes if user.profile else "",
        "insurance_details": user.profile.insurance_details if user.profile else ""
    }

    from backend.app.models.core.service_certificate import ServiceCertificate
    certificates_data = []
    certs = ServiceCertificate.query.filter_by(user_id=user.id).order_by(ServiceCertificate.certificate_issue_date.desc(), ServiceCertificate.id.desc()).all()
    for cert in certs:
        granted = []
        for g in cert.granted_services:
            granted.append({
                "id": g.id,
                "service_type_master_id": g.service_type_master_id,
                "granted_start_date": g.granted_start_date.isoformat() if g.granted_start_date else None,
                "granted_end_date": g.granted_end_date.isoformat() if g.granted_end_date else None,
                "granted_amount_description": g.granted_amount_description
            })
        certificates_data.append({
            "id": cert.id,
            "certificate_issue_date": cert.certificate_issue_date.isoformat() if cert.certificate_issue_date else None,
            "municipality_master_id": cert.municipality_master_id,
            "certificate_type": cert.certificate_type,
            "disability_support_classification": cert.disability_support_classification,
            "certificate_notes": cert.certificate_notes,
            "granted_services": granted
        })

    pii_response = {}
    if can_view_pii:
        pii_response = {
            "last_name": pii.last_name,
            "first_name": pii.first_name,
            "last_name_kana": pii.last_name_kana,
            "first_name_kana": pii.first_name_kana,
            "address": pii.address,
            "certificate_number": pii.certificate_number,
            "phone_number": pii.phone_number,
            "email": pii.email,
            "birth_date": pii.birth_date.isoformat() if pii.birth_date else None
        }
    else:
        pii_response = {
            "last_name": "********",
            "first_name": "********",
            "last_name_kana": "********",
            "first_name_kana": "********",
            "address": "********",
            "certificate_number": "********",
            "phone_number": "********",
            "email": "********",
            "birth_date": None
        }

    return jsonify({
        "id": user.id,
        "display_name": user.display_name,
        "status_id": user.status_id,
        "status_name": user.status.name if user.status else None,
        "service_start_date": user.service_start_date.isoformat() if user.service_start_date else None,
        "service_end_date": user.service_end_date.isoformat() if user.service_end_date else None,
        "support_plan": plan_info,
        "emergency_contacts": contacts,
        "profile": profile_info,
        "certificates": certificates_data,
        "pii": pii_response
    }), 200

@users_bp.route('/<int:user_id>/decrypt-pii', methods=['POST'])
@jwt_required()
def decrypt_user_pii(user_id):
    """
    特定の個人情報を閲覧し、監査ログを自動記録する。
    """
    current_supporter_id = get_jwt_identity()

    if not check_permission(current_supporter_id, 'VIEW_PII'):
        return jsonify({"msg": "Permission denied: Missing 'VIEW_PII' permission"}), 403

    data = request.get_json() or {}
    pii_type = data.get('pii_type')

    user = db.session.get(User, user_id)
    if not user or not user.pii:
        return jsonify({"msg": "User or PII record not found"}), 404

    pii = user.pii
    val = ""
    if pii_type == 'phone':
        val = pii.phone_number
    elif pii_type == 'email':
        val = pii.email
    elif pii_type == 'address':
        val = pii.address
    elif pii_type == 'name':
        val = f"{pii.last_name} {pii.first_name}"
    elif pii_type == 'certificate_number':
        val = pii.certificate_number or "未登録"
    elif pii_type == 'bank_account':
        val = pii.certificate_number or "未登録"
    else:
        return jsonify({"msg": "Invalid pii_type"}), 400

    _, supporter_id_int = parse_jwt_identity(current_supporter_id)

    audit_log = AuditActionLog(
        supporter_id=supporter_id_int,
        action_type='VIEW_PII',
        target_table='user_pii',
        target_id=user_id,
        change_details=f"PII Type: {pii_type} decrypted & accessed automatically"
    )
    db.session.add(audit_log)
    db.session.commit()

    return jsonify({"value": val}), 200
