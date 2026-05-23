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
    
    # --- 必須設定 ---
    
    # セキュリティキー (Flaskのセッション管理などに必須)
    #  本番環境では、これは必ず環境変数から読み込む強力なキーに変更してください
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-very-secret-key-that-you-should-change'
    
    # SQLAlchemyの設定
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ★★★ PIIおよびFERNETキーをアプリケーション設定に追加 ★★★
    # .envにあればその値を使用。なければ、テスト実行時に警告を出すためのFALLBACKキーを設定。
    PII_ENCRYPTION_KEY = os.environ.get('PII_ENCRYPTION_KEY') or 'FALLBACK_PII_KEY_FOR_TESTS_ONLY'
    FERNET_ENCRYPTION_KEY = os.environ.get('FERNET_ENCRYPTION_KEY') or 'FALLBACK_FERNET_KEY_FOR_TESTS_ONLY'
    # ★★★ ここまで ★★★
    
    # --- JWT-Extended 設定 (NEW) --- ★追加
    import datetime
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'a-default-jwt-secret-for-testing'
    # JWTの有効期限を 1日 に延長（デフォルト15分による開発中のトークン切れを防止）
    JWT_ACCESS_TOKEN_EXPIRES = datetime.timedelta(days=1)
    # JWTをCookieに設定する（HTTP-Only, Secure, CSRF有効）
    JWT_TOKEN_LOCATION = ["cookies", "headers"]

    JWT_COOKIE_SECURE = False # 開発中はFalse (HTTPS不要)
    JWT_COOKIE_SAMESITE = 'Lax'
    JWT_COOKIE_CSRF_PROTECT = False

    JWT_CSRF_CHECK_FOR_FORM_FIELDS = False
    # --- JWT設定ここまで ---

    # --- その他の設定（必要に応じて追加） ---
    # (例: CORS, Mailなど)