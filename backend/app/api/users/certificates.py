from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.app import db
from backend.app.models import User, OfficeServiceConfiguration
from backend.app.models.core.service_certificate import ServiceCertificate, GrantedService
from backend.app.services.core_service import check_permission
from datetime import datetime
from . import users_bp

@users_bp.route('/<int:user_id>/certificates', methods=['POST'])
@jwt_required()
def add_service_certificate(user_id):
    """
    受給者証情報の新規作成（履歴保持のためのコピー作成を含む）。
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
        office_config = OfficeServiceConfiguration.query.first()
        office_config_id = office_config.id if office_config else 1

        cert = ServiceCertificate(
            user_id=user.id,
            office_service_configuration_id=office_config_id,
            certificate_issue_date=datetime.strptime(data['certificate_issue_date'], '%Y-%m-%d').date() if data.get('certificate_issue_date') else datetime.utcnow().date(),
            municipality_master_id=data.get('municipality_master_id', 1),
            certificate_type=data.get('certificate_type'),
            disability_support_classification=data.get('disability_support_classification'),
            certificate_notes=data.get('certificate_notes')
        )
        db.session.add(cert)
        db.session.flush()

        for g in data.get('granted_services', []):
            granted = GrantedService(
                certificate_id=cert.id,
                service_type_master_id=g.get('service_type_master_id', 1),
                granted_start_date=datetime.strptime(g['granted_start_date'], '%Y-%m-%d').date() if g.get('granted_start_date') else datetime.utcnow().date(),
                granted_end_date=datetime.strptime(g['granted_end_date'], '%Y-%m-%d').date() if g.get('granted_end_date') else datetime.utcnow().date(),
                granted_amount_description=g.get('granted_amount_description')
            )
            db.session.add(granted)

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

    data = request.get_json()
    if not data:
        return jsonify({"msg": "Invalid data"}), 400

    try:
        if data.get('certificate_issue_date'):
            cert.certificate_issue_date = datetime.strptime(data['certificate_issue_date'], '%Y-%m-%d').date()
        if 'municipality_master_id' in data:
            cert.municipality_master_id = data['municipality_master_id']
        if 'certificate_type' in data:
            cert.certificate_type = data['certificate_type']
        if 'disability_support_classification' in data:
            cert.disability_support_classification = data['disability_support_classification']
        if 'certificate_notes' in data:
            cert.certificate_notes = data['certificate_notes']

        # GrantedServicesの入れ替え
        if 'granted_services' in data:
            GrantedService.query.filter_by(certificate_id=cert.id).delete()
            for g in data['granted_services']:
                granted = GrantedService(
                    certificate_id=cert.id,
                    service_type_master_id=g.get('service_type_master_id', 1),
                    granted_start_date=datetime.strptime(g['granted_start_date'], '%Y-%m-%d').date() if g.get('granted_start_date') else datetime.utcnow().date(),
                    granted_end_date=datetime.strptime(g['granted_end_date'], '%Y-%m-%d').date() if g.get('granted_end_date') else datetime.utcnow().date(),
                    granted_amount_description=g.get('granted_amount_description')
                )
                db.session.add(granted)

        db.session.commit()
        return jsonify({"msg": "Certificate updated successfully", "id": cert.id}), 200

    except Exception as e:
        db.session.rollback()
        import logging
        logging.error(f"Certificate Update Error: {str(e)}")
        return jsonify({"msg": f"更新に失敗しました: {str(e)}"}), 500
