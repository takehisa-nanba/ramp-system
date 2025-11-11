# app/api/auth_routes.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt, set_access_cookies, unset_jwt_cookies, get_jwt_identity
from functools import wraps
from app.extensions import db 
from app.models.core import Supporter
from app.models.master import RoleMaster, JobTitleMaster, SystemPermission 
from app.models.hr import SupporterJobAssignment
from app.models.core import User
from app.models.audit_log import SystemLog # 監査ログAPIで使用
from sqlalchemy import select

# 認証用の Blueprint を作成
auth_bp = Blueprint('auth', __name__)

# ======================================================
# 1. 職員ログイン API (POST /api/login) - 変更なし
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
    
    # 3. 認証成功: 職員のJobTitle名を取得し、クレームに追加（認証チェックを高速化するため）
    # (ここではレガシー互換性のためRole IDを渡すが、本来は JobTitle IDを渡すべき)
    
    # 監査ログ: ログイン成功を記録 (SystemLogに記録するAPIは別途作成推奨)
    
    access_token = create_access_token(identity=str(supporter.id), additional_claims={
        'role_id': supporter.role_id, # レガシー互換性のため残す
        'supporter_id': supporter.id
    })

    response = jsonify(
        msg="ログインに成功しました",
        supporter_id=supporter.id,
        role_id=supporter.role_id,
        full_name=f"{supporter.last_name} {supporter.first_name}"
    )
    
    set_access_cookies(response, access_token) 
    return response, 200

# ======================================================
# 2. RBAC/パーミッション デコレーターの実装
# ======================================================

def _check_permission(supporter_id: int, required_permission_code: str, db_session) -> bool:
    """
    指定された職員IDが、指定されたパーミッションコードを持っているか検証する。
    JobTitleの標準パーミッション、または個人設定(Override)で許可されていればOK。
    """
    
    # 1. パーミッションコードに対応する ID を取得
    permission = db_session.execute(
        select(SystemPermission.id)
        .where(SystemPermission.code == required_permission_code)
    ).scalar_one_or_none()
    
    if not permission:
        # 要求されたパーミッションコード自体が存在しない
        return False
        
    # 2. 職員が持つすべての JobTitle ID を取得
    job_titles = db_session.execute(
        select(SupporterJobAssignment.job_title_id)
        .where(SupporterJobAssignment.supporter_id == supporter_id)
        .where(SupporterJobAssignment.end_date == None) # 現在有効な職務のみ
    ).scalars().all()
    
    if not job_titles:
        return False # 職務が割り当てられていなければアクセス拒否

    # 3. JobTitleに基づく標準パーミッションをチェック
    has_standard_permission = db_session.execute(
        select(JobTitleMaster)
        .join(JobTitleMaster.standard_permissions)
        .where(JobTitleMaster.id.in_(job_titles))
        .where(JobTitleMaster.standard_permissions.c.permission_id == permission) # 中間テーブルのc属性を使って結合
    ).first()
    
    # 4. 個人の上書き（Override）設定をチェック (高度な機能、ここでは簡略化)
    # is_allowed=True のパーミッションが JobTitleMaster のパーミッションを上書きする

    # ★ 現状、標準パーミッションで許可されていればアクセスOKとする
    return has_standard_permission is not None

def permission_required(permission_code: str):
    """
    指定されたパーミッションコードを持つユーザーのみにアクセスを許可するデコレーター
    """
    def wrapper(fn):
        @wraps(fn)
        @jwt_required()
        def decorator(*args, **kwargs):
            try:
                supporter_id = get_jwt_identity()
                
                # データベース処理は app_context 内で行う
                with db.get_engine().connect() as connection:
                    session = db.session(bind=connection)
                    
                    if _check_permission(int(supporter_id), permission_code, session):
                        # 権限がある場合
                        return fn(*args, **kwargs)
                    else:
                        # 権限がない場合
                        return jsonify(msg=f"権限がありません (パーミッション '{permission_code}' 不足)"), 403
            
            except Exception as e:
                # デバッグ用にエラーを出力
                import traceback
                traceback.print_exc()
                return jsonify(msg=f"認証エラーが発生しました: {str(e)}"), 500
                
        return decorator
    return wrapper

# ★ 互換性のために古いデコレーターの名前を新しいデコレーターにマップ ★
role_required = permission_required 

# ======================================================
# 3. 監査ログ取得 API (GET /api/system_logs)
# ======================================================
@auth_bp.route('/system_logs', methods=['GET'])
# ★ 修正: SYSTEM_LOG_READ パーミッションが必要
@permission_required('SYSTEM_LOG_READ')
def get_system_logs():
    """
    システムログ（監査ログ）を取得します。
    """
    plan_id = request.args.get('plan_id', type=int)
    # (省略: ロジックはSystemLogをクエリする既存のロジックを流用)
    
    # 例として、常に空のリストを返す (実際のクエリは省略)
    return jsonify([]), 200

# ======================================================
# 4. ログアウト API (POST /api/logout) - 変更なし
# ======================================================
@auth_bp.route('/logout', methods=['POST'])
def logout():
    response = jsonify(msg="ログアウトしました")
    unset_jwt_cookies(response)
    return response, 200
