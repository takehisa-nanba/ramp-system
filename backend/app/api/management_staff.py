from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.app import db
from backend.app.models import Supporter, OfficeSetting, RoleMaster
from sqlalchemy.orm import joinedload
from datetime import datetime
from backend.app.utils.text_helpers import convert_to_katakana
from backend.app.utils.errors import AppError, ValidationError

management_staff_bp = Blueprint('management_staff', __name__, url_prefix='/api/management/staff')

def get_current_staff():
    from backend.app.services.core_service import parse_jwt_identity
    prefix, staff_id = parse_jwt_identity(get_jwt_identity())
    if prefix == 'staff' and staff_id:
        return Supporter.query.get(staff_id)
    return None

@management_staff_bp.route('', methods=['GET'])
@jwt_required()
def list_staff():
    from backend.app.services.core_service import check_permission
    current = get_current_staff()
    if not current: return jsonify({"msg": "Unauthorized"}), 401
    
    # 職員情報の詳細を閲覧するための権限チェック
    has_view_staff = check_permission(f"staff:{current.id}", "VIEW_STAFF")
    
    is_global_admin = any(r.role_scope in ['SYSTEM', 'CORPORATE'] and r.is_admin for r in current.roles)
    
    query = Supporter.query.options(
        joinedload(Supporter.pii),
        joinedload(Supporter.roles),
        joinedload(Supporter.shift_patterns)
    )
    
    if is_global_admin:
        staff_members = query.all()
    else:
        office_id = current.office_id
        if not office_id:
            first_office = OfficeSetting.query.first()
            office_id = first_office.id if first_office else None
            
        if office_id:
            staff_members = query.filter_by(office_id=office_id).all()
        else:
            staff_members = []
    
    if not has_view_staff:
        return jsonify([{
            "id": s.id,
            "name": f"{s.last_name} {s.first_name}",
            "last_name": s.last_name,
            "first_name": s.first_name,
            "last_name_kana": s.last_name_kana,
            "first_name_kana": s.first_name_kana,
            "staff_code": s.staff_code,
            "is_active": s.is_active,
            "roles": [r.name for r in s.roles],
            "role_ids": [r.id for r in s.roles],
            "job_assignments": [],
            "shift_patterns": [],
            "email": "N/A",
            "personal_phone": "",
            "address": "",
            "bank_account_info": ""
        } for s in staff_members]), 200
    
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
        "personal_phone": s.pii.personal_phone if s.pii else "",
        "address": s.pii.address if s.pii else "",
        "bank_account_info": s.pii.bank_account_info if s.pii else ""
    } for s in staff_members]), 200

