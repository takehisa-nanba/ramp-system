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

        user_id = user.id
        sabikan_id = sabikan.id
        policy_id = policy.id

        # 2. DRAFT の作成
        draft_plan = service.create_plan_draft(user_id, sabikan_id, policy_id)
        db.session.commit()
        assert draft_plan.plan_status == 'DRAFT'
        
        plan_id = draft_plan.id
        
        # 異常系1: DRAFT から ACTIVE への直接遷移の試み
        consent_log = DocumentConsentLog(
            document_id=plan_id,
            document_type='SUPPORT_PLAN',
            user_id=user_id,
            consent_proof='DIGITAL_SIGNATURE_XYZ'
        )
        db.session.add(consent_log)
        db.session.commit()
        consent_log_id = consent_log.id
        
        with pytest.raises(Exception, match="Plan is not in 'PENDING_CONSENT' status"):
            service.finalize_and_activate_plan(plan_id, consent_log_id)
            
        # 3. DRAFT -> PENDING_CONSENT への遷移 (サビ管承認)
        service.log_support_conference_and_approve(
            plan_id=plan_id,
            sabikan_id=sabikan_id,
            conference_date=datetime.now(timezone.utc),
            content="会議議事録",
            user_participated=True
        )
        db.session.commit()
        
        plan = db.session.get(SupportPlan, plan_id)
        assert plan.plan_status == 'PENDING_CONSENT'
        
        # 4. PENDING_CONSENT -> ACTIVE への遷移 (同意と有効化)
        active_plan = service.finalize_and_activate_plan(plan_id, consent_log_id)
        db.session.commit()
        
        assert active_plan.plan_status == 'ACTIVE'

def test_consent_api_flow(client, app):
    """
    テスト内容: 同意記録のAPI (POST /api/plans/<plan_id>/consent) 
    および有効化API (POST /api/plans/<plan_id>/activate) のフローを検証する。
    """
    from flask_jwt_extended import create_access_token
    from backend.tests.test_support_plan_service import setup_masters_and_user
    from backend.app.models import JobTitleMaster, SupporterJobAssignment, ServiceTypeMaster
    
    with app.app_context():
        # テストデータのセットアップ
        user, sabikan, policy = setup_masters_and_user(db.session, display_name="TestUserAPI", staff_code="S999")
        user_id = user.id
        sabikan_id = sabikan.id
        policy_id = policy.id
        
        # サビ管ロール（サービス管理責任者）の役職を割り当て
        sabi_title = db.session.query(JobTitleMaster).filter_by(title_name='サービス管理責任者').first()
        if not sabi_title:
            sabi_title = JobTitleMaster(title_name='サービス管理責任者', is_qualified_role=True)
            db.session.add(sabi_title)
            db.session.flush()
        sabi_title_id = sabi_title.id
        
        # ServiceTypeMaster の取得・作成
        st_master = db.session.query(ServiceTypeMaster).filter_by(service_code='TRAINING').first()
        if not st_master:
            st_master = ServiceTypeMaster(service_code='TRAINING', name='自立訓練')
            db.session.add(st_master)
            db.session.flush()
        st_master_id = st_master.id
        
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
                service_type_master_id=st_master_id,
                jigyosho_bango='1234567890',
                capacity=20
            )
            db.session.add(service_config)
            db.session.flush()
        service_config_id = service_config.id

        assignment = SupporterJobAssignment(
            supporter_id=sabikan_id,
            job_title_id=sabi_title_id,
            office_service_configuration_id=service_config_id,
            start_date=date(2025, 1, 1),
            assigned_minutes=480
        )
        db.session.add(assignment)
        db.session.commit()
        
        # 計画の下書き(DRAFT)を作成し、PENDING_CONSENTにする
        service = SupportPlanService()
        draft_plan = service.create_plan_draft(user_id, sabikan_id, policy_id)
        db.session.commit()
        plan_id = draft_plan.id
        
        service.log_support_conference_and_approve(
            plan_id=plan_id,
            sabikan_id=sabikan_id,
            conference_date=datetime.now(timezone.utc),
            content="APIテスト用会議",
            user_participated=True
        )
        db.session.commit()
        
        # サビ管用のJWTトークンを作成
        token = create_access_token(identity=f"staff:{sabikan_id}", additional_claims={"role_type": "staff"})
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

