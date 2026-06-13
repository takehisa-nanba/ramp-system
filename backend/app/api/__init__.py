# backend/app/api/__init__.py

# 責務: このパッケージ内の全てのブループリントをインポートし、一括でエクスポートする。
# これにより、app/__init__.py でのインポートを簡潔にする。

from .auth import auth_bp
from .users import users_bp
from .plans import plans_bp
from .daily_logs import daily_logs_bp
from .monitoring import monitoring_bp
from .case_conferences import case_conferences_bp
from .attendance import attendance_bp
from .user_support import user_support_bp # ★追加
from .staff_settings import staff_settings_bp
from .management_staff import management_staff_bp
from .management_office import management_office_bp
from .management_masters import management_masters_bp
from .dashboard import dashboard_bp
from .action_items import action_items_bp
from .schedules import schedules_bp

# すべてのブループリントをリストに集約し、外部に公開する。
ALL_BLUEPRINTS = [
    auth_bp,
    users_bp,
    plans_bp,
    daily_logs_bp,
    monitoring_bp,
    case_conferences_bp,
    attendance_bp,
    user_support_bp,
    staff_settings_bp,
    management_staff_bp,
    management_office_bp,
    management_masters_bp,
    dashboard_bp,
    action_items_bp,
    schedules_bp,
]