@management_staff_bp.route('/<int:staff_id>', methods=['PUT'])
@jwt_required()
def update_staff(staff_id):
    from backend.app.models import SupporterPII, RoleMaster, SupporterJobAssignment, OfficeServiceConfiguration
    from datetime import date
    from backend.app.services.core_service import check_permission
    
    current = get_current_staff()
    if not current: return jsonify({"msg": "Unauthorized"}), 401
    if not check_permission(f"staff:{current.id}", "EDIT_STAFF"):
        return jsonify({"msg": "アクセス権限がありません。必要な権限: EDIT_STAFF"}), 403
    
    staff = Supporter.query.get_or_404(staff_id)
    
    is_global_admin = any(r.role_scope in ['SYSTEM', 'CORPORATE'] and r.is_admin for r in current.roles)
    if not is_global_admin:
        if staff.office_id != current.office_id:
            return jsonify({"msg": "他事業所の職員情報を編集する権限がありません。"}), 403
    data = request.get_json()
    
    try:
        # ラストワン保護の検証
        from backend.app.services.core_service import validate_last_admin_protection
        validate_last_admin_protection(staff, data)

        if 'staff_code' in data and data['staff_code'] != staff.staff_code:
            if Supporter.query.filter_by(staff_code=data['staff_code']).first():
                raise ValidationError(f"職員コード「{data['staff_code']}」は既に別のスタッフで使用されています")
                
        if 'email' in data and staff.pii and data['email'] != staff.pii.email:
            if SupporterPII.query.filter_by(email=data['email']).first():
                raise ValidationError(f"メールアドレス「{data['email']}」は既に別のスタッフで使用されています")

        allow_overlap = bool(data.get('allow_overlap_calculation', staff.allow_overlap_calculation))
        weekly_minutes = int(data.get('weekly_scheduled_minutes', staff.weekly_scheduled_minutes))
        
        if 'job_assignments' in data:
            for a in data['job_assignments']:
                title_id = a.get('job_title_id')
                if not title_id or int(title_id) <= 0:
                    raise ValidationError("兼務職務を設定する場合は、すべての行で職種（役割）を選択してください。")

            if not allow_overlap:
                total_assigned = sum(int(a.get('assigned_minutes', 0)) for a in data['job_assignments'])
                if total_assigned > weekly_minutes:
                    raise ValidationError(f"各職務の割り当て合計（{total_assigned / 60:.1f}時間）が、週所定労働時間（{weekly_minutes / 60:.1f}時間）を超えています。複数事業の重複計上（特例）がOFFの間は登録できません。")

        if 'last_name' in data: staff.last_name = data['last_name']
        if 'first_name' in data: staff.first_name = data['first_name']
        if 'last_name_kana' in data: staff.last_name_kana = data['last_name_kana']
        if 'first_name_kana' in data: staff.first_name_kana = data['first_name_kana']
        if 'staff_code' in data: staff.staff_code = data['staff_code']

        if 'employment_type' in data: staff.employment_type = data['employment_type']
        if 'weekly_scheduled_minutes' in data: 
            staff.weekly_scheduled_minutes = int(data['weekly_scheduled_minutes'])
        if 'is_active' in data: staff.is_active = bool(data['is_active'])
        if 'allow_overlap_calculation' in data:
            staff.allow_overlap_calculation = bool(data['allow_overlap_calculation'])
        if 'last_name_kana' in data: staff.last_name_kana = convert_to_katakana(data['last_name_kana'])
        if 'first_name_kana' in data: staff.first_name_kana = convert_to_katakana(data['first_name_kana'])

        if 'hire_date' in data and data['hire_date']:
            try:
                staff.hire_date = datetime.fromisoformat(data['hire_date']).date()
            except (ValueError, TypeError):
                raise ValidationError("入職日の形式が不正です")

        if 'retirement_date' in data:
            if data['retirement_date']:
                try:
                    staff.retirement_date = datetime.fromisoformat(data['retirement_date']).date()
                except (ValueError, TypeError):
                    raise ValidationError("退職日の形式が不正です")
            else:
                staff.retirement_date = None

        if 'role_ids' in data:
            role_ids = data['role_ids']
            roles = RoleMaster.query.filter(RoleMaster.id.in_(role_ids)).all()
            staff.roles = roles

        if 'job_assignments' in data:
            from backend.app.services.core_service import reconcile_relations
            
            service_config = OfficeServiceConfiguration.query.filter_by(office_id=staff.office_id).first()
            if not service_config:
                from backend.app.models import ServiceTypeMaster
                st = ServiceTypeMaster.query.first()
                service_config = OfficeServiceConfiguration(
                    office_id=staff.office_id, 
                    service_type_master_id=st.id if st else 1,
                    jigyosho_bango=f"GEN-{staff.office_id}-0001",
                    capacity=20
                )
                db.session.add(service_config)
                db.session.flush()
            service_config_id = service_config.id
            
            def match_job(existing, incoming):
                return existing.job_title_id == int(incoming['job_title_id'])
                
            def update_job(item, incoming):
                item.supporter_id = staff.id
                item.job_title_id = int(incoming['job_title_id'])
                item.office_service_configuration_id = service_config_id
                item.start_date = staff.hire_date or date.today()
                item.assigned_minutes = int(incoming['assigned_minutes'])
                item.is_deemed_assignment = bool(incoming.get('is_deemed_assignment', False))
                expiry_val = None
                if incoming.get('deemed_expiry_date'):
                    try:
                        expiry_val = datetime.fromisoformat(incoming['deemed_expiry_date']).date()
                    except (ValueError, TypeError):
                        raise ValidationError("みなし資格有効期限の形式が不正です")
                item.deemed_expiry_date = expiry_val
                
            reconcile_relations(
                staff.job_assignments,
                data['job_assignments'],
                SupporterJobAssignment,
                db.session,
                match_job,
                update_job
            )

        if 'shift_patterns' in data:
            from backend.app.models import EmploymentShiftPattern
            from backend.app.services.core_service import reconcile_relations
            
            valid_patterns = [p for p in data['shift_patterns'] if p.get('day_of_week')]
            
            def match_shift(existing, incoming):
                return existing.day_of_week == incoming['day_of_week']
                
            def update_shift(item, incoming):
                item.supporter_id = staff.id
                item.day_of_week = incoming['day_of_week']
                item.start_time = incoming.get('start_time')
                item.end_time = incoming.get('end_time')
                item.break_minutes = int(incoming.get('break_minutes', 0))
                
            reconcile_relations(
                staff.shift_patterns,
                valid_patterns,
                EmploymentShiftPattern,
                db.session,
                match_shift,
                update_shift
            )

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
                
            if 'password' in data and data['password']:
                staff.pii.set_password(data['password'])

        db.session.commit()
        return jsonify({"msg": "Staff updated successfully"}), 200
        
    except AppError as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": {
                "code": e.code,
                "message": str(e)
            }
        }), e.status_code
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": {
                "code": "SYSTEM_ERROR",
                "message": f"更新に失敗しました: {str(e)}"
            }
        }), 500

