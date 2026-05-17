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
    if not any(r.role_scope in ['SYSTEM', 'CORPORATE', 'JOB'] for r in current.roles):
        return jsonify({"msg": "アクセス権限がありません。この操作には管理者権限が必要です。"}), 403
    
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
        "allow_overlap_calculation": s.allow_overlap_calculation,
        "hire_date": s.hire_date.isoformat() if s.hire_date else None,
        "retirement_date": s.retirement_date.isoformat() if s.retirement_date else None,
        "roles": [r.name for r in s.roles],
        "role_ids": [r.id for r in s.roles],
        "job_assignments": [{
            "id": a.id,
            "job_title_id": a.job_title_id,
            "title_name": a.job_title.title_name if a.job_title else "未設定",
            "assigned_minutes": a.assigned_minutes,
            "office_service_configuration_id": a.office_service_configuration_id,
            "is_deemed_assignment": a.is_deemed_assignment,
            "deemed_expiry_date": a.deemed_expiry_date.isoformat() if a.deemed_expiry_date else None
        } for a in s.job_assignments],
        "shift_patterns": [{
            "id": p.id,
            "day_of_week": p.day_of_week,
            "start_time": p.start_time,
            "end_time": p.end_time,
            "break_minutes": p.break_minutes
        } for p in s.shift_patterns],
        "email": s.pii.email if s.pii else "N/A",
        "personal_phone": s.pii.personal_phone if (s.pii and s.pii.encrypted_personal_phone) else "",
        "address": s.pii.address if (s.pii and s.pii.encrypted_address) else "",
        "bank_account_info": s.pii.bank_account_info if (s.pii and s.pii.encrypted_bank_account_info) else ""
    } for s in staff_members]), 200

