# backend/app/models/__init__.py

# SQLAlchemy Model Index and Exporter
# ------------------------------------
# Ramp-System V1.0 の全モデル定義を集約・公開する (設計変更 第2版)

# --- 1. master.py (基本マスターデータ) ---
from .master import (
    RoleMaster, StatusMaster, AttendanceStatusMaster, ReferralSourceMaster, 
    EmploymentTypeMaster, WorkStyleMaster, DisclosureTypeMaster, 
    ContactCategoryMaster, MeetingTypeMaster, ServiceLocationMaster, 
    AssessmentItemMaster, AssessmentScoreMaster, CertificateTypeMaster, 
    AssessmentTypeMaster, GenderLegalMaster, DisabilityTypeMaster, 
    MunicipalityMaster, HistoryCategoryMaster,
    GovernmentOffice, ServiceTemplate, PreparationActivityMaster,
    FeePayerMaster
)

# --- 2. core.py (システムの核となる利用者・職員) ---
from .core import (
    Supporter, User, AttendancePlan, DailyLog, Contact
    # (Prospectは削除)
)

# --- 3. compliance.py (法令・報酬マスタ) ---
from .compliance import (
    GovernmentFeeMaster, ComplianceRule, FeeEligibilityRequirement, 
    ComplianceFact
)

# --- 4. office_admin.py (法人・事業所管理) ---
from .office_admin import (
    Corporation, OfficeSetting, OfficeServiceConfiguration, 
    OfficeAdditiveFiling, FeeCalculationDecision
)

# --- 5. client_relations.py (受給者証・利用者関係) ---
from .client_relations import (
    EmergencyContact, MedicalInstitution, BeneficiaryCertificate, 
    ServiceProvisionPeriod, ServiceUnitPeriod, CopaymentLimitPeriod, 
    ProvisionalServicePeriod
)

# --- 6. initial_support.py (★ 削除 ★) ---
# (ProspectモデルはUserモデルに統合されたため、ファイル自体を削除)

# --- 7. plan.py (個別支援計画) ---
from .plan import (
    SupportPlan, ShortTermGoal, SpecificGoal, Monitoring, 
    Assessment, MeetingMinute, ReadinessAssessmentResult,
    PreEnrollmentLog, PreEnrollmentAssessmentScore # ★ initial_support.py から移動 ★
)

# --- 8. records.py (日々のサービス提供記録) ---
from .records import (
    ServiceRecord, # (ExternalSupportRecordは削除し、ここに統一)
    BreakRecord, 
    RecordSupporter, ServiceRecordAdditive, AttendanceRecord
)

# --- 9. retention.py (就労定着支援) ---
from .retention import (
    JobRetentionContract, JobRetentionRecord
)

# --- 10. business_dev.py (事業開発・営業) ---
from .business_dev import (
    JobOffer, CompanyContactLog, MarketingOutreachLog
)

# --- 11. hr.py (人事・勤怠) ---
from .hr import (
    SupporterTimecard, ExpenseCategoryMaster, ExpenseRecord
)

# --- 12. schedule.py (スケジュール) ---
from .schedule import (
    Schedule, ScheduleParticipant
)

# --- 13. communication.py (チャット・申請) ★ 修正 ★ ---
from .communication import (
    SupportThread, ChatMessage,                # 利用者連絡帳
    ChatChannel, ChannelParticipant, ChannelMessage, # 汎用チャット
    UserRequest                                # 汎用申請
)

# --- 14. audit_log.py (監査ログ) ---
from .audit_log import (
    SystemLog
)


# --- 全モデルを __all__ リストで公開 ---
__all__ = [
    # 1. master.py
    'RoleMaster', 'StatusMaster', 'AttendanceStatusMaster', 'ReferralSourceMaster', 
    'EmploymentTypeMaster', 'WorkStyleMaster', 'DisclosureTypeMaster', 
    'ContactCategoryMaster', 'MeetingTypeMaster', 'ServiceLocationMaster', 
    'AssessmentItemMaster', 'AssessmentScoreMaster', 'CertificateTypeMaster', 
    'AssessmentTypeMaster', 'GenderLegalMaster', 'DisabilityTypeMaster', 
    'MunicipalityMaster', 'HistoryCategoryMaster',
    'GovernmentOffice', 'ServiceTemplate', 'PreparationActivityMaster',
    'FeePayerMaster',

    # 2. core.py
    'Supporter', 'User', 'AttendancePlan', 'DailyLog', 'Contact',

    # 3. compliance.py
    'GovernmentFeeMaster', 'ComplianceRule', 'FeeEligibilityRequirement', 
    'ComplianceFact',

    # 4. office_admin.py
    'Corporation', 'OfficeSetting', 'OfficeServiceConfiguration', 
    'OfficeAdditiveFiling', 'FeeCalculationDecision',

    # 5. client_relations.py
    'EmergencyContact', 'MedicalInstitution', 'BeneficiaryCertificate', 
    'ServiceProvisionPeriod', 'ServiceUnitPeriod', 'CopaymentLimitPeriod', 
    'ProvisionalServicePeriod',

    # 6. initial_support.py (★ 削除 ★)

    # 7. plan.py
    'SupportPlan', 'ShortTermGoal', 'SpecificGoal', 'Monitoring', 
    'Assessment', 'MeetingMinute', 'ReadinessAssessmentResult',
    'PreEnrollmentLog', 'PreEnrollmentAssessmentScore', # ★ 追加

    # 8. records.py
    'ServiceRecord',
    'BreakRecord', 
    'RecordSupporter', 'ServiceRecordAdditive', 'AttendanceRecord',

    # 9. retention.py
    'JobRetentionContract', 'JobRetentionRecord',

    # 10. business_dev.py
    'JobOffer', 'CompanyContactLog', 'MarketingOutreachLog',

    # 11. hr.py
    'SupporterTimecard', 'ExpenseCategoryMaster', 'ExpenseRecord',

    # 12. schedule.py
    'Schedule', 'ScheduleParticipant',

    # 13. communication.py ★ 修正 ★
    'SupportThread', 'ChatMessage',
    'ChatChannel', 'ChannelParticipant', 'ChannelMessage',
    'UserRequest',

    # 14. audit_log.py
    'SystemLog',
]
