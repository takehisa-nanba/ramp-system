from flask import Flask
# ★ 修正点: 'from config' を 'from ..config' に変更
# これにより、appパッケージの「親」にある config.py を正しく参照する
from backend.config import Config
# 拡張機能を「app/extensions.py」からインポートします
from backend.app.extensions import db, bcrypt, migrate

def create_app(config_name='default'):
    """アプリケーションファクトリ関数"""
    app = Flask(__name__)
    app.config.from_object(Config) # config.py を参照

    # --- 1. 拡張機能の初期化 ---
    db.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)  # Migrateをappとdbに紐づける

    # --- 2. モデルを読み込む（DBのスキーマを認識させるため） ---
    # この 'from . import models' が、
    # 'app/models/__init__.py' (大窓口) を呼び出します。
    with app.app_context():
        from . import models
    
    # --- 3. ブループリント（APIルート）の登録 ---
    # (現在はAPIを削除しているため、ここは空のままです)

    return app