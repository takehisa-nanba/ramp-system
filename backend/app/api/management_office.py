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
    configs = office.service_configs.all()
    
    if not configs:
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
        configs = [service]

    services_list = []
    for service in configs:
        services_list.append({
            "id": service.id,
            "service_type_master_id": service.service_type_master_id,
            "manager_supporter_id": service.manager_supporter_id,
            "jigyosho_bango": service.jigyosho_bango,
            "capacity": service.capacity,
            "initial_designation_date": service.initial_designation_date.isoformat() if service.initial_designation_date else None,
            "designation_expiry_date": service.designation_expiry_date.isoformat() if service.designation_expiry_date else None,
            "regional_category": service.regional_category,
            "target_disabilities": service.target_disabilities,
            "cooperating_medical_institution": service.cooperating_medical_institution,
            "manager_name": f"{service.manager_supporter.last_name} {service.manager_supporter.first_name}" if service.manager_supporter else "未設定"
        })

    first_s = services_list[0]
    corp = office.corporation

    return jsonify({
        "id": office.id,
        "corporation_id": corp.id if corp else None,
        "corporation_name": corp.corporation_name if corp else "",
        "corporation_type": corp.corporation_type if corp else "",
        "corporation_number": corp.corporation_number if corp else "",
        "corporation_representative_name": corp.representative_name if corp else "",
        "corporation_postal_code": corp.postal_code if corp else "",
        "corporation_address": corp.address if corp else "",
        "corporation_phone_number": corp.phone_number if corp else "",
        "tenant_id": corp.tenant_id if corp else "",
        "office_name": office.office_name,
        "municipality_id": office.municipality_id,
        "full_time_weekly_minutes": office.full_time_weekly_minutes,
        "is_active": office.is_active,
        "postal_code": office.postal_code,
        "address": office.address,
        "phone_number": office.phone_number,
        "fax_number": office.fax_number,
        "email_address": office.email_address,
        "representative_name": office.representative_name,
        
        # 互換性のための単一サービス用の設定
        "service_config_id": first_s["id"],
        "service_type_master_id": first_s["service_type_master_id"],
        "manager_supporter_id": first_s["manager_supporter_id"],
        "jigyosho_bango": first_s["jigyosho_bango"],
        "capacity": first_s["capacity"],
        "initial_designation_date": first_s["initial_designation_date"],
        "designation_expiry_date": first_s["designation_expiry_date"],
        "regional_category": first_s["regional_category"],
        "target_disabilities": first_s["target_disabilities"],
        "cooperating_medical_institution": first_s["cooperating_medical_institution"],
        "manager_name": first_s["manager_name"],
        
        # 複数サービス（多機能型）の配列データ
        "services": services_list
    }), 200

