# backend/tests/test_draft_api.py

import pytest
import logging
from datetime import date
from backend.app import db
from backend.app.models import Supporter, SupporterFormDraft
from flask_jwt_extended import create_access_token

logger = logging.getLogger(__name__)

def test_supporter_form_draft_model(app):
    """
    SupporterFormDraftモデルの暗号化・復号化のテスト。
    """
    logger.info("🚀 TEST START: SupporterFormDraftモデルの検証")
    
    with app.app_context():
        # テスト用のサポーターを作成
        supporter = Supporter(
            staff_code="S_DRAFT_TEST",
            last_name="下書き",
            first_name="太郎",
            last_name_kana="したがき",
            first_name_kana="たろう",
            employment_type="FULL_TIME",
            weekly_scheduled_minutes=2400,
            hire_date=date(2025, 1, 1)
        )
        db.session.add(supporter)
        db.session.commit()
        
        # ドラフトデータの定義
        draft_key = "register_user_test"
        dummy_data = {
            "display_name": "テスト山田",
            "pii": {
                "last_name": "山田",
                "first_name": "太郎",
                "address": "東京都千代田区"
            },
            "emergency_contacts": [
                {"name": "山田花子", "phone_number": "090-1111-2222", "relation": "母"}
            ]
        }
        
        # 1. ドラフトレコードの作成と暗号化確認
        draft = SupporterFormDraft(
            supporter_id=supporter.id,
            draft_key=draft_key
        )
        db.session.add(draft)
        
        # セッター経由でデータを設定
        draft.data = dummy_data
        db.session.commit()
        
        # 暗号化されて平文では保存されていないことを確認
        assert draft.encrypted_data is not None
        assert "テスト山田" not in draft.encrypted_data
        
        # 2. データベースから再ロードして復号を確認
        db.session.expire_all()
        loaded_draft = SupporterFormDraft.query.filter_by(
            supporter_id=supporter.id,
            draft_key=draft_key
        ).first()
        
        assert loaded_draft is not None
        assert loaded_draft.data == dummy_data
        assert loaded_draft.data["pii"]["last_name"] == "山田"
        
        # クリーンアップ
        db.session.delete(loaded_draft)
        db.session.delete(supporter)
        db.session.commit()
        
        logger.info("✅ SupporterFormDraftモデルの検証完了")


def test_supporter_form_draft_api(app, client):
    """
    サポーターフォーム下書きAPI（保存、ロード、削除）の結合テスト。
    """
    logger.info("🚀 TEST START: 下書きAPIの検証")
    
    with app.app_context():
        # テスト用のサポーターを作成
        supporter = Supporter(
            staff_code="S_DRAFT_API",
            last_name="下書き",
            first_name="API",
            last_name_kana="したがき",
            first_name_kana="えーぴーあい",
            employment_type="FULL_TIME",
            weekly_scheduled_minutes=2400,
            hire_date=date(2025, 1, 1)
        )
        db.session.add(supporter)
        db.session.commit()
        
        # JWT認証トークンの生成
        token = create_access_token(identity=f"staff:{supporter.id}", additional_claims={
            "role_name": "STAFF",
            "full_name": "下書き API",
            "role_scopes": ["VIEW_PII"]
        })
        headers = {'Authorization': f'Bearer {token}'}
        
        draft_key = "register_user_api_test"
        dummy_data = {
            "display_name": "テスト鈴木",
            "pii": {
                "last_name": "鈴木",
                "first_name": "一郎",
                "phone_number": "080-9999-8888"
            }
        }
        
        # 1. 保存APIのテスト (POST /api/users/drafts)
        post_response = client.post(
            '/api/users/drafts',
            json={
                "draft_key": draft_key,
                "data": dummy_data
            },
            headers=headers
        )
        assert post_response.status_code == 200
        assert post_response.json["msg"] == "Draft auto-saved successfully"
        
        # DBに保存されていることを確認
        db_draft = SupporterFormDraft.query.filter_by(
            supporter_id=supporter.id,
            draft_key=draft_key
        ).first()
        assert db_draft is not None
        assert db_draft.data == dummy_data
        
        # 2. 取得APIのテスト (GET /api/users/drafts/<draft_key>)
        get_response = client.get(
            f'/api/users/drafts/{draft_key}',
            headers=headers
        )
        assert get_response.status_code == 200
        assert get_response.json["data"] == dummy_data
        
        # 存在しないキーの取得テスト
        get_none_response = client.get(
            '/api/users/drafts/non_existent_key',
            headers=headers
        )
        assert get_none_response.status_code == 200
        assert get_none_response.json["data"] is None
        
        # 3. 削除APIのテスト (DELETE /api/users/drafts/<draft_key>)
        delete_response = client.delete(
            f'/api/users/drafts/{draft_key}',
            headers=headers
        )
        assert delete_response.status_code == 200
        assert delete_response.json["msg"] == "Draft cleared successfully"
        
        # DBから削除されていることを確認
        assert SupporterFormDraft.query.filter_by(
            supporter_id=supporter.id,
            draft_key=draft_key
        ).first() is None
        
        # クリーンアップ
        db.session.delete(supporter)
        db.session.commit()
        
        logger.info("✅ 下書きAPIの検証完了")
