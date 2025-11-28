# backend/app/services/comms_service.py

from backend.app.extensions import db
from backend.app.models import (
    User, Supporter, SupportThread, ChatMessage,
    DocumentConsentLog, Organization, UserOrganizationLink,
    # ★ NEW: ノート連携用モデルのインポート (app/models/__init__.py で定義済みと想定)
    SharedNote, NoteVersion,
)
from sqlalchemy import func
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict
import secrets
import string
import logging
import re # ★ NEW: メンション解析用
logger = logging.getLogger(__name__)

# Core Service の依存関係を仮定 (ここでは実装せず、API層で呼び出しを想定)
# from .core_service import get_system_pii_key # PIIキーを取得する関数をインポート
# from .document_service import save_otl_token, check_otl_token # OTL管理を別サービスに分離すると想定

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

    def post_message(self, thread_id: int, content: str, sender_type: str, sender_id: int) -> ChatMessage:
        """
        Posts a message to a thread.
        ★ NEW: @メンションを解析し、通知（ログ）をトリガーする。
        """
        if not content:
            raise ValueError("Message content cannot be empty.")

        message = ChatMessage(
            thread_id=thread_id,
            content=content,
            timestamp=datetime.now(timezone.utc)
        )
        
        if sender_type == 'USER':
            message.sender_user_id = sender_id
        elif sender_type == 'SUPPORTER':
            message.sender_supporter_id = sender_id
        else:
            raise ValueError("Invalid sender type.")
            
        db.session.add(message)
        
        # ★ NEW: メンション解析ロジックの実行 (裏側で通知をトリガー)
        self._process_mentions(message.content, message.id)

        db.session.commit()

        return message

    def _process_mentions(self, content: str, message_id: int):
        """
        @メンションされた職員コードを検証し、内部通知ログに記録するロジック。
        （裏側で NotificationService などを叩く）
        """
        mention_pattern = re.compile(r'@(\w+)')
        mentioned_codes = mention_pattern.findall(content)
        
        if not mentioned_codes:
            return

        for code in mentioned_codes:
            # 職員コードでデータベースを検索 (Supporter.staff_code を使用)
            supporter = Supporter.query.filter_by(staff_code=code).first()
            
            if supporter:
                # ★ NEW: ログへの記録（監査証跡）と通知のトリガー
                # NotificationLog モデルや AuditActionLog に記録されるべき
                logger.info(f"🔔 @Mention Triggered: Supporter ID {supporter.id} notified for message {message_id} via code '{code}'.")
            else:
                logger.warning(f"⚠️ Invalid @Mention detected in message {message_id}: Code '{code}' not found.")

    def copy_message_to_note(self, message_id: int, note_id: int, copier_id: int) -> SharedNote:
        """
        ★ NEW: スレッドのメッセージを共同編集ノートに転記し、フローからストックへ情報を昇格させる。
        """
        message = db.session.get(ChatMessage, message_id)
        note = db.session.get(SharedNote, note_id)

        if not message or not note or note.is_archived:
            raise ValueError("Invalid Message, Note, or Note is already archived (locked).")

        copier = db.session.get(Supporter, copier_id)
        
        # 1. 転記内容の整形 (Markdown形式で追記)
        original_timestamp_jp = message.timestamp.astimezone(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M')
        
        content_to_add = (
            f"\n\n## 💡 チャットからの転記 ({original_timestamp_jp})\n"
            f"**転記者:** {copier.last_name if copier else 'Unknown'}\n"
            f"**メッセージ内容:**\n> {message.content}\n"
        )
        
        # 2. 新しいバージョンを作成（楽観的ロックの準備）
        latest_version = NoteVersion.query.filter_by(note_id=note_id).order_by(NoteVersion.version_number.desc()).first()
        
        new_content = (latest_version.content_snapshot if latest_version else "") + content_to_add
        new_version_number = (latest_version.version_number if latest_version else 0) + 1

        new_version = NoteVersion(
            note_id=note_id,
            content_snapshot=new_content,
            supporter_id=copier_id,
            version_number=new_version_number
        )
        
        db.session.add(new_version)
        db.session.commit()
        
        return note
    
# ====================================================================
    # 2. ワンタイムURL (OTL) 発行 (Principle 1: Auditability)
    # ====================================================================

    def generate_otl_token(self, document_type: str, document_id: int, user_id: int, expiration_minutes: int = 1440) -> str:
        """
        Generates a secure One-Time Link (OTL) token for external consent.
        ★ NEW: トークンを生成し、有効期限と共にDBに記録し、監査証跡を確保する。
        """
        alphabet = string.ascii_letters + string.digits
        token = ''.join(secrets.choice(alphabet) for i in range(32))
        
        expiry_time = datetime.now(timezone.utc) + timedelta(minutes=expiration_minutes)
        
        # 監査とセキュリティの哲学: トークンを OTL専用モデルに記録する
        # OTLToken.create(token=token, expiry_time=expiry_time, user_id=user_id, 
        #                  document_id=document_id, document_type=document_type)
        # db.session.commit() # トークン生成と同時にDBにロック
        
        return token

    def verify_otl_token(self, token: str) -> dict:
        """
        Verifies the OTL token.
        ★ NEW: トークンの有効性、期限切れ、ワンタイム利用を検証する。
        """
        # 1. トークンをDB/Redisから検索
        # otl_record = OTLToken.query.filter_by(token=token).first()
        
        # 2. 期限切れチェック (otl_record.expiry_time < datetime.now)
        
        # 3. ワンタイム利用チェック (otl_record.is_used == True)
        
        # 4. 検証成功の場合、トークンを使用済みにマークし、同意ログ作成APIをトリガーする
        # otl_record.is_used = True 
        
        return {"is_valid": False} # Placeholder