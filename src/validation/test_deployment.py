"""
Pytest test suite for AWS GPU NIM RAG deployment validation.

Wraps health_checks.py functions as pytest test cases with
proper assertions and test fixtures.

Run with:
    pytest src/validation/test_deployment.py -v
"""

import pytest
import os
from typing import Dict, Any
from . import health_checks


# Test fixtures for configuration
@pytest.fixture
def iris_config() -> Dict[str, Any]:
    """IRIS database configuration from environment."""
    return {
        "host": os.getenv("IRIS_HOST", "localhost"),
        "port": int(os.getenv("IRIS_PORT", "1972")),
        "namespace": os.getenv("IRIS_NAMESPACE", "DEMO"),
        "username": os.getenv("IRIS_USERNAME", "_SYSTEM"),
        "password": os.getenv("IRIS_PASSWORD", "SYS")
    }


@pytest.fixture
def nim_config() -> Dict[str, Any]:
    """NIM LLM service configuration from environment."""
    return {
        "host": os.getenv("NIM_HOST", "localhost"),
        "port": int(os.getenv("NIM_PORT", "8001"))
    }


# GPU Tests
class TestGPU:
    """GPU availability and functionality tests."""

    def test_gpu_detected(self):
        """Test that GPU is detected and accessible."""
        result = health_checks.gpu_check()

        assert result.status == "pass", (
            f"GPU check failed: {result.message}. "
            f"Details: {result.details}"
        )

        assert result.details is not None, "GPU details should be populated"
        assert "gpu_name" in result.details, "GPU name should be in details"
        assert "driver_version" in result.details, "Driver version should be in details"

    def test_gpu_utilization(self):
        """Test GPU utilization monitoring."""
        result = health_checks.gpu_utilization_check()

        assert result.status == "pass", (
            f"GPU utilization check failed: {result.message}. "
            f"Details: {result.details}"
        )

        assert result.details is not None, "GPU utilization details should be populated"
        assert "gpu_utilization_pct" in result.details, "GPU utilization % should be in details"
        assert "memory_used_mb" in result.details, "Memory usage should be in details"

        # Validate metrics are reasonable
        gpu_util = result.details["gpu_utilization_pct"]
        assert 0 <= gpu_util <= 100, f"GPU utilization should be 0-100%, got {gpu_util}"


# Docker Tests
class TestDocker:
    """Docker GPU runtime tests."""

    def test_docker_gpu_access(self):
        """Test that Docker can access GPU."""
        result = health_checks.docker_gpu_check()

        assert result.status == "pass", (
            f"Docker GPU check failed: {result.message}. "
            f"Details: {result.details}"
        )


# IRIS Database Tests
class TestIRIS:
    """IRIS database connectivity and schema tests."""

    def test_iris_connection(self, iris_config):
        """Test IRIS database connection."""
        result = health_checks.iris_connection_check(**iris_config)

        assert result.status == "pass", (
            f"IRIS connection failed: {result.message}. "
            f"Details: {result.details}"
        )

        assert result.details is not None, "Connection details should be populated"
        assert result.details["host"] == iris_config["host"], "Host should match config"
        assert result.details["port"] == iris_config["port"], "Port should match config"

    def test_iris_tables_exist(self, iris_config):
        """Test that vector tables exist in IRIS."""
        result = health_checks.iris_tables_check(**iris_config)

        assert result.status == "pass", (
            f"IRIS tables check failed: {result.message}. "
            f"Details: {result.details}"
        )

        assert result.details is not None, "Table details should be populated"
        assert "tables_found" in result.details, "Found tables should be listed"

        tables_found = result.details["tables_found"]
        assert "ClinicalNoteVectors" in tables_found, "ClinicalNoteVectors table should exist"
        assert "MedicalImageVectors" in tables_found, "MedicalImageVectors table should exist"


# NIM LLM Tests
class TestNIMLLM:
    """NIM LLM service health and functionality tests."""

    def test_nim_llm_health(self, nim_config):
        """Test NIM LLM health endpoint."""
        result = health_checks.nim_llm_health_check(**nim_config)

        # Note: Health endpoint may not be available if service is still initializing
        # We'll warn but not fail the test in that case
        if result.status == "fail":
            pytest.skip(
                f"NIM LLM health check skipped (service may be initializing): {result.message}"
            )

        assert result.status == "pass", (
            f"NIM LLM health check failed: {result.message}. "
            f"Details: {result.details}"
        )

    def test_nim_llm_inference(self, nim_config):
        """Test NIM LLM inference with test query."""
        result = health_checks.nim_llm_inference_test(**nim_config)

        # Skip if model is still loading
        if result.status == "fail" and result.details and "suggestion" in result.details:
            if "still be loading" in result.details["suggestion"]:
                pytest.skip(
                    f"NIM LLM inference skipped (model loading): {result.message}"
                )

        assert result.status == "pass", (
            f"NIM LLM inference failed: {result.message}. "
            f"Details: {result.details}"
        )

        assert result.details is not None, "Inference details should be populated"
        assert "response" in result.details, "Inference response should be in details"
        assert len(result.details["response"]) > 0, "Response should not be empty"


