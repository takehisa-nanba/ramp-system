import pytest
import logging
from datetime import date, datetime, timezone
from backend.app import db
from backend.app.models import (
    User, Supporter, SupporterPII, StatusMaster, JobTitleMaster,
    HolisticSupportPolicy, DocumentConsentLog,
    SupportPlan, LongTermGoal, ShortTermGoal, IndividualSupportGoal
)
from backend.app.services.support_service import SupportService

# ロガーの取得
logger = logging.getLogger(__name__)

def test_plan_workflow_and_guardrail(app):
    """
    支援計画のワークフロー（原案->承認->同意->成案）と
    Plan-Activityガードレールの動作を検証する。
    """
    logger.info("🚀 TEST START: 支援計画ワークフローの検証を開始します")

    with app.app_context():
        # --- 1. 準備: マスタと登場人物 ---
        logger.debug("📝 データセットアップ中...")
        
        # マスタ
        status = StatusMaster(name="利用中")
        job_sabikan = JobTitleMaster(title_name="サービス管理責任者")
        db.session.add_all([status, job_sabikan])
        db.session.flush()

        # 利用者 (田中さん)
        user = User(display_name="Tanaka", status_id=status.id)
        db.session.add(user)
        db.session.flush()

        # サビ管 (佐藤さん) - PII分離対応
        sabikan = Supporter(
            last_name="Sato", first_name="Sabikan", last_name_kana="サトウ", first_name_kana="サビカン",
            employment_type="FULL_TIME", weekly_scheduled_minutes=2400, hire_date=date.today()
        )
        # ★ 修正: PIIにメールアドレスを設定
        sabikan.pii = SupporterPII(email="sato@test.com")
        
        db.session.add(sabikan)
        db.session.flush()

        # 総合支援方針 (計画の根拠)
        policy = HolisticSupportPolicy(
            user_id=user.id,
            effective_date=date.today(),
            user_intention_content="働きたい",
            support_policy_content="生活リズムを整える"
        )
        db.session.add(policy)
        db.session.commit() # ID確定のためコミット

        service = SupportService()

        # --- 2. 原案作成 (DRAFT) ---
        logger.info("🔹 ステップ1: 原案作成")
        draft_plan = service.create_plan_draft(
            user_id=user.id,
            sabikan_id=sabikan.id,
            based_on_policy_id=policy.id
        )
        db.session.commit()
        
        assert draft_plan.plan_status == 'DRAFT'
        draft_plan_id = draft_plan.id # IDを控えておく
        logger.debug(f"   -> Plan ID: {draft_plan.id} Created. Status: {draft_plan.plan_status}")

        # --- 3. 会議とサビ管承認 (PENDING_CONSENT) ---
        logger.info("🔹 ステップ2: 支援会議とサビ管承認")
        service.log_support_conference_and_approve(
            plan_id=draft_plan.id,
            sabikan_id=sabikan.id,
            conference_date=datetime.now(timezone.utc),
            content="本人の意向を確認。目標設定に合意。",
            user_participated=True
        )
        db.session.commit()

        # リロードして確認
        # SQLAlchemyのセッションキャッシュをクリアするため db.session.get を使う
        updated_draft = db.session.get(SupportPlan, draft_plan.id)
        assert updated_draft.plan_status == 'PENDING_CONSENT'
        assert updated_draft.sabikan_approved_by_id == sabikan.id
        logger.debug(f"   -> Plan Status moved to: {updated_draft.plan_status}")

        # --- 4. 同意と成案化 (ACTIVE) ---
        logger.info("🔹 ステップ3: 利用者同意と成案化")
        
        # 同意ログの作成
        consent = DocumentConsentLog(
            user_id=user.id,
            document_type='SUPPORT_PLAN',
            document_id=draft_plan.id, # 原案に対する同意
            consent_proof="DIGITAL_SIGNATURE_XYZ"
        )
        db.session.add(consent)
        db.session.flush()

        # 成案化ロジック実行
        final_plan = service.finalize_and_activate_plan(
            plan_id=draft_plan.id,
            consent_log_id=consent.id
        )
        db.session.commit()

        # ★ 検証: IDは変わらず、ステータスだけがACTIVEになる（二重ロック）
        assert final_plan.plan_status == 'ACTIVE'
        assert final_plan.id == draft_plan_id 
        
        logger.info(f"✅ 成案化完了: Active Plan ID {final_plan.id}")

        # --- 5. ガードレールの検証 ---
        logger.info("🔹 ステップ4: Plan-Activity ガードレールのテスト")
        
        # 成案に目標を追加 (テスト用)
        ltg = LongTermGoal(plan_id=final_plan.id, description="長期目標")
        db.session.add(ltg)
        db.session.flush()
        stg = ShortTermGoal(long_term_goal_id=ltg.id, description="短期目標")
        db.session.add(stg)
        db.session.flush()
        isg = IndividualSupportGoal(
            short_term_goal_id=stg.id, 
            concrete_goal="毎日通所", user_commitment="頑張る", support_actions="見守り",
            service_type="TRAINING"
        )
        db.session.add(isg)
        db.session.commit()

        # 正しい紐づけ
        is_valid = service.validate_daily_log_against_plan(user_id=user.id, goal_id=isg.id)
        assert is_valid is True
        logger.debug("   -> 有効な目標への紐づけ: OK")

        # 間違った紐づけ (存在しないGoal)
        is_invalid = service.validate_daily_log_against_plan(user_id=user.id, goal_id=9999)
        assert is_invalid is False
        logger.debug("   -> 無効な目標への紐づけ: OK (Blocked)")