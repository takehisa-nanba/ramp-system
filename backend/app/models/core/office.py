# 🚨 修正点: 'from app...' を 'backend.app...' に修正
from backend.app.extensions import db
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, DateTime, Text, Numeric, func, JSON

# 🚨 修正点: マスタへの参照を追加
# (JobFilingRecordでJobTitleMasterを使うため)
from backend.app.models.masters.master_definitions import JobTitleMaster

# ====================================================================
# 1. Corporation (法人情報)
# ====================================================================
class Corporation(db.Model):
    """法人情報（法人格、契約主体）"""
    __tablename__ = 'corporations'
    
    id = Column(Integer, primary_key=True)
    corporation_name = Column(String(150), nullable=False)
    corporation_type = Column(String(50), nullable=False)
    representative_name = Column(String(100), nullable=True)
    corporation_number = Column(String(20), unique=True, nullable=True)
    establishment_date = Column(Date)
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
    
    id = Column(Integer, primary_key=True)
    corporation_id = Column(Integer, ForeignKey('corporations.id'), nullable=False, index=True)
    office_name = Column(String(100), nullable=False)
    
    municipality_id = Column(Integer, ForeignKey('municipality_master.id'), nullable=False, index=True) 
    
    is_active = Column(Boolean, default=True, nullable=False)
    office_seal_image_url = Column(String(500), nullable=True)
    
    # --- 常勤換算の基準 ---
    full_time_weekly_minutes = Column(Integer, nullable=False, default=2400)
    local_rules_config = Column(JSON, nullable=True)
    
    # BCP計画
    bcp_document_url = Column(String(500)) 
    
    # --- リレーションシップ ---
    corporation = relationship('Corporation', back_populates='office_settings')
    municipality_area = relationship('MunicipalityMaster', back_populates='offices_located_here')
    
    # 子テーブル
    service_configs = relationship('OfficeServiceConfiguration', back_populates='office', lazy='dynamic', cascade="all, delete-orphan")
    
    # ★ 復旧: 監査ログへのリレーション
    job_filings = relationship('JobFilingRecord', back_populates='office', lazy='dynamic', cascade="all, delete-orphan")
    committee_logs = relationship('CommitteeActivityLog', back_populates='office', lazy='dynamic')
    training_events = relationship('OfficeTrainingEvent', back_populates='office', lazy='dynamic')
    
    # Supporterからの逆参照 (owned_offices)
    owner_supporter = relationship('Supporter', 
        primaryjoin="OfficeSetting.id==Supporter.office_id", # 仮定義（本来は中間テーブルかFKが必要だが今回は省略）
        viewonly=True
    )
    # ※ owner_supporterのリレーション定義は supporter.py 側の定義に依存するため、
    #    循環参照を避けるためにここでは簡易的な定義または省略が望ましいですが、
    #    エラー回避のため一旦コメントアウト推奨です。
    # owner_supporter = ... 

# ====================================================================
# 3. OfficeServiceConfiguration (サービス構成 / 請求単位)
# ====================================================================
class OfficeServiceConfiguration(db.Model):
    """
    事業所が提供するサービス種別の設定（子/中身）。
    「請求単位」であり、「管理者」と「加算」の責務を持つ。
    """
    __tablename__ = 'office_service_configurations'
    
    id = Column(Integer, primary_key=True)
    office_id = Column(Integer, ForeignKey('office_settings.id'), nullable=False, index=True)
    service_type_master_id = Column(Integer, ForeignKey('service_type_master.id'), nullable=False)
    
    manager_supporter_id = Column(Integer, ForeignKey('supporters.id'), index=True) 
    
    jigyosho_bango = Column(String(20), nullable=False, unique=True)
    capacity = Column(Integer, nullable=False)
    
    initial_designation_date = Column(Date)
    operational_regulations_url = Column(String(500)) 
    
    # --- リレーションシップ ---
    office = relationship('OfficeSetting', back_populates='service_configs')
    manager_supporter = relationship('Supporter', foreign_keys=[manager_supporter_id])
    
    # ★ 復旧: 加算届出へのリレーション
    additive_filings = relationship('OfficeAdditiveFiling', back_populates='service_config', lazy='dynamic', cascade="all, delete-orphan")
    
    # fee_decisions = relationship('FeeCalculationDecision', ...) # financeパッケージ

# ====================================================================
# 4. OfficeAdditiveFiling (加算届出状況) - ★ 復旧 ★
# ====================================================================
class OfficeAdditiveFiling(db.Model):
    """
    事業所の加算届出状況の履歴。
    サービス構成(OfficeServiceConfiguration)に紐づく（原理3）。
    """
    __tablename__ = 'office_additive_filings'
    
    id = Column(Integer, primary_key=True)
    
    # 親: サービス構成（事業所番号）に紐づく
    office_service_configuration_id = Column(Integer, ForeignKey('office_service_configurations.id'), nullable=False, index=True)
    
    # 加算の種類（本来はマスタだが、今回は文字列で定義し柔軟性を持たせる）
    # または別途 GovernmentFeeMaster を作成して紐づける
    additive_name = Column(String(100), nullable=False) 
    
    is_filed = Column(Boolean, default=False, nullable=False)
    filing_date = Column(Date)
    effective_start_date = Column(Date)
    
    service_config = relationship('OfficeServiceConfiguration', back_populates='additive_filings')

# ====================================================================
# 5. JobFilingRecord (職務の行政届出履歴の証拠) - ★ 復旧 ★
# ====================================================================
class JobFilingRecord(db.Model):
    """
    職務の行政届出履歴の証拠（配置届出の監査用）。
    事業所(OfficeSetting)全体の配置として届け出る（原理1）。
    """
    __tablename__ = 'job_filing_records'
    
    id = Column(Integer, primary_key=True)
    
    # 親: 事業所全体に紐づく
    office_id = Column(Integer, ForeignKey('office_settings.id'), nullable=False, index=True) 
    
    # どの職務か
    job_title_id = Column(Integer, ForeignKey('job_title_master.id'), nullable=False) 
    
    effective_date = Column(Date, nullable=False) # 届出が有効になる日付
    document_url = Column(String(500), nullable=True) # 届出書類の証憑URL
    
    # リレーションシップ
    office = relationship('OfficeSetting', back_populates='job_filings')
    job_title = relationship('JobTitleMaster', back_populates='filing_history')