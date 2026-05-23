# backend/app/api/users.py

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.app import db
from backend.app.models import User, SupportPlan
from backend.app.services.core_service import check_permission

users_bp = Blueprint('users', __name__, url_prefix='/api/users')

@users_bp.route('/<int:user_id>/pii', methods=['GET'])
@jwt_required()
def get_user_pii(user_id):
    """
    指定された利用者のPII（個人特定可能情報）を取得する。
    権限 'VIEW_PII' が必要。
    """
    # 1. 実行者のIDを取得
    current_supporter_id = get_jwt_identity()

    # 2. 権限チェック (RBAC)
    if not check_permission(current_supporter_id, 'VIEW_PII'):
        return jsonify({"msg": "Permission denied: Missing 'VIEW_PII' permission"}), 403

    # 3. 利用者データの取得
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404

    # 4. PIIデータの取得
    # UserPIIモデルのプロパティアクセサが自動的に復号化処理を行います
    pii = user.pii
    if not pii:
        # PIIレコードが存在しない場合は、匿名情報のみ返すかエラーにする
        return jsonify({
            "id": user.id,
            "display_name": user.display_name,
            "msg": "No PII record found"
        }), 200

    # 5. 【セキュリティ強化】詳細情報を復号して画面にロードした時点で、監査ログを一括自動記録する！
    from backend.app.models.core.audit_log import AuditActionLog
    from backend.app.services.core_service import parse_jwt_identity
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

    # 最新の計画を取得
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

    # 緊急連絡先を取得
    contacts = [
        {
            "id": c.id,
            "name": c.name,
            "phone_number": c.phone_number,
            "relation": c.relation
        } for c in user.emergency_contacts
    ]

    profile_info = {
        "emergency_contact_notes": user.profile.emergency_contact_notes if user.profile else "",
        "insurance_details": user.profile.insurance_details if user.profile else ""
    }

    # 5. レスポンスの生成
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
        "pii": {
            # --- 階層2: システム共通鍵で復号 ---
            "last_name": pii.last_name,
            "first_name": pii.first_name,
            "last_name_kana": pii.last_name_kana,
            "first_name_kana": pii.first_name_kana,
            "address": pii.address,
            
            # --- 階層1: エンベロープ暗号化で復号 ---
            "certificate_number": pii.certificate_number,
            
            # --- 平文 ---
            "phone_number": pii.phone_number,
            "email": pii.email,
            "birth_date": pii.birth_date.isoformat() if pii.birth_date else None
        }
    }), 200

@users_bp.route('/statuses', methods=['GET'])
@jwt_required()
def list_statuses():
    """
    StatusMaster からステータス一覧を取得する。
    """
    from backend.app.models.masters.master_definitions import StatusMaster
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
    from flask import request
    query = User.query

    status_ids_str = request.args.get('status_ids')
    if status_ids_str:
        try:
            status_ids = [int(s.strip()) for s in status_ids_str.split(',')]
            query = query.filter(User.status_id.in_(status_ids))
        except ValueError:
            pass

    users = query.order_by(User.id.asc()).all()
    user_list = []
    for user in users:
        has_cert = False
        if user.pii and user.pii.certificate_number:
            has_cert = True
            
        active_plan = user.support_plans.filter_by(plan_status='ACTIVE').first()
        active_plan_end_date = active_plan.plan_end_date.isoformat() if active_plan and active_plan.plan_end_date else None
        
        user_list.append({
            "id": user.id,
            "display_name": user.display_name,
            "status_id": user.status_id,
            "status_name": user.status.name if user.status else None,
            "service_start_date": user.service_start_date.isoformat() if user.service_start_date else None,
            "has_certificate_number": has_cert,
            "active_plan_end_date": active_plan_end_date
        })

    return jsonify(user_list), 200

@users_bp.route('/<int:user_id>/decrypt-pii', methods=['POST'])
@jwt_required()
def decrypt_user_pii(user_id):
    """
    特定の個人情報を閲覧し、監査ログを自動記録する。
    """
    from flask import request
    from backend.app.models.core.audit_log import AuditActionLog
    from backend.app.services.core_service import parse_jwt_identity
    
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

    # 監査ログを記録 (誰が、いつ、誰の、何を閲覧したか自動記録)
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

