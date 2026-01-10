"""
Reset FHIR Security Configuration utility.
Handles password reset, role assignment, and CSP application configuration.
"""

import os
import sys
import argparse
import json
import base64
from typing import Optional, Dict, Any

# Ensure project root is in path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.db.connection import DatabaseConnection

def reset_security(username: str = "_SYSTEM", password: str = "SYS", fhir_app: str = "/csp/healthshare/demo/fhir/r4"):
    """
    Perform deep reset of FHIR security settings.
    """
    import iris
    print(f"Starting security reset for user {username} and app {fhir_app}...")
    
    conn = None
    try:
        # 1. Connect to IRIS
        # Try configured credentials first
        try:
            conn = DatabaseConnection.get_connection()
        except Exception:
            # Fallback to default superuser if config fails
            print("Configured connection failed, trying defaults (_SYSTEM/SYS)...")
            conn = DatabaseConnection.get_connection(username="_SYSTEM", password="SYS")
            
        db_native = iris.createIRIS(conn)
        
        # 2. Switch to %SYS namespace for administrative tasks
        print("Switching to %SYS namespace...")
        db_native.classMethodValue("%SYS.Process", "SetNamespace", "%SYS")
        
        # 3. Reset User Password (FR-001)
        print(f"Resetting password for user {username}...")
        status = db_native.classMethodValue("Security.Users", "ChangePassword", username, password)
        if status != 1:
            print(f"Warning: Password reset might have failed (Status: {status})")
            
        # 4. Configure CSP Application (FR-002)
        print(f"Ensuring Password auth is enabled for {fhir_app}...")
        props_ref = iris.IRISReference({})
        db_native.classMethodValue("Security.Applications", "Get", fhir_app, props_ref)
        
        # Enable Password (32) and ensure application is enabled
        authen = int(props_ref.value.get("AuthenEnabled", 0))
        props_ref.value["AuthenEnabled"] = authen | 32
        props_ref.value["Enabled"] = 1
        
        status = db_native.classMethodValue("Security.Applications", "Modify", fhir_app, props_ref)
        if status != 1:
            print(f"Warning: Application modification failed (Status: {status})")

        # 5. Assign Roles (FR-003)
        print(f"Assigning FHIR roles to {username}...")
        props_ref = iris.IRISReference({})
        db_native.classMethodValue("Security.Users", "Get", username, props_ref)
        
        roles = props_ref.value.get("Roles", "")
        required_roles = ["%DB_FHIR", "%HS_FHIR_USER", "%Manager"]
        for role in required_roles:
            if role not in roles:
                roles = f"{roles},{role}" if roles else role
        
        props_ref.value["Roles"] = roles
        status = db_native.classMethodValue("Security.Users", "Modify", username, props_ref)
        if status != 1:
            print(f"Warning: Role assignment failed (Status: {status})")

        # 6. Verify Reset (FR-005)
        print("Verifying FHIR connectivity...")
        import requests
        from requests.auth import HTTPBasicAuth
        
        # Get FHIR URL from environment or construct from app path
        fhir_url = os.getenv("FHIR_BASE_URL")
        if not fhir_url:
            # Fallback to standard mapping
            port = os.getenv("IRIS_PORT_WEB", "32783")
            fhir_url = f"http://localhost:{port}{fhir_app}"
            
        try:
            print(f"Checking {fhir_url}/metadata...")
            response = requests.get(
                f"{fhir_url}/metadata", 
                auth=HTTPBasicAuth(username, password),
                timeout=10
            )
            if response.status_code == 200:
                print("✅ FHIR connectivity verified!")
            else:
                print(f"⚠️ FHIR check returned status {response.status_code}")
        except Exception as e:
            print(f"⚠️ FHIR connectivity check failed: {e}")

        return True
    finally:
        if conn:
            conn.close()

def main():
    parser = argparse.ArgumentParser(description="Reset IRIS FHIR Security")
    parser.add_argument("--username", default="_SYSTEM", help="Target username")
    parser.add_argument("--password", default="SYS", help="New password")
    parser.add_argument("--fhir-app", default="/csp/healthshare/demo/fhir/r4", help="FHIR CSP Application path")
    
    args = parser.parse_args()
    
    try:
        if reset_security(args.username, args.password, args.fhir_app):
            print("✅ Security reset successful")
        else:
            print("❌ Security reset failed")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error during security reset: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
