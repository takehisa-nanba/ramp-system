# alembic_manage.py

import sys
import os
from flask import Flask
from alembic.config import Config
from alembic import command

# 1. Flaskアプリケーションをインポートし、コンテキストを作成
# (create_appは app/__init__.py にあると仮定)
from app import create_app 
app = create_app()

# 2. Alembic設定オブジェクトを作成
alembic_cfg = Config("alembic.ini") # alembic.ini を参照

# 3. Alembic設定に、マイグレーションスクリプトの場所を強制的にセット
alembic_cfg.set_main_option("script_location", "app/migrations")
# 4. SQLAlchemy URLも設定（env.pyがこれを上書きするため必須ではないが、安全のため）
alembic_cfg.set_main_option("sqlalchemy.url", app.config["SQLALCHEMY_DATABASE_URI"])

# 5. Flaskアプリケーションコンテキスト内で Alembicコマンドを実行するラッパー関数
def run_alembic_command(name, **kwargs):
    with app.app_context():
        # コマンドを実行
        if name == 'stamp':
            command.stamp(alembic_cfg, 'head')
        elif name == 'autogenerate':
            # autogenerateコマンドの実行
            message = kwargs.get('message', 'auto_migration')
            command.revision(alembic_cfg, message=message, autogenerate=True)

if __name__ == '__main__':
    # コマンドライン引数から Alembic コマンドを取得し実行
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == 'stamp_head':
            print("--- Alembic: 現在のDB状態を 'head' としてスタンプ ---")
            run_alembic_command('stamp')
            print("--- スタンプ完了 ---")
        elif cmd == 'migrate':
            message = sys.argv[2] if len(sys.argv) > 2 else "auto_migration"
            print(f"--- Alembic: 自動マイグレーション ({message}) を実行 ---")
            run_alembic_command('autogenerate', message=message)
            print("--- マイグレーションファイル生成完了 ---")
        else:
            print(f"不明なコマンド: {cmd}")