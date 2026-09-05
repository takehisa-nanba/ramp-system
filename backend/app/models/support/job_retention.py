# backend/app/models/support/job_retention.py

from backend.app.extensions import db
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, DateTime, Text, func, UniqueConstraint, Index
from sqlalchemy.orm import relationship
import dateutil.relativedelta
import datetime
from typing import Optional, Dict, Any

# ====================================================================
# 1. JobRetentionContract (就労定着支援 - 契約)
# ====================================================================
class JobRetentionContract(db.Model):
    """
    就労定着支援の契約情報。
    就職後の定着支援期間（最長3年）とステータスを管理する独立ドメイン。
    """
    __tablename__ = 'job_retention_contracts'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    office_service_configuration_id = Column(Integer, ForeignKey('office_service_configurations.id'), nullable=False, index=True)
    
    # 契約期間
    contract_start_date = Column(Date, nullable=False) # 契約開始日
    contract_end_date = Column(Date, nullable=False)   # 契約終了日 (最長3年)
    
    # ステータス: ACTIVE (支援中), TRANSITION_PENDING (転職移行期間), COMPLETED (満了終了), TERMINATED (中途終了)
    status = Column(String(30), nullable=False, default='ACTIVE', index=True)
    
    # 企業参加・同意設定
    is_company_involved = Column(Boolean, default=False, nullable=False) # 企業連携あり/なし (初期値False)
    consent_status = Column(String(50), default='NOT_SET', nullable=False) # 同意状況 (初期値NOT_SET: Fail Closed)
    
    # 補足・特記事項
    contract_details = Column(Text, nullable=True)
    
    # タイムスタンプ
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # --- リレーションシップ ---
    user = relationship('User', back_populates='retention_contracts')
    office_service_configuration = relationship('OfficeServiceConfiguration', foreign_keys=[office_service_configuration_id])
    
    # 就労エピソード履歴 (1対多)
    episodes = relationship('RetentionEmploymentEpisode', back_populates='contract', order_by='RetentionEmploymentEpisode.episode_number', cascade="all, delete-orphan")
    
    # 支援計画版履歴 (1対多)
    plans = relationship('RetentionSupportPlan', back_populates='contract', order_by='RetentionSupportPlan.version.asc()', cascade="all, delete-orphan")

    # 一次情報ログ
    voice_logs = relationship('RetentionUserVoiceLog', back_populates='contract', order_by='desc(RetentionUserVoiceLog.logged_at)', cascade="all, delete-orphan")
    employer_feedback_logs = relationship('RetentionEmployerFeedbackLog', back_populates='contract', order_by='desc(RetentionEmployerFeedbackLog.logged_at)', cascade="all, delete-orphan")
    action_logs = relationship('RetentionSupportActionLog', back_populates='contract', order_by='desc(RetentionSupportActionLog.action_date)', cascade="all, delete-orphan")
    monthly_reports = relationship('MonthlyRetentionReport', back_populates='contract', order_by='desc(MonthlyRetentionReport.report_year_month)', cascade="all, delete-orphan")
    
    # 既存コードとの互換用 (旧JobRetentionRecord)
    retention_records = relationship('JobRetentionRecord', back_populates='contract', lazy='dynamic', cascade="all, delete-orphan")


