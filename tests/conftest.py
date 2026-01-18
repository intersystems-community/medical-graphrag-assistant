"""
Pytest configuration - runs against LIVE EC2 IRIS. NO MOCKS.
See OPS.md for infrastructure details.
"""

import os
import pytest
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MCP_SERVER_DIR = os.path.join(PROJECT_ROOT, 'mcp-server')
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if MCP_SERVER_DIR not in sys.path:
    sys.path.insert(0, MCP_SERVER_DIR)

EC2_IP = "44.200.206.67"

IRIS_CONFIG = {
    "host": os.getenv("IRIS_HOST", EC2_IP),
    "port": int(os.getenv("IRIS_PORT", "1972")),
    "namespace": os.getenv("IRIS_NAMESPACE", "DEMO"),
    "username": os.getenv("IRIS_USERNAME", "_SYSTEM"),
    "password": os.getenv("IRIS_PASSWORD", "SYS"),
}

NVCLIP_CONFIG = {
    "base_url": os.getenv("NVCLIP_BASE_URL", f"http://{EC2_IP}:8002/v1"),
}

FHIR_CONFIG = {
    "base_url": os.getenv("FHIR_BASE_URL", f"http://{EC2_IP}:52773/csp/healthshare/demo/fhir/r4"),
}


def pytest_configure(config):
    os.environ.setdefault("IRIS_HOST", IRIS_CONFIG["host"])
    os.environ.setdefault("IRIS_PORT", str(IRIS_CONFIG["port"]))
    os.environ.setdefault("IRIS_NAMESPACE", IRIS_CONFIG["namespace"])
    os.environ.setdefault("IRIS_USERNAME", IRIS_CONFIG["username"])
    os.environ.setdefault("IRIS_PASSWORD", IRIS_CONFIG["password"])
    os.environ.setdefault("NVCLIP_BASE_URL", NVCLIP_CONFIG["base_url"])
    os.environ.setdefault("FHIR_BASE_URL", FHIR_CONFIG["base_url"])
    
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "contract: Contract tests")


@pytest.fixture(scope="session")
def iris_config():
    return IRIS_CONFIG


@pytest.fixture(scope="session")
def nvclip_config():
    return NVCLIP_CONFIG


@pytest.fixture(scope="session")
def iris_connection():
    try:
        from src.db.connection import DatabaseConnection
        
        conn = DatabaseConnection.get_connection(
            hostname=IRIS_CONFIG["host"],
            port=IRIS_CONFIG["port"],
            namespace=IRIS_CONFIG["namespace"],
            username=IRIS_CONFIG["username"],
            password=IRIS_CONFIG["password"],
        )
        yield conn
        conn.close()
    except Exception as e:
        pytest.skip(f"IRIS not available: {e}")


@pytest.fixture(scope="session")
def iris_cursor(iris_connection):
    cursor = iris_connection.cursor()
    yield cursor
    cursor.close()


def check_iris_available():
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((IRIS_CONFIG["host"], IRIS_CONFIG["port"]))
        sock.close()
        return result == 0
    except Exception:
        return False


@pytest.fixture(scope="session")
def require_iris():
    if not check_iris_available():
        pytest.skip(f"IRIS not available at {IRIS_CONFIG['host']}:{IRIS_CONFIG['port']}")
