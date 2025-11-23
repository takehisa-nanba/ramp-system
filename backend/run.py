import os
#  修正点: すべてのインポートを 'backend' 起点に統一
from backend.app import create_app, db
from backend.app import models 
# ★ 追加: Configクラスを直接インポート
from backend.config import Config

# 修正前 (NG): 文字列 'default' を渡していた
# config_name = os.getenv('FLASK_CONFIG') or 'default'
# app = create_app(config_name)

# ★ 修正後 (OK): Configクラスそのものを渡す
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
    app.run(debug=True)