@management_bp.route('/staff/<int:staff_id>', methods=['PUT'])
@jwt_required()
def update_staff(staff_id):
    from backend.app.models import SupporterPII, RoleMaster, SupporterJobAssignment, OfficeServiceConfiguration
    from datetime import date
    
    current = get_current_staff()
    if not current: return jsonify({"msg": "Unauthorized"}), 401
    if not any(r.role_scope in ['SYSTEM', 'CORPORATE', 'JOB'] for r in current.roles):
        return jsonify({"msg": "アクセス権限がありません。この操作には管理者権限が必要です。"}), 403
    
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

        # === 兼務時間 ＆ 特例重複計上バリデーション ===
        allow_overlap = bool(data.get('allow_overlap_calculation', staff.allow_overlap_calculation))
        weekly_minutes = int(data.get('weekly_scheduled_minutes', staff.weekly_scheduled_minutes))
        
        if 'job_assignments' in data:
            for a in data['job_assignments']:
                title_id = a.get('job_title_id')
                if not title_id or int(title_id) <= 0:
                    return jsonify({"msg": "兼務職務を設定する場合は、すべての行で職種（役割）を選択してください。"}), 400

            if not allow_overlap:
                total_assigned = sum(int(a.get('assigned_minutes', 0)) for a in data['job_assignments'])
                if total_assigned > weekly_minutes:
                    return jsonify({
                        "msg": f"各職務の割り当て合計（{total_assigned / 60:.1f}時間）が、週所定労働時間（{weekly_minutes / 60:.1f}時間）を超えています。複数事業の重複計上（特例）がOFFの間は登録できません。"
                    }), 400

        # 基本情報の更新
        if 'last_name' in data: staff.last_name = data['last_name']
        if 'first_name' in data: staff.first_name = data['first_name']
        if 'last_name_kana' in data: staff.last_name_kana = data['last_name_kana']
        if 'first_name_kana' in data: staff.first_name_kana = data['first_name_kana']
        if 'staff_code' in data: staff.staff_code = data['staff_code']
        def to_katakana(text):
            if not text: return text
            return "".join(chr(ord(c) + 96) if 0x3041 <= ord(c) <= 0x3096 else c for c in text)

        if 'employment_type' in data: staff.employment_type = data['employment_type']
        if 'weekly_scheduled_minutes' in data: 
            staff.weekly_scheduled_minutes = int(data['weekly_scheduled_minutes'])
        if 'is_active' in data: staff.is_active = bool(data['is_active'])
        if 'allow_overlap_calculation' in data:
            staff.allow_overlap_calculation = bool(data['allow_overlap_calculation'])
        
        if 'last_name_kana' in data: staff.last_name_kana = to_katakana(data['last_name_kana'])
        if 'first_name_kana' in data: staff.first_name_kana = to_katakana(data['first_name_kana'])

        if 'hire_date' in data and data['hire_date']:
            try:
                staff.hire_date = datetime.fromisoformat(data['hire_date']).date()
            except: pass

        if 'retirement_date' in data:
            if data['retirement_date']:
                try:
                    staff.retirement_date = datetime.fromisoformat(data['retirement_date']).date()
                except: pass
            else:
                staff.retirement_date = None

        # セキュリティ・ロール (RoleMaster) の同期更新
        if 'role_ids' in data:
            role_ids = data['role_ids']
            roles = RoleMaster.query.filter(RoleMaster.id.in_(role_ids)).all()
            staff.roles = roles

        # 福祉実務職務 (SupporterJobAssignment) の同期更新
        if 'job_assignments' in data:
            # 既存の割り当てを一度完全削除
            SupporterJobAssignment.query.filter_by(supporter_id=staff.id).delete()
            
            # 所属事業所の OfficeServiceConfiguration を取得
            service_config = OfficeServiceConfiguration.query.filter_by(office_id=staff.office_id).first()
            service_config_id = service_config.id if service_config else 1
            
            for a in data['job_assignments']:
                expiry_val = None
                if a.get('deemed_expiry_date'):
                    try:
                        expiry_val = datetime.fromisoformat(a['deemed_expiry_date']).date()
                    except: pass

                new_assign = SupporterJobAssignment(
                    supporter_id=staff.id,
                    job_title_id=int(a['job_title_id']),
                    office_service_configuration_id=service_config_id,
                    start_date=staff.hire_date or date.today(),
                    assigned_minutes=int(a['assigned_minutes']),
                    is_deemed_assignment=bool(a.get('is_deemed_assignment', False)),
                    deemed_expiry_date=expiry_val
                )
                db.session.add(new_assign)

        # 曜日別契約シフトパターン (EmploymentShiftPattern) の同期更新
        if 'shift_patterns' in data:
            from backend.app.models import EmploymentShiftPattern
            # 既存のパターンを全削除
            EmploymentShiftPattern.query.filter_by(supporter_id=staff.id).delete()
            
            for p in data['shift_patterns']:
                day = p.get('day_of_week')
                if not day: continue
                
                new_pat = EmploymentShiftPattern(
                    supporter_id=staff.id,
                    day_of_week=day,
                    start_time=p.get('start_time'),
                    end_time=p.get('end_time'),
                    break_minutes=int(p.get('break_minutes', 0))
                )
                db.session.add(new_pat)

        # PII の更新
        if any(k in data for k in ['email', 'personal_phone', 'address', 'bank_account_info', 'password']):
            if not staff.pii:
                staff.pii = SupporterPII(supporter_id=staff.id, email=data.get('email', 'temp@example.com'))
                db.session.add(staff.pii)
            
            if 'email' in data and data['email']:
                staff.pii.email = data['email']
            if 'personal_phone' in data:
                staff.pii.personal_phone = data['personal_phone']
            if 'address' in data:
                staff.pii.address = data['address']
            if 'bank_account_info' in data:
                staff.pii.bank_account_info = data['bank_account_info']
                
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

