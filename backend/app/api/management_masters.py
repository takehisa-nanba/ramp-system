from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from backend.app.models import RoleMaster

management_masters_bp = Blueprint('management_masters', __name__, url_prefix='/api/management/masters')

@management_masters_bp.route('', methods=['GET'])
@jwt_required()
def get_masters():
    """
    フロントエンドのセレクトボックス等で使用するマスターデータを一括で取得する。
    """
    from backend.app.models.masters.master_definitions import (
        MunicipalityMaster, ServiceTypeMaster, GenderLegalMaster, DisabilityTypeMaster
    )
    
    municipalities = MunicipalityMaster.query.order_by(MunicipalityMaster.id).all()
    service_types = ServiceTypeMaster.query.order_by(ServiceTypeMaster.id).all()
    genders = GenderLegalMaster.query.order_by(GenderLegalMaster.id).all()
    disabilities = DisabilityTypeMaster.query.order_by(DisabilityTypeMaster.id).all()
    
    return jsonify({
        "municipalities": [{"id": m.id, "city_name": m.name, "city_code": m.municipality_code} for m in municipalities],
        "service_types": [{"id": s.id, "service_name": s.name, "service_code": s.service_code} for s in service_types],
        "genders": [{"id": g.id, "name": g.name} for g in genders],
        "disabilities": [{"id": d.id, "name": d.name} for d in disabilities]
    }), 200

@management_masters_bp.route('/roles', methods=['GET'])
@jwt_required()
def get_available_roles():
    roles = RoleMaster.query.all()
    return jsonify([{
        "id": r.id,
        "name": r.name,
        "scope": r.role_scope,
        "is_admin": r.is_admin
    } for r in roles]), 200

@management_masters_bp.route('/job-titles', methods=['GET'])
@jwt_required()
def get_available_job_titles():
    from backend.app.models import JobTitleMaster
    titles = JobTitleMaster.query.all()
    return jsonify([{
        "id": t.id,
        "title_name": t.title_name,
        "is_management_role": t.is_management_role,
        "is_qualified_role": t.is_qualified_role
    } for t in titles]), 200
