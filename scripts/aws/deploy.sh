#!/usr/bin/env bash
#
# Complete AWS GPU NIM RAG System Deployment
#
# Orchestrates full deployment of FHIR AI RAG system on AWS:
# - EC2 g5.xlarge instance provisioning
# - NVIDIA GPU driver installation
# - Docker GPU runtime configuration
# - InterSystems IRIS vector database
# - NVIDIA NIM LLM (Llama 3.1 8B)
#
# Usage:
#   ./deploy.sh [--provision] [--skip-<component>]
#
# Options:
#   --provision              Provision new EC2 instance
#   --instance-id <id>       Use existing instance ID
#   --skip-drivers           Skip GPU driver installation
#   --skip-docker            Skip Docker GPU setup
#   --skip-iris              Skip IRIS deployment
#   --skip-nim-llm           Skip NIM LLM deployment
#   --force                  Force recreate all containers
#
# Environment Variables (required):
#   AWS_REGION              AWS region (default: us-east-1)
#   SSH_KEY_NAME            Name of SSH key pair
#   NVIDIA_API_KEY          NVIDIA NGC API key
#
# Optional Environment Variables:
#   INSTANCE_ID             Existing EC2 instance ID
#   PUBLIC_IP               Existing instance public IP

set -euo pipefail

# Colors
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly MAGENTA='\033[0;35m'
readonly NC='\033[0m'

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Configuration
PROVISION_INSTANCE=false
SKIP_DRIVERS=false
SKIP_DOCKER=false
SKIP_IRIS=false
SKIP_NIM_LLM=false
FORCE_RECREATE=false
INSTANCE_ID="${INSTANCE_ID:-}"
PUBLIC_IP="${PUBLIC_IP:-}"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --provision)
            PROVISION_INSTANCE=true
            shift
            ;;
        --instance-id)
            INSTANCE_ID="$2"
            shift 2
            ;;
        --skip-drivers)
            SKIP_DRIVERS=true
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
        --skip-nim-llm)
            SKIP_NIM_LLM=true
            shift
            ;;
        --force)
            FORCE_RECREATE=true
            shift
            ;;
        --help)
            grep '^#' "$0" | sed 's/^# \?//'
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}" >&2
            echo "Use --help for usage information" >&2
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

log_step() {
    echo -e "${MAGENTA}▶${NC} ${YELLOW}Step $1:${NC} $2"
}

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

# Function to check required environment variables
check_prerequisites() {
    log_step "0" "Checking prerequisites"

    local missing=0

    # Check SSH_KEY_NAME
    if [[ -z "${SSH_KEY_NAME:-}" ]]; then
        log_error "SSH_KEY_NAME environment variable is required"
        missing=1
    else
        log_success "SSH_KEY_NAME: $SSH_KEY_NAME"
    fi

    # Check NVIDIA_API_KEY
    if [[ -z "${NVIDIA_API_KEY:-}" ]]; then
        log_error "NVIDIA_API_KEY environment variable is required"
        missing=1
    else
        log_success "NVIDIA_API_KEY: [REDACTED]"
    fi

    # Check SSH key file exists
    local ssh_key_path="${SSH_KEY_PATH:-$HOME/.ssh/${SSH_KEY_NAME}.pem}"
    if [[ ! -f "$ssh_key_path" ]]; then
        log_error "SSH key not found: $ssh_key_path"
        missing=1
    else
        log_success "SSH key found: $ssh_key_path"
        export SSH_KEY_PATH="$ssh_key_path"
    fi

    # Check AWS credentials
    if ! aws sts get-caller-identity &>/dev/null; then
        log_error "AWS credentials not configured"
        log_error "Run: aws configure"
        missing=1
    else
        log_success "AWS credentials configured"
    fi

    if [[ $missing -gt 0 ]]; then
        log_error "Missing required prerequisites"
        exit 1
    fi

    log_success "All prerequisites met"
    echo ""
}

# Function to provision instance
provision_ec2_instance() {
    log_step "1" "Provisioning EC2 instance"

    if [[ -n "$INSTANCE_ID" ]]; then
        log_info "Using existing instance: $INSTANCE_ID"

        # Get public IP
        PUBLIC_IP=$(aws ec2 describe-instances \
            --instance-ids "$INSTANCE_ID" \
            --query 'Reservations[0].Instances[0].PublicIpAddress' \
            --output text)

        if [[ -z "$PUBLIC_IP" || "$PUBLIC_IP" == "None" ]]; then
            log_error "Could not get public IP for instance $INSTANCE_ID"
            exit 1
        fi

        log_success "Instance IP: $PUBLIC_IP"
    else
        log_info "Provisioning new EC2 instance..."

        if ! "$SCRIPT_DIR/provision-instance.sh"; then
            log_error "Instance provisioning failed"
            exit 1
        fi

        # Load instance info
        if [[ -f .instance-info ]]; then
            source .instance-info
            log_success "Instance provisioned: $INSTANCE_ID"
            log_success "Public IP: $PUBLIC_IP"
        else
            log_error "Instance info file not found"
            exit 1
        fi
    fi

    echo ""
}

