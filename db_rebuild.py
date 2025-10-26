# db_rebuild.py
import os
from app.__init__ import create_app
from app.extensions import db
from sqlalchemy import text, inspect
from sqlalchemy.exc import ProgrammingError

# Flaskアプリケーションのコンテキストを作成
app = create_app()

def rebuild_database():
    """
    依存関係を無視して全テーブルを強制削除し、最新のモデルで再構築する。
    """
    with app.app_context():
        try:
            print("--- データベースの強制リセットと再構築を開始します ---")
            
            # 1. 依存関係のあるテーブルを削除（CASCADEを使用）
            print("1. 既存のテーブルを強制削除します (DROP CASCADE)...")
            
            # 全てのテーブル名を SQLAlchemyのメタデータから取得
            table_names = list(db.metadata.tables.keys())
            
            with db.engine.connect() as connection:
                # PostgreSQLでのDROP CASCADEコマンドの実行
                # NOTE: テーブル名のDROP処理はSQLAlchemyのメタデータに依存するため、
                # ここでは最も確実に機能する raw SQL を実行します。
                for table_name in table_names:
                    # Alembicのテーブルは最後に処理
                    if table_name == 'alembic_version':
                        continue 
                    connection.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))
                    print(f"   -> DROPPED: {table_name}")
                
                # Alembicの履歴テーブルも削除
                connection.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE"))
                connection.commit()
            
            print("   -> 既存のDB構造のクリーンアップが完了しました。")

            # 2. 最新のモデルでテーブルを再作成
            print("2. 最新の models.py に基づき、全テーブルを再作成 (db.create_all)...")
            db.create_all()
            print("   -> DBスキーマの再構築が完了しました。")

        except ProgrammingError as e:
            db.session.rollback()
            print("\n!!! 重大なエラー: スキーマのリセットに失敗しました。")
            print("!!! PostgreSQLサーバーが起動しているか、データベース名が正しいか確認してください。")
            print(f"!!! 詳細: {e}")
        except Exception as e:
            db.session.rollback()
            print(f"!!! 予期せぬエラーが発生しました: {e}")

if __name__ == '__main__':
    rebuild_database()
    print("\n--- データベースのリセットと再構築が完了しました ---")

    print("次に、'insert_initial_data.py' を実行してマスターデータを投入してください。")
    