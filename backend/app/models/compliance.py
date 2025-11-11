# backend/app/models/compliance.py

from datetime import datetime
from app.extensions import db
from sqlalchemy.orm import relationship
from sqlalchemy import UniqueConstraint

# ----------------------------------------------------
# 1. GovernmentFeeMaster (厚労省報酬単位数マスタ)
# ----------------------------------------------------
class GovernmentFeeMaster(db.Model):
    # (変更なし)
    __tablename__ = 'government_fee_master'
    
    id = db.Column(db.Integer, primary_key=True)
    fee_code = db.Column(db.String(20), nullable=False, unique=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(20), nullable=False) 
    service_type = db.Column(db.String(50), nullable=False) 
    
    unit_price = db.Column(db.Numeric, nullable=False) 
    unit_type = db.Column(db.String(20), nullable=False) 
    
    disability_classification = db.Column(db.String(10)) 
    staff_ratio = db.Column(db.String(20)) 
    
    start_date = db.Column(db.Date, nullable=False) 
    end_date = db.Column(db.Date) 

    eligibility_summary = db.Column(db.Text) 
    rule_document_url = db.Column(db.String(255)) 

    requirements = db.relationship('FeeEligibilityRequirement', back_populates='fee_master', lazy=True)
    ### 'decisions' のリレーションシップは office_admin.py の FeeCalculationDecision 側で
    ### back_populates が設定されるため、こちら側には不要 (または backref を使う)
    ### ただし、元コードの 'decisions' は office_admin.py のモデルを参照していないため、
    ### ここでは元コードのまま 'decisions' を残すか、削除します。
    ### office_admin.py 側に一本化するため、ここでは削除を推奨します。
    # decisions = db.relationship('FeeCalculationDecision', back_populates='fee_master', lazy=True)

# ----------------------------------------------------
# 2. ComplianceRule (法令ルールマスタ)
# ----------------------------------------------------
class ComplianceRule(db.Model):
    # (変更なし)
    __tablename__ = 'compliance_rules'
    id = db.Column(db.Integer, primary_key=True)
    rule_source = db.Column(db.String(50), nullable=False) 
    rule_code = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=False)
    service_type = db.Column(db.String(50), nullable=False)
    min_frequency = db.Column(db.Integer) 
    is_active = db.Column(db.Boolean, default=True, nullable=False)

# ----------------------------------------------------
# 3. FeeEligibilityRequirement (報酬算定要件詳細)
# ----------------------------------------------------
class FeeEligibilityRequirement(db.Model):
    # (変更なし)
    __tablename__ = 'fee_eligibility_requirements'
    id = db.Column(db.Integer, primary_key=True)
    fee_master_id = db.Column(db.Integer, db.ForeignKey('government_fee_master.id'), nullable=False)
    compliance_rule_id = db.Column(db.Integer, db.ForeignKey('compliance_rules.id'))
    
    requirement_code = db.Column(db.String(50), nullable=False) 
    description = db.Column(db.Text, nullable=False) 
    check_type = db.Column(db.String(50), nullable=False) 
    reference_model = db.Column(db.String(50)) 

    fee_master = db.relationship('GovernmentFeeMaster', back_populates='requirements')
    compliance_rule = db.relationship('ComplianceRule')

# ----------------------------------------------------
# 4. ComplianceFact (システムによる要件充足度の評価結果)
# ----------------------------------------------------
class ComplianceFact(db.Model):
    # (変更なし)
    __tablename__ = 'compliance_facts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    fee_master_id = db.Column(db.Integer, db.ForeignKey('government_fee_master.id'), nullable=False)
    
    target_date = db.Column(db.Date, nullable=False) 
    
    check_result_code = db.Column(db.String(50), nullable=False) 
    is_satisfied = db.Column(db.Boolean, nullable=False) 
    feedback_message = db.Column(db.Text) 

    reference_model = db.Column(db.String(50))
    reference_id = db.Column(db.Integer)

    user = db.relationship('User', back_populates='compliance_facts')
    fee_master = db.relationship('GovernmentFeeMaster', foreign_keys=[fee_master_id])

### ----------------------------------------------------
### 5. FeeCalculationDecision (算定意思決定) モデルを削除
### ----------------------------------------------------
# class FeeCalculationDecision(db.Model):
#    ... (office_admin.py に定義を一本化するため、ここの定義はすべて削除)