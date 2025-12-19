#!/bin/bash
# ============================================================================
# MIMIC-CXR Environment Setup Script (Feature 009)
# ============================================================================
# This script sets up the complete MIMIC-CXR medical imaging environment:
#   1. Rebuilds the FHIR container with proper configuration
#   2. Creates the VectorSearch.MIMICCXRImages table
#   3. Ingests MIMIC-CXR images with NV-CLIP embeddings
#   4. Creates FHIR Patient resources for MIMIC subjects
#
# Usage:
#   ./scripts/setup_mimic_cxr_environment.sh [OPTIONS]
#
# Options:
#   --skip-rebuild       Skip Docker container rebuild
#   --skip-ingest        Skip MIMIC-CXR image ingestion
#   --skip-patients      Skip FHIR Patient creation
#   --limit N            Limit image ingestion to N images
#   --mimic-path PATH    Path to MIMIC-CXR data (default: ~/mimic-cxr-data)
#   --dry-run            Preview what would be done without executing
#
# Environment Variables (defaults shown):
#   FHIR_PORT=32783      FHIR web port
#   IRIS_PORT=32782      IRIS SuperServer port
#   FHIR_USER=_SYSTEM    FHIR username
#   FHIR_PASS=SYS        FHIR password (UPPERCASE required)
#
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration defaults
SKIP_REBUILD=false
SKIP_INGEST=false
SKIP_PATIENTS=false
SKIP_GRAPHRAG=false
DRY_RUN=false
LIMIT=""
MIMIC_PATH="${HOME}/mimic-cxr-data"
FHIR_PORT="${FHIR_PORT:-32783}"
IRIS_PORT="${IRIS_PORT:-32782}"
FHIR_USER="${FHIR_USER:-_SYSTEM}"
FHIR_PASS="${FHIR_PASS:-SYS}"

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-rebuild)
            SKIP_REBUILD=true
            shift
            ;;
        --skip-ingest)
            SKIP_INGEST=true
            shift
            ;;
        --skip-patients)
            SKIP_PATIENTS=true
            shift
            ;;
        --skip-graphrag)
            SKIP_GRAPHRAG=true
            shift
            ;;
        --limit)
            LIMIT="$2"
            shift 2
            ;;
        --mimic-path)
            MIMIC_PATH="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            head -35 "$0" | tail -30
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${GREEN}========================================${NC}\n"
}

# Check prerequisites
check_prerequisites() {
    log_step "Step 0: Checking Prerequisites"

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    log_info "Docker: OK"

    # Check curl
    if ! command -v curl &> /dev/null; then
        log_error "curl is not installed"
        exit 1
    fi
    log_info "curl: OK"

    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed"
        exit 1
    fi
    log_info "Python 3: OK"

    # Check MIMIC data path
    if [[ ! -d "$MIMIC_PATH" ]]; then
        log_warn "MIMIC-CXR data path not found: $MIMIC_PATH"
        if [[ "$SKIP_INGEST" != "true" ]]; then
            log_error "Either provide --mimic-path or use --skip-ingest"
            exit 1
        fi
    else
        DICOM_COUNT=$(find "$MIMIC_PATH" -name "*.dcm" 2>/dev/null | wc -l)
        log_info "MIMIC data path: $MIMIC_PATH ($DICOM_COUNT DICOM files)"
    fi

    # Check project structure
    if [[ ! -f "$PROJECT_ROOT/Dockerfhir/docker-compose.yaml" ]]; then
        log_error "Project structure not found. Run from project root."
        exit 1
    fi
    log_info "Project root: $PROJECT_ROOT"

    log_success "Prerequisites check passed"
}

# Step 1: Rebuild FHIR container
rebuild_fhir_container() {
    log_step "Step 1: Rebuilding FHIR Container"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would rebuild FHIR container"
        return
    fi

    cd "$PROJECT_ROOT/Dockerfhir"

    log_info "Stopping existing container..."
    docker compose down -v 2>/dev/null || true

    log_info "Building container..."
    docker compose build --no-cache 2>&1 | tail -20

    log_info "Starting container..."
    docker compose up -d

    log_info "Waiting for FHIR server initialization (90 seconds)..."
    for i in $(seq 1 18); do
        echo -n "."
        sleep 5
    done
    echo ""

    # Verify FHIR is up
    FHIR_URL="http://localhost:${FHIR_PORT}/csp/healthshare/demo/fhir/r4/metadata"
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -u "${FHIR_USER}:${FHIR_PASS}" "$FHIR_URL" 2>/dev/null || echo "000")

    if [[ "$HTTP_CODE" == "200" ]]; then
        log_success "FHIR server is ready (HTTP $HTTP_CODE)"
    else
        log_error "FHIR server not responding (HTTP $HTTP_CODE)"
        log_info "Check container logs: docker compose logs iris-fhir"
        exit 1
    fi

    cd "$PROJECT_ROOT"
}

