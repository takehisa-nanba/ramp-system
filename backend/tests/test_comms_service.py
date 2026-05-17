import pytest
import logging
# ★ 修正: date をインポート
from datetime import date
from backend.app import db
from backend.app.models import User, Supporter, StatusMaster
from backend.app.services.comms_service import CommsService

# ロガーの取得
logger = logging.getLogger(__name__)

def test_chat_functionality(app):
    """
    チャット機能のテスト。
    スレッドの自動生成とメッセージの送信・記録を確認する。
    """
    logger.info("🚀 TEST START: コミュニケーション機能の検証を開始します")

    with app.app_context():
        # --- 1. 準備 ---
        status = db.session.query(StatusMaster).filter_by(name="利用中").first()
        if not status:
            status = StatusMaster(name="利用中")
            db.session.add(status)
            db.session.flush()

        user = User(display_name="ChatUser", status_id=status.id)
        
        # ★ 修正: hire_date を文字列から date オブジェクトに変更
        supporter = Supporter(
            staff_code="S_COMMS",
            last_name="Staff", first_name="One", last_name_kana="スタッフ", first_name_kana="イチ",
            employment_type="FULL_TIME", weekly_scheduled_minutes=2400, 
            hire_date=date(2025, 1, 1) 
        )
        db.session.add_all([user, supporter])
        db.session.commit()

        service = CommsService()

        # --- 2. スレッド取得 (新規作成) ---
        logger.info("🔹 ステップ1: スレッド取得")
        thread = service.get_or_create_thread(user.id)
        assert thread is not None
        assert thread.user_id == user.id
        logger.debug(f"   -> Thread ID: {thread.id} Created")

        # --- 3. メッセージ送信 (利用者) ---
        logger.info("🔹 ステップ2: 利用者からのメッセージ")
        msg1 = service.post_message(thread.id, "こんにちは、相談があります。", "USER", user.id)
        assert msg1.content == "こんにちは、相談があります。"
        assert msg1.sender_user_id == user.id
        
        # --- 4. メッセージ送信 (職員) ---
        logger.info("🔹 ステップ3: 職員からの返信")
        msg2 = service.post_message(thread.id, "はい、どうされましたか？", "SUPPORTER", supporter.id)
        assert msg2.content == "はい、どうされましたか？"
        assert msg2.sender_supporter_id == supporter.id
        
        logger.info("✅ チャット機能の検証完了")