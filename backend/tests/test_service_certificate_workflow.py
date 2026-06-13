# backend/tests/test_service_certificate_workflow.py

import pytest
from datetime import date, datetime
from flask_jwt_extended import create_access_token
from backend.app import db
from backend.app.models import User, Supporter, StatusMaster, RoleMaster, PermissionMaster, OfficeServiceConfiguration
from backend.app.models.core.service_certificate import ServiceCertificate, GrantedService
from backend.app.models.masters.master_definitions import ServiceTypeMaster, MunicipalityMaster

def setup_user_and_supporters(app):
    with app.app_context():
        # Setup status
        status = db.session.query(StatusMaster).first()
        if not status:
            status = StatusMaster(name="利用中")
            db.session.add(status)
            db.session.flush()

        # Setup municipality
        muni = db.session.query(MunicipalityMaster).first()
        if not muni:
            muni = MunicipalityMaster(name="テスト自治体", municipality_code="123456")
            db.session.add(muni)
            db.session.flush()

        # Setup service type
        st1 = db.session.query(ServiceTypeMaster).filter_by(name="就労継続支援B型").first()
        if not st1:
            st1 = ServiceTypeMaster(name="就労継続支援B型", service_code="STB")
            db.session.add(st1)
            db.session.flush()

        st2 = db.session.query(ServiceTypeMaster).filter_by(name="生活介護").first()
        if not st2:
            st2 = ServiceTypeMaster(name="生活介護", service_code="STS")
            db.session.add(st2)
            db.session.flush()

        # Setup office configuration
        osc = db.session.query(OfficeServiceConfiguration).first()
        if not osc:
            from backend.app.models import Corporation, OfficeSetting
            corp = db.session.query(Corporation).first()
            if not corp:
                corp = Corporation(corporation_name="テスト法人", corporation_type="株式会社")
                db.session.add(corp)
                db.session.flush()
            office = db.session.query(OfficeSetting).first()
            if not office:
                office = OfficeSetting(corporation_id=corp.id, office_name="テスト事業所", municipality_id=muni.id)
                db.session.add(office)
                db.session.flush()
            osc = OfficeServiceConfiguration(office_id=office.id, service_type_master_id=st1.id, jigyosho_bango="1234567890", capacity=20)
            db.session.add(osc)
            db.session.flush()

        # Create user
        user = db.session.query(User).filter_by(user_code="WF_USR_1").first()
        if not user:
            user = User(display_name="Workflow Test User", status_id=status.id, user_code="WF_USR_1")
            db.session.add(user)
            db.session.flush()

        # Setup permissions & roles
        edit_pii_perm = PermissionMaster.query.filter_by(name='EDIT_PII').first()
        if not edit_pii_perm:
            edit_pii_perm = PermissionMaster(name='EDIT_PII')
            db.session.add(edit_pii_perm)
            db.session.flush()

        view_pii_perm = PermissionMaster.query.filter_by(name='VIEW_PII').first()
        if not view_pii_perm:
            view_pii_perm = PermissionMaster(name='VIEW_PII')
            db.session.add(view_pii_perm)
            db.session.flush()

        admin_role = RoleMaster.query.filter_by(name='Admin Role').first()
        if not admin_role:
            admin_role = RoleMaster(name='Admin Role', role_scope='SYSTEM', is_admin=True)
            db.session.add(admin_role)
            db.session.flush()

        if edit_pii_perm not in admin_role.permissions:
            admin_role.permissions.append(edit_pii_perm)
        if view_pii_perm not in admin_role.permissions:
            admin_role.permissions.append(view_pii_perm)
        db.session.flush()

        # Create creators and reviewers
        supporter1 = Supporter.query.filter_by(staff_code="S_CREATOR").first()
        if not supporter1:
            supporter1 = Supporter(
                staff_code="S_CREATOR", 
                last_name="Creator", first_name="Staff", 
                last_name_kana="クリエイター", first_name_kana="スタッフ", 
                employment_type="FULL_TIME", weekly_scheduled_minutes=2400,
                hire_date=date(2025, 1, 1)
            )
            supporter1.roles.append(admin_role)
            db.session.add(supporter1)

        supporter2 = Supporter.query.filter_by(staff_code="S_REVIEWER").first()
        if not supporter2:
            supporter2 = Supporter(
                staff_code="S_REVIEWER", 
                last_name="Reviewer", first_name="Staff", 
                last_name_kana="レビュアー", first_name_kana="スタッフ", 
                employment_type="FULL_TIME", weekly_scheduled_minutes=2400,
                hire_date=date(2025, 1, 1)
            )
            supporter2.roles.append(admin_role)
            db.session.add(supporter2)

        db.session.commit()
        return user.id, supporter1.id, supporter2.id, st1.id, st2.id, muni.id, osc.id

