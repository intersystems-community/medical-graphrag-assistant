#!/usr/bin/env bash
#
# AWS GPU NIM RAG System Validation
#
# Comprehensive validation script for deployed system.
# Validates GPU, Docker, IRIS database, and NIM services.
#
# Usage:
#   ./validate-deployment.sh [--remote <host>] [--ssh-key <path>]
#
# Options:
#   --remote <host>      Validate remote host via SSH
#   --ssh-key <path>     Path to SSH key for remote validation
#   --skip-<component>   Skip specific validation checks
#
# Environment Variables:
#   PUBLIC_IP           Remote host IP (alternative to --remote)
#   SSH_KEY_PATH        Path to SSH key (alternative to --ssh-key)
#   IRIS_HOST           IRIS host (default: localhost)
#   IRIS_PORT           IRIS port (default: 1972)
#   NIM_HOST            NIM LLM host (default: localhost)
#   NIM_PORT            NIM LLM port (default: 8001)

set -euo pipefail

# Colors
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly NC='\033[0m'

# Configuration
REMOTE_HOST="${PUBLIC_IP:-}"
SSH_KEY="${SSH_KEY_PATH:-}"
SKIP_GPU=false
SKIP_DOCKER=false
SKIP_IRIS=false
SKIP_NIM=false
IRIS_HOST="${IRIS_HOST:-localhost}"
IRIS_PORT="${IRIS_PORT:-1972}"
NIM_HOST="${NIM_HOST:-localhost}"
NIM_PORT="${NIM_PORT:-8001}"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --remote)
            REMOTE_HOST="$2"
            shift 2
            ;;
        --ssh-key)
            SSH_KEY="$2"
            shift 2
            ;;
        --skip-gpu)
            SKIP_GPU=true
            shift
            ;;
        --skip-docker)
            SKIP_DOCKER=true
            shift
            ;;
        --skip-iris)
            SKIP_IRIS=true
            shift
            ;;
        --skip-nim)
            SKIP_NIM=true
            shift
            ;;
        --help)
            grep '^#' "$0" | sed 's/^# \?//'
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}" >&2
            exit 1
            ;;
    esac
done

# Logging functions
log_header() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} $1"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

log_check() {
    echo -e "${BLUE}→${NC} Checking $1..."
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}!${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1" >&2
}

log_info() {
    echo -e "  $1"
}

# Validation functions for local execution
validate_gpu_local() {
    log_check "GPU availability"

    if ! command -v nvidia-smi &> /dev/null; then
        log_error "nvidia-smi not found"
        return 1
    fi

    if ! nvidia-smi &> /dev/null; then
        log_error "GPU not accessible"
        return 1
    fi

    # Get GPU info
    gpu_name=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -n1)
    gpu_memory=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -n1)
    driver_version=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -n1)
    cuda_version=$(nvidia-smi | grep "CUDA Version" | awk '{print $9}' || echo "Unknown")

    log_success "GPU detected: $gpu_name"
    log_info "Memory: ${gpu_memory} MB"
    log_info "Driver: $driver_version"
    log_info "CUDA: $cuda_version"

    return 0
}

validate_docker_gpu_local() {
    log_check "Docker GPU runtime"

    if ! command -v docker &> /dev/null; then
        log_error "Docker not installed"
        return 1
    fi

    # Test GPU access in container
    if docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi &> /dev/null; then
        log_success "Docker can access GPU"
        return 0
    else
        log_error "Docker cannot access GPU"
        log_info "Run: ./scripts/aws/setup-docker-gpu.sh"
        return 1
    fi
}

