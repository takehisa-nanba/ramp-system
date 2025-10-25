# app/models.py
from app.extensions import db 
from datetime import datetime
from flask_bcrypt import generate_password_hash, check_password_hash # ★ 追加インポート ★
from sqlalchemy.orm import relationship # リレーションシップ用にインポート

# --- マスターテーブル群 ---

class StatusMaster(db.Model):
    __tablename__ = 'status_master'
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(50), nullable=False)

class ReferralSourceMaster(db.Model):
    __tablename__ = 'referral_source_master'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)

class RoleMaster(db.Model):
    __tablename__ = 'role_master'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)

class EmploymentTypeMaster(db.Model):
    __tablename__ = 'employment_type_master'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    
class WorkStyleMaster(db.Model):
    __tablename__ = 'work_style_master'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)

class DisclosureTypeMaster(db.Model):
    __tablename__ = 'disclosure_type_master'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)

class ContactCategoryMaster(db.Model):
    __tablename__ = 'contact_category_master'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)

class AttendanceStatusMaster(db.Model):
    __tablename__ = 'attendance_status_master'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)

class MeetingTypeMaster(db.Model):
    __tablename__ = 'meeting_type_master'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)

# --- 主要な本棚（テーブル）群 ---

# 本棚③：職員マスタ (Supporters)
class Supporter(db.Model):
    __tablename__ = 'supporters'
    id = db.Column(db.Integer, primary_key=True)
    last_name = db.Column(db.String(50), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name_kana = db.Column(db.String(50))
    first_name_kana = db.Column(db.String(50))
    
    # ★ RBAC実装のための認証情報 ★
    email = db.Column(db.String(120), unique=True, nullable=True) 
    password_hash = db.Column(db.String(256), nullable=True)
    
    role_id = db.Column(db.Integer, db.ForeignKey('role_master.id'))
    hire_date = db.Column(db.Date)
    is_active = db.Column(db.Boolean, default=True)
    remarks = db.Column(db.Text)
    
    # ★ パスワード操作メソッドを追加（app/extensions.pyのbcryptを利用） ★
    def set_password(self, password):
        from .extensions import bcrypt
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        from .extensions import bcrypt
        return bcrypt.check_password_hash(self.password_hash, password)

# 本棚①：見込み利用者 (Prospects)
class Prospect(db.Model):
    __tablename__ = 'prospects'
    id = db.Column(db.Integer, primary_key=True)
    status_id = db.Column(db.Integer, db.ForeignKey('status_master.id'))
    last_name = db.Column(db.String(50), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name_kana = db.Column(db.String(50))
    first_name_kana = db.Column(db.String(50))
    phone_number = db.Column(db.String(20))
    email = db.Column(db.String(100))
    inquiry_date = db.Column(db.Date, default=datetime.utcnow)
    referral_source_id = db.Column(db.Integer, db.ForeignKey('referral_source_master.id'))
    referral_source_other = db.Column(db.String(200))
    notes = db.Column(db.Text)
    next_action_date = db.Column(db.Date)
    remarks = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # status = relationship('StatusMaster', foreign_keys=[status_id]) # リレーションは後で定義
    # referral_source = relationship('ReferralSourceMaster', foreign_keys=[referral_source_id]) # リレーションは後で定義

# 本棚②：利用者マスタ (Users)
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    prospect_id = db.Column(db.Integer, db.ForeignKey('prospects.id'), unique=True)
    status_id = db.Column(db.Integer, db.ForeignKey('status_master.id'))
    last_name = db.Column(db.String(50), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name_kana = db.Column(db.String(50))
    first_name_kana = db.Column(db.String(50))
    primary_supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id'))
    handbook_type = db.Column(db.String(50))
    primary_disorder = db.Column(db.String(200))
    remarks = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # ★ 既存の User モデルに追加された連絡先・属性情報 ★
    birth_date = db.Column(db.Date) # 元々不足していた項目を追加
    email = db.Column(db.String(120), unique=True) # 連絡用
    phone = db.Column(db.String(20)) # 元々不足していた項目を追加

    # ★ 新規追加：電子サイン用 PINコード（ハッシュ化） ★
    pin_hash = db.Column(db.String(128)) 

    # ★ PINコード設定用のメソッドを追加 ★
    def set_pin(self, pin):
        """ PINコードをハッシュ化して保存する """
        # PINコードは4桁の数字などを想定し、強力なハッシュ化で保護
        self.pin_hash = generate_password_hash(pin).decode('utf-8')

    def check_pin(self, pin):
        """ 入力されたPINコードがハッシュと一致するかチェックする """
        if self.pin_hash is None:
            return False
        return check_password_hash(self.pin_hash, pin)

# 本棚⑪：アセスメント記録 (Assessment)
class Assessment(db.Model):
    __tablename__ = 'assessments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    sabikan_id = db.Column(db.Integer, db.ForeignKey('supporters.id'), nullable=False)
    assessment_date = db.Column(db.Date, default=datetime.utcnow)
    summary = db.Column(db.Text)
    notes = db.Column(db.Text)
    
# 本棚⑬：事業所テンプレート (ServiceTemplate)
class ServiceTemplate(db.Model):
    __tablename__ = 'service_templates'
    id = db.Column(db.Integer, primary_key=True)
    template_name = db.Column(db.String(100), nullable=False, unique=True)
    category = db.Column(db.String(50))
    description = db.Column(db.Text)

# 本棚⑧：個別支援計画 (Support Plans)
class SupportPlan(db.Model):
    __tablename__ = 'support_plans'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status_id = db.Column(db.Integer, db.ForeignKey('status_master.id'))
    plan_date = db.Column(db.Date)
    
    # ★ 法的担保の追加 ★
    sabikan_id = db.Column(db.Integer, db.ForeignKey('supporters.id')) # 責任者ID
    start_date = db.Column(db.Date) # 計画全体の開始日
    end_date = db.Column(db.Date)   # 計画全体の終了日
    
    # ★ 支援の質向上のための追加 ★
    main_goal = db.Column(db.Text)
    comprehensive_policy = db.Column(db.Text) # 総合的な支援方針
    user_strengths = db.Column(db.Text)      # 本人の強み
    user_challenges = db.Column(db.Text)     # 本人の課題

    supporter_comments = db.Column(db.Text)
    user_consent_date = db.Column(db.DateTime) # ★ カラム名を API に合わせ、型を DateTime に変更 ★
    remarks = db.Column(db.Text)
    
# 本棚⑭：短期目標 (ShortTermGoal) - SupportPlanの子
class ShortTermGoal(db.Model):
    __tablename__ = 'short_term_goals'
    id = db.Column(db.Integer, primary_key=True)
    support_plan_id = db.Column(db.Integer, db.ForeignKey('support_plans.id'), nullable=False)
    short_goal = db.Column(db.String(500), nullable=False)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    
# 本棚⑮：具体的な目標・タスク (SpecificGoal) - ShortTermGoalの子
class SpecificGoal(db.Model):
    __tablename__ = 'specific_goals'
    id = db.Column(db.Integer, primary_key=True)
    short_term_goal_id = db.Column(db.Integer, db.ForeignKey('short_term_goals.id'), nullable=False)
    task_name = db.Column(db.String(500), nullable=False)
    priority = db.Column(db.Integer)
    responsible_supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id'))
    template_id = db.Column(db.Integer, db.ForeignKey('service_templates.id'))
    is_custom_task = db.Column(db.Boolean, default=True)

# 本棚⑨：日々の支援記録 (Daily Logs)
class DailyLog(db.Model):
    __tablename__ = 'daily_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id'))
    activity_date = db.Column(db.Date, nullable=False)
    attendance_status_id = db.Column(db.Integer, db.ForeignKey('attendance_status_master.id'))
    
    # ★ 追加：具体的な目標と日報の連携 ★
    specific_goal_id = db.Column(db.Integer, db.ForeignKey('specific_goals.id')) 
    
    mood_hp = db.Column(db.Integer)
    mood_mp = db.Column(db.Integer)
    activity_summary = db.Column(db.Text)
    user_voice = db.Column(db.Text)
    supporter_insight = db.Column(db.Text)
    remarks = db.Column(db.Text)


# 本棚⑫：モニタリング記録 (Monitoring)
class Monitoring(db.Model):
    __tablename__ = 'monitorings'
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('support_plans.id'), nullable=False)
    sabikan_id = db.Column(db.Integer, db.ForeignKey('supporters.id'), nullable=False)
    monitoring_date = db.Column(db.Date, default=datetime.utcnow)
    progress_score = db.Column(db.Integer)
    evaluation = db.Column(db.Text)
    next_plan = db.Column(db.Text)
    
