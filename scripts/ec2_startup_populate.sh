#!/bin/bash
# EC2 Startup Script - Populate GraphRAG data on deployment
# This script is designed to be called from Docker entrypoint or systemd service

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="/var/log/graphrag-populate.log"
LOCK_FILE="/tmp/graphrag-populate.lock"

# Use lock file to prevent duplicate runs
if [ -f "$LOCK_FILE" ]; then
    echo "Population already in progress or completed (lock file exists)"
    exit 0
fi

# Redirect output to log file
exec > >(tee -a "$LOG_FILE") 2>&1

echo "=================================="
echo "GraphRAG Data Population - $(date)"
echo "=================================="

# Create lock file
touch "$LOCK_FILE"

# Wait for IRIS to be ready
echo "Waiting for IRIS FHIR endpoint to be ready..."
MAX_WAIT=180
WAITED=0
FHIR_URL="${FHIR_BASE_URL:-http://localhost:32783/csp/healthshare/demo/fhir/r4}"

while [ $WAITED -lt $MAX_WAIT ]; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${FHIR_URL}/metadata" 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
        echo "FHIR endpoint is ready (HTTP $HTTP_CODE)"
        break
    fi
    echo "Waiting for FHIR endpoint (HTTP $HTTP_CODE)... ${WAITED}s/${MAX_WAIT}s"
    sleep 10
    WAITED=$((WAITED + 10))
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo "ERROR: FHIR endpoint not ready after ${MAX_WAIT}s"
    rm -f "$LOCK_FILE"
    exit 1
fi

# Check if data already exists
echo "Checking existing data..."
PATIENT_COUNT=$(curl -s "${FHIR_URL}/Patient?_summary=count" 2>/dev/null | grep -o '"total":[0-9]*' | grep -o '[0-9]*' || echo "0")
echo "Existing patients: $PATIENT_COUNT"

if [ "$PATIENT_COUNT" -ge 50 ]; then
    echo "Data already populated ($PATIENT_COUNT patients). Skipping population."
    exit 0
fi

# Run population script
echo "Running data population script..."
cd "$PROJECT_DIR"

# Activate virtual environment if it exists
if [ -f ~/medical-graphrag/venv/bin/activate ]; then
    source ~/medical-graphrag/venv/bin/activate
fi

# Set environment variables
export FHIR_BASE_URL="${FHIR_URL}"
export USE_REMOTE_IRIS="false"  # Running locally on the EC2

python scripts/populate_full_graphrag_data.py

RESULT=$?
if [ $RESULT -eq 0 ]; then
    echo "Data population completed successfully!"
else
    echo "Data population completed with warnings (exit code: $RESULT)"
fi

echo "=================================="
echo "Population finished - $(date)"
echo "=================================="

exit $RESULT
