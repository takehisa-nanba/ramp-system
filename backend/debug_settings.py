import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app import create_app
from backend.app.models import UserDailyLogSetting, OfficeSetting

app = create_app()
with app.app_context():
    office = OfficeSetting.query.first()
    if office:
        setting = UserDailyLogSetting.query.filter_by(office_id=office.id).first()
        if setting:
            print(f"DEBUG: Office ID {office.id} has settings: {json.dumps(setting.config, indent=2)}")
        else:
            print(f"DEBUG: Office ID {office.id} has NO settings.")
    else:
        print("DEBUG: No office found.")
