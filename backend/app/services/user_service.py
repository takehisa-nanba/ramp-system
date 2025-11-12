# app/services/user_service.py (概念コード)

from app.services.security_service import encrypt_data, decrypt_data
from app.models.core import User

def create_user_and_encrypt_certificate(data: dict):
    """新規ユーザー登録時に受給者証番号を暗号化する"""
    
    # 1. 暗号化処理の実行
    encrypted_cert = encrypt_data(data.get('certificate_number'))
    
    # 2. Userモデルのインスタンス化
    new_user = User(
        # 'certificate_number'の平文は渡さない
        display_name=data.get('display_name'),
        encrypted_certificate_number=encrypted_cert, # 暗号文を保存
        status_id=data.get('status_id', 1)
        # ... その他のカラム ...
    )
    
    # 3. データベースにコミット
    db.session.add(new_user)
    db.session.commit()
    
    return new_user

def get_user_certificate_number(user_id: int):
    """ユーザーから受給者証番号を復号して取得する（管理者権限が必要）"""
    user = User.query.get(user_id)
    if not user or not user.encrypted_certificate_number:
        return None
        
    # 復号処理の実行
    return decrypt_data(user.encrypted_certificate_number)
