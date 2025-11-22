import pytest
import logging
from datetime import date
from backend.app import db
from backend.app.models import User, Supporter, SupporterPII, StatusMaster, UserPII

logger = logging.getLogger(__name__)

def test_user_api_access(client, app):
    """
    利用者APIの動作検証。
    認証、一覧取得、詳細取得（自動復号）をテストする。
    """
    logger.info("🚀 TEST START: 利用者APIの検証を開始します")

    with app.app_context():
        # --- 1. 準備: マスタとデータ ---
        status = StatusMaster(name="利用中")
        db.session.add(status)
        db.session.flush()

        # 職員（ログイン用）
        supporter = Supporter(
            last_name="Admin", first_name="User", last_name_kana="アドミン", first_name_kana="ユーザー",
            employment_type="FULL_TIME", weekly_scheduled_minutes=2400, hire_date=date(2025, 1, 1)
        )
        # パスワード設定 ("password123")
        pii = SupporterPII(email="admin@test.com")
        pii.set_password("password123")
        supporter.pii = pii
        
        db.session.add(supporter)
        db.session.flush()

        # 利用者（ターゲット）
        user = User(display_name="TestUserA", status_id=status.id)
        user.pii = UserPII(
            email="user@test.com", 
            phone_number="090-0000-0000"
        )
        # 暗号化データのセット (プロパティ経由で自動暗号化される)
        user.pii.certificate_number = "1234567890" # 最高機密
        user.pii.last_name = "Tanaka" # 機密
        
        db.session.add(user)
        db.session.commit()
        
        user_id = user.id

    # --- 2. 認証なしでのアクセス（失敗すべき） ---
    logger.info("🔹 ステップ1: 認証なしアクセス")
    res = client.get('/api/users/')
    assert res.status_code == 401
    logger.debug("   -> 401 Unauthorized (OK)")

    # --- 3. ログイン & トークン取得 ---
    logger.info("🔹 ステップ2: ログイン")
    auth_res = client.post('/api/auth/login', json={
        "email": "admin@test.com",
        "password": "password123"
    })
    assert auth_res.status_code == 200
    token = auth_res.json['access_token']
    headers = {'Authorization': f'Bearer {token}'}
    logger.debug("   -> Token取得成功")

    # --- 4. 利用者一覧取得 ---
    logger.info("🔹 ステップ3: 利用者一覧取得")
    res_list = client.get('/api/users/', headers=headers)
    assert res_list.status_code == 200
    data_list = res_list.json
    assert len(data_list) == 1
    assert data_list[0]['display_name'] == "TestUserA"
    # 一覧にはPIIが含まれていないことを確認（キーがないか、None）
    assert 'pii' not in data_list[0] or data_list[0].get('pii') is None
    logger.debug("   -> 一覧取得成功 (PIIなし)")

    # --- 5. 利用者詳細取得 (自動復号の確認) ---
    logger.info("🔹 ステップ4: 詳細取得と復号化確認")
    res_detail = client.get(f'/api/users/{user_id}', headers=headers)
    assert res_detail.status_code == 200
    data_detail = res_detail.json
    
    # PIIが含まれているか
    assert 'pii' in data_detail
    pii = data_detail['pii']
    
    # ★ 暗号化されていたデータが、平文に戻っているか確認
    assert pii['certificate_number'] == "1234567890" # 階層1 (エンベロープ)
    assert pii['last_name'] == "Tanaka" # 階層2 (共通鍵)
    
    logger.info("✅ 利用者APIの検証完了: 暗号化データは正しく復号されました")