"""
Health check functions for AWS GPU NIM RAG system validation.

Provides structured health checks for all system components:
- GPU availability and utilization
- Docker GPU runtime
- IRIS database connectivity and schema
- NIM LLM service health and inference

All functions return structured results with pass/fail status
and diagnostic messages for troubleshooting.
"""

import subprocess
import json
import urllib.request
import urllib.error
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class HealthCheckResult:
    """Structured result from a health check.

    Attributes:
        component: Component name being checked
        status: 'pass' or 'fail'
        message: Human-readable status message
        details: Optional additional diagnostic information
    """
    component: str
    status: str  # 'pass' or 'fail'
    message: str
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return asdict(self)


def gpu_check() -> HealthCheckResult:
    """
    Check GPU availability and basic functionality.

    Verifies:
    - nvidia-smi command is available
    - GPU device is detected
    - Driver and CUDA versions

    Returns:
        HealthCheckResult with GPU information or error details
    """
    try:
        # Check if nvidia-smi exists
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=name,driver_version,memory.total', '--format=csv,noheader'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            return HealthCheckResult(
                component="GPU",
                status="fail",
                message="GPU not accessible",
                details={"error": result.stderr}
            )

        # Parse GPU information
        gpu_info = result.stdout.strip().split(', ')

        if len(gpu_info) < 3:
            return HealthCheckResult(
                component="GPU",
                status="fail",
                message="Could not parse GPU information",
                details={"output": result.stdout}
            )

        gpu_name = gpu_info[0]
        driver_version = gpu_info[1]
        memory_mb = gpu_info[2].split()[0]

        # Get CUDA version
        cuda_result = subprocess.run(
            ['nvidia-smi'],
            capture_output=True,
            text=True,
            timeout=10
        )

        cuda_version = "Unknown"
        for line in cuda_result.stdout.split('\n'):
            if "CUDA Version" in line:
                parts = line.split("CUDA Version:")
                if len(parts) > 1:
                    cuda_version = parts[1].strip().split()[0]
                break

        return HealthCheckResult(
            component="GPU",
            status="pass",
            message=f"GPU detected: {gpu_name}",
            details={
                "gpu_name": gpu_name,
                "driver_version": driver_version,
                "memory_mb": memory_mb,
                "cuda_version": cuda_version
            }
        )

    except FileNotFoundError:
        return HealthCheckResult(
            component="GPU",
            status="fail",
            message="nvidia-smi not found - GPU drivers may not be installed",
            details={"suggestion": "Run: ./scripts/aws/install-gpu-drivers.sh"}
        )
    except subprocess.TimeoutExpired:
        return HealthCheckResult(
            component="GPU",
            status="fail",
            message="nvidia-smi command timed out",
            details={}
        )
    except Exception as e:
        return HealthCheckResult(
            component="GPU",
            status="fail",
            message=f"Unexpected error checking GPU: {str(e)}",
            details={"error_type": type(e).__name__}
        )


def gpu_utilization_check() -> HealthCheckResult:
    """
    Check GPU utilization and memory usage.

    Provides real-time GPU metrics useful for monitoring workloads.

    Returns:
        HealthCheckResult with utilization metrics
    """
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu',
             '--format=csv,noheader,nounits'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            return HealthCheckResult(
                component="GPU Utilization",
                status="fail",
                message="Could not query GPU utilization",
                details={"error": result.stderr}
            )

        # Parse utilization info
        util_info = result.stdout.strip().split(', ')

        if len(util_info) < 4:
            return HealthCheckResult(
                component="GPU Utilization",
                status="fail",
                message="Could not parse GPU utilization",
                details={"output": result.stdout}
            )

        gpu_util_pct = float(util_info[0])
        memory_used_mb = float(util_info[1])
        memory_total_mb = float(util_info[2])
        temperature_c = float(util_info[3])

        memory_util_pct = (memory_used_mb / memory_total_mb) * 100 if memory_total_mb > 0 else 0

        return HealthCheckResult(
            component="GPU Utilization",
            status="pass",
            message=f"GPU utilization: {gpu_util_pct}%",
            details={
                "gpu_utilization_pct": gpu_util_pct,
                "memory_used_mb": memory_used_mb,
                "memory_total_mb": memory_total_mb,
                "memory_utilization_pct": round(memory_util_pct, 1),
                "temperature_c": temperature_c
            }
        )

    except Exception as e:
        return HealthCheckResult(
            component="GPU Utilization",
            status="fail",
            message=f"Error checking GPU utilization: {str(e)}",
            details={"error_type": type(e).__name__}
        )


