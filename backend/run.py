import os
import sys

# -------------------------------------------------------------------
# パス解決のロジック（重要）
# -------------------------------------------------------------------
# このファイルの場所: .../backend/run.py
current_dir = os.path.dirname(os.path.abspath(__file__))
# 親ディレクトリ: .../ramp-system (ここをルートとして認識させる)
project_root = os.path.dirname(current_dir)

# sys.pathの先頭に追加
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# -------------------------------------------------------------------
# アプリケーションのインポート
# -------------------------------------------------------------------
from backend.app import create_app, db
from backend.app import models 
from backend.config import Config

# どの設定で起動するかを決定 (環境変数から)
config_name = os.getenv('FLASK_CONFIG') or 'default'
app = create_app(Config)

@app.shell_context_processor
def make_shell_context():
    """'flask shell'コマンド用のコンテキスト"""
    context = {'db': db}
    for name in dir(models):
        obj = getattr(models, name)
        if isinstance(obj, type) and hasattr(obj, '__mro__') and db.Model in obj.__mro__:
            context[name] = obj
    return context

if __name__ == '__main__':
    # デバッグモードで起動
    app.run(debug=True)