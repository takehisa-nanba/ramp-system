# backend/app/services/comms_service.py

from backend.app.extensions import db
from backend.app.models import (
    User, Supporter, SupportThread, ChatMessage,
    DocumentConsentLog, Organization, UserOrganizationLink
)
from sqlalchemy import func
from datetime import datetime, timezone
from typing import Optional 
import secrets
import string

class CommsService:
    """
    コミュニケーションチャネル（チャット）および外部連携（OTL）を処理します。
    シームレスなコミュニケーション（原理5）と監査証跡（原理1）を優先します。
    """

    # ====================================================================
    # 1. チャット機能 (Principle 5: Seamless Communication)
    # ====================================================================

    def get_or_create_thread(self, user_id: int) -> SupportThread:
        """
        Gets the active chat thread for a user, or creates one if it doesn't exist.
        """
        thread = SupportThread.query.filter_by(user_id=user_id, status='OPEN').first()
        
        if not thread:
            thread = SupportThread(user_id=user_id, status='OPEN')
            db.session.add(thread)
            db.session.commit()
            
        return thread

    def post_message(self, thread_id: int, content: str, sender_type: str, sender_id: int) -> ChatMessage:
        """
        Posts a message to a thread.
        """
        if not content:
            raise ValueError("Message content cannot be empty.")

        message = ChatMessage(
            thread_id=thread_id,
            content=content,
            # ★ 修正: Timezone Aware
            timestamp=datetime.now(timezone.utc)
        )
        
        if sender_type == 'USER':
            message.sender_user_id = sender_id
        elif sender_type == 'SUPPORTER':
            message.sender_supporter_id = sender_id
        else:
            raise ValueError("Invalid sender type.")
            
        db.session.add(message)
        db.session.commit()
        
        return message
    
    def get_thread_id_by_user(self, user_id: int) -> Optional[int]:
        """
        利用者のアクティブなチャットスレッドのIDを返す。
        （スレッドへのリンク用）
        """
        thread = SupportThread.query.filter_by(user_id=user_id, status='OPEN').first()
        
        if thread:
            return thread.id
        else:
            # スレッドが存在しない場合、自動作成するロジックを呼ぶことも可能だが、
            # ここでは参照に特化し、Noneを返す
            return None 

    def get_message_by_id(self, message_id: int) -> Optional[ChatMessage]:
        """
        特定のメッセージを取得する（監査ログからメッセージ詳細へ飛ぶことを想定）。
        """
        return db.session.get(ChatMessage, message_id)

    # ====================================================================
    # 2. ワンタイムURL (OTL) 発行 (Principle 1: Auditability)
    # ====================================================================

    def generate_otl_token(self, document_type: str, document_id: int, user_id: int, expiration_minutes: int = 1440) -> str:
        """
        Generates a secure One-Time Link (OTL) token for external consent.
        """
        # 1. Generate a secure random token
        alphabet = string.ascii_letters + string.digits
        token = ''.join(secrets.choice(alphabet) for i in range(32))
        
        # 2. 本来はRedis等に保存するが、ここでは簡易的にトークン生成のみを行う
        # (実運用では有効期限管理が必要)
        
        return token

    def verify_otl_token(self, token: str) -> dict:
        """
        Verifies the OTL token.
        """
        return {} # Placeholder