@management_office_bp.route('', methods=['PUT'])
@jwt_required()
def update_office_settings():
    from backend.app.utils.errors import ValidationError
    from backend.app.services.core_service import reconcile_relations
    try:
        current = get_current_staff()
        data = request.get_json()
        office = OfficeSetting.query.get(current.office_id)
        corp = office.corporation

        if corp:
            corp.corporation_name = data.get('corporation_name', corp.corporation_name) or corp.corporation_name
            corp.corporation_type = data.get('corporation_type', corp.corporation_type) or corp.corporation_type
            corp.corporation_number = data.get('corporation_number', corp.corporation_number) or corp.corporation_number
            corp.representative_name = data.get('corporation_representative_name', corp.representative_name)
            corp.postal_code = data.get('corporation_postal_code', corp.postal_code)
            corp.address = data.get('corporation_address', corp.address)
            corp.phone_number = data.get('corporation_phone_number', corp.phone_number)
            corp.tenant_id = data.get('tenant_id', corp.tenant_id) or corp.tenant_id
        
        if 'office_name' in data: office.office_name = data['office_name'] or "未設定事業所"
        if 'municipality_id' in data and data['municipality_id']:
            try:
                office.municipality_id = int(data['municipality_id'])
            except (ValueError, TypeError):
                raise ValidationError("自治体の指定が不正です")
        if 'full_time_weekly_minutes' in data: 
            try:
                office.full_time_weekly_minutes = int(float(data['full_time_weekly_minutes']))
            except (ValueError, TypeError):
                raise ValidationError("週所定労働時間は数値で入力してください")
        
        office.postal_code = data.get('postal_code', office.postal_code)
        office.address = data.get('address', office.address)
        office.phone_number = data.get('phone_number', office.phone_number)
        office.fax_number = data.get('fax_number', office.fax_number)
        office.email_address = data.get('email_address', office.email_address)
        office.representative_name = data.get('representative_name', office.representative_name)
        
        # 新しい `services` の複数同期処理
        incoming_services = data.get('services')
        if incoming_services is not None:
            if not isinstance(incoming_services, list) or len(incoming_services) == 0:
                raise ValidationError("提供サービスは最低1つ登録する必要があります。")

            # 重複サービス種別のチェック
            selected_service_types = [int(s.get('service_type_master_id')) for s in incoming_services if s.get('service_type_master_id')]
            if len(selected_service_types) != len(set(selected_service_types)):
                raise ValidationError("同じサービス種別を複数登録することはできません。")

            def match_service(existing, incoming):
                inc_id = incoming.get('id')
                if not inc_id or int(inc_id) <= 0:
                    return False
                return existing.id == int(inc_id)
                
            def update_service(item, incoming):
                item.office_id = office.id
                item.service_type_master_id = int(incoming['service_type_master_id'])
                item.jigyosho_bango = incoming.get('jigyosho_bango', '0000000000') or '0000000000'
                
                try:
                    item.capacity = int(incoming.get('capacity', 20))
                except (ValueError, TypeError):
                    raise ValidationError("定員は数値で入力してください。")
                    
                item.manager_supporter_id = int(incoming['manager_supporter_id']) if incoming.get('manager_supporter_id') else None
                item.regional_category = incoming.get('regional_category')
                item.target_disabilities = incoming.get('target_disabilities')
                item.cooperating_medical_institution = incoming.get('cooperating_medical_institution')
                
                if incoming.get('initial_designation_date'):
                    try:
                        item.initial_designation_date = datetime.fromisoformat(incoming['initial_designation_date']).date()
                    except (ValueError, TypeError):
                        raise ValidationError("初回指定年月日の形式が不正です")
                else:
                    item.initial_designation_date = None
                    
                if incoming.get('designation_expiry_date'):
                    try:
                        item.designation_expiry_date = datetime.fromisoformat(incoming['designation_expiry_date']).date()
                    except (ValueError, TypeError):
                        raise ValidationError("指定有効期限の形式が不正です")
                else:
                    item.designation_expiry_date = None

            reconcile_relations(
                office.service_configs,
                incoming_services,
                OfficeServiceConfiguration,
                db.session,
                match_service,
                update_service
            )
        else:
            # 後方互換：services 配列が渡されなかった場合は、単一の first() を更新
            service = office.service_configs.first()
            if service:
                if 'service_type_master_id' in data and data['service_type_master_id']:
                    try:
                        service.service_type_master_id = int(data['service_type_master_id'])
                    except (ValueError, TypeError):
                        raise ValidationError("サービス種別の指定が不正です")

                if 'manager_supporter_id' in data:
                    service.manager_supporter_id = int(data['manager_supporter_id']) if data.get('manager_supporter_id') else None

                if 'jigyosho_bango' in data and data['jigyosho_bango']:
                    service.jigyosho_bango = data['jigyosho_bango']
                
                if 'capacity' in data:
                    try:
                        service.capacity = int(data['capacity'])
                    except (ValueError, TypeError):
                        raise ValidationError("定員は数値で入力してください")
                    
                service.regional_category = data.get('regional_category', service.regional_category)
                service.target_disabilities = data.get('target_disabilities', service.target_disabilities)
                service.cooperating_medical_institution = data.get('cooperating_medical_institution', service.cooperating_medical_institution)
                
                if data.get('initial_designation_date'):
                    try:
                        service.initial_designation_date = datetime.fromisoformat(data['initial_designation_date']).date()
                    except (ValueError, TypeError):
                        raise ValidationError("指定年月日の形式が不正です")
                if data.get('designation_expiry_date'):
                    try:
                        service.designation_expiry_date = datetime.fromisoformat(data['designation_expiry_date']).date()
                    except (ValueError, TypeError):
                        raise ValidationError("指定有効期限の形式が不正です")
            
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
    from backend.app.utils.errors import ValidationError
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
        except (ValueError, TypeError):
            raise ValidationError("届出日の形式が不正です")
        
    if data.get('start_date'):
        try:
            new_filing.effective_start_date = datetime.fromisoformat(data['start_date']).date()
        except (ValueError, TypeError):
            raise ValidationError("適用開始日の形式が不正です")
        
    if data.get('end_date'):
        try:
            new_filing.effective_end_date = datetime.fromisoformat(data['end_date']).date()
        except (ValueError, TypeError):
            raise ValidationError("適用終了日の形式が不正です")
        
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
