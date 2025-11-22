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

class Config:
    """
    アプリケーションの設定（コンフィグ）を管理するクラス。
    """
    
    # --- 必須設定 ---
    
    # セキュリティキー (Flaskのセッション管理などに必須)
    # 🚨 本番環境では、これは必ず環境変数から読み込む強力なキーに変更してください
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-very-secret-key-that-you-should-change'
    
    # SQLAlchemyの設定
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ★★★ PIIおよびFERNETキーをアプリケーション設定に追加 ★★★
    # .envにあればその値を使用。なければ、テスト実行時に警告を出すためのFALLBACKキーを設定。
    PII_ENCRYPTION_KEY = os.environ.get('PII_ENCRYPTION_KEY') or 'FALLBACK_PII_KEY_FOR_TESTS_ONLY'
    FERNET_ENCRYPTION_KEY = os.environ.get('FERNET_ENCRYPTION_KEY') or 'FALLBACK_FERNET_KEY_FOR_TESTS_ONLY'
    # ★★★ ここまで ★★★
    
    # --- その他の設定（必要に応じて追加） ---
    # (例: JWT, CORS, Mailなど)