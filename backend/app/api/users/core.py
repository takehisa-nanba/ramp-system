from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.app import db
from backend.app.models import User
from backend.app.models.masters.master_definitions import StatusMaster
from backend.app.services.core_service import check_permission, parse_jwt_identity
from backend.app.models.core.audit_log import AuditActionLog
from datetime import datetime, timezone
import re
from . import users_bp

@users_bp.route('/statuses', methods=['GET'])
@jwt_required()
def list_statuses():
    """
    StatusMaster からステータス一覧を取得する。
    """
    statuses = StatusMaster.query.order_by(StatusMaster.sort_order.asc()).all()
    return jsonify([
        {
            "id": s.id,
            "name": s.name,
            "description": s.description
        } for s in statuses
    ]), 200

@users_bp.route('', methods=['GET'])
@jwt_required()
def list_users():
    """
    利用者一覧を取得する。status_idsカンマ区切りでフィルタリング可能。
    """
    from backend.app.models.core.user import UserPII
    
    query = db.session.query(
        User,
        UserPII.encrypted_certificate_number.isnot(None).label('has_cert')
    ).outerjoin(UserPII, User.id == UserPII.user_id).filter(User.deleted_at.is_(None))

    status_ids_str = request.args.get('status_ids')
    if status_ids_str:
        try:
            status_ids = [int(s.strip()) for s in status_ids_str.split(',')]
            query = query.filter(User.status_id.in_(status_ids))
        except ValueError:
            pass

    results = query.order_by(User.id.asc()).all()
    user_list = []
    for user, has_cert in results:
        active_plan = user.support_plans.filter_by(plan_status='ACTIVE').first()
        active_plan_end_date = active_plan.plan_end_date.isoformat() if active_plan and active_plan.plan_end_date else None
        
        user_list.append({
            "id": user.id,
            "display_name": user.display_name,
            "status_id": user.status_id,
            "status_name": user.status.name if user.status else None,
            "service_start_date": user.service_start_date.isoformat() if user.service_start_date else None,
            "has_certificate_number": bool(has_cert),
            "active_plan_end_date": active_plan_end_date
        })

    return jsonify(user_list), 200

