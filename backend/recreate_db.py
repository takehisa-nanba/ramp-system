# backend/recreate_db.py
import os
import sys

# Add root folder to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import create_app
from backend.app.extensions import db

app = create_app()
with app.app_context():
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    print(f"Recreating database: {db_uri}")
    
    # SQLite file cleanup if needed
    if db_uri.startswith('sqlite:///'):
        db_path = os.path.join(os.path.dirname(__file__), 'app.db')
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
                print("Removed existing app.db file")
            except Exception as e:
                print(f"Could not remove db file: {e}")
                
    # Drop all tables first for a clean recreate
    try:
        db.drop_all()
        print("Dropped all existing tables successfully")
    except Exception as e:
        print(f"Could not drop tables: {e}")
            
    db.create_all()
    print("Created all tables successfully via db.create_all()")

