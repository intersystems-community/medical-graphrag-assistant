#!/usr/bin/env bash
#
# EC2 Instance Provisioning for FHIR AI Hackathon
#
# Provisions a g5.xlarge GPU instance with required security groups,
# EBS storage, and resource tags. Supports idempotency checks.
#
# Usage:
#   ./provision-instance.sh [--name <name>] [--region <region>] [--dry-run]
#
# Options:
#   --name <name>        Instance name (default: fhir-ai-hackathon)
#   --region <region>    AWS region (default: us-east-1 or AWS_REGION env var)
#   --dry-run            Show what would be created without creating it
#   --force              Skip idempotency check and create new instance
#
# Environment Variables:
#   AWS_REGION          AWS region (default: us-east-1)
#   SSH_KEY_NAME        Name of SSH key pair (required)
#   AWS_INSTANCE_TYPE   Instance type (default: g5.xlarge)
#
# Outputs:
#   Instance ID, Public IP, and connection details

set -euo pipefail

# Detect if output is to a terminal (disable colors if piped/captured)
if [[ -t 1 ]]; then
    # Colors for interactive terminal
    readonly RED='\033[0;31m'
    readonly GREEN='\033[0;32m'
    readonly YELLOW='\033[1;33m'
    readonly BLUE='\033[0;34m'
    readonly NC='\033[0m'
else
    # No colors when output is being captured
    readonly RED=''
    readonly GREEN=''
    readonly YELLOW=''
    readonly BLUE=''
    readonly NC=''
fi

# Default configuration
INSTANCE_NAME="${INSTANCE_NAME:-fhir-ai-hackathon}"
AWS_REGION="${AWS_REGION:-us-east-1}"
INSTANCE_TYPE="${AWS_INSTANCE_TYPE:-g5.xlarge}"
VOLUME_SIZE=500
VOLUME_TYPE="gp3"
DRY_RUN=false
FORCE=false

# Resource tags
readonly PROJECT_TAG="Project=FHIR-AI-Hackathon"
readonly MANAGED_BY_TAG="ManagedBy=deployment-automation"
readonly CREATED_BY_TAG="CreatedBy=$(whoami)"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --name)
            INSTANCE_NAME="$2"
            shift 2
            ;;
        --region)
            AWS_REGION="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --force)
            FORCE=true
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

# Validate required environment variables
if [[ -z "${SSH_KEY_NAME:-}" ]]; then
    echo -e "${RED}Error: SSH_KEY_NAME environment variable is required${NC}" >&2
    echo "Set it in your .env file or export it before running this script" >&2
    exit 1
fi

# Logging functions (all output to stderr to keep stdout clean)
log_info() {
    echo -e "${BLUE}→${NC} $1" >&2
}

log_success() {
    echo -e "${GREEN}✓${NC} $1" >&2
}

log_warn() {
    echo -e "${YELLOW}!${NC} $1" >&2
}

log_error() {
    echo -e "${RED}✗${NC} $1" >&2
}

log_dry_run() {
    echo -e "${YELLOW}[DRY RUN]${NC} $1" >&2
}

# Function to check for existing instances
check_existing_instances() {
    log_info "Checking for existing instances..."

    local existing_instances
    existing_instances=$(aws ec2 describe-instances \
        --region "$AWS_REGION" \
        --filters \
            "Name=tag:Name,Values=$INSTANCE_NAME" \
            "Name=tag:${PROJECT_TAG%%=*},Values=${PROJECT_TAG##*=}" \
            "Name=instance-state-name,Values=running,pending,stopping,stopped" \
        --query 'Reservations[*].Instances[*].[InstanceId,State.Name,PublicIpAddress,InstanceType]' \
        --output text 2>/dev/null || true)

    if [[ -n "$existing_instances" ]]; then
        echo "" >&2
        echo "Found existing instances:" >&2
        echo "$existing_instances" | while read -r instance_id state public_ip instance_type; do
            echo "  Instance ID:   $instance_id" >&2
            echo "  State:         $state" >&2
            echo "  Public IP:     ${public_ip:-N/A}" >&2
            echo "  Instance Type: $instance_type" >&2
            echo "" >&2
        done

        if [[ "$FORCE" != "true" ]]; then
            log_warn "Use --force to create a new instance anyway"
            return 1
        else
            log_warn "Force flag set, will create new instance"
            return 0
        fi
    fi

    return 0
}

