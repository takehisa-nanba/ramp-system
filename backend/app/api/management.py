from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.app import db
from backend.app.models import Supporter, OfficeSetting, RoleMaster, PermissionMaster, Corporation, OfficeServiceConfiguration
from sqlalchemy.orm import joinedload
from datetime import datetime
import logging

management_bp = Blueprint('management', __name__, url_prefix='/api/management')

def get_current_staff():
    identity = get_jwt_identity()
    if isinstance(identity, str) and identity.startswith('staff:'):
        staff_id = int(identity.split(':')[1])
        return Supporter.query.get(staff_id)
    return None

@management_bp.route('/staff', methods=['GET'])
@jwt_required()
def list_staff():
    current = get_current_staff()
    if not current: return jsonify({"msg": "Unauthorized"}), 401
    
    # 事業所内の全スタッフを取得
    staff_members = Supporter.query.filter_by(office_id=current.office_id).all()
    
    return jsonify([{
        "id": s.id,
        "name": f"{s.last_name} {s.first_name}",
        "last_name": s.last_name,
        "first_name": s.first_name,
        "last_name_kana": s.last_name_kana,
        "first_name_kana": s.first_name_kana,
        "staff_code": s.staff_code,
        "is_active": s.is_active,
        "employment_type": s.employment_type,
        "weekly_scheduled_minutes": s.weekly_scheduled_minutes,
        "hire_date": s.hire_date.isoformat() if s.hire_date else None,
        "roles": [r.name for r in s.roles],
        "role_ids": [r.id for r in s.roles],
        "email": s.pii.email if s.pii else "N/A"
    } for s in staff_members]), 200

@management_bp.route('/staff/<int:staff_id>', methods=['PUT'])
@jwt_required()
def update_staff(staff_id):
    from backend.app.models import SupporterPII
    
    current = get_current_staff()
    if not current: return jsonify({"msg": "Unauthorized"}), 401
    
    staff = Supporter.query.get_or_404(staff_id)
    data = request.get_json()
    
    try:
        # 重複チェック (他スタッフと競合しないか)
        if 'staff_code' in data and data['staff_code'] != staff.staff_code:
            if Supporter.query.filter_by(staff_code=data['staff_code']).first():
                return jsonify({"msg": f"職員コード「{data['staff_code']}」は既に別のスタッフで使用されています"}), 400
                
        if 'email' in data and staff.pii and data['email'] != staff.pii.email:
            if SupporterPII.query.filter_by(email=data['email']).first():
                return jsonify({"msg": f"メールアドレス「{data['email']}」は既に別のスタッフで使用されています"}), 400

        # 基本情報の更新
        if 'last_name' in data: staff.last_name = data['last_name']
        if 'first_name' in data: staff.first_name = data['first_name']
        if 'last_name_kana' in data: staff.last_name_kana = data['last_name_kana']
        if 'first_name_kana' in data: staff.first_name_kana = data['first_name_kana']
        if 'staff_code' in data: staff.staff_code = data['staff_code']
        if 'employment_type' in data: staff.employment_type = data['employment_type']
        if 'weekly_scheduled_minutes' in data: 
            staff.weekly_scheduled_minutes = int(data['weekly_scheduled_minutes'])
        if 'is_active' in data: staff.is_active = bool(data['is_active'])
        
        if 'hire_date' in data and data['hire_date']:
            try:
                staff.hire_date = datetime.fromisoformat(data['hire_date']).date()
            except: pass

        # PII の更新
        if 'email' in data and data['email']:
            if not staff.pii:
                staff.pii = SupporterPII(supporter_id=staff.id, email=data['email'])
                db.session.add(staff.pii)
            else:
                staff.pii.email = data['email']
                
            # パスワード更新指示がある場合のみ
            if 'password' in data and data['password']:
                staff.pii.set_password(data['password'])

        db.session.commit()
        return jsonify({"msg": "Staff updated successfully"}), 200
        
    except Exception as e:
        db.session.rollback()
        import logging
        logging.error(f"Update Staff Error: {str(e)}")
        return jsonify({"msg": f"更新に失敗しました: {str(e)}"}), 500

@management_bp.route('/roles', methods=['GET'])
@jwt_required()
def get_available_roles():
    roles = RoleMaster.query.all()
    return jsonify([{
        "id": r.id,
        "name": r.name,
        "scope": r.role_scope
    } for r in roles]), 200

@management_bp.route('/staff/<int:staff_id>/roles', methods=['PUT'])
@jwt_required()
def update_staff_roles(staff_id):
    data = request.get_json()
    staff = Supporter.query.get_or_404(staff_id)
    
    role_ids = data.get('role_ids', [])
    new_roles = RoleMaster.query.filter(RoleMaster.id.in_(role_ids)).all()
    
    staff.roles = new_roles
    db.session.commit()
    return jsonify({"msg": "Roles updated"}), 200

