from ...extensions import db
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, DateTime, Text, Numeric, func, JSON

# ====================================================================
# 1. Corporation (法人情報)
# ====================================================================
class Corporation(db.Model):
    """法人情報（法人格、契約主体）"""
    __tablename__ = 'corporations'
    
    id = Column(Integer, primary_key=True)
    corporation_name = Column(String(150), nullable=False)
    corporation_type = Column(String(50), nullable=False) # 例: NPO法人, 株式会社
    representative_name = Column(String(100), nullable=True)
    corporation_number = Column(String(20), unique=True, nullable=True)
    establishment_date = Column(Date) # 法人の設立年月日 (原理1)
    postal_code = Column(String(10), nullable=True)
    address = Column(String(255), nullable=True)
    phone_number = Column(String(20), nullable=True)
    corporation_seal_image_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # OfficeSettingからの逆参照
    office_settings = relationship('OfficeSetting', back_populates='corporation', lazy='dynamic')

# ====================================================================
# 2. OfficeSetting (事業所基本情報 / 常勤換算の分母)
# ====================================================================
class OfficeSetting(db.Model):
    """
    事業所情報（親/箱）。
    常勤換算の基準(分母)と、事業所全体の証憑(BCP)を管理する。
    """
    __tablename__ = 'office_settings'
    
    id = Column(Integer, primary_key=True) # 内部識別用の唯一のID
    corporation_id = Column(Integer, ForeignKey('corporations.id'), nullable=False, index=True)
    office_name = Column(String(100), nullable=False)
    
    # masters/master_definitions.py を参照
    municipality_id = Column(Integer, ForeignKey('municipality_master.id'), nullable=False, index=True) 
    
    is_active = Column(Boolean, default=True, nullable=False)
    office_seal_image_url = Column(String(500), nullable=True)
    
    # --- ★ 常勤換算の基準とBCP（法令遵守） ★ ---
    full_time_weekly_minutes = Column(Integer, nullable=False, default=2400) # 常勤職員の週所定労働時間（分）
    local_rules_config = Column(JSON, nullable=True) # その他ローカルルール設定
    
    # BCP計画（事業所全体に関わる証憑）
    bcp_document_url = Column(String(500)) 
    
    # --- リレーションシップ ---
    corporation = relationship('Corporation', back_populates='office_settings')
    municipality_area = relationship('MunicipalityMaster', back_populates='offices_located_here')
    
    # 子テーブル（サービス構成）
    service_configs = relationship('OfficeServiceConfiguration', back_populates='office', lazy='dynamic', cascade="all, delete-orphan")
    
    # 監査ログ（コンプライアンスパッケージ）
    job_filings = relationship('JobFilingRecord', back_populates='office', lazy='dynamic', cascade="all, delete-orphan")
    committee_logs = relationship('CommitteeActivityLog', back_populates='office', lazy='dynamic')
    training_events = relationship('OfficeTrainingEvent', back_populates='office', lazy='dynamic')

# ====================================================================
# 3. OfficeServiceConfiguration (サービス構成 / 請求単位 / 管理者の責務)
# ====================================================================
class OfficeServiceConfiguration(db.Model):
    """
    事業所が提供するサービス種別の設定（子/中身）。
    「請求単位」であり、「管理者」と「加算」の責務を持つ（原理1, 3）。
    """
    __tablename__ = 'office_service_configurations'
    
    id = Column(Integer, primary_key=True)
    office_id = Column(Integer, ForeignKey('office_settings.id'), nullable=False, index=True)
    
    # masters/master_definitions.py を参照
    service_type_master_id = Column(Integer, ForeignKey('service_type_master.id'), nullable=False)
    
    # サービスごとの管理責任者（サビ管など） (core/supporter.py を参照)
    manager_supporter_id = Column(Integer, ForeignKey('supporters.id'), index=True) 
    
    # --- 法令・行政関連情報 ---
    jigyosho_bango = Column(String(20), nullable=False, unique=True) # 行政発行の10桁事業所番号（請求キー）
    capacity = Column(Integer, nullable=False) # 定員
    
    initial_designation_date = Column(Date) # 初回指定年月日 (原理1)
    
    # 運営規定 (サービスに紐づく証憑)
    operational_regulations_url = Column(String(500)) 
    
    # --- リレーションシップ ---
    office = relationship('OfficeSetting', back_populates='service_configs')
    manager_supporter = relationship('Supporter', foreign_keys=[manager_supporter_id], back_populates='managed_services')
    
    # financeパッケージからの逆参照
    additive_filings = relationship('OfficeAdditiveFiling', back_populates='service_config', lazy='dynamic', cascade="all, delete-orphan")
    fee_decisions = relationship('FeeCalculationDecision', back_populates='service_config', lazy='dynamic', cascade="all, delete-orphan")