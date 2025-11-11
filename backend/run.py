# backend/run.py

import os
from app import create_app # <-- 修正後のインポート

# FLASK_ENV環境変数（例: development）などから設定を読み込む
config_name = os.getenv('FLASK_ENV', 'default')

# create_appファクトリを呼び出して 'app' インスタンスを作成
app = create_app()

# これで 'flask' コマンドが 'app' を見つけられるようになります。
# run.py (または app.py) 内デバッグモードでの実行
if __name__ == '__main__':
    app.run(debug=True)

