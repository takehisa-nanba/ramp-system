import os
from sqlalchemy import inspect
from backend.config import Config
from backend.app import create_app, db

app = create_app(Config)
with app.app_context():
    try:
        tables = inspect(db.engine).get_table_names()
    except Exception as e:
        tables = [str(e)]
    print(tables)