# Step 2: Create VectorSearch table (handled by ingestion script)
create_vectorsearch_table() {
    log_step "Step 2: VectorSearch Table"
    log_info "VectorSearch.MIMICCXRImages table will be auto-created during ingestion"
}

# Step 3: Ingest MIMIC-CXR images
ingest_mimic_images() {
    log_step "Step 3: Ingesting MIMIC-CXR Images"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would ingest MIMIC-CXR images from $MIMIC_PATH"
        return
    fi

    cd "$PROJECT_ROOT"

    # Build command
    INGEST_CMD="python scripts/ingest_mimic_cxr.py --source '$MIMIC_PATH' --batch-size 32"
    if [[ -n "$LIMIT" ]]; then
        INGEST_CMD="$INGEST_CMD --limit $LIMIT"
    fi

    log_info "Running: $INGEST_CMD"

    # Set environment variables
    export NVCLIP_BASE_URL="${NVCLIP_BASE_URL:-http://localhost:8002/v1}"
    export IRIS_HOST="${IRIS_HOST:-localhost}"
    export IRIS_PORT="${IRIS_PORT:-32782}"

    # Activate venv if available
    if [[ -f "${HOME}/medical-graphrag/venv/bin/activate" ]]; then
        source "${HOME}/medical-graphrag/venv/bin/activate"
    fi

    # Run ingestion
    eval "$INGEST_CMD"

    log_success "MIMIC-CXR image ingestion complete"
}

# Step 4: Create FHIR Patient resources
create_fhir_patients() {
    log_step "Step 4: Creating FHIR Patient Resources"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would create FHIR Patient resources"
        return
    fi

    FHIR_URL="http://localhost:${FHIR_PORT}/csp/healthshare/demo/fhir/r4/Patient"

    # Extract unique subjects from MIMIC data path
    log_info "Extracting unique MIMIC subjects..."
    SUBJECTS_FILE="/tmp/mimic_subjects_$$.txt"

    find "$MIMIC_PATH" -type d -name "p*" | \
        grep -oE 'p[0-9]{8}' | \
        sort -u > "$SUBJECTS_FILE"

    TOTAL=$(wc -l < "$SUBJECTS_FILE")
    log_info "Found $TOTAL unique subjects"

    if [[ "$TOTAL" -eq 0 ]]; then
        log_warn "No subjects found in $MIMIC_PATH"
        rm -f "$SUBJECTS_FILE"
        return
    fi

    # Create patients (IDEMPOTENT - checks for existing before creating)
    SUCCESS=0
    SKIPPED=0
    FAILED=0
    COUNTER=0

    while IFS= read -r SUBJECT_ID; do
        COUNTER=$((COUNTER + 1))

        # Check if patient already exists (IDEMPOTENCY CHECK)
        SEARCH_URL="${FHIR_URL}?identifier=urn:mimic-cxr:subject|${SUBJECT_ID}"
        EXISTING=$(curl -s -u "${FHIR_USER}:${FHIR_PASS}" "$SEARCH_URL" 2>/dev/null | grep -o '"total":[0-9]*' | grep -o '[0-9]*' || echo "0")

        if [[ "$EXISTING" -gt 0 ]]; then
            SKIPPED=$((SKIPPED + 1))
            # Progress report every 100 (including skipped)
            if [[ $((COUNTER % 100)) -eq 0 ]]; then
                log_info "Progress: $COUNTER/$TOTAL (Created: $SUCCESS, Skipped: $SKIPPED, Failed: $FAILED)"
            fi
            continue
        fi

        # Create patient JSON
        PATIENT_JSON=$(cat <<EOF
{
  "resourceType": "Patient",
  "identifier": [{
    "system": "urn:mimic-cxr:subject",
    "value": "$SUBJECT_ID"
  }],
  "active": true,
  "name": [{
    "use": "official",
    "family": "MIMIC-CXR",
    "given": ["Subject-$SUBJECT_ID"]
  }],
  "gender": "unknown"
}
EOF
)

        # POST to FHIR server
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
            -X POST \
            -u "${FHIR_USER}:${FHIR_PASS}" \
            -H "Content-Type: application/fhir+json" \
            "$FHIR_URL" \
            -d "$PATIENT_JSON" 2>/dev/null || echo "000")

        if [[ "$HTTP_CODE" == "201" ]] || [[ "$HTTP_CODE" == "200" ]]; then
            SUCCESS=$((SUCCESS + 1))
        else
            FAILED=$((FAILED + 1))
        fi

        # Progress report every 100
        if [[ $((COUNTER % 100)) -eq 0 ]]; then
            log_info "Progress: $COUNTER/$TOTAL (Created: $SUCCESS, Skipped: $SKIPPED, Failed: $FAILED)"
        fi

    done < "$SUBJECTS_FILE"

    rm -f "$SUBJECTS_FILE"

    log_success "FHIR Patient creation complete: $SUCCESS created, $SKIPPED skipped (already exist), $FAILED failed"
}

