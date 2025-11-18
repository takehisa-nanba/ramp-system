from backend.app.extensions import db
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, DateTime, Text, func

# ====================================================================
# 1. JobRetentionContract (就労定着支援 - 契約)
# ====================================================================
class JobRetentionContract(db.Model):
    """
    就労定着支援の契約情報（親モデル）。
    就職後6ヶ月経過後の、独立した請求サービス（原理3）の土台。
    """
    __tablename__ = 'job_retention_contracts'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    contract_start_date = Column(Date, nullable=False) # 契約開始日
    contract_end_date = Column(Date, nullable=False) # 契約終了日 (最長3年)
    
    # 契約内容（支援頻度、費用など）の詳細情報
    contract_details = Column(Text)
    
    user = relationship('User', back_populates='retention_contracts')
    retention_records = relationship('JobRetentionRecord', back_populates='contract', lazy='dynamic', cascade="all, delete-orphan")

# ====================================================================
# 2. JobRetentionRecord (就労定着支援 - 実施記録)
# ====================================================================
class JobRetentionRecord(db.Model):
    """
    就労定着支援の実施記録（JobRetentionContractと1対多）。
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
    contract = relationship('JobRetentionContract', back_populates='retention_records')
    supporter = relationship('Supporter', foreign_keys=[supporter_id])