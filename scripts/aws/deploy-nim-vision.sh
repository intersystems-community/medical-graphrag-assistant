#!/usr/bin/env bash
#
# Deploy NVIDIA NIM Vision Container
#
# Deploys NVIDIA NIM Vision service for multi-modal image embeddings.
# Requires:
# - NVIDIA GPU with drivers installed
# - Docker with GPU runtime configured
# - NVIDIA API key set in environment
#
# Usage:
#   ./scripts/aws/deploy-nim-vision.sh [--remote PUBLIC_IP] [--ssh-key SSH_KEY_PATH] [--force-recreate]
#
# Options:
#   --remote        Deploy to remote instance via SSH
#   --ssh-key       Path to SSH private key (required with --remote)
#   --force-recreate  Stop and remove existing container before deploying
#
# Environment Variables:
#   NVIDIA_API_KEY  NVIDIA NGC API key (required)
#   NGC_API_KEY     Alternative name for NVIDIA_API_KEY
#
# Exit Codes:
#   0  Success
#   1  Missing requirements or deployment failed
#
# Example:
#   ./scripts/aws/deploy-nim-vision.sh
#   ./scripts/aws/deploy-nim-vision.sh --remote 34.xxx.xxx.xxx --ssh-key ~/.ssh/my-key.pem

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CONTAINER_NAME="nim-vision"
NIM_VISION_IMAGE="nvcr.io/nim/nvidia/nv-clip-vit:latest"
VISION_PORT=8002
INTERNAL_PORT=8000
SHARED_MEMORY="8g"
HEALTH_ENDPOINT_PATH="/health"
HEALTH_CHECK_TIMEOUT=300  # 5 minutes
HEALTH_CHECK_INTERVAL=15  # 15 seconds between checks

# Parse command-line arguments
REMOTE_HOST=""
SSH_KEY_PATH=""
FORCE_RECREATE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --remote)
            REMOTE_HOST="$2"
            shift 2
            ;;
        --ssh-key)
            SSH_KEY_PATH="$2"
            shift 2
            ;;
        --force-recreate)
            FORCE_RECREATE=true
            shift
            ;;
        --help)
            head -n 28 "$0" | tail -n +3
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Validation
if [[ -n "$REMOTE_HOST" && -z "$SSH_KEY_PATH" ]]; then
    echo -e "${RED}Error: --ssh-key required when using --remote${NC}"
    exit 1
fi

if [[ -n "$SSH_KEY_PATH" && ! -f "$SSH_KEY_PATH" ]]; then
    echo -e "${RED}Error: SSH key not found: $SSH_KEY_PATH${NC}"
    exit 1
fi

# Function to execute commands (local or remote)
execute_cmd() {
    if [[ -n "$REMOTE_HOST" ]]; then
        ssh -i "$SSH_KEY_PATH" -o StrictHostKeyChecking=no "ubuntu@$REMOTE_HOST" "$@"
    else
        bash -c "$@"
    fi
}

# Function to check if API key is set
check_api_key() {
    local check_cmd='
        if [ -z "${NVIDIA_API_KEY:-}" ] && [ -z "${NGC_API_KEY:-}" ]; then
            echo "MISSING"
        else
            echo "OK"
        fi
    '

    local result
    result=$(execute_cmd "$check_cmd")

    if [[ "$result" == "MISSING" ]]; then
        echo -e "${RED}✗ NVIDIA API key not found${NC}"
        echo "  Set NVIDIA_API_KEY or NGC_API_KEY environment variable"
        echo "  Get your API key at: https://org.ngc.nvidia.com/setup/api-key"
        return 1
    fi

    echo -e "${GREEN}✓ NVIDIA API key found${NC}"
    return 0
}

# Function to check GPU availability
check_gpu() {
    echo -e "${BLUE}→ Verifying GPU availability...${NC}"

    local gpu_check_cmd='
        if ! command -v nvidia-smi &> /dev/null; then
            echo "MISSING"
        elif ! nvidia-smi &> /dev/null; then
            echo "ERROR"
        else
            echo "OK"
        fi
    '

    local result
    result=$(execute_cmd "$gpu_check_cmd")

    if [[ "$result" == "MISSING" ]]; then
        echo -e "${RED}✗ nvidia-smi not found${NC}"
        echo "  Install NVIDIA drivers first: ./scripts/aws/install-gpu-drivers.sh"
        return 1
    elif [[ "$result" == "ERROR" ]]; then
        echo -e "${RED}✗ GPU not accessible${NC}"
        echo "  Reboot may be required after driver installation"
        return 1
    fi

    echo -e "${GREEN}✓ GPU accessible${NC}"
    return 0
}

# Function to handle existing container
handle_existing_container() {
    echo -e "${BLUE}→ Checking for existing container...${NC}"

    local container_exists
    container_exists=$(execute_cmd "docker ps -a --filter name=^/${CONTAINER_NAME}$ --format '{{.Names}}' 2>/dev/null || true")

    if [[ -n "$container_exists" ]]; then
        if [[ "$FORCE_RECREATE" == true ]]; then
            echo -e "${YELLOW}! Removing existing container: $CONTAINER_NAME${NC}"
            execute_cmd "docker stop $CONTAINER_NAME 2>/dev/null || true"
            execute_cmd "docker rm $CONTAINER_NAME 2>/dev/null || true"
            echo -e "${GREEN}✓ Existing container removed${NC}"
        else
            echo -e "${YELLOW}! Container $CONTAINER_NAME already exists${NC}"
            echo "  Use --force-recreate to remove and redeploy"

            # Check if it's running
            local is_running
            is_running=$(execute_cmd "docker ps --filter name=^/${CONTAINER_NAME}$ --format '{{.Names}}' 2>/dev/null || true")

            if [[ -n "$is_running" ]]; then
                echo -e "${GREEN}✓ Container is already running${NC}"
                return 0
            else
                echo "  Starting stopped container..."
                execute_cmd "docker start $CONTAINER_NAME"
                echo -e "${GREEN}✓ Container started${NC}"
                return 0
            fi
        fi
    fi
}

