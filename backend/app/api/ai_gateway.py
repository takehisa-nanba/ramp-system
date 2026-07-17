from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from backend.app.services.ai_gateway_service import AIGatewayService

ai_gateway_bp = Blueprint('ai_gateway', __name__, url_prefix='/api/ai-gateway')

@ai_gateway_bp.route('/test', methods=['POST'])
@jwt_required()
def test_ai_gateway():
    """
    AIゲートウェイの疎通確認用テストエンドポイント。
    フロントエンドから送信されたプロンプトをGeminiに渡し、結果を返します。
    """
    data = request.get_json()
    if not data or 'prompt' not in data:
        return jsonify({"success": False, "error": "プロンプトが指定されていません"}), 400
        
    prompt = data['prompt']
    # 本番（高品質）モードにするかのフラグ（デフォルトはFalseで高速なFlashモデル）
    use_pro = data.get('use_pro', False)
    system_instruction = data.get('system_instruction', None)
    
    try:
        response_text = AIGatewayService.generate_text(
            prompt=prompt,
            use_pro=use_pro,
            system_instruction=system_instruction
        )
        return jsonify({
            "success": True,
            "response": response_text,
            "model_used": AIGatewayService.PRO_MODEL if use_pro else AIGatewayService.FLASH_MODEL
        }), 200
        
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "サーバー内部でエラーが発生しました"
        }), 500
