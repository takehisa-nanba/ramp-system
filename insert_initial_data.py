# insert_initial_data.py
import os
from app.__init__ import create_app, db
from app.models import (
    StatusMaster, ReferralSourceMaster, RoleMaster, 
    AttendanceStatusMaster, EmploymentTypeMaster, WorkStyleMaster,
    DisclosureTypeMaster, ContactCategoryMaster, MeetingTypeMaster,
    Supporter, User
)
from datetime import date
from sqlalchemy.exc import IntegrityError

# Flaskアプリケーションのコンテキストを作成
app = create_app()

def insert_data():
    with app.app_context():
        try:
            print("--- データベースへの初期データ投入を開始します ---")
            
            # --- 1. マスターデータの投入 ---
            print("1. マスターテーブルにデータを投入...")

            # StatusMaster
            db.session.add_all([
                # Prospect ステータス
                StatusMaster(category='prospect', name='初回面談待ち'),
                StatusMaster(category='prospect', name='体験利用中'),
                StatusMaster(category='prospect', name='契約完了'),
                # User ステータス
                StatusMaster(category='user', name='利用中'),
                StatusMaster(category='user', name='休止'),
                StatusMaster(category='user', name='就職決定'),
                # SupportPlan ステータス (将来の承認フロー用)
                StatusMaster(category='plan', name='Draft'),
                StatusMaster(category='plan', name='Pending_Approval'),
                StatusMaster(category='plan', name='Approved'),
            ])

            # RoleMaster (RBAC用)
            db.session.add_all([
                RoleMaster(name='経営者'),
                RoleMaster(name='管理者'),
                RoleMaster(name='支援員'),
            ])
            
            # ReferralSourceMaster
            db.session.add_all([
                ReferralSourceMaster(name='ハローワーク'),
                ReferralSourceMaster(name='病院・医療機関'),
                ReferralSourceMaster(name='家族・知人'),
            ])
            
            # AttendanceStatusMaster (勤怠用)
            db.session.add_all([
                AttendanceStatusMaster(name='通所'),
                AttendanceStatusMaster(name='午前休'),
                AttendanceStatusMaster(name='欠席'),
            ])

            # その他マスター (省略)
            db.session.add_all([
                EmploymentTypeMaster(name='正社員'), WorkStyleMaster(name='フルタイム'),
                DisclosureTypeMaster(name='オープン'), ContactCategoryMaster(name='病院'),
                MeetingTypeMaster(name='個別支援会議')
            ])

            db.session.commit()
            print("   -> マスターデータ投入完了。")

            # --- 2. テスト用コアデータの投入 ---
            print("2. テスト用コアデータ (職員, 利用者) を投入...")

            # 職員ロールと勤怠ステータスIDを取得
            supporter_role = RoleMaster.query.filter_by(name='支援員').first()
            user_status = StatusMaster.query.filter_by(name='利用中').first()

            if supporter_role and user_status:
                # 職員データの作成 (ID: 1 の職員を作成)
                supporter1 = Supporter(
                    last_name='山田', 
                    first_name='花子', 
                    role_id=supporter_role.id, 
                    hire_date=date(2023, 4, 1), 
                    is_active=True
                )
                db.session.add(supporter1)
                db.session.flush() # IDを取得するために一時的にDBに書き込む

                # 利用者データの作成 (ID: 1 の利用者を作成)
                db.session.add(User(
                    last_name='田中', 
                    first_name='太郎', 
                    status_id=user_status.id, 
                    primary_supporter_id=supporter1.id 
                ))
            
            db.session.commit()
            print("   -> コアデータ投入完了。")
            print("--- 初期データの投入が成功しました ---")

        except IntegrityError:
            db.session.rollback()
            print("!!! エラー: データが既に存在するか、制約違反が発生しました。スキップします。")
        except Exception as e:
            db.session.rollback()
            print(f"!!! 予期せぬエラーが発生しました: {e}")

if __name__ == '__main__':
    insert_data()