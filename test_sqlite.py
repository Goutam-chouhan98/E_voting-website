import os
import sys
import traceback
from app import app, init_db

def test_login():
    print("1. Initializing DB...")
    init_db()
    print("DB initialized successfully.")
    
    app.testing = True
    client = app.test_client()
    
    print("\n2. Testing voter login with valid credentials (MP001/pass123)...")
    try:
        response = client.post('/voter/login', data={'voter_id': 'MP001', 'password': 'pass123'})
        print(f"Response status: {response.status_code}")
        if response.status_code == 302:
            print("SUCCESS: Received a redirect (HTTP 302), which means the login was successful and no lock occurred!")
        elif response.status_code == 200:
            print("Received HTTP 200. This could mean invalid credentials or login page reload.")
        else:
            print(f"Received unexpected status: {response.status_code}")
    except Exception as e:
        print("\nERROR occurred during POST request:")
        traceback.print_exc()

if __name__ == "__main__":
    test_login()
