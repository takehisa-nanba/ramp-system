import os
# ★ 修正点: 'from app' を 'from .app' に変更
# これにより、run.py と同じ階層にある app パッケージを正しく参照する
from backend.app import create_app, db
from backend.app import models 

# どの設定で起動するかを決定 (環境変数から)
config_name = os.getenv('FLASK_CONFIG') or 'default'
app = create_app(config_name)

@app.shell_context_processor
def make_shell_context():
    """
    'flask shell'コマンド実行時に、
    自動的にdbインスタンスと全モデルをインポートするための設定
    """
    
    # 辞書を作成
    context = {'db': db}
    
    # 'app.models' (models/__init__.py) がインポートしたすべての属性を
    # 動的にループ処理でコンテキストに追加する。
    for name in dir(models):
        obj = getattr(models, name)
        # db.Model を継承したクラス（＝モデル）のみを対象とする
        if isinstance(obj, type) and hasattr(obj, '__mro__') and db.Model in obj.__mro__:
            context[name] = obj
            
    return context

if __name__ == '__main__':
    app.run(debug=True)
