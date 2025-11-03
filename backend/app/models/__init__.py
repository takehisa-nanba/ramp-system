# SQLAlchemy Model Index and Exporter

# --- 1. master.py からモデルをインポート ---
# Master Data Models
from .master import (
    StatusMaster, ReferralSourceMaster, RoleMaster, 
    AttendanceStatusMaster, ServiceLocationMaster, 
    EmploymentTypeMaster, WorkStyleMaster, DisclosureTypeMaster, 
    ContactCategoryMaster, MeetingTypeMaster,
)

# --- 2. core.py からモデルをインポート ---
# Core Functional Models
from .core import (
    Supporter, User, Prospect, AttendancePlan, DailyLog, Contact
)

# --- 3. plan.py からモデルをインポート ---
# Support Plan Models
from .plan import (
    SupportPlan, ShortTermGoal, SpecificGoal, Monitoring, 
    Assessment, MeetingMinute
)

# --- 4. audit_log.py からモデルをインポート ---
# Audit and Logging Models
from .audit_log import (
    SystemLog, # 監査ログ
    GovernmentOffice,         # ★ master.py に存在するべきモデル ★
    ServiceTemplate,          # ★ master.py に存在するべきモデル ★
    PreparationActivityMaster # ★ master.py に存在するべきモデル ★
)

# --- 5. user/* のサブモジュールからモデルをインポート ---
from .user.user import User  # (core.py と重複しているので注意, Userモデルはcoreかuserのどちらかのみに配置すべきです) 
from .user.profile import Profile # 例: UserProfileモデルなど
from .user.compliance import CertificateModel # 資格/コンプライアンス関連モデル
from .user.skill import QualificationModel # スキル/資格関連モデル

# --- 6. __all__ にインポートした全モデルを含める (外部公開用) ---
__all__ = [
    # master.py (全て直接インポート)
    'StatusMaster', 'ReferralSourceMaster', 'RoleMaster', 
    'AttendanceStatusMaster', 'ServiceLocationMaster', 
    'EmploymentTypeMaster', 'WorkStyleMaster', 'DisclosureTypeMaster', 
    'ContactCategoryMaster', 'MeetingTypeMaster',
    'GovernmentOffice', 'ServiceTemplate', 'PreparationActivityMaster',

    # core.py
    'Supporter', 'User', 'Prospect', 'AttendancePlan', 'DailyLog', 'Contact',

    # plan.py
    'SupportPlan', 'ShortTermGoal', 'SpecificGoal', 'Monitoring',
    'Assessment', 'MeetingMinute',
    
    # audit_log.py
    'SystemLog',
    
    # user/ サブディレクトリ
    'Profile', 'CertificateModel', 'QualificationModel', 
    
    # 注意: Userモデルはcoreかuserのどちらかに統一することを推奨します。
]
