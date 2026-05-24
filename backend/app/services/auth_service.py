# backend/app/services/auth_service.py

from backend.app.services.core_service import authenticate_user, authenticate_supporter

def perform_login(login_id, password, user_type):
    """
    ユーザーまたは職員の認証を行い、JWTトークンに含めるべきペイロード情報を生成する。
    
    :param login_id: ログインIDまたはメールアドレス
    :param password: パスワード
    :param user_type: 'staff' または 'user'
    :return: (成功可否: bool, token_data: dict, error_message: str)
    """
    if user_type == 'staff':
        supporter = authenticate_supporter(login_id, password)
        if supporter:
            role_name = "STAFF"
            identity = f"staff:{supporter.id}"
            full_name = f"{supporter.last_name} {supporter.first_name}"
            user_id = supporter.id
            role_scopes = [r.role_scope for r in supporter.roles]
        else:
            return False, None, "Invalid credentials"
            
    elif user_type == 'user':
        user = authenticate_user(login_id, password)
        if user:
            role_name = "USER"
            identity = f"user:{user.id}"
            full_name = user.display_name
            user_id = user.id
            role_scopes = []
        else:
            return False, None, "Invalid credentials"
            
    else:
        return False, None, "Invalid user_type. Must be 'staff' or 'user'."

    token_data = {
        'identity': identity,
        'claims': {
            "role_name": role_name,
            "full_name": full_name,
            "role_scopes": role_scopes
        },
        'response_data': {
            "user_id": user_id, 
            "role_name": role_name, 
            "full_name": full_name,
            "role_scopes": role_scopes
        }
    }
    
    return True, token_data, None
