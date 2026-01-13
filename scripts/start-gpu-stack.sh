#!/bin/bash
# =============================================================================
# Medical GraphRAG GPU Stack Launcher
# One-command startup for the full medical search stack
# =============================================================================
#
# Prerequisites:
#   - Docker with NVIDIA Container Toolkit
#   - NGC API Key (https://ngc.nvidia.com/setup/api-key)
#   - GPU instance (g5.xlarge minimum, g5.12xlarge recommended)
#
# Usage:
#   ./scripts/start-gpu-stack.sh              # Interactive mode
#   NGC_API_KEY=xxx ./scripts/start-gpu-stack.sh  # With key
#   ./scripts/start-gpu-stack.sh --stop       # Stop all services
#   ./scripts/start-gpu-stack.sh --status     # Check status
#
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.gpu.yml"

print_banner() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║     Medical GraphRAG Assistant - GPU Stack Launcher          ║"
    echo "║     IRIS FHIR + NIM LLM + NV-CLIP                            ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

check_prerequisites() {
    echo -e "${YELLOW}Checking prerequisites...${NC}"

    # Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}✗ Docker not found. Please install Docker.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Docker installed${NC}"

    # Docker Compose
    if ! docker compose version &> /dev/null; then
        echo -e "${RED}✗ Docker Compose not found. Please install Docker Compose V2.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Docker Compose installed${NC}"

    # NVIDIA Docker
    if ! docker info 2>/dev/null | grep -q "Runtimes.*nvidia"; then
        echo -e "${YELLOW}⚠ NVIDIA Container Toolkit may not be installed${NC}"
        echo "  Install: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html"
    else
        echo -e "${GREEN}✓ NVIDIA Container Toolkit installed${NC}"
    fi

    # GPU Check
    if command -v nvidia-smi &> /dev/null; then
        GPU_COUNT=$(nvidia-smi --query-gpu=name --format=csv,noheader | wc -l)
        GPU_MEM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader | head -1)
        echo -e "${GREEN}✓ Found $GPU_COUNT GPU(s) ($GPU_MEM each)${NC}"

        if [ "$GPU_COUNT" -lt 4 ]; then
            echo -e "${YELLOW}  Note: g5.12xlarge (4 GPUs) recommended for full stack${NC}"
            echo -e "${YELLOW}  Single GPU mode may require running LLM and NV-CLIP sequentially${NC}"
        fi
    else
        echo -e "${RED}✗ nvidia-smi not found. Is this a GPU instance?${NC}"
        exit 1
    fi

    # NGC API Key
    if [ -z "$NGC_API_KEY" ]; then
        # Try to load from .env
        if [ -f "$PROJECT_ROOT/.env" ]; then
            source "$PROJECT_ROOT/.env"
        fi
    fi

    if [ -z "$NGC_API_KEY" ]; then
        echo -e "${YELLOW}⚠ NGC_API_KEY not set${NC}"
        echo "  Get your key from: https://ngc.nvidia.com/setup/api-key"
        read -p "  Enter NGC API Key: " NGC_API_KEY
        export NGC_API_KEY

        # Save to .env
        echo "export NGC_API_KEY=$NGC_API_KEY" >> "$PROJECT_ROOT/.env"
        echo -e "${GREEN}✓ NGC_API_KEY saved to .env${NC}"
    else
        echo -e "${GREEN}✓ NGC_API_KEY configured${NC}"
    fi
}

start_stack() {
    echo ""
    echo -e "${BLUE}Starting Medical GraphRAG Stack...${NC}"
    echo ""

    cd "$PROJECT_ROOT"

    # Pull latest images
    echo -e "${YELLOW}Pulling latest images...${NC}"
    docker compose -f "$COMPOSE_FILE" pull

    # Start services
    echo ""
    echo -e "${YELLOW}Starting services...${NC}"
    docker compose -f "$COMPOSE_FILE" up -d

    # Wait for services
    echo ""
    echo -e "${YELLOW}Waiting for services to be healthy (this may take 3-5 minutes)...${NC}"

    # Wait for IRIS
    echo -n "  IRIS FHIR: "
    for i in {1..60}; do
        if docker compose -f "$COMPOSE_FILE" ps iris-fhir | grep -q "healthy"; then
            echo -e "${GREEN}Ready${NC}"
            break
        fi
        echo -n "."
        sleep 5
    done

    # Wait for LLM
    echo -n "  NIM LLM: "
    for i in {1..60}; do
        if curl -sf http://localhost:8001/v1/models > /dev/null 2>&1; then
            echo -e "${GREEN}Ready${NC}"
            break
        fi
        echo -n "."
        sleep 5
    done

    # Wait for NV-CLIP
    echo -n "  NV-CLIP: "
    for i in {1..60}; do
        if curl -sf -X POST http://localhost:8002/v1/embeddings \
            -H "Content-Type: application/json" \
            -d '{"input":["test"],"model":"nvidia/nvclip"}' > /dev/null 2>&1; then
            echo -e "${GREEN}Ready${NC}"
            break
        fi
        echo -n "."
        sleep 5
    done

    echo ""
    show_status
}

stop_stack() {
    echo -e "${YELLOW}Stopping Medical GraphRAG Stack...${NC}"
    cd "$PROJECT_ROOT"
    docker compose -f "$COMPOSE_FILE" down
    echo -e "${GREEN}✓ All services stopped${NC}"
}

show_status() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}                     SERVICE STATUS                            ${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

    cd "$PROJECT_ROOT"
    docker compose -f "$COMPOSE_FILE" ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}                       ENDPOINTS                               ${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

    PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "localhost")

    echo -e "  ${GREEN}Streamlit UI:${NC}    http://$PUBLIC_IP:8501"
    echo -e "  ${GREEN}IRIS Portal:${NC}     http://$PUBLIC_IP:32783/csp/sys/UtilHome.csp"
    echo -e "  ${GREEN}FHIR Endpoint:${NC}   http://$PUBLIC_IP:32783/csp/healthshare/demo/fhir/r4"
    echo -e "  ${GREEN}NIM LLM:${NC}         http://$PUBLIC_IP:8001/v1"
    echo -e "  ${GREEN}NV-CLIP:${NC}         http://$PUBLIC_IP:8002/v1"

    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}                     GPU ALLOCATION                            ${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    nvidia-smi --query-gpu=index,name,memory.used,memory.total --format=csv 2>/dev/null || echo "GPU info unavailable"
    echo ""
}

show_logs() {
    cd "$PROJECT_ROOT"
    docker compose -f "$COMPOSE_FILE" logs -f "$@"
}

# Main
print_banner

case "${1:-}" in
    --stop|-s)
        stop_stack
        ;;
    --status|-t)
        show_status
        ;;
    --logs|-l)
        shift
        show_logs "$@"
        ;;
    --help|-h)
        echo "Usage: $0 [OPTION]"
        echo ""
        echo "Options:"
        echo "  (none)      Start the full GPU stack"
        echo "  --stop      Stop all services"
        echo "  --status    Show service status"
        echo "  --logs      Follow service logs"
        echo "  --help      Show this help"
        ;;
    *)
        check_prerequisites
        start_stack
        ;;
esac