@users_bp.route('', methods=['POST'])
@jwt_required()
def create_user():
    """
    新しい利用者を新規登録し、暗号化個人情報(PII)を同時に設定する。
    """
    current_supporter_id = get_jwt_identity()
    
    if not check_permission(current_supporter_id, 'EDIT_PII'):
        return jsonify({"msg": "Permission denied: Missing 'EDIT_PII' permission to register users."}), 403

    data = request.get_json() or {}
    display_name = data.get('display_name')
    if not display_name or not display_name.strip():
        return jsonify({"msg": "表示名は必須です。"}), 400

    req_status_id = data.get('status_id')
    if req_status_id:
        status = StatusMaster.query.get(req_status_id)
        status_id = status.id if status else 1
    else:
        status = StatusMaster.query.filter_by(name='問い合わせ').first()
        status_id = status.id if status else 1

    max_user = User.query.filter(User.user_code.like('USR%')).order_by(User.user_code.desc()).first()
    if max_user and max_user.user_code:
        match = re.search(r'\d+', max_user.user_code)
        if match:
            next_num = int(match.group()) + 1
            user_code = f"USR{next_num:03d}"
        else:
            user_code = "USR001"
    else:
        user_code = "USR001"

    service_start_date_str = data.get('service_start_date')
    service_start_date = None
    if service_start_date_str:
        try:
            service_start_date = datetime.strptime(service_start_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    try:
        new_user = User(
            display_name=display_name,
            user_code=user_code,
            status_id=status_id,
            service_start_date=service_start_date
        )
        db.session.add(new_user)
        db.session.flush()

        from backend.app.models.core.user import UserPII
        pii_data = data.get('pii', {})
        new_pii = UserPII(user=new_user)
        db.session.add(new_pii)

        if 'last_name' in pii_data:
            new_pii.last_name = pii_data['last_name']
        if 'first_name' in pii_data:
            new_pii.first_name = pii_data['first_name']
        if 'last_name_kana' in pii_data:
            new_pii.last_name_kana = pii_data['last_name_kana']
        if 'first_name_kana' in pii_data:
            new_pii.first_name_kana = pii_data['first_name_kana']
        if 'address' in pii_data:
            new_pii.address = pii_data['address']
        if 'certificate_number' in pii_data:
            new_pii.certificate_number = pii_data['certificate_number']
            
        if 'phone_number' in pii_data:
            new_pii.phone_number = pii_data['phone_number']
        if 'email' in pii_data:
            new_pii.email = pii_data['email']
        if 'birth_date' in pii_data:
            try:
                new_pii.birth_date = datetime.strptime(pii_data['birth_date'], '%Y-%m-%d').date() if pii_data['birth_date'] else None
            except ValueError:
                return jsonify({"msg": "Invalid birth_date format, expected YYYY-MM-DD"}), 400

        from backend.app.models.core.user_profile import UserProfile
        profile_data = data.get('profile', {})
        new_profile = UserProfile(
            user=new_user,
            emergency_contact_notes=profile_data.get('emergency_contact_notes', ''),
            insurance_details=profile_data.get('insurance_details', '')
        )
        db.session.add(new_profile)

        from backend.app.models.core.user_profile import EmergencyContact
        contacts_data = data.get('emergency_contacts', [])
        for c in contacts_data:
            if c.get('name') and c.get('phone_number'):
                new_contact = EmergencyContact(
                    user=new_user,
                    name=c['name'],
                    phone_number=c['phone_number'],
                    relation=c.get('relation', '')
                )
                db.session.add(new_contact)

        _, supporter_id_int = parse_jwt_identity(current_supporter_id)
        audit_log = AuditActionLog(
            actor_supporter_id=supporter_id_int,
            action='CREATE_USER',
            entity_type='users',
            entity_id=new_user.id,
            after_value=f"New user registered: {display_name} ({user_code})"
        )
        db.session.add(audit_log)
        db.session.commit()

        return jsonify({
            "msg": "User registered successfully",
            "user_id": new_user.id,
            "user_code": user_code
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Database insertion failed: {e}"}), 500

@users_bp.route('/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    """
    利用者の基本情報および個人情報(PII)を更新する。
    """
    current_supporter_id = get_jwt_identity()
    
    if not check_permission(current_supporter_id, 'EDIT_PII'):
        return jsonify({"msg": "Permission denied: Missing 'EDIT_PII' permission to edit user details."}), 403

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404

    data = request.get_json() or {}
    
    if 'display_name' in data:
        user.display_name = data['display_name']
        
    pii = user.pii
    if not pii:
        from backend.app.models.core.user import UserPII
        pii = UserPII(user_id=user.id)
        db.session.add(pii)

    pii_data = data.get('pii', {})
    
    if 'last_name' in pii_data:
        pii.last_name = pii_data['last_name']
    if 'first_name' in pii_data:
        pii.first_name = pii_data['first_name']
    if 'last_name_kana' in pii_data:
        pii.last_name_kana = pii_data['last_name_kana']
    if 'first_name_kana' in pii_data:
        pii.first_name_kana = pii_data['first_name_kana']
    if 'address' in pii_data:
        pii.address = pii_data['address']
    if 'certificate_number' in pii_data:
        pii.certificate_number = pii_data['certificate_number']
        
    if 'phone_number' in pii_data:
        pii.phone_number = pii_data['phone_number']
    if 'email' in pii_data:
        pii.email = pii_data['email']
    if 'birth_date' in pii_data:
        try:
            pii.birth_date = datetime.strptime(pii_data['birth_date'], '%Y-%m-%d').date() if pii_data['birth_date'] else None
        except ValueError:
            return jsonify({"msg": "Invalid birth_date format, expected YYYY-MM-DD"}), 400

    profile_data = data.get('profile', {})
    profile = user.profile
    if not profile:
        from backend.app.models.core.user_profile import UserProfile
        profile = UserProfile(user=user)
        db.session.add(profile)
    
    if 'emergency_contact_notes' in profile_data:
        profile.emergency_contact_notes = profile_data['emergency_contact_notes']
    if 'insurance_details' in profile_data:
        profile.insurance_details = profile_data['insurance_details']

    if 'emergency_contacts' in data:
        from backend.app.models.core.user_profile import EmergencyContact
        from backend.app.services.core_service import reconcile_relations
        
        valid_contacts = [c for c in data['emergency_contacts'] if c.get('name') and c.get('phone_number')]
        
        def match_contact(existing, incoming):
            return existing.name == incoming['name'] and existing.phone_number == incoming['phone_number']
            
        def update_contact(item, incoming):
            item.user_id = user.id
            item.name = incoming['name']
            item.phone_number = incoming['phone_number']
            item.relation = incoming.get('relation', '')
            
        reconcile_relations(
            user.emergency_contacts,
            valid_contacts,
            EmergencyContact,
            db.session,
            match_contact,
            update_contact
        )

    _, supporter_id_int = parse_jwt_identity(current_supporter_id)
    audit_log = AuditActionLog(
        actor_supporter_id=supporter_id_int,
        action='EDIT_USER',
        entity_type='users',
        entity_id=user_id,
        after_value=f"User details and PII updated"
    )
    db.session.add(audit_log)
    
    try:
        db.session.commit()
        return jsonify({"msg": "User details updated successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Database update failed: {e}"}), 500

@users_bp.route('/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    """
    指定された利用者情報を完全に削除する。
    """
    current_supporter_id = get_jwt_identity()

    if not check_permission(current_supporter_id, 'EDIT_PII'):
        return jsonify({"msg": "Permission denied: Missing 'EDIT_PII' permission"}), 403

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404

    if user.support_plans.count() > 0:
        return jsonify({"msg": "Cannot delete user: This user already has Support Plans associated."}), 400

    try:
        data = request.get_json() or {}
        delete_reason = data.get('reason', '利用者削除')

        _, supporter_id_int = parse_jwt_identity(current_supporter_id)
        
        user.deleted_at = datetime.now(timezone.utc)
        user.deleted_by_id = supporter_id_int
        user.delete_reason = delete_reason
        user.status_id = 5 # 例：利用終了（退所）など、適切なステータスにしてもよい
        
        audit_log = AuditActionLog(
            actor_supporter_id=supporter_id_int,
            action='DELETE_USER',
            entity_type='users',
            entity_id=user_id,
            reason=delete_reason,
            before_value=f"User {user.display_name} (Code: {user.user_code}) Active",
            after_value="Soft Deleted"
        )
        db.session.add(audit_log)
        db.session.commit()
        return jsonify({"msg": "User deleted successfully"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Failed to delete user: {e}"}), 500

@users_bp.route('/<int:user_id>/status', methods=['PUT'])
@jwt_required()
def update_user_status(user_id):
    """
    利用者のステータス（および利用開始日・終了日）を更新する。
    """
    current_supporter_id = get_jwt_identity()

    if not check_permission(current_supporter_id, 'EDIT_PII'):
        return jsonify({"msg": "Permission denied: Missing 'EDIT_PII' permission"}), 403

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404

    data = request.get_json() or {}
    new_status_id = data.get('status_id')
    service_start_date_str = data.get('service_start_date')
    service_end_date_str = data.get('service_end_date')

    if not new_status_id:
        return jsonify({"msg": "status_id is required"}), 400

    new_status = db.session.get(StatusMaster, new_status_id)
    if not new_status:
        return jsonify({"msg": "Invalid status_id"}), 400

    old_status_name = user.status.name if user.status else "Unknown"
    user.status_id = new_status_id

    if service_start_date_str is not None:
        if service_start_date_str == "":
            user.service_start_date = None
        else:
            try:
                user.service_start_date = datetime.strptime(service_start_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass

    if service_end_date_str is not None:
        if service_end_date_str == "":
            user.service_end_date = None
        else:
            try:
                user.service_end_date = datetime.strptime(service_end_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass

    try:
        _, supporter_id_int = parse_jwt_identity(current_supporter_id)
        audit_log = AuditActionLog(
            actor_supporter_id=supporter_id_int,
            action='EDIT_USER',
            entity_type='users',
            entity_id=user_id,
            after_value=f"Status changed from '{old_status_name}' to '{new_status.name}'"
        )
        db.session.add(audit_log)
        
        db.session.commit()
        return jsonify({"msg": "Status updated successfully"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Failed to update status: {e}"}), 500
