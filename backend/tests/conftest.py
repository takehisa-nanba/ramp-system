import pytest
import sys
import os

# -------------------------------------------------------------------
# パス解決のロジック（修正）
# -------------------------------------------------------------------
# テスト実行時、'backend' パッケージをルートから認識させるため、
# 2階層上（プロジェクトルート）をシステムパスに追加する。

# .../backend/tests
current_dir = os.path.dirname(os.path.abspath(__file__))
# .../backend
backend_dir = os.path.dirname(current_dir)
# .../ramp-system (Project Root)
project_root = os.path.dirname(backend_dir)

# パスの先頭に追加して優先させる
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.app import create_app, db
from backend.config import Config

class TestConfig(Config):
    """テスト専用の設定"""
    TESTING = True
    # テストは高速化と安全性のため、メモリ上の使い捨てDB(SQLite)を使う
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    # CSRF保護などはテスト中は無効化することもあるが、一旦そのまま

@pytest.fixture
def app():
    """テスト用のアプリケーションを作成する"""
    # Configオブジェクトを直接渡してアプリを作成
    app = create_app(TestConfig) 

    with app.app_context():
        # テスト開始前に全テーブルを作成
        db.create_all()
        yield app
        # テスト終了後に全テーブルを削除（クリーンアップ）
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """テスト用のブラウザ（クライアント）を作成する"""
    return app.test_client()

@pytest.fixture
def runner(app):
    """テスト用のコマンドランナーを作成する"""
    return app.test_cli_runner()