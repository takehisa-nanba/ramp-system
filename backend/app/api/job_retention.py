from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import date
from backend.app.models import JobRetentionContract
from backend.app.services.job_retention_service import JobRetentionService
from backend.app.services.core_service import parse_jwt_identity
from backend.app.utils.errors import PermissionDenied, ValidationError

job_retention_bp = Blueprint('job_retention', __name__, url_prefix='/api/job-retention')


def actor_id():
    identity = get_jwt_identity()
    if not isinstance(identity, str) or not identity.startswith('staff:'):
        raise PermissionDenied()
    role, staff_id = parse_jwt_identity(identity)
    if role != 'staff' or not staff_id:
        raise PermissionDenied()
    return staff_id


def payload():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError('JSONオブジェクトを指定してください。')
    return data


def parse_date(data, key):
    try:
        value = data[key]
        if not isinstance(value, str) or len(value) != 10:
            raise ValueError()
        return date.fromisoformat(value)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValidationError(f'{key} は YYYY-MM-DD 形式で指定してください。') from exc


@job_retention_bp.get('/users')
@jwt_required()
def list_users():
    return jsonify(items=JobRetentionService.list_users(actor_id()))


@job_retention_bp.get('/users/<int:user_id>')
@jwt_required()
def user_contracts(user_id):
    contracts = JobRetentionService.contracts_query(actor_id()).filter(JobRetentionContract.user_id == user_id).all()
    return jsonify(items=[JobRetentionService.serialize(c) for c in contracts])


@job_retention_bp.get('/contracts/<int:contract_id>')
@jwt_required()
def get_contract(contract_id):
    return jsonify(JobRetentionService.serialize(JobRetentionService.get_contract(contract_id, actor_id())))


@job_retention_bp.post('/users/<int:user_id>/start')
@jwt_required()
def start(user_id):
    data = payload()
    config_id = data.get('office_service_configuration_id')
    if type(config_id) is not int or config_id <= 0:
        raise ValidationError('事業所サービスを指定してください。')
    contract = JobRetentionService.start_retention_support(user_id, config_id,
        parse_date(data, 'contract_start_date'), parse_date(data, 'contract_end_date'),
        actor_id(), data.get('reason'), request.remote_addr, request.user_agent.string)
    return jsonify(JobRetentionService.serialize(contract)), 201


@job_retention_bp.post('/contracts/<int:contract_id>/finish')
@jwt_required()
def finish(contract_id):
    data = payload()
    contract = JobRetentionService.finish_retention_support(contract_id,
        parse_date(data, 'contract_end_date'), actor_id(), data.get('reason'),
        request.remote_addr, request.user_agent.string)
    return jsonify(JobRetentionService.serialize(contract))
