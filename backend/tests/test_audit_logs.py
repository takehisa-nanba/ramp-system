import pytest
import logging
from flask_jwt_extended import create_access_token
from backend.app import db
from backend.app.models import User, Supporter, StatusMaster
from backend.app.models.core.audit_log import AuditActionLog

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

def test_soft_delete_creates_audit_log(app):
    """
    論理削除実行時に、AuditActionLog が事実ベースで正しく生成されることを検証する。
    """
    logger.info("🚀 TEST START: test_soft_delete_creates_audit_log")
    
    from datetime import date
    with app.app_context():
        status = db.session.query(StatusMaster).first()
        if not status:
            status = StatusMaster(name="利用中")
            db.session.add(status)
            db.session.flush()

        user = User(display_name="Delete Target User", status_id=status.id, user_code="USR_DEL_1")
        db.session.add(user)
        db.session.flush()
        
        supporter = Supporter(
            staff_code="S_DEL_EXEC", 
            last_name="Exec", first_name="Staff", 
            last_name_kana="エグゼク", first_name_kana="スタッフ", 
            employment_type="FULL_TIME", weekly_scheduled_minutes=2400,
            hire_date=date(2025, 1, 1)
        )
        db.session.add(supporter)
        
        # Setup roles and permissions
        from backend.app.models import RoleMaster, PermissionMaster
        edit_pii_perm = PermissionMaster.query.filter_by(name='EDIT_PII').first()
        if not edit_pii_perm:
            edit_pii_perm = PermissionMaster(name='EDIT_PII')
            db.session.add(edit_pii_perm)
            
        admin_role = RoleMaster.query.filter_by(name='Admin Role').first()
        if not admin_role:
            admin_role = RoleMaster(name='Admin Role', role_scope='SYSTEM')
            db.session.add(admin_role)
            admin_role.permissions.append(edit_pii_perm)
            
        supporter.roles.append(admin_role)
        db.session.commit()
        
        token = create_access_token(identity=f"staff:{supporter.id}", additional_claims={
            "role_scopes": ["JOB", "EDIT_PII"] # Require EDIT_PII to delete
        })
        
        client = app.test_client()
        delete_reason = "退所のため"
        response = client.delete(f'/api/users/{user.id}', json={"reason": delete_reason}, headers={'Authorization': f'Bearer {token}'})
        
        assert response.status_code == 200
        
        # Verify AuditActionLog creation
        audit_log = AuditActionLog.query.filter_by(
            action='DELETE_USER',
            entity_type='users',
            entity_id=user.id
        ).first()
        
        assert audit_log is not None
        assert audit_log.actor_supporter_id == supporter.id
        assert audit_log.reason == delete_reason
        assert "Active" in audit_log.before_value
        assert audit_log.after_value == "Soft Deleted"
