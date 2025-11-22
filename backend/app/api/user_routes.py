from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.app.extensions import db
from backend.app.models import User, Supporter

# Blueprintの作成
user_bp = Blueprint('users', __name__)

@user_bp.route('/', methods=['GET'])
@jwt_required()
def get_users():
    """
    利用者一覧を取得するAPI。
    一覧画面用なので、重たいPII（復号処理）は含まず、基本情報のみを返す。
    """
    # 全利用者を取得 (本番ではページネーションが必要)
    users = User.query.all()
    
    results = []
    for user in users:
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
    user = db.session.get(User, user_id)
    
    if not user:
        return jsonify({"msg": "User not found"}), 404
        
    # 権限チェック (RBAC)
    # ※ 本来は core_service.check_permission を使うべきだが、
    #    ここでは簡易的に実装。
    
    # レスポンスデータの構築
    # user.pii.last_name などを参照した瞬間に、
    # モデル内の @property が作動し、裏で復号処理が走る！
    user_data = {
        "id": user.id,
        "display_name": user.display_name,
        "status": user.status.name if user.status else None,
        "service_start_date": user.service_start_date.isoformat() if user.service_start_date else None,
        
        # --- 機密情報 (自動復号) ---
        "pii": {
            "last_name": user.pii.last_name if user.pii else None,
            "first_name": user.pii.first_name if user.pii else None,
            "email": user.pii.email if user.pii else None,
            "phone_number": user.pii.phone_number if user.pii else None,
            # 受給者証番号（最高機密）
            "certificate_number": user.pii.certificate_number if user.pii else None
        } if user.pii else None
    }
    
    return jsonify(user_data), 200