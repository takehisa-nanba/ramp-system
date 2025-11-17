# 責務: 新しい論理パッケージ内の全モデルをインポートし、
# アプリケーション全体に「app.models」という単一の窓口を提供する。

# --- masters パッケージ ---
from .masters.master_definitions import (
    StatusMaster, DisabilityTypeMaster, GenderLegalMaster, MunicipalityMaster,
    JobTitleMaster, ServiceTypeMaster, QualificationMaster, SkillMaster,
    TrainingPrerequisiteMaster, DocumentTypeMaster, CommitteeTypeMaster,
    StaffActivityMaster, ProductMaster, VendorMaster, RoleMaster, PermissionMaster
)

# --- core パッケージ ---
from .core.office import (
    Corporation, OfficeSetting, OfficeServiceConfiguration
)
from .core.supporter import (
    Supporter, SupporterTimecard, SupporterJobAssignment, 
    SupporterQualification, AttendanceCorrectionRequest
)
from .core.user import (
    User, UserPII
)
from .core.service_certificate import (
    ServiceCertificate, GrantedService, CopaymentLimit, 
    MealAddonStatus, CopaymentManagement
)
from .core.audit_log import (
    SystemLog, AuditActionLog
)
from .core.user_documents import (
    UserSkill, UserDocument
)
from .core.holistic_support_policy import (
    HolisticSupportPolicy
)
# rbac_links.py はリレーションシップ定義専用のため、ここではインポート不要

# --- support パッケージ ---
from .support.support_plan import (
    SupportPlan, LongTermGoal, ShortTermGoal, IndividualSupportGoal,
    SupportConferenceLog, PlanReviewRequest, AssessorType, GoalAssessment
)
from .support.daily_record import (
    DailyLog, BreakRecord, DailyProductivityLog
)
from .support.schedule import (
    Schedule
    # schedule_participants テーブルは Schedule モデル経由で db.Model.metadata に登録される
)
from .support.job_retention import (
    JobRetentionContract, JobRetentionRecord
)
from .support.follow_up import (
    PostTransitionFollowUp
)
from .support.monitoring import (
    MonitoringReport
)
from .support.crisis_plan import (
    CrisisPlan
)
from .support.attendance_workflow import (
    AttendanceRecord, UserAttendanceCorrectionRequest, 
    MonthlyAttendancePlan, AbsenceResponseLog
)

# --- finance パッケージ ---
from .finance.billing_compliance import (
    ContractReportDetail, ComplianceEventLog
)
from .finance.accounting_management import (
    MonthlyBillingSummary, ClientInvoice, AgencyReceiptStatement, DocumentConsentLog
)
from .finance.wage_management import (
    SalesInvoice, UserWageLog
)

# --- comms パッケージ ---
from .comms.communication_channels import (
    SupportThread, ChatMessage, UserRequest
)
from .comms.client_relations import (
    Organization, UserOrganizationLink
)
from .comms.acquisition_activities import (
    AcquisitionActivityLog
)

# --- compliance パッケージ ---
from .compliance.incident_management import (
    IncidentReport, ComplaintLog
)
from .compliance.safety_and_training import (
    CommitteeActivityLog, OfficeTrainingEvent, TrainingLog,
    SupporterFeedbackLog, StaffReflectionLog
)

# --- employment パッケージ ---
from .employment.job_placement import (
    EmployerMaster, JobPlacementLog, JobDevelopmentLog
)