from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.app import db
from backend.app.models import User, OfficeServiceConfiguration, Supporter
from backend.app.models.core.service_certificate import ServiceCertificate, GrantedService, CopaymentLimit, MealAddonStatus, CopaymentManagement
from backend.app.models.finance.billing_compliance import ContractReportDetail
from backend.app.models.masters.master_definitions import ServiceTypeMaster
from backend.app.models.core.audit_log import AuditActionLog
from backend.app.services.core_service import check_permission, parse_jwt_identity
from datetime import datetime
import json
from . import users_bp

def check_cbac_cert(supporter_id_int, office_config_id=None, cert=None):
    supporter = db.session.get(Supporter, supporter_id_int)
    if not supporter or not supporter.office:
        return False
    
    if cert:
        if not cert.managing_service or not cert.managing_service.office:
            return False
        return supporter.office.corporation_id == cert.managing_service.office.corporation_id
    elif office_config_id:
        office_config = db.session.get(OfficeServiceConfiguration, office_config_id)
        if not office_config or not office_config.office:
            return False
        return supporter.office.corporation_id == office_config.office.corporation_id
    return False

def serialize_cert(cert, mask_pii=False):
    granted = []
    for g in cert.granted_services:
        cd_info = None
        if g.contract_detail:
            cd_info = {
                "office_service_configuration_id": g.contract_detail.office_service_configuration_id,
                "contract_office_name": g.contract_detail.contract_office_name,
                "contract_corporation_name": g.contract_detail.contract_corporation_name,
                "contract_service_type": g.contract_detail.contract_service_type,
                "contract_date": g.contract_detail.contract_date.isoformat() if g.contract_detail.contract_date else None,
                "contract_end_date": g.contract_detail.contract_end_date.isoformat() if g.contract_detail.contract_end_date else None,
                "contract_end_used_days": g.contract_detail.contract_end_used_days,
                "contract_document_url": g.contract_detail.contract_document_url,
                "important_matters_url": g.contract_detail.important_matters_url
            }
        granted.append({
            "id": g.id,
            "service_type_master_id": g.service_type_master_id,
            "granted_start_date": g.granted_start_date.isoformat() if g.granted_start_date else None,
            "granted_end_date": g.granted_end_date.isoformat() if g.granted_end_date else None,
            "granted_amount_description": g.granted_amount_description,
            "max_service_days": g.max_service_days,
            "max_service_days_type": g.max_service_days_type,
            "granted_amount_start_date": g.granted_amount_start_date.isoformat() if g.granted_amount_start_date else None,
            "granted_amount_end_date": g.granted_amount_end_date.isoformat() if g.granted_amount_end_date else None,
            "contract_detail": cd_info
        })
        
    copayments = []
    for cl in cert.copayment_limits:
        copayments.append({
            "id": cl.id,
            "limit_start_date": cl.limit_start_date.isoformat() if cl.limit_start_date else None,
            "limit_end_date": cl.limit_end_date.isoformat() if cl.limit_end_date else None,
            "limit_amount": float(cl.limit_amount) if cl.limit_amount is not None else 0.0,
            "is_management_required": cl.is_management_required
        })

    meal_addons = []
    for ma in cert.meal_addon_statuses:
        meal_addons.append({
            "id": ma.id,
            "meal_addon_start_date": ma.meal_addon_start_date.isoformat() if ma.meal_addon_start_date else None,
            "meal_addon_end_date": ma.meal_addon_end_date.isoformat() if ma.meal_addon_end_date else None,
            "is_applicable": ma.is_applicable
        })

    managements = []
    for cm in cert.copayment_management:
        managements.append({
            "id": cm.id,
            "management_start_date": cm.management_start_date.isoformat() if cm.management_start_date else None,
            "management_end_date": cm.management_end_date.isoformat() if cm.management_end_date else None,
            "is_applicable": cm.is_applicable,
            "managing_office_number": cm.managing_office_number,
            "managing_office_name": cm.managing_office_name
        })

    recipient_num = cert.recipient_number
    if mask_pii and recipient_num and len(recipient_num) > 2:
        recipient_num = recipient_num[0] + "*" * (len(recipient_num) - 2) + recipient_num[-1]
    elif mask_pii and recipient_num:
        recipient_num = "***"

    return {
        "id": cert.id,
        "certificate_issue_date": cert.certificate_issue_date.isoformat() if cert.certificate_issue_date else None,
        "municipality_master_id": cert.municipality_master_id,
        "certificate_type": cert.certificate_type,
        "disability_support_classification": cert.disability_support_classification,
        "certificate_notes": cert.certificate_notes,
        "recipient_number": recipient_num,
        "office_service_configuration_id": cert.office_service_configuration_id,
        "granted_services": granted,
        "copayment_limits": copayments,
        "meal_addon_statuses": meal_addons,
        "copayment_managements": managements,
        "status": cert.status,
        "created_by_supporter_id": cert.created_by_supporter_id,
        "submitted_by_supporter_id": cert.submitted_by_supporter_id,
        "reviewed_by_supporter_id": cert.reviewed_by_supporter_id,
        "reviewed_at": cert.reviewed_at.isoformat() if cert.reviewed_at else None,
        "review_reason": cert.review_reason,
        "voided_by_supporter_id": cert.voided_by_supporter_id,
        "voided_at": cert.voided_at.isoformat() if cert.voided_at else None,
        "void_reason": cert.void_reason
    }

