# 🚨 修正点: 'from backend.app.extensions' (絶対参照)
from backend.app.extensions import db
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, DateTime, Text, Numeric, func

# ====================================================================
# 1. MonthlyBillingSummary (月次請求サマリー / ロック)
# ====================================================================
class MonthlyBillingSummary(db.Model):
    """
    月次請求サマリー（国保連への公費請求）。
    請求確定後にロック(FINALIZED)され、不可逆な監査証跡(原理1)となる。
    """
    __tablename__ = 'monthly_billing_summary'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    # どのサービス(事業所番号)での請求か
    office_service_configuration_id = Column(Integer, ForeignKey('office_service_configurations.id'), nullable=False, index=True)
    
    billing_month = Column(Date, nullable=False, index=True) # 請求対象月 (例: 2025-11-01)
    
    # --- 請求集計（原理3） ---
    total_units_claimed = Column(Integer, nullable=False) # 請求単位の合計
    claim_amount = Column(Numeric(precision=10, scale=2), nullable=False) # 請求金額（公費）
    
    # --- ワークフロー（原理1：不可逆性） ---
    # (PENDING, FINALIZED_BY_MANAGER, SUBMITTED, PAID, REJECTED)
    claim_status = Column(String(30), default='PENDING', nullable=False)
    lock_date = Column(DateTime) # 請求提出日（ロック日時）
    
    user = db.relationship('User')
    service_config = db.relationship('OfficeServiceConfiguration')
    
    # このサマリーに対応する代理受領書
    agency_receipt = db.relationship('AgencyReceiptStatement', back_populates='billing_summary', uselist=False, cascade="all, delete-orphan")

# ====================================================================
# 2. ClientInvoice (利用者への自己負担請求書 & 領収証)
# ====================================================================
class ClientInvoice(db.Model):
    """
    自己負担請求書（利用者への請求）および領収証。
    未収金管理と入金後の証憑管理の土台となる（原理3）。
    """
    __tablename__ = 'client_invoices'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    billing_month = Column(Date, nullable=False, index=True) # 請求対象月
    
    # --- 請求内容 ---
    self_pay_amount = Column(Numeric(precision=10, scale=2), nullable=False) # 1割負担などの自己負担額
    actual_cost_amount = Column(Numeric(precision=10, scale=2), nullable=False) # 食費などの実費額
    total_amount = Column(Numeric(precision=10, scale=2), nullable=False)
    
    # --- 請求の証憑 ---
    invoice_pdf_url = Column(String(500)) # 発行した請求書のURL
    
    # --- 入金確認（原理1） ---
    # (PENDING, PAID, OVERDUE)
    payment_status = Column(String(30), default='PENDING', nullable=False)
    payment_date = Column(Date) # 入金日
    payment_confirmed_by_id = Column(Integer, ForeignKey('supporters.id')) # 入金確認を行った職員
    
    # --- 領収証（★ NEW: 入金後の証憑） ---
    receipt_pdf_url = Column(String(500)) # 発行した領収証のURL
    receipt_issued_at = Column(DateTime) # 領収証発行日時
    
    # --- 受領確認（原理1：請求書/領収証の受け渡し） ---
    receipt_confirmation_timestamp = Column(DateTime) # 確実に手渡した（またはOTL閲覧）日時
    handover_method = Column(String(30)) # (例: 'DIGITAL_VIEW', 'IN_PERSON_HANDOVER')
    handover_supporter_id = Column(Integer, ForeignKey('supporters.id')) # 手渡した職員
    
    user = db.relationship('User')
    payment_confirmer = db.relationship('Supporter', foreign_keys=[payment_confirmed_by_id])
    handover_supporter = db.relationship('Supporter', foreign_keys=[handover_supporter_id])

# ====================================================================
# 3. AgencyReceiptStatement (代理受領書)
# ====================================================================
class AgencyReceiptStatement(db.Model):
    """
    代理受領書（国保連からの入金確認後、利用者へ発行する報告書）。
    会計の透明性（原理5）を担保する。
    """
    __tablename__ = 'agency_receipt_statements'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    billing_month = Column(Date, nullable=False, index=True)
    
    # どの請求（入金）に対する報告か
    monthly_summary_id = Column(Integer, ForeignKey('monthly_billing_summary.id'), unique=True, nullable=False)
    
    # --- 入金事実（原理3） ---
    kokuhoren_payment_date = Column(Date, nullable=False) # 国保連からの入金確認日
    
    # --- 証憑と受領確認（原理1） ---
    statement_pdf_url = Column(String(500), nullable=False) # 利用者へ発行した代理受領書のURL
    
    receipt_confirmation_timestamp = Column(DateTime) # 確実に手渡した（またはOTL閲覧）日時
    handover_method = Column(String(30))
    handover_supporter_id = Column(Integer, ForeignKey('supporters.id'))
    
    user = db.relationship('User')
    billing_summary = db.relationship('MonthlyBillingSummary', back_populates='agency_receipt')
    handover_supporter = db.relationship('Supporter', foreign_keys=[handover_supporter_id])

# ====================================================================
# 4. DocumentConsentLog (同意証跡ログ / OTL対応)
# ====================================================================
class DocumentConsentLog(db.Model):
    """
    同意証跡ログ（電子署名・OTL）。
    計画書(SupportPlan)や会議録(MonitoringReport)への同意を記録する
    汎用的な監査証跡（原理1）。
    """
    __tablename__ = 'document_consent_logs'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # どの文書に対する同意か (汎用リレーション)
    document_type = Column(String(50), nullable=False) # (例: 'SUPPORT_PLAN', 'MONITORING_REPORT')
    document_id = Column(Integer, nullable=False, index=True)
    
    # --- 証跡（原理1） ---
    consent_timestamp = Column(DateTime, nullable=False, default=func.now())
    # (例: 'OTL_TOKEN_ID_...', 'PIN_HASH_...', 'DIGITAL_SIGNATURE_ID')
    consent_proof = Column(String(255)) 
    
    # 同意がなされた時点での、システム自動生成された証憑PDFのURL
    generated_document_url = Column(String(500)) 

    user = db.relationship('User')
    # SupportPlanへのリレーション (SupportPlan側で定義)
    plan = db.relationship(
        'SupportPlan', 
        primaryjoin="and_(DocumentConsentLog.document_id == SupportPlan.id, DocumentConsentLog.document_type == 'SUPPORT_PLAN')",
        foreign_keys="DocumentConsentLog.document_id",
        back_populates='consent_log'
    )