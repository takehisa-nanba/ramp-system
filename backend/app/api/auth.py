# backend/app/api/auth.py (新規ファイル)

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, unset_jwt_cookies, set_access_cookies
from backend.app.services.core_service import authenticate_supporter

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['POST'])
def login():
    """職員ログイン処理"""
    data = request.get_json()
    email = data.get('email', None)
    password = data.get('password', None)

    # 1. サービス層の認証関数を呼び出す
    supporter = authenticate_supporter(email, password)

    if supporter:
        # 2. ロール情報などを claims に含める (簡略化)
        role_name = "STAFF"
        access_token = create_access_token(identity=supporter.id, additional_claims={'roles': [role_name]})
        
        response = jsonify({
            'msg': 'Login successful',
            'supporter_id': supporter.id,
            'full_name': f"{supporter.last_name} {supporter.first_name}",
            'role_name': role_name
        })
        
        # 3. HTTP-Only Cookieにトークンを設定 (セキュリティ対策)
        set_access_cookies(response, access_token) 

        return response, 200
    
    return jsonify({"msg": "Invalid credentials"}), 401

@auth_bp.route('/logout', methods=['POST'])
@jwt_required() # 認証済みのユーザーのみ実行可能
def logout():
    """ログアウト処理（Cookie削除）"""
    response = jsonify({"msg": "Successfully logged out"})
    # JWT Cookieを削除
    unset_jwt_cookies(response)
    return response, 200