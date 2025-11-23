from flask import Flask
#  修正点: 'from config' を 'from backend.config' に修正
from backend.config import Config
#  修正点: '.extensions' を 'backend.app.extensions' に修正
from backend.app.extensions import db, bcrypt, migrate, jwt, cors

def create_app(config_class=Config): # ★ 引数名を変更し、クラスを受け取れるようにする
    """アプリケーションファクトリ関数"""
    app = Flask(__name__)
    
    # 渡された設定クラス（本番ならConfig、テストならTestConfig）を適用
    app.config.from_object(config_class)

    cors.init_app(app, resources={r"/api/*": {"origins": "*", "supports_credentials": True}})

    # --- 1. 拡張機能の初期化 ---
    db.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app) # ★追加
    # cors.init_app(app, supports_credentials=True) # ★追加 (Cookie連携を許可)

    # --- 2. モデルを読み込む（DBのスキーマを認識させるため） ---
    with app.app_context():
        #  修正点: '.models' を 'backend.app.models' に修正
        from backend.app import models    
        # --- 3. ブループリント（APIルート）の登録 ---
        from backend.app.api import ALL_BLUEPRINTS # ★ALL_BLUEPRINTSだけをインポート
        
        for bp in ALL_BLUEPRINTS:
            # url_prefixは各Blueprint定義内ですでに設定されていますが、
            # ここで明示的に上書き・統一することも可能です。
            # 今回はBlueprint側で '/api/auth' 等と定義しているため、そのまま登録します。
            # もし '/api/{bp.name}' というルールで強制したい場合は url_prefix を指定してください。
            app.register_blueprint(bp) 
    
    return app