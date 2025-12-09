# Backend/app/models/core/supporter.py (SQLAlchemy 2.0 Async Migration - FINAL)

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Boolean, ForeignKey, Date, DateTime, Text, Enum, UniqueConstraint
from typing import List, Optional
import datetime
from enum import Enum as PyEnum

# 新しいプロジェクト構造に合わせる（ベースクラスとMix-inのインポート）
# Base と TimestampMixin は base.py で定義済み
from ..base import Base, TimestampMixin 

# rbac_linksは別ファイルにあるものと想定し、その外部結合テーブル名は必要
# 例: supporter_role_link = Table('supporter_role_link', Base.metadata, ...)
SUPPORTER_ROLE_LINK_TABLE_NAME = "supporter_role_link" # secondaryテーブル名を文字列定数として保持

# 雇用形態のEnumを定義 (旧コードから継承)
class EmploymentType(PyEnum):
    FULL_TIME = "FULL_TIME"
    SHORTENED_FT = "SHORTENED_FT"
    PART_TIME = "PART_TIME"


# ====================================================================
# 1. Supporter (職員の業務エンティティ / 表)
# ====================================================================
class Supporter(TimestampMixin, Base): # <-- TimestampMixinを継承
    """
    職員（支援者）の業務情報（表）。
    """
    
    # ★ NEW: 職員コード (Quick Authentication/Business Key)
    staff_code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    
    # --- 基本情報 (平文・業務上必須) ---
    last_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    last_name_kana: Mapped[str] = mapped_column(String(50), nullable=False)
    first_name_kana: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # 所属事業所 (ホームベース / JOBロールの基本単位)
    office_id: Mapped[int | None] = mapped_column(ForeignKey('office_settings.id'), index=True, nullable=True)
    
    # --- 契約ステータス (常勤換算の基礎) ---
    hire_date: Mapped[datetime.date] = mapped_column(Date, nullable=False) # 入社日
    retirement_date: Mapped[datetime.date | None] = mapped_column(Date, nullable=True) # 退職日
    
    employment_type: Mapped[EmploymentType] = mapped_column(Enum(EmploymentType), nullable=False)
    
    # 個人の週所定労働時間（分）。常勤/非常勤の判定に使用
    weekly_scheduled_minutes: Mapped[int] = mapped_column(Integer, nullable=False) 
    
    # アカウント有効化フラグ
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # created_at/updated_at は TimestampMixin から継承されるため削除
    
    # --- リレーションシップ ---
    pii: Mapped["SupporterPII"] = relationship(back_populates='supporter', uselist=False, cascade="all, delete-orphan", lazy='noload')
    
    # 子テーブル (全て lazy='noload' へ変更)
    timecards: Mapped[List["SupporterTimecard"]] = relationship(back_populates='supporter', lazy='noload', cascade="all, delete-orphan")
    job_assignments: Mapped[List["SupporterJobAssignment"]] = relationship(back_populates='supporter', lazy='noload', cascade="all, delete-orphan")
    qualifications: Mapped[List["SupporterQualification"]] = relationship(back_populates='supporter', lazy='noload', cascade="all, delete-orphan")
    
    activity_allocations: Mapped[List["StaffActivityAllocationLog"]] = relationship(
        'StaffActivityAllocationLog', 
        back_populates='supporter', 
        foreign_keys='StaffActivityAllocationLog.supporter_id', 
        lazy='noload', 
        cascade="all, delete-orphan"
    )
    
    attendance_correction_requests: Mapped[List["AttendanceCorrectionRequest"]] = relationship(
        'AttendanceCorrectionRequest', 
        back_populates='supporter',
        foreign_keys='AttendanceCorrectionRequest.supporter_id', 
        lazy='noload'
    )
    
    # ★ RBAC（役割）へのリレーションシップ
    roles: Mapped[List["RoleMaster"]] = relationship('RoleMaster', secondary=SUPPORTER_ROLE_LINK_TABLE_NAME, back_populates='supporters', lazy='noload')
    
    # 逆参照 (User - 主担当職員)
    primary_users: Mapped[List["User"]] = relationship('User', back_populates='primary_supporter', lazy='noload')
    
    managed_services: Mapped[List["OfficeServiceConfiguration"]] = relationship('OfficeServiceConfiguration', back_populates='manager_supporter', foreign_keys='OfficeServiceConfiguration.manager_supporter_id', lazy='noload')
    
    reflection_logs: Mapped[List["StaffReflectionLog"]] = relationship('StaffReflectionLog', back_populates='supporter', lazy='noload')
    
    # ★ 所属事業所へのリレーション
    office: Mapped["OfficeSetting"] = relationship(back_populates='staff_members', foreign_keys=[office_id], lazy='noload')
    
    # ★ スケジュールへの明示的なリレーション
    supporter_schedules: Mapped[List["Schedule"]] = relationship(
        'Schedule', 
        secondary='schedule_participants', 
        back_populates='participants_supporter',
        lazy='noload'
    )