# 本棚⑯：コメント・フィードバック (Comment)
class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    support_plan_id = db.Column(db.Integer, db.ForeignKey('support_plans.id'), nullable=False)
    supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# 本棚⑩：支援会議議事録 (Meeting Minutes)
class MeetingMinute(db.Model):
    __tablename__ = 'meeting_minutes'
    id = db.Column(db.Integer, primary_key=True)
    support_plan_id = db.Column(db.Integer, db.ForeignKey('support_plans.id'))
    meeting_date = db.Column(db.DateTime)
    meeting_type_id = db.Column(db.Integer, db.ForeignKey('meeting_type_master.id'))
    attendees = db.Column(db.Text)
    agenda = db.Column(db.Text)
    decisions = db.Column(db.Text)
    next_actions = db.Column(db.Text)
    remarks = db.Column(db.Text)

# 本棚④：契約・受給者証情報 (Contracts & Certificates)
class ContractCertificate(db.Model):
    __tablename__ = 'contracts_certificates'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    certificate_number = db.Column(db.String(100))
    valid_from = db.Column(db.Date)
    valid_to = db.Column(db.Date)
    max_burden_amount = db.Column(db.Integer)
    supply_amount = db.Column(db.Integer)
    remarks = db.Column(db.Text)

# 本棚⑤：就職・定着情報 (Employments)
class Employment(db.Model):
    __tablename__ = 'employments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    company_name = db.Column(db.String(100))
    department = db.Column(db.String(100))
    contact_person = db.Column(db.String(100))
    contact_person_kana = db.Column(db.String(100))
    address = db.Column(db.String(200))
    phone_number = db.Column(db.String(20))
    email = db.Column(db.String(100))
    start_date = db.Column(db.Date)
    employment_type_id = db.Column(db.Integer, db.ForeignKey('employment_type_master.id'))
    work_style_id = db.Column(db.Integer, db.ForeignKey('work_style_master.id'))
    disclosure_type_id = db.Column(db.Integer, db.ForeignKey('disclosure_type_master.id'))
    remarks = db.Column(db.Text)

