#!/usr/bin/env bash
#
# NVIDIA NIM LLM Deployment
#
# Deploys NVIDIA NIM LLM container (Llama 3.1 8B Instruct) with GPU support.
# Requires GPU drivers and Docker GPU runtime to be configured.
#
# Usage:
#   ./deploy-nim-llm.sh [--remote <host>] [--ssh-key <path>]
#
# Options:
#   --remote <host>      Deploy on remote host via SSH
#   --ssh-key <path>     Path to SSH key for remote deployment
#   --force-recreate     Remove existing container and recreate
#   --skip-verification  Skip health check verification
#   --model <model>      NIM model to deploy (default: meta/llama-3.1-8b-instruct)
#
# Environment Variables:
#   PUBLIC_IP           Remote host IP (alternative to --remote)
#   SSH_KEY_PATH        Path to SSH key (alternative to --ssh-key)
#   NVIDIA_API_KEY      NVIDIA NGC API key (required)

set -euo pipefail

# Colors
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

# Configuration
REMOTE_HOST="${PUBLIC_IP:-}"
SSH_KEY="${SSH_KEY_PATH:-}"
FORCE_RECREATE=false
SKIP_VERIFICATION=false
NIM_MODEL="${NIM_MODEL:-meta/llama3-8b-instruct}"
CONTAINER_NAME="nim-llm"
NIM_PORT=8001
LOCAL_CONTAINER_PORT=8000

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
        --force-recreate)
            FORCE_RECREATE=true
            shift
            ;;
        --skip-verification)
            SKIP_VERIFICATION=true
            shift
            ;;
        --model)
            NIM_MODEL="$2"
            shift 2
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
log_info() {
    echo -e "${BLUE}→${NC} $1"
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

# Function to check for NVIDIA API key
check_api_key() {
    if [[ -z "${NVIDIA_API_KEY:-}" ]]; then
        log_error "NVIDIA_API_KEY environment variable is required"
        log_error "Set it in your .env file or export it before running this script"
        return 1
    fi
    log_success "NVIDIA API key found"
}

# Function to deploy NIM LLM locally
deploy_nim_llm_local() {
    log_info "Deploying NVIDIA NIM LLM..."
    log_info "Model: $NIM_MODEL"

    # Check for API key
    check_api_key || return 1

    # Check if container already exists
    if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        if [[ "$FORCE_RECREATE" == "true" ]]; then
            log_warn "Removing existing container..."
            docker stop "$CONTAINER_NAME" 2>/dev/null || true
            docker rm "$CONTAINER_NAME" 2>/dev/null || true
        else
            log_warn "Container $CONTAINER_NAME already exists"
            log_info "Use --force-recreate to remove and recreate"

            # Check if it's running
            if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
                log_success "Container is running"
                return 0
            else
                log_info "Starting existing container..."
                docker start "$CONTAINER_NAME"
                log_success "Container started"
                return 0
            fi
        fi
    fi

    # Verify GPU is available
    log_info "Verifying GPU availability..."
    if ! docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi &>/dev/null; then
        log_error "GPU not accessible in Docker containers"
        log_error "Run ./scripts/aws/setup-docker-gpu.sh first"
        return 1
    fi
    log_success "GPU is accessible"

    # Pull NIM LLM image
    log_info "Pulling NIM LLM image (this may take several minutes)..."
    local nim_image="nvcr.io/nim/${NIM_MODEL}:latest"

    if ! docker pull "$nim_image"; then
        log_error "Failed to pull NIM image: $nim_image"
        log_error "Verify NVIDIA_API_KEY is valid and has access to NIM"
        return 1
    fi
    log_success "Image pulled"

    # Run NIM LLM container
    log_info "Starting NIM LLM container..."
    log_info "This will download model weights on first run (5-10 minutes)..."

    docker run -d \
        --name "$CONTAINER_NAME" \
        --gpus all \
        --restart unless-stopped \
        -p ${NIM_PORT}:${LOCAL_CONTAINER_PORT} \
        -e NGC_API_KEY="$NVIDIA_API_KEY" \
        --shm-size=16g \
        "$nim_image"

    log_success "NIM LLM container started"

    # Wait for initialization
    log_info "Waiting for NIM to initialize (checking every 30s)..."
    local max_wait=600  # 10 minutes
    local elapsed=0
    local interval=30

    while [[ $elapsed -lt $max_wait ]]; do
        if docker ps | grep -q "$CONTAINER_NAME"; then
            # Check logs for ready signal
            if docker logs "$CONTAINER_NAME" 2>&1 | grep -q -i "ready\|listening\|started"; then
                log_success "NIM is initializing"
                break
            fi
        else
            log_error "Container stopped unexpectedly"
            docker logs "$CONTAINER_NAME" --tail 50
            return 1
        fi

        sleep $interval
        elapsed=$((elapsed + interval))
        log_info "Still initializing... ($elapsed/${max_wait}s)"
    done

    if [[ $elapsed -ge $max_wait ]]; then
        log_warn "Initialization taking longer than expected"
        log_warn "Check logs: docker logs $CONTAINER_NAME"
    fi

    log_success "NIM LLM deployed"
}

# Function to deploy on remote host
deploy_nim_llm_remote() {
    local host="$1"
    local ssh_key="$2"

    log_info "Deploying NIM LLM on remote host: $host"

    if [[ -z "$ssh_key" ]]; then
        log_error "SSH key required for remote deployment"
        return 1
    fi

    if [[ ! -f "$ssh_key" ]]; then
        log_error "SSH key not found: $ssh_key"
        return 1
    fi

    # Execute deployment on remote host
    ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i "$ssh_key" "ubuntu@${host}" << ENDSSH
set -e

# Load environment variables
if [ -f ~/fhir-ai-hackathon/.env ]; then
    source ~/fhir-ai-hackathon/.env
fi

CONTAINER_NAME="$CONTAINER_NAME"
NIM_MODEL="$NIM_MODEL"
FORCE_RECREATE="$FORCE_RECREATE"
NIM_PORT="$NIM_PORT"

echo "→ Deploying NVIDIA NIM LLM..."
echo "  Model: \$NIM_MODEL"

# Check for API key
if [[ -z "\${NVIDIA_API_KEY:-}" ]]; then
    echo "✗ NVIDIA_API_KEY not found in environment"
    exit 1
fi

echo "✓ NVIDIA API key found"

# Check if container exists
if docker ps -a --format '{{.Names}}' | grep -q "^\${CONTAINER_NAME}\$"; then
    if [[ "\$FORCE_RECREATE" == "true" ]]; then
        echo "! Removing existing container..."
        docker stop \$CONTAINER_NAME 2>/dev/null || true
        docker rm \$CONTAINER_NAME 2>/dev/null || true
    else
        echo "! Container already exists"
        if docker ps --format '{{.Names}}' | grep -q "^\${CONTAINER_NAME}\$"; then
            echo "✓ Container is running"
            exit 0
        else
            echo "→ Starting existing container..."
            docker start \$CONTAINER_NAME
            echo "✓ Container started"
            exit 0
        fi
    fi
fi

# Verify GPU
echo "→ Verifying GPU..."
if ! docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi &>/dev/null; then
    echo "✗ GPU not accessible in Docker"
    exit 1
fi
echo "✓ GPU accessible"

# Pull image
echo "→ Pulling NIM LLM image..."
nim_image="nvcr.io/nim/\${NIM_MODEL}:latest"

if ! docker pull "\$nim_image"; then
    echo "✗ Failed to pull NIM image"
    exit 1
fi
echo "✓ Image pulled"

# Run container
echo "→ Starting NIM LLM container..."
docker run -d \
    --name \$CONTAINER_NAME \
    --gpus all \
    --restart unless-stopped \
    -p \${NIM_PORT}:8000 \
    -e NGC_API_KEY="\$NVIDIA_API_KEY" \
    -e NIM_MODEL_PROFILE=auto \
    --shm-size=16g \
    "\$nim_image"

echo "✓ NIM LLM container started"

echo ""
echo "→ Waiting for initialization (30 seconds)..."
sleep 30

# Verify container is running
if docker ps | grep -q "\$CONTAINER_NAME"; then
    echo "✓ Container is running"
    echo ""
    docker ps | grep \$CONTAINER_NAME
else
    echo "✗ Container failed to start"
    docker logs \$CONTAINER_NAME --tail 50
    exit 1
fi

echo ""
echo "✓ NIM LLM deployment complete"
ENDSSH

    return $?
}

# Function to verify deployment
verify_deployment() {
    local host="${1:-localhost}"
    local is_remote="${2:-false}"

    if [[ "$SKIP_VERIFICATION" == "true" ]]; then
        log_info "Skipping verification (--skip-verification)"
        return 0
    fi

    log_info "Verifying NIM LLM deployment..."

    if [[ "$is_remote" == "true" ]]; then
        ssh -o StrictHostKeyChecking=no -i "$SSH_KEY" "ubuntu@${host}" << 'ENDSSH'
# Check container status
if docker ps | grep -q nim-llm; then
    echo "✓ Container is running"
    echo ""
    docker ps | grep nim-llm
    echo ""
    echo "API Endpoint:"
    echo "  http://$(curl -s ifconfig.me):8001/v1/chat/completions"
else
    echo "✗ Container is not running"
    exit 1
fi

# Check logs for errors
echo ""
echo "Recent logs:"
docker logs nim-llm --tail 10
ENDSSH
    else
        if docker ps | grep -q "$CONTAINER_NAME"; then
            log_success "Container is running"
            echo ""
            docker ps | grep "$CONTAINER_NAME"
            echo ""
            log_info "API Endpoint:"
            log_info "  http://localhost:${NIM_PORT}/v1/chat/completions"

            # Show recent logs
            echo ""
            log_info "Recent logs:"
            docker logs "$CONTAINER_NAME" --tail 10
        else
            log_error "Container is not running"
            return 1
        fi
    fi
}

# Main execution
main() {
    log_info "NVIDIA NIM LLM Deployment"
    echo ""

    if [[ -n "$REMOTE_HOST" ]]; then
        # Remote deployment
        if deploy_nim_llm_remote "$REMOTE_HOST" "$SSH_KEY"; then
            log_success "Remote deployment complete"
            verify_deployment "$REMOTE_HOST" true
        else
            log_error "Remote deployment failed"
            exit 1
        fi
    else
        # Local deployment
        deploy_nim_llm_local
        verify_deployment
    fi

    echo ""
    log_success "=========================================="
    log_success "NVIDIA NIM LLM Deployed"
    log_success "=========================================="
    echo ""
    log_info "Model: $NIM_MODEL"
    log_info "Endpoint: http://${REMOTE_HOST:-localhost}:${NIM_PORT}/v1/chat/completions"
    echo ""
    log_info "Test with curl:"
    echo ""
    cat << 'EOF'
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta/llama-3.1-8b-instruct",
    "messages": [{"role": "user", "content": "What is RAG?"}],
    "max_tokens": 100
  }'
EOF
    echo ""
    log_info "Monitor logs:"
    log_info "  docker logs -f $CONTAINER_NAME"
    echo ""
    log_info "Next steps:"
    log_info "  1. Wait for model download to complete (check logs)"
    log_info "  2. Test LLM endpoint with curl"
    log_info "  3. Integrate with RAG pipeline"
    echo ""
}

# Run main function
main