def docker_gpu_check() -> HealthCheckResult:
    """
    Check Docker GPU runtime configuration.

    Verifies:
    - Docker is installed
    - Docker can access GPU via --gpus flag
    - GPU is accessible inside containers

    Returns:
        HealthCheckResult with Docker GPU status
    """
    try:
        # Test GPU access in container
        result = subprocess.run(
            ['docker', 'run', '--rm', '--gpus', 'all',
             'nvidia/cuda:12.2.0-base-ubuntu22.04', 'nvidia-smi'],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            return HealthCheckResult(
                component="Docker GPU Runtime",
                status="fail",
                message="Docker cannot access GPU",
                details={
                    "error": result.stderr,
                    "suggestion": "Run: ./scripts/aws/setup-docker-gpu.sh"
                }
            )

        return HealthCheckResult(
            component="Docker GPU Runtime",
            status="pass",
            message="Docker can access GPU",
            details={}
        )

    except FileNotFoundError:
        return HealthCheckResult(
            component="Docker GPU Runtime",
            status="fail",
            message="Docker not found",
            details={"suggestion": "Install Docker first"}
        )
    except subprocess.TimeoutExpired:
        return HealthCheckResult(
            component="Docker GPU Runtime",
            status="fail",
            message="Docker GPU test timed out",
            details={}
        )
    except Exception as e:
        return HealthCheckResult(
            component="Docker GPU Runtime",
            status="fail",
            message=f"Error checking Docker GPU: {str(e)}",
            details={"error_type": type(e).__name__}
        )


from src.db.connection import DatabaseConnection

def iris_connection_check(host: Optional[str] = None, port: Optional[int] = None,
                          namespace: Optional[str] = None, username: Optional[str] = None,
                          password: Optional[str] = None) -> HealthCheckResult:
    """
    Check IRIS database connectivity.

    Args:
        host: IRIS host address (default: env)
        port: IRIS SuperServer port (default: env)
        namespace: IRIS namespace (default: env)
        username: Database username (default: env)
        password: Database password (default: env)

    Returns:
        HealthCheckResult with connection status
    """
    # Resolve defaults for reporting
    db_config = DatabaseConnection.get_config()
    report_host = host or db_config['hostname']
    report_port = port or db_config['port']
    report_ns = namespace or db_config['namespace']

    try:
        # Attempt connection using centralized logic
        # get_connection handles None arguments by falling back to env/defaults
        conn = DatabaseConnection.get_connection(
            hostname=host, port=port, namespace=namespace,
            username=username, password=password
        )
        cursor = conn.cursor()

        # Test with simple query
        cursor.execute("SELECT 1")
        result = cursor.fetchone()

        conn.close()

        if result and result[0] == 1:
            return HealthCheckResult(
                component="IRIS Connection",
                status="pass",
                message=f"Connected to IRIS at {host}:{port}/{namespace}",
                details={
                    "host": host,
                    "port": port,
                    "namespace": namespace
                }
            )
        else:
            return HealthCheckResult(
                component="IRIS Connection",
                status="fail",
                message="Query test failed",
                details={"result": str(result)}
            )

    except ImportError:
        return HealthCheckResult(
            component="IRIS Connection",
            status="fail",
            message="iris Python module not installed",
            details={"suggestion": "pip install intersystems-irispython"}
        )
    except Exception as e:
        return HealthCheckResult(
            component="IRIS Connection",
            status="fail",
            message=f"Connection failed: {str(e)}",
            details={
                "error_type": type(e).__name__,
                "host": host,
                "port": port,
                "suggestion": "Check IRIS container is running: docker ps | grep iris"
            }
        )


def iris_tables_check(host: str = "localhost", port: int = 1972,
                      namespace: str = "DEMO", username: str = "_SYSTEM",
                      password: str = "SYS") -> HealthCheckResult:
    """
    Check IRIS vector table schema.

    Verifies:
    - ClinicalNoteVectors table exists
    - MedicalImageVectors table exists

    Args:
        host: IRIS host address
        port: IRIS SuperServer port
        namespace: IRIS namespace
        username: Database username
        password: Database password

    Returns:
        HealthCheckResult with table existence status
    """
    try:
        # Use centralized connection logic
        conn = DatabaseConnection.get_connection(
            hostname=host, port=port, namespace=namespace,
            username=username, password=password
        )
        cursor = conn.cursor()

        # Check ClinicalNoteVectors table
        cursor.execute("""
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA=? AND TABLE_NAME='ClinicalNoteVectors'
        """, (namespace,))
        clinical_exists = cursor.fetchone()[0] > 0

        # Check MedicalImageVectors table
        cursor.execute("""
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA=? AND TABLE_NAME='MedicalImageVectors'
        """, (namespace,))
        image_exists = cursor.fetchone()[0] > 0

        conn.close()

        tables_found = []
        tables_missing = []

        if clinical_exists:
            tables_found.append("ClinicalNoteVectors")
        else:
            tables_missing.append("ClinicalNoteVectors")

        if image_exists:
            tables_found.append("MedicalImageVectors")
        else:
            tables_missing.append("MedicalImageVectors")

        if len(tables_found) == 2:
            return HealthCheckResult(
                component="IRIS Tables",
                status="pass",
                message="All vector tables exist",
                details={
                    "tables_found": tables_found,
                    "namespace": namespace
                }
            )
        elif len(tables_found) > 0:
            return HealthCheckResult(
                component="IRIS Tables",
                status="fail",
                message="Some vector tables missing",
                details={
                    "tables_found": tables_found,
                    "tables_missing": tables_missing,
                    "suggestion": "Run schema creation scripts"
                }
            )
        else:
            return HealthCheckResult(
                component="IRIS Tables",
                status="fail",
                message="No vector tables found",
                details={
                    "tables_missing": tables_missing,
                    "suggestion": "Run: python src/setup/create_text_vector_table.py"
                }
            )

    except ImportError:
        return HealthCheckResult(
            component="IRIS Tables",
            status="fail",
            message="iris Python module not installed",
            details={"suggestion": "pip install intersystems-iris"}
        )
    except Exception as e:
        return HealthCheckResult(
            component="IRIS Tables",
            status="fail",
            message=f"Table check failed: {str(e)}",
            details={"error_type": type(e).__name__}
        )


def nim_llm_health_check(host: str = "localhost", port: int = 8001) -> HealthCheckResult:
    """
    Check NIM LLM service health endpoint.

    Args:
        host: NIM service host
        port: NIM service port

    Returns:
        HealthCheckResult with service health status
    """
    try:
        url = f"http://{host}:{port}/health"

        req = urllib.request.Request(url)

        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                return HealthCheckResult(
                    component="NIM LLM Health",
                    status="pass",
                    message=f"NIM LLM service healthy at {host}:{port}",
                    details={"endpoint": url}
                )
            else:
                return HealthCheckResult(
                    component="NIM LLM Health",
                    status="fail",
                    message=f"Health endpoint returned status {response.status}",
                    details={"status_code": response.status}
                )

    except urllib.error.URLError as e:
        return HealthCheckResult(
            component="NIM LLM Health",
            status="fail",
            message="Health endpoint not accessible",
            details={
                "error": str(e),
                "endpoint": f"http://{host}:{port}/health",
                "suggestion": "NIM may still be initializing - check: docker logs nim-llm"
            }
        )
    except Exception as e:
        return HealthCheckResult(
            component="NIM LLM Health",
            status="fail",
            message=f"Error checking health: {str(e)}",
            details={"error_type": type(e).__name__}
        )


def nim_llm_inference_test(host: str = "localhost", port: int = 8001) -> HealthCheckResult:
    """
    Test NIM LLM inference with a simple query.

    Args:
        host: NIM service host
        port: NIM service port

    Returns:
        HealthCheckResult with inference test status and response
    """
    url = f"http://{host}:{port}/v1/chat/completions"
    try:
        payload = {
            "model": "meta/llama-3.1-8b-instruct",
            "messages": [
                {"role": "user", "content": "What is 2+2? Answer with just the number."}
            ],
            "max_tokens": 10
        }

        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=data,
            headers={'Content-Type': 'application/json'}
        )

        with urllib.request.urlopen(req, timeout=30) as response:
            if response.status == 200:
                response_data = json.loads(response.read().decode('utf-8'))

                if 'choices' in response_data and len(response_data['choices']) > 0:
                    answer = response_data['choices'][0]['message']['content']

                    return HealthCheckResult(
                        component="NIM LLM Inference",
                        status="pass",
                        message="Inference test successful",
                        details={
                            "test_query": "What is 2+2?",
                            "response": answer.strip(),
                            "endpoint": url
                        }
                    )
                else:
                    return HealthCheckResult(
                        component="NIM LLM Inference",
                        status="fail",
                        message="Response missing expected fields",
                        details={"response": response_data}
                    )
            else:
                return HealthCheckResult(
                    component="NIM LLM Inference",
                    status="fail",
                    message=f"Inference endpoint returned status {response.status}",
                    details={"status_code": response.status}
                )

    except urllib.error.URLError as e:
        return HealthCheckResult(
            component="NIM LLM Inference",
            status="fail",
            message="Inference endpoint not accessible",
            details={
                "error": str(e),
                "endpoint": url,
                "suggestion": "Model may still be loading - check: docker logs nim-llm"
            }
        )
    except json.JSONDecodeError as e:
        return HealthCheckResult(
            component="NIM LLM Inference",
            status="fail",
            message="Could not parse response JSON",
            details={"error": str(e)}
        )
    except Exception as e:
        return HealthCheckResult(
            component="NIM LLM Inference",
            status="fail",
            message=f"Inference test failed: {str(e)}",
            details={"error_type": type(e).__name__}
        )


