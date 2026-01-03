"""
Integration tests for the CLI health check command.
Verifies that the CLI correctly handles and formats health check results.
"""

import pytest
import subprocess
import json
import os

def test_cli_help():
    """Verify CLI help command."""
    result = subprocess.run(
        ["python3", "-m", "src.cli", "--help"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "check-health" in result.stdout

def test_cli_check_health_output_format():
    """
    Verify CLI check-health output is valid JSON.
    Note: This will likely fail or return 'fail' status if IRIS is not reachable,
    but it should still return valid JSON.
    """
    # We'll use a mocked environment or just check if it's valid JSON
    result = subprocess.run(
        ["python3", "-m", "src.cli", "check-health"],
        capture_output=True,
        text=True
    )
    
    # Even if it fails, it should output JSON
    try:
        data = json.loads(result.stdout)
        assert "status" in data
        assert "checks" in data
        assert isinstance(data["checks"], list)
    except json.JSONDecodeError:
        pytest.fail(f"CLI output is not valid JSON: {result.stdout}\nError: {result.stderr}")

def test_cli_smoke_test_flag():
    """Verify smoke-test flag is accepted."""
    # We won't actually run it if it takes too long, but check if flag is parsed
    # Use -h on subparser to see if flag exists
    result = subprocess.run(
        ["python3", "-m", "src.cli", "check-health", "-h"],
        capture_output=True,
        text=True
    )
    assert "--smoke-test" in result.stdout
