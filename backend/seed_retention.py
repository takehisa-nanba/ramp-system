# backend/seed_retention.py

import sys
import os
import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app import create_app, db
from backend.config import Config
from backend.app.models import (
    User, UserPII, Supporter, SupporterPII,
    JobRetentionContract, RetentionEmploymentEpisode,
    RetentionUserVoiceLog, RetentionSupportActionLog
)

app = create_app(Config)
with app.app_context():
    print("Seeding Job Retention Verification Data...")

    # 1. 職員アカウント確認・パスワード設定
    supporter = Supporter.query.first()
    if supporter and supporter.pii:
        supporter.pii.set_password('password')
        print(f"Supporter ready: ID={supporter.id}, Code={supporter.staff_code}, Email={supporter.pii.email}")

    # 2. 利用者アカウント確認・パスワード設定
    user = User.query.filter_by(user_code='USR001').first()
    if not user:
        user = User.query.first()
    if user and user.pii:
        user.pii.set_password('password')
        print(f"User ready: ID={user.id}, Code={user.user_code}, DisplayName={user.display_name}")

    if not user:
        print("Error: No user found!")
        sys.exit(1)

    # 3. 既存定着契約をクリーンアップ
    JobRetentionContract.query.filter_by(user_id=user.id).delete()
    db.session.commit()

    # 4. 定着支援契約の作成
    start_date = datetime.date(2026, 9, 1)
    end_date = datetime.date(2029, 8, 31)

    contract = JobRetentionContract(
        user_id=user.id,
        contract_start_date=start_date,
        contract_end_date=end_date,
        status='ACTIVE',
        is_company_involved=True,
        consent_status='CONSENTED_ALL',
        contract_details="就職後6か月経過に伴う就労定着支援への移行契約。月1回の定期訪問面談および必要時の関係機関連携を行う。"
    )
    db.session.add(contract)
    db.session.flush()

    # 5. 就労エピソード（勤務先）
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

    # 6. 本人の声（できごと）初期サンプル
    voice1 = RetentionUserVoiceLog(
        contract_id=contract.id,
        logged_at=datetime.datetime(2026, 9, 2, 17, 30),
        raw_voice="新しいExcel作業に少し戸惑ったけど、質問して進められた。",
        trouble_point="関数（VLOOKUP）の使い方がマニュアルと違って焦った。",
        success_point="隣の先輩に自分から声をかけて確認できた。",
        self_coping_action="深呼吸してマニュアルの更新日付を確認し、先輩に「今よろしいでしょうか」と聞いた。",
        self_coping_result="疑問が解消し、午後には予定通りの入力件数を達成できた。",
        needs_help=False
    )
    voice2 = RetentionUserVoiceLog(
        contract_id=contract.id,
        logged_at=datetime.datetime(2026, 9, 4, 18, 0),
        raw_voice="今週は1日も遅刻せず出勤できた。金曜日は少し疲れたけど達成感がある。",
        trouble_point="夕方に少し目の疲れと肩こりが出た。",
        success_point="1週間安定して出勤できた。",
        self_coping_action="帰宅後にお風呂に浸かってストレッチをした。",
        self_coping_result="翌朝には疲れが取れてリフレッシュできた。",
        needs_help=False
    )
    db.session.add_all([voice1, voice2])

    # 7. 支援員の支援実施記録
    action = RetentionSupportActionLog(
        contract_id=contract.id,
        supporter_id=supporter.id if supporter else 1,
        action_date=datetime.date(2026, 9, 3),
        has_user_interview=True,
        interview_method='FACE_TO_FACE',
        has_company_visit=True,
        has_coordination=True,
        confirmed_situation="職場訪問にて上司と面談後、本人と会議室で対面面談を実施。勤務リズム安定、勤怠問題なし。上司より業務指示の理解が進んでいると高評価。",
        provided_support="上司との間で業務指示の出し方（タスクごとの締め切り明示）を再確認し、本人が相談しやすい環境を調整した。",
        user_action_observed="不明点を自ら付箋にメモし、まとめて先輩に質問できている。",
        staff_intervention_boundary="企業側への配慮依頼の文言整理のみ支援員が介在し、日々の質問は本人が自力で行えている。",
        next_step="来月は業務量増加の予定があるため、疲れの蓄積がないか電話で中間確認を行う予定。"
    )
    db.session.add(action)

    db.session.commit()
    print("✅ Seed data inserted successfully!")
