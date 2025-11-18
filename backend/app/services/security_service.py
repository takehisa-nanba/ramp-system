# 🚨 修正点: 'backend.app.models' への依存（インポート）を「すべて削除」
from backend.app.extensions import db, bcrypt
from cryptography.fernet import Fernet, InvalidToken
import os
import functools

# ====================================================================
# 1. 鍵管理（Key Management）
# ====================================================================

# 🚨 哲学（原理6）:
# このサービスは、もはや「どの鍵を使うか」を知らない。
# 渡された鍵（バイト列）で暗号化/復号化を実行する「道具」に徹する。

@functools.lru_cache(maxsize=None)
def _get_cipher_suite(key_bytes: bytes) -> Fernet:
    """
    暗号鍵（バイト列）を受け取り、Fernetインスタンスを返す（キャッシュ利用）。
    """
    if not key_bytes:
        raise ValueError("Encryption key cannot be empty.")
    try:
        return Fernet(key_bytes)
    except Exception as e:
        raise ValueError(f"Invalid key format: {e}")

# ====================================================================
# 2. 階層2：システム共通鍵サービス (PII用)
# ====================================================================

def encrypt_data_pii(plaintext: str, key_bytes: bytes) -> str:
    """
    【階層2】
    平文と「システム共通鍵（DEK）」を受け取り、暗号化する。
    (対象: 氏名, 住所, 電話番号など)
    """
    if not plaintext:
        return None
    try:
        cipher_suite = _get_cipher_suite(key_bytes)
        encrypted_bytes = cipher_suite.encrypt(plaintext.encode('utf-8'))
        return encrypted_bytes.decode('utf-8')
    except Exception as e:
        print(f"PII Encryption failed: {e}")
        return None

def decrypt_data_pii(encrypted_text: str, key_bytes: bytes) -> str:
    """
    【階層2】
    暗号化された文字列と「システム共通鍵（DEK）」を受け取り、復号化する。
    """
    if not encrypted_text:
        return None
    try:
        cipher_suite = _get_cipher_suite(key_bytes)
        decrypted_bytes = cipher_suite.decrypt(encrypted_text.encode('utf-8'))
        return decrypted_bytes.decode('utf-8')
    except InvalidToken:
        print("PII Decryption failed: Invalid Token")
        return None
    except Exception as e:
        print(f"PII Decryption failed: {e}")
        return None

# ====================================================================
# 3. 階層1：エンベロープ暗号化サービス (最高機密用)
# ====================================================================

def encrypt_data_envelope(plaintext: str, kek_bytes: bytes) -> (str, str):
    """
    【階層1】
    平文と「法人のマスターキー（KEK）」を受け取り、
    暗号化されたデータと、暗号化されたDEK（データキー）を返す。
    """
    if not plaintext:
        return None, None
    try:
        # 1. データキー (DEK) を「それぞれ発行」する
        dek_bytes = Fernet.generate_key()
        dek_cipher = _get_cipher_suite(dek_bytes)
        
        # 2. DEKで「データ」を暗号化
        encrypted_data_bytes = dek_cipher.encrypt(plaintext.encode('utf-8'))
        
        # 3. 法人マスターキー (KEK) で「DEK」を暗号化
        kek_cipher = _get_cipher_suite(kek_bytes)
        encrypted_dek_bytes = kek_cipher.encrypt(dek_bytes)
        
        return encrypted_data_bytes.decode('utf-8'), encrypted_dek_bytes.decode('utf-8')
        
    except Exception as e:
        print(f"Envelope Encryption failed: {e}")
        return None, None

def decrypt_data_envelope(encrypted_text: str, encrypted_dek: str, kek_bytes: bytes) -> str:
    """
    【階層1】
    暗号化データ、暗号化DEK、法人のKEKを受け取り、平文を返す。
    """
    if not encrypted_text or not encrypted_dek:
        return None
    try:
        # 1. KEKで「DEK」を復号化
        kek_cipher = _get_cipher_suite(kek_bytes)
        dek_bytes = kek_cipher.decrypt(encrypted_dek.encode('utf-8'))
        
        # 2. DEKで「データ」を復号化
        dek_cipher = _get_cipher_suite(dek_bytes)
        decrypted_bytes = dek_cipher.decrypt(encrypted_text.encode('utf-8'))
        
        return decrypted_bytes.decode('utf-8')
        
    except InvalidToken:
        print(f"Envelope Decryption failed: Invalid Token (wrong KEK?)")
        return None
    except Exception as e:
        print(f"Envelope Decryption failed: {e}")
        return None