@users_bp.route('/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    """
    利用者の基本情報および個人情報(PII)を更新する。
    """
    from flask import request
    from backend.app.services.core_service import parse_jwt_identity
    from backend.app.models.core.audit_log import AuditActionLog
    
    current_supporter_id = get_jwt_identity()
    
    if not check_permission(current_supporter_id, 'VIEW_PII'):
        return jsonify({"msg": "Permission denied: Missing permission to edit user details."}), 403

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404

    data = request.get_json() or {}
    
    # 1. 基本情報の更新
    if 'display_name' in data:
        user.display_name = data['display_name']
        
    # 2. PII情報の更新
    pii = user.pii
    if not pii:
        from backend.app.models.core.user import UserPII
        pii = UserPII(user_id=user.id)
        db.session.add(pii)

    pii_data = data.get('pii', {})
    
    # ゲッター・セッター経由で自動暗号化して保存
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
        
    # 平文フィールド
    if 'phone_number' in pii_data:
        pii.phone_number = pii_data['phone_number']
    if 'email' in pii_data:
        pii.email = pii_data['email']
    if 'birth_date' in pii_data:
        from datetime import datetime
        try:
            pii.birth_date = datetime.strptime(pii_data['birth_date'], '%Y-%m-%d').date() if pii_data['birth_date'] else None
        except ValueError:
            return jsonify({"msg": "Invalid birth_date format, expected YYYY-MM-DD"}), 400

    # 2.5. UserProfile の更新
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

    # 2.6. EmergencyContacts の一括更新 (差分整合)
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

    # 監査ログを記録
    _, supporter_id_int = parse_jwt_identity(current_supporter_id)
    audit_log = AuditActionLog(
        supporter_id=supporter_id_int,
        action_type='EDIT_USER',
        target_table='users',
        target_id=user_id,
        change_details=f"User details and PII updated"
    )
    db.session.add(audit_log)
    
    try:
        db.session.commit()
        return jsonify({"msg": "User details updated successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Database update failed: {e}"}), 500

@users_bp.route('', methods=['POST'])
@jwt_required()
def create_user():
    """
    新しい利用者を新規登録し、暗号化個人情報(PII)を同時に設定する。
    """
    from flask import request
    from backend.app.services.core_service import parse_jwt_identity
    from backend.app.models.core.audit_log import AuditActionLog
    from backend.app.models.masters.master_definitions import StatusMaster
    from datetime import datetime
    
    current_supporter_id = get_jwt_identity()
    
    if not check_permission(current_supporter_id, 'VIEW_PII'):
        return jsonify({"msg": "Permission denied: Missing permission to register users."}), 403

    data = request.get_json() or {}
    display_name = data.get('display_name')
    if not display_name or not display_name.strip():
        return jsonify({"msg": "表示名は必須です。"}), 400

    # 1. ステータスの取得（指定があればそれ、なければ「問い合わせ」）
    req_status_id = data.get('status_id')
    if req_status_id:
        status = StatusMaster.query.get(req_status_id)
        status_id = status.id if status else 1
    else:
        status = StatusMaster.query.filter_by(name='問い合わせ').first()
        status_id = status.id if status else 1

    # 2. user_code の自動採番 (USR001, USR002, ...)
    import re
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
        # 3. User レコード作成
        new_user = User(
            display_name=display_name,
            user_code=user_code,
            status_id=status_id,
            service_start_date=service_start_date
        )
        db.session.add(new_user)
        db.session.flush() # IDを確定させる

        # 4. UserPII レコード作成
        from backend.app.models.core.user import UserPII
        pii_data = data.get('pii', {})
        new_pii = UserPII(
            user=new_user
        )
        db.session.add(new_pii)

        # ゲッター・セッター経由で自動暗号化して保存
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
            
        # 平文フィールド
        if 'phone_number' in pii_data:
            new_pii.phone_number = pii_data['phone_number']
        if 'email' in pii_data:
            new_pii.email = pii_data['email']
        if 'birth_date' in pii_data:
            try:
                new_pii.birth_date = datetime.strptime(pii_data['birth_date'], '%Y-%m-%d').date() if pii_data['birth_date'] else None
            except ValueError:
                return jsonify({"msg": "Invalid birth_date format, expected YYYY-MM-DD"}), 400

        # 4.5. UserProfile (支援詳細情報・成育歴等) の作成
        from backend.app.models.core.user_profile import UserProfile
        profile_data = data.get('profile', {})
        new_profile = UserProfile(
            user=new_user,
            emergency_contact_notes=profile_data.get('emergency_contact_notes', ''),
            insurance_details=profile_data.get('insurance_details', '')
        )
        db.session.add(new_profile)

        # 4.6. EmergencyContacts (緊急連絡先) の一括作成
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

        # 5. 監査ログを記録
        _, supporter_id_int = parse_jwt_identity(current_supporter_id)
        audit_log = AuditActionLog(
            supporter_id=supporter_id_int,
            action_type='CREATE_USER',
            target_table='users',
            target_id=new_user.id,
            change_details=f"New user registered: {display_name} ({user_code})"
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


# ====================================================================
# 【新規】下書き（一時保存）API
# ====================================================================

@users_bp.route('/drafts', methods=['POST'])
@jwt_required()
def save_draft():
    """
    フォーム入力データの一時下書きを暗号化保存する（オートセーブ用）。
    """
    from flask import request
    from backend.app.models import SupporterFormDraft
    from backend.app.services.core_service import parse_jwt_identity
    
    current_supporter_id = get_jwt_identity()
    _, supporter_id_int = parse_jwt_identity(current_supporter_id)
    
    data = request.get_json() or {}
    draft_key = data.get('draft_key')
    draft_data = data.get('data')
    
    if not draft_key:
        return jsonify({"msg": "Missing draft_key"}), 400
        
    try:
        # 既存の下書きを取得、なければ新規作成
        draft = SupporterFormDraft.query.filter_by(
            supporter_id=supporter_id_int,
            draft_key=draft_key
        ).first()
        
        if not draft:
            draft = SupporterFormDraft(
                supporter_id=supporter_id_int,
                draft_key=draft_key
            )
            db.session.add(draft)
            
        # 辞書データを代入（セッターにより自動的にAES-256暗号化されます）
        draft.data = draft_data
        db.session.commit()
        
        return jsonify({"msg": "Draft auto-saved successfully"}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Draft save failed: {e}"}), 500


@users_bp.route('/drafts/<string:draft_key>', methods=['GET'])
@jwt_required()
def get_draft(draft_key):
    """
    指定されたキーの一時下書きデータを取得し、復号して返却する。
    """
    from backend.app.models import SupporterFormDraft
    from backend.app.services.core_service import parse_jwt_identity
    
    current_supporter_id = get_jwt_identity()
    _, supporter_id_int = parse_jwt_identity(current_supporter_id)
    
    try:
        draft = SupporterFormDraft.query.filter_by(
            supporter_id=supporter_id_int,
            draft_key=draft_key
        ).first()
        
        if not draft:
            return jsonify({"data": None}), 200
            
        # ゲッターにより自動的にAES-256復号されて辞書型で返ります
        return jsonify({"data": draft.data}), 200
        
    except Exception as e:
        return jsonify({"msg": f"Draft load failed: {e}"}), 500

@users_bp.route('/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    """
    指定された利用者情報を完全に削除する。
    誤って登録された利用者を想定しており、すでに個別支援計画などの業務実績が存在する場合は削除を拒否する。
    """
    current_supporter_id = get_jwt_identity()

    # 1. 権限チェック (RBAC - 管理者やサビ管のみ可能とするのが望ましいが、ここでは簡易的に設定)
    if not check_permission(current_supporter_id, 'EDIT_PII'):
        return jsonify({"msg": "Permission denied: Missing 'EDIT_PII' permission"}), 403

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404

    # 2. 業務実績（個別支援計画など）の存在チェック
    if user.support_plans.count() > 0:
        return jsonify({"msg": "Cannot delete user: This user already has Support Plans associated."}), 400

    try:
        # PII等の関連情報はcascade="all, delete-orphan"により自動削除される
        db.session.delete(user)
        
        # 監査ログの記録
        from backend.app.models.core.audit_log import AuditActionLog
        from backend.app.services.core_service import parse_jwt_identity
        _, supporter_id_int = parse_jwt_identity(current_supporter_id)
        audit_log = AuditActionLog(
            supporter_id=supporter_id_int,
            action_type='DELETE_USER',
            target_table='users',
            target_id=user_id,
            change_details=f"Deleted user {user.display_name} (Code: {user.user_code})"
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
    from flask import request
    from backend.app.models.core.audit_log import AuditActionLog
    from backend.app.services.core_service import parse_jwt_identity
    from backend.app.models.masters.master_definitions import StatusMaster
    from datetime import datetime

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
        # 監査ログの記録
        _, supporter_id_int = parse_jwt_identity(current_supporter_id)
        audit_log = AuditActionLog(
            supporter_id=supporter_id_int,
            action_type='EDIT_USER',
            target_table='users',
            target_id=user_id,
            change_details=f"Status changed from '{old_status_name}' to '{new_status.name}'"
        )
        db.session.add(audit_log)
        
        db.session.commit()
        return jsonify({"msg": "Status updated successfully"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Failed to update status: {e}"}), 500


@users_bp.route('/drafts/<string:draft_key>', methods=['DELETE'])
@jwt_required()
def delete_draft(draft_key):
    """
    指定されたキーの一時下書きデータをDBから削除する（登録成功時やキャンセル時）。
    """
    from backend.app.models import SupporterFormDraft
    from backend.app.services.core_service import parse_jwt_identity
    
    current_supporter_id = get_jwt_identity()
    _, supporter_id_int = parse_jwt_identity(current_supporter_id)
    
    try:
        draft = SupporterFormDraft.query.filter_by(
            supporter_id=supporter_id_int,
            draft_key=draft_key
        ).first()
        
        if draft:
            db.session.delete(draft)
            db.session.commit()
            
        return jsonify({"msg": "Draft cleared successfully"}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Draft clear failed: {e}"}), 500