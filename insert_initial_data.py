# insert_initial_data.py
import os
from app.__init__ import create_app
from app.extensions import db

# ★ 修正: 新しいモデルパッケージ構造からインポートする ★
from app.models.master import (
    StatusMaster, ReferralSourceMaster, RoleMaster, 
    AttendanceStatusMaster, EmploymentTypeMaster, WorkStyleMaster,
    DisclosureTypeMaster, ContactCategoryMaster, MeetingTypeMaster,
    ServiceLocationMaster, # master.py に残るモデル
)
from app.models.audit_log import (
    PreparationActivityMaster, ServiceTemplate, GovernmentOffice # audit_log.py からインポート
)
from app.models.core import User, Supporter
from datetime import date

from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import text # SQLコマンドの実行に必要

# Flaskアプリケーションのコンテキストを作成
app = create_app()

def insert_data():
    """
    システムの全マスターテーブルに初期設定データを投入する。
    既にデータが存在する場合は IntegrityError でスキップし、安全を保つ。
    """
    with app.app_context():
        try:
            print("--- データベースへの初期データ投入を開始します ---")
            
            # --- 1. マスターデータの投入 ---
            print("1. マスターテーブルにデータを投入...")

            # StatusMaster (計画、利用者、見込客の全ステータス)
            db.session.add_all([
                # Plan ステータス (承認フロー用)
                StatusMaster(category='plan', name='Draft'),
                StatusMaster(category='plan', name='Pending_Approval'),
                StatusMaster(category='plan', name='Approved_Active'),
                # Prospect ステータス
                StatusMaster(category='prospect', name='初回面談待ち'),
                StatusMaster(category='prospect', name='体験利用中'),
                # User ステータス
                StatusMaster(category='user', name='利用中'),
                StatusMaster(category='user', name='休止'),
                StatusMaster(category='user', name='就職決定'),
            ])
            print("   -> StatusMaster データ投入完了...")

            # RoleMaster (RBAC用)
            print('   -> RoleMaster データ投入中...'),
            db.session.add_all([
                RoleMaster(name='経営者'),
                RoleMaster(name='管理者'),
                RoleMaster(name='支援員'),
                RoleMaster(name='サービス管理責任者'), # ★ SATO職員に割り当てられるロール ★
            ])
            
            # ReferralSourceMaster
            print('   -> ReferralSourceMaster データ投入中...'),
            db.session.add_all([
                ReferralSourceMaster(name='ハローワーク'),
                ReferralSourceMaster(name='病院・医療機関'),
                ReferralSourceMaster(name='家族・知人'),
            ])
            
            # AttendanceStatusMaster (勤怠用)
            print('   -> AttendanceStatusMaster データ投入中...'),
            db.session.add_all([
                AttendanceStatusMaster(name='通所'),
                AttendanceStatusMaster(name='午前休'),
                AttendanceStatusMaster(name='欠席'),
            ])
            
            # ServiceLocationMaster (施設外支援用)
            print('   -> ServiceLocationMaster データ投入中...'),
            db.session.add_all([
                ServiceLocationMaster(location_name='Onsite_Facility', is_offsite=False),
                ServiceLocationMaster(location_name='Remote_Home', is_offsite=False),
                ServiceLocationMaster(location_name='Offsite_Trial_wSup', is_offsite=True),
                ServiceLocationMaster(location_name='Offsite_Employment', is_offsite=True),
            ])
            
            # PreparationActivityMaster (就労準備加算用)
            print('   -> PreparationActivityMaster データ投入中...'),
            db.session.add_all([
                PreparationActivityMaster(activity_name='職業適性検査', is_billable=True),
                PreparationActivityMaster(activity_name='求人検索指導', is_billable=True),
                PreparationActivityMaster(activity_name='PC基礎訓練', is_billable=False),
            ])

            # その他マスター
            print('   -> その他マスターデータ投入中...'),
            db.session.add_all([
                EmploymentTypeMaster(name='正社員'), 
                WorkStyleMaster(name='フルタイム'),
                DisclosureTypeMaster(name='オープン'), 
                ContactCategoryMaster(name='病院'),
                MeetingTypeMaster(name='個別支援会議')
            ])

            db.session.commit()
            print("   -> マスターデータ投入完了。")
            print("--- 初期データの投入が成功しました ---")

        except IntegrityError:
            db.session.rollback()
            print("!!! エラー: データが既に存在するか、制約違反が発生しました。スキップします。")
        except Exception as e:
            db.session.rollback()
            print(f"!!! 予期せぬエラーが発生しました: {e}")

if __name__ == '__main__':
    insert_data()