from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager # ★追加
from flask_cors import CORS # ★追加

# 🚨 将来の認証機能(API)のためにJWTもここで定義
# from flask_jwt_extended import JWTManager
# 🚨 将来のフロントエンド連携(CORS)のためにここで定義
# from flask_cors import CORS

# ====================================================================
# 拡張機能の「実体（インスタンス）」をここで一元的に定義する。
# 
# 哲学（ムダの排除）:
# アプリケーション本体(app)とは分離して定義することで、
# 他のモジュール（例: モデル）が 'from .extensions import db' と
# 参照しても、循環参照エラーが発生しないようにする。
# ====================================================================

# データベースオブジェクト (SQLAlchemy)
db = SQLAlchemy()

# 暗号化オブジェクト (Bcrypt)
bcrypt = Bcrypt()

# マイグレーションオブジェクト (Migrate)
migrate = Migrate()

# 将来の認証(JWT)オブジェクト
jwt = JWTManager() 

# 将来のCORSオブジェクト
cors = CORS()
