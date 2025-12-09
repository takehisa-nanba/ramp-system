# backend/tests/test_support_service.py

import pytest
import logging
from unittest.mock import Mock, MagicMock
from datetime import date, datetime, timezone, timedelta
from backend.app import db
from backend.app.models import (
    User, Supporter, SupporterPII, StatusMaster, JobTitleMaster,
    HolisticSupportPolicy, DocumentConsentLog,
    SupportPlan, LongTermGoal, ShortTermGoal, IndividualSupportGoal,
    AbsenceResponseLog
)
from backend.app.services.support_service import SupportService

# ロガーの取得
logger = logging.getLogger(__name__)

# =======================================================================
# UTILITY FUNCTIONS / FIXTURES (テスト間の重複回避とDIの準備)
# =======================================================================

def setup_masters_and_user(session, display_name="TestUser", staff_code="S999"):
    """マスタデータと基本エンティティを作成し、セッションにフラッシュする"""
    
    # マスタデータ: UNIQUE制約違反を防ぐため、存在しない場合のみ作成
    status = session.query(StatusMaster).filter_by(name="利用中").first()
    if not status:
        status = StatusMaster(name="利用中")
        session.add(status)
    
    job_sabikan = session.query(JobTitleMaster).filter_by(title_name="サービス管理責任者").first()
    if not job_sabikan:
        job_sabikan = JobTitleMaster(title_name="サービス管理責任者")
        session.add(job_sabikan)
        
    session.flush() # ID確定
    
    # 利用者
    user = User(
            display_name=display_name, 
            status_id=status.id, 
            service_start_date=date(2025, 1, 1)
            )
    session.add(user)
    session.flush()

    # サビ管 (staff_codeはNOT NULL回避のため必須)
    sabikan = Supporter(
        staff_code=staff_code,
        last_name="Sato", first_name="Sabikan", last_name_kana="サトウ", first_name_kana="サビカン",
        employment_type="FULL_TIME", weekly_scheduled_minutes=2400, hire_date=date.today()
    )
    sabikan.pii = SupporterPII(email=f"{staff_code}@test.com")
    session.add(sabikan)
    session.flush()
    
    # 総合支援方針
    policy = HolisticSupportPolicy(
        user_id=user.id, effective_date=date.today(), user_intention_content="test", support_policy_content="test"
    )
    session.add(policy)
    session.commit() # ID確定のためコミット

    return user, sabikan, policy

# =======================================================================
# TEST CASES
# =======================================================================

def test_plan_workflow_and_guardrail(app):
    """
    支援計画のワークフロー（原案->承認->同意->成案）と
    Plan-Activityガードレールの動作を検証する。
    """
    logger.info("🚀 TEST START: 支援計画ワークフローの検証を開始します")

    with app.app_context():
        # --- 1. 準備: マスタと登場人物 ---
        user, sabikan, policy = setup_masters_and_user(db.session, display_name="Tanaka", staff_code="S001")
        
        # DIなしでサービスをインスタンス化
        service = SupportService() 

        # --- 2. 原案作成 (DRAFT) ---
        logger.info("🔹 ステップ1: 原案作成")
        draft_plan = service.create_plan_draft(
            user_id=user.id,
            sabikan_id=sabikan.id,
            based_on_policy_id=policy.id
        )
        # 【修正】ここでコミットし、IDを確定させる
        db.session.commit() 
        draft_plan_id = draft_plan.id
        
        assert draft_plan.plan_status == 'DRAFT'
        logger.debug(f"   -> Plan ID: {draft_plan.id} Created. Status: {draft_plan.plan_status}")

        # --- 3. 会議とサビ管承認 (PENDING_CONSENT) ---
        logger.info("🔹 ステップ2: 支援会議とサビ管承認")
        service.log_support_conference_and_approve(
            plan_id=draft_plan_id, # 確定したIDを使用
            sabikan_id=sabikan.id,
            conference_date=datetime.now(timezone.utc),
            content="本人の意向を確認。目標設定に合意。",
            user_participated=True # 本人参加
        )
        db.session.commit()

        updated_draft = db.session.get(SupportPlan, draft_plan_id)
        assert updated_draft.plan_status == 'PENDING_CONSENT'
        logger.debug(f"   -> Plan Status moved to: {updated_draft.plan_status}")

        # --- 4. 同意と成案化 (ACTIVE) ---
        logger.info("🔹 ステップ3: 利用者同意と成案化")
        consent = DocumentConsentLog(
            user_id=user.id, document_type='SUPPORT_PLAN', document_id=draft_plan_id, consent_proof="DIGITAL_SIGNATURE_XYZ"
        )
        db.session.add(consent)
        db.session.flush()

        final_plan = service.finalize_and_activate_plan(
            plan_id=draft_plan_id,
            consent_log_id=consent.id
        )
        db.session.commit()

        assert final_plan.plan_status == 'ACTIVE'
        assert final_plan.id == draft_plan_id 
        logger.info(f"✅ 成案化完了: Active Plan ID {final_plan.id}")

        # --- 5. ガードレールの検証 ---
        logger.info("🔹 ステップ4: Plan-Activity ガードレールのテスト")
        
        # 成案に目標を追加 (期間内のデータセットアップ)
        ltg = LongTermGoal(plan_id=final_plan.id, description="長期目標")
        db.session.add(ltg)
        db.session.flush() # LongTermGoalのIDをここで確定させる
        
        stg = ShortTermGoal(long_term_goal_id=ltg.id, description="短期目標") 
        db.session.add(stg)
        db.session.flush() # ShortTermGoalのIDをここで確定させる
        
        isg = IndividualSupportGoal(
            short_term_goal_id=stg.id, 
            concrete_goal="毎日通所", user_commitment="頑張る", support_actions="見守り",
            service_type="TRAINING"
        )
        db.session.add(isg)
        db.session.commit()
        
        # 正しい紐づけ (現在日付を有効期間内として仮定)
        is_valid = service.validate_daily_log_against_plan(
            user_id=user.id, 
            goal_id=isg.id, 
            # Active Planの開始日（2025-01-01）を使用
            log_date=datetime.combine(final_plan.plan_start_date, datetime.min.time(), tzinfo=timezone.utc),
            location_type='ON_SITE_FACILITY'
        )
        assert is_valid is True
        logger.debug("   -> 有効な目標への紐づけ: OK")

        # 間違った紐づけ (存在しないGoal)
        is_invalid = service.validate_daily_log_against_plan(
            user_id=user.id, 
            goal_id=9999, 
            log_date=datetime.now(timezone.utc), 
            location_type='ON_SITE_FACILITY'
        )
        assert is_invalid is False
        logger.debug("   -> 無効な目標への紐づけ: OK (Blocked)")


