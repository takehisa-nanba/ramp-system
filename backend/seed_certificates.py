import sys
import os

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app import create_app, db
from backend.app.models import User, OfficeServiceConfiguration
from backend.app.models.core.service_certificate import ServiceCertificate, GrantedService
from datetime import date, timedelta
import random

app = create_app()

def seed_certificates():
    with app.app_context():
        users = User.query.all()
        if not users:
            print("No users found.")
            return

        office_config = OfficeServiceConfiguration.query.first()
        if not office_config:
            print("No office configuration found.")
            return

        for user in users:
            # Check if certificate already exists
            existing = ServiceCertificate.query.filter_by(user_id=user.id).first()
            if existing:
                continue
            
            issue_date = date(2025, 4, 1)
            
            # Create an old certificate
            old_cert = ServiceCertificate(
                user_id=user.id,
                office_service_configuration_id=office_config.id,
                certificate_issue_date=issue_date - timedelta(days=365),
                municipality_master_id=1,
                certificate_type="障害福祉サービス受給者証",
                disability_support_classification="区分3",
                certificate_notes="旧受給者証データ（ダミー履歴）"
            )
            db.session.add(old_cert)
            db.session.flush()
            
            old_granted = GrantedService(
                certificate_id=old_cert.id,
                service_type_master_id=1, # 就労継続支援B型
                granted_start_date=issue_date - timedelta(days=365),
                granted_end_date=issue_date - timedelta(days=1),
                granted_amount_description="20日/月"
            )
            db.session.add(old_granted)

            # Create current certificate
            new_cert = ServiceCertificate(
                user_id=user.id,
                office_service_configuration_id=office_config.id,
                certificate_issue_date=issue_date,
                municipality_master_id=1,
                certificate_type="障害福祉サービス受給者証",
                disability_support_classification="区分3",
                certificate_notes="現在の受給者証（ダミー）"
            )
            db.session.add(new_cert)
            db.session.flush()

            new_granted = GrantedService(
                certificate_id=new_cert.id,
                service_type_master_id=1, # 就労継続支援B型
                granted_start_date=issue_date,
                granted_end_date=issue_date + timedelta(days=364),
                granted_amount_description="22日/月"
            )
            db.session.add(new_granted)

        db.session.commit()
        print("Successfully seeded certificates.")

if __name__ == '__main__':
    seed_certificates()