def iris_schema_check(host: Optional[str] = None, port: Optional[int] = None,
                      namespace: Optional[str] = None, username: Optional[str] = None,
                      password: Optional[str] = None) -> HealthCheckResult:
    """
    Comprehensive check of IRIS database schema for all required tables.
    
    Verifies existence of:
    - SQLUser.FHIRDocuments
    - SQLUser.Entities
    - SQLUser.EntityRelationships
    - VectorSearch.MIMICCXRImages
    
    Returns:
        HealthCheckResult with schema validation status
    """
    try:
        # Use centralized connection logic
        conn = DatabaseConnection.get_connection(
            hostname=host, port=port, namespace=namespace,
            username=username, password=password
        )
        cursor = conn.cursor()
        
        required_tables = [
            ("SQLUser", "FHIRDocuments"),
            ("RAG", "Entities"),
            ("RAG", "EntityRelationships"),
            ("VectorSearch", "MIMICCXRImages")
        ]
        
        found = []
        missing = []
        
        for schema, table in required_tables:
            cursor.execute("""
                SELECT COUNT(*)
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA=? AND TABLE_NAME=?
            """, (schema, table))
            
            if cursor.fetchone()[0] > 0:
                found.append(f"{schema}.{table}")
            else:
                missing.append(f"{schema}.{table}")
                
        conn.close()
        
        if not missing:
            return HealthCheckResult(
                component="IRIS Schema",
                status="pass",
                message="All required tables exist",
                details={"tables": found}
            )
        else:
            return HealthCheckResult(
                component="IRIS Schema",
                status="fail",
                message=f"Missing tables: {', '.join(missing)}",
                details={
                    "found": found,
                    "missing": missing,
                    "suggestion": "Run setup scripts or recreate missing tables"
                }
            )
            
    except Exception as e:
        return HealthCheckResult(
            component="IRIS Schema",
            status="fail",
            message=f"Schema check failed: {str(e)}"
        )

