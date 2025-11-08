# app/__init__.py

from flask import Flask
from flask_cors import CORS
import os
from dotenv import load_dotenv

# プロジェクトルートにある設定ファイルをインポート
from config import Config  # ★ 修正: config.py から Config クラスをインポート ★

# 拡張機能（db, bcryptなど）のインポート
from .extensions import db, migrate, bcrypt 
from flask_jwt_extended import JWTManager 

# .env ファイルから環境変数を読み込む（プロジェクトルートでの実行を想定）
load_dotenv() 

def create_app():
    # 1. アプリケーションの初期化
    app = Flask(__name__)
    
    # 2. 設定のロード
    # ★ 修正: config.py からすべての設定を一括でロードする ★
    app.config.from_object(Config)

    # 3. 拡張機能の初期化（アプリへの紐付け）
    db.init_app(app)
    migrate.init_app(app, db, directory='migrations')
    
    # ★ 修正: Cookie認証を有効にするため supports_credentials=True を設定 ★
    # origins="*" の場合、セキュリティ警告が出る可能性があるため、
    # 開発中は "http://localhost:5173" などフロントのURLに制限することが推奨されます。
    CORS(app, supports_credentials=True) 
    
    bcrypt.init_app(app) # Bcrypt を初期化
    jwt = JWTManager(app) # JWTManager の初期化 (config から設定を読み込む)

    # 4. モデルのインポート（DBテーブルのクラス定義をロード）
    from . import models 

    # 5. Blueprint（APIルート）のインポートと登録
    # 認証 (ログイン・ログアウト)
    from .api.auth_routes import auth_bp    
    # 利用者 (User)
    from .api.user_routes import user_bp    
    # 職員 (Supporter)
    from .api.supporter_routes import supporter_bp # ★ 新規追加    
    # 見込み客 (Prospect)
    from .api.prospect_routes import prospect_bp # ★ 新規追加    
    # サービス記録 (ServiceRecord)
    from .api.record_routes import record_bp # ★ 新規追加
    # 個別支援計画 (SupportPlan)
    from .api.support_plan_routes import support_plan_bp    
    # 監査ログ (SystemLog)
    from .api.audit_log_routes import audit_log_bp # ★ 新規追加

    # --- Blueprint の登録 ---
    app.register_blueprint(auth_bp, url_prefix='/api')
    app.register_blueprint(user_bp, url_prefix='/api')
    app.register_blueprint(supporter_bp, url_prefix='/api')     # ★ 新規追加
    app.register_blueprint(prospect_bp, url_prefix='/api')       # ★ 新規追加
    app.register_blueprint(record_bp, url_prefix='/api')         # ★ 新規追加
    app.register_blueprint(support_plan_bp, url_prefix='/api')
    app.register_blueprint(audit_log_bp, url_prefix='/api')      # ★ 新規追加
    
    return app