def test_create_plan_with_fallback_policy(client, app):
    """
    テスト内容: HolisticSupportPolicy が未指定の場合の暫定方針自動生成、
    および plan_start_date, plan_end_date 指定時の上書き検証。
    """
    from flask_jwt_extended import create_access_token
    from backend.tests.test_support_plan_service import setup_masters_and_user
    
    with app.app_context():
        user, sabikan, policy = setup_masters_and_user(db.session, display_name="TestUserFallback", staff_code="S888")
        user_id = user.id
        sabikan_id = sabikan.id
        
        # フォールバックを検証するため、一度既存の総合支援方針を削除する
        db.session.delete(policy)
        db.session.commit()
        
        token = create_access_token(identity=f"staff:{sabikan_id}", additional_claims={"role_type": "staff"})
        headers = {
            "Authorization": f"Bearer {token}"
        }

    # 1. パラメータ指定なしでの新規作成（フォールバックが機能するはず）
    response = client.post("/api/plans/", json={"user_id": user_id}, headers=headers)
    assert response.status_code == 201
    res_data = response.get_json()
    plan_id = res_data["plan_id"]
    
    with app.app_context():
        plan = db.session.get(SupportPlan, plan_id)
        assert plan.holistic_policy is not None
        assert "【暫定支援方針】" in plan.holistic_policy.support_policy_content
        assert "【暫定本人の意向】" in plan.holistic_policy.user_intention_content

    # 2. 日付およびカスタム方針パラメータを指定しての新規作成
    plan_data = {
        "user_id": user_id,
        "plan_start_date": "2026-07-01",
        "plan_end_date": "2026-09-30",
        "user_intention_content": "就労を目指したい",
        "support_policy_content": "就労移行支援を進める"
    }
    response = client.post("/api/plans/", json=plan_data, headers=headers)
    assert response.status_code == 201
    res_data = response.get_json()
    new_plan_id = res_data["plan_id"]
    
    with app.app_context():
        new_plan = db.session.get(SupportPlan, new_plan_id)
        assert new_plan.plan_start_date.isoformat() == "2026-07-01"
        assert new_plan.plan_end_date.isoformat() == "2026-09-30"
        assert new_plan.holistic_policy.user_intention_content == "就労を目指したい"
        assert new_plan.holistic_policy.support_policy_content == "就労移行支援を進める"

