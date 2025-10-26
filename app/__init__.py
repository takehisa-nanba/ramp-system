# app/__init__.py
from flask import Flask
from flask_cors import CORS
import os
from dotenv import load_dotenv

# extensions から db, migrate, bcrypt をインポート
from .extensions import db, migrate, bcrypt 
from flask_jwt_extended import JWTManager # ★ 追加 ★

load_dotenv() 

def create_app():
    app = Flask(__name__)
    
    # データベース設定
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # ★ JWT のシークレットキー設定 ★
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'your_super_secret_key_change_me_in_env') 

    # 拡張機能の初期化
    db.init_app(app)
    migrate.init_app(app, db, directory='migrations')
    CORS(app)
    bcrypt.init_app(app) # Bcrypt を初期化
    
    jwt = JWTManager(app) # ★ JWTManager の初期化 ★

    # ルートのインポート
    from .api.auth_routes import auth_bp
    from .api.user_routes import user_bp
    from .api.daily_log_routes import daily_log_bp
    from .api.support_plan_routes import support_plan_bp
    from .api.attendance_routes import attendance_bp 
    
    # ★ 必須: 全てのモデルファイルをインポートする行を、手動で追加 ★
    from .models import core, master, plan_audit 
    
    # Blueprint の登録（全て /api プレフィックスで統一）
    app.register_blueprint(auth_bp, url_prefix='/api')
    app.register_blueprint(user_bp, url_prefix='/api')
    app.register_blueprint(daily_log_bp, url_prefix='/api')
    app.register_blueprint(support_plan_bp, url_prefix='/api')
    app.register_blueprint(attendance_bp, url_prefix='/api')

    return app