# ====================================================================
# 2. SupporterPII (職員機密情報 / 裏 / 暗号化)
# ====================================================================
class SupporterPII(Base):
    """職員の機密情報保管庫。"""

    supporter_id: Mapped[int] = mapped_column(ForeignKey('supporters.id'), unique=True, nullable=False)
    
    # --- 認証情報 ---
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(128), nullable=True) 
    
    # --- 機密個人情報 ---
    encrypted_personal_phone: Mapped[str | None] = mapped_column(String(255), nullable=True)
    encrypted_address: Mapped[str | None] = mapped_column(String(512), nullable=True)
    encrypted_bank_account_info: Mapped[str | None] = mapped_column(String(512), nullable=True) 
    
    # --- 契約書類 (証憑) ---
    encrypted_employment_contract_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    encrypted_resume_url: Mapped[str | None] = mapped_column(String(500), nullable=True) 
    
    supporter: Mapped["Supporter"] = relationship(back_populates='pii', uselist=False, lazy='noload')

    # ゲッター/セッター/認証メソッドはAsyncサービス層に分離済み


# ====================================================================
# 3. SupporterTimecard (日々の勤怠 / 常勤換算の実績)
# ====================================================================
class SupporterTimecard(TimestampMixin, Base): # <-- TimestampMixinを継承
    """職員の勤怠記録。常勤換算の分子となる「事実」を記録する。"""

    supporter_id: Mapped[int] = mapped_column(ForeignKey('supporters.id'), nullable=False, index=True)
    office_service_configuration_id: Mapped[int] = mapped_column(ForeignKey('office_service_configurations.id'), nullable=False, index=True)
    
    work_date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    
    # --- 実績時間 ---
    check_in: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True) 
    check_out: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    total_break_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    scheduled_work_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False) 
    is_absent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False) 
    absence_type: Mapped[str | None] = mapped_column(String(50), nullable=True) 
    deemed_work_minutes: Mapped[int | None] = mapped_column(Integer, default=0, nullable=True) 
    
    # 施設外就労の担当時間
    facility_out_minutes: Mapped[int | None] = mapped_column(Integer, default=0, nullable=True)
    
    # リレーション
    supporter: Mapped["Supporter"] = relationship(back_populates='timecards', lazy='noload')
    service_config: Mapped["OfficeServiceConfiguration"] = relationship(lazy='noload')