@management_bp.route('/office', methods=['GET'])
@jwt_required()
def get_office_settings():
    current = get_current_staff()
    if not current or not current.office_id:
        return jsonify({"msg": "Office not found"}), 404
    
    office = OfficeSetting.query.get(current.office_id)
    service = office.service_configs.first()
    
    if not service:
        # サービス設定がない場合はデフォルトを作成 (セーフティネット)
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

@management_bp.route('/office', methods=['PUT'])
@jwt_required()
def update_office_settings():
    # ... (existing update logic)
    try:
        current = get_current_staff()
        data = request.get_json()
        office = OfficeSetting.query.get(current.office_id)
        service = office.service_configs.first()
        
        # OfficeSetting更新 (Noneチェック付き)
        if 'office_name' in data: office.office_name = data['office_name'] or "未設定事業所"
        if 'full_time_weekly_minutes' in data: 
            try:
                office.full_time_weekly_minutes = int(float(data['full_time_weekly_minutes']))
            except: pass
        
        office.postal_code = data.get('postal_code', office.postal_code)
        office.address = data.get('address', office.address)
        office.phone_number = data.get('phone_number', office.phone_number)
        office.fax_number = data.get('fax_number', office.fax_number)
        office.email_address = data.get('email_address', office.email_address)
        office.representative_name = data.get('representative_name', office.representative_name)
        
        # ServiceConfig更新
        if service:
            if 'jigyosho_bango' in data and data['jigyosho_bango']:
                service.jigyosho_bango = data['jigyosho_bango']
            
            if 'capacity' in data:
                try:
                    service.capacity = int(data['capacity'])
                except: pass
                
            service.regional_category = data.get('regional_category', service.regional_category)
            service.cooperating_medical_institution = data.get('cooperating_medical_institution', service.cooperating_medical_institution)
            
            # 日付文字列のパース
            if data.get('initial_designation_date'):
                try:
                    service.initial_designation_date = datetime.fromisoformat(data['initial_designation_date']).date()
                except: pass
            if data.get('designation_expiry_date'):
                try:
                    service.designation_expiry_date = datetime.fromisoformat(data['designation_expiry_date']).date()
                except: pass
            
        db.session.commit()
        return jsonify({"msg": "Office settings updated"}), 200
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Update failed: {str(e)}")
        return jsonify({"msg": f"保存に失敗しました: {str(e)}"}), 500

@management_bp.route('/staff', methods=['POST'])
@jwt_required()
def register_staff():
    from backend.app.models import SupporterPII, RoleMaster
    from backend.app.extensions import bcrypt
    from datetime import date
    
    current = get_current_staff()
    data = request.get_json()
    
    try:
        # 重複チェック
        if Supporter.query.filter_by(staff_code=data['staff_code']).first():
            return jsonify({"msg": f"職員コード「{data['staff_code']}」は既に登録されています"}), 400
        if SupporterPII.query.filter_by(email=data['email']).first():
            return jsonify({"msg": f"メールアドレス「{data['email']}」は既に使用されています"}), 400

        # 必須項目の抽出
        required_fields = ['last_name', 'first_name', 'last_name_kana', 'first_name_kana', 'staff_code', 'email', 'hire_date', 'weekly_scheduled_minutes']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"msg": f"必須項目「{field}」が不足しています"}), 400

        # office_id の安全なフォールバック判定
        target_office_id = current.office_id if current else None
        if not target_office_id:
            first_office = OfficeSetting.query.first()
            if first_office:
                target_office_id = first_office.id

        # 新規スタッフ作成 (厳格なバリデーション)
        new_staff = Supporter(
            office_id=target_office_id,
            staff_code=data['staff_code'],
            last_name=data['last_name'],
            first_name=data['first_name'],
            last_name_kana=data['last_name_kana'],
            first_name_kana=data['first_name_kana'],
            hire_date=datetime.fromisoformat(data['hire_date']).date(),
            employment_type=data.get('employment_type', 'FULL_TIME'),
            weekly_scheduled_minutes=int(data['weekly_scheduled_minutes']),
            is_active=True
        )

        # 初期ロールの割り当て
        role_ids = data.get('role_ids', [])
        if role_ids:
            roles = RoleMaster.query.filter(RoleMaster.id.in_(role_ids)).all()
            new_staff.roles = roles
        else:
            default_role = RoleMaster.query.filter_by(name='事業所管理者').first()
            if default_role:
                new_staff.roles = [default_role]

        db.session.add(new_staff)
        db.session.flush()

        # PII (個人情報) 作成
        new_pii = SupporterPII(
            supporter_id=new_staff.id,
            email=data['email']
        )
        # 初期パスワード設定 (ハッシュ化)
        new_pii.set_password(data.get('password', 'password123'))
        db.session.add(new_pii)
        
        db.session.commit()
        return jsonify({"msg": "Staff registered successfully", "id": new_staff.id}), 201
        
    except Exception as e:
        db.session.rollback()
        import logging
        logging.error(f"Registration Error: {str(e)}")
        return jsonify({"msg": f"登録に失敗しました: {str(e)}"}), 500


