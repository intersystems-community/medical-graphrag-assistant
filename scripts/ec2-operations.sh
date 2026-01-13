#!/bin/bash
# EC2 Service Operations Script for Medical GraphRAG Assistant
# Verified reliable start/stop commands for AWS production deployment
#
SSH_KEY="$HOME/.ssh/fhir-ai-key-recovery.pem"
EC2_HOST="ubuntu@13.222.216.34"
SSH_CMD="ssh -o StrictHostKeyChecking=no -i $SSH_KEY $EC2_HOST"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

function print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

function print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

function print_error() {
    echo -e "${RED}✗${NC} $1"
}

function check_status() {
    echo "=== Service Status Check ==="
    $SSH_CMD "
    echo '--- Streamlit ---'
    pgrep -af streamlit || echo 'Not running'
    echo ''
    echo '--- Docker Containers ---'
    docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
    echo ''
    echo '--- Port Listeners ---'
    ss -tlnp | grep -E '(8501|8002|32782|32783)' || echo 'No ports listening'
    "
}

function stop_streamlit() {
    echo "=== Stopping Streamlit ==="
    $SSH_CMD "pkill -9 streamlit" 2>/dev/null
    sleep 2

    # Verify it's down
    if $SSH_CMD "pgrep -q streamlit" 2>/dev/null; then
        print_error "Streamlit still running!"
        return 1
    else
        print_status "Streamlit stopped"
    fi

    # External health check
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 http://13.222.216.34:8501/)
    if [ "$HTTP_CODE" = "000" ]; then
        print_status "External access confirmed down (HTTP $HTTP_CODE)"
    else
        print_warning "Unexpected HTTP code: $HTTP_CODE"
    fi
}

function start_streamlit() {
    echo "=== Starting Streamlit ==="
    $SSH_CMD "
    cd ~/medical-graphrag-assistant
    if [ -f .env ]; then
        source .env
    fi
    cd mcp-server
    source ~/medical-graphrag/venv/bin/activate
    export NVCLIP_BASE_URL=http://localhost:8002/v1
    nohup streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0 > ~/streamlit.log 2>&1 &
    "

    echo "Waiting for startup..."
    sleep 5

    # Verify it's running
    if $SSH_CMD "pgrep -q streamlit" 2>/dev/null; then
        print_status "Streamlit process running"
    else
        print_error "Streamlit failed to start! Check ~/streamlit.log"
        return 1
    fi

    # External health check
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 http://13.218.19.254:8501/)
    if [ "$HTTP_CODE" = "200" ]; then
        print_status "External health check passed (HTTP $HTTP_CODE)"
    else
        print_error "Health check failed (HTTP $HTTP_CODE)"
        return 1
    fi
}

function restart_streamlit() {
    echo "=== Restarting Streamlit ==="
    stop_streamlit
    sleep 2
    start_streamlit
}

function stop_docker() {
    echo "=== Stopping Docker Containers ==="
    $SSH_CMD "
    docker stop iris-fhir nim-nvclip 2>/dev/null
    docker ps --format '{{.Names}} - {{.Status}}'
    "
    print_status "Docker containers stopped"
}

function start_docker() {
    echo "=== Starting Docker Containers ==="
    $SSH_CMD "
    docker start iris-fhir nim-nvclip 2>/dev/null
    sleep 10
    docker ps --format 'table {{.Names}}\t{{.Status}}'
    "
    print_status "Docker containers started"
}

function view_logs() {
    echo "=== Recent Streamlit Logs ==="
    $SSH_CMD "tail -50 ~/streamlit.log"
}

function deploy_latest() {
    echo "=== Deploying Latest Code ==="
    local BRANCH=${1:-main}

    $SSH_CMD "
    cd ~/medical-graphrag-assistant
    git fetch origin
    git reset --hard origin/$BRANCH
    "
    print_status "Code updated to $BRANCH (hard reset)"

    restart_streamlit
}

# Main command handler
case "$1" in
    status)
        check_status
        ;;
    stop)
        stop_streamlit
        ;;
    start)
        start_streamlit
        ;;
    restart)
        restart_streamlit
        ;;
    stop-docker)
        stop_docker
        ;;
    start-docker)
        start_docker
        ;;
    logs)
        view_logs
        ;;
    deploy)
        deploy_latest "$2"
        ;;
    health)
        echo "=== Health Check ==="
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 http://13.222.216.34:8501/)
        if [ "$HTTP_CODE" = "200" ]; then
            print_status "Streamlit: HTTP $HTTP_CODE (healthy)"
        else
            print_error "Streamlit: HTTP $HTTP_CODE (unhealthy)"
        fi
        ;;
    *)
        echo "Usage: $0 {status|stop|start|restart|stop-docker|start-docker|logs|deploy [branch]|health}"
        echo ""
        echo "Commands:"
        echo "  status       - Show all service status"
        echo "  stop         - Stop Streamlit service"
        echo "  start        - Start Streamlit service"
        echo "  restart      - Restart Streamlit service"
        echo "  stop-docker  - Stop Docker containers (iris-fhir, nim-nvclip)"
        echo "  start-docker - Start Docker containers"
        echo "  logs         - View recent Streamlit logs"
        echo "  deploy       - Deploy latest code from branch (default: main)"
        echo "  health       - Quick health check"
        exit 1
        ;;
esac