# ====================================================================
# 4. SupporterJobAssignment (職務割り当て / 兼務の責務)
# ====================================================================
class SupporterJobAssignment(TimestampMixin, Base): # <-- TimestampMixinを継承
    """職員の職務割り当て履歴。"""

    __table_args__ = (
        UniqueConstraint('supporter_id', 'job_title_id', 'start_date', 'office_service_configuration_id', name='uq_supporter_job_assignment'),
    )

    supporter_id: Mapped[int] = mapped_column(ForeignKey('supporters.id'), nullable=False, index=True)
    job_title_id: Mapped[int] = mapped_column(ForeignKey('job_title_master.id'), nullable=False, index=True)
    office_service_configuration_id: Mapped[int] = mapped_column(ForeignKey('office_service_configurations.id'), nullable=False, index=True)
    
    start_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    end_date: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    
    assigned_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    
    is_deemed_assignment: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deemed_expiry_date: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    
    supporter: Mapped["Supporter"] = relationship(back_populates='job_assignments', lazy='noload')
    job_title: Mapped["JobTitleMaster"] = relationship(back_populates='assignments', lazy='noload')


# ====================================================================
# 5. SupporterQualification (保有資格 / 証憑と公開設定)
# ====================================================================
class SupporterQualification(TimestampMixin, Base): # <-- TimestampMixinを継承
    """職員の保有資格・スキル・実務経験証明書。"""

    supporter_id: Mapped[int] = mapped_column(ForeignKey('supporters.id'), nullable=False, index=True)
    qualification_master_id: Mapped[int] = mapped_column(ForeignKey('qualification_master.id'), nullable=False)
    
    certification_date: Mapped[datetime.date | None] = mapped_column(Date, nullable=True) 
    expiry_date: Mapped[datetime.date | None] = mapped_column(Date, nullable=True) 
    certificate_document_url: Mapped[str | None] = mapped_column(String(500), nullable=True) 
    
    visibility_scope: Mapped[str] = mapped_column(String(20), default='PUBLIC', nullable=False) 
    
    supporter: Mapped["Supporter"] = relationship(back_populates='qualifications', lazy='noload')
    qualification_master: Mapped["QualificationMaster"] = relationship(back_populates='supporter_qualifications', lazy='noload')


# ====================================================================
# 6. StaffActivityAllocationLog (活動配分 / ムダ取り)
# ====================================================================
class StaffActivityAllocationLog(TimestampMixin, Base): # <-- TimestampMixinを継承
    """職員の日次の活動時間配分。"""

    supporter_id: Mapped[int] = mapped_column(ForeignKey('supporters.id'), nullable=False, index=True)
    activity_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    
    staff_activity_master_id: Mapped[int] = mapped_column(ForeignKey('staff_activity_master.id'), nullable=False)
    
    allocated_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    
    is_governance_task: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    approver_id: Mapped[int | None] = mapped_column(ForeignKey('supporters.id'), nullable=True)
    
    supporter: Mapped["Supporter"] = relationship(foreign_keys=[supporter_id], back_populates='activity_allocations', lazy='noload')
    activity_type: Mapped["StaffActivityMaster"] = relationship(back_populates='logs', lazy='noload')
    approver: Mapped["Supporter"] = relationship(foreign_keys=[approver_id], lazy='noload')


# ====================================================================
# 7. AttendanceCorrectionRequest (勤怠修正申請)
# ====================================================================
class AttendanceCorrectionRequest(TimestampMixin, Base): # <-- TimestampMixinを継承
    """職員による勤怠修正申請ログ。"""

    supporter_id: Mapped[int] = mapped_column(ForeignKey('supporters.id'), nullable=False, index=True)
    
    target_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    record_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # requested_timestamp は TimestampMixin の created_at/updated_at に置き換え可能だが、
    # 申請日時として明確に残すため、created_atに依存させず残す
    requested_timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False) 
    
    request_reason: Mapped[str] = mapped_column(Text, nullable=False) 
    
    request_status: Mapped[str] = mapped_column(String(20), default='PENDING', nullable=False) 
    approver_id: Mapped[int | None] = mapped_column(ForeignKey('supporters.id'), nullable=True)
    processed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    
    supporter: Mapped["Supporter"] = relationship(foreign_keys=[supporter_id], back_populates='attendance_correction_requests', lazy='noload')
    approver: Mapped["Supporter"] = relationship(foreign_keys=[approver_id], lazy='noload')