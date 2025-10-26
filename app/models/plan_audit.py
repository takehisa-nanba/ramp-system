# app/models/plan_audit.py

from app.extensions import db
from datetime import datetime
from sqlalchemy.orm import relationship
from .core import User, Supporter # 例: 同じパッケージ内のcore.pyからインポート
from .master import StatusMaster, MeetingTypeMaster # 例: master.pyからインポート

# --- 個別支援計画、アセスメント、監査テーブル ---

class SupportPlan(db.Model):
    __tablename__ = 'support_plans'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # 法令責任者（サビ管）
    sabikan_id = db.Column(db.Integer, db.ForeignKey('supporters.id'))
    status_id = db.Column(db.Integer, db.ForeignKey('status_master.id')) # Draft, Approvedなど
    
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)

    user_consent_date = db.Column(db.DateTime) # 利用者サイン完了日時
    main_goal = db.Column(db.Text)             # 長期目標
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    remarks = db.Column(db.Text)

    # リレーションシップ（堅牢性対応）
    user = db.relationship('User', back_populates='support_plans')
    sabikan = db.relationship('Supporter', back_populates='plan_approvals', foreign_keys=[sabikan_id])
    status = db.relationship('StatusMaster', foreign_keys=[status_id])
    
    # 子要素（双方向リレーションシップの追加）
    short_term_goals = db.relationship('ShortTermGoal', back_populates='support_plan')
    monitorings = db.relationship('Monitoring', back_populates='plan')
    meeting_minutes = db.relationship('MeetingMinute', back_populates='support_plan') # MeetingMinuteとの連携


class ShortTermGoal(db.Model):
    __tablename__ = 'short_term_goals'
    id = db.Column(db.Integer, primary_key=True)
    support_plan_id = db.Column(db.Integer, db.ForeignKey('support_plans.id'), nullable=False)
    short_goal = db.Column(db.String(500), nullable=False) # 短期目標のテキスト
    
    # 期間を明確化
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)

    # リレーションシップ
    support_plan = db.relationship('SupportPlan', back_populates='short_term_goals')
    specific_goals = db.relationship('SpecificGoal', back_populates='short_term_goal')


class SpecificGoal(db.Model):
    __tablename__ = 'specific_goals'
    id = db.Column(db.Integer, primary_key=True)
    short_term_goal_id = db.Column(db.Integer, db.ForeignKey('short_term_goals.id'), nullable=False)
    task_name = db.Column(db.String(500), nullable=False) # 具体的タスクのテキスト
    
    priority = db.Column(db.Integer) # 優先度
    
    # 担当職員（FK to Supporter）
    responsible_supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id')) 
    template_id = db.Column(db.Integer, db.ForeignKey('service_templates.id'))

    is_custom_task = db.Column(db.Boolean, default=True) # テンプレートからの派生ではない場合

    # リレーションシップ（堅牢性対応）
    short_term_goal = db.relationship('ShortTermGoal', back_populates='specific_goals')
    template = db.relationship('ServiceTemplate', back_populates='specific_goals')
    responsible_supporter = db.relationship(
        'Supporter', 
        back_populates='responsible_tasks',
        foreign_keys=[responsible_supporter_id]
    )
    # 関連する日報記録
    daily_logs = db.relationship('DailyLog', back_populates='specific_goal')


class Assessment(db.Model):
    __tablename__ = 'assessments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # サビ管責任者
    sabikan_id = db.Column(db.Integer, db.ForeignKey('supporters.id'), nullable=False)
    assessment_date = db.Column(db.Date, nullable=False)
    
    assessment_detail = db.Column(db.Text) # アセスメント記録本体

    # リレーションシップ（堅牢性対応）
    user = db.relationship('User', back_populates='assessments')
    sabikan = db.relationship('Supporter', back_populates='assessment_approvals', foreign_keys=[sabikan_id])


class Monitoring(db.Model):
    __tablename__ = 'monitorings'
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('support_plans.id'), nullable=False)
    
    # サビ管責任者
    sabikan_id = db.Column(db.Integer, db.ForeignKey('supporters.id'), nullable=False)
    monitoring_date = db.Column(db.Date, nullable=False)
    
    progress_summary = db.Column(db.Text) # 進捗サマリー
    next_plan = db.Column(db.Text)        # 次期計画への提案

    # リレーションシップ（堅牢性対応）
    plan = db.relationship('SupportPlan', back_populates='monitorings')
    sabikan = db.relationship('Supporter', back_populates='monitoring_approvals', foreign_keys=[sabikan_id])


class MeetingMinute(db.Model):
    __tablename__ = 'meeting_minutes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # ★ 追加: どの支援計画に関連するか
    support_plan_id = db.Column(db.Integer, db.ForeignKey('support_plans.id'))
    
    meeting_date = db.Column(db.Date, nullable=False)
    meeting_type_id = db.Column(db.Integer, db.ForeignKey('meeting_type_master.id'))
    
    attendees = db.Column(db.String(500)) # 参加者リスト（カンマ区切りなど）
    summary = db.Column(db.Text)
    
    # リレーションシップ（堅牢性対応）
    user = db.relationship('User', back_populates='meeting_minutes')
    meeting_type = db.relationship('MeetingTypeMaster')
    support_plan = db.relationship('SupportPlan', back_populates='meeting_minutes')


class SystemLog(db.Model):
    __tablename__ = 'system_logs'
    id = db.Column(db.Integer, primary_key=True)
    
    action = db.Column(db.String(100), nullable=False) # 例: 'plan_consent', 'user_login'
    supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id'), nullable=False)
    
    # UserやSupportPlanへの参照をNullableで持つ
    user_id = db.Column(db.Integer, db.ForeignKey('users.id')) 
    support_plan_id = db.Column(db.Integer, db.ForeignKey('support_plans.id'))
    
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # リレーションシップ
    supporter = db.relationship('Supporter')
    user = db.relationship('User', back_populates='system_logs')
    support_plan = db.relationship('SupportPlan')
# 本棚Z：関係機関連絡先 (Contact)
class Contact(db.Model):
    __tablename__ = 'contacts'
    id = db.Column(db.Integer, primary_key=True)
    
    # 外部キー
    user_id = db.Column(db.Integer, db.ForeignKey('users.id')) # 特定の利用者に紐づく連絡先の場合 (任意)
    contact_category_id = db.Column(db.Integer, db.ForeignKey('contact_category_master.id'), nullable=False)
    government_office_id = db.Column(db.Integer, db.ForeignKey('government_offices.id')) # 行政機関との紐付け (任意)

    # データカラム
    organization_name = db.Column(db.String(150), nullable=False)
    contact_person = db.Column(db.String(100))
    phone_number = db.Column(db.String(20))
    email = db.Column(db.String(120))
    remarks = db.Column(db.Text)
    
    # 監査日時
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # リレーションシップ
    # 'User' 'ContactCategoryMaster' 'GovernmentOffice' は別ファイルにあるため、文字列で指定
    user = relationship('User', back_populates='contacts') 
    category = relationship('ContactCategoryMaster', back_populates='contacts') 
    government_office = relationship('GovernmentOffice', back_populates='contacts')