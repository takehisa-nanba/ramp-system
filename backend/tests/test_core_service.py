import pytest
import os
import logging
from datetime import datetime, timezone, date, timedelta
from backend.app.extensions import db, bcrypt
from backend.app.models import (
    # モデルのインポート（テストデータ作成に必要）
    Supporter, SupporterPII, User, UserPII,
    Corporation, OfficeSetting, OfficeServiceConfiguration,
    MunicipalityMaster, ServiceTypeMaster, StatusMaster,
    ServiceCertificate, GrantedService, ContractReportDetail,
)
from backend.app.services.core_service import (
    authenticate_supporter, 
    get_supporter_by_id, 
    get_corporation_id_for_user,
    get_system_pii_key
    # get_corporation_kekは環境変数に依存するためテストは簡易的に
)

# --- テスト用のデータ ---
TEST_EMAIL = "core_logic@rampsys.jp"
TEST_PASSWORD = "CorePass123!"
TEST_EMPLOYEE_ID = "C999"

logger = logging.getLogger(__name__)

@pytest.fixture(scope="module")
def setup_test_data(app):
    """
    認証ロジック検証用の職員データと、契約チェーン検証用の組織・利用者データを作成する。
    """
    with app.app_context():
        # 1. 認証用職員データのクリーンアップ
        SupporterPII.query.filter_by(email=TEST_EMAIL).delete()
        db.session.commit()
        
        # 認証用職員データの作成
        supporter = Supporter(
            employee_id=TEST_EMPLOYEE_ID,
            last_name="コア",
            first_name="ロジック",
            last_name_kana="コア",
            first_name_kana="ロジック",
            hire_date=datetime.now(timezone.utc).date(),
            employment_type="FULL_TIME",
            weekly_scheduled_minutes=2400,
            is_active=True
        )
        db.session.add(supporter)
        db.session.flush() 
        
        pii = SupporterPII(
            supporter_id=supporter.id,
            email=TEST_EMAIL,
        )
        pii.set_password(TEST_PASSWORD)
        db.session.add(pii)
        db.session.commit()
        
        # 契約チェーンテスト用のマスタ、組織、利用者をここで作成（テスト間で共有）
        
        # 2. 組織・マスタの作成 (ID: 999 の法人を期待)
        corp = Corporation(id=999, corporation_name="Test Corp 999", corporation_type="KK")
        db.session.add(corp)
        
        muni = MunicipalityMaster(municipality_code="123456", name="Test City")
        stype = ServiceTypeMaster(name="Test Service", service_code="TS", required_review_months=6)
        status = StatusMaster(name="Test Status")
        db.session.add_all([muni, stype, status])
        db.session.flush()

        office = OfficeSetting(corporation_id=corp.id, office_name="Test Office", municipality_id=muni.id, full_time_weekly_minutes=2400)
        db.session.add(office)
        db.session.flush()

        service_config = OfficeServiceConfiguration(
            office_id=office.id, 
            service_type_master_id=stype.id,
            jigyosho_bango="1234567890",
            capacity=20
        )
        db.session.add(service_config)
        db.session.flush()

        # 3. ユーザーと契約チェーンの作成
        user = User(display_name="Test User", status_id=status.id)
        db.session.add(user)
        db.session.flush()

        cert = ServiceCertificate(user_id=user.id, certificate_issue_date=date.today() - timedelta(days=365), municipality_master_id=muni.id, office_service_configuration_id=service_config.id)
        db.session.add(cert)
        db.session.flush()

        grant = GrantedService(certificate_id=cert.id, granted_start_date=date.today() - timedelta(days=360), granted_end_date=date.today() + timedelta(days=360), service_type_master_id=stype.id)
        db.session.add(grant)
        db.session.flush()

        contract = ContractReportDetail(
            granted_service_id=grant.id,
            office_service_configuration_id=service_config.id # これが Corp ID 999 にリンクする
        )
        db.session.add(contract)
        db.session.commit()

        # テスト実行中はセッションを維持
        yield {"supporter": supporter, "user": user, "corp_id": corp.id}

# ====================================================================
# 1. 認証ロジックの単体テスト
# ====================================================================

@pytest.mark.usefixtures("setup_test_data")
def test_authenticate_supporter_success(app):
    """正常な認証が Supporter オブジェクトを返すこと。"""
    supporter = authenticate_supporter(TEST_EMAIL, TEST_PASSWORD)
    assert supporter is not None
    assert supporter.last_name == "コア"

@pytest.mark.usefixtures("setup_test_data")
def test_authenticate_supporter_fail_password(app):
    """パスワード間違いで認証に失敗すること。"""
    supporter = authenticate_supporter(TEST_EMAIL, "WrongPassword")
    assert supporter is None

# ====================================================================
# 2. データアクセスロジックの単体テスト
# ====================================================================

@pytest.mark.usefixtures("setup_test_data")
def test_get_supporter_by_id_success(setup_test_data):
    """IDで職員を正しく取得できること。"""
    supporter_id = setup_test_data["supporter"].id
    found_supporter = get_supporter_by_id(supporter_id)
    assert found_supporter is not None
    assert found_supporter.id == supporter_id
    
# ====================================================================
# 3. 契約チェーンと鍵ロジックの単体テスト
# ====================================================================

@pytest.mark.usefixtures("setup_test_data")
def test_get_corporation_id_for_user_success(setup_test_data):
    """
    利用者データから契約チェーンを辿って正しい法人IDを取得できること。
    期待値はフィクスチャで設定した ID 999。
    """
    user_to_test = setup_test_data["user"]
    expected_corp_id = setup_test_data["corp_id"] # 999
    
    result_id = get_corporation_id_for_user(user_to_test)

    # 4. 判定: 期待通り 999 が返ってくるか？
    assert result_id == expected_corp_id
    
def test_get_system_pii_key_default(app):
    """PII_ENCRYPTION_KEY がない場合、デフォルトのキーを返すこと（フォールバック）。"""
    # core_service.py のロジックに依存
    key = get_system_pii_key()
    assert isinstance(key, bytes)
    # デフォルトの鍵が設定されていることを確認
    assert key == b'XyZ7aBCdEfGhIjKlMnOpQrStUvWxYz0123456789Abc='