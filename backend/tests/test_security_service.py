import pytest
import logging
from cryptography.fernet import Fernet

#  修正点: 責務分離に合わせてインポート元を変更
# 1. 暗号化ロジック（道具）
from backend.app.services.security_service import (
    encrypt_data_pii, decrypt_data_pii,
    encrypt_data_envelope, decrypt_data_envelope
)
# 2. 鍵取得ロジック（金庫番）
from backend.app.services.core_service import (
    get_system_pii_key, get_corporation_kek
)

logger = logging.getLogger(__name__)

def test_pii_encryption_decryption(app):
    """
    階層2: システム共通鍵による暗号化・復号化のテスト
    """
    logger.info("🚀 TEST START: PII暗号化(階層2)の検証")
    
    with app.app_context():
        # 1. core_service から鍵を取得
        key = get_system_pii_key()
        original_text = "東京都港区1-2-3"
        
        # 2. 暗号化
        encrypted = encrypt_data_pii(original_text, key)
        logger.debug(f"   -> Encrypted: {encrypted[:10]}...")
        assert encrypted != original_text
        
        # 3. 復号化
        decrypted = decrypt_data_pii(encrypted, key)
        logger.debug(f"   -> Decrypted: {decrypted}")
        assert decrypted == original_text

        # 4. 不正な鍵での復号（失敗を確認）
        invalid_key = Fernet.generate_key()
        failed_decryption = decrypt_data_pii(encrypted, invalid_key)
        assert failed_decryption is None
        logger.info("✅ PII暗号化/復号化/防御の検証完了")

def test_envelope_encryption_decryption(app):
    """
    階層1: エンベロープ暗号化（二重鍵）のテスト
    """
    logger.info("🚀 TEST START: エンベロープ暗号化(階層1)の検証")

    with app.app_context():
        # 1. core_service から法人KEKを取得
        corp_id = 1
        kek = get_corporation_kek(corp_id)
        original_text = "1234567890" # 受給者証番号など
        
        # 2. 暗号化 (データとDEKが返る)
        enc_data, enc_dek = encrypt_data_envelope(original_text, kek)
        
        assert enc_data is not None
        assert enc_dek is not None
        assert enc_data != original_text
        logger.debug(f"   -> Encrypted Data: {enc_data[:10]}...")
        logger.debug(f"   -> Encrypted DEK: {enc_dek[:10]}...")

        # 3. 復号化
        decrypted = decrypt_data_envelope(enc_data, enc_dek, kek)
        assert decrypted == original_text
        logger.debug(f"   -> Decrypted: {decrypted}")

        # 4. 不正なKEKでの復号（失敗を確認）
        # 別の法人の鍵（をシミュレートした偽鍵）では開かないはず
        fake_kek = Fernet.generate_key()
        failed_decryption = decrypt_data_envelope(enc_data, enc_dek, fake_kek)
        assert failed_decryption is None
        logger.info("✅ エンベロープ暗号化の検証完了")