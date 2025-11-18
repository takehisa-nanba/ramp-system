from backend.app.extensions import db
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, DateTime, Text, Numeric, func

# ====================================================================
# 1. ServiceCertificate (受給者証の基本情報 - 親)
# ====================================================================
class ServiceCertificate(db.Model):
    """
    受給者証の基本情報（親）。
    利用者(User)と1対多。責務は「交付日」と「発行自治体（請求先）」の管理。
    変動する決定事項はすべて子テーブルに分離する。
    """
    __tablename__ = 'service_certificates'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # --- 受給者証の基本情報 (1ページ目) ---
    certificate_issue_date = Column(Date, nullable=False) # 交付年月日（これが基本の適用年月日）
    
    # masters/master_definitions.py を参照
    # 「発行自治体」であり、同時に「請求先」でもある（責務の統一）
    municipality_master_id = Column(Integer, ForeignKey('municipality_master.id'), nullable=False, index=True)
    
    # fee_payer_number は municipality_master_id と重複するため削除 (ムダの排除)
    
    certificate_type = Column(String(50)) # 証の種別 (例: 訓練等給付, 介護給付)
    
    # 障害支援区分 (空欄もある)
    disability_support_classification = Column(String(20)) 
    
    certificate_notes = Column(Text) # 特記事項・予備欄など

    # --- タイムスタンプ ---
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # --- リレーションシップ ---
    user = relationship('User', back_populates='certificates')
    issuance_municipality = relationship('MunicipalityMaster', back_populates='certificates', foreign_keys=[municipality_master_id])
    
    # 子テーブル (期間管理が独立しているもの)
    granted_services = relationship('GrantedService', back_populates='certificate', lazy='dynamic', cascade="all, delete-orphan")
    copayment_limits = relationship('CopaymentLimit', back_populates='certificate', lazy='dynamic', cascade="all, delete-orphan")
    meal_addon_statuses = relationship('MealAddonStatus', back_populates='certificate', lazy='dynamic', cascade="all, delete-orphan")
    copayment_management = relationship('CopaymentManagement', back_populates='certificate', lazy='dynamic', cascade="all, delete-orphan")

# ====================================================================
# 2. GrantedService (支給決定サービス / 暫定期間)
# ====================================================================
class GrantedService(db.Model):
    """支給決定サービスの詳細と支給量、適用期間（支給量変更履歴に対応）"""
    __tablename__ = 'granted_services'
    
    id = Column(Integer, primary_key=True)
    certificate_id = Column(Integer, ForeignKey('service_certificates.id'), nullable=False, index=True)
    
    # --- 支給量と期間 (6ページ目) ---
    granted_start_date = Column(Date, nullable=False)
    granted_end_date = Column(Date, nullable=False) # 終了日は必須（アラートのため）
    
    granted_amount_description = Column(String(100)) # 支給量（例: "当該月の日数-8日", "10日"）
    
    # --- 暫定支給決定期間 (6ページ目) ---
    is_tentative = Column(Boolean, default=False, nullable=False)
    tentative_start_date = Column(Date)
    tentative_end_date = Column(Date)
    
    # サービス種別マスタへの外部キー
    service_type_master_id = Column(Integer, ForeignKey('service_type_master.id'), nullable=False)
    
    # --- リレーションシップ ---
    certificate = relationship('ServiceCertificate', back_populates='granted_services')
    service_type = relationship('ServiceTypeMaster', back_populates='granted_services', foreign_keys=[service_type_master_id])
    
    # financeパッケージの ContractReportDetailへの一対一リレーション
    contract_detail = relationship('ContractReportDetail', back_populates='granted_service', uselist=False, cascade="all, delete-orphan")

# ====================================================================
# 3. CopaymentLimit (利用者負担上限額 / 期間)
# ====================================================================
class CopaymentLimit(db.Model):
    """利用者負担上限額の履歴と適用期間（負担額変更履歴に対応）"""
    __tablename__ = 'copayment_limits'
    
    id = Column(Integer, primary_key=True)
    certificate_id = Column(Integer, ForeignKey('service_certificates.id'), nullable=False, index=True)
    
    # --- 負担額と期間 (8ページ目) ---
    limit_start_date = Column(Date, nullable=False)
    limit_end_date = Column(Date, nullable=False) # 期間が異なる場合があるため必須
    
    limit_amount = Column(Numeric(precision=10, scale=2), nullable=False, default=0) # 0, 9300, 37200

    # --- リレーションシップ ---
    certificate = relationship('ServiceCertificate', back_populates='copayment_limits')

# ====================================================================
# 4. MealAddonStatus (食事提供加算 / 期間)
# ====================================================================
class MealAddonStatus(db.Model):
    """食事提供加算対象者の履歴と適用期間"""
    __tablename__ = 'meal_addon_statuses'
    
    id = Column(Integer, primary_key=True)
    certificate_id = Column(Integer, ForeignKey('service_certificates.id'), nullable=False, index=True)

    # --- 食事加算と期間 (8ページ目) ---
    meal_addon_start_date = Column(Date, nullable=False)
    meal_addon_end_date = Column(Date, nullable=False) # 期間が異なる場合があるため必須
    
    # '該当' (True) / '非該当' (False)
    is_applicable = Column(Boolean, nullable=False) 

    # --- リレーションシップ ---
    certificate = relationship('ServiceCertificate', back_populates='meal_addon_statuses')

# ====================================================================
# 5. CopaymentManagement (利用者負担上限管理)
# ====================================================================
class CopaymentManagement(db.Model):
    """利用者負担上限管理事業所の履歴と適用期間"""
    __tablename__ = 'copayment_management'
    
    id = Column(Integer, primary_key=True)
    certificate_id = Column(Integer, ForeignKey('service_certificates.id'), nullable=False, index=True)

    # --- 上限管理と期間 (8ページ目) ---
    management_start_date = Column(Date, nullable=False)
    management_end_date = Column(Date, nullable=False) # 期間が異なる場合があるため必須
    
    # '該当' (True) / '非該当' (False)
    is_applicable = Column(Boolean, nullable=False) 
    
    # 他事業所が管理する場合の事業所名（該当の場合のみ）
    managing_office_name = Column(String(255))
    
    # --- リレーションシップ ---
    certificate = relationship('ServiceCertificate', back_populates='copayment_management')