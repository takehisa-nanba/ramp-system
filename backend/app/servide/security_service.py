# app/services/security_service.py

from cryptography.fernet import Fernet
import os
from flask import current_app # Flaskの設定を読み込むために使用

# 環境変数からマスターキーを取得 (KMSの鍵IDの代わり)
# 鍵が設定されていない場合のフォールバックを設定
MASTER_KEY = os.environ.get("ENCRYPTION_MASTER_KEY") 

def initialize_fernet_client():
    """環境変数からマスターキーを読み込み、Fernetクライアントを初期化する"""
    if not MASTER_KEY:
        # 本番環境ではここでアプリケーションを停止すべき重大なエラー
        raise ValueError("ENCRYPTION_MASTER_KEY環境変数が設定されていません。")
    try:
        # 環境変数から鍵をデコードしてFernetクライアントを初期化
        return Fernet(MASTER_KEY.encode('utf-8'))
    except Exception as e:
        raise ValueError(f"暗号化マスターキーの初期化に失敗しました: {e}")

def encrypt_data(plaintext: str) -> str:
    """受給者証番号を暗号化する"""
    if not plaintext:
        return None
    f = initialize_fernet_client()
    ciphertext = f.encrypt(plaintext.encode('utf-8'))
    return ciphertext.decode('utf-8')

def decrypt_data(ciphertext: str) -> str:
    """暗号文を復号化する"""
    if not ciphertext:
        return None
    try:
        f = initialize_fernet_client()
        # 復号中に例外が発生する可能性（鍵違い、データ破損など）があるためtry-exceptで囲む
        plaintext = f.decrypt(ciphertext.encode('utf-8'))
        return plaintext.decode('utf-8')
    except Exception:
        # 復号失敗時は、データが無効である旨を示すか、Noneを返すなど安全な処理を行う
        current_app.logger.error("Failed to decrypt data due to invalid key or token.")
        return None # 失敗時は安全のためにNoneを返す

# ★ 鍵を生成し、環境変数として設定するステップを忘れずに行ってください
# 例: print(Fernet.generate_key().decode()) を実行して得られた文字列を使う