validate_iris_local() {
    log_check "IRIS database connectivity"

    # Check if iris container is running
    if ! docker ps | grep -q "iris-vector-db\|iris-fhir"; then
        log_error "IRIS container not running"
        log_info "Run: ./scripts/aws/deploy-iris.sh"
        return 1
    fi

    log_success "IRIS container running"

    # Test Python connection
    log_check "IRIS database connection (Python)"

    python3 << 'EOF'
import sys
try:
    import iris
    conn = iris.connect('localhost', 1972, 'DEMO', '_SYSTEM', 'SYS')
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    result = cursor.fetchone()
    conn.close()
    if result and result[0] == 1:
        print("✓ Python connection successful")
        sys.exit(0)
    else:
        print("✗ Query failed")
        sys.exit(1)
except Exception as e:
    print(f"✗ Connection failed: {e}")
    sys.exit(1)
EOF

    if [[ $? -eq 0 ]]; then
        log_success "IRIS database connection working"
    else
        log_error "IRIS database connection failed"
        return 1
    fi

    # Check for vector tables
    log_check "Vector tables existence"

    python3 << 'EOF'
import sys
try:
    import iris
    conn = iris.connect('localhost', 1972, 'DEMO', '_SYSTEM', 'SYS')
    cursor = conn.cursor()

    # Check ClinicalNoteVectors table
    cursor.execute("""
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA='DEMO' AND TABLE_NAME='ClinicalNoteVectors'
    """)
    clinical_exists = cursor.fetchone()[0] > 0

    # Check MedicalImageVectors table
    cursor.execute("""
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA='DEMO' AND TABLE_NAME='MedicalImageVectors'
    """)
    image_exists = cursor.fetchone()[0] > 0

    conn.close()

    if clinical_exists and image_exists:
        print("✓ Both vector tables exist")
        sys.exit(0)
    elif clinical_exists:
        print("! ClinicalNoteVectors exists, MedicalImageVectors missing")
        sys.exit(0)
    elif image_exists:
        print("! MedicalImageVectors exists, ClinicalNoteVectors missing")
        sys.exit(0)
    else:
        print("✗ No vector tables found")
        sys.exit(1)
except Exception as e:
    print(f"✗ Table check failed: {e}")
    sys.exit(1)
EOF

    if [[ $? -eq 0 ]]; then
        log_success "Vector tables validated"
    else
        log_error "Vector tables not found"
        log_info "Tables may need to be created"
        return 1
    fi

    return 0
}

validate_nim_llm_local() {
    log_check "NIM LLM service health"

    # Check if NIM container is running
    if ! docker ps | grep -q "nim-llm"; then
        log_error "NIM LLM container not running"
        log_info "Run: ./scripts/aws/deploy-nim-llm.sh"
        return 1
    fi

    log_success "NIM LLM container running"

    # Test health endpoint
    log_check "NIM LLM health endpoint"

    if curl -s -f "http://${NIM_HOST}:${NIM_PORT}/health" > /dev/null; then
        log_success "NIM LLM health endpoint responding"
    else
        log_warn "Health endpoint not available (may still be initializing)"
    fi

    # Test inference
    log_check "NIM LLM inference test"

    response=$(curl -s -X POST "http://${NIM_HOST}:${NIM_PORT}/v1/chat/completions" \
        -H "Content-Type: application/json" \
        -d '{
            "model": "meta/llama-3.1-8b-instruct",
            "messages": [{"role": "user", "content": "What is 2+2?"}],
            "max_tokens": 10
        }' 2>/dev/null || echo "")

    if [[ -n "$response" ]] && echo "$response" | grep -q "choices"; then
        log_success "NIM LLM inference working"
        # Extract and show response
        answer=$(echo "$response" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['choices'][0]['message']['content'] if 'choices' in data else 'No response')" 2>/dev/null || echo "")
        if [[ -n "$answer" ]]; then
            log_info "Test response: $answer"
        fi
    else
        log_warn "NIM LLM inference not responding (may still be loading model)"
        log_info "Check logs: docker logs nim-llm"
        return 1
    fi

    return 0
}

