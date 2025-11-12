import pytest
from app.services.security_service import encrypt_data, decrypt_data
from cryptography.fernet import Fernet
import os

# テストに必要な環境変数を設定するためのフィクスチャを定義
# 実際の環境変数を使わず、テスト用の鍵を生成して使用します
@pytest.fixture(scope='session', autouse=True)
def setup_test_encryption_key():
    """テストセッション全体で有効な暗号化キーを設定"""
    
    # 新しい鍵を生成し、環境変数に設定
    test_key = Fernet.generate_key().decode()
    os.environ['ENCRYPTION_MASTER_KEY'] = test_key
    
    # モジュール内で鍵が読み込まれるようにMASTER_KEYを更新
    # ※ security_service.pyでMASTER_KEYが読み込まれるタイミングによっては、
    #    この方法では反映されない場合がありますが、まずは試します。

    print(f"\n--- [SETUP] TEST KEY GENERATED: {test_key[:10]}... ---")
    
    yield  # テストの実行を待機
    
    # テスト終了後に環境変数をクリア
    del os.environ['ENCRYPTION_MASTER_KEY']

# ====================================================================
# テストケース
# ====================================================================

def test_encryption_decryption_cycle_success(setup_test_encryption_key):
    """
    暗号化と復号のサイクルが正常に動作し、元のデータが回復できることを確認する
    """
    original_data = "1234567890-支援福祉サービス"
    
    # 1. 暗号化
    encrypted_data = encrypt_data(original_data)
    
    # 2. 検証: 暗号文が元のデータと異なり、Noneではないことを確認
    assert encrypted_data is not None
    assert encrypted_data != original_data
    
    # 3. 復号
    decrypted_data = decrypt_data(encrypted_data)
    
    # 4. 検証: 復号されたデータが元のデータと完全に一致することを確認
    assert decrypted_data == original_data

def test_decryption_with_wrong_key(setup_test_encryption_key):
    """
    異なる鍵で復号を試みた場合、安全にNoneが返されることを確認する
    """
    original_data = "999-安全第一-000"
    
    # 1. 元の鍵で暗号化
    correct_key = os.environ['ENCRYPTION_MASTER_KEY']
    encrypted_data = encrypt_data(original_data)

    # 2. 異なる鍵を設定 (KMSの鍵を変更した場合をシミュレート)
    os.environ['ENCRYPTION_MASTER_KEY'] = Fernet.generate_key().decode() 
    
    # 3. 復号を試みる
    failed_decryption = decrypt_data(encrypted_data)
    
    # 4. 検証: 復号は失敗し、安全にNoneが返されることを確認
    assert failed_decryption is None 
    
    # 5. 元の鍵に戻す
    os.environ['ENCRYPTION_MASTER_KEY'] = correct_key