@management_staff_bp.route('', methods=['POST'])
@jwt_required()
def register_staff():
    from backend.app.models import SupporterPII, RoleMaster, SupporterJobAssignment, OfficeServiceConfiguration
    from backend.app.extensions import bcrypt
    from datetime import date
    from backend.app.services.core_service import check_permission
    
    current = get_current_staff()
    if not current: return jsonify({"msg": "Unauthorized"}), 401
    if not check_permission(f"staff:{current.id}", "CREATE_STAFF"):
        return jsonify({"msg": "アクセス権限がありません。必要な権限: CREATE_STAFF"}), 403
    data = request.get_json()
    
    try:
        if Supporter.query.filter_by(staff_code=data['staff_code']).first():
            raise ValidationError(f"職員コード「{data['staff_code']}」は既に登録されています")
        if SupporterPII.query.filter_by(email=data['email']).first():
            raise ValidationError(f"メールアドレス「{data['email']}」は既に使用されています")

        required_fields = ['last_name', 'first_name', 'last_name_kana', 'first_name_kana', 'staff_code', 'email', 'hire_date', 'weekly_scheduled_minutes']
        for field in required_fields:
            if field not in data or not data[field]:
                raise ValidationError(f"必須項目「{field}」が不足しています")

        allow_overlap = bool(data.get('allow_overlap_calculation', False))
        weekly_minutes = int(data['weekly_scheduled_minutes'])
        
        if 'job_assignments' in data:
            for a in data['job_assignments']:
                title_id = a.get('job_title_id')
                if not title_id or int(title_id) <= 0:
                    raise ValidationError("兼務職務を設定する場合は、すべての行で職種（役割）を選択してください。")

            if not allow_overlap:
                total_assigned = sum(int(a.get('assigned_minutes', 0)) for a in data['job_assignments'])
                if total_assigned > weekly_minutes:
                    raise ValidationError(f"各職務の割り当て合計（{total_assigned / 60:.1f}時間）が、週所定労働時間（{weekly_minutes / 60:.1f}時間）を超えています。複数事業の重複計上（特例）がOFFの間は登録できません。")

        target_office_id = current.office_id if current else None
        if not target_office_id:
            first_office = OfficeSetting.query.first()
            if first_office:
                target_office_id = first_office.id

        ret_date = None
        if data.get('retirement_date'):
            try:
                ret_date = datetime.fromisoformat(data['retirement_date']).date()
            except (ValueError, TypeError):
                raise ValidationError("退職日の形式が不正です")

        new_staff = Supporter(
            office_id=target_office_id,
            staff_code=data['staff_code'],
            last_name=data['last_name'],
            first_name=data['first_name'],
            last_name_kana=convert_to_katakana(data['last_name_kana']),
            first_name_kana=convert_to_katakana(data['first_name_kana']),
            hire_date=datetime.fromisoformat(data['hire_date']).date(),
            retirement_date=ret_date,
            employment_type=data.get('employment_type', 'FULL_TIME'),
            weekly_scheduled_minutes=weekly_minutes,
            allow_overlap_calculation=allow_overlap,
            is_active=True
        )

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

        if 'job_assignments' in data:
            service_config = OfficeServiceConfiguration.query.filter_by(office_id=new_staff.office_id).first()
            if not service_config:
                from backend.app.models import ServiceTypeMaster
                st = ServiceTypeMaster.query.first()
                service_config = OfficeServiceConfiguration(
                    office_id=new_staff.office_id, 
                    service_type_master_id=st.id if st else 1,
                    jigyosho_bango=f"GEN-{new_staff.office_id}-0001",
                    capacity=20
                )
                db.session.add(service_config)
                db.session.flush()
            service_config_id = service_config.id
            
            for a in data['job_assignments']:
                expiry_val = None
                if a.get('deemed_expiry_date'):
                    try:
                        expiry_val = datetime.fromisoformat(a['deemed_expiry_date']).date()
                    except (ValueError, TypeError):
                        raise ValidationError("みなし資格有効期限の形式が不正です")

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
            
        new_pii.set_password(data.get('password', 'password123'))
        db.session.add(new_pii)
        
        db.session.commit()
        return jsonify({"msg": "Staff registered successfully", "id": new_staff.id}), 201
        
    except AppError as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": {
                "code": e.code,
                "message": str(e)
            }
        }), e.status_code
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": {
                "code": "SYSTEM_ERROR",
                "message": f"登録に失敗しました: {str(e)}"
            }
        }), 500