# Remote validation function
validate_remote() {
    local host="$1"
    local ssh_key="$2"

    log_info "Validating remote host: $host"

    if [[ -z "$ssh_key" ]]; then
        log_error "SSH key required for remote validation"
        return 1
    fi

    if [[ ! -f "$ssh_key" ]]; then
        log_error "SSH key not found: $ssh_key"
        return 1
    fi

    # Execute validation on remote host
    ssh -o StrictHostKeyChecking=no -i "$ssh_key" "ubuntu@${host}" << 'ENDSSH'
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}→${NC} Checking GPU..."
if nvidia-smi &> /dev/null; then
    gpu_name=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -n1)
    echo -e "${GREEN}✓${NC} GPU detected: $gpu_name"
else
    echo -e "${RED}✗${NC} GPU not accessible"
    exit 1
fi

echo ""
echo -e "${BLUE}→${NC} Checking Docker GPU runtime..."
if docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi &> /dev/null; then
    echo -e "${GREEN}✓${NC} Docker can access GPU"
else
    echo -e "${RED}✗${NC} Docker cannot access GPU"
    exit 1
fi

echo ""
echo -e "${BLUE}→${NC} Checking IRIS database..."
if docker ps | grep -q "iris-vector-db"; then
    echo -e "${GREEN}✓${NC} IRIS container running"
else
    echo -e "${RED}✗${NC} IRIS container not running"
    exit 1
fi

echo ""
echo -e "${BLUE}→${NC} Checking NIM LLM service..."
if docker ps | grep -q "nim-llm"; then
    echo -e "${GREEN}✓${NC} NIM LLM container running"

    # Test health endpoint
    if curl -s -f http://localhost:8001/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} NIM LLM health endpoint responding"
    else
        echo -e "${YELLOW}!${NC} Health endpoint not available (may be initializing)"
    fi
else
    echo -e "${RED}✗${NC} NIM LLM container not running"
    exit 1
fi

echo ""
echo -e "${GREEN}✓${NC} All checks passed"
ENDSSH

    return $?
}

# Main execution
main() {
    log_header "AWS GPU NIM RAG System Validation"

    local all_passed=true

    if [[ -n "$REMOTE_HOST" ]]; then
        # Remote validation
        if ! validate_remote "$REMOTE_HOST" "$SSH_KEY"; then
            all_passed=false
        fi
    else
        # Local validation
        if [[ "$SKIP_GPU" != "true" ]]; then
            if ! validate_gpu_local; then
                all_passed=false
            fi
            echo ""
        fi

        if [[ "$SKIP_DOCKER" != "true" ]]; then
            if ! validate_docker_gpu_local; then
                all_passed=false
            fi
            echo ""
        fi

        if [[ "$SKIP_IRIS" != "true" ]]; then
            if ! validate_iris_local; then
                all_passed=false
            fi
            echo ""
        fi

        if [[ "$SKIP_NIM" != "true" ]]; then
            if ! validate_nim_llm_local; then
                all_passed=false
            fi
            echo ""
        fi
    fi

    # Summary
    echo ""
    log_header "Validation Summary"

    if [[ "$all_passed" == "true" ]]; then
        echo -e "${GREEN}✓ All validation checks passed${NC}"
        echo ""
        echo "System is ready for use!"
        echo ""
        echo "Next steps:"
        echo "  1. Vectorize clinical notes: python src/vectorization/vectorize_documents.py"
        echo "  2. Test vector search: python src/query/test_vector_search.py"
        echo "  3. Run RAG query: python src/query/rag_query.py --query 'your question'"
        echo ""
        return 0
    else
        echo -e "${RED}✗ Some validation checks failed${NC}"
        echo ""
        echo "Please review the errors above and:"
        echo "  1. Check troubleshooting guide: docs/troubleshooting.md"
        echo "  2. Review deployment logs"
        echo "  3. Verify all services are running: docker ps"
        echo ""
        return 1
    fi
}

# Run main function
main
