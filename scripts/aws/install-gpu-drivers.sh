#!/usr/bin/env bash
#
# NVIDIA GPU Driver Installation
#
# Installs NVIDIA driver 535 (LTS) and utilities on Ubuntu 24.04.
# Verifies installation and provides reboot guidance.
#
# Usage:
#   ./install-gpu-drivers.sh [--remote <host>] [--ssh-key <path>]
#
# Options:
#   --remote <host>      Install on remote host via SSH
#   --ssh-key <path>     Path to SSH key for remote installation
#   --skip-verification  Skip GPU verification after installation
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

# Function to install drivers locally
install_drivers_local() {
    log_info "Installing NVIDIA drivers (driver-535 LTS)..."

    # Update package list
    sudo apt-get update -qq

    # Install NVIDIA driver and utilities
    log_info "Installing nvidia-driver-535 and nvidia-utils-535..."
    sudo apt-get install -y -qq nvidia-driver-535 nvidia-utils-535

    log_success "NVIDIA drivers installed"
}

# Function to verify installation
verify_installation() {
    log_info "Verifying GPU driver installation..."

    if command -v nvidia-smi &> /dev/null; then
        log_success "nvidia-smi is available"

        # Try to run nvidia-smi
        if nvidia-smi &> /dev/null; then
            log_success "GPU is accessible"
            echo ""
            nvidia-smi
            return 0
        else
            log_warn "nvidia-smi installed but GPU not accessible"
            log_warn "Reboot required for driver to load"
            return 1
        fi
    else
        log_error "nvidia-smi not found"
        return 1
    fi
}

# Function to install on remote host
install_drivers_remote() {
    local host="$1"
    local ssh_key="$2"

    log_info "Installing NVIDIA drivers on remote host: $host"

    if [[ -z "$ssh_key" ]]; then
        log_error "SSH key required for remote installation"
        log_error "Use --ssh-key or set SSH_KEY_PATH environment variable"
        return 1
    fi

    if [[ ! -f "$ssh_key" ]]; then
        log_error "SSH key not found: $ssh_key"
        return 1
    fi

    # Execute installation on remote host
    ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i "$ssh_key" "ubuntu@${host}" << 'ENDSSH'
set -e

echo "→ Updating package list..."
sudo apt-get update -qq

echo "→ Installing NVIDIA driver 535 (LTS)..."
sudo apt-get install -y -qq nvidia-driver-535 nvidia-utils-535

echo "✓ NVIDIA drivers installed"

# Check if nvidia-smi is available
if command -v nvidia-smi &> /dev/null; then
    echo "✓ nvidia-smi is available"

    # Try to run nvidia-smi
    if nvidia-smi &> /dev/null; then
        echo "✓ GPU is accessible (no reboot needed)"
        nvidia-smi
    else
        echo "! GPU not yet accessible - reboot required"
        exit 2  # Special exit code for reboot needed
    fi
else
    echo "✗ nvidia-smi not found"
    exit 1
fi
ENDSSH

    local exit_code=$?

    if [[ $exit_code -eq 0 ]]; then
        log_success "Drivers installed and GPU is accessible"
        return 0
    elif [[ $exit_code -eq 2 ]]; then
        log_warn "Drivers installed but reboot required"
        return 2
    else
        log_error "Driver installation failed"
        return 1
    fi
}

# Function to reboot remote host
reboot_remote_host() {
    local host="$1"
    local ssh_key="$2"

    log_info "Rebooting remote host..."

    ssh -o StrictHostKeyChecking=no -i "$ssh_key" "ubuntu@${host}" 'sudo reboot' || true

    log_info "Waiting 60 seconds for instance to reboot..."
    sleep 60

    # Wait for SSH to be available again
    log_info "Waiting for SSH to be available..."
    local retries=30
    local count=0

    while [[ $count -lt $retries ]]; do
        if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -i "$ssh_key" "ubuntu@${host}" 'echo ready' &> /dev/null; then
            log_success "Instance is back online"
            return 0
        fi
        count=$((count + 1))
        sleep 10
    done

    log_error "Instance did not come back online after reboot"
    return 1
}

# Function to verify remote GPU
verify_remote_gpu() {
    local host="$1"
    local ssh_key="$2"

    log_info "Verifying GPU on remote host..."

    ssh -o StrictHostKeyChecking=no -i "$ssh_key" "ubuntu@${host}" << 'ENDSSH'
if nvidia-smi &> /dev/null; then
    echo "✓ GPU is accessible"
    echo ""
    nvidia-smi
    exit 0
else
    echo "✗ GPU still not accessible"
    exit 1
fi
ENDSSH

    return $?
}

# Main execution
main() {
    log_info "NVIDIA GPU Driver Installation"
    echo ""

    if [[ -n "$REMOTE_HOST" ]]; then
        # Remote installation
        if install_drivers_remote "$REMOTE_HOST" "$SSH_KEY"; then
            log_success "Installation complete - GPU is accessible"
        elif [[ $? -eq 2 ]]; then
            log_warn "Reboot required to load drivers"
            echo ""
            read -p "Reboot instance now? (yes/no): " -r response
            if [[ "$response" == "yes" ]]; then
                reboot_remote_host "$REMOTE_HOST" "$SSH_KEY"
                verify_remote_gpu "$REMOTE_HOST" "$SSH_KEY"
            else
                log_info "Reboot manually and run again to verify"
            fi
        else
            log_error "Installation failed"
            exit 1
        fi
    else
        # Local installation
        install_drivers_local

        if [[ "$SKIP_VERIFICATION" != "true" ]]; then
            if ! verify_installation; then
                echo ""
                log_warn "=========================================="
                log_warn "REBOOT REQUIRED"
                log_warn "=========================================="
                log_warn "Drivers are installed but GPU is not accessible"
                log_warn "The system must be rebooted for drivers to load"
                echo ""
                log_info "To reboot: sudo reboot"
                log_info "After reboot, verify with: nvidia-smi"
                echo ""
                exit 2
            fi
        fi
    fi

    echo ""
    log_success "=========================================="
    log_success "NVIDIA Driver Installation Complete"
    log_success "=========================================="
    echo ""
    log_info "Next steps:"
    log_info "  1. If not already done, reboot the system"
    log_info "  2. Verify GPU: nvidia-smi"
    log_info "  3. Run: ./scripts/aws/setup-docker-gpu.sh"
    echo ""
}

# Run main function
main