@users_bp.route('/<int:user_id>/certificates', methods=['POST'])
@jwt_required()
def add_service_certificate(user_id):
    """
    受給者証情報の新規作成。
    """
    current_supporter_id = get_jwt_identity()
    if not check_permission(current_supporter_id, 'VIEW_PII'):
        return jsonify({"msg": "Permission denied"}), 403

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"msg": "Invalid data"}), 400

    try:
        office_config_id = data.get('office_service_configuration_id')
        _, supporter_id_int = parse_jwt_identity(current_supporter_id)

        if not office_config_id:
            return jsonify({"msg": "office_service_configuration_id is required"}), 400

        if not check_cbac_cert(supporter_id_int, office_config_id=office_config_id):
            return jsonify({"msg": "CBAC: この事業所コンテキストでの受給者証作成権限がありません"}), 403
        
        status = data.get('status', 'DRAFT')
        if status not in ('DRAFT', 'PENDING_REVIEW'):
            status = 'DRAFT'
            
        submitted_by = None
        if status == 'PENDING_REVIEW':
            submitted_by = supporter_id_int

        cert = ServiceCertificate(
            user_id=user.id,
            office_service_configuration_id=office_config_id,
            certificate_issue_date=datetime.strptime(data['certificate_issue_date'], '%Y-%m-%d').date() if data.get('certificate_issue_date') else datetime.utcnow().date(),
            municipality_master_id=data.get('municipality_master_id', 1),
            certificate_type=data.get('certificate_type'),
            disability_support_classification=data.get('disability_support_classification'),
            recipient_number=data.get('recipient_number'),
            certificate_notes=data.get('certificate_notes'),
            status=status,
            created_by_supporter_id=supporter_id_int,
            submitted_by_supporter_id=submitted_by
        )
        db.session.add(cert)
        db.session.flush()

        # 1. granted_services
        for g in data.get('granted_services', []):
            granted = GrantedService(
                certificate_id=cert.id,
                service_type_master_id=g.get('service_type_master_id', 1),
                granted_start_date=datetime.strptime(g['granted_start_date'], '%Y-%m-%d').date() if g.get('granted_start_date') else datetime.utcnow().date(),
                granted_end_date=datetime.strptime(g['granted_end_date'], '%Y-%m-%d').date() if g.get('granted_end_date') else datetime.utcnow().date(),
                granted_amount_description=g.get('granted_amount_description'),
                max_service_days=int(g['max_service_days']) if g.get('max_service_days') is not None else None,
                max_service_days_type=g.get('max_service_days_type', 'FIXED'),
                granted_amount_start_date=datetime.strptime(g['granted_amount_start_date'], '%Y-%m-%d').date() if g.get('granted_amount_start_date') else None,
                granted_amount_end_date=datetime.strptime(g['granted_amount_end_date'], '%Y-%m-%d').date() if g.get('granted_amount_end_date') else None
            )
            db.session.add(granted)
            db.session.flush()

            cd = g.get('contract_detail')
            if cd:
                osc_id = cd.get('office_service_configuration_id')
                contract_office_name = None
                contract_corporation_name = None
                contract_service_type = None

                if osc_id:
                    osc = db.session.get(OfficeServiceConfiguration, osc_id)
                    if osc:
                        contract_office_name = osc.office.office_name
                        if osc.office.corporation:
                            contract_corporation_name = osc.office.corporation.corporation_name
                        st = db.session.get(ServiceTypeMaster, osc.service_type_master_id)
                        if st:
                            contract_service_type = st.name

                contract_detail = ContractReportDetail(
                    granted_service_id=granted.id,
                    office_service_configuration_id=osc_id,
                    contract_corporation_name=contract_corporation_name,
                    contract_office_name=contract_office_name,
                    contract_service_type=contract_service_type,
                    contract_granted_days=int(cd['contract_granted_days']) if cd.get('contract_granted_days') is not None else None,
                    contract_date=datetime.strptime(cd['contract_date'], '%Y-%m-%d').date() if cd.get('contract_date') else None,
                    contract_end_date=datetime.strptime(cd['contract_end_date'], '%Y-%m-%d').date() if cd.get('contract_end_date') else None,
                    contract_end_used_days=int(cd['contract_end_used_days']) if cd.get('contract_end_used_days') is not None else None,
                    contract_document_url=cd.get('contract_document_url'),
                    important_matters_url=cd.get('important_matters_url')
                )
                db.session.add(contract_detail)

        # 2. copayment_limits
        for cl in data.get('copayment_limits', []):
            limit = CopaymentLimit(
                certificate_id=cert.id,
                limit_start_date=datetime.strptime(cl['limit_start_date'], '%Y-%m-%d').date() if cl.get('limit_start_date') else None,
                limit_end_date=datetime.strptime(cl['limit_end_date'], '%Y-%m-%d').date() if cl.get('limit_end_date') else None,
                limit_amount=float(cl['limit_amount']) if cl.get('limit_amount') is not None else 0.0,
                is_management_required=bool(cl.get('is_management_required', False))
            )
            db.session.add(limit)

        # 3. meal_addon_statuses
        for ma in data.get('meal_addon_statuses', []):
            addon = MealAddonStatus(
                certificate_id=cert.id,
                meal_addon_start_date=datetime.strptime(ma['meal_addon_start_date'], '%Y-%m-%d').date() if ma.get('meal_addon_start_date') else None,
                meal_addon_end_date=datetime.strptime(ma['meal_addon_end_date'], '%Y-%m-%d').date() if ma.get('meal_addon_end_date') else None,
                is_applicable=bool(ma.get('is_applicable', False))
            )
            db.session.add(addon)

        # 4. copayment_managements
        for cm in data.get('copayment_managements', []):
            mgmt = CopaymentManagement(
                certificate_id=cert.id,
                management_start_date=datetime.strptime(cm['management_start_date'], '%Y-%m-%d').date() if cm.get('management_start_date') else None,
                management_end_date=datetime.strptime(cm['management_end_date'], '%Y-%m-%d').date() if cm.get('management_end_date') else None,
                is_applicable=bool(cm.get('is_applicable', False)),
                managing_office_number=cm.get('managing_office_number'),
                managing_office_name=cm.get('managing_office_name')
            )
            db.session.add(mgmt)

        db.session.flush()

        after_serialized = json.dumps(serialize_cert(cert, mask_pii=True), ensure_ascii=False)
        _, supporter_id_int = parse_jwt_identity(current_supporter_id)
        audit_log = AuditActionLog(
            actor_supporter_id=supporter_id_int,
            action='CREATE_CERTIFICATE',
            entity_type='service_certificate',
            entity_id=cert.id,
            before_value=None,
            after_value=after_serialized,
            reason="受給者証情報の新規登録"
        )
        db.session.add(audit_log)

        db.session.commit()
        return jsonify({"msg": "Certificate added successfully", "id": cert.id}), 201

    except Exception as e:
        db.session.rollback()
        import logging
        logging.error(f"Certificate Error: {str(e)}")
        return jsonify({"msg": f"保存に失敗しました: {str(e)}"}), 500

