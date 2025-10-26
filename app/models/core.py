# app/models/core.py

from app.extensions import db, bcrypt
from datetime import datetime
from sqlalchemy.orm import relationship
from sqlalchemy import UniqueConstraint
# ★ 修正: 他のモデルファイルからのインポートが必要な場合は、ここで絶対パスを使用 ★
# from .master import RoleMaster, StatusMaster # 例: 同じパッケージ内のmaster.pyからインポート

# --- コアユーザーおよび活動記録テーブル ---

class Supporter(db.Model):
    __tablename__ = 'supporters'
    id = db.Column(db.Integer, primary_key=True)
    last_name = db.Column(db.String(50), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    # ★ 追加カラム（網羅性対応）
    last_name_kana = db.Column(db.String(50))
    first_name_kana = db.Column(db.String(50))
    
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(128), nullable=False)
    
    # ★ 追加カラム（既存コードで利用）
    hire_date = db.Column(db.Date)
    is_active = db.Column(db.Boolean, default=True)

    role_id = db.Column(db.Integer, db.ForeignKey('role_master.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) # ★ この行が必須 ★
    remarks = db.Column(db.Text)

    # リレーションシップ（堅牢性対応）
    role = db.relationship('RoleMaster', back_populates='supporters')
    # 主担当している利用者一覧（双方向リレーションシップの追加）
    primary_users = db.relationship(
        'User', 
        back_populates='primary_supporter',
        foreign_keys='User.primary_supporter_id'
    )
    # 支援計画のサビ管責任者としての承認一覧
    plan_approvals = db.relationship(
        'SupportPlan',
        back_populates='sabikan',
        foreign_keys='SupportPlan.sabikan_id'
    )
    primary_users = db.relationship('User', backref='primary_supporter', lazy=True)

    # ★ 修正1: 自分が作成した日報一覧 (DailyLog.supporter_id を参照することを明示) ★
    daily_logs = db.relationship(
        'DailyLog', 
        backref='creator', 
        lazy=True, 
        foreign_keys='[DailyLog.supporter_id]'
    )

    # ★ 修正2: 自分が承認した日報一覧 (DailyLog.approved_by_supporter_id を参照することを明示) ★
    approved_daily_logs = db.relationship(
        'DailyLog',
        backref='approver',
        lazy=True,
        foreign_keys='[DailyLog.approved_by_supporter_id]'
    )
    onsite_daily_logs = db.relationship('DailyLog', back_populates='supporter_on_site')
    # アセスメント承認一覧
    assessment_approvals = db.relationship('Assessment', back_populates='sabikan', foreign_keys='Assessment.sabikan_id')
    # モニタリング評価一覧
    monitoring_approvals = db.relationship('Monitoring', back_populates='sabikan', foreign_keys='Monitoring.sabikan_id')
    # 担当タスク一覧
    responsible_tasks = db.relationship('SpecificGoal', back_populates='responsible_supporter', foreign_keys='SpecificGoal.responsible_supporter_id')
    
    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    last_name = db.Column(db.String(50), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    # ★ 追加カラム（網羅性対応）
    last_name_kana = db.Column(db.String(50))
    first_name_kana = db.Column(db.String(50))
    birth_date = db.Column(db.Date)
    gender = db.Column(db.String(10)) # Male, Female, Other
    postal_code = db.Column(db.String(10))
    address = db.Column(db.String(255))
    phone_number = db.Column(db.String(20))

    pin_hash = db.Column(db.String(128)) # 電子サイン用
    email = db.Column(db.String(120), unique=True) # 連絡用
    
    primary_supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id'))
    status_id = db.Column(db.Integer, db.ForeignKey('status_master.id'))
    
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) # ★ この行が必須 ★
    remarks = db.Column(db.Text)

    # リレーションシップ（堅牢性対応）
    status = db.relationship('StatusMaster') # 汎用ステータス
    primary_supporter = db.relationship(
        'Supporter', 
        back_populates='primary_users',
        foreign_keys='User.primary_supporter_id'
    )
    # 利用者のデータ一覧（双方向リレーションシップの追加）
    attendance_plans = db.relationship('AttendancePlan', back_populates='user')
    daily_logs = db.relationship('DailyLog', back_populates='user')
    support_plans = db.relationship('SupportPlan', back_populates='user')
    assessments = db.relationship('Assessment', back_populates='user')
    meeting_minutes = db.relationship('MeetingMinute', back_populates='user')
    system_logs = db.relationship('SystemLog', back_populates='user')
    contacts = relationship('Contact', back_populates='user')

    def set_pin(self, pin):
        # PINのハッシュ化は、必要に応じて bcrypt ではなく別のシンプルなハッシュ関数を使用
        self.pin_hash = bcrypt.generate_password_hash(pin).decode('utf-8')

    def check_pin(self, pin):
        return bcrypt.check_password_hash(self.pin_hash, pin)


class Prospect(db.Model):
    __tablename__ = 'prospects'
    id = db.Column(db.Integer, primary_key=True)
    last_name = db.Column(db.String(50), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    # ★ 追加カラム（網羅性対応）
    last_name_kana = db.Column(db.String(50))
    first_name_kana = db.Column(db.String(50))
    contact_info = db.Column(db.Text) # 電話、メール、メモなどを記録
    
    status_id = db.Column(db.Integer, db.ForeignKey('status_master.id'))
    referral_source_id = db.Column(db.Integer, db.ForeignKey('referral_source_master.id'))
    
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) # ★ この行が必須 ★
    remarks = db.Column(db.Text)

    # リレーションシップ
    status = db.relationship('StatusMaster', foreign_keys=[status_id])
    referral_source = db.relationship('ReferralSourceMaster')


class AttendancePlan(db.Model):
    __tablename__ = 'attendance_plans'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    planned_date = db.Column(db.Date, nullable=False)
    planned_check_in = db.Column(db.String(5), nullable=False) # "10:00"
    planned_check_out = db.Column(db.String(5))
    is_recurring = db.Column(db.Boolean, default=False)
    remarks = db.Column(db.Text)

    # リレーションシップ
    user = db.relationship('User', back_populates='attendance_plans')
    
    # 複合ユニーク制約: ユーザーは同じ日に一つの予定のみ
    __table_args__ = (
        UniqueConstraint('user_id', 'planned_date', name='uq_user_date'),
    )


class DailyLog(db.Model):
    __tablename__ = 'daily_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id'))
    
    activity_date = db.Column(db.Date, nullable=False)
    
    attendance_status_id = db.Column(db.Integer, db.ForeignKey('attendance_status_master.id'))
    service_location_id = db.Column(db.Integer, db.ForeignKey('service_location_master.id')) # ★ 追加
    preparation_activity_id = db.Column(db.Integer, db.ForeignKey('preparation_activity_master.id'))
    
    # サービス提供時間（分）
    service_duration_min = db.Column(db.Integer) 

    # スタッフの出退勤時刻（実績確定時刻）
    staff_check_in = db.Column(db.DateTime)
    staff_check_out = db.Column(db.DateTime)
    
    # SOAP形式の記録
    activity_summary = db.Column(db.Text) # Objective (O) + Assessment (A) + Plan (P)
    user_voice = db.Column(db.Text)       # Subjective (S)
    supporter_insight = db.Column(db.Text) # 支援員の気づき
    
    check_in_time = db.Column(db.DateTime)      # 利用者打刻の通所時刻
    check_out_time = db.Column(db.DateTime)     # 利用者打刻の退所時刻
    staff_check_in = db.Column(db.DateTime)     # スタッフ承認/入力の通所実績
    staff_check_out = db.Column(db.DateTime)    # スタッフ承認/入力の退所実績
    service_duration_min = db.Column(db.Integer) # 確定した提供時間（分）
    approved_by_id = db.Column(db.Integer, db.ForeignKey('supporters.id')) # 実績承認職員

    supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id')) # 記録職員
    approved_by_id = db.Column(db.Integer, db.ForeignKey('supporters.id')) # 実績承認職員
    supporter_on_site_id = db.Column(db.Integer, db.ForeignKey('supporters.id')) # 同行職員

    # リレーションシップ
    user = db.relationship('User', back_populates='daily_logs')
    supporter = db.relationship(
        'Supporter', 
        foreign_keys='[DailyLog.supporter_id]', # DailyLog.supporter_id を使用
        back_populates='daily_logs'
    )
    approved_by = db.relationship(
        'Supporter', 
        foreign_keys='[DailyLog.approved_by_id]', # DailyLog.approved_by_id を使用
        back_populates='approved_daily_logs'
    )
    supporter_on_site = db.relationship(
        'Supporter', 
        foreign_keys='[DailyLog.supporter_on_site_id]', # DailyLog.supporter_on_site_id を使用
        back_populates='onsite_daily_logs'
    )
    attendance_status = db.relationship('AttendanceStatusMaster', back_populates='daily_logs')
    service_location = db.relationship('ServiceLocationMaster', back_populates='daily_logs')
    preparation_activity = db.relationship('PreparationActivityMaster', back_populates='daily_logs')
    
    # 具体目標との紐づけ
    specific_goal_id = db.Column(db.Integer, db.ForeignKey('specific_goals.id'))
    specific_goal = db.relationship('SpecificGoal', back_populates='daily_logs')
    # タイムスタンプ
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) # ★ この行が必須 ★
    remarks = db.Column(db.Text)
