from flask import Flask
# 🚨 修正点: 'from config' を 'from backend.config' に修正
from backend.config import Config
# 🚨 修正点: '.extensions' を 'backend.app.extensions' に修正
from backend.app.extensions import db, bcrypt, migrate

def create_app(config_class=Config): # ★ 引数名を変更し、クラスを受け取れるようにする
    """アプリケーションファクトリ関数"""
    app = Flask(__name__)
    
    # 渡された設定クラス（本番ならConfig、テストならTestConfig）を適用
    app.config.from_object(config_class)

    # --- 1. 拡張機能の初期化 ---
    db.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)

    # --- 2. モデルを読み込む（DBのスキーマを認識させるため） ---
    with app.app_context():
        # 🚨 修正点: '.models' を 'backend.app.models' に修正
        from backend.app import models
    
    # --- 3. ブループリント（APIルート）の登録 ---
    # (現在はAPIを削除しているため、ここは空のままです)

    return app