import json
import pytest
from datetime import datetime, timezone
from backend.app.extensions import db
from backend.app.models import Supporter, SupporterPII 
# SupporterPIIにはパスワードハッシュ用の check_password メソッドが必要です。

# --- テスト用のグローバルなデータ ---
TEST_EMAIL = "test_auth@rampsys.jp"
TEST_PASSWORD = "TestPass123!"
TEST_EMPLOYEE_ID = "T001"

@pytest.fixture(scope="module")
def setup_test_data(app):
    """
    テストモジュール実行前に、認証に必要なダミー職員データをDBに作成する。
    """
    with app.app_context():
        # 既存のテストデータをクリーンアップ（テストの独立性を保証）
        SupporterPII.query.filter_by(email=TEST_EMAIL).delete()
        db.session.commit()
        
        # 1. Supporter 本体を作成（必要な情報のみ）
        supporter = Supporter(
            employee_id=TEST_EMPLOYEE_ID,
            last_name="テスト",
            first_name="職員",
            last_name_kana="テスト",
            first_name_kana="ショクイン",
            hire_date=datetime.now(timezone.utc).date(),
            employment_type="FULL_TIME",
            weekly_scheduled_minutes=2400,
            is_active=True
        )
        db.session.add(supporter)
        db.session.flush() # IDを取得するため一旦Flush
        
        # 2. SupporterPII (認証情報) を作成
        pii = SupporterPII(
            supporter_id=supporter.id,
            email=TEST_EMAIL,
        )
        # パスワードをハッシュ化して設定（SupporterPIIモデルのメソッドを使用）
        pii.set_password(TEST_PASSWORD)
        db.session.add(pii)
        
        db.session.commit()
        
        # このフィクスチャを呼び出したテストにデータを提供
        yield supporter
        
        # テスト後処理は conftest.py の app フィクスチャで処理されるため省略可

# ====================================================================
# 機能テストケース
# ====================================================================

@pytest.mark.usefixtures("setup_test_data")
def test_1_login_success(client):
    """
    POST /api/auth/login: 正しいクレデンシャルで認証に成功し、両トークンが返されること。
    """
    response = client.post(
        '/api/auth/login',
        data=json.dumps({'email': TEST_EMAIL, 'password': TEST_PASSWORD}),
        content_type='application/json'
    )
    data = response.get_json()

    assert response.status_code == 200
    assert 'access_token' in data
    assert 'refresh_token' in data
    
    # トークンを他のテストのために pytest のグローバル属性として保存
    pytest.access_token = data['access_token']
    pytest.refresh_token = data['refresh_token']


@pytest.mark.usefixtures("setup_test_data")
def test_2_login_failure_wrong_password(client):
    """
    POST /api/auth/login: 間違ったパスワードで認証に失敗すること。
    """
    response = client.post(
        '/api/auth/login',
        data=json.dumps({'email': TEST_EMAIL, 'password': 'WrongPassword'}),
        content_type='application/json'
    )
    data = response.get_json()

    assert response.status_code == 401
    assert data['msg'] == "Bad email or password"


def test_3_me_endpoint_success(client):
    """
    GET /api/auth/me: 有効なアクセストークンでユーザー情報を取得できること。
    """
    # test_1_login_success が成功している前提
    if not hasattr(pytest, 'access_token'):
         return # ログインテストが失敗している場合はスキップ
         
    response = client.get(
        '/api/auth/me',
        headers={'Authorization': f'Bearer {pytest.access_token}'}
    )
    data = response.get_json()

    assert response.status_code == 200
    assert data['email'] == TEST_EMAIL
    assert data['name'] == "テスト 職員" # Supporterモデルの平文の氏名


def def_4_refresh_token_success(client):
    """
    POST /api/auth/refresh: リフレッシュトークンで新しいアクセストークンを取得できること。
    """
    if not hasattr(pytest, 'refresh_token'):
         return

    response = client.post(
        '/api/auth/refresh',
        headers={'Authorization': f'Bearer {pytest.refresh_token}'}
    )
    data = response.get_json()

    assert response.status_code == 200
    assert 'access_token' in data
    assert data['access_token'] != pytest.access_token # 新旧トークンが異なることを確認
    
    # 後続テストのために新しいトークンを保存
    pytest.access_token = data['access_token']


def def_5_me_endpoint_failure_no_token(client):
    """
    GET /api/auth/me: トークンなしでアクセスすると失敗すること。
    """
    response = client.get('/api/auth/me')
    assert response.status_code == 401 # Unauthorized