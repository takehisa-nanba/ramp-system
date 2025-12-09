# Backend/app/models/core/user.py (SQLAlchemy 2.0 Async Migration - FINAL)

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Boolean, ForeignKey, Date, DateTime, Text
from typing import List, Optional
import datetime
# funcは不要になりました (TimestampMixinで定義されているため)

# Base と TimestampMixin は base.py で定義済み
from ..base import Base, TimestampMixin 

# ====================================================================
# 1. User (利用者の業務データ / システムの核)
# ====================================================================
class User(TimestampMixin, Base): # <-- TimestampMixinを継承！
    """
    利用者の業務データ（システムの核）。
    個人特定可能情報(PII)や認証情報を一切含まず、匿名IDのみで管理する。
    """
    # ★ 必須: 匿名化後も使用する表示名（原理5）
    display_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True) 
    
    # --- システム管理情報 ---
    status_id: Mapped[int] = mapped_column(ForeignKey('status_master.id'), nullable=False, index=True)
    primary_supporter_id: Mapped[int | None] = mapped_column(ForeignKey('supporters.id'), index=True, nullable=True)
    service_start_date: Mapped[datetime.date | None] = mapped_column(Date, index=True, nullable=True) 
    service_end_date: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    
    # ★ 復職支援ケースフラグ（原理14）
    is_return_to_work_case: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)

    # created_at, updated_at は TimestampMixin から継承されるため削除
    
    # --- リレーションシップ ---
    pii: Mapped["UserPII"] = relationship(back_populates='user', uselist=False, cascade="all, delete-orphan", lazy='noload') # lazy='noload'適用
    
    status: Mapped["StatusMaster"] = relationship(back_populates='users', foreign_keys=[status_id], lazy='noload')
    
    primary_supporter: Mapped["Supporter"] = relationship(back_populates='primary_users', foreign_keys=[primary_supporter_id], lazy='noload')
    
    # --- 利用者の中核的な子テーブル --- (lazy='noload'適用)
    certificates: Mapped[List["ServiceCertificate"]] = relationship(back_populates='user', lazy='noload', cascade="all, delete-orphan")
    profile: Mapped["UserProfile"] = relationship(back_populates='user', uselist=False, cascade="all, delete-orphan", lazy='noload')
    holistic_policies: Mapped[List["HolisticSupportPolicy"]] = relationship(back_populates='user', lazy='noload', cascade="all, delete-orphan")
    skills: Mapped[List["UserSkill"]] = relationship(back_populates='user', lazy='noload', cascade="all, delete-orphan")
    documents: Mapped[List["UserDocument"]] = relationship(back_populates='user', lazy='noload', cascade="all, delete-orphan")
    family_members: Mapped[List["FamilyMember"]] = relationship(back_populates='user', lazy='noload', cascade="all, delete-orphan")
    emergency_contacts: Mapped[List["EmergencyContact"]] = relationship(back_populates='user', lazy='noload', cascade="all, delete-orphan")

    # --- 支援プロセスの子テーブル ---
    support_plans: Mapped[List["SupportPlan"]] = relationship(back_populates='user', lazy='noload', cascade="all, delete-orphan")
    daily_logs: Mapped[List["DailyLog"]] = relationship(back_populates='user', lazy='noload', cascade="all, delete-orphan")

    # --- 請求・会計の子テーブル ---
    billings: Mapped[List["BillingData"]] = relationship(back_populates='user', lazy='noload', cascade="all, delete-orphan")
    
    # --- コミュニケーションの子テーブル ---
    support_threads: Mapped[List["SupportThread"]] = relationship(back_populates='user', lazy='noload', cascade="all, delete-orphan")
    user_requests: Mapped[List["UserRequest"]] = relationship(back_populates='user', lazy='noload', cascade="all, delete-orphan")
    organization_links: Mapped[List["UserOrganizationLink"]] = relationship(back_populates='user', lazy='noload')
    
    # --- 定着支援の子テーブル ---
    retention_contracts: Mapped[List["JobRetentionContract"]] = relationship(back_populates='user', lazy='noload')
    follow_ups: Mapped[List["PostTransitionFollowUp"]] = relationship(back_populates='user', lazy='noload')
    
    # --- 就労先の子テーブル ---
    job_placements: Mapped[List["JobPlacementLog"]] = relationship(back_populates='user', lazy='noload')
    
    # --- ★ 追加: 危機対応計画 ---
    crisis_plans: Mapped[List["CrisisPlan"]] = relationship(back_populates='user', lazy='noload', cascade="all, delete-orphan")
    # --- ★ 追加: インシデント・苦情 ---
    incident_reports: Mapped[List["IncidentReport"]] = relationship(back_populates='user', lazy='noload')
    
    # 苦情ログ
    complaints: Mapped[List["ComplaintLog"]] = relationship(
        'ComplaintLog', 
        primaryjoin="User.id == ComplaintLog.target_user_id",
        foreign_keys='ComplaintLog.target_user_id', 
        lazy='noload'
    )
    
    # --- ★ 追加: ケース会議 ---
    case_conferences: Mapped[List["CaseConferenceLog"]] = relationship(back_populates='user', lazy='noload')
    # --- 監査・コンプライアンス ---
    compliance_events: Mapped[List["ComplianceEventLog"]] = relationship(back_populates='user', lazy='noload')
    
    # ★ スケジュールへの明示的なリレーション
    user_schedules: Mapped[List["Schedule"]] = relationship(
        secondary='schedule_participants', 
        back_populates='participants_user',
        lazy='noload'
    )

