# backend/app/models/finance/accounting_management.py

# 修正点: 'from backend.app.extensions' (絶対参照)
from backend.app.extensions import db
from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, ForeignKey, Text, Boolean, func

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
    document_type = Column(String(50), nullable=False) # (例: 'SUPPORT_PLAN', 'RETENTION_SUPPORT_REPORT')
    document_id = Column(Integer, nullable=False, index=True)
    document_version = Column(Integer, nullable=False) # 文書版数（defaultなし、明示必須）
    action = Column(String(30), nullable=False) # 'CONSENT'（計画同意）または 'ACKNOWLEDGEMENT'（レポート確認）
    
    # --- 署名・同意証跡 ---
    signature_method = Column(String(30), nullable=False) # 'USER_DIGITAL', 'PAPER_UPLOAD', 'LEGACY_STAFF_RECORDED'
    consent_timestamp = Column(DateTime, nullable=False, default=func.now()) # 本人が署名または確認した日時
    consent_proof = Column(String(255)) 
    
    # 本人へ提示・交付した確定版文書URL
    generated_document_url = Column(String(500)) 
    
    # 紙署名の場合の署名済み証拠ファイルURL (画像/PDF)
    evidence_file_url = Column(String(500), nullable=True)
    
    # 登録職員情報
    recorded_by_supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=True)
    recorded_at = Column(DateTime, nullable=False, default=func.now()) # システムへ証跡を登録した日時

    user = db.relationship('User', foreign_keys=[user_id])
    recorded_by_supporter = db.relationship('Supporter', foreign_keys=[recorded_by_supporter_id])
    
    # SupportPlanへのリレーション
    plan = db.relationship(
        'SupportPlan', 
        primaryjoin="and_(DocumentConsentLog.document_id == SupportPlan.id, DocumentConsentLog.document_type == 'SUPPORT_PLAN')",
        foreign_keys="DocumentConsentLog.document_id",
        back_populates='consent_log'
    )

# ====================================================================
# 5. DocumentDeliveryLog (文書交付・閲覧履歴)
# ====================================================================
class DocumentDeliveryLog(db.Model):
    """
    確定文書の交付・閲覧履歴。
    同意・確認証跡（DocumentConsentLog）とは分離し、
    電磁的交付（DIGITAL）や紙交付（PAPER）の事実および初回閲覧を記録する。
    """
    __tablename__ = 'document_delivery_logs'
    __table_args__ = (
        db.UniqueConstraint(
            'document_type', 'document_id', 'document_version', 'recipient_user_id', 'delivery_method',
            name='uq_doc_delivery_recipient_method'
        ),
    )

    id = Column(Integer, primary_key=True)
    document_type = Column(String(50), nullable=False, index=True) # 'SUPPORT_PLAN', 'RETENTION_SUPPORT_REPORT'
    document_id = Column(Integer, nullable=False, index=True)
    document_version = Column(Integer, nullable=False) # defaultなし（アプリケーション側でVersion明示必須、Fail Closed）

    recipient_user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True) # 本人限定、NOT NULL

    delivery_method = Column(String(20), nullable=False) # 'DIGITAL', 'PAPER'
    delivered_at = Column(DateTime, nullable=False, default=func.now())
    viewed_at = Column(DateTime, nullable=True) # 初回閲覧日時

    delivered_by_supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())

    recipient_user = db.relationship('User', foreign_keys=[recipient_user_id])
    delivered_by = db.relationship('Supporter', foreign_keys=[delivered_by_supporter_id])


class CorporateTransferLog(db.Model):
    """
    法人からのサービス提供費（工賃原資など）の繰入指示の証跡。
    会計の分離原則を担保する。
    """
    __tablename__ = 'corporate_transfer_logs'
    
    id = Column(Integer, primary_key=True)
    
    corporation_id = Column(Integer, ForeignKey('corporations.id'), nullable=False, index=True)
    
    # 財務上の正当性を証明する項目
    transfer_amount = Column(Numeric(precision=10, scale=2), nullable=False)
    transfer_date = Column(Date, nullable=False)
    
    # 繰入の理由 (例: 'WAGE_DEFICIT_COVERAGE', 'OPERATING_SUBSIDY')
    transfer_reason_type = Column(String(50), nullable=False)
    notes = Column(Text)

    # 誰が承認したか
    approver_supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=False)
    approved_at = Column(DateTime, default=func.now(), nullable=False)

    # リレーションシップ
    corporation = db.relationship('Corporation')
    approver = db.relationship('Supporter')