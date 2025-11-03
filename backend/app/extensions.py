# app/extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt 
from flask_jwt_extended import JWTManager # JWTManagerはここで初期化しない

db = SQLAlchemy()
migrate = Migrate()
bcrypt = Bcrypt()
# JWTManagerのインスタンスはcreate_app内で初期化します