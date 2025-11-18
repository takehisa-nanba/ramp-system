from backend.app.extensions import db
from backend.app.models import (
    User, Supporter, SupportThread, ChatMessage,
    DocumentConsentLog, Organization, UserOrganizationLink
)
from sqlalchemy import func
from datetime import datetime, timedelta
import secrets
import string

class CommsService:
    """
    Handles communication channels (Chat) and external coordination (OTL).
    Prioritizes seamless communication (Principle 5) and audit trails (Principle 1).
    """

    # ====================================================================
    # 1. チャット機能 (Principle 5: Seamless Communication)
    # ====================================================================

    def get_or_create_thread(self, user_id: int) -> SupportThread:
        """
        Gets the active chat thread for a user, or creates one if it doesn't exist.
        Ensures continuity even if the user status changes (Principle 5).
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
        Records the sender type ('USER' or 'SUPPORTER') for audit trails.
        """
        if not content:
            raise ValueError("Message content cannot be empty.")

        message = ChatMessage(
            thread_id=thread_id,
            content=content,
            timestamp=datetime.utcnow()
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

    # ====================================================================
    # 2. ワンタイムURL (OTL) 発行 (Principle 1: Auditability / Principle 4: No Waste)
    # ====================================================================

    def generate_otl_token(self, document_type: str, document_id: int, user_id: int, expiration_minutes: int = 1440) -> str:
        """
        Generates a secure One-Time Link (OTL) token for external consent.
        Instead of forcing external users to login (Waste), we verify identity via token.
        
        Args:
            document_type: 'SUPPORT_PLAN', 'AGENCY_RECEIPT', etc.
            document_id: ID of the document to be signed.
            expiration_minutes: Token validity duration (default 24h).
        """
        
        # 1. Generate a secure random token
        alphabet = string.ascii_letters + string.digits
        token = ''.join(secrets.choice(alphabet) for i in range(32))
        
        # 2. Create a log entry (Pending Consent)
        # 実際には、このトークンを一時的なストア（Redisや専用テーブル）に保存し、
        # 有効期限と紐づける必要があります。
        # ここでは、DocumentConsentLogを 'PENDING' 状態で作成する簡易実装とします。
        
        # (実装イメージ: OTL管理テーブルへの保存)
        # otl_record = OTLRecord(token=token, user_id=user_id, doc_type=..., expires_at=...)
        # db.session.add(otl_record)
        
        return token

    def verify_otl_token(self, token: str) -> dict:
        """
        Verifies the OTL token and returns the associated context (user_id, document_id).
        Returns None if invalid or expired.
        """
        # (実装イメージ: OTL管理テーブルからの検索と検証)
        # record = OTLRecord.query.filter_by(token=token).first()
        # if not record or record.expires_at < datetime.utcnow():
        #     return None
        
        # return {'user_id': record.user_id, 'document_id': record.document_id, ...}
        
        return {} # Placeholder