# ====================================================================
# 2. RetentionEmploymentEpisode (就労エピソード履歴)
# ====================================================================
class RetentionEmploymentEpisode(db.Model):
    """
    定着支援期間中の就労先ごとのエピソード履歴。
    退職の事実だけで自動終了せず、前職と次職の連続性を一次情報として保持する。
    """
    __tablename__ = 'retention_employment_episodes'

    id = Column(Integer, primary_key=True)
    contract_id = Column(Integer, ForeignKey('job_retention_contracts.id'), nullable=False, index=True)
    
    episode_number = Column(Integer, nullable=False, default=1) # 第1期, 第2期...
    employer_id = Column(Integer, ForeignKey('employer_master.id'), nullable=True, index=True) # 既存企業マスタ
    workplace_name = Column(String(200), nullable=False) # 勤務先企業・事業所名
    department_name = Column(String(100), nullable=True) # 配属部署
    job_title = Column(String(100), nullable=True)        # 職種・業務内容
    
    job_start_date = Column(Date, nullable=False) # 就職日
    job_end_date = Column(Date, nullable=True)    # 退職日 (在職中はNULL)
    
    work_conditions = Column(Text, nullable=True) # 勤務形態・労働時間・配慮事項など
    resignation_reason = Column(Text, nullable=True) # 退職理由・経緯
    
    previous_episode_id = Column(Integer, ForeignKey('retention_employment_episodes.id'), nullable=True)
    
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    contract = relationship('JobRetentionContract', back_populates='episodes')
    previous_episode = relationship('RetentionEmploymentEpisode', remote_side=[id])


# ====================================================================
# 3. RetentionUserVoiceLog (本人の生の声・行動ログ) — 一次情報
# ====================================================================
class RetentionUserVoiceLog(db.Model):
    """
    本人がスマホ等から日記感覚で短時間で残す一次情報ログ。
    数値スコアの強要は行わず、生の声・困りごと・対処を保持する。
    """
    __tablename__ = 'retention_user_voice_logs'

    id = Column(Integer, primary_key=True)
    contract_id = Column(Integer, ForeignKey('job_retention_contracts.id'), nullable=False, index=True)
    
    logged_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    
    raw_voice = Column(Text, nullable=True)           # 最近あったこと・生の声・つぶやき
    trouble_point = Column(Text, nullable=True)       # 困ったこと・気になったこと
    success_point = Column(Text, nullable=True)       # うまくいったこと・嬉しかったこと
    self_coping_action = Column(Text, nullable=True)  # 自分でやってみた対処・工夫
    self_coping_result = Column(Text, nullable=True)  # その結果どうだったか
    
    needs_help = Column(Boolean, default=False, nullable=False) # 支援員に相談したいか
    help_topic = Column(String(200), nullable=True)             # 相談したい内容（任意）
    
    # 入力元プロベナンス: USER_DIRECT (本人直接入力), STAFF_HEARING (支援員聞き取り等)
    input_channel = Column(String(30), default='USER_DIRECT', nullable=False)
    
    created_at = Column(DateTime, default=func.now(), nullable=False)

    contract = relationship('JobRetentionContract', back_populates='voice_logs')


# ====================================================================
# 4. RetentionEmployerFeedbackLog (企業の声・職場観測) — 一次情報 (補助)
# ====================================================================
class RetentionEmployerFeedbackLog(db.Model):
    """
    企業担当者から提供される職場の様子・フィードバック（本人同意に基づく補助情報）。
    """
    __tablename__ = 'retention_employer_feedback_logs'

    id = Column(Integer, primary_key=True)
    contract_id = Column(Integer, ForeignKey('job_retention_contracts.id'), nullable=False, index=True)
    
    logged_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    contact_person = Column(String(100), nullable=True) # 企業担当者名・役職
    
    workplace_observation = Column(Text, nullable=True)   # 職場で気になっていること・勤務の様子
    positive_changes = Column(Text, nullable=True)        # 本人の良い変化・評価
    direct_coordination_status = Column(Text, nullable=True) # 本人との直接の調整状況
    consultation_topic = Column(Text, nullable=True)      # 支援員へ共有・相談したいこと
    
    created_at = Column(DateTime, default=func.now(), nullable=False)

    contract = relationship('JobRetentionContract', back_populates='employer_feedback_logs')


