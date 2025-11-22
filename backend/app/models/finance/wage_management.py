# backend/app/models/support/job_retention.py
from backend.app.extensions import db
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, DateTime, Text, Numeric, func

# ====================================================================
# 1. SalesInvoice (A/B型 事業収入 - 売上請求)
# ====================================================================
class SalesInvoice(db.Model):
    """
    A型・B型の生産活動における、取引先（VendorMaster）への売上請求書。
    「公費請求」とは異なる「一般事業収入」を管理する（原理3）。
    """
    __tablename__ = 'sales_invoices'
    
    id = Column(Integer, primary_key=True)
    
    # どのサービス(事業所番号)での売上か
    office_service_configuration_id = Column(Integer, ForeignKey('office_service_configurations.id'), nullable=False, index=True)
    
    # どの取引先への請求か (masters/master_definitions.py を参照)
    vendor_id = Column(Integer, ForeignKey('vendor_master.id'), nullable=False, index=True)
    
    issue_date = Column(Date, nullable=False) # 請求日
    due_date = Column(Date) # 支払期日
    
    # --- 請求内容 ---
    total_amount = Column(Numeric(precision=10, scale=2), nullable=False)
    tax_amount = Column(Numeric(precision=10, scale=2), nullable=False)
    
    # --- ワークフロー ---
    # (DRAFT, SENT, PAID, CANCELLED)
    invoice_status = Column(String(30), default='DRAFT', nullable=False)
    payment_date = Column(Date) # 入金確認日
    
    # --- 領収書（★ NEW: 入金後の証憑） ---
    # 取引先へ発行した領収書の控え
    receipt_pdf_url = Column(String(500)) 
    receipt_issued_at = Column(DateTime) 
    
    service_config = db.relationship('OfficeServiceConfiguration')
    vendor = db.relationship('VendorMaster', back_populates='invoices')

# ====================================================================
# 2. UserWageLog (利用者工賃記録 - 支払と受取書)
# ====================================================================
class UserWageLog(db.Model):
    """
    利用者ごとの月次工賃の計算根拠と支払事実の記録（原理3）。
    DailyProductivityLogの実績に基づき計算される。
    """
    __tablename__ = 'user_wage_logs'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    calculation_month = Column(Date, nullable=False, index=True) # 工賃計算対象月
    
    # --- 計算根拠（原理1） ---
    # (DailyProductivityLogから集計した値)
    total_work_minutes = Column(Integer) # 月次総労働時間（分）
    total_units_passed = Column(Integer) # 月次良品生産数
    
    # --- 支払（原理3） ---
    gross_wage_amount = Column(Numeric(precision=10, scale=2), nullable=False) # 総工賃額
    deductions = Column(Numeric(precision=10, scale=2)) # 控除額（ある場合）
    net_payment_amount = Column(Numeric(precision=10, scale=2), nullable=False) # 差引支払額
    
    payment_timestamp = Column(DateTime) # 支払日（証跡）
    
    # --- 受取書（利用者発行領収書） ---
    # 利用者が工賃を受け取ったことを証明する書類のURL
    recipient_receipt_url = Column(String(500)) 
    # 署名または受領確認が行われた日
    receipt_signed_date = Column(Date)

    user = db.relationship('User')

# ====================================================================
# 3. FeeCalculationDecision (給付費算定決定)
# ====================================================================
class FeeCalculationDecision(db.Model):
    """
    給付費算定の決定履歴。
    毎月の請求計算において、どの加算・減算が適用されたかの最終決定ログ。
    """
    __tablename__ = 'fee_calculation_decisions'
    
    id = Column(Integer, primary_key=True)
    office_service_configuration_id = Column(Integer, ForeignKey('office_service_configurations.id'), nullable=False, index=True)
    
    calculation_month = Column(Date, nullable=False)
    
    # 適用された加算・減算のリスト（JSONなどで保持）
    applied_fees_json = Column(Text) 
    
    is_finalized = Column(Boolean, default=False)
    finalized_at = Column(DateTime)
    
    service_config = db.relationship('OfficeServiceConfiguration', back_populates='fee_decisions')