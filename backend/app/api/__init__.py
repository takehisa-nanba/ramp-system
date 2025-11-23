# backend/app/api/__init__.py

# 責務: このパッケージ内の全てのブループリントをインポートし、一括でエクスポートする。
# これにより、app/__init__.py でのインポートを簡潔にする。

from .auth import auth_bp
# from .users import users_bp  # 将来のユーザーAPI
# from .plans import plans_bp  # 将来の計画API
# ...

# すべてのブループリントをリストに集約し、外部に公開する。
ALL_BLUEPRINTS = [
    auth_bp,
    # users_bp,
    # plans_bp,
]