# Step 5: Populate GraphRAG tables
populate_graphrag_tables() {
    log_step "Step 5: Populating GraphRAG Knowledge Graph Tables"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would populate GraphRAG tables"
        return
    fi

    cd "$PROJECT_ROOT"

    # Activate venv if available
    if [[ -f "${HOME}/medical-graphrag/venv/bin/activate" ]]; then
        source "${HOME}/medical-graphrag/venv/bin/activate"
    fi

    # Set environment variables
    export IRIS_HOST="${IRIS_HOST:-localhost}"
    export IRIS_PORT="${IRIS_PORT:-32782}"

    log_info "Running GraphRAG population script..."
    python scripts/populate_graphrag_tables.py

    if [[ $? -eq 0 ]]; then
        log_success "GraphRAG tables populated successfully"
    else
        log_warn "GraphRAG population completed with warnings (may already exist)"
    fi
}

# Step 6: Verify setup
verify_setup() {
    log_step "Step 6: Verifying Setup"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would verify setup"
        return
    fi

    # Check FHIR Patient count
    FHIR_URL="http://localhost:${FHIR_PORT}/csp/healthshare/demo/fhir/r4/Patient?_summary=count"
    PATIENT_COUNT=$(curl -s -u "${FHIR_USER}:${FHIR_PASS}" "$FHIR_URL" 2>/dev/null | grep -o '"total":[0-9]*' | grep -o '[0-9]*' || echo "0")
    log_info "FHIR Patients: $PATIENT_COUNT"

    # Check VectorSearch table (via Python)
    cd "$PROJECT_ROOT"
    if [[ -f "${HOME}/medical-graphrag/venv/bin/activate" ]]; then
        source "${HOME}/medical-graphrag/venv/bin/activate"
    fi

    export IRIS_HOST="${IRIS_HOST:-localhost}"
    export IRIS_PORT="${IRIS_PORT:-32782}"

    VECTOR_COUNT=$(python3 -c "
from src.db.connection import get_connection
conn = get_connection()
cursor = conn.cursor()
try:
    cursor.execute('SELECT COUNT(*) FROM VectorSearch.MIMICCXRImages')
    print(cursor.fetchone()[0])
except:
    print('0')
finally:
    cursor.close()
    conn.close()
" 2>/dev/null || echo "0")

    log_info "VectorSearch Images: $VECTOR_COUNT"

    echo ""
    log_success "Environment setup complete!"
    echo ""
    echo "Summary:"
    echo "  - FHIR Patients: $PATIENT_COUNT"
    echo "  - Vector Embeddings: $VECTOR_COUNT"
    echo ""
    echo "FHIR Endpoint: http://localhost:${FHIR_PORT}/csp/healthshare/demo/fhir/r4"
    echo "Streamlit App: Run 'cd mcp-server && streamlit run streamlit_app.py'"
}

# Main execution
main() {
    echo ""
    echo "============================================"
    echo "MIMIC-CXR Environment Setup"
    echo "============================================"
    echo ""
    echo "Configuration:"
    echo "  MIMIC Path:     $MIMIC_PATH"
    echo "  FHIR Port:      $FHIR_PORT"
    echo "  IRIS Port:      $IRIS_PORT"
    echo "  Skip Rebuild:   $SKIP_REBUILD"
    echo "  Skip Ingest:    $SKIP_INGEST"
    echo "  Skip Patients:  $SKIP_PATIENTS"
    echo "  Skip GraphRAG:  $SKIP_GRAPHRAG"
    echo "  Limit:          ${LIMIT:-None}"
    echo "  Dry Run:        $DRY_RUN"
    echo ""

    check_prerequisites

    if [[ "$SKIP_REBUILD" != "true" ]]; then
        rebuild_fhir_container
    else
        log_info "Skipping container rebuild (--skip-rebuild)"
    fi

    create_vectorsearch_table

    if [[ "$SKIP_INGEST" != "true" ]]; then
        ingest_mimic_images
    else
        log_info "Skipping image ingestion (--skip-ingest)"
    fi

    if [[ "$SKIP_PATIENTS" != "true" ]]; then
        create_fhir_patients
    else
        log_info "Skipping FHIR Patient creation (--skip-patients)"
    fi

    if [[ "$SKIP_GRAPHRAG" != "true" ]]; then
        populate_graphrag_tables
    else
        log_info "Skipping GraphRAG population (--skip-graphrag)"
    fi

    verify_setup
}

# Run main
main