def test_put_goals_only_in_draft_guard(client, app):
    """
    テスト内容: PUT /api/plans/<plan_id>/goals による目標の一括保存、
    および DRAFT 状態以外での編集拒否（ガードレール）の検証。
    """
    from flask_jwt_extended import create_access_token
    from backend.tests.test_support_plan_service import setup_masters_and_user
    
    with app.app_context():
        user, sabikan, policy = setup_masters_and_user(db.session, display_name="TestUserGoals", staff_code="S777")
        user_id = user.id
        sabikan_id = sabikan.id
        
        token = create_access_token(identity=f"staff:{sabikan_id}", additional_claims={"role_type": "staff"})
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        # DRAFTの計画作成
        response = client.post("/api/plans/", json={"user_id": user_id}, headers=headers)
        res_data = response.get_json()
        plan_id = res_data["plan_id"]

    # 1. DRAFT 状態での目標保存（成功するはず）
    goals_data = {
        "long_term_goals": [
            {
                "description": "長期目標A",
                "short_term_goals": [
                    {
                        "description": "短期目標A-1",
                        "individual_goals": [
                          {
                            "concrete_goal": "個別目標A-1-a",
                            "user_commitment": "本人の取り組み内容",
                            "support_actions": "支援内容",
                            "service_type": "TRAINING",
                            "is_facility_in_deemed": False,
                            "is_work_preparation_positioning": False
                          }
                        ]
                    }
                ]
            }
        ]
    }
    response = client.put(f"/api/plans/{plan_id}/goals", json=goals_data, headers=headers)
    assert response.status_code == 200
    
    with app.app_context():
        plan = db.session.get(SupportPlan, plan_id)
        assert len(plan.long_term_goals) == 1
        assert plan.long_term_goals[0].description == "長期目標A"
        assert len(plan.long_term_goals[0].short_term_goals) == 1
        assert plan.long_term_goals[0].short_term_goals[0].description == "短期目標A-1"
        assert len(plan.long_term_goals[0].short_term_goals[0].individual_goals) == 1
        assert plan.long_term_goals[0].short_term_goals[0].individual_goals[0].concrete_goal == "個別目標A-1-a"

    # 2. 計画を PENDING_CONSENT に進める
    with app.app_context():
        service = SupportPlanService()
        service.log_support_conference_and_approve(
            plan_id=plan_id,
            sabikan_id=sabikan_id,
            conference_date=datetime.now(timezone.utc),
            content="テスト用会議",
            user_participated=True
        )
        db.session.commit()
        plan = db.session.get(SupportPlan, plan_id)
        assert plan.plan_status == 'PENDING_CONSENT'

    # 3. PENDING_CONSENT 状態での目標保存（400エラーになるはず）
    response = client.put(f"/api/plans/{plan_id}/goals", json=goals_data, headers=headers)
    assert response.status_code == 400
    assert "Only DRAFT plans can be edited" in response.get_json()["msg"]

def test_create_next_draft_cloning(client, app):
    """
    テスト内容: 有効な ACTIVE 計画から、次期 DRAFT 計画を複製する API の検証。
    """
    from flask_jwt_extended import create_access_token
    from backend.tests.test_support_plan_service import setup_masters_and_user
    
    with app.app_context():
        user, sabikan, policy = setup_masters_and_user(db.session, display_name="TestUserClone", staff_code="S666")
        user_id = user.id
        sabikan_id = sabikan.id
        policy_id = policy.id
        
        token = create_access_token(identity=f"staff:{sabikan_id}", additional_claims={"role_type": "staff"})
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        # 1. DRAFT 計画の作成
        service = SupportPlanService()
        draft_plan = service.create_plan_draft(user_id, sabikan_id, policy_id)
        db.session.commit()
        plan_id = draft_plan.id
        
    goals_data = {
        "long_term_goals": [
            {
                "description": "長期目標コピー元",
                "short_term_goals": [
                    {
                        "description": "短期目標コピー元",
                        "individual_goals": [
                          {
                            "concrete_goal": "個別支援コピー元",
                            "user_commitment": "取り組み",
                            "support_actions": "支援",
                            "service_type": "TRAINING",
                            "is_facility_in_deemed": True,
                            "is_work_preparation_positioning": False
                          }
                        ]
                    }
                ]
            }
        ]
    }
    client.put(f"/api/plans/{plan_id}/goals", json=goals_data, headers=headers)
    
    with app.app_context():
        # 2. ACTIVE に進める
        service = SupportPlanService()
        service.log_support_conference_and_approve(
            plan_id=plan_id,
            sabikan_id=sabikan_id,
            conference_date=datetime.now(timezone.utc),
            content="クローン元計画の会議",
            user_participated=True
        )
        db.session.commit()
        
        consent_log = DocumentConsentLog(
            document_id=plan_id,
            document_type='SUPPORT_PLAN',
            user_id=user_id,
            consent_proof='DIGITAL_SIGNATURE'
        )
        db.session.add(consent_log)
        db.session.commit()
        
        active_plan = service.finalize_and_activate_plan(plan_id, consent_log.id)
        db.session.commit()
        assert active_plan.plan_status == 'ACTIVE'
        active_plan_id = active_plan.id

    # 3. 次期原案の作成 API の呼び出し
    response = client.post(f"/api/plans/{active_plan_id}/create-next-draft", headers=headers)
    assert response.status_code == 201
    res_data = response.get_json()
    new_draft_id = res_data["plan_id"]
    
    with app.app_context():
        new_draft = db.session.get(SupportPlan, new_draft_id)
        assert new_draft.plan_status == 'DRAFT'
        assert new_draft.based_on_plan_id == active_plan_id
        
        # 目標ツリーが複製されていることを検証
        assert len(new_draft.long_term_goals) == 1
        assert new_draft.long_term_goals[0].description == "長期目標コピー元"
        assert len(new_draft.long_term_goals[0].short_term_goals) == 1
        assert new_draft.long_term_goals[0].short_term_goals[0].description == "短期目標コピー元"
        assert len(new_draft.long_term_goals[0].short_term_goals[0].individual_goals) == 1
        assert new_draft.long_term_goals[0].short_term_goals[0].individual_goals[0].concrete_goal == "個別支援コピー元"
        assert new_draft.long_term_goals[0].short_term_goals[0].individual_goals[0].is_facility_in_deemed is True


