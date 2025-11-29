# 責務: 新しい論理パッケージ内の全モデルをインポートし、
# アプリケーション全体に「app.models」という単一の窓口を提供する。

# --- 1. masters パッケージ ---
from backend.app.models.masters.master_definitions import (
    StatusMaster, DisabilityTypeMaster, GenderLegalMaster, MunicipalityMaster,
    JobTitleMaster, ServiceTypeMaster, QualificationMaster, SkillMaster,
    TrainingPrerequisiteMaster, DocumentTypeMaster, CommitteeTypeMaster,
    StaffActivityMaster, ProductMaster, VendorMaster, RoleMaster, PermissionMaster,
    TrainingTypeMaster,
    # ★ 追加: 失敗の財産化・ナレッジ共有のための新マスタ
    FailureFactorMaster, IssueCategoryMaster,
    ServiceUnitMaster
)

# --- 2. core パッケージ (SessionLockの追加) ---
from backend.app.models.core.office import (
    Corporation, OfficeSetting, OfficeServiceConfiguration,
    OfficeAdditiveFiling, JobFilingRecord,
    # ★ 追加: 事業所運営会議
    OfficeOperationsLog
)
from backend.app.models.core.supporter import (
    Supporter, SupporterPII, SupporterTimecard, SupporterJobAssignment, 
    SupporterQualification, AttendanceCorrectionRequest,
    StaffActivityAllocationLog
)
from backend.app.models.core.user import (
    User, UserPII
)
from backend.app.models.core.user_profile import (
    UserProfile, EmergencyContact, FamilyMember
)
from backend.app.models.core.user_documents import (
    UserSkill, UserDocument
)
from backend.app.models.core.service_certificate import (
    ServiceCertificate, GrantedService, CopaymentLimit, 
    MealAddonStatus, CopaymentManagement
)
from backend.app.models.core.audit_log import (
    SystemLog, AuditActionLog
)
from backend.app.models.core.user_documents import (
    UserSkill, UserDocument
)
from backend.app.models.core.holistic_support_policy import (
    HolisticSupportPolicy
)
from backend.app.models.core.session_management import (
    SessionLock # PII揮発性のためのモデル
)
from backend.app.models.core.rbac_links import (
    supporter_role_link, role_permission_link
)

# --- 3. support パッケージ ---
from backend.app.models.support.support_plan import (
    SupportPlan, LongTermGoal, ShortTermGoal, IndividualSupportGoal,
    SupportConferenceLog, PlanReviewRequest, AssessorType, GoalAssessment,
    ISP_Continuity_Gap_Log, GapReasonType # Enumもインポート

)
from backend.app.models.support.daily_log import (
    DailyLog, DailyLogActivity, BreakRecord, DailyProductivityLog
)
from backend.app.models.support.schedule import (
    Schedule
)
from backend.app.models.support.job_retention import (
    JobRetentionContract, JobRetentionRecord
)
from backend.app.models.support.follow_up import (
    PostTransitionFollowUp
)
from backend.app.models.support.monitoring import (
    MonitoringReport
)
from backend.app.models.support.crisis_plan import (
    CrisisPlan
)
from backend.app.models.support.attendance_workflow import (
    AttendanceRecord, UserAttendanceCorrectionRequest, 
    MonthlyAttendancePlan, AbsenceResponseLog
)
# ★ 追加: ケース会議
from backend.app.models.support.case_management import (
    CaseConferenceLog
)

# --- 4. finance パッケージ ---
from backend.app.models.finance.billing_compliance import (
    ContractReportDetail, ComplianceEventLog
)
from backend.app.models.finance.billing_data import (
    BillingData
)
from backend.app.models.finance.accounting_management import (
    MonthlyBillingSummary, ClientInvoice, AgencyReceiptStatement, DocumentConsentLog,
    CorporateTransferLog
)
from backend.app.models.finance.wage_management import (
    SalesInvoice, UserWageLog
)

# --- 5. comms パッケージ ---
from backend.app.models.comms.communication_channels import (
    SupportThread, ChatMessage, UserRequest
)
from backend.app.models.comms.client_relations import (
    Organization, UserOrganizationLink
)
from backend.app.models.comms.acquisition_activities import (
    AcquisitionActivityLog
)
from backend.app.models.comms.communication_channels import (
    SupportThread, ChatMessage, UserRequest
)
from backend.app.models.comms.shared_note import (
    SharedNote, NoteVersion # ★ NEW: 共同編集ノート
)

# --- 6. compliance パッケージ ---
from backend.app.models.compliance.incident_management import (
    IncidentReport, ComplaintLog
)
from backend.app.models.compliance.safety_and_training import (
    CommitteeActivityLog, OfficeTrainingEvent, TrainingLog,
    SupporterFeedbackLog, StaffReflectionLog, StaffWellnessLog
)
from backend.app.models.compliance.audit_tracking import (
    UnresponsiveRiskCounter # ★ NEW: 断罪の証拠化 (URAC)
)

# --- 7. employment パッケージ ---
from backend.app.models.employment.job_placement import (
    EmployerMaster, JobPlacementLog, JobDevelopmentLog
)