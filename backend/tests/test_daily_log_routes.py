import pytest
import logging
from datetime import date, datetime, timezone
from backend.app import db
from backend.app.models import (
    User, Supporter, SupporterPII, StatusMaster, JobTitleMaster,
    RoleMaster, PermissionMaster,
    SupportPlan, LongTermGoal, ShortTermGoal, IndividualSupportGoal,
    DailyLog
)

logger = logging.getLogger(__name__)

def test_daily_log_workflow(client, app):
    """
    日報APIの検証。
    1. ガードレール（計画外の拒否）
    2. 作成（正常系）
    3. 承認（権限チェック）
    """
    logger.info("🚀 TEST START: 日報APIの検証を開始します")

    with app.app_context():
        # --- 1. 準備: マスタと権限 ---
        status = StatusMaster(name="利用中")
        
        # 権限とロールの作成
        perm_approve = PermissionMaster(name="APPROVE_DAILY_LOG")
        perm_create = PermissionMaster(name="CREATE_DAILY_LOG")
        db.session.add_all([status, perm_approve, perm_create])
        db.session.flush()

        # サビ管ロール（承認権限あり）
        role_sabikan = RoleMaster(name="Sabikan", role_scope="JOB")
        role_sabikan.permissions.append(perm_approve)
        role_sabikan.permissions.append(perm_create)
        
        # 支援員ロール（作成権限のみ、承認なし）
        role_staff = RoleMaster(name="Staff", role_scope="JOB")
        role_staff.permissions.append(perm_create)
        
        db.session.add_all([role_sabikan, role_staff])
        db.session.flush()

        # --- 2. 登場人物 ---
        # サビ管 (承認者)
        sabikan = Supporter(
            last_name="Boss", first_name="Sabi", last_name_kana="ボス", first_name_kana="サビ",
            employment_type="FULL_TIME", weekly_scheduled_minutes=2400, hire_date=date(2025, 1, 1)
        )
        sabikan.pii = SupporterPII(email="sabikan@test.com")
        sabikan.pii.set_password("pass123")
        sabikan.roles.append(role_sabikan)

        # 支援員 (作成者)
        staff = Supporter(
            last_name="Member", first_name="A", last_name_kana="メン", first_name_kana="エー",
            employment_type="FULL_TIME", weekly_scheduled_minutes=2400, hire_date=date(2025, 1, 1)
        )
        staff.pii = SupporterPII(email="staff@test.com")
        staff.pii.set_password("pass123")
        staff.roles.append(role_staff)

        # 利用者
        user = User(display_name="TestUser", status_id=status.id)
        
        db.session.add_all([sabikan, staff, user])
        db.session.flush()

        # --- 3. 計画と目標（ガードレール用） ---
        # 有効な計画 (ACTIVE)
        plan = SupportPlan(user_id=user.id, plan_status='ACTIVE')
        db.session.add(plan)
        db.session.flush()

        ltg = LongTermGoal(plan_id=plan.id, description="LTG")
        db.session.add(ltg)
        db.session.flush()
        stg = ShortTermGoal(long_term_goal_id=ltg.id, description="STG")
        db.session.add(stg)
        db.session.flush()
        
        # 有効な目標
        goal = IndividualSupportGoal(
            short_term_goal_id=stg.id,
            concrete_goal="Goal A", user_commitment="Do A", support_actions="Support A",
            service_type="TRAINING"
        )
        db.session.add(goal)
        db.session.commit()
        
        goal_id = goal.id
        user_id = user.id

    # --- 4. ログイン (支援員) ---
    auth_res = client.post('/api/auth/login', json={
        "email": "staff@test.com",
        "password": "pass123"
    })
    staff_token = auth_res.json['access_token']
    staff_headers = {'Authorization': f'Bearer {staff_token}'}

    # --- 5. ガードレールのテスト (失敗すべき) ---
    logger.info("🔹 ステップ1: 計画外の活動記録（ガードレール）")
    # 存在しない目標ID(999)で記録しようとする
    res_fail = client.post('/api/daily-logs/', headers=staff_headers, json={
        "user_id": user_id,
        "goal_id": 999, # 無効
        "log_date": "2025-11-22",
        "support_content_notes": "計画外の支援"
    })
    assert res_fail.status_code == 400
    logger.debug("   -> 400 Bad Request (Blocked as expected)")

    # --- 6. 日報作成 (成功) ---
    logger.info("🔹 ステップ2: 正常な日報作成")
    res_create = client.post('/api/daily-logs/', headers=staff_headers, json={
        "user_id": user_id,
        "goal_id": goal_id, # 有効
        "log_date": "2025-11-22",
        "support_content_notes": "適切な支援を実施しました。",
        "heartwarming_episode": "笑顔が見られた。"
    })
    assert res_create.status_code == 201
    log_id = res_create.json['id']
    logger.debug(f"   -> Log ID: {log_id} Created")

    # --- 7. 承認権限のテスト (失敗すべき) ---
    logger.info("🔹 ステップ3: 権限なしでの承認試行")
    # 支援員(staff)には承認権限がない
    res_deny = client.post(f'/api/daily-logs/{log_id}/approve', headers=staff_headers)
    assert res_deny.status_code == 403
    logger.debug("   -> 403 Forbidden (Blocked as expected)")

    # --- 8. 承認 (サビ管でログインして実行) ---
    logger.info("🔹 ステップ4: サビ管による承認")
    # サビ管でログイン
    auth_res_sabikan = client.post('/api/auth/login', json={
        "email": "sabikan@test.com",
        "password": "pass123"
    })
    sabikan_token = auth_res_sabikan.json['access_token']
    sabikan_headers = {'Authorization': f'Bearer {sabikan_token}'}

    # 承認実行
    res_approve = client.post(f'/api/daily-logs/{log_id}/approve', headers=sabikan_headers)
    assert res_approve.status_code == 200
    assert res_approve.json['status'] == 'FINALIZED'
    logger.info("✅ 日報APIの検証完了: 承認フローとガードレールは正常です")