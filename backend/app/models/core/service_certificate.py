# backend/app/models/core/service_certificate.py

# 修正点: 'from backend.app.extensions' (絶対参照)
from backend.app.extensions import db
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, DateTime, Text, Numeric, func

# ====================================================================
# 1. ServiceCertificate (受給者証の基本情報 - 親)
# ====================================================================
class ServiceCertificate(db.Model):
    """
    受給者証の基本情報（親）。
    利用者(User)と1対多。責務は「交付日」と「発行自治体（＝請求先）」の管理。
    変動する決定事項はすべて子テーブルに分離する。
    """
    __tablename__ = 'service_certificates'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # 管理責任を持つ事業所サービスへの紐づけ
    office_service_configuration_id = Column(Integer, ForeignKey('office_service_configurations.id'), nullable=False, index=True)

    # --- 受給者証の基本情報 (1ページ目) ---
    certificate_issue_date = Column(Date, nullable=False) # 交付年月日
    
    # masters/master_definitions.py を参照
    municipality_master_id = Column(Integer, ForeignKey('municipality_master.id'), nullable=False, index=True)
    
    certificate_type = Column(String(50)) # 証の種別
    disability_support_classification = Column(String(20)) # 障害支援区分
    recipient_number = Column(String(10), nullable=True) # 受給者証番号 (10桁, PII保護対象)
    certificate_notes = Column(Text) # 特記事項・予備欄など

    # --- 承認ワークフロー / 二重チェック (原理1, 2) ---
    status = Column(String(30), nullable=False, default='DRAFT')
    created_by_supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=True)
    submitted_by_supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=True)
    reviewed_by_supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_reason = Column(Text, nullable=True)
    
    # --- 誤登録無効化 ---
    voided_by_supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=True)
    voided_at = Column(DateTime, nullable=True)
    void_reason = Column(Text, nullable=True)

    # --- タイムスタンプ ---
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # --- リレーションシップ ---
    user = db.relationship('User', back_populates='certificates')
    issuance_municipality = db.relationship('MunicipalityMaster', back_populates='certificates')
    managing_service = db.relationship('OfficeServiceConfiguration') 
    
    # 子テーブル (期間管理が独立しているもの)
    granted_services = db.relationship('GrantedService', back_populates='certificate', lazy='dynamic', cascade="all, delete-orphan")
    copayment_limits = db.relationship('CopaymentLimit', back_populates='certificate', lazy='dynamic', cascade="all, delete-orphan")
    meal_addon_statuses = db.relationship('MealAddonStatus', back_populates='certificate', lazy='dynamic', cascade="all, delete-orphan")
    copayment_management = db.relationship('CopaymentManagement', back_populates='certificate', lazy='dynamic', cascade="all, delete-orphan")
    
    #  削除: 送迎加算と特別地域加算は、受給者証記載事項ではないためここからは削除。
    # Financeパッケージの ComplianceEventLog で管理する。

# ====================================================================
# 2. GrantedService (支給決定サービス / 暫定期間)
# ====================================================================
class GrantedService(db.Model):
    __tablename__ = 'granted_services'
    id = Column(Integer, primary_key=True)
    certificate_id = Column(Integer, ForeignKey('service_certificates.id'), nullable=False, index=True)
    
    granted_start_date = Column(Date, nullable=False)
    granted_end_date = Column(Date, nullable=False) 
    granted_amount_description = Column(String(100)) 
    
    is_tentative = Column(Boolean, default=False, nullable=False)
    tentative_start_date = Column(Date)
    tentative_end_date = Column(Date)
    
    # 支給決定日数 (支給量、例: 23日)
    max_service_days = Column(Integer, nullable=True, default=23)
    max_service_days_type = Column(String(30), default='FIXED', nullable=False) # 支給量の種別: 'FIXED' or 'DYNAMIC_MONTH_MINUS_8'
    granted_amount_start_date = Column(Date, nullable=True) # 支給量の有効期間 開始
    granted_amount_end_date = Column(Date, nullable=True) # 支給量の有効期間 終了
    
    service_type_master_id = Column(Integer, ForeignKey('service_type_master.id'), nullable=False)
    
    certificate = db.relationship('ServiceCertificate', back_populates='granted_services')
    service_type = db.relationship('ServiceTypeMaster', back_populates='granted_services')
    
    contract_detail = db.relationship('ContractReportDetail', back_populates='granted_service', uselist=False, cascade="all, delete-orphan")


# ====================================================================
# 3. CopaymentLimit (利用者負担上限額 / 期間)
# ====================================================================
class CopaymentLimit(db.Model):
    __tablename__ = 'copayment_limits'
    id = Column(Integer, primary_key=True)
    certificate_id = Column(Integer, ForeignKey('service_certificates.id'), nullable=False, index=True)
    
    limit_start_date = Column(Date, nullable=False)
    limit_end_date = Column(Date, nullable=False) 
    limit_amount = Column(Numeric(precision=10, scale=2), nullable=False, default=0) 
    is_management_required = Column(Boolean, default=False, nullable=False) # 0円以外の場合の上限管理有無

    certificate = db.relationship('ServiceCertificate', back_populates='copayment_limits')


# ====================================================================
# 4. MealAddonStatus (食事提供加算 / 期間)
# ====================================================================
class MealAddonStatus(db.Model):
    __tablename__ = 'meal_addon_statuses'
    id = Column(Integer, primary_key=True)
    certificate_id = Column(Integer, ForeignKey('service_certificates.id'), nullable=False, index=True)

    meal_addon_start_date = Column(Date, nullable=False)
    meal_addon_end_date = Column(Date, nullable=False) 
    is_applicable = Column(Boolean, nullable=False) 

    certificate = db.relationship('ServiceCertificate', back_populates='meal_addon_statuses')


# ====================================================================
# 5. CopaymentManagement (利用者負担上限管理)
# ====================================================================
class CopaymentManagement(db.Model):
    """利用者負担上限管理事業所の履歴と適用期間"""
    __tablename__ = 'copayment_management'
    
    id = Column(Integer, primary_key=True)
    certificate_id = Column(Integer, ForeignKey('service_certificates.id'), nullable=False, index=True)

    management_start_date = Column(Date, nullable=False)
    management_end_date = Column(Date, nullable=False) 
    
    # '該当' (True) / '非該当' (False)
    is_applicable = Column(Boolean, nullable=False) 
    
    # ★ 追加: 管理事業所番号（請求に必須）
    managing_office_number = Column(String(10))
    
    # 他事業所が管理する場合の事業所名
    managing_office_name = Column(String(255))
    
    certificate = db.relationship('ServiceCertificate', back_populates='copayment_management')