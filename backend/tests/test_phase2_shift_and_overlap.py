import pytest
import logging
from datetime import date, datetime, timedelta, time
from flask_jwt_extended import create_access_token
from backend.app import db
from backend.app.models import (
    User, Supporter, StatusMaster, DailyLog, DailyLogActivity, 
    EmploymentShiftPattern, StaffActivityMaster,
    SupportPlan, LongTermGoal, ShortTermGoal, IndividualSupportGoal
)

logger = logging.getLogger(__name__)

def test_employment_shift_patterns(app):
    """
    曜日別契約シフトパターン (EmploymentShiftPattern) の永続化テスト
    """
    logger.info("🚀 TEST START: 曜日別契約シフトパターンの永続化テスト")

    with app.app_context():
        # 1. 職員の作成
        staff = Supporter(
            staff_code="S_SHIFT_TEST",
            last_name="シフト", first_name="太郎", last_name_kana="シフト", first_name_kana="タロウ",
            employment_type="FULL_TIME", weekly_scheduled_minutes=2400, hire_date=date(2025, 1, 1)
        )
        db.session.add(staff)
        db.session.flush()

        # 2. シフトパターンの追加
        monday_pattern = EmploymentShiftPattern(
            supporter_id=staff.id,
            day_of_week="Monday",
            start_time="09:00",
            end_time="18:00",
            break_minutes=60
        )
        tuesday_pattern = EmploymentShiftPattern(
            supporter_id=staff.id,
            day_of_week="Tuesday",
            start_time="09:00",
            end_time="17:00",
            break_minutes=45
        )
        db.session.add_all([monday_pattern, tuesday_pattern])
        db.session.commit()

        # 3. 再取得してアサーション
        retrieved_staff = db.session.get(Supporter, staff.id)
        assert retrieved_staff is not None
        assert len(retrieved_staff.shift_patterns) == 2
        
        patterns = {p.day_of_week: p for p in retrieved_staff.shift_patterns}
        assert "Monday" in patterns
        assert patterns["Monday"].start_time == "09:00"
        assert patterns["Monday"].end_time == "18:00"
        assert patterns["Monday"].break_minutes == 60

        assert "Tuesday" in patterns
        assert patterns["Tuesday"].start_time == "09:00"
        assert patterns["Tuesday"].end_time == "17:00"
        assert patterns["Tuesday"].break_minutes == 45

        logger.info("✅ 曜日別契約シフトパターンの検証完了")