# Function to install GPU drivers
install_gpu_drivers() {
    log_step "2" "Installing NVIDIA GPU drivers"

    if [[ "$SKIP_DRIVERS" == "true" ]]; then
        log_warn "Skipping GPU driver installation (--skip-drivers)"
        echo ""
        return 0
    fi

    log_info "Installing nvidia-driver-535 on $PUBLIC_IP..."

    if "$SCRIPT_DIR/install-gpu-drivers.sh" --remote "$PUBLIC_IP" --ssh-key "$SSH_KEY_PATH"; then
        log_success "GPU drivers installed"
    else
        local exit_code=$?
        if [[ $exit_code -eq 2 ]]; then
            log_warn "Reboot required for GPU drivers"
            log_info "Rebooting instance..."

            # Reboot instance
            ssh -o StrictHostKeyChecking=no -i "$SSH_KEY_PATH" "ubuntu@${PUBLIC_IP}" 'sudo reboot' || true

            log_info "Waiting 90 seconds for reboot..."
            sleep 90

            # Wait for SSH to come back
            log_info "Waiting for SSH..."
            local retries=30
            local count=0

            while [[ $count -lt $retries ]]; do
                if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -i "$SSH_KEY_PATH" "ubuntu@${PUBLIC_IP}" 'echo ready' &>/dev/null; then
                    log_success "Instance is back online"
                    break
                fi
                count=$((count + 1))
                sleep 10
            done

            if [[ $count -ge $retries ]]; then
                log_error "Instance did not come back online"
                exit 1
            fi

            # Verify GPU
            log_info "Verifying GPU..."
            if ssh -o StrictHostKeyChecking=no -i "$SSH_KEY_PATH" "ubuntu@${PUBLIC_IP}" 'nvidia-smi' &>/dev/null; then
                log_success "GPU is accessible"
            else
                log_error "GPU verification failed"
                exit 1
            fi
        else
            log_error "GPU driver installation failed"
            exit 1
        fi
    fi

    echo ""
}

# Function to setup Docker GPU runtime
setup_docker_gpu() {
    log_step "3" "Setting up Docker GPU runtime"

    if [[ "$SKIP_DOCKER" == "true" ]]; then
        log_warn "Skipping Docker GPU setup (--skip-docker)"
        echo ""
        return 0
    fi

    log_info "Configuring Docker with GPU support on $PUBLIC_IP..."

    if "$SCRIPT_DIR/setup-docker-gpu.sh" --remote "$PUBLIC_IP" --ssh-key "$SSH_KEY_PATH"; then
        log_success "Docker GPU runtime configured"
    else
        log_error "Docker GPU setup failed"
        exit 1
    fi

    echo ""
}

# Function to deploy IRIS
deploy_iris_database() {
    log_step "4" "Deploying InterSystems IRIS Vector Database"

    if [[ "$SKIP_IRIS" == "true" ]]; then
        log_warn "Skipping IRIS deployment (--skip-iris)"
        echo ""
        return 0
    fi

    log_info "Deploying IRIS on $PUBLIC_IP..."

    local force_flag=""
    if [[ "$FORCE_RECREATE" == "true" ]]; then
        force_flag="--force-recreate"
    fi

    if "$SCRIPT_DIR/deploy-iris.sh" --remote "$PUBLIC_IP" --ssh-key "$SSH_KEY_PATH" $force_flag; then
        log_success "IRIS vector database deployed"
    else
        log_error "IRIS deployment failed"
        exit 1
    fi

    echo ""
}

# Function to deploy NIM LLM
deploy_nim_llm() {
    log_step "5" "Deploying NVIDIA NIM LLM"

    if [[ "$SKIP_NIM_LLM" == "true" ]]; then
        log_warn "Skipping NIM LLM deployment (--skip-nim-llm)"
        echo ""
        return 0
    fi

    log_info "Deploying NIM LLM on $PUBLIC_IP..."

    local force_flag=""
    if [[ "$FORCE_RECREATE" == "true" ]]; then
        force_flag="--force-recreate"
    fi

    # Export NVIDIA_API_KEY for remote script
    export NVIDIA_API_KEY

    if "$SCRIPT_DIR/deploy-nim-llm.sh" --remote "$PUBLIC_IP" --ssh-key "$SSH_KEY_PATH" $force_flag; then
        log_success "NIM LLM deployed"
    else
        log_error "NIM LLM deployment failed"
        exit 1
    fi

    echo ""
}