# ====================================================================
# 2. UserPII (個人特定可能情報 & 認証 / 3階層暗号化)
# ====================================================================
class UserPII(Base): # UserPII はタイムスタンプ不要のため TimestampMixin は継承しない
    """
    利用者の最高機密情報（PII）および認証情報。
    """
    __table_args__ = (
        UniqueConstraint('sns_provider', 'sns_account_id', name='uq_userpii_sns_auth'),
        CheckConstraint(
            '(sns_provider IS NULL AND sns_account_id IS NULL) OR '
            '(sns_provider IS NOT NULL AND sns_account_id IS NOT NULL)',
            name='ck_userpii_sns_auth_pair'
        )
    )

    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), unique=True, nullable=False)
    
    # --- 階層1：最高機密（エンベロープ暗号化） ---
    encrypted_certificate_number: Mapped[str | None] = mapped_column(String(512), nullable=True)
    encrypted_data_key: Mapped[str | None] = mapped_column(String(512), nullable=True) 

    # --- 階層2：機密PII（システム共通鍵暗号化） ---
    encrypted_last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    encrypted_first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    encrypted_last_name_kana: Mapped[str | None] = mapped_column(String(255), nullable=True)
    encrypted_first_name_kana: Mapped[str | None] = mapped_column(String(255), nullable=True)
    encrypted_address: Mapped[str | None] = mapped_column(String(512), nullable=True)
    
    # --- 平文（検索・計算・ユニーク制約用） ---
    birth_date: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(20), index=True, nullable=True)
    email: Mapped[str | None] = mapped_column(String(120), unique=True, index=True, nullable=True)
    
    sns_account_id: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    sns_provider: Mapped[str | None] = mapped_column(String(50), index=True, nullable=True)

    # --- 階層3：認証情報（ハッシュ化） ---
    password_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    pin_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    
    # --- 平文（暗号化不要）の業務データ ---
    gender_legal_id: Mapped[int | None] = mapped_column(ForeignKey('gender_legal_master.id'), nullable=True) 
    gender_identity: Mapped[str | None] = mapped_column(String(100), nullable=True)
    disability_type_id: Mapped[int | None] = mapped_column(ForeignKey('disability_type_master.id'), nullable=True) 
    disability_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    support_needs: Mapped[str | None] = mapped_column(Text, nullable=True)
    handbook_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_handbook_certified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # --- リレーションシップ ---
    user: Mapped["User"] = relationship(back_populates='pii', uselist=False, lazy='noload')
    gender_legal: Mapped["GenderLegalMaster"] = relationship(foreign_keys=[gender_legal_id], lazy='noload')
    disability_type: Mapped["DisabilityTypeMaster"] = relationship(foreign_keys=[disability_type_id], lazy='noload')

    # ゲッター/セッター/認証メソッドはAsyncサービス層に分離済み