import os
import sys
import traceback
import datetime

# -------------------------------------------------------------------
# パス解決のロジック
# -------------------------------------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_dir)

if project_root not in sys.path:
    sys.path.insert(0, project_root)

# ログファイルのパス
LOG_FILE = os.path.join(current_dir, 'model_loading_error.log')

def log_error(title, exception):
    """エラーをターミナルとファイルの両方に出力する"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    error_msg = f"\n{'='*60}\n"
    error_msg += f"🚨 {title} - {timestamp}\n"
    error_msg += f"{'='*60}\n"
    error_msg += traceback.format_exc()
    error_msg += f"\n{'='*60}\n"

    # ターミナル出力（色付きだと尚良しだが、標準出力で）
    print(error_msg)

    # ファイル出力
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(error_msg)
        print(f"📝 Error details saved to: {LOG_FILE}")
    except Exception as e:
        print(f"Could not write to log file: {e}")

def diagnose():
    print(f"🔍 Starting Model Loading Diagnosis...")
    print(f"   Target: {backend_dir}")
    
    # 既存のログをクリア（任意）
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w') as f:
            f.write(f"Diagnosis Session: {datetime.datetime.now()}\n")

    # 1. アプリケーションファクトリのインポートテスト
    try:
        print("👉 Step 1: Importing create_app...")
        from backend.app import create_app, db
        print("   ✅ Success.")
    except Exception as e:
        log_error("Step 1 Failed: Could not import 'create_app'", e)
        return

    # 2. アプリケーションコンテキストの作成とモデル読み込み
    try:
        print("👉 Step 2: Creating App Context & Importing Models...")
        app = create_app()
        with app.app_context():
            print("   ✅ App context pushed.")
            
            # 3. SQLAlchemyのマッパー設定（リレーションの整合性チェック）
            # ここで 'InvalidRequestError' (紐づけ先不明) などが発覚する
            print("👉 Step 3: Configuring SQLAlchemy Mappers...")
            try:
                from sqlalchemy.orm import configure_mappers
                configure_mappers()
                print("   ✅ Success. All models and relationships are valid.")
            except Exception as e:
                log_error("Step 3 Failed: Mapper Configuration Error (Relationship Mismatch)", e)
                print("   💡 Hint: Check if the related model is imported in 'app/models/__init__.py'")
                return

            print("\n🎉 DIAGNOSIS COMPLETE: System is healthy!")

    except Exception as e:
        log_error("Step 2 Failed: Error during app initialization", e)

if __name__ == '__main__':
    diagnose()