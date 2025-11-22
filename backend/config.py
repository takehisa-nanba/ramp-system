import os
from datetime import timedelta # ★ 追加

# データベースのURIを環境変数から取得（なければデフォルトのSQLite）
basedir = os.path.abspath(os.path.dirname(__file__))
DATABASE_URL = os.environ.get('DATABASE_URL') or \
    'sqlite:///' + os.path.join(basedir, 'app.db')

class Config:
    """
    アプリケーションの設定（コンフィグ）を管理するクラス。
    """
    
    # --- 必須設定 ---
    
    # セキュリティキー (Flaskのセッション管理などに必須)
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-very-secret-key-that-you-should-change'
    
    # SQLAlchemyの設定
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # --- JWT設定 (Auth) ★ 追加 ---
    # 🚨 本番では必ず強力なランダム文字列に変更すること
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'super-secret-jwt-key-change-this'
    # トークンの有効期限 (例: 12時間)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=12)