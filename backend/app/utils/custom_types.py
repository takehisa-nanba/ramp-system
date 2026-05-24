# backend/app/utils/custom_types.py

from sqlalchemy.types import TypeDecorator, String
from backend.app.services.security_service import encrypt_data_pii, decrypt_data_pii
from backend.config import Config

class EncryptedString(TypeDecorator):
    """透過的にシステム共通鍵(PII_ENCRYPTION_KEY)で暗号化・復号を行うカスタム型"""
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """PythonからDBに保存する際の暗号化処理"""
        if value is None:
            return None
        # Configクラスから直接キーを取得（current_appに依存しない）
        return encrypt_data_pii(value, Config.PII_ENCRYPTION_KEY)

    def process_result_value(self, value, dialect):
        """DBからPythonに読み出す際の復号処理"""
        if value is None:
            return None
        return decrypt_data_pii(value, Config.PII_ENCRYPTION_KEY)
