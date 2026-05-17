# backend/app/api/users.py

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.app import db
from backend.app.models import User
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

    # 5. レスポンスの生成
    return jsonify({
        "id": user.id,
        "display_name": user.display_name,
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

@users_bp.route('', methods=['GET'])
@jwt_required()
def list_users():
    """
    利用者一覧を取得する（ドロップダウン選択用など）。
    """
    users = User.query.all()
    return jsonify([
        {
            "id": user.id,
            "display_name": user.display_name
        } for user in users
    ]), 200

@users_bp.route('/<int:user_id>/decrypt-pii', methods=['POST'])
@jwt_required()
def decrypt_user_pii(user_id):
    """
    理由入力付きで特定の個人情報を閲覧し、監査ログを記録する。
    """
    from flask import request
    from backend.app.models.core.audit_log import AuditActionLog
    
    current_supporter_id = get_jwt_identity()

    if not check_permission(current_supporter_id, 'VIEW_PII'):
        return jsonify({"msg": "Permission denied: Missing 'VIEW_PII' permission"}), 403

    data = request.get_json() or {}
    pii_type = data.get('pii_type')
    reason = data.get('reason')

    if not pii_type or not reason:
        return jsonify({"msg": "pii_type and reason are required"}), 400

    if len(reason) < 10:
        return jsonify({"msg": "閲覧理由は10文字以上で入力してください。"}), 400

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
    elif pii_type == 'bank_account':
        val = pii.certificate_number or "未登録"
    else:
        return jsonify({"msg": "Invalid pii_type"}), 400

    # 監査ログを記録
    audit_log = AuditActionLog(
        supporter_id=current_supporter_id,
        action_type='VIEW_PII',
        target_table='user_pii',
        target_id=user_id,
        change_details=f"PII Type: {pii_type} | Reason: {reason}"
    )
    db.session.add(audit_log)
    db.session.commit()

    return jsonify({"value": val}), 200