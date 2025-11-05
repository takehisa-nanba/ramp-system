# SQLAlchemy Model Index and Exporter
# ------------------------------------
# Ramp-System V1.0 の全モデル定義を集約・公開する

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

# --- 6. initial_support.py (初期支援・見込み客) ---
from .initial_support import (
    Prospect, PreEnrollmentLog, PreEnrollmentAssessmentScore
)

# --- 7. plan.py (個別支援計画) ---
from .plan import (
    SupportPlan, ShortTermGoal, SpecificGoal, Monitoring, 
    Assessment, MeetingMinute, ReadinessAssessmentResult
)

# --- 8. records.py (日々のサービス提供記録) ---
from .records import (
    ServiceRecord, ExternalSupportRecord, BreakRecord, 
    RecordSupporter, ServiceRecordAdditive, AttendanceRecord
)

# --- 9. retention.py (就労定着支援) ---
from .retention import (
    JobRetentionContract, JobRetentionRecord
)

# --- 10. business_dev.py (事業開発・営業) ---
# ★★★ ファイル名のリネームを反映 ★★★
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

# --- 13. communication.py (チャット) ---
from .communication import (
    ChatMessage
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

    # 6. initial_support.py
    'Prospect', 'PreEnrollmentLog', 'PreEnrollmentAssessmentScore',

    # 7. plan.py
    'SupportPlan', 'ShortTermGoal', 'SpecificGoal', 'Monitoring', 
    'Assessment', 'MeetingMinute', 'ReadinessAssessmentResult',

    # 8. records.py
    'ServiceRecord', 'ExternalSupportRecord', 'BreakRecord', 
    'RecordSupporter', 'ServiceRecordAdditive', 'AttendanceRecord',

    # 9. retention.py
    'JobRetentionContract', 'JobRetentionRecord',

    # 10. business_dev.py (★変更なし。モデル名はそのまま)
    'JobOffer', 'CompanyContactLog', 'MarketingOutreachLog',

    # 11. hr.py
    'SupporterTimecard', 'ExpenseCategoryMaster', 'ExpenseRecord',

    # 12. schedule.py
    'Schedule', 'ScheduleParticipant',

    # 13. communication.py
    'ChatMessage',

    # 14. audit_log.py
    'SystemLog',
]