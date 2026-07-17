import os
from flask import current_app

class AIGatewayService:
    """
    Ramp-System全体のAI連携を統括するゲートウェイサービス。
    Gemini APIを利用してテキスト生成を行います。
    テスト時のコストを最小化するため、用途に応じて軽量モデルと高性能モデルを切り替えます。
    """
    
    FLASH_MODEL = "gemini-3.5-flash"
    PRO_MODEL = "gemini-3.5-flash" # Proモデルが未確定のためFlashで代用
    
    @classmethod
    def _get_client(cls):
        # google-genaiの新しいSDKのインポート
        try:
            from google import genai
        except ImportError:
            return None
            
        api_key = current_app.config.get('GEMINI_API_KEY')
        if not api_key:
            return None
            
        return genai.Client(api_key=api_key)

    @classmethod
    def generate_text(cls, prompt: str, use_pro: bool = False, system_instruction: str = None) -> str:
        """
        AIにプロンプトを送信し、テキストを生成します。
        
        Args:
            prompt (str): ユーザー入力プロンプト
            use_pro (bool): Trueの場合は高性能なGemini 1.5 Proを使用。Falseの場合は安価/高速なFlashを使用。
            system_instruction (str): AIに対するシステム指示（オプション）
            
        Returns:
            str: AIからの返答テキスト。APIキーがない場合はモックテキストを返します。
        """
        client = cls._get_client()
        
        if not client:
            model_name = cls.PRO_MODEL if use_pro else cls.FLASH_MODEL
            return f"[Mock AI Response - {model_name}] 開発環境のためAPIキーが未設定です。プロンプト: {prompt[:20]}..."

        model_name = cls.PRO_MODEL if use_pro else cls.FLASH_MODEL
        
        try:
            # system_instructionが指定された場合は設定に追加
            config = None
            if system_instruction:
                from google.genai import types
                config = types.GenerateContentConfig(
                    system_instruction=system_instruction,
                )
                
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config
            )
            return response.text
        except Exception as e:
            current_app.logger.error(f"Gemini API Error: {str(e)}")
            raise ValueError(f"AIの生成中にエラーが発生しました: {str(e)}")