# ====================================================================
# 5. RetentionSupportActionLog (支援員の面談・訪問・介入記録) — 一次情報
# ====================================================================
class RetentionSupportActionLog(db.Model):
    """
    支援員による月次面談・企業訪問・調整などの実施記録。
    1回の支援実施で「企業訪問＋本人面談＋調整」など複数の実施内容を保持可能。
    """
    __tablename__ = 'retention_support_action_logs'

    id = Column(Integer, primary_key=True)
    contract_id = Column(Integer, ForeignKey('job_retention_contracts.id'), nullable=False, index=True)
    supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=False, index=True)
    
    action_date = Column(Date, nullable=False, index=True)
    
    # 複数支援種別フラグ (1回で訪問＋面談＋調整を同時に実施可能)
    has_user_interview = Column(Boolean, default=False, nullable=False) # 本人面談を実施したか
    interview_method = Column(String(30), nullable=True) # 'FACE_TO_FACE', 'ONLINE', 'PHONE'
    
    has_company_visit = Column(Boolean, default=False, nullable=False)  # 企業訪問を実施したか
    has_coordination = Column(Boolean, default=False, nullable=False)   # 関係機関・企業等との連絡・調整
    has_other_support = Column(Boolean, default=False, nullable=False)  # その他支援
    
    # 現場で確認・実施した内容（一次情報）
    confirmed_situation = Column(Text, nullable=False) # 面談・訪問で確認した状況（就労面・生活面）
    provided_support = Column(Text, nullable=False)    # 実際に行った支援・調整内容
    
    # 本人の対処と支援員の介在境界（客観的事実）
    user_action_observed = Column(Text, nullable=True)         # 本人がどこまで自分で対処したか
    staff_intervention_boundary = Column(Text, nullable=True)  # 支援員がどこから介在したか
    
    next_step = Column(Text, nullable=True) # 次回予定・確認事項
    
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    contract = relationship('JobRetentionContract', back_populates='action_logs')
    supporter = relationship('Supporter', foreign_keys=[supporter_id])


# ====================================================================
# 6. MonthlyRetentionReport (月次就労定着支援レポート)
# ====================================================================
class MonthlyRetentionReport(db.Model):
    """
    公式の就労定着支援状況報告書の各項目へ一次情報をルールベースで構造化マッピング。
    本人・企業・支援員の一次情報そのものは変更・上書きせず、報告書項目として保持・微調整する。
    """
    __tablename__ = 'monthly_retention_reports'
    __table_args__ = (
        UniqueConstraint('contract_id', 'report_year_month', name='uq_monthly_retention_report_contract_month'),
    )

    id = Column(Integer, primary_key=True)
    contract_id = Column(Integer, ForeignKey('job_retention_contracts.id'), nullable=False, index=True)
    report_year_month = Column(String(7), nullable=False, index=True) # 'YYYY-MM'
    
    status = Column(String(20), default='DRAFT', nullable=False) # 'DRAFT', 'FINALIZED'
    
    # 内部整理項目（一次情報のまとめ）
    interview_records = Column(Text, nullable=True)         # 面談実施状況（実施日、方法、時間等）
    company_visit_records = Column(Text, nullable=True)     # 企業訪問実施状況（実施日、対応者、職場状況）
    work_status_summary = Column(Text, nullable=True)       # 就労状況（勤務時間・出勤、業務内容・環境変化）
    life_status_summary = Column(Text, nullable=True)       # 生活状況（生活リズム、健康管理等）
    user_coping_summary = Column(Text, nullable=True)       # 本人の状況・自力対処の状況・本人の意向
    employer_feedback_summary = Column(Text, nullable=True) # 企業の状況・評価・要望
    support_details = Column(Text, nullable=True)           # 今月実施した支援・調整内容
    future_support_policy = Column(Text, nullable=True)     # 今後の支援方針・次回課題
    
    # 公式帳票標準項目（就労定着支援状況報告書・実績記録票）
    support_goal = Column(Text, nullable=True)              # 当月の主な支援目標
    support_content = Column(Text, nullable=True)           # 支援実施内容
    support_result = Column(Text, nullable=True)            # 支援結果
    future_support_plan = Column(Text, nullable=True)       # 今後の支援内容
    stakeholder_efforts = Column(Text, nullable=True)       # 対象者・事業主・関係機関等の取組
    sharing_notes = Column(Text, nullable=True)             # 共有事項
    
    created_by_id = Column(Integer, ForeignKey('supporters.id'), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    contract = relationship('JobRetentionContract', back_populates='monthly_reports')
    created_by = relationship('Supporter', foreign_keys=[created_by_id])


# ====================================================================
# 7. JobRetentionRecord (既存互換モデル)
# ====================================================================
class JobRetentionRecord(db.Model):
    """旧JobRetentionRecord互換用"""
    __tablename__ = 'job_retention_records'
    
    id = Column(Integer, primary_key=True)
    contract_id = Column(Integer, ForeignKey('job_retention_contracts.id'), nullable=False, index=True)
    record_date = Column(Date, nullable=False)
    support_method = Column(String(50), nullable=False) 
    support_details = Column(Text, nullable=False)
    supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=False)
    document_url = Column(String(500))
    
    contract = relationship('JobRetentionContract', back_populates='retention_records')
    supporter = relationship('Supporter', foreign_keys=[supporter_id])


