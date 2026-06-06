import pytest
from datetime import datetime, timezone
from backend.app.services.support_plan_service import SupportPlanService
from backend.app.models import SupportPlan, DocumentConsentLog
from backend.app import db

def test_support_plan_state_transitions(app):
    """
    テスト内容: SupportPlan の状態遷移 (DRAFT -> PENDING_CONSENT -> ACTIVE) 
    および異常系遷移のガードレールを検証する。
    """
    with app.app_context():
        service = SupportPlanService()
        
        from backend.tests.test_support_plan_service import setup_masters_and_user
        user, sabikan, policy = setup_masters_and_user(db.session, display_name="TestUser", staff_code="S009")
        
        if not user or not sabikan or not policy:
            pytest.skip("Required test data missing")

        # 2. DRAFT の作成
        draft_plan = service.create_plan_draft(user.id, sabikan.id, policy.id)
        db.session.commit()
        assert draft_plan.plan_status == 'DRAFT'
        
        plan_id = draft_plan.id
        
        # 異常系1: DRAFT から ACTIVE への直接遷移の試み
        # finalize_and_activate_plan に DRAFT 状態の計画を渡すと失敗するはず
        consent_log = DocumentConsentLog(
            document_id=plan_id,
            document_type='SUPPORT_PLAN',
            user_id=user.id,
            consent_proof='DIGITAL_SIGNATURE_XYZ'
        )
        db.session.add(consent_log)
        db.session.commit()
        
        with pytest.raises(Exception, match="Plan is not in 'PENDING_CONSENT' status"):
            service.finalize_and_activate_plan(plan_id, consent_log.id)
            
        # 3. DRAFT -> PENDING_CONSENT への遷移 (サビ管承認)
        service.log_support_conference_and_approve(
            plan_id=plan_id,
            sabikan_id=sabikan.id,
            conference_date=datetime.now(timezone.utc),
            content="会議議事録",
            user_participated=True
        )
        db.session.commit()
        
        plan = db.session.get(SupportPlan, plan_id)
        assert plan.plan_status == 'PENDING_CONSENT'
        
        # 4. PENDING_CONSENT -> ACTIVE への遷移 (同意と有効化)
        active_plan = service.finalize_and_activate_plan(plan_id, consent_log.id)
        db.session.commit()
        
        assert active_plan.plan_status == 'ACTIVE'
