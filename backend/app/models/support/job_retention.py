# backend/app/models/support/job_retention.py

# 修正点: 'from backend.app.extensions' (絶対参照)
from backend.app.extensions import db
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, DateTime, Text, func, Index, CheckConstraint, text

# ====================================================================
# 1. JobRetentionContract (就労定着支援 - 契約)
# ====================================================================
class JobRetentionContract(db.Model):
    """
    就労定着支援の契約情報（親モデル）。
    就職後6ヶ月経過後の、独立した請求サービス（原理3）の土台。
    User.status_id = '定着支援中' の期間を管理する。
    """
    __tablename__ = 'job_retention_contracts'
    __table_args__ = (
        CheckConstraint("status != 'ACTIVE' OR office_service_configuration_id IS NOT NULL", name='ck_retention_active_service'),
        Index('uq_retention_active_user', 'user_id', unique=True,
              postgresql_where=text("status = 'ACTIVE' AND deleted_at IS NULL"),
              sqlite_where=text("status = 'ACTIVE' AND deleted_at IS NULL")),
    )
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    contract_start_date = Column(Date, nullable=False) # 契約開始日
    contract_end_date = Column(Date, nullable=False) # 契約終了日 (最長3年)
    
    # NULL is reserved for legacy contracts requiring explicit reconciliation.
    office_service_configuration_id = Column(Integer, ForeignKey('office_service_configurations.id'), nullable=True, index=True)
    status = Column(String(30), nullable=False, default='LEGACY_REVIEW', server_default='LEGACY_REVIEW')
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime)
    deleted_by_id = Column(Integer, ForeignKey('supporters.id'))
    delete_reason = Column(Text)
    service_configuration = db.relationship('OfficeServiceConfiguration')

    # 契約内容（支援頻度、費用など）の詳細情報
    contract_details = Column(Text)
    
    # --- リレーションシップ ---
    user = db.relationship('User', back_populates='retention_contracts')
    retention_records = db.relationship('JobRetentionRecord', back_populates='contract', lazy='dynamic')

# ====================================================================
# 2. JobRetentionRecord (就労定着支援 - 実施記録)
# ====================================================================
class JobRetentionRecord(db.Model):
    """
    互換性保持専用の旧実施記録。新規の支援事実は SupportRecord に記録する。
    請求対象となる支援の監査証跡（原理1）。
    """
    __tablename__ = 'job_retention_records'
    
    id = Column(Integer, primary_key=True)
    contract_id = Column(Integer, ForeignKey('job_retention_contracts.id'), nullable=False, index=True)
    
    record_date = Column(Date, nullable=False)
    
    # 支援方法 (例: '企業訪問', '利用者面談（対面）', '利用者面談（電話/オンライン）')
    support_method = Column(String(50), nullable=False) 
    
    support_details = Column(Text, nullable=False) # 実施した支援の詳細 (NULL禁止)
    supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=False) # 担当職員
    
    # --- 証憑（原理1） ---
    document_url = Column(String(500)) # 詳細な面談記録票や確認書などのファイルURL
    
    # --- リレーションシップ ---
    contract = db.relationship('JobRetentionContract', back_populates='retention_records')
    supporter = db.relationship('Supporter', foreign_keys=[supporter_id])