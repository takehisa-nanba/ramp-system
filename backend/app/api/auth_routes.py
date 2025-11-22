from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from backend.app.services.core_service import authenticate_supporter
from backend.app.models import Supporter

# Blueprintの作成（APIのグループ化）
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    ログインAPI。
    Emailとパスワードを検証し、JWTアクセストークンを返す。
    """
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"msg": "Email and password required"}), 400

    # 1. サービス層で認証（原理6: ロジックの分離）
    supporter = authenticate_supporter(email, password)

    if not supporter:
        return jsonify({"msg": "Bad email or password"}), 401

    # 2. トークンの発行
    # identityには一意なID（supporter_id）を入れる
    access_token = create_access_token(identity=str(supporter.id))

    return jsonify(access_token=access_token), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required() # ★ このデコレータで保護（通行証が必要）
def get_current_user():
    """
    現在ログインしているユーザーの情報を返す。
    """
    # トークンからIDを取り出す
    current_user_id = get_jwt_identity()
    
    # DBから取得（本来はサービス層経由が望ましいが、簡易参照のため直接取得）
    # ※ from backend.app.extensions import db が必要なら追加
    from backend.app.extensions import db
    supporter = db.session.get(Supporter, int(current_user_id))
    
    if not supporter:
        return jsonify({"msg": "User not found"}), 404
        
    return jsonify({
        "id": supporter.id,
        "name": f"{supporter.last_name} {supporter.first_name}",
        "email": supporter.pii.email if supporter.pii else None,
        # ロール情報なども将来ここに追加
    }), 200