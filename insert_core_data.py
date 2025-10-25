# insert_core_data.py

from app.__init__ import create_app
from app.models import User, Supporter, StatusMaster, RoleMaster
from datetime import date
from sqlalchemy.sql import text
from sqlalchemy.exc import IntegrityError
from app.extensions import db # dbを直接インポート

# Flaskアプリケーションのコンテキストを作成
app = create_app()

def insert_core_data():
    with app.app_context():
        try:
            print("--- コアテストデータの投入を開始します ---")
            
            # --- 1. IDリセットと既存データ削除 (PostgreSQL専用コマンド) ---
            print("1. 既存の利用者・職員データを削除し、IDをリセットします...")
            with db.engine.connect() as connection:
                connection.execute(text("TRUNCATE TABLE daily_logs RESTART IDENTITY")) # 日報もリセット
                connection.execute(text("TRUNCATE TABLE supporters RESTART IDENTITY CASCADE"))
                connection.execute(text("TRUNCATE TABLE users RESTART IDENTITY CASCADE"))
                connection.commit()
            print("   -> リセット完了。IDは 1 から始まります。")

            # --- 2. マスターデータの取得 ---
            supporter_role = RoleMaster.query.filter_by(name='支援員').first()
            user_status = StatusMaster.query.filter_by(name='利用中').first()

            if not supporter_role or not user_status:
                print("!!! エラー: 必須マスターデータ（支援員ロールまたは利用中ステータス）が存在しません。")
                print("!!! 'insert_initial_data.py' を先に実行してマスターデータを投入してください。")
                return

            # --- 3. 職員データの作成 (Supporter ID: 1, ログイン可能) ---
            print("3. 職員データ (山田 花子, ID: 1, ログイン用) を投入...")
            supporter1 = Supporter(
                last_name='山田', 
                first_name='花子', 
                role_id=supporter_role.id, 
                hire_date=date(2023, 4, 1), 
                is_active=True,
                email='yamada@ramp.co.jp' # ログイン用メールアドレス
            )
            db.session.add(supporter1)
            db.session.flush() # ID (1) を取得
            
            # ★ パスワードの設定 ('testpassword' でログイン可能) ★
            supporter1.set_password('testpassword') 
            print(f"   -> 職員ID: {supporter1.id} (Email: yamada@ramp.co.jp, Pass: testpassword) を作成しました。")

            # --- 4. 利用者データの作成 (User ID: 1) ---
            print("4. 利用者データ (田中 太郎, ID: 1) を投入...")
            user1 = User(
                last_name='田中', 
                first_name='太郎', 
                status_id=user_status.id, 
                primary_supporter_id=supporter1.id,
                email='tanaka@mail.com' # Emailも設定
            )
            db.session.add(user1)

            db.session.commit()
            print("--- コアデータの投入が成功しました ---")

        except IntegrityError:
            db.session.rollback()
            print("!!! エラー: データが既に存在するか、制約違反が発生しました。")
        except Exception as e:
            db.session.rollback()
            print(f"!!! 予期せぬエラーが発生しました: {e}")

if __name__ == '__main__':
    insert_core_data()