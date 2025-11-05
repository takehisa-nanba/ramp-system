# backend/app/models/hr.py

from datetime import datetime
from app.extensions import db
from sqlalchemy.orm import relationship
from sqlalchemy import UniqueConstraint

# ----------------------------------------------------
# 1. SupporterTimecard (職員タイムカード - 常勤換算の根拠)
# ----------------------------------------------------
class SupporterTimecard(db.Model):
    __tablename__ = 'supporter_timecards'
    
    id = db.Column(db.Integer, primary_key=True)
    supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id'), nullable=False)
    
    work_date = db.Column(db.Date, nullable=False)
    check_in = db.Column(db.DateTime, nullable=False)
    check_out = db.Column(db.DateTime) # 未退勤の場合はNULL
    break_duration_minutes = db.Column(db.Integer, default=0, nullable=False)
    
    actual_work_minutes = db.Column(db.Integer, default=0, nullable=False) # 実働時間 (計算値)
    is_approved = db.Column(db.Boolean, default=False, nullable=False)
    
    supporter = db.relationship('Supporter', back_populates='timecards')


# ----------------------------------------------------
# 2. ExpenseCategoryMaster (勘定科目マスタ)
# ----------------------------------------------------
class ExpenseCategoryMaster(db.Model):
    __tablename__ = 'expense_category_master'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), nullable=False, unique=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    is_active = db.Column(db.Boolean, default=True)


# ----------------------------------------------------
# 3. ExpenseRecord (経費精算記録)
# ----------------------------------------------------
class ExpenseRecord(db.Model):
    __tablename__ = 'expense_records'
    id = db.Column(db.Integer, primary_key=True)
    supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id'), nullable=False)
    expense_date = db.Column(db.Date, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('expense_category_master.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=False)
    is_approved = db.Column(db.Boolean, default=False, nullable=False)
    approval_supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id'))

    supporter = db.relationship('Supporter', foreign_keys=[supporter_id], backref='expense_claims')
    approver = db.relationship('Supporter', foreign_keys=[approval_supporter_id], backref='expenses_approved')
    category = db.relationship('ExpenseCategoryMaster')