@users_bp.route('/<int:user_id>/certificates/<int:cert_id>', methods=['PUT'])
@jwt_required()
def update_service_certificate(user_id, cert_id):
    """
    既存の受給者証情報および支給決定内容を修正する。
    """
    current_supporter_id = get_jwt_identity()
    if not check_permission(current_supporter_id, 'EDIT_PII'):
        return jsonify({"msg": "Permission denied"}), 403

    user = db.session.get(User, user_id)
    cert = db.session.get(ServiceCertificate, cert_id)
    if not user or not cert or cert.user_id != user.id:
        return jsonify({"msg": "Certificate not found"}), 404

    _, supporter_id_int = parse_jwt_identity(current_supporter_id)
    if not check_cbac_cert(supporter_id_int, cert=cert):
        return jsonify({"msg": "CBAC: この受給者証を編集する権限がありません"}), 403

    if cert.status not in ('DRAFT', 'REJECTED'):
        return jsonify({"msg": "下書きまたは却下状態の受給者証のみ編集可能です。"}), 400

    data = request.get_json()
    if not data:
        return jsonify({"msg": "Invalid data"}), 400

    # 1. update_reason Validation (optional, defaults if empty)
    update_reason = data.get('update_reason')
    if not update_reason:
        update_reason = "受給者証の更新"

    try:
        before_serialized = json.dumps(serialize_cert(cert, mask_pii=True), ensure_ascii=False)
        _, supporter_id_int = parse_jwt_identity(current_supporter_id)

        # Update status and submitted_by if PENDING_REVIEW is selected
        status = data.get('status')
        if status == 'PENDING_REVIEW':
            cert.status = 'PENDING_REVIEW'
            cert.submitted_by_supporter_id = supporter_id_int
        else:
            cert.status = 'DRAFT'

        # Update core fields
        if data.get('certificate_issue_date'):
            cert.certificate_issue_date = datetime.strptime(data['certificate_issue_date'], '%Y-%m-%d').date()
        if 'municipality_master_id' in data:
            cert.municipality_master_id = data['municipality_master_id']
        if 'certificate_type' in data:
            cert.certificate_type = data['certificate_type']
        if 'disability_support_classification' in data:
            cert.disability_support_classification = data['disability_support_classification']
        if 'recipient_number' in data:
            cert.recipient_number = data['recipient_number']
        if 'certificate_notes' in data:
            cert.certificate_notes = data['certificate_notes']
        if 'office_service_configuration_id' in data:
            cert.office_service_configuration_id = data['office_service_configuration_id']

        # Clear child tables (洗い替え)
        gs_ids = [gs.id for gs in cert.granted_services.all()]
        if gs_ids:
            ContractReportDetail.query.filter(ContractReportDetail.granted_service_id.in_(gs_ids)).delete(synchronize_session=False)
        cert.granted_services.delete()
        cert.copayment_limits.delete()
        cert.meal_addon_statuses.delete()
        cert.copayment_management.delete()
        db.session.flush()

        # Add child tables back
        # 1. granted_services
        for g in data.get('granted_services', []):
            granted = GrantedService(
                certificate_id=cert.id,
                service_type_master_id=g.get('service_type_master_id', 1),
                granted_start_date=datetime.strptime(g['granted_start_date'], '%Y-%m-%d').date() if g.get('granted_start_date') else datetime.utcnow().date(),
                granted_end_date=datetime.strptime(g['granted_end_date'], '%Y-%m-%d').date() if g.get('granted_end_date') else datetime.utcnow().date(),
                granted_amount_description=g.get('granted_amount_description'),
                max_service_days=int(g['max_service_days']) if g.get('max_service_days') is not None else None,
                max_service_days_type=g.get('max_service_days_type', 'FIXED'),
                granted_amount_start_date=datetime.strptime(g['granted_amount_start_date'], '%Y-%m-%d').date() if g.get('granted_amount_start_date') else None,
                granted_amount_end_date=datetime.strptime(g['granted_amount_end_date'], '%Y-%m-%d').date() if g.get('granted_amount_end_date') else None
            )
            db.session.add(granted)
            db.session.flush()

            cd = g.get('contract_detail')
            if cd:
                osc_id = cd.get('office_service_configuration_id')
                contract_office_name = None
                contract_corporation_name = None
                contract_service_type = None

                if osc_id:
                    osc = db.session.get(OfficeServiceConfiguration, osc_id)
                    if osc:
                        contract_office_name = osc.office.office_name
                        if osc.office.corporation:
                            contract_corporation_name = osc.office.corporation.corporation_name
                        st = db.session.get(ServiceTypeMaster, osc.service_type_master_id)
                        if st:
                            contract_service_type = st.name

                contract_detail = ContractReportDetail(
                    granted_service_id=granted.id,
                    office_service_configuration_id=osc_id,
                    contract_corporation_name=contract_corporation_name,
                    contract_office_name=contract_office_name,
                    contract_service_type=contract_service_type,
                    contract_granted_days=int(cd['contract_granted_days']) if cd.get('contract_granted_days') is not None else None,
                    contract_date=datetime.strptime(cd['contract_date'], '%Y-%m-%d').date() if cd.get('contract_date') else None,
                    contract_end_date=datetime.strptime(cd['contract_end_date'], '%Y-%m-%d').date() if cd.get('contract_end_date') else None,
                    contract_end_used_days=int(cd['contract_end_used_days']) if cd.get('contract_end_used_days') is not None else None,
                    contract_document_url=cd.get('contract_document_url'),
                    important_matters_url=cd.get('important_matters_url')
                )
                db.session.add(contract_detail)

        # 2. copayment_limits
        for cl in data.get('copayment_limits', []):
            limit = CopaymentLimit(
                certificate_id=cert.id,
                limit_start_date=datetime.strptime(cl['limit_start_date'], '%Y-%m-%d').date() if cl.get('limit_start_date') else None,
                limit_end_date=datetime.strptime(cl['limit_end_date'], '%Y-%m-%d').date() if cl.get('limit_end_date') else None,
                limit_amount=float(cl['limit_amount']) if cl.get('limit_amount') is not None else 0.0,
                is_management_required=bool(cl.get('is_management_required', False))
            )
            db.session.add(limit)

        # 3. meal_addon_statuses
        for ma in data.get('meal_addon_statuses', []):
            addon = MealAddonStatus(
                certificate_id=cert.id,
                meal_addon_start_date=datetime.strptime(ma['meal_addon_start_date'], '%Y-%m-%d').date() if ma.get('meal_addon_start_date') else None,
                meal_addon_end_date=datetime.strptime(ma['meal_addon_end_date'], '%Y-%m-%d').date() if ma.get('meal_addon_end_date') else None,
                is_applicable=bool(ma.get('is_applicable', False))
            )
            db.session.add(addon)

        # 4. copayment_managements
        for cm in data.get('copayment_managements', []):
            mgmt = CopaymentManagement(
                certificate_id=cert.id,
                management_start_date=datetime.strptime(cm['management_start_date'], '%Y-%m-%d').date() if cm.get('management_start_date') else None,
                management_end_date=datetime.strptime(cm['management_end_date'], '%Y-%m-%d').date() if cm.get('management_end_date') else None,
                is_applicable=bool(cm.get('is_applicable', False)),
                managing_office_number=cm.get('managing_office_number'),
                managing_office_name=cm.get('managing_office_name')
            )
            db.session.add(mgmt)

        db.session.flush()

        after_serialized = json.dumps(serialize_cert(cert, mask_pii=True), ensure_ascii=False)
        _, supporter_id_int = parse_jwt_identity(current_supporter_id)

        audit_log = AuditActionLog(
            actor_supporter_id=supporter_id_int,
            action='UPDATE_CERTIFICATE',
            entity_type='service_certificate',
            entity_id=cert.id,
            before_value=before_serialized,
            after_value=after_serialized,
            reason=update_reason
        )
        db.session.add(audit_log)

        db.session.commit()
        return jsonify({"msg": "Certificate updated successfully", "id": cert.id}), 200

    except Exception as e:
        db.session.rollback()
        import logging
        logging.error(f"Certificate Update Error: {str(e)}")
        return jsonify({"msg": f"更新に失敗しました: {str(e)}"}), 500