def test_daily_log_overlap_guardrail(app, client):
    """
    日報重複防止ガードレール API レベルのテスト
    """
    logger.info("🚀 TEST START: 日報重複防止ガードレールAPIのテスト")

    with app.app_context():
        status = db.session.query(StatusMaster).filter_by(name="利用中").first()
        if not status:
            status = StatusMaster(name="利用中")
            db.session.add(status)
            db.session.flush()

        # 活動タグ (直接支援) の準備
        direct_tag = db.session.query(StaffActivityMaster).filter_by(is_direct_support=True).first()
        if not direct_tag:
            direct_tag = StaffActivityMaster(activity_name="直接支援タグ", is_direct_support=True)
            db.session.add(direct_tag)
            db.session.flush()

        # テストデータの準備
        user_a = User(display_name="利用者A", status_id=status.id)
        user_b = User(display_name="利用者B", status_id=status.id)
        
        staff = Supporter(
            staff_code="S_OVERLAP",
            last_name="重複", first_name="ガード", last_name_kana="ジュウフク", first_name_kana="ガード",
            employment_type="FULL_TIME", weekly_scheduled_minutes=2400, hire_date=date(2025, 1, 1)
        )
        db.session.add_all([user_a, user_b, staff])
        db.session.flush()

        # 利用者Aの目標設定 (DailyLogActivity 登録に必須)
        plan_a = SupportPlan(user_id=user_a.id, plan_status='ACTIVE', plan_start_date=date(2025, 1, 1))
        db.session.add(plan_a)
        db.session.flush()
        ltg_a = LongTermGoal(plan_id=plan_a.id, description="A長期")
        db.session.add(ltg_a)
        db.session.flush()
        stg_a = ShortTermGoal(long_term_goal_id=ltg_a.id, description="A短期")
        db.session.add(stg_a)
        db.session.flush()
        isg_a = IndividualSupportGoal(short_term_goal_id=stg_a.id, concrete_goal="A目標", user_commitment="頑張る", support_actions="支援", service_type="TRAINING")
        db.session.add(isg_a)

        # 利用者Bの目標設定 (DailyLogActivity 登録に必須)
        plan_b = SupportPlan(user_id=user_b.id, plan_status='ACTIVE', plan_start_date=date(2025, 1, 1))
        db.session.add(plan_b)
        db.session.flush()
        ltg_b = LongTermGoal(plan_id=plan_b.id, description="B長期")
        db.session.add(ltg_b)
        db.session.flush()
        stg_b = ShortTermGoal(long_term_goal_id=ltg_b.id, description="B短期")
        db.session.add(stg_b)
        db.session.flush()
        isg_b = IndividualSupportGoal(short_term_goal_id=stg_b.id, concrete_goal="B目標", user_commitment="頑張る", support_actions="支援", service_type="TRAINING")
        db.session.add(isg_b)
        db.session.flush()

        # 既存の支援記録 (利用者Aに対する直接支援: 10:00〜11:00) を登録
        today = datetime.now().date()
        daily_log_a = DailyLog(user_id=user_a.id, log_date=today, location_type='ON_SITE', support_content_notes='テスト')
        db.session.add(daily_log_a)
        db.session.flush()

        existing_activity = DailyLogActivity(
            daily_log_id=daily_log_a.id,
            supporter_id=staff.id,
            support_start_time=datetime.combine(today, time(10, 0)),
            support_end_time=datetime.combine(today, time(11, 0)),
            support_content='テスト',
            support_goal_id=isg_a.id
        )
        db.session.add(existing_activity)
        db.session.commit()

        # JWT アクセストークンを生成
        token = create_access_token(identity=f"staff:{staff.id}")
        headers = {
            'Authorization': f'Bearer {token}'
        }

        # テスト用パラメータのショートカット
        tag_id = direct_tag.id
        user_b_id = user_b.id

        # ----------------------------------------------------
        # テストケース1: 重複する時間帯での登録 (後ろが被る: 10:30〜11:30) -> 400 Bad Request
        # ----------------------------------------------------
        payload = {
            "tag_id": tag_id,
            "user_id": user_b_id,
            "start_time": datetime.combine(today, time(10, 30)).isoformat(),
            "end_time": datetime.combine(today, time(11, 30)).isoformat(),
            "duration_minutes": 60
        }
        res = client.post('/api/activities/log', json=payload, headers=headers)
        assert res.status_code == 400
        assert "既に同時間帯" in res.get_json()["msg"]
        assert "利用者A" in res.get_json()["msg"]
        logger.info("✅ テストケース1クリア: 重複登録ブロックを確認")

        # ----------------------------------------------------
        # テストケース2: 重複しない時間帯での登録 (11:00〜12:00) -> 200/201 Success
        # ----------------------------------------------------
        payload = {
            "tag_id": tag_id,
            "user_id": user_b_id,
            "start_time": datetime.combine(today, time(11, 0)).isoformat(),
            "end_time": datetime.combine(today, time(12, 0)).isoformat(),
            "duration_minutes": 60
        }
        res = client.post('/api/activities/log', json=payload, headers=headers)
        assert res.status_code in [200, 201]
        logger.info("✅ テストケース2クリア: 非重複登録の成功を確認")

        # ----------------------------------------------------
        # テストケース3: 同一利用者への重複登録 (10:00〜11:00) -> 重複チェック除外のため成功
        # ----------------------------------------------------
        payload = {
            "tag_id": tag_id,
            "user_id": user_a.id,
            "start_time": datetime.combine(today, time(10, 0)).isoformat(),
            "end_time": datetime.combine(today, time(11, 0)).isoformat(),
            "duration_minutes": 60
        }
        res = client.post('/api/activities/log', json=payload, headers=headers)
        assert res.status_code in [200, 201]
        logger.info("✅ テストケース3クリア: 同一利用者の重複チェック除外を確認")

    logger.info("✅ 日報重複防止ガードレールAPIのテスト完了")


