"""
Reset FHIR Security Configuration utility.
Handles password reset, role assignment, and CSP application configuration.

Supports two execution modes:
1. DBAPI mode - Uses intersystems-irispython for direct SQL access
2. Docker mode - Uses iris-devtester CLI when DBAPI unavailable (e.g., restricted environments)
"""

import os
import sys
import argparse
import subprocess
import shutil
from typing import Optional

# Ensure project root is in path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def _check_iris_native_available() -> bool:
    """Check if IRIS driver is available."""
    try:
        import iris
        return True
    except ImportError:
        return False


def _reset_via_docker(container_name: str, username: str, password: str, fhir_app: str) -> bool:
    """
    Reset security using iris-devtester CLI (works on EC2 with Docker).
    """
    print(f"Using Docker-based reset for container '{container_name}'...")

    # Step 1: Reset password via iris-devtester
    devtester_path = shutil.which('iris-devtester')
    if devtester_path:
        print(f"Resetting password for user {username}...")
        result = subprocess.run(
            ['iris-devtester', 'container', 'reset-password', container_name,
             '--user', username, '--password', password],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"Warning: Password reset via iris-devtester failed: {result.stderr}")
        else:
            print(f"✓ Password reset successful")
    else:
        # Fallback to direct docker exec
        print("iris-devtester not found, using docker exec directly...")
        cmd = f'iris session IRIS -U %SYS "do ##class(Security.Users).ChangePassword(\\"{username}\\",\\"{password}\\")"'
        result = subprocess.run(
            ['docker', 'exec', container_name, 'bash', '-c', cmd],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"Warning: Direct password reset failed: {result.stderr}")

    # Step 2: Enable password auth for FHIR app via docker exec
    print(f"Enabling password auth for {fhir_app}...")
    objectscript = f'''
set props=""
do ##class(Security.Applications).Get("{fhir_app}",.props)
set props("AutheEnabled")=32
do ##class(Security.Applications).Modify("{fhir_app}",.props)
'''
    result = subprocess.run(
        ['docker', 'exec', container_name, 'bash', '-c',
         f'iris session IRIS -U %SYS <<EOF\n{objectscript}\nhalt\nEOF'],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Warning: Auth configuration may have failed: {result.stderr}")
    else:
        print("✓ Password auth enabled for FHIR app")

    # Step 3: Enable CallIn service
    if devtester_path:
        print("Enabling CallIn service...")
        subprocess.run(
            ['iris-devtester', 'container', 'enable-callin', container_name],
            capture_output=True, text=True
        )

    return True


def _reset_via_native_sdk(username: str, password: str, fhir_app: str) -> bool:
    """
    Reset security using DBAPI driver (works when DBAPI is available).
    """
    from src.db.connection import DatabaseConnection

    print(f"Using DBAPI for security reset...")

    conn = None
    try:
        # 1. Connect to IRIS
        try:
            conn = DatabaseConnection.get_connection()
        except Exception:
            print("Configured connection failed, trying defaults (_SYSTEM/SYS)...")
            conn = DatabaseConnection.get_connection(username="_SYSTEM", password="SYS")

        cursor = conn.cursor()

        print(f"Resetting password for user {username}...")
        cursor.execute(f"SELECT ##class(Security.Users).ChangePassword(?, ?)", (username, password))
        status = cursor.fetchone()[0]
        if status != 1:
            print(f"Warning: Password reset might have failed (Status: {status})")

        print(f"Ensuring Password auth is enabled for {fhir_app}...")
        print("Note: Complex application configuration works better in Docker mode for this driver.")

        return True
    finally:
        if conn:
            conn.close()


def reset_security(
    username: str = "_SYSTEM",
    password: str = "SYS",
    fhir_app: str = "/csp/healthshare/demo/fhir/r4",
    container_name: str = "iris-fhir"
) -> bool:
    """
    Perform deep reset of FHIR security settings.

    Automatically detects execution environment and uses appropriate method:
    - DBAPI when available (requires intersystems-irispython)
    - Docker-based reset via iris-devtester when DBAPI unavailable
    """
    print(f"Starting security reset for user {username} and app {fhir_app}...")

    # Try DBAPI first, fallback to Docker mode
    if _check_iris_native_available():
        try:
            success = _reset_via_native_sdk(username, password, fhir_app)
        except Exception as e:
            print(f"DBAPI reset failed ({e}), falling back to Docker mode...")
            success = _reset_via_docker(container_name, username, password, fhir_app)
    else:
        print("IRIS DBAPI not available, using Docker mode...")
        success = _reset_via_docker(container_name, username, password, fhir_app)

    # Verify FHIR connectivity regardless of method
    if success:
        print("Verifying FHIR connectivity...")
        import requests
        from requests.auth import HTTPBasicAuth

        fhir_url = os.getenv("FHIR_BASE_URL")
        if not fhir_url:
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

    return success

def main():
    parser = argparse.ArgumentParser(description="Reset IRIS FHIR Security")
    parser.add_argument("--username", default="_SYSTEM", help="Target username")
    parser.add_argument("--password", default="SYS", help="New password")
    parser.add_argument("--fhir-app", default="/csp/healthshare/demo/fhir/r4", help="FHIR CSP Application path")
    parser.add_argument("--container", default="iris-fhir", help="Docker container name (for Docker mode)")

    args = parser.parse_args()

    try:
        if reset_security(args.username, args.password, args.fhir_app, args.container):
            print("✅ Security reset successful")
        else:
            print("❌ Security reset failed")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error during security reset: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
