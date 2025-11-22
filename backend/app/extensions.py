from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager # ★ 追加

# データベースオブジェクト
db = SQLAlchemy()

# 暗号化オブジェクト
bcrypt = Bcrypt()

# マイグレーションオブジェクト
migrate = Migrate()

# JWTマネージャー ★ 追加
jwt = JWTManager()

# 🚨 他の拡張機能（CORSなど）もここに追加
# from flask_cors import CORS
# cors = CORS()