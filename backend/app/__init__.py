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

    cors.init_app(app, resources={r"/api/*": {"origins": app.config.get('CORS_ORIGINS', '*'), "supports_credentials": True}})

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
            app.register_blueprint(bp) 

    from backend.app.utils.errors import AppError
    from flask import jsonify

    @app.errorhandler(AppError)
    def handle_app_error(e):
        return jsonify({
            "success": False,
            "error": {
                "code": e.code,
                "message": e.message
            }
        }), e.status_code

    @app.errorhandler(Exception)
    def handle_unexpected_error(e):
        app.logger.exception(e)
        return jsonify({
            "success": False,
            "error": {
                "code": "SYSTEM_ERROR",
                "message": "システムエラーが発生しました。"
            }
        }), 500

    return app