# ====================================================================
# 8. RetentionSupportPlan (就労定着支援計画 - 版管理)
# ====================================================================
def calculate_max_review_deadline(base_date: datetime.date) -> datetime.date:
    """見直し基準日から暦上の6か月後（上限）を算出"""
    return base_date + dateutil.relativedelta.relativedelta(months=6)


class RetentionSupportPlan(db.Model):
    """
    就労定着支援計画の版管理テーブル。
    大まかな支援目標と次回見直し期限を保持し、随時見直し履歴を残す。
    """
    __tablename__ = 'retention_support_plans'
    __table_args__ = (
        UniqueConstraint('contract_id', 'version', name='uq_retention_plan_contract_version'),
        Index(
            'uq_active_retention_plan',
            'contract_id',
            unique=True,
            postgresql_where=db.text("status = 'ACTIVE'"),
            sqlite_where=db.text("status = 'ACTIVE'")
        ),
    )

    id = Column(Integer, primary_key=True)
    contract_id = Column(Integer, ForeignKey('job_retention_contracts.id', ondelete='CASCADE'), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)

    # 支援方針
    overall_support_goal = Column(Text, nullable=False) # 現在の大まかな支援目標

    # 期間・見直し管理
    start_date = Column(Date, nullable=False)           # 当該版の適用開始日
    review_date = Column(Date, nullable=True)           # 見直し実施日
    review_reason = Column(Text, nullable=True)         # 見直し理由
    next_review_deadline = Column(Date, nullable=False) # 次回見直し期限 (上限: 基準日+暦上6か月)

    # ステータス: ACTIVE (現在有効・1契約につき1件のみ), ARCHIVED (過去履歴)
    status = Column(String(20), nullable=False, default='ACTIVE', index=True)

    created_by_id = Column(Integer, ForeignKey('supporters.id'), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    contract = relationship('JobRetentionContract', back_populates='plans')
    created_by = relationship('Supporter', foreign_keys=[created_by_id])

    def compute_deadline_status(self, today: Optional[datetime.date] = None) -> Dict[str, Any]:
        """次回見直し期限のステータスと残日数を計算"""
        if today is None:
            today = datetime.date.today()
        days_diff = (self.next_review_deadline - today).days

        if days_diff > 14:
            status_code = 'NORMAL'
        elif days_diff > 0:
            status_code = 'APPROACHING'
        elif days_diff == 0:
            status_code = 'DUE_TODAY'
        elif days_diff >= -30:
            status_code = 'OVERDUE_WITHIN_MONTH'
        else:
            status_code = 'OVERDUE_BILLING_RISK'

        return {
            "status_code": status_code,
            "days_diff": days_diff,
            "next_review_deadline": self.next_review_deadline.isoformat(),
            "is_overdue": days_diff < 0
        }