@management_bp.route('/job-titles', methods=['GET'])
@jwt_required()
def get_available_job_titles():
    from backend.app.models import JobTitleMaster
    titles = JobTitleMaster.query.all()
    return jsonify([{
        "id": t.id,
        "title_name": t.title_name,
        "is_management_role": t.is_management_role,
        "is_qualified_role": t.is_qualified_role
    } for t in titles]), 200

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
    from backend.app.models import SupporterPII, RoleMaster, SupporterJobAssignment, OfficeServiceConfiguration
    from backend.app.extensions import bcrypt
    from datetime import date
    
    current = get_current_staff()
    if not current: return jsonify({"msg": "Unauthorized"}), 401
    if not any(r.role_scope in ['SYSTEM', 'CORPORATE', 'JOB'] for r in current.roles):
        return jsonify({"msg": "アクセス権限がありません。この操作には管理者権限が必要です。"}), 403
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

        # === 兼務時間 ＆ 特例重複計上バリデーション ===
        allow_overlap = bool(data.get('allow_overlap_calculation', False))
        weekly_minutes = int(data['weekly_scheduled_minutes'])
        
        if 'job_assignments' in data:
            for a in data['job_assignments']:
                title_id = a.get('job_title_id')
                if not title_id or int(title_id) <= 0:
                    return jsonify({"msg": "兼務職務を設定する場合は、すべての行で職種（役割）を選択してください。"}), 400

            if not allow_overlap:
                total_assigned = sum(int(a.get('assigned_minutes', 0)) for a in data['job_assignments'])
                if total_assigned > weekly_minutes:
                    return jsonify({
                        "msg": f"各職務の割り当て合計（{total_assigned / 60:.1f}時間）が、週所定労働時間（{weekly_minutes / 60:.1f}時間）を超えています。複数事業の重複計上（特例）がOFFの間は登録できません。"
                    }), 400

        # office_id の安全なフォールバック判定
        target_office_id = current.office_id if current else None
        if not target_office_id:
            first_office = OfficeSetting.query.first()
            if first_office:
                target_office_id = first_office.id

        # ひらがなカタカナ変換関数
        def to_katakana(text):
            if not text: return text
            return "".join(chr(ord(c) + 96) if 0x3041 <= ord(c) <= 0x3096 else c for c in text)

        ret_date = None
        if data.get('retirement_date'):
            try:
                ret_date = datetime.fromisoformat(data['retirement_date']).date()
            except: pass

        # 新規スタッフ作成 (厳格なバリデーション)
        new_staff = Supporter(
            office_id=target_office_id,
            staff_code=data['staff_code'],
            last_name=data['last_name'],
            first_name=data['first_name'],
            last_name_kana=to_katakana(data['last_name_kana']),
            first_name_kana=to_katakana(data['first_name_kana']),
            hire_date=datetime.fromisoformat(data['hire_date']).date(),
            retirement_date=ret_date,
            employment_type=data.get('employment_type', 'FULL_TIME'),
            weekly_scheduled_minutes=weekly_minutes,
            allow_overlap_calculation=allow_overlap,
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

        # 福祉実務職務 (SupporterJobAssignment) の同期登録
        if 'job_assignments' in data:
            # 所属事業所の OfficeServiceConfiguration を取得
            service_config = OfficeServiceConfiguration.query.filter_by(office_id=new_staff.office_id).first()
            service_config_id = service_config.id if service_config else 1
            
            for a in data['job_assignments']:
                expiry_val = None
                if a.get('deemed_expiry_date'):
                    try:
                        expiry_val = datetime.fromisoformat(a['deemed_expiry_date']).date()
                    except: pass

                new_assign = SupporterJobAssignment(
                    supporter_id=new_staff.id,
                    job_title_id=int(a['job_title_id']),
                    office_service_configuration_id=service_config_id,
                    start_date=new_staff.hire_date,
                    assigned_minutes=int(a['assigned_minutes']),
                    is_deemed_assignment=bool(a.get('is_deemed_assignment', False)),
                    deemed_expiry_date=expiry_val
                )
                db.session.add(new_assign)

        # 曜日別契約シフトパターン (EmploymentShiftPattern) の同期登録
        if 'shift_patterns' in data:
            from backend.app.models import EmploymentShiftPattern
            for p in data['shift_patterns']:
                day = p.get('day_of_week')
                if not day: continue
                
                new_pat = EmploymentShiftPattern(
                    supporter_id=new_staff.id,
                    day_of_week=day,
                    start_time=p.get('start_time'),
                    end_time=p.get('end_time'),
                    break_minutes=int(p.get('break_minutes', 0))
                )
                db.session.add(new_pat)

        # PII (個人情報) 作成
        new_pii = SupporterPII(
            supporter_id=new_staff.id,
            email=data['email']
        )
        if 'personal_phone' in data:
            new_pii.personal_phone = data['personal_phone']
        if 'address' in data:
            new_pii.address = data['address']
        if 'bank_account_info' in data:
            new_pii.bank_account_info = data['bank_account_info']
            
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


