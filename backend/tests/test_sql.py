import os
import sys

sys.path.append(r'c:\Users\難波\Desktop\ramp-system')

from backend.app import create_app
from backend.app.models import Supporter

app = create_app()
with app.app_context():
    query = Supporter.query.filter_by(office_id=1)
    print("Generated SQL Query:")
    print(query)
