from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from backend.app.api.job_retention import actor_id, payload
from backend.app.services.job_retention_plan_service import JobRetentionPlanService as Service

retention_plans_bp = Blueprint('retention_plans', __name__, url_prefix='/api/plans')


def context():
    return dict(ip_address=request.remote_addr, user_agent=request.user_agent.string)


@retention_plans_bp.get('/<int:plan_id>/retention-detail')
@jwt_required()
def get_detail(plan_id):
    return jsonify(Service.view_detail(plan_id, actor_id(), **context()))


@retention_plans_bp.put('/<int:plan_id>/retention-detail')
@jwt_required()
def save_detail(plan_id):
    return jsonify(Service.save_detail(plan_id, actor_id(), payload(), **context()))


@retention_plans_bp.post('/<int:plan_id>/retention-support-items')
@jwt_required()
def create_item(plan_id):
    return jsonify(Service.save_item(plan_id, actor_id(), payload(), **context())), 201


@retention_plans_bp.route('/<int:plan_id>/retention-support-items/<int:item_id>', methods=['PUT','DELETE'])
@jwt_required()
def change_item(plan_id, item_id):
    return jsonify(Service.save_item(plan_id, actor_id(), payload(), item_id=item_id,
        delete=request.method == 'DELETE', **context()))


@retention_plans_bp.post('/<int:plan_id>/retention-evaluation')
@jwt_required()
def evaluate(plan_id):
    return jsonify(Service.evaluate(plan_id, actor_id(), payload(), **context()))


@retention_plans_bp.put('/<int:plan_id>/retention-employment')
@jwt_required()
def employment(plan_id):
    return jsonify(Service.update_employment(plan_id, actor_id(), payload(), **context()))