def test_update_plan_details_and_retrieval(client, app):
    """
    テスト内容: GET /api/plans/<plan_id> による計画詳細取得、
    および PUT /api/plans/<plan_id> による期間・方針更新の検証。
    """
    from flask_jwt_extended import create_access_token
    from backend.tests.test_support_plan_service import setup_masters_and_user
    
    with app.app_context():
        user, sabikan, policy = setup_masters_and_user(db.session, display_name="TestUserUpdate", staff_code="S555")
        user_id = user.id
        sabikan_id = sabikan.id
        policy_id = policy.id
        
        token = create_access_token(identity=f"staff:{sabikan_id}", additional_claims={"role_type": "staff"})
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        service = SupportPlanService()
        draft_plan = service.create_plan_draft(user_id, sabikan_id, policy_id)
        db.session.commit()
        plan_id = draft_plan.id
 
    # 1. 計画の基本情報（日付・方針）更新
    update_data = {
        "plan_start_date": "2026-08-01",
        "plan_end_date": "2026-10-31",
        "user_intention_content": "新意向",
        "support_policy_content": "新方針"
    }
    response = client.put(f"/api/plans/{plan_id}", json=update_data, headers=headers)
    assert response.status_code == 200
    
    # 2. 計画詳細の取得と検証
    response = client.get(f"/api/plans/{plan_id}", headers=headers)
    assert response.status_code == 200
    details = response.get_json()
    assert details["start_date"] == "2026-08-01"
    assert details["end_date"] == "2026-10-31"
    assert details["holistic_policy"]["user_intention_content"] == "新意向"
    assert details["holistic_policy"]["support_policy_content"] == "新方針"