# Function to pull NIM Vision image
pull_image() {
    echo -e "${BLUE}→ Pulling NVIDIA NIM Vision image...${NC}"
    echo "  Image: $NIM_VISION_IMAGE"
    echo "  This may take several minutes..."

    if execute_cmd "docker pull $NIM_VISION_IMAGE 2>&1" | grep -q "Downloaded\|Image is up to date"; then
        echo -e "${GREEN}✓ Image pulled${NC}"
        return 0
    else
        echo -e "${RED}✗ Failed to pull image${NC}"
        echo "  Check NGC API key and network connectivity"
        return 1
    fi
}

# Function to start NIM Vision container
start_container() {
    echo -e "${BLUE}→ Starting NVIDIA NIM Vision container...${NC}"

    local run_cmd="
        docker run -d \\
            --name $CONTAINER_NAME \\
            --gpus all \\
            --restart unless-stopped \\
            -p $VISION_PORT:$INTERNAL_PORT \\
            -e NGC_API_KEY=\${NVIDIA_API_KEY:-\${NGC_API_KEY}} \\
            -e NIM_MODEL_PROFILE=auto \\
            --shm-size=$SHARED_MEMORY \\
            $NIM_VISION_IMAGE
    "

    if execute_cmd "$run_cmd" &> /dev/null; then
        echo -e "${GREEN}✓ Container started${NC}"
        echo "  Container name: $CONTAINER_NAME"
        echo "  Port mapping: $VISION_PORT:$INTERNAL_PORT"
        return 0
    else
        echo -e "${RED}✗ Failed to start container${NC}"
        execute_cmd "docker logs $CONTAINER_NAME --tail 50 2>&1 || true"
        return 1
    fi
}

# Function to wait for service health
wait_for_health() {
    echo -e "${BLUE}→ Waiting for NIM Vision to initialize...${NC}"
    echo "  This may take 3-5 minutes (model download on first run)"

    local elapsed=0
    local endpoint

    if [[ -n "$REMOTE_HOST" ]]; then
        endpoint="http://$REMOTE_HOST:$VISION_PORT$HEALTH_ENDPOINT_PATH"
    else
        endpoint="http://localhost:$VISION_PORT$HEALTH_ENDPOINT_PATH"
    fi

    while [[ $elapsed -lt $HEALTH_CHECK_TIMEOUT ]]; do
        # Check if container is still running
        local is_running
        is_running=$(execute_cmd "docker ps --filter name=^/${CONTAINER_NAME}$ --format '{{.Names}}' 2>/dev/null || true")

        if [[ -z "$is_running" ]]; then
            echo -e "${RED}✗ Container stopped unexpectedly${NC}"
            echo "  Checking logs..."
            execute_cmd "docker logs $CONTAINER_NAME --tail 50"
            return 1
        fi

        # Try health check
        if execute_cmd "command -v curl &> /dev/null" &> /dev/null; then
            if execute_cmd "curl -sf $endpoint" &> /dev/null; then
                echo -e "${GREEN}✓ NIM Vision service is healthy${NC}"
                return 0
            fi
        fi

        # Show progress
        echo "  Still initializing... (${elapsed}s/${HEALTH_CHECK_TIMEOUT}s)"
        sleep $HEALTH_CHECK_INTERVAL
        elapsed=$((elapsed + HEALTH_CHECK_INTERVAL))
    done

    echo -e "${YELLOW}! Health check timeout${NC}"
    echo "  Service may still be initializing - check logs:"
    echo "  docker logs $CONTAINER_NAME"
    return 0  # Don't fail deployment, just warn
}

# Function to show deployment info
show_deployment_info() {
    local host
    if [[ -n "$REMOTE_HOST" ]]; then
        host="$REMOTE_HOST"
    else
        host="localhost"
    fi

    cat << EOF

${GREEN}==========================================
NVIDIA NIM Vision Deployed
==========================================${NC}

Model: CLIP Vision Transformer
Endpoint: http://$host:$VISION_PORT
Health: http://$host:$VISION_PORT/health

Container Details:
  Name: $CONTAINER_NAME
  Port: $VISION_PORT (external) → $INTERNAL_PORT (internal)
  GPU: Enabled
  Shared Memory: $SHARED_MEMORY

Test with curl:
  curl -X POST http://$host:$VISION_PORT/v1/embeddings \\
    -H "Content-Type: application/json" \\
    -d '{
      "input": "base64_encoded_image_here",
      "model": "nv-clip-vit"
    }'

Check logs:
  docker logs $CONTAINER_NAME

Monitor GPU usage:
  nvidia-smi --loop=1

EOF
}

# Main deployment flow
main() {
    echo ""
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║ NVIDIA NIM Vision Deployment                                 ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    if [[ -n "$REMOTE_HOST" ]]; then
        echo -e "${BLUE}Remote deployment to: $REMOTE_HOST${NC}"
        echo ""
    fi

    # Run deployment steps
    check_api_key || exit 1
    check_gpu || exit 1
    handle_existing_container || exit 1
    pull_image || exit 1
    start_container || exit 1
    wait_for_health || echo -e "${YELLOW}(Continuing despite health check timeout)${NC}"

    show_deployment_info

    echo -e "${GREEN}✅ NIM Vision deployment complete!${NC}"
    echo ""
}

# Execute main function
main
