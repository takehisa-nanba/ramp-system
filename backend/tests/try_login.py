import os
import sys

sys.path.append(r'c:\Users\難波\Desktop\ramp-system')

from backend.app import create_app
from backend.app.models import Supporter, SupporterPII
from backend.app.services.core_service import authenticate_supporter

app = create_app()
with app.app_context():
    email = "admin@example.com"
    password = "password"
    
    print("--- Directly Querying DB ---")
    pii = SupporterPII.query.filter_by(email=email).first()
    if pii:
        print("SupporterPII found in DB!")
        print("supporter_id:", pii.supporter_id)
        print("password_hash:", pii.password_hash)
        
        # Test password check
        match = pii.check_password(password)
        print(f"Password '{password}' check match:", match)
        
        # Test relation
        supporter = pii.supporter
        if supporter:
            print("Supporter name:", supporter.last_name, supporter.first_name)
        else:
            print("No linked supporter found!")
    else:
        print("SupporterPII NOT found in DB!")
        
    print("\n--- Trying authenticate_supporter ---")
    supporter = authenticate_supporter(email, password)
    print("Result:", supporter)
