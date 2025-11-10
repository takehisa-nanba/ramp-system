# backend/run.py

import os
from app import create_app # <-- 修正後のインポート

from app.models import (
    master, core, audit_log, client_relations, compliance, communication,
    business_dev, hr, office_admin, plan, records, retention, schedule
)

# FLASK_ENV環境変数（例: development）などから設定を読み込む
config_name = os.getenv('FLASK_ENV', 'default')

# create_appファクトリを呼び出して 'app' インスタンスを作成
app = create_app()

# これで 'flask' コマンドが 'app' を見つけられるようになります。