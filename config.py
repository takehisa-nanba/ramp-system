import os
from dotenv import load_dotenv

# プロジェクトルートの .env ファイルを読み込む
# (WSGIサーバーやCLI実行時に、この行がプロジェクトのスタートアップで実行される必要がある)
load_dotenv() 

class Config:
    # ----------------------------------------------------
    # 1. SQLAlchemy/PostgreSQL 設定
    # ----------------------------------------------------
    # .env の DATABASE_URL を Flask-SQLAlchemy のキーにマッピング
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    
    # トラッキングを無効化（リソース節約と警告回避のため推奨）
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ----------------------------------------------------
    # 2. JWT 設定
    # ----------------------------------------------------
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

    # ----------------------------------------------------
    # 3. Flask コア設定
    # ----------------------------------------------------
    SECRET_KEY = os.getenv("JWT_SECRET_KEY") # Flaskセッションなどで利用 (JWTキーを流用)

    # 開発環境用設定
    FLASK_ENV = os.getenv("FLASK_ENV", "production")
    DEBUG = (FLASK_ENV == "development")