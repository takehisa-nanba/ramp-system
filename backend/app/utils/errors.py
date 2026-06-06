class AppError(Exception):
    """基本となるアプリケーション例外"""
    def __init__(self, message, code="APP_ERROR", status_code=400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code

class ValidationError(AppError):
    """入力不正"""
    def __init__(self, message="入力値が不正です"):
        super().__init__(message, code="VALIDATION_ERROR", status_code=400)

class PermissionDenied(AppError):
    """権限なし"""
    def __init__(self, message="この操作を行う権限がありません"):
        super().__init__(message, code="PERMISSION_DENIED", status_code=403)

class NotFoundError(AppError):
    """対象なし"""
    def __init__(self, message="対象が見つかりません"):
        super().__init__(message, code="NOT_FOUND", status_code=404)

class ConflictError(AppError):
    """状態矛盾"""
    def __init__(self, message="状態に矛盾があります"):
        super().__init__(message, code="CONFLICT_ERROR", status_code=409)

class BusinessRuleError(AppError):
    """業務ルール違反"""
    def __init__(self, message="業務ルールに違反しています"):
        super().__init__(message, code="BUSINESS_RULE_ERROR", status_code=400)

class SystemError(AppError):
    """想定外のエラー"""
    def __init__(self, message="システムエラーが発生しました"):
        super().__init__(message, code="SYSTEM_ERROR", status_code=500)
