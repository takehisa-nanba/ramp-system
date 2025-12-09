# backend/tests/conftest.py

import pytest
import sys
import os
import logging  # ★ 追加
from dotenv import load_dotenv
from datetime import date
import uuid # staff_code 生成用
# -------------------------------------------------------------------
# パス解決のロジック
# -------------------------------------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_dir)

# ★★★ ここにコードを追加してください ★★★
# .env ファイルのパスを特定し、強制的にロードする
dotenv_path = os.path.join(backend_dir, '.env')
if os.path.exists(dotenv_path):
    # ★ 修正: override=True を追加して、既存の環境変数を強制的に上書きする
    load_dotenv(dotenv_path, override=True)
# ★★★ ここまで ★★★

if project_root not in sys.path:
    sys.path.insert(0, project_root)


from backend.app import create_app, db
from backend.config import Config
from backend.app.models import (
    User, Supporter, StatusMaster, OfficeSetting, Corporation, 
    MunicipalityMaster, RoleMaster, # RBAC, URAC, PIIテスト用
    OfficeServiceConfiguration
)

# ★ ロガーの取得
logger = logging.getLogger(__name__)

class TestConfig(Config):
    """テスト専用の設定"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

@pytest.fixture(scope='session')
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

# ★ NEW: setup_initial_masters フィクスチャを追加 (マスタデータの土台)
@pytest.fixture(scope='session')
def setup_initial_masters(app):
    """マスタデータを一度だけセットアップするフィクスチャ"""
    with app.app_context():
        if not db.session.query(StatusMaster).count():
            status = StatusMaster(name="利用中")
            muni = MunicipalityMaster(municipality_code="999999", name="Test City")
            db.session.add_all([status, muni])
            db.session.commit()
            return status, muni # 返すことで依存関係を確立

# ★ 修正: setup_supporters_and_roles (カナ氏名の追加)
@pytest.fixture(scope='function')
def setup_supporters_and_roles(app):
    """URACテストのために、職員とロールをセットアップするフィクスチャ"""
    with app.app_context():
        db.session.query(Supporter).delete()
        # ... (Corporationのチェックは省略) ...
        
        # staff_code, カナ氏名は NOT NULL のため必須
        staff = Supporter(
            staff_code="S002", last_name="Staff", first_name="A",
            last_name_kana="スタッフ", first_name_kana="エー", # ★ 追加
            employment_type="FULL_TIME", weekly_scheduled_minutes=2400, hire_date=date(2025, 1, 1)
        )
        manager = Supporter(
            staff_code="M101", last_name="Manager", first_name="B",
            last_name_kana="マネージャー", first_name_kana="ビー", # ★ 追加
            employment_type="FULL_TIME", weekly_scheduled_minutes=2400, hire_date=date(2025, 1, 1)
        )
        db.session.add_all([staff, manager])
        db.session.commit()
        
        yield staff, manager 

# ★ 修正: setup_active_user (setup_initial_masters への依存を修正し、カナ氏名を追加)
@pytest.fixture(scope='function')
def setup_active_user(app, setup_initial_masters):
    """日次人員配置テストのために、アクティブな利用者と職員をセットアップするフィクスチャ"""
    with app.app_context():
        # setup_initial_masters が実行されることを保証
        # setup_initial_masters の戻り値を受け取る必要は必ずしもないため、明示的に呼び出さない
        
        corp = db.session.query(Corporation).first() 
        muni = db.session.query(MunicipalityMaster).first()
        status = db.session.query(StatusMaster).first()
        
        # ★ 修正: OfficeSettingのセットアップを復元し、office変数を定義する ★
        office = db.session.query(OfficeSetting).first()
        if not office:
            # 必須カラムをここで定義し、ローカル変数 'office' に格納
            office = OfficeSetting(
                corporation_id=corp.id, 
                office_name="Test Office", 
                municipality_id=muni.id, 
                full_time_weekly_minutes=2400 # FTEテストに必須な分母
            )
            db.session.add(office)
            db.session.flush()
        
        # ... (OfficeSettingのセットアップ省略) ...

        # Supporter データのセットアップ (staff_code とカナ氏名は必須)
        staff = Supporter(
            staff_code=str(uuid.uuid4())[:4], last_name="Staff", first_name="Active", 
            last_name_kana="アクティブ", first_name_kana="スタッフ", # ★ 追加
            office_id=office.id, employment_type="FULL_TIME", weekly_scheduled_minutes=2400, hire_date=date(2025, 1, 1)
        )
        manager = Supporter(
            staff_code=str(uuid.uuid4())[:4], last_name="Manager", first_name="Lead", 
            last_name_kana="リード", first_name_kana="マネージャー", # ★ 追加
            office_id=office.id, employment_type="FULL_TIME", weekly_scheduled_minutes=2400, hire_date=date(2025, 1, 1)
        )
        user = User(display_name="TestUser", status_id=status.id)
        
        db.session.add_all([staff, manager, user])
        db.session.commit()
        
        yield user, staff, manager