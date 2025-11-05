from datetime import datetime
from app.extensions import db
from sqlalchemy.orm import relationship

# ----------------------------------------------------
# 1. JobOffer (求人情報)
# ----------------------------------------------------
class JobOffer(db.Model):
    __tablename__ = 'job_offers'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 基本情報
    company_name = db.Column(db.String(100), nullable=False)
    job_title = db.Column(db.String(100), nullable=False)
    work_location = db.Column(db.String(200), nullable=False)
    
    # 労働条件
    salary_type = db.Column(db.String(20))
    salary_amount = db.Column(db.Integer)
    
    # マッチング情報（戦略的情報）
    required_skills = db.Column(db.Text) # 企業が求めるスキル
    suitable_user_profiles = db.Column(db.Text) # 想定される利用者特性（例: 精神障害を持つ経験者向け）
    is_matched = db.Column(db.Boolean, default=False) # 既存の利用者とマッチング済みか
    
    is_disabled_friendly = db.Column(db.Boolean, default=True, nullable=False)
    description = db.Column(db.Text, nullable=False)
    
    # 管理情報
    contact_supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id'), nullable=False)
    received_date = db.Column(db.Date, nullable=False)
    expiration_date = db.Column(db.Date)
    
    supporter = db.relationship('Supporter')


# ----------------------------------------------------
# 2. CompanyContactLog (企業営業履歴 - 就職開拓)
# ----------------------------------------------------
class CompanyContactLog(db.Model):
    __tablename__ = 'company_contact_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    company_name = db.Column(db.String(100), nullable=False)
    contact_date = db.Column(db.DateTime, nullable=False)
    supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id'), nullable=False)
    
    # 活動内容
    contact_method = db.Column(db.String(50), nullable=False)
    purpose = db.Column(db.String(100), nullable=False)
    summary = db.Column(db.Text, nullable=False)
    is_lead_generated = db.Column(db.Boolean, default=False, nullable=False)

    # 企業評価（経営・戦略的情報）
    acceptance_score = db.Column(db.Integer) # 受入度スコア (1-5点)
    is_sustainable_partner = db.Column(db.Boolean, default=False) # 継続的な連携が可能か
    next_follow_up_date = db.Column(db.Date) # 次回のフォローアップ予定日

    supporter = db.relationship('Supporter')


# ----------------------------------------------------
# 3. MarketingOutreachLog (集客営業履歴 - 流入チャネル開拓)
# ----------------------------------------------------
class MarketingOutreachLog(db.Model):
    __tablename__ = 'marketing_outreach_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    outreach_date = db.Column(db.DateTime, nullable=False)
    supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id'), nullable=False)
    
    target_institution = db.Column(db.String(200), nullable=False) # 訪問先名称（例: 病院、学校、相談事業所）
    contact_method = db.Column(db.String(50), nullable=False)
    purpose = db.Column(db.String(100), nullable=False)
    summary = db.Column(db.Text, nullable=False)
    
    is_referral_generated = db.Column(db.Boolean, default=False, nullable=False) # この活動が見込み客の紹介につながったか
    next_follow_up_date = db.Column(db.Date) # 次回のフォローアップ予定日

    supporter = db.relationship('Supporter')
