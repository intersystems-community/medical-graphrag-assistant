#!/usr/bin/env bash
#
# Docker GPU Runtime Setup
#
# Installs Docker CE, NVIDIA Container Toolkit, and configures GPU runtime.
# Verifies GPU accessibility within containers.
#
# Usage:
#   ./setup-docker-gpu.sh [--remote <host>] [--ssh-key <path>]
#
# Options:
#   --remote <host>      Setup on remote host via SSH
#   --ssh-key <path>     Path to SSH key for remote setup
#   --skip-verification  Skip GPU verification test
#
# Environment Variables:
#   PUBLIC_IP           Remote host IP (alternative to --remote)
#   SSH_KEY_PATH        Path to SSH key (alternative to --ssh-key)

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
SKIP_VERIFICATION=false

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
        --skip-verification)
            SKIP_VERIFICATION=true
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

# Function to setup Docker and GPU runtime locally
setup_docker_gpu_local() {
    log_info "Setting up Docker with GPU support..."

    # Check if Docker is already installed
    if command -v docker &> /dev/null; then
        log_success "Docker is already installed"
        docker --version
    else
        log_info "Installing Docker CE..."

        # Install prerequisites
        sudo apt-get update -qq
        sudo apt-get install -y -qq ca-certificates curl

        # Add Docker's official GPG key
        sudo install -m 0755 -d /etc/apt/keyrings
        sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
            -o /etc/apt/keyrings/docker.asc
        sudo chmod a+r /etc/apt/keyrings/docker.asc

        # Add repository
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
            $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
            sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

        # Install Docker
        sudo apt-get update -qq
        sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

        # Add current user to docker group
        sudo usermod -aG docker "$USER"

        log_success "Docker installed"
    fi

    # Install NVIDIA Container Toolkit
    log_info "Installing NVIDIA Container Toolkit..."

    # Get distribution
    distribution=$(. /etc/os-release;echo $ID$VERSION_ID)

    # Add NVIDIA GPG key
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
        sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

    # Add repository
    curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
        sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
        sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

    # Install toolkit
    sudo apt-get update -qq
    sudo apt-get install -y -qq nvidia-container-toolkit

    log_success "NVIDIA Container Toolkit installed"

    # Configure Docker runtime
    log_info "Configuring Docker for GPU..."
    sudo nvidia-ctk runtime configure --runtime=docker

    # Restart Docker
    log_info "Restarting Docker..."
    sudo systemctl restart docker

    log_success "Docker configured for GPU"
}

# Function to verify GPU in container
verify_gpu_in_container() {
    log_info "Verifying GPU accessibility in containers..."

    # Run nvidia-smi in a container
    if docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi; then
        log_success "GPU is accessible in containers"
        return 0
    else
        log_error "GPU is not accessible in containers"
        return 1
    fi
}

# Function to setup on remote host
setup_docker_gpu_remote() {
    local host="$1"
    local ssh_key="$2"

    log_info "Setting up Docker GPU runtime on remote host: $host"

    if [[ -z "$ssh_key" ]]; then
        log_error "SSH key required for remote setup"
        return 1
    fi

    if [[ ! -f "$ssh_key" ]]; then
        log_error "SSH key not found: $ssh_key"
        return 1
    fi

    # Execute setup on remote host
    ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i "$ssh_key" "ubuntu@${host}" << 'ENDSSH'
set -e

echo "→ Checking for Docker..."
if command -v docker &> /dev/null; then
    echo "✓ Docker is already installed"
    docker --version
else
    echo "→ Installing Docker CE..."

    # Install prerequisites
    sudo apt-get update -qq
    sudo apt-get install -y -qq ca-certificates curl

    # Add Docker's official GPG key
    sudo install -m 0755 -d /etc/apt/keyrings
    sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        -o /etc/apt/keyrings/docker.asc
    sudo chmod a+r /etc/apt/keyrings/docker.asc

    # Add repository
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
        $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
        sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Install Docker
    sudo apt-get update -qq
    sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Add ubuntu user to docker group
    sudo usermod -aG docker ubuntu

    echo "✓ Docker installed"
fi

echo ""
echo "→ Installing NVIDIA Container Toolkit..."

# Get distribution
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)

# Add NVIDIA GPG key
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
    sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

# Add repository
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# Install toolkit
sudo apt-get update -qq
sudo apt-get install -y -qq nvidia-container-toolkit

echo "✓ NVIDIA Container Toolkit installed"

echo ""
echo "→ Configuring Docker for GPU..."
sudo nvidia-ctk runtime configure --runtime=docker

echo "→ Restarting Docker..."
sudo systemctl restart docker

echo "✓ Docker configured for GPU"

echo ""
echo "→ Verifying GPU in container..."
if docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi; then
    echo ""
    echo "✓ GPU is accessible in containers"
    exit 0
else
    echo "✗ GPU is not accessible in containers"
    exit 1
fi
ENDSSH

    return $?
}

# Main execution
main() {
    log_info "Docker GPU Runtime Setup"
    echo ""

    if [[ -n "$REMOTE_HOST" ]]; then
        # Remote setup
        if setup_docker_gpu_remote "$REMOTE_HOST" "$SSH_KEY"; then
            log_success "Remote setup complete"
        else
            log_error "Remote setup failed"
            exit 1
        fi
    else
        # Local setup
        setup_docker_gpu_local

        if [[ "$SKIP_VERIFICATION" != "true" ]]; then
            echo ""
            if verify_gpu_in_container; then
                echo ""
                log_success "Verification successful"
            else
                log_error "Verification failed"
                log_error "GPU is not accessible in containers"
                exit 1
            fi
        fi
    fi

    echo ""
    log_success "=========================================="
    log_success "Docker GPU Runtime Setup Complete"
    log_success "=========================================="
    echo ""
    log_info "Docker is now configured to use GPUs"
    echo ""
    log_info "Test GPU access:"
    log_info "  docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi"
    echo ""
    log_info "Next steps:"
    log_info "  1. Run: ./scripts/aws/deploy-iris.sh"
    log_info "  2. Run: ./scripts/aws/deploy-nim-llm.sh"
    echo ""
}

# Run main function
main
