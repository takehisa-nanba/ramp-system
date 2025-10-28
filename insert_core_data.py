# insert_core_data.py
import os
from app.__init__ import create_app, db
from app.models.core import User, Supporter, DailyLog
from app.models.master import StatusMaster, RoleMaster
from datetime import date
from sqlalchemy.sql import text
from sqlalchemy.exc import NoResultFound, IntegrityError

# Flaskアプリケーションのコンテキストを作成
app = create_app()

def insert_core_data():
    """
    システムのログイン、RBACテスト、APIテストに必要なコアデータを投入する。
    テーブルをTRUNCATEし、User ID: 1, Supporter ID: 1, 2 を確実に作成する。
    """
    with app.app_context():
        try:
            print("--- コアテストデータの投入を開始します ---")
            
            # --- 1. IDリセットと既存データ削除 ---
            # TRUNCATE CASCADE で依存関係を無視し、全テーブルのデータを削除・IDをリセット
            print("1. 既存の利用者・職員データを削除し、IDをリセットします...")
            with db.engine.connect() as connection:
                # 安全のため、依存関係にあるテーブルを順にTRUNCATE
                connection.execute(text("TRUNCATE TABLE daily_logs RESTART IDENTITY"))
                connection.execute(text("TRUNCATE TABLE users RESTART IDENTITY CASCADE"))
                connection.execute(text("TRUNCATE TABLE supporters RESTART IDENTITY CASCADE"))
                connection.commit()
            print("   -> リセット完了。User, Supporter IDは 1 から始まります。")

            # --- 2. マスターデータの取得（存在しない場合はエラー） ---
            # ※ insert_initial_data.py の実行が前提
            role_supporter = RoleMaster.query.filter_by(name='支援員').first()
            role_manager = RoleMaster.query.filter_by(name='管理者').first()
            role_sabikan = RoleMaster.query.filter_by(name='サービス管理責任者').first()
            user_status = StatusMaster.query.filter_by(category='user', name='利用中').first()

            if not all([role_supporter, role_manager, role_sabikan, user_status]):
                print("!!! エラー: 依存するマスターデータ（ロールまたはステータス）が不足しています。")
                print("!!! 'insert_initial_data.py' を先に実行し、マスターを投入してください。")
                return

            # --- 3. 職員データの作成 (ID: 1 - 支援員) ---
            print("3. 職員データ (山田 花子, ID: 1 - 支援員) を投入...")
            supporter1 = Supporter(
                last_name='山田', 
                first_name='花子',
                role_id=role_supporter.id, 
                hire_date=date(2023, 4, 1), 
                is_active=True,
                email='yamada@ramp.co.jp',
                password_hash='' # パスワードは後で設定
            )
            print("3. 職員データ (山田 花子, ID: 1 - 支援員) の投入を確認...")
            db.session.add(supporter1)
            print("   -> supporter1 added to session.")
            db.session.flush() # ID=1を確定
            print("   -> supporter1 ID flushed:", supporter1.id)

            # 職員データの作成 (ID: 2 - サビ管/管理者 ログイン用)
            print("   職員データ (佐藤 健太, ID: 2 - サビ管/管理者) を投入...")
            supporter2 = Supporter(
                last_name='佐藤', 
                first_name='健太', 
                role_id=role_sabikan.id,  # サービス管理責任者ロール
                hire_date=date(2024, 1, 15), 
                is_active=True,
                email='sato@ramp.co.jp', # ログインを試行するアカウント
                password_hash='' # パスワードは後で設定
            )
            db.session.add(supporter2)
            db.session.flush() # ID=2を確定

            # --- 4. パスワードの設定 ---
            # パスワードは 'testpassword' で共通
            supporter1.set_password('testpassword') 
            supporter2.set_password('adminpassword') # 管理者用パスワード
            print("   -> パスワード設定完了。")

            # --- 5. 利用者データの作成 (User ID: 1) ---
            print("5. 利用者データ (田中 太郎, ID: 1) を投入...")
            user1 = User(
                last_name='田中', 
                first_name='太郎', 
                status_id=user_status.id, 
                primary_supporter_id=supporter1.id,
                email='tanaka@user.com' 
            )

            # --- 5. 利用者データの作成 (User ID: 2) ---
            print("5. 利用者データ (鈴木 次郎, ID: 2) を投入...")
            user2 = User(
                last_name='鈴木', 
                first_name='次郎', 
                status_id=user_status.id, 
                primary_supporter_id=supporter1.id,
                email='suzuki@user.com' 
            )
            db.session.add(user1)
            db.session.add(user2)
            print("   -> user1 and user2 added to session.")
            db.session.flush() # ID=1,2を確定
            print("   -> user1 ID flushed:", user1.id)
            print("   -> user2 ID flushed:", user2.id)
            
            # --- 6. 確定（コミット） ---
            db.session.commit()
            print("--- コアテストデータの投入が成功しました (User ID: 1, Supporter ID: 1, 2) ---")

        except IntegrityError:
            db.session.rollback()
            print("!!! エラー: データが既に存在するか、制約違反が発生しました。")
        except Exception as e:
            db.session.rollback()
            print(f"!!! 予期せぬエラーが発生しました: {e}")

if __name__ == '__main__':
    insert_core_data()