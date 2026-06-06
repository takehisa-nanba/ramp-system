import pytest
from datetime import datetime, timezone, date
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

def test_consent_api_flow(client, app):
    """
    テスト内容: 同意記録のAPI (POST /api/plans/<plan_id>/consent) 
    および有効化API (POST /api/plans/<plan_id>/activate) のフローを検証する。
    """
    from flask_jwt_extended import create_access_token
    from backend.tests.test_support_plan_service import setup_masters_and_user
    from backend.app.models import JobTitleMaster, SupporterJobAssignment
    
    with app.app_context():
        # テストデータのセットアップ
        user, sabikan, policy = setup_masters_and_user(db.session, display_name="TestUserAPI", staff_code="S999")
        
        # サビ管ロール（サービス管理責任者）の役職を割り当て
        sabi_title = db.session.query(JobTitleMaster).filter_by(title_name='サービス管理責任者').first()
        if not sabi_title:
            sabi_title = JobTitleMaster(title_name='サービス管理責任者', is_qualified_role=True)
            db.session.add(sabi_title)
            db.session.flush()
        
        # 必要なマスタ・設定データの取得または作成 (NOT NULL制約回避)
        from backend.app.models import Corporation, OfficeSetting, OfficeServiceConfiguration, MunicipalityMaster
        corp = db.session.query(Corporation).first()
        if not corp:
            corp = Corporation(corporation_name="Test Corp", corporation_type="KK")
            db.session.add(corp)
            db.session.flush()
        
        muni = db.session.query(MunicipalityMaster).first()
        if not muni:
            muni = MunicipalityMaster(municipality_code="999999", name="Test City")
            db.session.add(muni)
            db.session.flush()

        office = db.session.query(OfficeSetting).first()
        if not office:
            office = OfficeSetting(
                corporation_id=corp.id,
                office_name="Test Office",
                municipality_id=muni.id,
                full_time_weekly_minutes=2400
            )
            db.session.add(office)
            db.session.flush()

        service_config = db.session.query(OfficeServiceConfiguration).first()
        if not service_config:
            service_config = OfficeServiceConfiguration(
                office_id=office.id,
                service_type='TRAINING',
                office_service_number='1234567890',
                capacity=20
            )
            db.session.add(service_config)
            db.session.flush()

        assignment = SupporterJobAssignment(
            supporter_id=sabikan.id,
            job_title_id=sabi_title.id,
            office_service_configuration_id=service_config.id,
            start_date=date(2025, 1, 1),
            assigned_minutes=480
        )
        db.session.add(assignment)
        db.session.commit()
        
        # 計画の下書き(DRAFT)を作成し、PENDING_CONSENTにする
        service = SupportPlanService()
        draft_plan = service.create_plan_draft(user.id, sabikan.id, policy.id)
        db.session.commit()
        
        service.log_support_conference_and_approve(
            plan_id=draft_plan.id,
            sabikan_id=sabikan.id,
            conference_date=datetime.now(timezone.utc),
            content="APIテスト用会議",
            user_participated=True
        )
        db.session.commit()
        
        user_id = user.id
        plan_id = draft_plan.id
        
        # サビ管用のJWTトークンを作成
        token = create_access_token(identity=f"staff:{sabikan.id}", additional_claims={"role_type": "staff"})
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
    # 1. 同意証跡の登録
    # PENDING_CONSENT の状態でのみ登録できるはず
    consent_data = {
        "user_id": user_id,
        "consent_proof": "DIGITAL_SIGNATURE_BY_USER",
        "generated_document_url": "http://example.com/doc.pdf"
    }
    response = client.post(f"/api/plans/{plan_id}/consent", json=consent_data, headers=headers)
    assert response.status_code == 201
    res_data = response.get_json()
    consent_log_id = res_data["consent_log_id"]
    assert consent_log_id > 0
    
    # 2. 計画の有効化 (ACTIVE化)
    activate_data = {
        "consent_log_id": consent_log_id
    }
    response = client.post(f"/api/plans/{plan_id}/activate", json=activate_data, headers=headers)
    assert response.status_code == 200
    res_data = response.get_json()
    assert res_data["msg"] == "Plan activated successfully"
    assert res_data["status"] == "ACTIVE"
    
    # 3. DB状態の再確認
    with app.app_context():
        plan = db.session.get(SupportPlan, plan_id)
        assert plan.plan_status == 'ACTIVE'
