# backend/app/models/comms/shared_note.py (新規作成)

from backend.app.extensions import db
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text, func

class SharedNote(db.Model):
    """
    共同編集ノートのメタデータ。事業所内スタッフは全員閲覧・編集可能（共同掲示板ポリシー）。
    特定の業務エンティティに紐づく動的なコンテンツを管理する。
    """
    __tablename__ = 'shared_notes'
    
    id = Column(Integer, primary_key=True)
    office_id = Column(Integer, ForeignKey('office_settings.id'), nullable=False, index=True)
    
    # ノートの種別 (例: 'CASE_CONFERENCE_DRAFT', 'SUPPORT_PLAN_DRAFT', 'STAFF_REFLECTION')
    note_type = Column(String(50), nullable=False)
    
    # 連携先の業務エンティティ（例: SupportPlan.id, CaseConferenceLog.id）
    linked_entity_type = Column(String(50), nullable=True)
    linked_entity_id = Column(Integer, nullable=True, index=True)
    
    # 最終確定（Lock & Copy）されたか？
    is_archived = Column(Boolean, default=False, nullable=False) 
    
    # リレーションシップ
    versions = db.relationship('NoteVersion', back_populates='note', cascade="all, delete-orphan", lazy='dynamic')
    
    def __repr__(self):
        return f'<SharedNote {self.id} | Type: {self.note_type}>'

class NoteVersion(db.Model):
    """
    共同編集ノートのコンテンツと変更履歴。
    """
    __tablename__ = 'note_versions'
    
    id = Column(Integer, primary_key=True)
    note_id = Column(Integer, ForeignKey('shared_notes.id'), nullable=False, index=True)
    
    # Markdownコンテンツの格納
    content_snapshot = Column(Text, nullable=False) 
    
    supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=False) # 編集者
    created_at = Column(DateTime, default=func.now()) # 変更日時
    
    # 共同編集の衝突を避けるためのバージョン番号
    version_number = Column(Integer, nullable=False)

    # リレーションシップ
    note = db.relationship('SharedNote', back_populates='versions')
    supporter = db.relationship('Supporter')
    
    __table_args__ = (
        # 同じノートIDで同じバージョン番号の重複を避ける（整合性の担保）
        UniqueConstraint('note_id', 'version_number', name='uq_note_version_number'),
    )