@management_staff_bp.route('/<int:staff_id>/roles', methods=['PUT'])
@jwt_required()
def update_staff_roles(staff_id):
    from backend.app.services.core_service import check_permission
    current = get_current_staff()
    if not current: return jsonify({"msg": "Unauthorized"}), 401
    if not check_permission(f"staff:{current.id}", "EDIT_STAFF"):
        return jsonify({"msg": "アクセス権限がありません。必要な権限: EDIT_STAFF"}), 403
        
    staff = Supporter.query.get_or_404(staff_id)
    
    is_global_admin = any(r.role_scope in ['SYSTEM', 'CORPORATE'] and r.is_admin for r in current.roles)
    if not is_global_admin:
        if staff.office_id != current.office_id:
            return jsonify({"msg": "他事業所の職員情報を編集する権限がありません。"}), 403
            
    data = request.get_json()
    role_ids = data.get('role_ids', [])
    
    try:
        from backend.app.services.core_service import validate_last_admin_protection
        validate_last_admin_protection(staff, {"role_ids": role_ids})

        new_roles = RoleMaster.query.filter(RoleMaster.id.in_(role_ids)).all()
        staff.roles = new_roles
        db.session.commit()
        return jsonify({"msg": "Roles updated"}), 200
    except AppError as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": {
                "code": e.code,
                "message": str(e)
            }
        }), e.status_code
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": {
                "code": "SYSTEM_ERROR",
                "message": f"ロールの更新に失敗しました: {str(e)}"
            }
        }), 500
