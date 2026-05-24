from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.app import db
from backend.app.models import SupporterFormDraft
from backend.app.services.core_service import parse_jwt_identity
from . import users_bp

@users_bp.route('/drafts', methods=['POST'])
@jwt_required()
def save_draft():
    """
    フォーム入力データの一時下書きを暗号化保存する（オートセーブ用）。
    """
    current_supporter_id = get_jwt_identity()
    _, supporter_id_int = parse_jwt_identity(current_supporter_id)
    
    data = request.get_json() or {}
    draft_key = data.get('draft_key')
    draft_data = data.get('data')
    
    if not draft_key:
        return jsonify({"msg": "Missing draft_key"}), 400
        
    try:
        draft = SupporterFormDraft.query.filter_by(
            supporter_id=supporter_id_int,
            draft_key=draft_key
        ).first()
        
        if not draft:
            draft = SupporterFormDraft(
                supporter_id=supporter_id_int,
                draft_key=draft_key
            )
            db.session.add(draft)
            
        draft.data = draft_data
        db.session.commit()
        
        return jsonify({"msg": "Draft auto-saved successfully"}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Draft save failed: {e}"}), 500

@users_bp.route('/drafts/<string:draft_key>', methods=['GET'])
@jwt_required()
def get_draft(draft_key):
    """
    指定されたキーの一時下書きデータを取得し、復号して返却する。
    """
    current_supporter_id = get_jwt_identity()
    _, supporter_id_int = parse_jwt_identity(current_supporter_id)
    
    try:
        draft = SupporterFormDraft.query.filter_by(
            supporter_id=supporter_id_int,
            draft_key=draft_key
        ).first()
        
        if not draft:
            return jsonify({"data": None}), 200
            
        return jsonify({"data": draft.data}), 200
        
    except Exception as e:
        return jsonify({"msg": f"Draft load failed: {e}"}), 500

@users_bp.route('/drafts/<string:draft_key>', methods=['DELETE'])
@jwt_required()
def delete_draft(draft_key):
    """
    指定されたキーの一時下書きデータをDBから削除する（登録成功時やキャンセル時）。
    """
    current_supporter_id = get_jwt_identity()
    _, supporter_id_int = parse_jwt_identity(current_supporter_id)
    
    try:
        draft = SupporterFormDraft.query.filter_by(
            supporter_id=supporter_id_int,
            draft_key=draft_key
        ).first()
        
        if draft:
            db.session.delete(draft)
            db.session.commit()
            
        return jsonify({"msg": "Draft cleared successfully"}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Draft clear failed: {e}"}), 500