# 本棚⑥：関係機関 (Contacts)
class Contact(db.Model):
    __tablename__ = 'contacts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    category_id = db.Column(db.Integer, db.ForeignKey('contact_category_master.id'))
    organization_name = db.Column(db.String(100))
    contact_person = db.Column(db.String(100))
    address = db.Column(db.String(200))
    phone_number = db.Column(db.String(20))
    email = db.Column(db.String(100))
    remarks = db.Column(db.Text)

# 本棚⑦：行政機関マスタ (Government Offices)
class GovernmentOffice(db.Model):
    __tablename__ = 'government_offices'
    id = db.Column(db.Integer, primary_key=True)
    municipality_name = db.Column(db.String(100))
    municipality_code = db.Column(db.String(20))
    department = db.Column(db.String(100))
    contact_person = db.Column(db.String(100))
    address = db.Column(db.String(200))
    phone_number = db.Column(db.String(20))
    email = db.Column(db.String(100))
    remarks = db.Column(db.Text)

# 本棚⑯：システム操作ログ（監査証跡）
class SystemLog(db.Model):
    __tablename__ = 'system_logs'
    id = db.Column(db.Integer, primary_key=True)
    
    # ログ種別 ('plan_consent', 'plan_approval', 'user_login'など)
    action = db.Column(db.String(100), nullable=False)
    
    # 実行した職員（サビ管）のID
    supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id'), nullable=False)
    
    # 対象の利用者ID（同意操作の場合は利用者）
    target_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) 
    
    # 対象の計画ID（同意操作の場合は計画）
    target_plan_id = db.Column(db.Integer, db.ForeignKey('support_plans.id'), nullable=True)
    
    # 操作日時
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # JSON形式の追加情報（オプション）
    details = db.Column(db.Text)

# ★ リレーションシップ定義（循環参照を避けるため、クラス定義後に実行） ★
# Supporter と RoleMaster のリレーションシップ
Supporter.role = relationship('RoleMaster', backref='supporters')

# SupportPlan と ShortTermGoal, Monitoring のリレーションシップ
SupportPlan.short_term_goals = relationship('ShortTermGoal', backref='plan', lazy=True)
SupportPlan.monitorings = relationship('Monitoring', backref='plan', lazy=True)
SupportPlan.comments = relationship('Comment', backref='plan', lazy=True)

# ShortTermGoal と SpecificGoal のリレーションシップ
ShortTermGoal.specific_goals = relationship('SpecificGoal', backref='short_term_goal', lazy=True)