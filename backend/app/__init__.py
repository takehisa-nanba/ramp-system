from flask import Flask
from backend.config import Config
from backend.app.extensions import db, bcrypt, migrate, jwt

def create_app(config_class=Config):
    """アプリケーションファクトリ関数"""
    app = Flask(__name__)
    
    # 渡された設定クラス（本番ならConfig、テストならTestConfig）を適用
    app.config.from_object(config_class)

    # --- 1. 拡張機能の初期化 ---
    db.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app) # ★ 追加: JWTの初期化

    # --- 2. モデルを読み込む（DBのスキーマを認識させるため） ---
    with app.app_context():
        # 🚨 修正点: '.models' を 'backend.app.models' に修正
        from backend.app import models
    
    # --- 3. APIルートの一括登録（Switchboard） ---
    # ★ 修正: 個別のbpをインポートせず、apiパッケージに任せる
    from backend.app import api
    api.init_app(app)

    return app