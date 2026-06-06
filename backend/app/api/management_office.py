from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.app import db
from backend.app.models import Supporter, OfficeSetting, OfficeServiceConfiguration, OfficeAdditiveFiling, GovernmentFeeMaster
from datetime import datetime
from backend.app.utils.errors import AppError

management_office_bp = Blueprint('management_office', __name__, url_prefix='/api/management/office')

def get_current_staff():
    from backend.app.services.core_service import parse_jwt_identity
    prefix, staff_id = parse_jwt_identity(get_jwt_identity())
    if prefix == 'staff' and staff_id:
        return Supporter.query.get(staff_id)
    return None

@management_office_bp.route('', methods=['GET'])
@jwt_required()
def get_office_settings():
    current = get_current_staff()
    if not current or not current.office_id:
        return jsonify({"msg": "Office not found"}), 404
    
    office = OfficeSetting.query.get(current.office_id)
    service = office.service_configs.first()
    
    if not service:
        from backend.app.models import ServiceTypeMaster
        st = ServiceTypeMaster.query.first()
        service = OfficeServiceConfiguration(
            office_id=office.id, 
            service_type_master_id=st.id if st else 1,
            jigyosho_bango="0000000000",
            capacity=20
        )
        db.session.add(service)
        db.session.commit()

    return jsonify({
        "id": office.id,
        "office_name": office.office_name,
        "full_time_weekly_minutes": office.full_time_weekly_minutes,
        "is_active": office.is_active,
        "postal_code": office.postal_code,
        "address": office.address,
        "phone_number": office.phone_number,
        "fax_number": office.fax_number,
        "email_address": office.email_address,
        "representative_name": office.representative_name,
        "jigyosho_bango": service.jigyosho_bango,
        "capacity": service.capacity,
        "initial_designation_date": service.initial_designation_date.isoformat() if service.initial_designation_date else None,
        "designation_expiry_date": service.designation_expiry_date.isoformat() if service.designation_expiry_date else None,
        "regional_category": service.regional_category,
        "cooperating_medical_institution": service.cooperating_medical_institution,
        "manager_name": f"{service.manager_supporter.last_name} {service.manager_supporter.first_name}" if service.manager_supporter else "未設定"
    }), 200

@management_office_bp.route('', methods=['PUT'])
@jwt_required()
def update_office_settings():
    try:
        current = get_current_staff()
        data = request.get_json()
        office = OfficeSetting.query.get(current.office_id)
        service = office.service_configs.first()
        
        if 'office_name' in data: office.office_name = data['office_name'] or "未設定事業所"
        if 'full_time_weekly_minutes' in data: 
            try:
                office.full_time_weekly_minutes = int(float(data['full_time_weekly_minutes']))
            except (ValueError, TypeError): pass
        
        office.postal_code = data.get('postal_code', office.postal_code)
        office.address = data.get('address', office.address)
        office.phone_number = data.get('phone_number', office.phone_number)
        office.fax_number = data.get('fax_number', office.fax_number)
        office.email_address = data.get('email_address', office.email_address)
        office.representative_name = data.get('representative_name', office.representative_name)
        
        if service:
            if 'jigyosho_bango' in data and data['jigyosho_bango']:
                service.jigyosho_bango = data['jigyosho_bango']
            
            if 'capacity' in data:
                try:
                    service.capacity = int(data['capacity'])
                except (ValueError, TypeError): pass
                
            service.regional_category = data.get('regional_category', service.regional_category)
            service.cooperating_medical_institution = data.get('cooperating_medical_institution', service.cooperating_medical_institution)
            
            if data.get('initial_designation_date'):
                try:
                    service.initial_designation_date = datetime.fromisoformat(data['initial_designation_date']).date()
                except (ValueError, TypeError): pass
            if data.get('designation_expiry_date'):
                try:
                    service.designation_expiry_date = datetime.fromisoformat(data['designation_expiry_date']).date()
                except (ValueError, TypeError): pass
            
        db.session.commit()
        return jsonify({"msg": "Office settings updated"}), 200
        
    except Exception as e:
        db.session.rollback()
        raise AppError(f"保存に失敗しました: {str(e)}", status_code=500)