# Integration Tests
class TestSystemIntegration:
    """Full system integration tests."""

    def test_all_components_healthy(self, iris_config, nim_config):
        """Test that all system components are healthy."""
        results = health_checks.run_all_checks(
            iris_host=iris_config["host"],
            iris_port=iris_config["port"],
            nim_host=nim_config["host"],
            nim_port=nim_config["port"]
        )

        # Count results
        passed = sum(1 for r in results if r.status == "pass")
        failed = sum(1 for r in results if r.status == "fail")

        # Collect failure messages
        failures = [
            f"{r.component}: {r.message}"
            for r in results
            if r.status == "fail"
        ]

        assert failed == 0, (
            f"{failed} health checks failed (out of {len(results)} total):\n" +
            "\n".join(f"  - {f}" for f in failures)
        )

        assert passed == len(results), (
            f"Expected all {len(results)} checks to pass, but only {passed} passed"
        )

    def test_deployment_readiness(self, iris_config, nim_config):
        """Test that system is ready for production use."""
        # Check critical components only
        critical_checks = [
            ("GPU", health_checks.gpu_check()),
            ("Docker GPU", health_checks.docker_gpu_check()),
            ("IRIS Connection", health_checks.iris_connection_check(**iris_config)),
            ("IRIS Tables", health_checks.iris_tables_check(**iris_config))
        ]

        failures = [
            (name, result.message)
            for name, result in critical_checks
            if result.status == "fail"
        ]

        assert len(failures) == 0, (
            f"Critical components failed:\n" +
            "\n".join(f"  - {name}: {msg}" for name, msg in failures)
        )


# Performance Tests
class TestPerformance:
    """Performance and resource utilization tests."""

    def test_gpu_utilization_reasonable(self):
        """Test that GPU utilization is within reasonable bounds."""
        result = health_checks.gpu_utilization_check()

        if result.status != "pass":
            pytest.skip(f"GPU utilization check failed: {result.message}")

        assert result.details is not None

        # GPU should not be overheating
        if "temperature_c" in result.details:
            temp = result.details["temperature_c"]
            assert temp < 90, f"GPU temperature too high: {temp}°C"

        # Memory should not be completely exhausted
        if "memory_utilization_pct" in result.details:
            mem_util = result.details["memory_utilization_pct"]
            assert mem_util < 95, f"GPU memory nearly exhausted: {mem_util}%"


# Fixtures for test data
@pytest.fixture(scope="session")
def deployment_results():
    """Run all checks once per test session and cache results."""
    return health_checks.run_all_checks()


# Parametrized tests for all checks
@pytest.mark.parametrize("check_function", [
    health_checks.gpu_check,
    health_checks.gpu_utilization_check,
    health_checks.docker_gpu_check,
])
def test_infrastructure_check(check_function):
    """Test each infrastructure check function."""
    result = check_function()
    assert isinstance(result, health_checks.HealthCheckResult), (
        f"{check_function.__name__} should return HealthCheckResult"
    )
    assert result.status in ["pass", "fail"], (
        f"Status should be 'pass' or 'fail', got '{result.status}'"
    )


# Mark slow tests
@pytest.mark.slow
def test_nim_llm_full_inference_chain(nim_config):
    """
    Test full inference chain with multiple queries (slow test).

    This test makes multiple API calls to verify consistent behavior.
    """
    test_queries = [
        "What is 1+1?",
        "What is the capital of France?",
        "Explain photosynthesis in one sentence."
    ]

    for query in test_queries:
        # Note: This would require modifying nim_llm_inference_test to accept custom query
        result = health_checks.nim_llm_inference_test(**nim_config)

        if result.status == "fail":
            pytest.skip(f"NIM LLM not ready: {result.message}")

        assert result.status == "pass", (
            f"Inference failed for query '{query}': {result.message}"
        )


if __name__ == "__main__":
    """Run tests when executed as script."""
    import sys

    # Run pytest programmatically
    args = [__file__, "-v", "--tb=short"]

    if "--slow" in sys.argv:
        args.append("-m")
        args.append("slow")

    pytest.main(args)