# Function to get latest Ubuntu 24.04 LTS AMI
get_ubuntu_ami() {
    log_info "Finding Ubuntu 24.04 LTS AMI in $AWS_REGION..."

    local ami_id
    ami_id=$(aws ec2 describe-images \
        --region "$AWS_REGION" \
        --owners 099720109477 \
        --filters \
            'Name=name,Values=ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*' \
            'Name=state,Values=available' \
        --query 'Images | sort_by(@, &CreationDate) | [-1].ImageId' \
        --output text)

    if [[ -z "$ami_id" || "$ami_id" == "None" ]]; then
        log_error "Failed to find Ubuntu 24.04 LTS AMI"
        return 1
    fi

    log_success "Found AMI: $ami_id"
    echo "$ami_id"
}

# Function to create security group
create_security_group() {
    local sg_name="$INSTANCE_NAME-sg"

    log_info "Creating security group: $sg_name..."

    # Check if security group already exists
    local existing_sg
    existing_sg=$(aws ec2 describe-security-groups \
        --region "$AWS_REGION" \
        --filters \
            "Name=group-name,Values=$sg_name" \
            "Name=tag:${PROJECT_TAG%%=*},Values=${PROJECT_TAG##*=}" \
        --query 'SecurityGroups[0].GroupId' \
        --output text 2>/dev/null || echo "None")

    if [[ "$existing_sg" != "None" && -n "$existing_sg" ]]; then
        log_success "Security group already exists: $existing_sg"
        echo "$existing_sg"
        return 0
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        log_dry_run "Would create security group: $sg_name"
        log_dry_run "Would allow ports: 22 (SSH), 1972 (IRIS SQL), 52773 (IRIS Management), 8000 (NIM Embeddings), 8001 (NIM LLM)"
        echo "sg-dryrun"
        return 0
    fi

    # Create security group
    local sg_id
    sg_id=$(aws ec2 create-security-group \
        --region "$AWS_REGION" \
        --group-name "$sg_name" \
        --description "Security group for FHIR AI Hackathon deployment" \
        --tag-specifications "ResourceType=security-group,Tags=[{Key=Name,Value=$sg_name},{Key=${PROJECT_TAG%%=*},Value=${PROJECT_TAG##*=}},{Key=${MANAGED_BY_TAG%%=*},Value=${MANAGED_BY_TAG##*=}}]" \
        --query 'GroupId' \
        --output text)

    log_success "Created security group: $sg_id"

    # Add ingress rules
    log_info "Configuring security group rules..."

    # SSH (port 22)
    aws ec2 authorize-security-group-ingress \
        --region "$AWS_REGION" \
        --group-id "$sg_id" \
        --protocol tcp \
        --port 22 \
        --cidr 0.0.0.0/0 \
        --tag-specifications "ResourceType=security-group-rule,Tags=[{Key=Description,Value=SSH access}]" \
        > /dev/null

    # IRIS SQL port (1972)
    aws ec2 authorize-security-group-ingress \
        --region "$AWS_REGION" \
        --group-id "$sg_id" \
        --protocol tcp \
        --port 1972 \
        --cidr 0.0.0.0/0 \
        --tag-specifications "ResourceType=security-group-rule,Tags=[{Key=Description,Value=IRIS SQL}]" \
        > /dev/null

    # IRIS Management Portal (52773)
    aws ec2 authorize-security-group-ingress \
        --region "$AWS_REGION" \
        --group-id "$sg_id" \
        --protocol tcp \
        --port 52773 \
        --cidr 0.0.0.0/0 \
        --tag-specifications "ResourceType=security-group-rule,Tags=[{Key=Description,Value=IRIS Management}]" \
        > /dev/null

    # NIM Embeddings (8000)
    aws ec2 authorize-security-group-ingress \
        --region "$AWS_REGION" \
        --group-id "$sg_id" \
        --protocol tcp \
        --port 8000 \
        --cidr 0.0.0.0/0 \
        --tag-specifications "ResourceType=security-group-rule,Tags=[{Key=Description,Value=NIM Embeddings}]" \
        > /dev/null

    # NIM LLM (8001)
    aws ec2 authorize-security-group-ingress \
        --region "$AWS_REGION" \
        --group-id "$sg_id" \
        --protocol tcp \
        --port 8001 \
        --cidr 0.0.0.0/0 \
        --tag-specifications "ResourceType=security-group-rule,Tags=[{Key=Description,Value=NIM LLM}]" \
        > /dev/null

    log_success "Security group configured with all required ports"

    echo "$sg_id"
}