@users_bp.route('/<int:user_id>/certificates/<int:cert_id>/submit', methods=['POST'])
@jwt_required()
def submit_service_certificate(user_id, cert_id):
    """
    受給者証情報を受領審査（確認）へ提出する。
    """
    current_supporter_id = get_jwt_identity()
    if not check_permission(current_supporter_id, 'EDIT_PII'):
        return jsonify({"msg": "Permission denied"}), 403

    user = db.session.get(User, user_id)
    cert = db.session.get(ServiceCertificate, cert_id)
    if not user or not cert or cert.user_id != user.id:
        return jsonify({"msg": "Certificate not found"}), 404

    _, supporter_id_int = parse_jwt_identity(current_supporter_id)
    if not check_cbac_cert(supporter_id_int, cert=cert):
        return jsonify({"msg": "CBAC: この受給者証の提出権限がありません"}), 403

    if cert.status not in ('DRAFT', 'REJECTED'):
        return jsonify({"msg": "下書きまたは却下状態の受給者証のみ提出可能です。"}), 400

    cert.status = 'PENDING_REVIEW'
    cert.submitted_by_supporter_id = supporter_id_int
    
    db.session.commit()
    return jsonify({"msg": "Certificate submitted for review", "status": cert.status}), 200


@users_bp.route('/<int:user_id>/certificates/<int:cert_id>/review', methods=['POST'])
@jwt_required()
def review_service_certificate(user_id, cert_id):
    """
    受給者証情報を承認または却下する。
    """
    current_supporter_id = get_jwt_identity()
    if not check_permission(current_supporter_id, 'EDIT_PII'):
        return jsonify({"msg": "Permission denied"}), 403

    user = db.session.get(User, user_id)
    cert = db.session.get(ServiceCertificate, cert_id)
    if not user or not cert or cert.user_id != user.id:
        return jsonify({"msg": "Certificate not found"}), 404

    _, supporter_id_int = parse_jwt_identity(current_supporter_id)
    if not check_cbac_cert(supporter_id_int, cert=cert):
        return jsonify({"msg": "CBAC: この受給者証の確認権限がありません"}), 403

    if cert.status != 'PENDING_REVIEW':
        return jsonify({"msg": "確認待ち状態の受給者証のみ承認・却下可能です。"}), 400

    data = request.get_json()
    if not data or 'action' not in data:
        return jsonify({"msg": "Invalid request"}), 400

    action = data['action']
    review_reason = data.get('review_reason')

    # Guardrail: Separating applicant and reviewer
    if cert.submitted_by_supporter_id == supporter_id_int:
        return jsonify({"msg": "自身が申請した受給者証の確認・承認は行えません。"}), 400

    if action == 'reject':
        if not review_reason or not review_reason.strip():
            return jsonify({"msg": "却下理由を入力してください。"}), 400
        
        cert.status = 'REJECTED'
        cert.reviewed_by_supporter_id = supporter_id_int
        cert.reviewed_at = datetime.utcnow()
        cert.review_reason = review_reason.strip()
        
        db.session.commit()
        return jsonify({"msg": "Certificate rejected", "status": cert.status}), 200

    elif action == 'approve':
        cert.status = 'ACTIVE'
        cert.reviewed_by_supporter_id = supporter_id_int
        cert.reviewed_at = datetime.utcnow()
        cert.review_reason = review_reason.strip() if review_reason else None

        # Automatic archiving logic for overlapping ACTIVE certs
        active_certs = ServiceCertificate.query.filter(
            ServiceCertificate.user_id == cert.user_id,
            ServiceCertificate.status == 'ACTIVE',
            ServiceCertificate.id != cert.id
        ).all()

        for other_cert in active_certs:
            overlap_found = False
            for other_g in other_cert.granted_services:
                for new_g in cert.granted_services:
                    if other_g.service_type_master_id == new_g.service_type_master_id:
                        # Check date overlap
                        if other_g.granted_start_date <= new_g.granted_end_date and new_g.granted_start_date <= other_g.granted_end_date:
                            overlap_found = True
                            break
                if overlap_found:
                    break
            if overlap_found:
                other_cert.status = 'ARCHIVED'

        db.session.commit()
        return jsonify({"msg": "Certificate approved", "status": cert.status}), 200

    else:
        return jsonify({"msg": "Invalid action"}), 400


