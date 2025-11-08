# backend/config.py

import os
from dotenv import load_dotenv

# プロジェクトルートの .env ファイルを読み込む
load_dotenv() 

class Config:
    # ----------------------------------------------------
    # 1. SQLAlchemy/PostgreSQL 設定
    # ----------------------------------------------------
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ----------------------------------------------------
    # 2. Flask コア設定
    # ----------------------------------------------------
    # ⚠️ 推奨: JWTとは別の強力なランダムな値を使用
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "your_default_fallback_secret_key") 

    FLASK_ENV = os.getenv("FLASK_ENV", "production")
    DEBUG = (FLASK_ENV == "development")

    # ----------------------------------------------------
    # 3. JWT 設定 (Flask-JWT-Extended)
    # ----------------------------------------------------
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

    # JWTをどこに格納するかを定義 (ヘッダーではなくCookieを使用)
    JWT_TOKEN_LOCATION = ["cookies"]

    # Cookie名 (アクセス/リフレッシュトークン)
    # デフォルトから変更することで、Cookieを保護しやすくします
    JWT_ACCESS_COOKIE_NAME = "access_token_ramp" 
    JWT_REFRESH_COOKIE_NAME = "refresh_token_ramp"

    # XSS対策のため必須: JavaScriptからCookieにアクセスできないようにする
    JWT_COOKIE_SAMESITE = "Lax"

    # CSRF対策: Cookieベース認証では、トークンをCookieとヘッダーの両方でチェックします
    JWT_COOKIE_CSRF_PROTECT = True
    
    # 開発環境以外ではHTTPSでのみ送信
    # FLASK_ENVに基づき自動で切り替える
    if FLASK_ENV != "development":
        JWT_COOKIE_SECURE = True
    else:
        # ローカル開発環境では False に設定
        JWT_COOKIE_SECURE = False