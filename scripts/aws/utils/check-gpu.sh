#!/usr/bin/env bash
#
# GPU Verification Utility
#
# Checks if NVIDIA GPU is available and returns device information.
# Used by deployment scripts to verify GPU support before deploying services.
#
# Usage:
#   ./check-gpu.sh [--json]
#
# Options:
#   --json    Output results in JSON format
#
# Exit codes:
#   0 - GPU found and working
#   1 - nvidia-smi not found
#   2 - GPU not detected
#   3 - Driver error

set -euo pipefail

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m' # No Color

# JSON output flag
JSON_OUTPUT=false
if [[ "${1:-}" == "--json" ]]; then
    JSON_OUTPUT=true
fi

# Function to output messages
log_info() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${GREEN}✓${NC} $1"
    fi
}

log_error() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${RED}✗${NC} $1" >&2
    fi
}

log_warn() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${YELLOW}!${NC} $1" >&2
    fi
}

# Check if nvidia-smi exists
if ! command -v nvidia-smi &> /dev/null; then
    if [[ "$JSON_OUTPUT" == "true" ]]; then
        echo '{"status":"error","code":1,"message":"nvidia-smi not found","gpu_present":false}'
    else
        log_error "nvidia-smi not found"
        log_info "Install NVIDIA drivers with: sudo apt-get install nvidia-driver-535"
    fi
    exit 1
fi

# Run nvidia-smi and capture output
if ! nvidia_output=$(nvidia-smi --query-gpu=name,driver_version,memory.total,compute_cap --format=csv,noheader,nounits 2>&1); then
    if [[ "$JSON_OUTPUT" == "true" ]]; then
        echo '{"status":"error","code":3,"message":"nvidia-smi failed","gpu_present":false,"error":"'"${nvidia_output}"'"}'
    else
        log_error "nvidia-smi command failed"
        log_error "Error: ${nvidia_output}"
        log_warn "GPU drivers may not be loaded. Try rebooting the system."
    fi
    exit 3
fi

# Check if any GPU was detected
if [[ -z "$nvidia_output" ]]; then
    if [[ "$JSON_OUTPUT" == "true" ]]; then
        echo '{"status":"error","code":2,"message":"No GPU detected","gpu_present":false}'
    else
        log_error "No NVIDIA GPU detected"
        log_info "Ensure GPU is installed and drivers are loaded"
    fi
    exit 2
fi

# Parse GPU information
IFS=',' read -r gpu_name driver_version memory_mb compute_cap <<< "$nvidia_output"

# Trim whitespace
gpu_name=$(echo "$gpu_name" | xargs)
driver_version=$(echo "$driver_version" | xargs)
memory_mb=$(echo "$memory_mb" | xargs)
compute_cap=$(echo "$compute_cap" | xargs)

# Convert memory to GB
memory_gb=$(awk "BEGIN {printf \"%.1f\", $memory_mb / 1024}")

# Get CUDA version
cuda_version=$(nvidia-smi | grep "CUDA Version" | awk '{print $9}' || echo "unknown")

# Count number of GPUs
gpu_count=$(nvidia-smi --list-gpus | wc -l)

if [[ "$JSON_OUTPUT" == "true" ]]; then
    # JSON output
    cat <<EOF
{
  "status": "success",
  "code": 0,
  "gpu_present": true,
  "gpu_count": ${gpu_count},
  "gpu_name": "${gpu_name}",
  "driver_version": "${driver_version}",
  "cuda_version": "${cuda_version}",
  "memory_total_mb": ${memory_mb},
  "memory_total_gb": ${memory_gb},
  "compute_capability": "${compute_cap}"
}
EOF
else
    # Human-readable output
    log_info "GPU Check Passed"
    echo ""
    echo "GPU Information:"
    echo "  Name:               ${gpu_name}"
    echo "  Count:              ${gpu_count}"
    echo "  Driver Version:     ${driver_version}"
    echo "  CUDA Version:       ${cuda_version}"
    echo "  Memory:             ${memory_gb} GB (${memory_mb} MB)"
    echo "  Compute Capability: ${compute_cap}"
    echo ""

    # Check if it's the expected g5.xlarge GPU
    if [[ "$gpu_name" == *"A10G"* ]]; then
        log_info "Detected NVIDIA A10G (AWS g5.xlarge)"
    else
        log_warn "Expected NVIDIA A10G for g5.xlarge, found: ${gpu_name}"
    fi

    # Check memory requirements
    memory_gb_int=${memory_gb%.*}
    if [[ "$memory_gb_int" -ge 20 ]]; then
        log_info "Sufficient GPU memory for NIM LLM (≥20GB)"
    else
        log_warn "GPU memory may be insufficient for some NIM models (${memory_gb}GB < 20GB)"
    fi
fi

exit 0