@management_office_bp.route('/additive-filings', methods=['GET'])
@jwt_required()
def get_additive_filings():
    current = get_current_staff()
    if not current or not current.office_id:
        return jsonify({"msg": "Office not found"}), 404
    
    office = OfficeSetting.query.get(current.office_id)
    service = office.service_configs.first()
    if not service:
        return jsonify([]), 200
        
    filing_query = OfficeAdditiveFiling.query.filter_by(
        office_service_configuration_id=service.id
    ).filter(OfficeAdditiveFiling.deleted_at.is_(None))
    filings = filing_query.all()
    result = []
    for f in filings:
        result.append({
            "id": f.id,
            "fee_master_id": f.fee_master_id,
            "fee_name": f.fee_master.name if f.fee_master else "",
            "filing_date": f.filing_date.isoformat() if f.filing_date else None,
            "start_date": f.effective_start_date.isoformat() if f.effective_start_date else None,
            "end_date": f.effective_end_date.isoformat() if f.effective_end_date else None
        })
    return jsonify(result), 200

@management_office_bp.route('/additive-filings', methods=['POST'])
@jwt_required()
def add_additive_filing():
    current = get_current_staff()
    if not current or not current.office_id:
        return jsonify({"msg": "Office not found"}), 404
        
    office = OfficeSetting.query.get(current.office_id)
    service = office.service_configs.first()
    if not service:
        return jsonify({"msg": "Service configuration not found"}), 404
        
    data = request.get_json()
    
    fee_name = data.get('fee_name')
    if not fee_name:
        return jsonify({"msg": "fee_name is required"}), 400
        
    fee_master = GovernmentFeeMaster.query.filter_by(name=fee_name).first()
    if not fee_master:
        fee_master = GovernmentFeeMaster(
            name=fee_name,
            code=f"FEE_{int(datetime.now().timestamp())}",
            category="ADD",
            calculation_type="ADD_TO_BASE"
        )
        db.session.add(fee_master)
        db.session.flush()

    new_filing = OfficeAdditiveFiling(
        office_service_configuration_id=service.id,
        fee_master_id=fee_master.id,
        is_filed=True,
    )
    
    if data.get('filing_date'):
        try:
            new_filing.filing_date = datetime.fromisoformat(data['filing_date']).date()
        except (ValueError, TypeError): pass
        
    if data.get('start_date'):
        try:
            new_filing.effective_start_date = datetime.fromisoformat(data['start_date']).date()
        except (ValueError, TypeError): pass
        
    if data.get('end_date'):
        try:
            new_filing.effective_end_date = datetime.fromisoformat(data['end_date']).date()
        except (ValueError, TypeError): pass
        
    db.session.add(new_filing)
    db.session.commit()
    
    return jsonify({
        "id": new_filing.id,
        "fee_master_id": new_filing.fee_master_id,
        "fee_name": fee_master.name,
        "filing_date": new_filing.filing_date.isoformat() if new_filing.filing_date else None,
        "start_date": new_filing.effective_start_date.isoformat() if new_filing.effective_start_date else None,
        "end_date": new_filing.effective_end_date.isoformat() if new_filing.effective_end_date else None
    }), 201

@management_office_bp.route('/additive-filings/<int:filing_id>', methods=['DELETE'])
@jwt_required()
def delete_additive_filing(filing_id):
    filing = OfficeAdditiveFiling.query.get_or_404(filing_id)
    data = request.get_json() or {}
    delete_reason = data.get('reason', '設定削除')
    
    current = get_current_staff()
    supporter_id = current.id if current else None

    filing.deleted_at = datetime.now()
    filing.deleted_by_id = supporter_id
    filing.delete_reason = delete_reason
    db.session.commit()
    return jsonify({"msg": "Filing deleted successfully"}), 200
