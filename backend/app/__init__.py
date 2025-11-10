# backend/app/__init__.py

from flask import Flask
from flask_cors import CORS
import os
from dotenv import load_dotenv
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager 

# プロジェクトルートにある設定ファイルをインポート
from config import Config 

# 拡張機能（db, bcryptなど）のインポート
from .extensions import db, migrate, bcrypt 

# .env ファイルから環境変数を読み込む
load_dotenv() 

def create_app():
    # 1. アプリケーションの初期化
    app = Flask(__name__)
    
    # 2. 設定のロード
    app.config.from_object(Config)

    # 3. 拡張機能の初期化（アプリへの紐付け）
    db.init_app(app)
    migrate.init_app(app, db, directory='migrations')
    CORS(app, supports_credentials=True) 
    bcrypt.init_app(app)
    jwt = JWTManager(app)

    # 4. モデルのインポート（DBテーブルのクラス定義をロード）
    from . import models 

    # 5. Blueprint（APIルート）のインポートと登録
    from .api.auth_routes import auth_bp
    from .api.user_routes import user_bp
    from .api.supporter_routes import supporter_bp 
    from .api.prospect_routes import prospect_bp
    from .api.record_routes import record_bp 
    from .api.support_plan_routes import support_plan_bp
    from .api.audit_log_routes import audit_log_bp 

    # --- Blueprint の登録 ---
    app.register_blueprint(auth_bp, url_prefix='/api')
    app.register_blueprint(user_bp, url_prefix='/api')
    app.register_blueprint(supporter_bp, url_prefix='/api') 
    app.register_blueprint(prospect_bp, url_prefix='/api') 
    app.register_blueprint(record_bp, url_prefix='/api') 
    app.register_blueprint(support_plan_bp, url_prefix='/api')
    app.register_blueprint(audit_log_bp, url_prefix='/api')

    return app

# ★★★ 修正: CLIコマンドの登録を外部に移すための準備 ★★★
# Flask 2.x の CLIコマンド登録は、appインスタンス作成後にapp.cliで自動的に行われるべきです
# しかし、ここではdb_structure_exporter.pyが直接appを読み込むため、関数定義は不要です。
# 代わりに、db_structure_exporter.py を修正します。
# --------------------------------------------------------------------------

# 以下のコードは、db_structure_exporter.pyに移動させます。
# from db_structure_exporter import export_db_report, print_report 
# @app.cli.command("db-report")
# def db_report_command():
#     from app.extensions import db as current_db
#     report = export_db_report(current_db)
#     print_report(report)