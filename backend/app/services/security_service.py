# app/services/security_service.py (最終修正版)

import os
from cryptography.fernet import Fernet
import base64
import logging

# ★ トップレベルから CMK_KEY 定義を削除しました ★

def _get_cmk_fernet() -> Fernet | None:
    """CMK (マスターキー) の役割を担うFernetインスタンスを生成する"""
    # 鍵を関数内で os.environ から動的に読み込む
    cmk_key = os.environ.get('ENCRYPTION_MASTER_KEY')
    
    if not cmk_key:
        logging.error("CMK (ENCRYPTION_MASTER_KEY) が設定されていません。")
        # 鍵がない場合は処理続行不可
        return None
    try:
        # 環境変数から最新の鍵を使ってインスタンスを生成
        return Fernet(cmk_key.encode('utf-8'))
    except Exception:
        logging.error("CMKの初期化に失敗しました。")
        return None

def encrypt_data(plaintext: str) -> str:
    """エンベロープ暗号化を実行 (暗号化済みDEKとデータ本体を連結)"""
    if not plaintext: return None
        
    # 1. DEKの動的生成
    data_key_plaintext = Fernet.generate_key() 
    data_key_fernet = Fernet(data_key_plaintext)
    
    # 2. データ本体の暗号化 (DEKを使用)
    ciphertext_data = data_key_fernet.encrypt(plaintext.encode('utf-8'))
    
    # 3. DEKの暗号化 (CMKを使用 - ここがKMSの役割)
    cmk_fernet = _get_cmk_fernet()
    if not cmk_fernet: raise Exception("CMKアクセス失敗")
        
    encrypted_data_key = cmk_fernet.encrypt(data_key_plaintext)
    
    # 4. 暗号文と暗号化DEKを連結して保存
    return (base64.b64encode(encrypted_data_key).decode('utf-8') + ":" + 
            base64.b64encode(ciphertext_data).decode('utf-8'))

def decrypt_data(ciphertext_envelope: str) -> str | None:
    """KMS (CMK) を使ってDEKを復号し、データ本体を復号します"""
    if not ciphertext_envelope or ":" not in ciphertext_envelope: return None

    try:
        encrypted_dek_b64, ciphertext_data_b64 = ciphertext_envelope.split(":")
        
        # 1. CMKを使って暗号化済みDEKを復号 (KMSアクセスをシミュレート)
        cmk_fernet = _get_cmk_fernet()
        if not cmk_fernet: return None
        
        encrypted_dek = base64.b64decode(encrypted_dek_b64)
        data_key_plaintext = cmk_fernet.decrypt(encrypted_dek) # ★ ここで鍵が異なると例外が発生 ★
        
        # 2. 復号されたDEKを使ってデータ本体を復号
        data_key_fernet = Fernet(data_key_plaintext)
        ciphertext_data = base64.b64decode(ciphertext_data_b64)
        
        plaintext = data_key_fernet.decrypt(ciphertext_data)
        return plaintext.decode('utf-8')
        
    except Exception as e:
        # 鍵違い (Fernetのdecrypt失敗) やデータ破損の場合、安全にNoneを返す
        # print(f"DEBUG: Decryption failed due to {e}") 
        return None