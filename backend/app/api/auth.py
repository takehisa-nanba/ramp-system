# backend/app/api/auth.py (新規作成)

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, set_access_cookies, unset_jwt_cookies, jwt_required, get_jwt_identity
from backend.app.services.core_service import authenticate_supporter
from backend.app.models import Supporter # 型ヒントとしてインポート

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/login', methods=['POST'])
def login():
    """職員または利用者のログイン処理"""
    data = request.get_json()
    login_id = data.get('email') or data.get('login_id') # emailまたはlogin_id
    password = data.get('password')

    user_type = data.get('user_type') # 'staff' or 'user'
    
    if not login_id or not password or not user_type:
        return jsonify({"msg": "Missing credentials or user_type"}), 400

    from backend.app.services.core_service import authenticate_user, authenticate_supporter
    
    if user_type == 'staff':
        supporter = authenticate_supporter(login_id, password)
        if supporter:
            role_name = "STAFF"
            identity = f"staff:{supporter.id}"
            full_name = f"{supporter.last_name} {supporter.first_name}"
            user_id = supporter.id
            role_scopes = [r.role_scope for r in supporter.roles]
        else:
            return jsonify({"msg": "Invalid credentials"}), 401
    elif user_type == 'user':
        user = authenticate_user(login_id, password)
        if user:
            role_name = "USER"
            identity = f"user:{user.id}"
            full_name = user.display_name
            user_id = user.id
            role_scopes = []
        else:
            return jsonify({"msg": "Invalid credentials"}), 401
    else:
        return jsonify({"msg": "Invalid user_type. Must be 'staff' or 'user'."}), 400

    additional_claims = {
        "role_name": role_name,
        "full_name": full_name,
        "role_scopes": role_scopes
    }
    access_token = create_access_token(identity=identity, additional_claims=additional_claims)
    
    response = jsonify({
        "msg": "Login successful", 
        "user_id": user_id, 
        "role_name": role_name, 
        "full_name": full_name,
        "role_scopes": role_scopes
    })
    
    set_access_cookies(response, access_token)
    return response, 200


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """ログアウト処理（Cookieを削除）"""
    response = jsonify({"msg": "Logout successful"})
    unset_jwt_cookies(response)
    return response, 200

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    """現在のセッション情報（ユーザー情報）を復元する"""
    from flask_jwt_extended import get_jwt
    claims = get_jwt()
    identity = get_jwt_identity() # 例: 'staff:1' または 'user:5'
    
    # identityからidを抽出（必要であればDB再検索も可能ですが、JWTクレームで十分な場合はそのまま返す）
    user_id_str = identity.split(':')[1] if ':' in identity else identity
    try:
        user_id = int(user_id_str)
    except ValueError:
        user_id = 0
    
    return jsonify({
        "msg": "Session active",
        "user_id": user_id,
        "role_name": claims.get('role_name'),
        "full_name": claims.get('full_name'),
        "role_scopes": claims.get('role_scopes', [])
    }), 200

@auth_bp.route('/salaries', methods=['GET'])
@jwt_required()
def salaries():
    """認証テスト用のダミーエンドポイント"""
    current_supporter_id = get_jwt_identity()
    return jsonify({"data": f"Salary data for supporter {current_supporter_id}"}), 200