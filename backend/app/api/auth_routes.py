# backend/app/api/auth_routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, 
    create_refresh_token, 
    jwt_required, 
    # refresh_token_required, # ★ 追加
    get_jwt_identity
)
# ★ 修正: get_supporter_by_id を追加
from backend.app.services.core_service import authenticate_supporter, get_supporter_by_id 
from backend.app.models import Supporter
# Blueprintの作成（APIのグループ化）
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    ログインAPI。
    Emailとパスワードを検証し、JWTアクセストークンとリフレッシュトークンを返す。
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
    identity_data = str(supporter.id) 
    access_token = create_access_token(identity=identity_data)
    refresh_token = create_refresh_token(identity=identity_data) # ★ 追加

    return jsonify(
        access_token=access_token,
        refresh_token=refresh_token # ★ 追加
    ), 200

# @auth_bp.route('/refresh', methods=['POST'])
# @refresh_token_required # ★ リフレッシュトークンを要求
# def refresh():
#     """
#     リフレッシュトークンを使用して新しいアクセストークンを生成する。
#     """
#     current_user_id = get_jwt_identity() 
    
#     # 新しいアクセストークンのみを発行 (リフレッシュトークンは再発行しない)
#     new_access_token = create_access_token(identity=current_user_id)
    
#     return jsonify(access_token=new_access_token), 200 # ★ 追加: /refresh エンドポイント

@auth_bp.route('/me', methods=['GET'])
@jwt_required() # ★ このデコレータで保護（通行証が必要）
def get_current_user():
    """
    現在ログインしているユーザーの情報を返す。
    """
    # トークンからIDを取り出す
    current_user_id = get_jwt_identity()
    
    # ★ 修正: サービス層を経由してSupporterを取得
    supporter = get_supporter_by_id(int(current_user_id))
    
    if not supporter:
        return jsonify({"msg": "User not found"}), 404
        
    return jsonify({
        "id": supporter.id,
        "name": f"{supporter.last_name} {supporter.first_name}",
        # PIIへのアクセスは、PIIモデルのプロパティを介して安全に行われることを想定
        "email": supporter.pii.email if supporter.pii else None, 
        # ロール情報なども将来ここに追加
    }), 200