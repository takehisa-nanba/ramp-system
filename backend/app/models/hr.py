# backend/app/models/hr.py の修正版 (循環参照の断絶を最優先)

from datetime import datetime
from app.extensions import db
from sqlalchemy.orm import relationship
from sqlalchemy import UniqueConstraint, Date, Integer, ForeignKey, Column

# ----------------------------------------------------
# 1. SupporterTimecard (職員タイムカード - 常勤換算の根拠)
# ----------------------------------------------------
class SupporterTimecard(db.Model):
    __tablename__ = 'supporter_timecards'
    
    id = Column(Integer, primary_key=True)
    supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=False)
    
    work_date = Column(Date, nullable=False)
    check_in = Column(db.DateTime, nullable=False)
    check_out = Column(db.DateTime) # 未退勤の場合はNULL
    break_duration_minutes = Column(Integer, default=0, nullable=False)
    
    actual_work_minutes = Column(Integer, default=0, nullable=False) # 実働時間 (計算値)
    is_approved = Column(db.Boolean, default=False, nullable=False)
    
    # Supporter モデルは core.py にあり、循環参照の対象ではないため、そのまま
    supporter = db.relationship('Supporter', back_populates='timecards')

# ----------------------------------------------------
# 2. SupporterJobAssignment (★ 法令上の職務割り当て履歴 / 履歴管理 ★)
# ----------------------------------------------------
class SupporterJobAssignment(db.Model):
    __tablename__ = 'supporter_job_assignments'
    
    id = Column(Integer, primary_key=True)
    
    # 「誰が」
    supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=False)
    
    # 「どの職務を」
    job_title_id = Column(Integer, ForeignKey('job_title_master.id'), nullable=False)
    
    # 「いつから」
    start_date = Column(Date, nullable=False)
    
    # 「いつまで」 (NULLの場合は現在も有効)
    end_date = Column(Date, nullable=True)
    
    # リレーションシップ
    supporter = db.relationship('Supporter', back_populates='job_assignments')
    
    # A. 厳格化適用: JobTitleMaster をクラス名文字列に変更
    job_title = db.relationship(
        'JobTitleMaster', # <- クラス名を参照する文字列に変更
        back_populates='assignments'
    )

    __table_args__ = (
        UniqueConstraint('supporter_id', 'job_title_id', 'start_date', name='uq_supporter_job_start'),
    )

# ----------------------------------------------------
# 3. JobFilingRecord (★ 新規追加: 職務の行政届出履歴の証拠 ★)
# ----------------------------------------------------
class JobFilingRecord(db.Model):
    __tablename__ = 'job_filing_records'
    
    id = Column(Integer, primary_key=True)
    
    # どの事業所について届け出たか (組織ロールの所属先)
    office_id = Column(Integer, ForeignKey('office_settings.id'), nullable=False)
    
    # どの職務について届け出たか
    job_title_id = Column(Integer, ForeignKey('job_title_master.id'), nullable=False)
    
    # 届出が有効になる日付（行政から受理された日付）
    effective_date = Column(Date, nullable=False)
    
    # 届出書類の証憑URL（S3など）
    document_url = Column(db.String(500), nullable=True)
    
    # リレーションシップ
    # C. 厳格化適用: OfficeSetting をクラス名文字列に変更 (office_admin.pyとの循環参照回避)
    office = db.relationship(
        'OfficeSetting', # <- クラス名を参照する文字列に変更
        back_populates='job_filings'
    )
    
    # A. 厳格化適用: JobTitleMaster をクラス名文字列に変更
    job_title = db.relationship(
        'JobTitleMaster', # <- クラス名を参照する文字列に変更
        back_populates='filing_history'
    )

# ----------------------------------------------------
# 4. ExpenseCategoryMaster (勘定科目マスタ)
# ----------------------------------------------------
class ExpenseCategoryMaster(db.Model):
# ... (変更なし) ...
    __tablename__ = 'expense_category_master'
    id = Column(Integer, primary_key=True)
    code = db.Column(db.String(20), nullable=False, unique=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    is_active = db.Column(db.Boolean, default=True)

# ----------------------------------------------------
# 5. ExpenseRecord (経費精算記録)
# ----------------------------------------------------
class ExpenseRecord(db.Model):
# ... (変更なし) ...
    __tablename__ = 'expense_records'
    id = Column(Integer, primary_key=True)
    supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=False)
    expense_date = Column(Date, nullable=False)
    category_id = Column(Integer, ForeignKey('expense_category_master.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=False)
    is_approved = db.Column(db.Boolean, default=False, nullable=False)
    approval_supporter_id = Column(Integer, ForeignKey('supporters.id'))

    supporter = db.relationship('Supporter', foreign_keys=[supporter_id], backref='expense_claims')
    approver = db.relationship('Supporter', foreign_keys=[approval_supporter_id], backref='expenses_approved')
    category = db.relationship('ExpenseCategoryMaster')