def test_challenges_validation_and_cloning(client, app):
    """
    テスト内容: 長期目標に紐づく「課題・相談内容（challenges）」の保存、
    承認（成案化）時における空文字バリデーションガードレールの検証、
    および次期計画クローン（複製）時の引き継ぎ検証。
    """
    from flask_jwt_extended import create_access_token
    from backend.tests.test_support_plan_service import setup_masters_and_user
    from backend.app.models import SupportPlan, CaseConferenceLog
    from datetime import datetime
    
    with app.app_context():
        user, sabikan, policy = setup_masters_and_user(db.session, display_name="TestChallengesUser", staff_code="S3857")
        user_id = user.id
        sabikan_id = sabikan.id
        policy_id = policy.id
        
        # サビ管職種のアサインメントを登録 (依存マスタ・設定の解決)
        from backend.app.models import SupporterJobAssignment, JobTitleMaster, ServiceTypeMaster
        from backend.app.models import Corporation, OfficeSetting, OfficeServiceConfiguration, MunicipalityMaster
        from datetime import date
        
        sabi_title = db.session.query(JobTitleMaster).filter_by(title_name='サービス管理責任者').first()
        if not sabi_title:
            sabi_title = JobTitleMaster(title_name='サービス管理責任者', is_qualified_role=True)
            db.session.add(sabi_title)
            db.session.flush()
        sabi_title_id = sabi_title.id
        
        st_master = db.session.query(ServiceTypeMaster).filter_by(service_code='TRAINING').first()
        if not st_master:
            st_master = ServiceTypeMaster(service_code='TRAINING', name='自立訓練')
            db.session.add(st_master)
            db.session.flush()
        st_master_id = st_master.id
        
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
                service_type_master_id=st_master_id,
                jigyosho_bango='1234567890',
                capacity=20
            )
            db.session.add(service_config)
            db.session.flush()
        service_config_id = service_config.id

        assignment = SupporterJobAssignment(
            supporter_id=sabikan_id,
            job_title_id=sabi_title_id,
            office_service_configuration_id=service_config_id,
            start_date=date(2025, 1, 1),
            assigned_minutes=480
        )
        db.session.add(assignment)
        db.session.commit()
        
        token = create_access_token(identity=f"staff:{sabikan_id}", additional_claims={"role_type": "staff"})
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        # DRAFT計画を作成
        service = SupportPlanService()
        draft_plan = service.create_plan_draft(user_id, sabikan_id, policy_id)
        db.session.commit()
        plan_id = draft_plan.id

    # 1. 課題（challenges）が空文字の目標ツリーを登録
    goals_with_empty_challenges = {
        "long_term_goals": [{
            "description": "長期目標の検証",
            "challenges": "", # 空欄
            "short_term_goals": [{
                "description": "短期目標の検証",
                "individual_goals": [{
                    "concrete_goal": "具体的目標の検証",
                    "user_commitment": "本人の取組の検証",
                    "support_actions": "支援内容の検証",
                    "service_type": "TRAINING"
                }]
            }]
        }]
    }
    response = client.put(f"/api/plans/{plan_id}/goals", json=goals_with_empty_challenges, headers=headers)
    assert response.status_code == 200

    # 本人同席会議を登録
    conf_data = {
        "user_id": user_id,
        "conference_type": "PERSON_CENTERED_MEETING",
        "concern_summary": "検証用議題",
        "agreed_action": "検証用決定事項",
        "participant_ids": [sabikan_id],
        "conference_datetime": datetime.now().isoformat(),
        "support_plan_id": plan_id,
        "user_participated": True
    }
    response = client.post("/api/case-conferences", json=conf_data, headers=headers)
    assert response.status_code == 201

    # 2. 承認を試みる（課題が空なのでバリデーションでブロックされるはず）
    response = client.post(f"/api/plans/{plan_id}/approve", headers=headers)
    assert response.status_code == 400
    assert "課題が未入力の目標があります" in response.get_json()["msg"]

    # 3. 課題（challenges）を正しく入力して目標ツリーを更新
    goals_with_challenges = {
        "long_term_goals": [{
            "description": "長期目標の検証",
            "challenges": "検証用の課題・相談内容", # 入力あり
            "short_term_goals": [{
                "description": "短期目標の検証",
                "individual_goals": [{
                    "concrete_goal": "具体的目標の検証",
                    "user_commitment": "本人の取組の検証",
                    "support_actions": "支援内容の検証",
                    "service_type": "TRAINING"
                }]
            }]
        }]
    }
    response = client.put(f"/api/plans/{plan_id}/goals", json=goals_with_challenges, headers=headers)
    assert response.status_code == 200

    # 4. 再度承認（今度は成功するはず）
    response = client.post(f"/api/plans/{plan_id}/approve", headers=headers)
    assert response.status_code == 200

    with app.app_context():
        plan = db.session.get(SupportPlan, plan_id)
        assert plan.plan_status == "PENDING_CONSENT"
        assert plan.long_term_goals[0].challenges == "検証用の課題・相談内容"

    # 同意および有効化して ACTIVE にする
    consent_data = {
        "consent_proof": "署名画像ダミー",
        "user_id": user_id
    }
    response = client.post(f"/api/plans/{plan_id}/consent", json=consent_data, headers=headers)
    assert response.status_code == 201
    consent_log_id = response.get_json()["consent_log_id"]

    activate_data = {
        "consent_log_id": consent_log_id
    }
    response = client.post(f"/api/plans/{plan_id}/activate", json=activate_data, headers=headers)
    assert response.status_code == 200

    # 5. 次期計画のクローンを作成し、課題が複製されているか確認
    response = client.post(f"/api/plans/{plan_id}/create-next-draft", headers=headers)
    assert response.status_code == 201
    next_plan_id = response.get_json()["plan_id"]

    with app.app_context():
        next_plan = db.session.get(SupportPlan, next_plan_id)
        assert next_plan.plan_status == "DRAFT"
        assert len(next_plan.long_term_goals) == 1
        assert next_plan.long_term_goals[0].challenges == "検証用の課題・相談内容"
        assert next_plan.long_term_goals[0].description == "長期目標の検証"


