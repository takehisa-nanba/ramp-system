# app/__init__.py

from flask import Flask
from flask_cors import CORS
import os
from dotenv import load_dotenv

# 拡張機能（db, bcryptなど）のインポート
from .extensions import db, migrate, bcrypt 
from flask_jwt_extended import JWTManager 

load_dotenv() # .env ファイルから環境変数を読み込む

def create_app():
    # 1. アプリケーションの初期化
    app = Flask(__name__)
    
    # 2. 設定のロード
    # データベース設定
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # JWT のシークレットキー設定
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'your_super_secret_key_change_me_in_env') 

    # 3. 拡張機能の初期化（アプリへの紐付け）
    db.init_app(app)
    migrate.init_app(app, db, directory='migrations')
    CORS(app) # CORSを有効化
    bcrypt.init_app(app) # Bcrypt を初期化
    jwt = JWTManager(app) # JWTManager の初期化

    # 4. モデルのインポート（DBテーブルのクラス定義をロード）
    # この処理により、DBテーブルの構造がアプリに認識されます。
    from . import models 

    # 5. Blueprint（APIルート）のインポートと登録
    # app/api/ にある全てのルートを /api プレフィックスで登録
    from .api.user_routes import user_bp
    from .api.daily_log_routes import daily_log_bp
    from .api.auth_routes import auth_bp
    from .api.support_plan_routes import support_plan_bp
    from .api.attendance_routes import attendance_bp

    app.register_blueprint(user_bp, url_prefix='/api')
    app.register_blueprint(daily_log_bp, url_prefix='/api')
    app.register_blueprint(auth_bp, url_prefix='/api')
    app.register_blueprint(support_plan_bp, url_prefix='/api')
    app.register_blueprint(attendance_bp, url_prefix='/api')

    return app