#!/usr/bin/env bash
#
# Resource Cleanup Utility
#
# Safely terminates EC2 instances, removes Docker containers, and cleans up
# resources based on deployment tags. Use this to tear down a deployment.
#
# Usage:
#   ./cleanup.sh [--instance-id <id>] [--all] [--dry-run] [--force]
#
# Options:
#   --instance-id <id>  Clean up specific EC2 instance
#   --all               Clean up all resources with deployment tags
#   --dry-run           Show what would be cleaned up without doing it
#   --force             Skip confirmation prompts
#
# Examples:
#   ./cleanup.sh --instance-id i-1234567890abcdef0
#   ./cleanup.sh --all --dry-run
#   ./cleanup.sh --all --force
#
# Safety Features:
#   - Requires confirmation before destructive operations
#   - Supports dry-run mode
#   - Tags-based filtering to avoid accidental deletion
#   - Graceful container shutdown before removal

set -euo pipefail

# Colors
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

# Configuration
readonly PROJECT_TAG="Project=FHIR-AI-Hackathon"
readonly MANAGED_BY_TAG="ManagedBy=deployment-automation"

# Flags
INSTANCE_ID=""
CLEANUP_ALL=false
DRY_RUN=false
FORCE=false

# Parse arguments
while [[ $# -gt 0 ]]; then
    case "$1" in
        --instance-id)
            INSTANCE_ID="$2"
            shift 2
            ;;
        --all)
            CLEANUP_ALL=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        *)
            echo "Unknown option: $1" >&2
            echo "Usage: $0 [--instance-id <id>] [--all] [--dry-run] [--force]" >&2
            exit 1
            ;;
    esac
done

# Validate arguments
if [[ -z "$INSTANCE_ID" ]] && [[ "$CLEANUP_ALL" == "false" ]]; then
    echo "Error: Must specify either --instance-id or --all" >&2
    echo "Usage: $0 [--instance-id <id>] [--all] [--dry-run] [--force]" >&2
    exit 1
fi

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

log_dry_run() {
    echo -e "${YELLOW}[DRY RUN]${NC} $1"
}

# Function to confirm action
confirm() {
    local message="$1"

    if [[ "$FORCE" == "true" ]]; then
        return 0
    fi

    echo -en "${YELLOW}?${NC} ${message} (yes/no): "
    read -r response

    if [[ "$response" != "yes" ]]; then
        log_warn "Operation cancelled"
        return 1
    fi
    return 0
}

# Function to get instances
get_instances() {
    if [[ -n "$INSTANCE_ID" ]]; then
        echo "$INSTANCE_ID"
    else
        # Get all instances with our tags
        aws ec2 describe-instances \
            --filters \
                "Name=tag:${PROJECT_TAG%%=*},Values=${PROJECT_TAG##*=}" \
                "Name=tag:${MANAGED_BY_TAG%%=*},Values=${MANAGED_BY_TAG##*=}" \
                "Name=instance-state-name,Values=running,stopped,stopping" \
            --query 'Reservations[*].Instances[*].InstanceId' \
            --output text || true
    fi
}

# Function to cleanup Docker containers on remote instance
cleanup_docker_containers() {
    local instance_ip="$1"
    local ssh_key="${SSH_KEY_PATH:-./fhir-ai-key.pem}"

    log_info "Cleaning up Docker containers on ${instance_ip}"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_dry_run "Would stop and remove Docker containers: iris-fhir, nim-llm, nim-embeddings, nim-vision"
        return 0
    fi

    # SSH into instance and cleanup containers
    ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i "$ssh_key" "ubuntu@${instance_ip}" << 'EOF' || true
        echo "Stopping Docker containers..."

        # Stop containers gracefully (30 second timeout)
        for container in iris-fhir nim-llm nim-embeddings nim-vision; do
            if docker ps -a --format '{{.Names}}' | grep -q "^${container}$"; then
                echo "  Stopping ${container}..."
                docker stop -t 30 "$container" 2>/dev/null || true
            fi
        done

        # Remove containers
        echo "Removing Docker containers..."
        for container in iris-fhir nim-llm nim-embeddings nim-vision; do
            if docker ps -a --format '{{.Names}}' | grep -q "^${container}$"; then
                echo "  Removing ${container}..."
                docker rm "$container" 2>/dev/null || true
            fi
        done

        echo "Docker cleanup complete"
EOF

    if [[ $? -eq 0 ]]; then
        log_success "Docker containers cleaned up"
    else
        log_warn "Could not connect to instance or cleanup failed (instance may already be terminated)"
    fi
}

