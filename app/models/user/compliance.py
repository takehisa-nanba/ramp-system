# app/models/user/compliance.py
from app.extensions import db
from datetime import datetime, timezone
from sqlalchemy.orm import relationship

class Certificate(db.Model):
    """
    受給者証情報モデル (利用者に1対多)
    障害福祉サービス受給者証の情報を格納する。
    """
    __tablename__ = 'certificates'
    __table_args__ = ({"extend_existing": True},)
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # マスタ（master.pyで定義済み）を参照
    certificate_type_id = db.Column(db.Integer, db.ForeignKey('certificate_type_master.id')) 
    certificate_number = db.Column(db.String(100)) # 受給者証番号
    
    # 請求に必要な「市区町村コード」を参照 (master.pyのMunicipalityMasterへ)
    billing_municipality_id = db.Column(db.Integer, db.ForeignKey('municipality_master.id'))
    
    # --- 支給決定期間 ---
    issue_date = db.Column(db.Date) # 支給決定日
    expiry_date = db.Column(db.Date, index=True) # 支給満了日

    # --- 上限負担月額 ---
    copayment_limit = db.Column(db.Integer) # 利用者負担上限月額
    copayment_start_date = db.Column(db.Date) # 上限負担月額 適用開始日
    copayment_end_date = db.Column(db.Date) # 上限負担月額 適用終了日

    # --- 支給量（受給者証全体）---
    service_amount = db.Column(db.String(50)) # 例: '20', '月-8'
    service_type = db.Column(db.String(100)) # 例: 就労移行支援

    # --- RAMP契約情報（様式第26号 関連）---
    ramp_service_field_index = db.Column(db.Integer, nullable=True) # 事業者記入欄の番号
    ramp_service_amount = db.Column(db.String(50)) # RAMPの契約支給量
    ramp_contract_date = db.Column(db.Date) # RAMPとの契約日
    ramp_contract_status = db.Column(db.String(20), nullable=True) # '新規契約', '契約変更'など

    # --- タイムスタンプ ---
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    remarks = db.Column(db.Text)

    # --- リレーションシップ ---
    user = db.relationship('User', back_populates='certificates')
    certificate_type = db.relationship('CertificateTypeMaster')
    billing_municipality = db.relationship('MunicipalityMaster', back_populates='certificates_issued_here')

    def __repr__(self):
        return f'<Certificate {self.id} (User: {self.user_id})>'