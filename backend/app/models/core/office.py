# backend/app/models/core/office.py
from backend.app.extensions import db
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, DateTime, Text, Numeric, func, JSON

# 🚨 修正点: マスタへの参照を追加
from backend.app.models.masters.master_definitions import JobTitleMaster, GovernmentFeeMaster

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
    
    # 所在地
    postal_code = Column(String(10), nullable=True)
    address = Column(String(255), nullable=True)
    phone_number = Column(String(20), nullable=True)
    corporation_seal_image_url = Column(String(500), nullable=True)
    
    is_active = Column(Boolean, default=True, nullable=False)
    
    # ★ NEW: 法人マスターキー(KEK)の参照ID (原理6)
    # 実際の鍵はKMSなどにあり、ここには参照IDのみを置く
    kek_reference_id = Column(String(255)) 
    
    # OfficeSettingからの逆参照
    office_settings = db.relationship('OfficeSetting', back_populates='corporation', lazy='dynamic')

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
    
    # 運営規定のバージョン（設定変更のガードレール）
    operational_regulations_version = Column(String(50)) 
    
    # ローカルルール設定（厳格/緩やかモードなど）
    local_rules_config = Column(JSON, nullable=True) 
    
    # BCP計画（事業所全体に関わる証憑）
    bcp_document_url = Column(String(500)) 
    
    # --- リレーションシップ ---
    corporation = db.relationship('Corporation', back_populates='office_settings')
    municipality_area = db.relationship('MunicipalityMaster', back_populates='offices_located_here')
    
    # 子テーブル（サービス構成）
    service_configs = db.relationship('OfficeServiceConfiguration', back_populates='office', lazy='dynamic', cascade="all, delete-orphan")
    
    # 監査ログ（コンプライアンスパッケージ）
    job_filings = db.relationship('JobFilingRecord', back_populates='office', lazy='dynamic', cascade="all, delete-orphan")
    committee_logs = db.relationship('CommitteeActivityLog', back_populates='office', lazy='dynamic')
    training_events = db.relationship('OfficeTrainingEvent', back_populates='office', lazy='dynamic')
    
    # 運営会議ログ
    operations_logs = db.relationship('OfficeOperationsLog', back_populates='office', lazy='dynamic')
    
    # Supporterからの逆参照 (owned_offices)
    staff_members = db.relationship('Supporter', back_populates='office', lazy='dynamic')


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
    office = db.relationship('OfficeSetting', back_populates='service_configs')
    manager_supporter = db.relationship('Supporter', foreign_keys=[manager_supporter_id], back_populates='managed_services')
    
    # financeパッケージからの逆参照
    additive_filings = db.relationship('OfficeAdditiveFiling', back_populates='service_config', lazy='dynamic', cascade="all, delete-orphan")
    fee_decisions = db.relationship('FeeCalculationDecision', back_populates='service_config', lazy='dynamic', cascade="all, delete-orphan")

# ====================================================================
# 4. OfficeAdditiveFiling (加算届出状況)
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
    
    # ★ 修正: 文字列ではなくマスタ(GovernmentFeeMaster)を参照
    fee_master_id = Column(Integer, ForeignKey('government_fee_master.id'), nullable=False)
    
    is_filed = Column(Boolean, default=False, nullable=False)
    filing_date = Column(Date)
    effective_start_date = Column(Date)
    effective_end_date = Column(Date)
    
    service_config = db.relationship('OfficeServiceConfiguration', back_populates='additive_filings')
    fee_master = db.relationship('GovernmentFeeMaster', back_populates='office_filings')

# ====================================================================
# 5. JobFilingRecord (職務の行政届出履歴の証拠)
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
    office = db.relationship('OfficeSetting', back_populates='job_filings')
    job_title = db.relationship('JobTitleMaster', back_populates='filing_history')

# ====================================================================
# 6. OfficeOperationsLog (事業所運営会議ログ) ★新規追加
# ====================================================================
class OfficeOperationsLog(db.Model):
    """
    事業所運営会議（職員会議、朝礼、夕礼など）。
    「現場の戦術」と「周知徹底」の証跡。
    """
    __tablename__ = 'office_operations_logs'
    
    id = Column(Integer, primary_key=True)
    office_id = Column(Integer, ForeignKey('office_settings.id'), nullable=False, index=True)
    
    # 会議種別（例: 'MORNING_ASSEMBLY', 'MONTHLY_STAFF_MEETING', 'SAFETY_SHARING'）
    meeting_type = Column(String(50), nullable=False)
    
    meeting_date = Column(DateTime, default=func.now())
    
    # --- 議論と決定 ---
    agenda_summary = Column(Text) # 議題
    shared_information = Column(Text) # 周知事項（ヒヤリハット共有など）
    decisions_made = Column(Text) # 決定事項（誰が何をするか）
    
    # --- 証憑 ---
    minutes_file_url = Column(String(500)) # 手書き議事録のスキャンなど
    
    office = db.relationship('OfficeSetting', back_populates='operations_logs')