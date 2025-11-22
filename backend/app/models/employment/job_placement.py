# backend/app/models/support/job_retention.py
from backend.app.extensions import db
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, DateTime, Text, func

# ====================================================================
# 1. EmployerMaster (企業マスター)
# ====================================================================
class EmployerMaster(db.Model):
    """
    就労先・実習先・開拓先企業（取引先とは異なる）のマスターデータ。
    企業情報を一元管理し、重複登録のムダを排除する（原理4）。
    """
    __tablename__ = 'employer_master'
    
    id = Column(Integer, primary_key=True)
    company_name = Column(String(255), nullable=False, index=True)
    industry_type = Column(String(100)) # 業種
    address = Column(String(255))
    contact_person = Column(String(100)) # 担当者
    contact_number = Column(String(20))
    
    # 逆参照
    placements = db.relationship('JobPlacementLog', back_populates='employer', lazy='dynamic')
    development_logs = db.relationship('JobDevelopmentLog', back_populates='employer', lazy='dynamic')

# ====================================================================
# 2. JobPlacementLog (就労・定着ログ / 復職支援)
# ====================================================================
class JobPlacementLog(db.Model):
    """
    利用者の就労・復職の事実と定着支援の経過ログ。
    定着率（原理3）の計算土台となる。
    """
    __tablename__ = 'job_placement_logs'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    employer_id = Column(Integer, ForeignKey('employer_master.id'), nullable=False, index=True)
    
    # --- 就労・復職の事実（原理14） ---
    placement_date = Column(Date, nullable=False) # 就職日または復職日
    
    # (例: 'NEW_PLACEMENT'（新規就職）, 'RETURN_TO_WORK'（復職支援）)
    support_scenario = Column(String(50), nullable=False) 
    
    job_title = Column(String(100)) # 職種
    employment_status = Column(String(50)) # 雇用形態 (例: '正社員', 'パート')
    weekly_work_hours = Column(Integer) # 週の労働時間（分）
    
    # --- 定着支援の記録 ---
    follow_up_support_content = Column(Text) # 定着支援の記録（履歴管理対象）
    
    separation_date = Column(Date) # 離職日 (NULLの場合は在職中)
    
    # --- リレーションシップ ---
    user = db.relationship('User', back_populates='job_placements')
    employer = db.relationship('EmployerMaster', back_populates='placements')

# ====================================================================
# 3. JobDevelopmentLog (企業開拓ログ)
# ====================================================================
class JobDevelopmentLog(db.Model):
    """
    職員による新規の企業開拓活動（連絡、訪問）の履歴。
    営業活動の重複（ムダ）を防ぐ。
    """
    __tablename__ = 'job_development_logs'
    
    id = Column(Integer, primary_key=True)
    supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=False, index=True)
    
    # 開拓対象の企業 (NULL許容、新規開拓中のため)
    employer_id = Column(Integer, ForeignKey('employer_master.id'), nullable=True, index=True)
    
    activity_timestamp = Column(DateTime, nullable=False, default=func.now())
    
    # (例: 'PHONE_CALL', 'VISIT', 'EMAIL')
    activity_type = Column(String(50), nullable=False) 
    activity_summary = Column(Text, nullable=False) # 活動概要 (NULL禁止)
    
    # --- リレーションシップ ---
    supporter = db.relationship('Supporter')
    employer = db.relationship('EmployerMaster', back_populates='development_logs')