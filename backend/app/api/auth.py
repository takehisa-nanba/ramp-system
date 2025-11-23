# backend/app/api/auth.py (新規作成)

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, set_access_cookies, unset_jwt_cookies, jwt_required, get_jwt_identity
from backend.app.services.core_service import authenticate_supporter
from backend.app.models import Supporter # 型ヒントとしてインポート

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/login', methods=['POST'])
def login():
    """職員のログイン処理"""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"msg": "Missing email or password"}), 400

    supporter: Supporter = authenticate_supporter(email, password)
    
    if supporter:
        # ロール情報は JWT claims に含めるのが一般的ですが、今回はダミーIDを使用
        # 🚨 修正点: identity=supporter.id を identity=str(supporter.id) に修正
        additional_claims = {
            "role_id": 1, 
            "full_name": f"{supporter.last_name} {supporter.first_name}"
        }
        access_token = create_access_token(identity=str(supporter.id), additional_claims=additional_claims)
        
        response = jsonify({
            "msg": "Login successful", 
            "supporter_id": supporter.id, 
            "role_id": 1, 
            "full_name": f"{supporter.last_name} {supporter.first_name}"
        })
        
        set_access_cookies(response, access_token)
        return response, 200
    else:
        return jsonify({"msg": "Invalid credentials"}), 401

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