def fhir_auth_check(url: Optional[str] = None, username: Optional[str] = None,
                    password: Optional[str] = None) -> HealthCheckResult:
    """
    Check FHIR server authentication and availability.
    
    Args:
        url: FHIR base URL
        username: Auth username
        password: Auth password
        
    Returns:
        HealthCheckResult with auth status
    """
    import os
    import base64
    import requests
    
    fhir_url = url or os.getenv("FHIR_BASE_URL", "http://localhost:32783/csp/healthshare/demo/fhir/r4")
    user = username or os.getenv("FHIR_USERNAME", "_SYSTEM")
    pw = password or os.getenv("FHIR_PASSWORD", "SYS")
    
    try:
        auth = base64.b64encode(f"{user}:{pw}".encode()).decode()
        headers = {
            "Accept": "application/fhir+json",
            "Authorization": f"Basic {auth}"
        }
        
        # Test with metadata endpoint
        response = requests.get(f"{fhir_url}/metadata", headers=headers, timeout=10)
        
        if response.status_code == 200:
            return HealthCheckResult(
                component="FHIR Auth",
                status="pass",
                message=f"Authenticated successfully with {fhir_url}",
                details={"status_code": 200}
            )
        elif response.status_code == 401:
            return HealthCheckResult(
                component="FHIR Auth",
                status="fail",
                message="401 Unauthorized - FHIR credentials invalid",
                details={
                    "status_code": 401,
                    "suggestion": "Run 'python -m src.cli reset-security' to fix IRIS security configuration."
                }
            )
        else:
            return HealthCheckResult(
                component="FHIR Auth",
                status="fail",
                message=f"Unexpected status code {response.status_code}",
                details={"status_code": response.status_code}
            )
            
    except Exception as e:
        return HealthCheckResult(
            component="FHIR Auth",
            status="fail",
            message=f"FHIR connectivity check failed: {str(e)}",
            details={"error_type": type(e).__name__}
        )