# Function to launch EC2 instance
launch_instance() {
    local ami_id="$1"
    local sg_id="$2"

    log_info "Launching $INSTANCE_TYPE instance in $AWS_REGION..."

    if [[ "$DRY_RUN" == "true" ]]; then
        log_dry_run "Would launch instance:"
        log_dry_run "  Name:          $INSTANCE_NAME"
        log_dry_run "  Instance Type: $INSTANCE_TYPE"
        log_dry_run "  AMI:           $ami_id"
        log_dry_run "  Security Group: $sg_id"
        log_dry_run "  SSH Key:       $SSH_KEY_NAME"
        log_dry_run "  Region:        $AWS_REGION"
        echo "i-dryrun12345"
        return 0
    fi

    # Launch instance
    local instance_id
    instance_id=$(aws ec2 run-instances \
        --region "$AWS_REGION" \
        --image-id "$ami_id" \
        --instance-type "$INSTANCE_TYPE" \
        --key-name "$SSH_KEY_NAME" \
        --security-group-ids "$sg_id" \
        --block-device-mappings "[{\"DeviceName\":\"/dev/sda1\",\"Ebs\":{\"VolumeSize\":$VOLUME_SIZE,\"VolumeType\":\"$VOLUME_TYPE\",\"DeleteOnTermination\":true}}]" \
        --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$INSTANCE_NAME},{Key=${PROJECT_TAG%%=*},Value=${PROJECT_TAG##*=}},{Key=${MANAGED_BY_TAG%%=*},Value=${MANAGED_BY_TAG##*=}},{Key=${CREATED_BY_TAG%%=*},Value=${CREATED_BY_TAG##*=}}]" \
        --query 'Instances[0].InstanceId' \
        --output text)

    log_success "Instance launched: $instance_id"

    # Wait for instance to be running
    log_info "Waiting for instance to be running..."
    aws ec2 wait instance-running \
        --region "$AWS_REGION" \
        --instance-ids "$instance_id"

    log_success "Instance is now running"

    echo "$instance_id"
}

# Function to get instance details
get_instance_details() {
    local instance_id="$1"

    if [[ "$DRY_RUN" == "true" ]]; then
        echo "203.0.113.1"  # TEST-NET-3 (RFC 5737)
        return 0
    fi

    local public_ip
    public_ip=$(aws ec2 describe-instances \
        --region "$AWS_REGION" \
        --instance-ids "$instance_id" \
        --query 'Reservations[0].Instances[0].PublicIpAddress' \
        --output text)

    echo "$public_ip"
}

# Main execution
main() {
    log_info "FHIR AI Hackathon - EC2 Instance Provisioning"
    echo "" >&2

    if [[ "$DRY_RUN" == "true" ]]; then
        log_warn "DRY RUN MODE - No resources will be created"
        echo "" >&2
    fi

    # Check for existing instances (unless force flag is set)
    if ! check_existing_instances; then
        exit 0
    fi

    # Get Ubuntu AMI
    ami_id=$(get_ubuntu_ami)

    # Create security group
    sg_id=$(create_security_group)

    # Launch instance
    instance_id=$(launch_instance "$ami_id" "$sg_id")

    # Get instance details
    public_ip=$(get_instance_details "$instance_id")

    # Display summary
    echo "" >&2
    echo "==========================================" >&2
    echo "Instance Provisioned Successfully" >&2
    echo "==========================================" >&2
    echo "  Instance ID:   $instance_id" >&2
    echo "  Instance Type: $INSTANCE_TYPE" >&2
    echo "  Public IP:     $public_ip" >&2
    echo "  Region:        $AWS_REGION" >&2
    echo "  SSH Key:       $SSH_KEY_NAME" >&2
    echo "" >&2
    echo "Connection command:" >&2
    echo "  ssh -i ~/.ssh/$SSH_KEY_NAME.pem ubuntu@$public_ip" >&2
    echo "" >&2
    echo "Next steps:" >&2
    echo "  1. Wait 2-3 minutes for instance to fully boot" >&2
    echo "  2. Run: ./scripts/aws/install-gpu-drivers.sh" >&2
    echo "  3. Run: ./scripts/aws/setup-docker-gpu.sh" >&2
    echo "  4. Run: ./scripts/aws/deploy-iris.sh" >&2
    echo "  5. Run: ./scripts/aws/deploy-nim-llm.sh" >&2
    echo "" >&2
    echo "Or use the automated deployment:" >&2
    echo "  ./scripts/aws/deploy.sh" >&2
    echo "==========================================" >&2

    # Save instance info to file for later use
    if [[ "$DRY_RUN" != "true" ]]; then
        cat > .instance-info <<EOF
INSTANCE_ID=$instance_id
PUBLIC_IP=$public_ip
INSTANCE_TYPE=$INSTANCE_TYPE
AWS_REGION=$AWS_REGION
SSH_KEY_NAME=$SSH_KEY_NAME
SECURITY_GROUP_ID=$sg_id
EOF
        log_success "Instance info saved to .instance-info"
    fi
}

# Run main function
main
