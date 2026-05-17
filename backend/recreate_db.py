# backend/recreate_db.py
import os
import sys

# Add root folder to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import create_app
from backend.app.extensions import db

app = create_app()
with app.app_context():
    db_path = os.path.join(os.path.dirname(__file__), 'app.db')
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            print("Removed existing app.db")
        except Exception as e:
            print(f"Could not remove db file: {e}")
            
    db.create_all()
    print("Created all tables successfully via db.create_all()")