def test_staff_extended_features(app, client):
    """
    スタッフ管理の拡張機能（退職日、みなし配置、カナ自動カタカナ変換、暗号化PII）のテスト
    """
    logger.info("🚀 TEST START: スタッフ管理拡張機能（カナ変換・PII・みなし配置等）のテスト")

    from backend.app.models.core.supporter import SupporterJobAssignment, SupporterPII
    from backend.app.models.masters.master_definitions import JobTitleMaster, RoleMaster
    from backend.app.models.core.rbac_links import supporter_role_link

    with app.app_context():
        # テスト用のセキュリティロールと職種を取得または作成
        sys_role = db.session.query(RoleMaster).filter_by(role_scope="SYSTEM").first()
        if not sys_role:
            sys_role = RoleMaster(name="システム管理者", role_scope="SYSTEM")
            db.session.add(sys_role)
            db.session.flush()

        job_title = db.session.query(JobTitleMaster).filter_by(title_name="サービス管理責任者").first()
        if not job_title:
            job_title = JobTitleMaster(title_name="サービス管理責任者")
            db.session.add(job_title)
            db.session.flush()

        admin_staff = Supporter(
            staff_code="S_ADMIN_T",
            last_name="管理", first_name="者", last_name_kana="カンリ", first_name_kana="シャ",
            employment_type="FULL_TIME", weekly_scheduled_minutes=2400, hire_date=date(2025, 1, 1)
        )
        db.session.add(admin_staff)
        db.session.flush()
        
        # 権限紐付け
        db.session.execute(supporter_role_link.insert().values(supporter_id=admin_staff.id, role_id=sys_role.id))
        db.session.commit()

        # 管理者のトークンを生成
        token = create_access_token(identity=f"staff:{admin_staff.id}")
        headers = {'Authorization': f'Bearer {token}'}

        # ----------------------------------------------------
        # テストケース1: スタッフ登録（ひらがなフリガナ、退職日、みなし配置、PIIを含める）
        # ----------------------------------------------------
        payload = {
            "last_name": "試験",
            "first_name": "職員",
            "last_name_kana": "しけん",  # ひらがなで送信（カタカナ変換されるべき）
            "first_name_kana": "しょくいん",  # ひらがなで送信（カタカナ変換されるべき）
            "staff_code": "S_EXT_001",
            "email": "ext_staff@example.com",
            "employment_type": "FULL_TIME",
            "hire_date": "2025-01-01",
            "retirement_date": "2026-12-31",  # 退職日を設定
            "weekly_scheduled_minutes": 2400,
            "role_ids": [],
            "allow_overlap_calculation": False,
            "is_active": True,
            "job_assignments": [
                {
                    "job_title_id": job_title.id,
                    "assigned_minutes": 2400,
                    "is_deemed_assignment": True,  # みなし配置ON
                    "deemed_expiry_date": "2026-06-30"  # みなし期限
                }
            ],
            "shift_patterns": [],
            "personal_phone": "090-9999-8888",
            "address": "大阪府大阪市北区梅田1-1-1",
            "bank_account_info": "テスト銀行 テスト支店 普通 9876543 シケン ショクイン"
        }

        res = client.post('/api/management/staff', json=payload, headers=headers)
        assert res.status_code in [200, 201], f"Failed to register staff: {res.data.decode()}"
        data = res.get_json()
        new_staff_id = data["id"]

        # データベースから直接確認
        staff_in_db = db.session.get(Supporter, new_staff_id)
        assert staff_in_db is not None
        # フリガナがカタカナに変換されていること
        assert staff_in_db.last_name_kana == "シケン"
        assert staff_in_db.first_name_kana == "ショクイン"
        # 退職日が正しく登録されていること
        assert staff_in_db.retirement_date == date(2026, 12, 31)

        # 暗号化PIIが正しく保存されていること
        pii_in_db = db.session.query(SupporterPII).filter_by(supporter_id=new_staff_id).first()
        assert pii_in_db is not None
        # DB上では暗号化されたバイナリデータ等であるはずだが、property を介して復号されること
        assert pii_in_db.personal_phone == "090-9999-8888"
        assert pii_in_db.address == "大阪府大阪市北区梅田1-1-1"
        assert pii_in_db.bank_account_info == "テスト銀行 テスト支店 普通 9876543 シケン ショクイン"

        # みなし配置が正しく保存されていること
        assignment_in_db = db.session.query(SupporterJobAssignment).filter_by(supporter_id=new_staff_id).first()
        assert assignment_in_db is not None
        assert assignment_in_db.is_deemed_assignment is True
        assert assignment_in_db.deemed_expiry_date == date(2026, 6, 30)

        # ----------------------------------------------------
        # テストケース2: スタッフ一覧 API を叩いて復号化された平文 PII と退職日・みなし配置が返ることを確認
        # ----------------------------------------------------
        res_list = client.get('/api/management/staff', headers=headers)
        assert res_list.status_code == 200
        staff_list = res_list.get_json()
        
        # 登録したスタッフを見つける
        target_staff = next((s for s in staff_list if s["id"] == new_staff_id), None)
        assert target_staff is not None
        assert target_staff["retirement_date"] == "2026-12-31"
        assert target_staff["personal_phone"] == "090-9999-8888"
        assert target_staff["address"] == "大阪府大阪市北区梅田1-1-1"
        assert target_staff["bank_account_info"] == "テスト銀行 テスト支店 普通 9876543 シケン ショクイン"

        # みなし配置も返っていること
        tgt_assignment = target_staff["job_assignments"][0]
        assert tgt_assignment["is_deemed_assignment"] is True
        assert tgt_assignment["deemed_expiry_date"] == "2026-06-30"

        # ----------------------------------------------------
        # テストケース3: スタッフ情報の更新（みなし期限、PII等の変更）
        # ----------------------------------------------------
        update_payload = {
            "last_name": "試験",
            "first_name": "職員改",
            "last_name_kana": "シケン",
            "first_name_kana": "ショクインカイ",
            "staff_code": "S_EXT_001",
            "email": "ext_staff@example.com",
            "employment_type": "FULL_TIME",
            "hire_date": "2025-01-01",
            "retirement_date": None,  # 退職日を消去
            "weekly_scheduled_minutes": 2400,
            "role_ids": [],
            "allow_overlap_calculation": False,
            "is_active": True,
            "job_assignments": [
                {
                    "job_title_id": job_title.id,
                    "assigned_minutes": 2400,
                    "is_deemed_assignment": False,  # みなし配置を解除
                    "deemed_expiry_date": None
                }
            ],
            "shift_patterns": [],
            "personal_phone": "080-1111-2222",  # 電話変更
            "address": "京都府京都市",  # 住所変更
            "bank_account_info": "テスト銀行 テスト支店 普通 1111111 シケン ショクインカイ"  # 口座変更
        }

        res_update = client.put(f'/api/management/staff/{new_staff_id}', json=update_payload, headers=headers)
        assert res_update.status_code == 200

        # DBアサーション
        staff_after_update = db.session.get(Supporter, new_staff_id)
        assert staff_after_update.retirement_date is None
        
        pii_after_update = db.session.query(SupporterPII).filter_by(supporter_id=new_staff_id).first()
        assert pii_after_update.personal_phone == "080-1111-2222"
        assert pii_after_update.address == "京都府京都市"

        assignment_after_update = db.session.query(SupporterJobAssignment).filter_by(supporter_id=new_staff_id).first()
        assert assignment_after_update.is_deemed_assignment is False
        assert assignment_after_update.deemed_expiry_date is None

        logger.info("✅ スタッフ管理拡張機能（カナ変換・PII・みなし配置等）のテスト完了")
