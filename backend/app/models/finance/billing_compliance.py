# 🚨 修正点: 'from backend.app.extensions' (絶対参照)
from backend.app.extensions import db
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, DateTime, Text, Numeric, func

# ====================================================================
# 1. ContractReportDetail (事業所記入欄 / 契約内容報告書)
# ====================================================================
class ContractReportDetail(db.Model):
    """
    契約内容報告書に記載する、提供サービスに関する詳細。
    支給決定期間（GrantedService）に一対一で紐づく（原理1）。
    """
    __tablename__ = 'contract_report_details'
    
    id = Column(Integer, primary_key=True)
    
    # core/service_certificate.py の GrantedService への 1:1 リンク
    granted_service_id = Column(
        Integer, 
        ForeignKey('granted_services.id'), 
        nullable=False, 
        unique=True, # 1対1を保証
        index=True
    )
    
    # ★ 追加: 利用者の「在籍」を確定させるための紐づけ（原理3）
    # これにより、「どの事業所（サービス）」の利用者かが確定する。
    office_service_configuration_id = Column(Integer, ForeignKey('office_service_configurations.id'), nullable=False, index=True)
    
    # --- 事業所記入欄の情報（原理3：会計の正確性） ---
    contract_corporation_name = Column(String(100)) # 提供事業者（法人名）
    contract_office_name = Column(String(100))      # 提供事業所（事業所名）
    contract_service_type = Column(String(50))      # 提供サービス
    contract_granted_days = Column(Integer)         # 事業所の支給量
    
    # 契約日
    contract_date = Column(Date)
    
    # --- 証憑（原理1） ---
    # 利用者と締結した契約書・重要事項説明書のURL
    contract_document_url = Column(String(500))
    important_matters_url = Column(String(500))
    
    # --- リレーションシップ ---
    granted_service = db.relationship('GrantedService', back_populates='contract_detail')
    service_config = db.relationship('OfficeServiceConfiguration') # 在籍先

    def __repr__(self):
        return f'<ContractDetail for GrantedService {self.granted_service_id}>'

# ====================================================================
# 2. ComplianceEventLog (加算・減算・助成金の期間管理)
# ====================================================================
class ComplianceEventLog(db.Model):
    """
    加算・減算・助成金など、会計に影響する事象の「期間」を管理するログ。
    送迎加算や初期加算の適用期間もここで管理する（原理3）。
    """
    __tablename__ = 'compliance_event_logs'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # どの事象か (例: '集中支援加算', '計画未作成減算', '送迎加算', '特別地域加算')
    # 運用柔軟性のためString型とするが、ロジック内で定数管理する
    event_type = Column(String(100), nullable=False, index=True) 
    
    # --- 法令遵守（原理1） ---
    start_date = Column(Date, nullable=False) # 適用開始日
    end_date = Column(Date, nullable=False) # 適用終了日
    
    # --- 証憑（原理1） ---
    document_url = Column(String(500)) # 根拠となる届出書や評価シートのURL
    notes = Column(Text) # 備考
    
    user = db.relationship('User', back_populates='compliance_events')