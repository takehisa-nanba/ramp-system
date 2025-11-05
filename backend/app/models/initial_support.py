# backend/app/models/initial_support.py
### (変更なし。こちらをProspectモデルの正として使用します)

from datetime import datetime
from app.extensions import db
from sqlalchemy.orm import relationship
from .master import StatusMaster, ReferralSourceMaster, AssessmentItemMaster

# ----------------------------------------------------
# 1. Prospect (見込み客)
# ----------------------------------------------------
class Prospect(db.Model):
    __tablename__ = 'prospects'
    
    id = db.Column(db.Integer, primary_key=True)
    last_name = db.Column(db.String(50), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name_kana = db.Column(db.String(50))
    first_name_kana = db.Column(db.String(50))
    contact_info = db.Column(db.Text)
    
    status_id = db.Column(db.Integer, db.ForeignKey('status_master.id'))
    referral_source_id = db.Column(db.Integer, db.ForeignKey('referral_source_master.id'))
    
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    remarks = db.Column(db.Text)

    # リレーションシップ
    status = db.relationship('StatusMaster', foreign_keys=[status_id])
    referral_source = db.relationship('ReferralSourceMaster')
    enrollment_logs = db.relationship('PreEnrollmentLog', back_populates='prospect', lazy=True)


# ----------------------------------------------------
# 2. PreEnrollmentLog (利用前接触記録)
# ----------------------------------------------------
class PreEnrollmentLog(db.Model):
    __tablename__ = 'pre_enrollment_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    prospect_id = db.Column(db.Integer, db.ForeignKey('prospects.id'), nullable=False)
    
    contact_date = db.Column(db.DateTime, nullable=False)
    log_type = db.Column(db.String(50), nullable=False) 
    supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id'), nullable=False)
    
    summary = db.Column(db.Text)
    initial_assessment_memo = db.Column(db.Text)

    # リレーションシップ
    prospect = db.relationship('Prospect', back_populates='enrollment_logs')
    supporter = db.relationship('Supporter')
    
    assessment_scores = db.relationship('PreEnrollmentAssessmentScore', back_populates='enrollment_log', lazy=True)


# ----------------------------------------------------
# 3. PreEnrollmentAssessmentScore (新規: 初期アセスメント評価)
# ----------------------------------------------------
class PreEnrollmentAssessmentScore(db.Model):
    __tablename__ = 'pre_enrollment_assessment_scores'
    
    id = db.Column(db.Integer, primary_key=True)
    log_id = db.Column(db.Integer, db.ForeignKey('pre_enrollment_logs.id'), nullable=False)
    
    item_id = db.Column(db.Integer, db.ForeignKey('assessment_item_master.id'), nullable=False) 
    
    score = db.Column(db.Integer) 
    comment = db.Column(db.Text)

    # リレーションシップ
    enrollment_log = db.relationship('PreEnrollmentLog', back_populates='assessment_scores')
    assessment_item = db.relationship('AssessmentItemMaster')