def test_monitoring_report_flow(client, app):
    """
    テスト内容: モニタリングレポートの新規登録、DB永続化、および取得APIの検証。
    """
    from flask_jwt_extended import create_access_token
    from backend.tests.test_support_plan_service import setup_masters_and_user
    from backend.app.models import SupportPlan, DocumentConsentLog, MonitoringReport
    from datetime import date, datetime
    
    with app.app_context():
        user, sabikan, policy = setup_masters_and_user(db.session, display_name="TestMonUser", staff_code="S7777")
        user_id = user.id
        sabikan_id = sabikan.id
        policy_id = policy.id
        
        token = create_access_token(identity=f"staff:{sabikan_id}", additional_claims={"role_type": "staff"})
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        # 1. 計画をACTIVEまで進める
        service = SupportPlanService()
        draft_plan = service.create_plan_draft(user_id, sabikan_id, policy_id)
        db.session.commit()
        plan_id = draft_plan.id
        
        # 原案承認
        service.log_support_conference_and_approve(
            plan_id=plan_id,
            sabikan_id=sabikan_id,
            conference_date=datetime.now().date(),
            content="モニタリングテスト用会議",
            user_participated=True
        )
        db.session.commit()
        
        # 同意
        consent_log = DocumentConsentLog(
            document_id=plan_id,
            document_type='SUPPORT_PLAN',
            user_id=user_id,
            consent_proof='DIGITAL_SIGNATURE'
        )
        db.session.add(consent_log)
        db.session.commit()
        
        # 有効化
        active_plan = service.finalize_and_activate_plan(plan_id, consent_log.id)
        db.session.commit()
        assert active_plan.plan_status == 'ACTIVE'

    # 2. モニタリング結果を登録
    mon_data = {
        "support_plan_id": plan_id,
        "report_date": "2026-06-07",
        "monitoring_summary": "テスト評価概要",
        "target_goal_progress_notes": "目標進捗所見",
        "contextual_analysis": "背景分析文脈"
    }
    response = client.post("/api/monitoring-reports", json=mon_data, headers=headers)
    assert response.status_code == 201
    
    # 3. DBに永続化されているか検証
    with app.app_context():
        reports = MonitoringReport.query.filter_by(support_plan_id=plan_id).all()
        assert len(reports) == 1
        assert reports[0].monitoring_summary == "テスト評価概要"
        assert reports[0].target_goal_progress_notes == "目標進捗所見"
        assert reports[0].contextual_analysis == "背景分析文脈"

    # 4. 取得APIで履歴が含まれているか検証
    response = client.get(f"/api/users/{user_id}/monitoring-reports", headers=headers)
    assert response.status_code == 200
    res_data = response.get_json()
    assert len(res_data["history"]) == 1
    assert res_data["history"][0]["monitoring_summary"] == "テスト評価概要"
    assert res_data["history"][0]["target_goal_progress_notes"] == "目標進捗所見"

