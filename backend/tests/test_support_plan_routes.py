import pytest
import logging
from datetime import date, datetime
from backend.app import db
from backend.app.models import User, Supporter, SupporterPII, StatusMaster, HolisticSupportPolicy, DocumentConsentLog

logger = logging.getLogger(__name__)

def test_support_plan_api_workflow(client, app):
    """
    支援計画APIのワークフローテスト。
    """
    logger.info("🚀 TEST START: 支援計画APIの検証")

    with app.app_context():
        # 1. 準備
        status = StatusMaster(name="利用中")
        db.session.add(status)
        db.session.flush()

        user = User(display_name="PlanUser", status_id=status.id)
        db.session.add(user)
        db.session.flush()

        sabikan = Supporter(
            last_name="Sabi", first_name="Kan", last_name_kana="サビ", first_name_kana="カン",
            employment_type="FULL_TIME", weekly_scheduled_minutes=2400, hire_date=date(2025, 1, 1)
        )
        sabikan.pii = SupporterPII(email="sabi@test.com")
        sabikan.pii.set_password("pass123")
        db.session.add(sabikan)
        db.session.flush()
        
        policy = HolisticSupportPolicy(
            user_id=user.id, effective_date=date.today(),
            user_intention_content="Hope", support_policy_content="Policy"
        )
        db.session.add(policy)
        db.session.commit()
        
        user_id = user.id
        policy_id = policy.id

    # 2. ログイン
    auth = client.post('/api/auth/login', json={"email": "sabi@test.com", "password": "pass123"})
    token = auth.json['access_token']
    headers = {'Authorization': f'Bearer {token}'}

    # 3. 原案作成 (API)
    logger.info("🔹 API: 原案作成")
    res_draft = client.post('/api/plans/', headers=headers, json={
        "user_id": user_id,
        "policy_id": policy_id
    })
    assert res_draft.status_code == 201
    plan_id = res_draft.json['id']
    assert res_draft.json['status'] == 'DRAFT'

    # 4. 会議記録 & 承認 (API)
    logger.info("🔹 API: 会議記録")
    res_conf = client.post(f'/api/plans/{plan_id}/conference', headers=headers, json={
        "conference_date": datetime.now().isoformat(),
        "content": "議事録内容",
        "user_participated": True
    })
    assert res_conf.status_code == 200
    assert res_conf.json['status'] == 'PENDING_CONSENT'

    # 5. 同意 & 成案化 (API)
    logger.info("🔹 API: 成案化")
    # 同意ログは先に作っておく必要がある（本来はOTL経由だが、ここではDB直接作成で代用）
    with app.app_context():
        consent = DocumentConsentLog(
            user_id=user_id, document_type='SUPPORT_PLAN', document_id=plan_id, consent_proof="SIG"
        )
        db.session.add(consent)
        db.session.commit()
        consent_id = consent.id

    res_final = client.post(f'/api/plans/{plan_id}/finalize', headers=headers, json={
        "consent_log_id": consent_id
    })
    assert res_final.status_code == 200
    assert res_final.json['status'] == 'ACTIVE'
    
    logger.info("✅ 支援計画APIの検証完了")