def test_service_certificate_workflow(app):
    user_id, creator_id, reviewer_id, st1_id, st2_id, muni_id, osc_id = setup_user_and_supporters(app)

    with app.app_context():
        # Get JWT tokens
        token_creator = create_access_token(identity=f"staff:{creator_id}", additional_claims={"role_scopes": ["JOB", "EDIT_PII", "VIEW_PII"]})
        token_reviewer = create_access_token(identity=f"staff:{reviewer_id}", additional_claims={"role_scopes": ["JOB", "EDIT_PII", "VIEW_PII"]})

        client = app.test_client()

        # 1. Create a DRAFT certificate
        payload = {
            "certificate_issue_date": "2025-01-01",
            "municipality_master_id": muni_id,
            "office_service_configuration_id": osc_id,
            "certificate_type": "受給者証",
            "disability_support_classification": "区分3",
            "recipient_number": "1234567890",
            "certificate_notes": "テスト用ノート",
            "granted_services": [
                {
                    "service_type_master_id": st1_id,
                    "granted_start_date": "2025-01-01",
                    "granted_end_date": "2025-12-31",
                    "granted_amount_description": "20日/月",
                    "max_service_days": 20,
                    "max_service_days_type": "FIXED",
                    "granted_amount_start_date": "2025-01-01",
                    "granted_amount_end_date": "2025-12-31",
                    "contract_detail": {
                        "office_service_configuration_id": osc_id,
                        "contract_granted_days": 20,
                        "contract_date": "2025-01-01",
                        "contract_end_date": "2025-12-31",
                        "contract_end_used_days": 0
                    }
                }
            ],
            "copayment_limits": [
                {
                    "limit_start_date": "2025-01-01",
                    "limit_end_date": "2025-12-31",
                    "limit_amount": 9300.0,
                    "is_management_required": True
                }
            ],
            "meal_addon_statuses": [],
            "copayment_managements": []
        }

        # Create as DRAFT
        res = client.post(f'/api/users/{user_id}/certificates', json=payload, headers={'Authorization': f'Bearer {token_creator}'})
        assert res.status_code == 201
        cert_id = res.get_json()['id']

        # Verify initial status is DRAFT and created_by is populated
        cert = db.session.get(ServiceCertificate, cert_id)
        assert cert.status == 'DRAFT'
        assert cert.created_by_supporter_id == creator_id
        assert cert.submitted_by_supporter_id is None

        # 2. Update the draft
        payload['recipient_number'] = "0987654321"
        res = client.put(f'/api/users/{user_id}/certificates/{cert_id}', json=payload, headers={'Authorization': f'Bearer {token_creator}'})
        assert res.status_code == 200
        db.session.refresh(cert)
        assert cert.recipient_number == "0987654321"

        # 3. Submit for review
        res = client.post(f'/api/users/{user_id}/certificates/{cert_id}/submit', headers={'Authorization': f'Bearer {token_creator}'})
        assert res.status_code == 200
        db.session.refresh(cert)
        assert cert.status == 'PENDING_REVIEW'
        assert cert.submitted_by_supporter_id == creator_id

        # 4. Try to edit while PENDING_REVIEW -> should fail (editability rule)
        res = client.put(f'/api/users/{user_id}/certificates/{cert_id}', json=payload, headers={'Authorization': f'Bearer {token_creator}'})
        assert res.status_code == 400
        assert "下書きまたは却下状態の受給者証のみ編集可能です" in res.get_json()['msg']

        # 5. Try to approve/reject own submission -> should fail (separation of duties)
        res = client.post(f'/api/users/{user_id}/certificates/{cert_id}/review', json={"action": "approve"}, headers={'Authorization': f'Bearer {token_creator}'})
        assert res.status_code == 400
        assert "確認・承認は行えません" in res.get_json()['msg']

        # 6. Reject without comment -> should fail
        res = client.post(f'/api/users/{user_id}/certificates/{cert_id}/review', json={"action": "reject", "review_reason": ""}, headers={'Authorization': f'Bearer {token_reviewer}'})
        assert res.status_code == 400
        assert "却下理由を入力してください" in res.get_json()['msg']

        # 7. Reject with comment -> succeeds
        res = client.post(f'/api/users/{user_id}/certificates/{cert_id}/review', json={"action": "reject", "review_reason": "情報が不足しています。"}, headers={'Authorization': f'Bearer {token_reviewer}'})
        assert res.status_code == 200
        db.session.refresh(cert)
        assert cert.status == 'REJECTED'
        assert cert.reviewed_by_supporter_id == reviewer_id
        assert cert.review_reason == "情報が不足しています。"

        # 8. Edit the rejected certificate -> succeeds (returns to DRAFT)
        res = client.put(f'/api/users/{user_id}/certificates/{cert_id}', json=payload, headers={'Authorization': f'Bearer {token_creator}'})
        assert res.status_code == 200
        db.session.refresh(cert)
        assert cert.status == 'DRAFT'

        # 9. Submit again
        res = client.post(f'/api/users/{user_id}/certificates/{cert_id}/submit', headers={'Authorization': f'Bearer {token_creator}'})
        assert res.status_code == 200
        db.session.refresh(cert)
        assert cert.status == 'PENDING_REVIEW'

        # 10. Approve it -> succeeds
        res = client.post(f'/api/users/{user_id}/certificates/{cert_id}/review', json={"action": "approve", "review_reason": "確認しました。"}, headers={'Authorization': f'Bearer {token_reviewer}'})
        assert res.status_code == 200
        db.session.refresh(cert)
        assert cert.status == 'ACTIVE'

        # 11. Try to edit while ACTIVE -> should fail
        res = client.put(f'/api/users/{user_id}/certificates/{cert_id}', json=payload, headers={'Authorization': f'Bearer {token_creator}'})
        assert res.status_code == 400

        # 12. Test overlap automatic archiving
        # Create a second certificate overlapping with st1 and the same period
        payload2 = dict(payload)
        payload2['recipient_number'] = "1111222233"
        payload2['granted_services'] = [
            {
                "service_type_master_id": st1_id, # Same service type
                "granted_start_date": "2025-06-01", # Overlapping period
                "granted_end_date": "2025-12-31",
                "granted_amount_description": "20日/月",
                "max_service_days": 20,
                "max_service_days_type": "FIXED",
                "granted_amount_start_date": "2025-06-01",
                "granted_amount_end_date": "2025-12-31",
                "contract_detail": {
                    "office_service_configuration_id": osc_id,
                    "contract_granted_days": 20,
                    "contract_date": "2025-06-01",
                    "contract_end_date": "2025-12-31",
                    "contract_end_used_days": 0
                }
            }
        ]

        res = client.post(f'/api/users/{user_id}/certificates', json=payload2, headers={'Authorization': f'Bearer {token_creator}'})
        assert res.status_code == 201
        cert_id2 = res.get_json()['id']

        # Submit second certificate
        res = client.post(f'/api/users/{user_id}/certificates/{cert_id2}/submit', headers={'Authorization': f'Bearer {token_creator}'})
        assert res.status_code == 200

        # Approve second certificate
        res = client.post(f'/api/users/{user_id}/certificates/{cert_id2}/review', json={"action": "approve"}, headers={'Authorization': f'Bearer {token_reviewer}'})
        assert res.status_code == 200

        # Verify that the first certificate is now ARCHIVED
        db.session.refresh(cert)
        assert cert.status == 'ARCHIVED'

        # Verify that the second certificate is ACTIVE
        cert2 = db.session.get(ServiceCertificate, cert_id2)
        assert cert2.status == 'ACTIVE'

        # 13. Create a third certificate with non-overlapping service type (st2_id)
        # Should NOT archive the second certificate (st1_id)
        payload3 = dict(payload)
        payload3['recipient_number'] = "9999888877"
        payload3['granted_services'] = [
            {
                "service_type_master_id": st2_id, # Different service type
                "granted_start_date": "2025-01-01",
                "granted_end_date": "2025-12-31",
                "granted_amount_description": "20日/月",
                "max_service_days": 20,
                "max_service_days_type": "FIXED",
                "granted_amount_start_date": "2025-01-01",
                "granted_amount_end_date": "2025-12-31",
                "contract_detail": {
                    "office_service_configuration_id": osc_id,
                    "contract_granted_days": 20,
                    "contract_date": "2025-01-01",
                    "contract_end_date": "2025-12-31",
                    "contract_end_used_days": 0
                }
            }
        ]

        res = client.post(f'/api/users/{user_id}/certificates', json=payload3, headers={'Authorization': f'Bearer {token_creator}'})
        assert res.status_code == 201
        cert_id3 = res.get_json()['id']

        # Submit third
        res = client.post(f'/api/users/{user_id}/certificates/{cert_id3}/submit', headers={'Authorization': f'Bearer {token_creator}'})
        assert res.status_code == 200

        # Approve third
        res = client.post(f'/api/users/{user_id}/certificates/{cert_id3}/review', json={"action": "approve"}, headers={'Authorization': f'Bearer {token_reviewer}'})
        assert res.status_code == 200

        # Verify that the second certificate (st1_id) remains ACTIVE (no overlap on service type)
        db.session.refresh(cert2)
        assert cert2.status == 'ACTIVE'
        
        # Verify that the third certificate (st2_id) is ACTIVE
        cert3 = db.session.get(ServiceCertificate, cert_id3)
        assert cert3.status == 'ACTIVE'


