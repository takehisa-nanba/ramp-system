from flask import Flask

def init_app(app: Flask):
    """
    全てのAPI Blueprintをここで一括登録する。
    create_app を汚さずに、ここでルートの追加・管理を行う。
    """
    # 1. 認証API
    from .auth_routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/api/auth')

    # 2. 利用者API (今後追加)
    from .user_routes import user_bp
    app.register_blueprint(user_bp, url_prefix='/api/users')

    # 3. 日報API (今後追加)
    from .daily_log_routes import daily_log_bp
    app.register_blueprint(daily_log_bp, url_prefix='/api/daily_logs')
    
    # 4. 支援計画API
    from .support_plan_routes import support_plan_bp
    app.register_blueprint(support_plan_bp, url_prefix='/api/support_plans')

