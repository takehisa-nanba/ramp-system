# app/models/__init__.py

# --- 1. master.py からモデルをインポート (変更あり) ---
from . import master

# --- 2. core.py からモデルをインポート (変更あり) ---
from .core import (
    Supporter, User, Prospect, AttendancePlan, DailyLog,
    Contact # plan_audit.py から移動
)

# --- 3. plan.py からモデルをインポート (新規) ---
from .plan import (
    SupportPlan, ShortTermGoal, SpecificGoal, Monitoring, 
    Assessment, MeetingMinute
)

# --- 4. audit_log.py からモデルをインポート (新規) ---
from .audit_log import (
    SystemLog, # plan_audit.py から移動
    GovernmentOffice, # master.py から移動
    ServiceTemplate, # master.py から移動
    PreparationActivityMaster # master.py から移動
)

from .user import user # user.py
from .user import profile # profile.py

# --- ▼▼▼ 以下を追記 ▼▼▼ ---
from .user import compliance # compliance.py (Certificateモデル)
from .user import skill # skill.py (Qualificationモデル)

# --- 5. __all__ に全モデルを含める ---
__all__ = [
    # master.py (移動モデル削除)
    'StatusMaster', 'ReferralSourceMaster', 'RoleMaster', 
    'AttendanceStatusMaster', 'ServiceLocationMaster', 
    'EmploymentTypeMaster', 'WorkStyleMaster', 'DisclosureTypeMaster', 
    'ContactCategoryMaster', 'MeetingTypeMaster',

    # core.py (Contact を追加)
    'Supporter', 'User', 'Prospect', 'AttendancePlan', 'DailyLog', 'Contact',

    # plan.py (plan_audit.py から移動)
    'SupportPlan', 'ShortTermGoal', 'SpecificGoal', 'Monitoring',
    'Assessment', 'MeetingMinute',
    
    # audit_log.py (新規/移動モデル)
    'SystemLog', 'GovernmentOffice', 'ServiceTemplate', 'PreparationActivityMaster'
]
# --- End of app/models/__init__.py ---