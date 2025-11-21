import pytest
from datetime import date
from backend.app import db
from backend.app.models import (
    Corporation, OfficeSetting, OfficeServiceConfiguration,
    MunicipalityMaster, ServiceTypeMaster, StatusMaster,
    User, ServiceCertificate, GrantedService, ContractReportDetail
)
from backend.app.services.core_service import get_corporation_id_for_user

def test_get_corporation_id_for_user(app):
    """
    契約チェーンを辿って正しい法人IDが取得できるかテスト
    """
    with app.app_context():
        # 1. 準備: マスタと組織構造を作る
        # 法人 (ID: 999 を期待値とする)
        corp = Corporation(id=999, corporation_name="Test Corp", corporation_type="KK")
        db.session.add(corp)
        
        # マスタ
        muni = MunicipalityMaster(municipality_code="123456", name="Test City")
        stype = ServiceTypeMaster(name="Test Service", service_code="TS", required_review_months=6)
        status = StatusMaster(name="Test Status")
        db.session.add_all([muni, stype, status])
        db.session.flush()

        # 事業所とサービス
        office = OfficeSetting(corporation_id=corp.id, office_name="Test Office", municipality_id=muni.id)
        db.session.add(office)
        db.session.flush()

        service_config = OfficeServiceConfiguration(
            office_id=office.id, 
            service_type_master_id=stype.id,
            jigyosho_bango="1234567890",
            capacity=20
        )
        db.session.add(service_config)
        db.session.flush()

        # 2. ユーザーと契約を作る
        user = User(display_name="Test User", status_id=status.id)
        db.session.add(user)
        db.session.flush()

        cert = ServiceCertificate(user_id=user.id, certificate_issue_date=date.today(), municipality_master_id=muni.id, office_service_configuration_id=service_config.id)
        db.session.add(cert)
        db.session.flush()

        grant = GrantedService(certificate_id=cert.id, granted_start_date=date.today(), granted_end_date=date.today(), service_type_master_id=stype.id)
        db.session.add(grant)
        db.session.flush()

        # ★ ここが紐づけの核心
        contract = ContractReportDetail(
            granted_service_id=grant.id,
            office_service_configuration_id=service_config.id # ここで事業所(999)に紐づく
        )
        db.session.add(contract)
        db.session.commit()

        # 3. 検証: ロジックを呼び出す
        result_id = get_corporation_id_for_user(user)

        # 4. 判定: 期待通り 999 が返ってくるか？
        assert result_id == 999