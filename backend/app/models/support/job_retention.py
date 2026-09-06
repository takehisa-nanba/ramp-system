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
def calculate_plan_end_date(start_date: datetime.date) -> datetime.date:
    """計画開始日から暦上の終了予定日（原則: start_date + 6 calendar months - 1 day）を算出"""
    return start_date + dateutil.relativedelta.relativedelta(months=6) - datetime.timedelta(days=1)


def calculate_max_review_deadline(base_date: datetime.date) -> datetime.date:
    """後方互換用: calculate_plan_end_date と同等"""
    return calculate_plan_end_date(base_date)


class RetentionSupportPlan(db.Model):
    """
    就労定着支援計画の版管理テーブル。
    大まかな支援目標と計画終了予定日を保持し、随時見直し履歴を残す。
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
    review_date = Column(Date, nullable=True)           # 見直し実施日（随時見直し時）
    review_reason = Column(Text, nullable=True)         # 見直し理由
    plan_end_date = Column(Date, nullable=False)        # 当該計画版の終了予定日 (原則: start_date + 6 calendar months - 1 day)

    # ステータス: ACTIVE (現在有効・1契約につき1件のみ), ARCHIVED (過去履歴)
    status = Column(String(20), nullable=False, default='ACTIVE', index=True)

    created_by_id = Column(Integer, ForeignKey('supporters.id'), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    contract = relationship('JobRetentionContract', back_populates='plans')
    created_by = relationship('Supporter', foreign_keys=[created_by_id])

    @property
    def next_plan_start_date(self) -> datetime.date:
        """次版の開始予定日（終了予定日の翌日）"""
        return self.plan_end_date + datetime.timedelta(days=1)

    @property
    def next_review_deadline(self) -> datetime.date:
        """後方互換プロパティ"""
        return self.plan_end_date

    @next_review_deadline.setter
    def next_review_deadline(self, val: datetime.date):
        self.plan_end_date = val

    def compute_deadline_status(self, today: Optional[datetime.date] = None) -> Dict[str, Any]:
        """
        計画終了予定日および次計画開始予定日を基準とした更新ステータス判定。
        - today <= plan_end_date: 現行計画期間内 (終了間近なら APPROACHING, 本日なら DUE_TODAY)
        - today > plan_end_date:
            - 次計画開始予定日の属する月と同じ月内: OVERDUE_WITHIN_MONTH (当月内更新猶予あり)
            - その翌月以降: OVERDUE_BILLING_RISK (前月内に更新されていないため請求影響リスクあり)
        """
        if today is None:
            today = datetime.date.today()

        next_start = self.next_plan_start_date
        days_diff = (self.plan_end_date - today).days

        if today < self.plan_end_date:
            if days_diff <= 14:
                status_code = 'APPROACHING'
            else:
                status_code = 'NORMAL'
        elif today == self.plan_end_date:
            status_code = 'DUE_TODAY'
        else:
            # today > plan_end_date (次計画期間突入)
            if (today.year, today.month) == (next_start.year, next_start.month):
                status_code = 'OVERDUE_WITHIN_MONTH'
            elif (today.year, today.month) > (next_start.year, next_start.month):
                status_code = 'OVERDUE_BILLING_RISK'
            else:
                status_code = 'NORMAL'

        return compute_retention_deadline_status(self.plan_end_date, today)


def compute_retention_deadline_status(plan_end_date: datetime.date, today: Optional[datetime.date] = None) -> Dict[str, Any]:
    """
    計画終了予定日および次計画開始予定日を基準とした更新ステータス判定（共通ヘルパー）。
    - today <= plan_end_date: 現行計画期間内 (終了間近なら APPROACHING, 本日なら DUE_TODAY)
    - today > plan_end_date:
        - 次計画開始予定日の属する月と同じ月内: OVERDUE_WITHIN_MONTH (当月内更新猶予あり)
        - その翌月以降: OVERDUE_BILLING_RISK (前月内に更新されていないため請求影響リスクあり)
    """
    if today is None:
        today = datetime.date.today()

    next_start = plan_end_date + datetime.timedelta(days=1)
    days_diff = (plan_end_date - today).days

    if today < plan_end_date:
        if days_diff <= 14:
            status_code = 'APPROACHING'
        else:
            status_code = 'NORMAL'
    elif today == plan_end_date:
        status_code = 'DUE_TODAY'
    else:
        # today > plan_end_date (次計画期間突入)
        if (today.year, today.month) == (next_start.year, next_start.month):
            status_code = 'OVERDUE_WITHIN_MONTH'
        elif (today.year, today.month) > (next_start.year, next_start.month):
            status_code = 'OVERDUE_BILLING_RISK'
        else:
            status_code = 'NORMAL'

    days_remaining = max(0, days_diff)
    days_overdue = max(0, -days_diff)

    return {
        "status_code": status_code,
        "days_diff": days_diff,
        "days_remaining": days_remaining,
        "days_overdue": days_overdue,
        "plan_end_date": plan_end_date.isoformat(),
        "next_plan_start_date": next_start.isoformat(),
        "next_review_deadline": plan_end_date.isoformat(),
        "is_overdue": today > plan_end_date
    }


# ====================================================================
# 9. RetentionSupportPlanDetail (共通SupportPlanに1対1紐づく定着固有詳細)
# ====================================================================
class RetentionSupportPlanDetail(db.Model):
    """
    就労定着支援計画の固有詳細モデル（厚労省通知・別紙様式2完全準拠）。
    SupportPlan と 1対1 で結合し、定着固有の確定スナップショット・様式項目・日常サマリーを保持する。
    """
    __tablename__ = 'retention_support_plan_details'

    id = Column(Integer, primary_key=True)
    support_plan_id = Column(
        Integer, 
        ForeignKey('support_plans.id', ondelete='CASCADE'), 
        nullable=False, 
        unique=True, 
        index=True
    )
    retention_contract_id = Column(
        Integer, 
        ForeignKey('job_retention_contracts.id', ondelete='CASCADE'), 
        nullable=False, 
        index=True
    )

    # --- 日常表示用サマリー（短期目標から確定時に初期提案・固定） ---
    overall_support_goal = Column(Text, nullable=False)
    review_date = Column(Date, nullable=True)             # 実際の見直し実施日
    review_reason = Column(Text, nullable=True)           # 見直し理由

    # --- 共通SupportPlan互換プロパティ ---
    @property
    def version(self) -> int:
        return self.support_plan.plan_version if self.support_plan else 1

    @property
    def status(self) -> str:
        return self.support_plan.plan_status if self.support_plan else 'DRAFT'

    @property
    def start_date(self) -> Optional[datetime.date]:
        return self.support_plan.plan_start_date if self.support_plan else None

    @property
    def plan_end_date(self) -> Optional[datetime.date]:
        return self.support_plan.plan_end_date if self.support_plan else None

    @property
    def next_plan_start_date(self) -> Optional[datetime.date]:
        if self.plan_end_date:
            return self.plan_end_date + datetime.timedelta(days=1)
        return None

    @property
    def next_review_deadline(self) -> Optional[datetime.date]:
        return self.plan_end_date

    @property
    def created_by_id(self) -> Optional[int]:
        return self.support_plan.created_by_id if self.support_plan else None

    def compute_deadline_status(self, today: Optional[datetime.date] = None) -> Dict[str, Any]:
        if not self.plan_end_date:
            return {
                "status_code": "NORMAL",
                "days_diff": 0,
                "days_remaining": 0,
                "days_overdue": 0,
                "plan_end_date": None,
                "next_plan_start_date": None,
                "next_review_deadline": None,
                "is_overdue": False
            }
        return compute_retention_deadline_status(self.plan_end_date, today)

    # --- 1. 利用者基本情報スナップショット（様式2 公式欄） ---
    user_name = Column(String(100), nullable=True)
    user_name_kana = Column(String(100), nullable=True)
    gender = Column(String(20), nullable=True)
    birth_date = Column(Date, nullable=True)
    age_at_planning = Column(Integer, nullable=True)
    support_level = Column(String(50), nullable=True)              # 障害支援区分
    disability_handbook_type = Column(String(50), nullable=True)   # 障害者手帳区分

    # --- 2. 雇用先・労働条件・職場環境スナップショット ---
    employer_name = Column(String(200), nullable=True)
    employer_industry = Column(String(100), nullable=True)
    employer_address = Column(String(300), nullable=True)
    employer_tel = Column(String(50), nullable=True)
    employer_contact_person = Column(String(100), nullable=True)
    job_start_date = Column(Date, nullable=True)
    work_content = Column(Text, nullable=True)                     # 職種・業務内容
    employment_type = Column(String(100), nullable=True)           # 雇用形態
    wage_condition = Column(String(200), nullable=True)            # 賃金
    holiday_condition = Column(String(200), nullable=True)         # 休日
    working_hours_and_break = Column(Text, nullable=True)          # 勤務時間・休憩
    physical_work_environment = Column(Text, nullable=True)        # 物理的環境
    human_work_environment = Column(Text, nullable=True)           # 人的環境
    related_support_organizations = Column(Text, nullable=True)    # 関係支援機関

    # --- 3. 本人の状況・生活環境・定着課題 ---
    pre_employment_handover = Column(Text, nullable=True)          # 就職前事業所からの引継事項
    user_wishes = Column(Text, nullable=True)                      # 本人の希望・意向
    health_condition = Column(Text, nullable=True)                 # 健康状態
    living_environment_support = Column(Text, nullable=True)       # 生活環境・生活面サポート体制
    retention_challenges = Column(Text, nullable=True)             # 就労定着に向けた課題

    # --- 4. 本人説明・同意 & 帳票出力用事業所・スタッフスナップショット ---
    office_name = Column(String(200), nullable=True)
    office_number = Column(String(50), nullable=True)
    office_address = Column(String(300), nullable=True)
    office_tel = Column(String(50), nullable=True)
    office_fax = Column(String(50), nullable=True)

    staff_creator_name = Column(String(100), nullable=True)
    staff_evaluator_name = Column(String(100), nullable=True)
    staff_manager_name = Column(String(100), nullable=True)
    staff_service_manager_name = Column(String(100), nullable=True)
    staff_job_supporter_name = Column(String(100), nullable=True)
    staff_explainer_name = Column(String(100), nullable=True)

    explained_date = Column(Date, nullable=True)
    agreed_date = Column(Date, nullable=True)
    consent_confirmed = Column(Boolean, default=False)
    consent_notes = Column(String(200), nullable=True)

    evaluation_date = Column(Date, nullable=True)
    overall_evaluation = Column(Text, nullable=True)
    special_notes = Column(Text, nullable=True)

    # --- 5. 公式帳票外・内部整理情報 ---
    internal_employer_wishes = Column(Text, nullable=True)
    internal_overall_policy = Column(Text, nullable=True)

    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # リレーション
    support_plan = db.relationship('SupportPlan', back_populates='retention_detail')
    contract = db.relationship('JobRetentionContract', backref='retention_plan_details')
    items = db.relationship(
        'RetentionSupportPlanItem', 
        back_populates='detail', 
        cascade='all, delete-orphan', 
        order_by='RetentionSupportPlanItem.item_number'
    )
    source_links = db.relationship(
        'RetentionSupportPlanSourceLink', 
        back_populates='detail', 
        cascade='all, delete-orphan'
    )


# ====================================================================
# 10. RetentionSupportPlanItem (様式2の①〜③ 支援内容・評価 子テーブル)
# ====================================================================
class RetentionSupportPlanItem(db.Model):
    """
    厚労省様式2の「支援内容・評価」表行（①〜③）。
    ShortTermGoal と明示的に接続し、課題ごとの支援方針・内容・期間・頻度・役割分担・事後評価を保持する。
    """
    __tablename__ = 'retention_support_plan_items'
    __table_args__ = (
        UniqueConstraint('detail_id', 'item_number', name='uq_retention_detail_item_number'),
    )

    id = Column(Integer, primary_key=True)
    detail_id = Column(
        Integer, 
        ForeignKey('retention_support_plan_details.id', ondelete='CASCADE'), 
        nullable=False, 
        index=True
    )
    short_term_goal_id = Column(
        Integer, 
        ForeignKey('short_term_goals.id', ondelete='SET NULL'), 
        nullable=True, 
        index=True
    )
    item_number = Column(Integer, nullable=False) # 1, 2, 3... (様式2の①〜③)

    # 計画策定時 (公式項目)
    challenge_topic = Column(String(200), nullable=True)   # 課題・ニーズ
    support_policy = Column(Text, nullable=True)            # 支援方針
    support_content = Column(Text, nullable=True)           # 支援内容
    support_period_start = Column(Date, nullable=True)      # 支援期間開始
    support_period_end = Column(Date, nullable=True)        # 支援期間終了
    support_frequency = Column(String(100), nullable=True)  # 支援頻度

    # 計画策定時 (公式外・内部整理情報)
    role_sharing = Column(Text, nullable=True)              # 関係者の役割分担

    # 評価時 (公式項目)
    implementation_status = Column(String(20), nullable=True)     # IMPLEMENTED, PARTIAL, NOT_IMPLEMENTED, NULL
    achievement_status = Column(String(20), nullable=True)        # ACHIEVED, PARTIAL, NOT_ACHIEVED, NULL
    effectiveness_satisfaction = Column(Text, nullable=True)      # 効果、満足度など（自由記述）
    remaining_challenges = Column(Text, nullable=True)            # 残課題と対策

    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    detail = db.relationship('RetentionSupportPlanDetail', back_populates='items')
    short_term_goal = db.relationship('ShortTermGoal', back_populates='retention_items')
    source_links = db.relationship('RetentionSupportPlanSourceLink', back_populates='plan_item', cascade='all, delete-orphan')


# ====================================================================
# 11. RetentionSupportPlanSourceLink (一次情報出所追跡 子テーブル)
# ====================================================================
class RetentionSupportPlanSourceLink(db.Model):
    """
    入力支援で採用された一次情報（本人の声、企業情報、支援記録、月次レポート等）の出所プロベナンスを追跡するテーブル。
    """
    __tablename__ = 'retention_support_plan_source_links'

    id = Column(Integer, primary_key=True)
    detail_id = Column(
        Integer, 
        ForeignKey('retention_support_plan_details.id', ondelete='CASCADE'), 
        nullable=False, 
        index=True
    )
    plan_item_id = Column(
        Integer, 
        ForeignKey('retention_support_plan_items.id', ondelete='CASCADE'), 
        nullable=True, 
        index=True
    )
    
    target_field = Column(String(100), nullable=False) # 反映先項目名
    source_type = Column(String(50), nullable=False)   # 'USER_VOICE', 'EMPLOYER_FEEDBACK', 'SUPPORT_ACTION', 'MONTHLY_REPORT', 'STAFF_HEARING'
    source_id = Column(Integer, nullable=True)         # 元レコードのID
    excerpt_text = Column(Text, nullable=True)         # 採用時点の抜粋テキストスナップショット
    
    created_at = Column(DateTime, default=func.now(), nullable=False)

    detail = db.relationship('RetentionSupportPlanDetail', back_populates='source_links')
    plan_item = db.relationship('RetentionSupportPlanItem', back_populates='source_links')
