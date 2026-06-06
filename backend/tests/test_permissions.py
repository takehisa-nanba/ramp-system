import pytest
import logging
from datetime import date
from flask_jwt_extended import create_access_token
from backend.app import db
from backend.app.models import User, Supporter, StatusMaster, PermissionMaster
from backend.app.models.core.user import UserPII

logger = logging.getLogger(__name__)

def create_supporter(staff_code):
    supporter = Supporter(
        staff_code=staff_code, 
        last_name="Test", first_name="Staff", 
        last_name_kana="テスト", first_name_kana="スタッフ", 
        employment_type="FULL_TIME", weekly_scheduled_minutes=2400,
        hire_date=date(2025, 1, 1)
    )
    db.session.add(supporter)
    return supporter

def test_view_pii_without_permission_masks_fields(app):
    """
    VIEW_PII権限を持たないユーザーがGET /api/users/<id>/pii を実行した場合、
    200 OKは返るが、PII情報が '********' にマスクされていることを検証する。
    """
    logger.info("🚀 TEST START: test_view_pii_without_permission_masks_fields")
    
    with app.app_context():
        status = db.session.query(StatusMaster).first()
        if not status:
            status = StatusMaster(name="利用中")
            db.session.add(status)
            db.session.flush()

        user = User(display_name="PII Test User", status_id=status.id, user_code="USR999")
        db.session.add(user)
        db.session.flush()
        
        pii = UserPII(user=user, last_name="山田", first_name="太郎", address="東京都", phone_number="090-0000-0000")
        db.session.add(pii)
        
        supporter = create_supporter("S_NO_VIEW")
        db.session.commit()
        
        token = create_access_token(identity=f"staff:{supporter.id}", additional_claims={
            "role_scopes": ["JOB"]
        })
        
        client = app.test_client()
        response = client.get(f'/api/users/{user.id}/pii', headers={'Authorization': f'Bearer {token}'})
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['pii']['last_name'] == "********"
        assert data['pii']['phone_number'] == "********"
        assert data['pii']['birth_date'] is None

def test_edit_pii_without_permission_returns_403(app):
    """
    EDIT_PII権限を持たないユーザーが POST /api/users を実行した場合、
    403 Forbidden が返ることを検証する。
    """
    logger.info("🚀 TEST START: test_edit_pii_without_permission_returns_403")
    
    with app.app_context():
        supporter = create_supporter("S_NO_EDIT")
        db.session.commit()
        
        token = create_access_token(identity=f"staff:{supporter.id}", additional_claims={
            "role_scopes": ["JOB"]
        })
        
        client = app.test_client()
        payload = {
            "display_name": "Test Create",
            "pii": {"last_name": "Create", "first_name": "User"}
        }
        response = client.post('/api/users', json=payload, headers={'Authorization': f'Bearer {token}'})
        
        assert response.status_code == 403
        data = response.get_json()
        assert "Missing 'EDIT_PII' permission" in data['msg']

def test_soft_deleted_user_is_excluded_from_list(app):
    """
    論理削除されたユーザーが、利用者一覧 (GET /api/users) から除外されることを検証する。
    """
    logger.info("🚀 TEST START: test_soft_deleted_user_is_excluded_from_list")
    
    with app.app_context():
        status = db.session.query(StatusMaster).first()
        if not status:
            status = StatusMaster(name="利用中")
            db.session.add(status)
            db.session.flush()
        
        active_user = User(display_name="Active User", status_id=status.id, user_code="USR101")
        deleted_user = User(display_name="Deleted User", status_id=status.id, user_code="USR102")
        
        db.session.add_all([active_user, deleted_user])
        db.session.flush()
        
        pii1 = UserPII(user=active_user)
        pii2 = UserPII(user=deleted_user)
        db.session.add_all([pii1, pii2])
        
        deleted_user.deleted_at = date.today()
        deleted_user.deleted_by_id = 1
        deleted_user.delete_reason = "Test Delete"
        db.session.commit()
        
        supporter = create_supporter("S_LIST")
        db.session.commit()
        
        token = create_access_token(identity=f"staff:{supporter.id}", additional_claims={
            "role_scopes": ["JOB"]
        })
        
        client = app.test_client()
        response = client.get('/api/users', headers={'Authorization': f'Bearer {token}'})
        
        assert response.status_code == 200
        data = response.get_json()
        
        user_ids = [u['id'] for u in data]
        assert active_user.id in user_ids
        assert deleted_user.id not in user_ids
