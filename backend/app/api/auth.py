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

    if not login_id or not password:
        return jsonify({"msg": "Missing credentials"}), 400

    from backend.app.services.core_service import authenticate_user
    
    # 1. 職員としての認証を試行
    supporter = authenticate_supporter(login_id, password)
    if supporter:
        role_name = "STAFF"
        identity = f"staff:{supporter.id}"
        full_name = f"{supporter.last_name} {supporter.first_name}"
        user_id = supporter.id
    else:
        # 2. 利用者としての認証を試行
        user = authenticate_user(login_id, password)
        if user:
            role_name = "USER"
            identity = f"user:{user.id}"
            full_name = user.display_name
            user_id = user.id
        else:
            return jsonify({"msg": "Invalid credentials"}), 401

    additional_claims = {
        "role_name": role_name,
        "full_name": full_name
    }
    access_token = create_access_token(identity=identity, additional_claims=additional_claims)
    
    response = jsonify({
        "msg": "Login successful", 
        "user_id": user_id, 
        "role_name": role_name, 
        "full_name": full_name
    })
    
    set_access_cookies(response, access_token)
    return response, 200


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """ログアウト処理（Cookieを削除）"""
    response = jsonify({"msg": "Logout successful"})
    unset_jwt_cookies(response)
    return response, 200

@auth_bp.route('/salaries', methods=['GET'])
@jwt_required()
def salaries():
    """認証テスト用のダミーエンドポイント"""
    current_supporter_id = get_jwt_identity()
    return jsonify({"data": f"Salary data for supporter {current_supporter_id}"}), 200