@users_bp.route('/<int:user_id>/certificates/<int:cert_id>/void', methods=['POST'])
@jwt_required()
def void_service_certificate(user_id, cert_id):
    """
    受給者証情報を無効化(VOIDED)する。
    """
    current_supporter_id = get_jwt_identity()
    if not check_permission(current_supporter_id, 'EDIT_PII'):
        return jsonify({"msg": "Permission denied"}), 403

    user = db.session.get(User, user_id)
    cert = db.session.get(ServiceCertificate, cert_id)
    if not user or not cert or cert.user_id != user.id:
        return jsonify({"msg": "Certificate not found"}), 404

    # Enforce status check: ACTIVE or PENDING_REVIEW only
    if cert.status not in ('ACTIVE', 'PENDING_REVIEW'):
        return jsonify({"msg": "有効または確認待ち状態の受給者証のみ無効化可能です。"}), 400

    prefix, supporter_id_int = parse_jwt_identity(current_supporter_id)
    if not supporter_id_int or prefix != 'staff':
        return jsonify({"msg": "Permission denied"}), 403

    supporter = db.session.get(Supporter, supporter_id_int)
    if not supporter:
        return jsonify({"msg": "Supporter not found"}), 404

    if not check_cbac_cert(supporter_id_int, cert=cert):
        return jsonify({"msg": "所属する法人以外の受給者証は無効化できません。"}), 403

    # Check permission strictly: role_scope in ("SYSTEM", "CORPORATE") and is_admin == true
    is_system_admin = any(r.role_scope == 'SYSTEM' and r.is_admin for r in supporter.roles)
    is_corporate_admin = any(r.role_scope == 'CORPORATE' and r.is_admin for r in supporter.roles)

    if not (is_system_admin or is_corporate_admin):
        return jsonify({"msg": "無効化操作は管理者権限（SYSTEMまたはCORPORATE）が必要です。"}), 403


    # Get and validate void_reason
    data = request.get_json()
    if not data:
        return jsonify({"msg": "Invalid data"}), 400
    void_reason = data.get('void_reason')
    if not void_reason or not void_reason.strip():
        return jsonify({"msg": "無効化の理由を入力してください。"}), 400

    try:
        before_serialized = json.dumps(serialize_cert(cert, mask_pii=True), ensure_ascii=False)

        cert.status = 'VOIDED'
        cert.voided_by_supporter_id = supporter_id_int
        cert.voided_at = datetime.utcnow()
        cert.void_reason = void_reason.strip()

        db.session.flush()

        # Write audit log
        after_serialized = json.dumps(serialize_cert(cert, mask_pii=True), ensure_ascii=False)
        audit_log = AuditActionLog(
            actor_supporter_id=supporter_id_int,
            action='VOID_CERTIFICATE',
            entity_type='service_certificate',
            entity_id=cert.id,
            before_value=before_serialized,
            after_value=after_serialized,
            reason=void_reason.strip()
        )
        db.session.add(audit_log)

        db.session.commit()
        return jsonify({"msg": "Certificate voided successfully", "status": cert.status}), 200

    except Exception as e:
        db.session.rollback()
        import logging
        logging.error(f"Certificate Void Error: {str(e)}")
        return jsonify({"msg": f"無効化に失敗しました: {str(e)}"}), 500


