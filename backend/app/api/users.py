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