def run_all_checks(iris_host: Optional[str] = None, iris_port: Optional[int] = None,
                  nim_host: str = "localhost", nim_port: int = 8001,
                  skip_gpu: bool = False, skip_docker: bool = False,
                  skip_iris: bool = False, skip_nim: bool = False) -> List[HealthCheckResult]:
    """
    Run all health checks and return results.

    Args:
        iris_host: IRIS database host (default: env or localhost)
        iris_port: IRIS database port (default: env or 1972)
        nim_host: NIM service host
        nim_port: NIM service port
        skip_gpu: Skip GPU checks
        skip_docker: Skip Docker checks
        skip_iris: Skip IRIS checks
        skip_nim: Skip NIM checks

    Returns:
        List of HealthCheckResult objects
    """
    # Load defaults from DatabaseConnection if not provided
    db_config = DatabaseConnection.get_config()
    if iris_host is None:
        iris_host = db_config['hostname']
    if iris_port is None:
        iris_port = db_config['port']

    results = []

    if not skip_gpu:
        results.append(gpu_check())
        results.append(gpu_utilization_check())

    if not skip_docker:
        results.append(docker_gpu_check())

    if not skip_iris:
        results.append(iris_connection_check(iris_host, iris_port))
        results.append(iris_schema_check(iris_host, iris_port))
        results.append(fhir_auth_check())

    if not skip_nim:
        results.append(nim_llm_health_check(nim_host, nim_port))
        results.append(nim_llm_inference_test(nim_host, nim_port))

    return results


if __name__ == "__main__":
    """Run all health checks when executed as script."""
    print("Running health checks...")
    print()

    results = run_all_checks()

    passed = sum(1 for r in results if r.status == "pass")
    failed = sum(1 for r in results if r.status == "fail")

    for result in results:
        status_symbol = "✓" if result.status == "pass" else "✗"
        print(f"{status_symbol} {result.component}: {result.message}")

        if result.details and result.status == "fail":
            if "suggestion" in result.details:
                print(f"   Suggestion: {result.details['suggestion']}")
            if "error" in result.details:
                print(f"   Error: {result.details['error']}")
        print()

    print(f"Results: {passed} passed, {failed} failed")

    # Exit with error code if any check failed
    exit(0 if failed == 0 else 1)
