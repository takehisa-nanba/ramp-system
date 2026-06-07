import os
import sys
from datetime import date

sys.path.append(r'c:\Users\難波\Desktop\ramp-system')

from backend.app import create_app
from backend.app.models import Supporter, RoleMaster, JobTitleMaster, OfficeServiceConfiguration
from flask_jwt_extended import create_access_token

app = create_app()
with app.app_context():
    client = app.test_client()
    
    # 1. Prepare Admin
    admin = Supporter.query.filter_by(staff_code="admin-001").first()
    token = create_access_token(identity=f"staff:{admin.id}", additional_claims={
        "role_name": "STAFF",
        "full_name": f"{admin.last_name} {admin.first_name}",
        "role_scopes": [r.role_scope for r in admin.roles]
    })
    headers = {'Authorization': f'Bearer {token}'}
    
    # 2. Get Job Titles and Roles
    job_title = JobTitleMaster.query.filter_by(title_name="サービス管理責任者").first()
    
    print(f"Using Job Title: {job_title.title_name} (ID: {job_title.id})")
    
    # 3. Payload with roles and job assignments
    payload = {
        "last_name": "テスト",
        "first_name": "二郎",
        "last_name_kana": "てすと",
        "first_name_kana": "じろう",
        "staff_code": "S_TEST_888",
        "email": "test_888@example.com",
        "employment_type": "FULL_TIME",
        "hire_date": "2025-01-01",
        "weekly_scheduled_minutes": 2400,
        "role_ids": [],
        "allow_overlap_calculation": False,
        "is_active": True,
        "job_assignments": [
            {
                "job_title_id": job_title.id,
                "assigned_minutes": 2400,
                "is_deemed_assignment": False,
                "deemed_expiry_date": None
            }
        ]
    }
    
    response = client.post('/api/management/staff', json=payload, headers=headers)
    print("POST Status Code:", response.status_code)
    print("POST Response:", response.json)