# Function to verify deployment
verify_deployment() {
    log_step "6" "Verifying deployment"

    log_info "Running comprehensive validation..."
    echo ""

    # Run validation script
    if "$SCRIPT_DIR/validate-deployment.sh" --remote "$PUBLIC_IP" --ssh-key "$SSH_KEY_PATH"; then
        log_success "All validation checks passed"
        return 0
    else
        log_error "Validation checks failed"
        log_info "Review errors above and check:"
        log_info "  - docs/troubleshooting.md for solutions"
        log_info "  - docker logs on instance for service errors"
        return 1
    fi
}

# Function to display deployment summary
display_summary() {
    log_header "DEPLOYMENT COMPLETE"

    cat << EOF
${GREEN}✓ AWS GPU-based NVIDIA NIM RAG System Deployed${NC}

${CYAN}Instance Details:${NC}
  Instance ID:  ${INSTANCE_ID}
  Public IP:    ${PUBLIC_IP}
  Instance Type: g5.xlarge
  Region:       ${AWS_REGION:-us-east-1}

${CYAN}Service Endpoints:${NC}
  IRIS SQL:              ${PUBLIC_IP}:1972
  IRIS Management:       http://${PUBLIC_IP}:52773/csp/sys/UtilHome.csp
  NIM LLM API:           http://${PUBLIC_IP}:8001/v1/chat/completions

${CYAN}Credentials:${NC}
  IRIS Username:         _SYSTEM
  IRIS Password:         SYS
  IRIS Namespace:        DEMO

${CYAN}SSH Access:${NC}
  ssh -i ${SSH_KEY_PATH} ubuntu@${PUBLIC_IP}

${CYAN}Test NIM LLM:${NC}
  curl -X POST http://${PUBLIC_IP}:8001/v1/chat/completions \\
    -H "Content-Type: application/json" \\
    -d '{
      "model": "meta/llama-3.1-8b-instruct",
      "messages": [{"role": "user", "content": "What is RAG?"}],
      "max_tokens": 100
    }'

${CYAN}Monitor Services:${NC}
  ssh -i ${SSH_KEY_PATH} ubuntu@${PUBLIC_IP} 'docker ps'
  ssh -i ${SSH_KEY_PATH} ubuntu@${PUBLIC_IP} 'docker logs iris-vector-db'
  ssh -i ${SSH_KEY_PATH} ubuntu@${PUBLIC_IP} 'docker logs nim-llm'

${CYAN}Next Steps:${NC}
  1. Test IRIS connection with Python client
  2. Test NIM LLM endpoint with curl
  3. Run vectorization pipeline for clinical notes
  4. Test vector similarity search
  5. Integrate with RAG application

${CYAN}Documentation:${NC}
  Deployment Guide:  docs/deployment-guide.md
  Troubleshooting:   docs/troubleshooting.md

EOF
}

# Main execution
main() {
    log_header "AWS GPU NIM RAG System Deployment"

    log_info "Starting automated deployment..."
    log_info "This process will take 10-15 minutes"
    echo ""

    # Step 0: Check prerequisites
    check_prerequisites

    # Step 1: Provision instance (if requested)
    if [[ "$PROVISION_INSTANCE" == "true" || -z "$INSTANCE_ID" ]]; then
        provision_ec2_instance
    else
        log_step "1" "Using existing instance"
        log_info "Instance ID: $INSTANCE_ID"
        log_info "Public IP: ${PUBLIC_IP:-<will retrieve>}"

        # Get public IP if not provided
        if [[ -z "$PUBLIC_IP" ]]; then
            PUBLIC_IP=$(aws ec2 describe-instances \
                --instance-ids "$INSTANCE_ID" \
                --query 'Reservations[0].Instances[0].PublicIpAddress' \
                --output text)
            log_success "Retrieved Public IP: $PUBLIC_IP"
        fi
        echo ""
    fi

    # Step 2: Install GPU drivers
    install_gpu_drivers

    # Step 3: Setup Docker GPU runtime
    setup_docker_gpu

    # Step 4: Deploy IRIS
    deploy_iris_database

    # Step 5: Deploy NIM LLM
    deploy_nim_llm

    # Step 6: Verify deployment
    verify_deployment

    # Display summary
    display_summary

    log_success "Deployment completed successfully!"
}

# Run main function
main
