# backend/app/api/user_routes.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
# ★ 修正: db, User の直接インポートを削除し、サービス層から関数をインポート
from backend.app.services.core_service import get_all_users_lite, get_user_by_id 

# Blueprintの作成
user_bp = Blueprint('users', __name__)

@user_bp.route('/', methods=['GET'])
@jwt_required()
def get_users():
    """
    利用者一覧を取得するAPI。
    一覧画面用なので、重たいPII（復号処理）は含まず、基本情報のみを返す。
    """
    # 1. ★ 修正: サービス層経由で全利用者を取得
    users = get_all_users_lite()
    
    results = []
    for user in users:
        # PIIの復号処理を行わない軽量なデータを返す
        results.append({
            "id": user.id,
            "display_name": user.display_name, # 匿名ID
            "status": user.status.name if user.status else None,
            # 必要な軽量データのみ返す
        })
    
    return jsonify(results), 200


@user_bp.route('/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user_detail(user_id):
    """
    利用者詳細を取得するAPI。
    ここで初めてPII（氏名など）にアクセスし、自動復号されたデータを返す。
    """
    # 1. ★ 修正: サービス層経由でユーザーを取得
    user = get_user_by_id(user_id)
    
    if not user:
        return jsonify({"msg": "User not found"}), 404
        
    # 権限チェック (RBAC) - ※ 将来的にここにロジックを追加
    
    # 2. レスポンスデータの構築
    # user.pii.last_name などを参照した瞬間に、モデル内の @property が作動し、裏で復号処理が走る！
    user_data = {
        "id": user.id,
        "display_name": user.display_name,
        "status": user.status.name if user.status else None,
        "service_start_date": user.service_start_date.isoformat() if user.service_start_date else None,
        
        # --- 機密情報 (自動復号) ---
        "pii": {
            # ★ 修正: user.pii の存在チェックを追加 (安全のため)
            "last_name": user.pii.last_name if user.pii else None,
            "first_name": user.pii.first_name if user.pii else None,
            "email": user.pii.email if user.pii else None,
            "phone_number": user.pii.phone_number if user.pii else None,
            "certificate_number": user.pii.certificate_number if user.pii else None
        } if user.pii else None
    }
    
    return jsonify(user_data), 200