def test_plan_approval_absence_guardrail_with_urac_hook(app):
    """
    STEP 3-1 & 3-2: 不在時の承認ブロック、デジタル宣誓、URACフックの活性化を検証する。
    """
    logger.info("🚀 TEST START: 不在時の承認ブロックとURACフック検証")
    
    # 【DIの準備】ComplianceService のモックを作成 (URACフックの検証用)
    mock_compliance_service = Mock()
    mock_compliance_service.log_unresponsive_risk_increment = MagicMock()
    
    with app.app_context():
        # --- 1. 準備 ---
        user, sabikan, policy = setup_masters_and_user(db.session, display_name="AbsentUser", staff_code="S003")
        
        # 【DIの実行】SupportServiceにモックを注入
        service = SupportService(compliance_service=mock_compliance_service)
        
        draft_plan = service.create_plan_draft(user.id, sabikan.id, policy.id)
        db.session.commit() # IDを確定させる
        draft_plan_id = draft_plan.id
        
        # AbsenceResponseLog のダミーを作成 (必須チェックをパスさせるため)
        absence_log = AbsenceResponseLog(
            user_id=user.id,
            absence_date=date.today(), # NOT NULL回避
            linked_plan_id=draft_plan_id, # 確定したIDを使用
            response_method="TEST_METHOD", # NOT NULL回避
            response_supporter_id=sabikan.id, # NOT NULL回避
            response_summary="テスト用不在対応の要約" # 正しい属性名
        ) 
        db.session.add(absence_log)
        db.session.commit() # AbsenceResponseLogもコミット
        
        # --- 2. 失敗ケース: デジタル宣誓なしで不在承認を試みる (FAILURE) ---
        logger.info("🔹 ケース1: デジタル宣誓なしで承認を試行 -> 拒否")
        try:
            service.log_support_conference_and_approve(
                plan_id=draft_plan_id,
                sabikan_id=sabikan.id,
                conference_date=datetime.now(timezone.utc),
                content="入院のため、内容未確認。",
                user_participated=False, # 本人不在
                reason_for_absence="緊急入院のため、対面不可。", 
                is_sabikan_digital_declaration=False, # 宣誓なし
                absence_monitoring_summary="10文字以上のモニタリングサマリー" # サマリーあり
            )
            pytest.fail("デジタル宣誓なしで不在承認が成功してしまった。")

        except Exception as excinfo:
        # URACフックの検証 (STEP 3-2): 拒否されたため、リスクカウンターが増分されるべき
            mock_compliance_service.log_unresponsive_risk_increment.assert_called_once()
            
            # URAC呼び出しをリセット
            mock_compliance_service.log_unresponsive_risk_increment.reset_mock()
        
            # 検証: 拒否の理由が 'Digital Declaration required' であることを確認
            # 【修正】 excinfo.value ではなく excinfo を直接使用する
            assert "Digital Declaration required" in str(excinfo), "拒否理由が宣誓不足ではない。"
            logger.debug("   -> 拒否判定OK。URACフック活性化成功。")

        # --- 3. 成功ケース: デジタル宣誓を有効にし、不在承認を完了させる (SUCCESS) ---
        logger.info("🔹 ケース2: デジタル宣誓を有効にし、不在承認を完了 -> 成功")
        service.log_support_conference_and_approve(
            plan_id=draft_plan_id,
            sabikan_id=sabikan.id,
            conference_date=datetime.now(timezone.utc),
            content="緊急承認。不在中のモニタリング概要は別途添付。",
            user_participated=False,
            reason_for_absence="入院中のため、実態反映した内容で遡及開始を宣言。",
            is_sabikan_digital_declaration=True, # デジタル宣誓ON
            absence_monitoring_summary="10文字以上のモニタリングサマリー"
        )
        db.session.commit()
        
        updated_plan = db.session.get(SupportPlan, draft_plan_id)
        # 検証: 不在にもかかわらず、PENDING_CONSENTに移行したことを証明
        assert updated_plan.plan_status == 'PENDING_CONSENT'
        # URACフックの検証: 成功したため、リスクカウンターは増分されない
        mock_compliance_service.log_unresponsive_risk_increment.assert_not_called()
        logger.debug("   -> 宣誓ON: PENDING_CONSENT 移行成功。URACフック不活性化成功。")
        
    logger.info("✅ 不在時の強制ロジックとURACフック検証完了")