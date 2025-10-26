# app/api/auth_routes.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt
from functools import wraps
from app.extensions import db 
from app.models import Supporter, RoleMaster

# 認証用の Blueprint を作成
auth_bp = Blueprint('auth', __name__)

# ======================================================
# 1. 職員ログイン API (POST /api/login)
# ======================================================
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"msg": "メールアドレスとパスワードを入力してください。"}), 400

    # 1. 職員をメールアドレスで検索
    supporter = Supporter.query.filter_by(email=email).first()

    # 2. 認証チェック
    if supporter is None or not supporter.check_password(password):
        return jsonify({"msg": "認証情報が無効です。"}), 401

# 3. 認証成功: アクセストークンを生成
# identity=supporter.id を identity=str(supporter.id) に修正
    access_token = create_access_token(identity=str(supporter.id), additional_claims={
        'role_id': supporter.role_id,
        'role_name': supporter.role.name 
    })

    # 4. レスポンスを返す
    return jsonify(
        access_token=access_token,
        supporter_id=supporter.id,
        role_id=supporter.role_id,
        full_name=f"{supporter.last_name} {supporter.first_name}"
    ), 200

# ======================================================
# 2. RBAC デコレーターの実装 (全てのインポートが上部にあるため、問題なく動作)
# ======================================================
def role_required(role_names):
    """ 指定されたロールのいずれかを持つユーザーのみにアクセスを許可するデコレーター """
    def wrapper(fn):
        @wraps(fn)
        @jwt_required() # まず、トークン認証を必須にする
        def decorator(*args, **kwargs):
            claims = get_jwt()
            user_role_id = claims.get('role_id')

            # ユーザーのロール名を取得
            user_role = RoleMaster.query.get(user_role_id)
            if user_role and user_role.name in role_names:
                # 権限がある場合
                return fn(*args, **kwargs)
            else:
                # 権限がない場合
                return jsonify(msg="権限がありません (アクセスロール不足)"), 403
        return decorator
    return wrapper

# ======================================================
# 3. 機密データ API (テスト用)
# ======================================================
@auth_bp.route('/salaries', methods=['GET'])
@role_required(['経営者', '管理者']) # アクセスを管理者以上のロールに制限
def get_salaries():
    """ 経営層（管理者以上）のみがアクセスできるダミーの給与データ """
    return jsonify({
        "msg": "機密情報へのアクセスが許可されました。",
        "data": [
            {"supporter": "佐藤健太", "salary": "7,000,000 JPY"},
            {"supporter": "山田花子", "salary": "4,500,000 JPY"}
        ]
    }), 200

# ======================================================
# 4. 監査ログ取得 API (GET /api/system_logs)
# ======================================================
@auth_bp.route('/system_logs', methods=['GET'])
@role_required(['サービス管理責任者', '管理者', '経営者']) # ★ 監査ログへのアクセスを制限 ★
def get_system_logs():
    # クエリパラメータから plan_id を取得し、特定の計画に絞り込む（オプション）
    plan_id = request.args.get('plan_id', type=int)

    # 1. 監査ログと実行職員の情報を結合して取得
    log_query = db.select(
        SystemLog,
        Supporter.last_name.label('supporter_last_name'),
        Supporter.first_name.label('supporter_first_name')
    ).join(Supporter, SystemLog.supporter_id == Supporter.id)
    
    if plan_id:
        # 特定の計画に絞り込む
        log_query = log_query.where(SystemLog.target_plan_id == plan_id)

    # 監査ログは新しいものから順に表示
    logs = db.session.execute(
        log_query.order_by(SystemLog.timestamp.desc())
    ).all()
    
    # 2. 結果をJSON形式に整形
    log_list = []
    for log_row in logs:
        log = log_row[0]
        
        log_list.append({
            "id": log.id,
            "timestamp": log.timestamp.isoformat(),
            "action": log.action,
            "supporter_name": f"{log_row.supporter_last_name} {log_row.supporter_first_name}",
            "target_user_id": log.target_user_id,
            "target_plan_id": log.target_plan_id,
            "details": log.details
        })
        
    return jsonify(log_list), 200

