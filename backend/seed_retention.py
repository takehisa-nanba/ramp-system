# backend/seed_retention.py

import sys
import os
import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app import create_app, db
from backend.config import Config
from backend.app.models import (
    User, Supporter, OfficeServiceConfiguration,
    JobRetentionContract, RetentionEmploymentEpisode,
    RetentionUserVoiceLog, RetentionSupportActionLog,
    PermissionMaster, RoleMaster
)

# 安全装置: 開発環境以外、または明示的な環境変数がない場合の誤実行を防止
if os.getenv('FLASK_ENV') != 'development' and '--force-dev' not in sys.argv:
    print("安全のため、seed_retention.py は開発環境（FLASK_ENV=development または --force-dev）でのみ実行可能です。")
    sys.exit(0)

app = create_app(Config)
with app.app_context():
    print("Seeding Job Retention Verification Data (Safe & Idempotent)...")

    # 1. 定着支援専用パーミッションの初期投入 (未存在時のみ)
    permissions = [
        ('JOB_RETENTION_VIEW', '就労定着支援の閲覧権限'),
        ('JOB_RETENTION_EDIT', '就労定着支援の記録・作成権限'),
        ('JOB_RETENTION_APPROVE', '就労定着支援レポート確定権限'),
    ]
    for perm_name, _ in permissions:
        perm = PermissionMaster.query.filter_by(name=perm_name).first()
        if not perm:
            perm = PermissionMaster(name=perm_name)
            db.session.add(perm)
            print(f"Created Permission: {perm_name}")

    # 管理者ロールへのパーミッション紐付け
    admin_role = RoleMaster.query.filter_by(is_admin=True).first()
    if admin_role:
        existing_perm_names = {p.name for p in admin_role.permissions}
        for perm_name, _ in permissions:
            if perm_name not in existing_perm_names:
                p = PermissionMaster.query.filter_by(name=perm_name).first()
                if p:
                    admin_role.permissions.append(p)
                    print(f"Linked {perm_name} to admin role: {admin_role.name}")
    db.session.commit()

    # 2. 職員と利用者の確認 (※ 既存パスワードの上書きは行わない)
    supporter = Supporter.query.first()
    user = User.query.filter_by(user_code='USR001').first() or User.query.first()

    if not supporter or not user:
        print("Error: Supporter or User not found in DB. Please run base seed first.")
        sys.exit(0)

    # 3. 事業所サービス設定 (定着支援または就労移行)
    service_config = OfficeServiceConfiguration.query.filter_by(office_id=supporter.office_id).first()
    if not service_config:
        service_config = OfficeServiceConfiguration.query.first()

    if not service_config:
        print("Error: No OfficeServiceConfiguration found.")
        sys.exit(0)

    # 4. 既存契約の確認 (※ 既存契約の削除は行わず、既に存在すればスキップ)
    existing_contract = JobRetentionContract.query.filter_by(user_id=user.id).first()
    if existing_contract:
        print(f"Contract already exists for User {user.id} (Contract ID={existing_contract.id}). Skipping seed.")
        sys.exit(0)

    # 5. 新規契約の作成
    start_date = datetime.date(2026, 9, 1)
    end_date = datetime.date(2029, 8, 31)

    contract = JobRetentionContract(
        user_id=user.id,
        office_service_configuration_id=service_config.id,
        contract_start_date=start_date,
        contract_end_date=end_date,
        status='ACTIVE',
        is_company_involved=False,
        consent_status='NOT_SET', # Fail Closed初期値
        contract_details="就職後6か月経過に伴う就労定着支援への移行契約。月1回の定期訪問面談および必要時の関係機関連携を行う。"
    )
    db.session.add(contract)
    db.session.flush()

    # 6. 就労エピソード（勤務先）
    episode = RetentionEmploymentEpisode(
        contract_id=contract.id,
        episode_number=1,
        workplace_name="株式会社テクノロジーズ",
        department_name="総務管理部",
        job_title="事務補助・PCデータ入力",
        job_start_date=start_date,
        work_conditions="週5日 1日6時間勤務（9:30〜16:30、休憩60分）。PC作業中心、疲労時の適宜小休憩可。"
    )
    db.session.add(episode)

    # 7. 本人の声（できごと）初期サンプル
    voice1 = RetentionUserVoiceLog(
        contract_id=contract.id,
        logged_at=datetime.datetime(2026, 9, 2, 17, 30),
        raw_voice="新しいExcel作業に少し戸惑ったけど、質問して進められた。",
        trouble_point="関数（VLOOKUP）の使い方がマニュアルと違って焦った。",
        success_point="隣の先輩に自分から声をかけて確認できた。",
        self_coping_action="深呼吸してマニュアルの更新日付を確認し、先輩に「今よろしいでしょうか」と聞いた。",
        self_coping_result="疑問が解消し、午後には予定通りの入力件数を達成できた。",
        needs_help=False,
        input_channel='USER_DIRECT'
    )
    voice2 = RetentionUserVoiceLog(
        contract_id=contract.id,
        logged_at=datetime.datetime(2026, 9, 4, 18, 0),
        raw_voice="今週は1日も遅刻せず出勤できた。金曜日は少し疲れたけど達成感がある。",
        trouble_point="夕方に少し目の疲れと肩こりが出た。",
        success_point="1週間安定して出勤できた。",
        self_coping_action="帰宅後にお風呂に浸かってストレッチをした。",
        self_coping_result="翌朝には疲れが取れてリフレッシュできた。",
        needs_help=False,
        input_channel='USER_DIRECT'
    )
    db.session.add_all([voice1, voice2])

    # 8. 支援員の支援実施記録
    action = RetentionSupportActionLog(
        contract_id=contract.id,
        supporter_id=supporter.id,
        action_date=datetime.date(2026, 9, 3),
        has_user_interview=True,
        interview_method='FACE_TO_FACE',
        has_company_visit=True,
        has_coordination=False,
        confirmed_situation="職場環境には馴染んでおり勤務態度も良好。PC入力時の不明点について自発的に質問できていた。",
        provided_support="先輩職員への質問の仕方が適切であったことをフィードバックし、焦らずマニュアル確認から行う手順を整理・助言した。",
        user_action_observed="VLOOKUPの記述エラー時、周囲に声かけして解決していた。",
        staff_intervention_boundary="直接の操作指示は行わず、質問内容の言語化と休憩の取り方のみ助言。",
        next_step="週後半の疲れやすさについて次週振り返りを行う。"
    )
    db.session.add(action)
    db.session.commit()

    print(f"Successfully seeded Job Retention Contract #{contract.id} safely.")
