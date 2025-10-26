# app/models/__init__.py

# master.py からモデルをインポート
from .master import (
    StatusMaster, ReferralSourceMaster, RoleMaster, 
    AttendanceStatusMaster, ServiceLocationMaster, PreparationActivityMaster, 
    EmploymentTypeMaster, WorkStyleMaster, DisclosureTypeMaster, 
    ContactCategoryMaster, MeetingTypeMaster, ServiceTemplate
)

# core.py からモデルをインポート
from .core import (
    Supporter, User, Prospect, AttendancePlan, DailyLog
)

# plan_audit.py からモデルをインポート
from .plan_audit import (
    SupportPlan, ShortTermGoal, SpecificGoal, Monitoring, 
    Assessment, MeetingMinute, SystemLog
)

# SQLAlchemy-migrate がモデルを認識できるように、__all__ に全モデルを含める
__all__ = [
    'StatusMaster', 'ReferralSourceMaster', 'RoleMaster', 
    'AttendanceStatusMaster', 'ServiceLocationMaster', 'PreparationActivityMaster', 
    'EmploymentTypeMaster', 'WorkStyleMaster', 'DisclosureTypeMaster', 
    'ContactCategoryMaster', 'MeetingTypeMaster', 'ServiceTemplate',
    'GoalCategoryMaster',
    'Supporter', 'User', 'Prospect', 'AttendancePlan', 'DailyLog',
    'SupportPlan', 'ShortTermGoal', 'SpecificGoal', 'Monitoring','Contact', 
    'Assessment', 'MeetingMinute', 'SystemLog'
]