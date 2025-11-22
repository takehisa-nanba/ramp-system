import pytest
import sys
import os
import logging  # ★ 追加

# -------------------------------------------------------------------
# パス解決のロジック
# -------------------------------------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_dir)

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.app import create_app, db
from backend.config import Config

# ★ ロガーの取得
logger = logging.getLogger(__name__)

class TestConfig(Config):
    """テスト専用の設定"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

@pytest.fixture
def app():
    """テスト用のアプリケーションを作成する"""
    logger.info("🛠️ SETUP: テスト用アプリケーションを初期化しています...") # ★ ログ
    
    app = create_app(TestConfig)

    with app.app_context():
        logger.debug("🗄️ DB: インメモリデータベースを作成中...") # ★ ログ
        db.create_all()
        
        yield app
        
        logger.debug("🗑️ TEARDOWN: データベースを破棄しています...") # ★ ログ
        db.session.remove()
        db.drop_all()
    
    logger.info("✅ CLEANUP: テスト用アプリケーションを終了しました") # ★ ログ

@pytest.fixture
def client(app):
    """テスト用のブラウザ（クライアント）を作成する"""
    return app.test_client()

@pytest.fixture
def runner(app):
    """テスト用のコマンドランナーを作成する"""
    return app.test_cli_runner()