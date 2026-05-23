# backend/app/models/core/supporter_form_draft.py

from backend.app.extensions import db
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint, func

class SupporterFormDraft(db.Model):
    """
    サポーターが入力中のフォームデータを一時保存（下書き）するテーブル。
    個人特定可能情報(PII)が含まれるため、データはAES-256（システム共通鍵）で高度に暗号化されて保存される。
    """
    __tablename__ = 'supporter_form_drafts'
    
    id = Column(Integer, primary_key=True)
    supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=False, index=True)
    draft_key = Column(String(100), nullable=False, index=True) # 例: 'register_user', 'edit_user_1'
    
    # 暗号化されたJSON文字列データ
    encrypted_data = Column(Text, nullable=False)
    
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 1人のサポーターに対して、1つのフォームキーにつき1下書きレコードのみ許容
    __table_args__ = (
        UniqueConstraint('supporter_id', 'draft_key', name='uq_supporter_form_draft'),
    )

    # リレーション
    supporter = db.relationship('Supporter')

    @property
    def data(self):
        """暗号化されたJSONデータを復号して辞書型で読み出す"""
        if not self.encrypted_data:
            return {}
        from backend.app.services.core_service import get_system_pii_key
        from backend.app.services.security_service import decrypt_data_pii
        import json
        
        key = get_system_pii_key()
        decrypted_str = decrypt_data_pii(self.encrypted_data, key)
        return json.loads(decrypted_str) if decrypted_str else {}

    @data.setter
    def data(self, value):
        """辞書データをJSON化し、暗号化して保存する"""
        from backend.app.services.core_service import get_system_pii_key
        from backend.app.services.security_service import encrypt_data_pii
        import json
        
        if value:
            key = get_system_pii_key()
            json_str = json.dumps(value)
            self.encrypted_data = encrypt_data_pii(json_str, key)
        else:
            self.encrypted_data = None

    def __repr__(self):
        return f'<SupporterFormDraft {self.id}: Supporter {self.supporter_id} - Key {self.draft_key}>'
