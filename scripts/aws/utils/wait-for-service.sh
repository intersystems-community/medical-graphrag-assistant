#!/usr/bin/env bash
#
# Service Health Check Utility
#
# Polls a service URL until it responds with HTTP 200 or timeout expires.
# Useful for waiting for Docker containers and services to become healthy.
#
# Usage:
#   ./wait-for-service.sh <url> [timeout_seconds] [--quiet]
#
# Arguments:
#   url              Service URL to check (e.g., http://localhost:8001/health)
#   timeout_seconds  Maximum time to wait in seconds (default: 300)
#   --quiet          Suppress progress output
#
# Examples:
#   ./wait-for-service.sh http://localhost:8001/health 60
#   ./wait-for-service.sh http://localhost:1972 300 --quiet
#
# Exit codes:
#   0 - Service is healthy
#   1 - Invalid arguments
#   2 - Service did not become healthy within timeout

set -euo pipefail

# Colors for output
readonly GREEN='\033[0;32m'
readonly RED='\033[0;31m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m'

# Parse arguments
if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <url> [timeout_seconds] [--quiet]" >&2
    echo "" >&2
    echo "Examples:" >&2
    echo "  $0 http://localhost:8001/health" >&2
    echo "  $0 http://localhost:8001/v1/models 60" >&2
    echo "  $0 http://localhost:1972 300 --quiet" >&2
    exit 1
fi

readonly URL="$1"
readonly TIMEOUT="${2:-300}"  # Default 5 minutes
QUIET=false

# Check for --quiet flag
if [[ "${3:-}" == "--quiet" ]] || [[ "${2:-}" == "--quiet" ]]; then
    QUIET=true
fi

# Validate timeout is a number
if ! [[ "$TIMEOUT" =~ ^[0-9]+$ ]]; then
    echo -e "${RED}Error: timeout must be a number${NC}" >&2
    exit 1
fi

# Function to log (respects --quiet)
log() {
    if [[ "$QUIET" == "false" ]]; then
        echo -e "$1"
    fi
}

log_success() {
    if [[ "$QUIET" == "false" ]]; then
        echo -e "${GREEN}✓${NC} $1"
    fi
}

log_error() {
    echo -e "${RED}✗${NC} $1" >&2
}

log_info() {
    if [[ "$QUIET" == "false" ]]; then
        echo -e "${YELLOW}→${NC} $1"
    fi
}

# Check if curl is available
if ! command -v curl &> /dev/null; then
    log_error "curl is required but not installed"
    exit 1
fi

log_info "Waiting for service at ${URL}"
log_info "Timeout: ${TIMEOUT} seconds"

start_time=$(date +%s)
elapsed=0
attempt=0

while [[ $elapsed -lt $TIMEOUT ]]; do
    attempt=$((attempt + 1))

    # Try to connect to the service
    # -s: silent, -f: fail on HTTP errors, -o /dev/null: discard output
    # --max-time 5: timeout individual requests after 5 seconds
    # --connect-timeout 2: timeout connection after 2 seconds
    if curl -sf --max-time 5 --connect-timeout 2 "$URL" -o /dev/null 2>&1; then
        log_success "Service is healthy at ${URL}"
        log_info "Total wait time: ${elapsed} seconds (${attempt} attempts)"
        exit 0
    fi

    # Calculate elapsed time
    current_time=$(date +%s)
    elapsed=$((current_time - start_time))

    # Log progress every 10 seconds
    if [[ $((attempt % 10)) -eq 0 ]]; then
        remaining=$((TIMEOUT - elapsed))
        log "  Still waiting... (${elapsed}s elapsed, ${remaining}s remaining, attempt ${attempt})"
    fi

    # Wait 1 second before next attempt
    sleep 1
done

# Timeout reached
log_error "Service did not become healthy within ${TIMEOUT} seconds"
log_error "URL: ${URL}"
log_error "Total attempts: ${attempt}"

# Try one final time and show the error
log_info "Final connection attempt:"
if ! curl -sf --max-time 5 --connect-timeout 2 -v "$URL" 2>&1 | tail -10; then
    log_error "Connection failed"
fi

exit 2
