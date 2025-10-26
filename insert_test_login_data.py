# insert_test_login_data.py
import os
from app.__init__ import create_app
from app.extensions import db
from app.models import Supporter, RoleMaster
from datetime import date
from sqlalchemy.exc import IntegrityError

app = create_app()

def insert_test_login_data():
    """
    管理者アカウントを作成し、ログインテスト用のデータを投入する。
    """
    with app.app_context():
        try:
            print("--- テスト用管理者ログインデータの投入を開始します ---")
            
            # 1. 必須ロールIDの取得 (管理者)
            admin_role = RoleMaster.query.filter_by(name='管理者').first()
            if not admin_role:
                print("!!! エラー: 必須マスターデータ（管理者ロール）が存在しません。")
                print("!!! insert_initial_data.py を先に実行してください。")
                return

            test_email = 'sato@ramp.co.jp'
            test_password = 'adminpassword'

            # 2. 職員（管理者）が存在するかチェック
            # ※ Supporterテーブルは一度リセットされる想定ですが、念のため
            supporter = Supporter.query.filter_by(email=test_email).first()
            
            if supporter:
                print(f"   -> 職員アカウント ({test_email}) は既に存在します。パスワードをリセットします。")
                supporter.set_password(test_password)
            else:
                # 3. 新しい管理者職員を作成 (IDは自動採番される)
                new_supporter = Supporter(
                    last_name='佐藤', 
                    first_name='一郎', 
                    email=test_email, # ログイン用メールアドレスを設定
                    role_id=admin_role.id, 
                    hire_date=date(2023, 1, 1), 
                    is_active=True
                )
                
                # 4. パスワードを設定（Bcryptでハッシュ化される）
                new_supporter.set_password(test_password)
                
                db.session.add(new_supporter)
                print(f"   -> 職員 (佐藤 一郎, Role: 管理者) を作成しました。")
            
            db.session.commit()
            print("--- テスト用管理者ログインデータの投入が完了しました ---")

        except IntegrityError as e:
            db.session.rollback()
            print(f"!!! データベースエラーが発生しました: {e}")
            print("!!! 投入をロールバックしました。")
        except Exception as e:
            db.session.rollback()
            print(f"!!! 不明なエラーが発生しました: {e}")
            
if __name__ == '__main__':
    insert_test_login_data()