def test_service_certificate_void(app):
    user_id, creator_id, reviewer_id, st1_id, st2_id, muni_id, osc_id = setup_user_and_supporters(app)

    with app.app_context():
        # Get models and db session
        from backend.app.models import Corporation, OfficeSetting
        client = app.test_client()

        # Let's create supporter roles for testing
        # 1. System Admin
        sys_admin_role = RoleMaster.query.filter_by(name='SYSTEM_ADMIN').first()
        if not sys_admin_role:
            sys_admin_role = RoleMaster(name='SYSTEM_ADMIN', role_scope='SYSTEM', is_admin=True)
            db.session.add(sys_admin_role)
        
        # 2. Corporate Admin (Same Corporation)
        corp_admin_role = RoleMaster.query.filter_by(name='CORP_ADMIN').first()
        if not corp_admin_role:
            corp_admin_role = RoleMaster(name='CORP_ADMIN', role_scope='CORPORATE', is_admin=True)
            db.session.add(corp_admin_role)

        # 3. Regular (no admin)
        regular_role = RoleMaster.query.filter_by(name='REGULAR').first()
        if not regular_role:
            regular_role = RoleMaster(name='REGULAR', role_scope='JOB', is_admin=False)
            db.session.add(regular_role)
        
        db.session.flush()

        edit_pii_perm = PermissionMaster.query.filter_by(name='EDIT_PII').first()
        if edit_pii_perm not in sys_admin_role.permissions:
            sys_admin_role.permissions.append(edit_pii_perm)
        if edit_pii_perm not in corp_admin_role.permissions:
            corp_admin_role.permissions.append(edit_pii_perm)
        if edit_pii_perm not in regular_role.permissions:
            regular_role.permissions.append(edit_pii_perm)
        
        db.session.flush()

        # Get existing corporation and office from setup
        osc = db.session.get(OfficeServiceConfiguration, osc_id)
        same_corp_id = osc.office.corporation_id

        # Create another corporation and office
        other_corp = Corporation(corporation_name="別法人", corporation_type="株式会社")
        db.session.add(other_corp)
        db.session.flush()
        other_office = OfficeSetting(corporation_id=other_corp.id, office_name="別事業所", municipality_id=muni_id)
        db.session.add(other_office)
        db.session.flush()

        # Create supporters
        # Supporter 1: System Admin
        supporter_sys_admin = Supporter(
            staff_code="S_SYS_ADMIN", 
            last_name="Sys", first_name="Admin", 
            last_name_kana="シス", first_name_kana="アドミン", 
            employment_type="FULL_TIME", weekly_scheduled_minutes=2400,
            hire_date=date(2025, 1, 1),
            office_id=osc.office_id
        )
        supporter_sys_admin.roles.append(sys_admin_role)
        db.session.add(supporter_sys_admin)

        # Supporter 2: Corporate Admin (Same Corp)
        supporter_corp_admin_same = Supporter(
            staff_code="S_CORP_ADMIN_SAME", 
            last_name="Corp", first_name="AdminSame", 
            last_name_kana="コープ", first_name_kana="サメ", 
            employment_type="FULL_TIME", weekly_scheduled_minutes=2400,
            hire_date=date(2025, 1, 1),
            office_id=osc.office_id
        )
        supporter_corp_admin_same.roles.append(corp_admin_role)
        db.session.add(supporter_corp_admin_same)

        # Supporter 3: Corporate Admin (Different Corp)
        supporter_corp_admin_diff = Supporter(
            staff_code="S_CORP_ADMIN_DIFF", 
            last_name="Corp", first_name="AdminDiff", 
            last_name_kana="コープ", first_name_kana="ディフ", 
            employment_type="FULL_TIME", weekly_scheduled_minutes=2400,
            hire_date=date(2025, 1, 1),
            office_id=other_office.id
        )
        supporter_corp_admin_diff.roles.append(corp_admin_role)
        db.session.add(supporter_corp_admin_diff)

        # Supporter 4: Regular Supporter
        supporter_regular = Supporter(
            staff_code="S_REGULAR", 
            last_name="Reg", first_name="Staff", 
            last_name_kana="レグ", first_name_kana="スタッフ", 
            employment_type="FULL_TIME", weekly_scheduled_minutes=2400,
            hire_date=date(2025, 1, 1),
            office_id=osc.office_id
        )
        supporter_regular.roles.append(regular_role)
        db.session.add(supporter_regular)

        db.session.commit()

        # Generate access tokens
        tok_sys_admin = create_access_token(identity=f"staff:{supporter_sys_admin.id}")
        tok_corp_admin_same = create_access_token(identity=f"staff:{supporter_corp_admin_same.id}")
        tok_corp_admin_diff = create_access_token(identity=f"staff:{supporter_corp_admin_diff.id}")
        tok_regular = create_access_token(identity=f"staff:{supporter_regular.id}")

        # Let's create an ACTIVE certificate to void
        cert_active = ServiceCertificate(
            user_id=user_id,
            office_service_configuration_id=osc_id,
            certificate_issue_date=date(2025, 1, 1),
            municipality_master_id=muni_id,
            status='ACTIVE'
        )
        db.session.add(cert_active)
        db.session.flush()

        # Let's create a PENDING_REVIEW certificate to void
        cert_pending = ServiceCertificate(
            user_id=user_id,
            office_service_configuration_id=osc_id,
            certificate_issue_date=date(2025, 1, 1),
            municipality_master_id=muni_id,
            status='PENDING_REVIEW'
        )
        db.session.add(cert_pending)
        db.session.flush()

        # Let's create a DRAFT certificate (which should NOT be allowed to void)
        cert_draft = ServiceCertificate(
            user_id=user_id,
            office_service_configuration_id=osc_id,
            certificate_issue_date=date(2025, 1, 1),
            municipality_master_id=muni_id,
            status='DRAFT'
        )
        db.session.add(cert_draft)
        db.session.flush()

        db.session.commit()

        # --- Test 1: Void DRAFT cert (Should fail 400) ---
        res = client.post(
            f'/api/users/{user_id}/certificates/{cert_draft.id}/void',
            json={"void_reason": "DRAFTを無効化します"},
            headers={'Authorization': f'Bearer {tok_sys_admin}'}
        )
        assert res.status_code == 400
        assert "有効または確認待ち状態" in res.get_json()['msg']

        # --- Test 2: Void with missing reason (Should fail 400) ---
        res = client.post(
            f'/api/users/{user_id}/certificates/{cert_active.id}/void',
            json={"void_reason": ""},
            headers={'Authorization': f'Bearer {tok_sys_admin}'}
        )
        assert res.status_code == 400
        assert "無効化の理由を入力してください" in res.get_json()['msg']

        # --- Test 3: Void by non-admin regular staff (Should fail 403) ---
        res = client.post(
            f'/api/users/{user_id}/certificates/{cert_active.id}/void',
            json={"void_reason": "権限なし無効化"},
            headers={'Authorization': f'Bearer {tok_regular}'}
        )
        assert res.status_code == 403
        assert "無効化操作は管理者権限" in res.get_json()['msg']

        # --- Test 4: Void by corporate admin in different corporation (Should fail 403) ---
        res = client.post(
            f'/api/users/{user_id}/certificates/{cert_active.id}/void',
            json={"void_reason": "別法人のため失敗"},
            headers={'Authorization': f'Bearer {tok_corp_admin_diff}'}
        )
        assert res.status_code == 403
        assert "所属する法人以外の受給者証は無効化できません" in res.get_json()['msg']

        # --- Test 5: Void by corporate admin in SAME corporation (Should succeed 200) ---
        res = client.post(
            f'/api/users/{user_id}/certificates/{cert_active.id}/void',
            json={"void_reason": "同一法人管理者による無効化。誤入力のため。"},
            headers={'Authorization': f'Bearer {tok_corp_admin_same}'}
        )
        assert res.status_code == 200
        assert res.get_json()['status'] == 'VOIDED'

        db.session.refresh(cert_active)
        assert cert_active.status == 'VOIDED'
        assert cert_active.void_reason == "同一法人管理者による無効化。誤入力のため。"
        assert cert_active.voided_by_supporter_id == supporter_corp_admin_same.id
        assert cert_active.voided_at is not None

        # --- Test 6: Void PENDING_REVIEW by system admin (Should succeed 200) ---
        res = client.post(
            f'/api/users/{user_id}/certificates/{cert_pending.id}/void',
            json={"void_reason": "システム管理者による無効化。誤申請のため。"},
            headers={'Authorization': f'Bearer {tok_sys_admin}'}
        )
        assert res.status_code == 200
        assert res.get_json()['status'] == 'VOIDED'

        db.session.refresh(cert_pending)
        assert cert_pending.status == 'VOIDED'
        assert cert_pending.void_reason == "システム管理者による無効化。誤申請のため。"
        assert cert_pending.voided_by_supporter_id == supporter_sys_admin.id
        assert cert_pending.voided_at is not None

        # --- Test 7: Verify serialization includes void fields ---
        from backend.app.api.users.certificates import serialize_cert
        serialized_active = serialize_cert(cert_active)
        assert serialized_active['status'] == 'VOIDED'
        assert serialized_active['void_reason'] == "同一法人管理者による無効化。誤入力のため。"
        assert serialized_active['voided_by_supporter_id'] == supporter_corp_admin_same.id
        assert serialized_active['voided_at'] is not None


