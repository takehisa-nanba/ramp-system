import os
from dotenv import load_dotenv # ★追加★

# ★★★ .envファイルを強制的にロードするロジックをファイル上部に移動 ★★★
basedir = os.path.abspath(os.path.dirname(__file__))
dotenv_path = os.path.join(basedir, '../.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path, override=True)
# ★★★ ここまで ★★★
# データベースのURIを環境変数から取得（なければデフォルトのSQLite）
# 船長の環境に合わせて、PostgreSQLの接続文字列を環境変数 'DATABASE_URL' に設定してください
#例: postgresql://user:password@localhost/ramp_db
DATABASE_URL = os.environ.get('DATABASE_URL') or \
    'sqlite:///' + os.path.join(basedir, 'app.db')

# ★★★ Windows/WSL 2環境用: localhost接続をWSL IPに動的解決するロジック ★★★
# (ローカルWindows環境にPostgreSQLをインストールして直接接続するため、動的解決を無効化しそのまま返します)
def resolve_wsl_ip(url: str) -> str:
    return url

DATABASE_URL = resolve_wsl_ip(DATABASE_URL)
# ★★★ ここまで ★★★


class Config:
    """
    アプリケーションの設定（コンフィグ）を管理するクラス。
    """
    
    # SQLAlchemyの設定
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ★★★ PIIおよびFERNETキーをアプリケーション設定に追加 ★★★
    # 本番環境では必須。開発環境ではフォールバックを使用。
    is_production = os.environ.get('FLASK_ENV') == 'production'
    
    _secret_key = os.environ.get('SECRET_KEY')
    _pii_key = os.environ.get('PII_ENCRYPTION_KEY')
    _fernet_key = os.environ.get('FERNET_ENCRYPTION_KEY')
    
    if is_production and (not _secret_key or not _pii_key or not _fernet_key):
        raise ValueError("CRITICAL: Missing encryption keys in production environment. System halting.")

    SECRET_KEY = _secret_key or 'a-very-secret-key-that-you-should-change'
    PII_ENCRYPTION_KEY = _pii_key or 'FALLBACK_PII_KEY_FOR_TESTS_ONLY'
    FERNET_ENCRYPTION_KEY = _fernet_key or 'FALLBACK_FERNET_KEY_FOR_TESTS_ONLY'
    # ★★★ ここまで ★★★
    
    # --- JWT-Extended 設定 (NEW) --- ★追加
    import datetime
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'a-default-jwt-secret-for-testing'
    # JWTの有効期限を 30分 に短縮（本番運用向け）
    JWT_ACCESS_TOKEN_EXPIRES = datetime.timedelta(minutes=30)
    # JWTをCookieに設定する（HTTP-Only, Secure, CSRF有効）
    JWT_TOKEN_LOCATION = ["cookies", "headers"]

    JWT_COOKIE_SECURE = is_production # 本番環境ではTrue (HTTPS必須)
    JWT_COOKIE_SAMESITE = 'Lax'
    JWT_COOKIE_CSRF_PROTECT = is_production # 本番環境ではCSRF保護を有効化

    JWT_CSRF_CHECK_FOR_FORM_FIELDS = False
    
    # --- CORS設定 ---
    # CORS_ORIGINS が指定されていない場合は、開発用に localhost を許可する
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:5173').split(',')
    # --- JWT設定ここまで ---

    # --- その他の設定（必要に応じて追加） ---
    # (例: CORS, Mailなど)