# Function to terminate EC2 instance
terminate_instance() {
    local instance_id="$1"

    log_info "Terminating EC2 instance: ${instance_id}"

    # Get instance details
    instance_details=$(aws ec2 describe-instances \
        --instance-ids "$instance_id" \
        --query 'Reservations[0].Instances[0].[PublicIpAddress,InstanceType,State.Name]' \
        --output text 2>/dev/null || echo "unknown unknown unknown")

    read -r public_ip instance_type state <<< "$instance_details"

    echo "  IP Address:     ${public_ip:-N/A}"
    echo "  Instance Type:  ${instance_type}"
    echo "  Current State:  ${state}"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_dry_run "Would terminate instance ${instance_id}"
        return 0
    fi

    # Cleanup Docker containers if instance is accessible
    if [[ "$state" == "running" ]] && [[ -n "$public_ip" ]] && [[ "$public_ip" != "None" ]]; then
        cleanup_docker_containers "$public_ip"
    fi

    # Terminate instance
    if aws ec2 terminate-instances --instance-ids "$instance_id" &>/dev/null; then
        log_success "Instance ${instance_id} terminated"
    else
        log_error "Failed to terminate instance ${instance_id}"
        return 1
    fi
}

# Function to cleanup security groups
cleanup_security_groups() {
    log_info "Looking for security groups to cleanup"

    # Find security groups with our tags
    sg_ids=$(aws ec2 describe-security-groups \
        --filters \
            "Name=tag:${PROJECT_TAG%%=*},Values=${PROJECT_TAG##*=}" \
            "Name=tag:${MANAGED_BY_TAG%%=*},Values=${MANAGED_BY_TAG##*=}" \
        --query 'SecurityGroups[*].GroupId' \
        --output text || true)

    if [[ -z "$sg_ids" ]]; then
        log_info "No security groups found"
        return 0
    fi

    for sg_id in $sg_ids; do
        sg_name=$(aws ec2 describe-security-groups \
            --group-ids "$sg_id" \
            --query 'SecurityGroups[0].GroupName' \
            --output text)

        if [[ "$DRY_RUN" == "true" ]]; then
            log_dry_run "Would delete security group: ${sg_id} (${sg_name})"
        else
            log_info "Deleting security group: ${sg_id} (${sg_name})"

            # Wait a bit for instances to fully terminate
            sleep 5

            if aws ec2 delete-security-group --group-id "$sg_id" 2>/dev/null; then
                log_success "Security group ${sg_id} deleted"
            else
                log_warn "Could not delete security group ${sg_id} (may still be in use)"
            fi
        fi
    done
}

# Function to cleanup EBS volumes
cleanup_ebs_volumes() {
    log_info "Looking for unattached EBS volumes to cleanup"

    # Find available (unattached) volumes with our tags
    volume_ids=$(aws ec2 describe-volumes \
        --filters \
            "Name=tag:${PROJECT_TAG%%=*},Values=${PROJECT_TAG##*=}" \
            "Name=tag:${MANAGED_BY_TAG%%=*},Values=${MANAGED_BY_TAG##*=}" \
            "Name=status,Values=available" \
        --query 'Volumes[*].VolumeId' \
        --output text || true)

    if [[ -z "$volume_ids" ]]; then
        log_info "No unattached volumes found"
        return 0
    fi

    for volume_id in $volume_ids; do
        volume_size=$(aws ec2 describe-volumes \
            --volume-ids "$volume_id" \
            --query 'Volumes[0].Size' \
            --output text)

        if [[ "$DRY_RUN" == "true" ]]; then
            log_dry_run "Would delete volume: ${volume_id} (${volume_size}GB)"
        else
            log_info "Deleting volume: ${volume_id} (${volume_size}GB)"

            if aws ec2 delete-volume --volume-id "$volume_id" 2>/dev/null; then
                log_success "Volume ${volume_id} deleted"
            else
                log_warn "Could not delete volume ${volume_id}"
            fi
        fi
    done
}

# Main cleanup logic
main() {
    log_info "FHIR AI Hackathon Deployment Cleanup"
    echo ""

    if [[ "$DRY_RUN" == "true" ]]; then
        log_warn "DRY RUN MODE - No resources will be modified"
        echo ""
    fi

    # Get instances to cleanup
    instances=$(get_instances)

    if [[ -z "$instances" ]]; then
        log_warn "No instances found to cleanup"
        return 0
    fi

    # Count instances
    instance_count=$(echo "$instances" | wc -w)

    # Show summary
    echo "Found ${instance_count} instance(s) to cleanup:"
    for id in $instances; do
        echo "  - $id"
    done
    echo ""

    # Confirm if not in force mode
    if ! confirm "Proceed with cleanup of ${instance_count} instance(s)?"; then
        return 1
    fi

    echo ""

    # Terminate instances
    for instance_id in $instances; do
        terminate_instance "$instance_id"
        echo ""
    done

    # Wait for instances to terminate
    if [[ "$DRY_RUN" == "false" ]] && [[ -n "$instances" ]]; then
        log_info "Waiting for instances to terminate..."
        aws ec2 wait instance-terminated --instance-ids $instances || true
        log_success "All instances terminated"
        echo ""
    fi

    # Cleanup security groups
    cleanup_security_groups
    echo ""

    # Cleanup EBS volumes
    cleanup_ebs_volumes
    echo ""

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "Dry run complete - no resources were modified"
    else
        log_success "Cleanup complete!"
    fi
}

# Run main function
main
