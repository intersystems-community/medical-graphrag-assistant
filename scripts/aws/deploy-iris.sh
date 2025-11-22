#!/usr/bin/env bash
#
# InterSystems IRIS Database Deployment
#
# Deploys IRIS Community 2025.1 with vector database support.
# Creates persistent volumes, configures namespace, and creates vector tables.
#
# Usage:
#   ./deploy-iris.sh [--remote <host>] [--ssh-key <path>]
#
# Options:
#   --remote <host>      Deploy on remote host via SSH
#   --ssh-key <path>     Path to SSH key for remote deployment
#   --skip-schema        Skip schema creation (only deploy container)
#   --force-recreate     Remove existing container and recreate
#
# Environment Variables:
#   PUBLIC_IP           Remote host IP (alternative to --remote)
#   SSH_KEY_PATH        Path to SSH key (alternative to --ssh-key)
#   IRIS_PASSWORD       SuperUser password (default: SYS)
#   IRIS_NAMESPACE      Namespace to create (default: DEMO)

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
SKIP_SCHEMA=false
FORCE_RECREATE=false
IRIS_PASSWORD="${IRIS_PASSWORD:-SYS}"
IRIS_NAMESPACE="${IRIS_NAMESPACE:-DEMO}"
CONTAINER_NAME="iris-vector-db"
IRIS_IMAGE="intersystemsdc/iris-community:latest"
IRIS_PORT_SQL=1972
IRIS_PORT_WEB=52773

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
        --skip-schema)
            SKIP_SCHEMA=true
            shift
            ;;
        --force-recreate)
            FORCE_RECREATE=true
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

# Function to deploy IRIS locally
deploy_iris_local() {
    log_info "Deploying InterSystems IRIS Vector Database..."

    # Check if container already exists
    if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        if [[ "$FORCE_RECREATE" == "true" ]]; then
            log_warn "Removing existing container..."
            docker stop "$CONTAINER_NAME" 2>/dev/null || true
            docker rm "$CONTAINER_NAME" 2>/dev/null || true
        else
            log_warn "Container $CONTAINER_NAME already exists"
            log_info "Use --force-recreate to remove and recreate"

            # Check if it's running
            if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
                log_success "Container is running"
                return 0
            else
                log_info "Starting existing container..."
                docker start "$CONTAINER_NAME"
                log_success "Container started"
                return 0
            fi
        fi
    fi

    # Pull IRIS image
    log_info "Pulling IRIS image: $IRIS_IMAGE..."
    docker pull "$IRIS_IMAGE"
    log_success "Image pulled"

    # Create Docker volume for persistence
    log_info "Creating persistent volume..."
    docker volume create iris-data 2>/dev/null || true
    log_success "Volume created"

    # Run IRIS container
    log_info "Starting IRIS container..."
    docker run -d \
        --name "$CONTAINER_NAME" \
        --restart unless-stopped \
        -p ${IRIS_PORT_SQL}:1972 \
        -p ${IRIS_PORT_WEB}:52773 \
        -v iris-data:/usr/irissys/mgr \
        -e IRIS_PASSWORD="$IRIS_PASSWORD" \
        -e IRIS_USERNAME="_SYSTEM" \
        "$IRIS_IMAGE"

    log_success "IRIS container started"

    # Wait for IRIS to be ready
    log_info "Waiting for IRIS to initialize (30 seconds)..."
    sleep 30

    # Verify IRIS is running
    if ! docker ps | grep -q "$CONTAINER_NAME"; then
        log_error "Container failed to start"
        docker logs "$CONTAINER_NAME" --tail 20
        return 1
    fi

    log_success "IRIS is running"

    # Create namespace and schema
    if [[ "$SKIP_SCHEMA" != "true" ]]; then
        create_schema_local
    fi
}

# Function to create schema locally
create_schema_local() {
    log_info "Creating namespace and vector tables..."

    # Create SQL script for schema
    cat > /tmp/iris_schema.sql << 'EOF'
-- Create namespace DEMO if it doesn't exist
-- Note: Namespace creation requires ObjectScript, handled separately

-- Switch to DEMO namespace (will be created via iris session)
-- Create ClinicalNoteVectors table
CREATE TABLE IF NOT EXISTS ClinicalNoteVectors (
    ResourceID VARCHAR(255) PRIMARY KEY,
    PatientID VARCHAR(255),
    DocumentType VARCHAR(100),
    TextContent VARCHAR(10000),
    Embedding VECTOR(DOUBLE, 1024),
    EmbeddingModel VARCHAR(100),
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on patient ID
CREATE INDEX IF NOT EXISTS idx_clinical_patient ON ClinicalNoteVectors(PatientID);

-- Create index on document type
CREATE INDEX IF NOT EXISTS idx_clinical_doctype ON ClinicalNoteVectors(DocumentType);

-- Create MedicalImageVectors table
CREATE TABLE IF NOT EXISTS MedicalImageVectors (
    ResourceID VARCHAR(255) PRIMARY KEY,
    PatientID VARCHAR(255),
    ImageType VARCHAR(100),
    Modality VARCHAR(50),
    ImagePath VARCHAR(500),
    Embedding VECTOR(DOUBLE, 1024),
    EmbeddingModel VARCHAR(100),
    Metadata VARCHAR(2000),
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on patient ID
CREATE INDEX IF NOT EXISTS idx_image_patient ON MedicalImageVectors(PatientID);

-- Create index on modality
CREATE INDEX IF NOT EXISTS idx_image_modality ON MedicalImageVectors(Modality);

-- Create index on image type
CREATE INDEX IF NOT EXISTS idx_image_type ON MedicalImageVectors(ImageType);
EOF

    # Create ObjectScript to create namespace
    cat > /tmp/iris_namespace.cos << EOF
    // Create namespace DEMO
    Set namespace = "DEMO"

    // Check if namespace exists
    If '##class(Config.Namespaces).Exists(namespace) {
        Write "Creating namespace ",namespace,!

        // Create namespace
        Set properties("Globals") = "DEMO"
        Set properties("Library") = "IRISLIB"
        Set properties("Routines") = "DEMO"

        Set sc = ##class(Config.Namespaces).Create(namespace, .properties)

        If \$\$\$ISOK^%apiOBJ(sc) {
            Write "Namespace created successfully",!
        } Else {
            Write "Error creating namespace: ",\$System.Status.GetErrorText(sc),!
            Quit
        }

        // Create database for DEMO
        Set dbProperties("Directory") = "/usr/irissys/mgr/demo"
        Set sc = ##class(Config.Databases).Create("DEMO", .dbProperties)

        If \$\$\$ISOK^%apiOBJ(sc) {
            Write "Database created successfully",!
        }
    } Else {
        Write "Namespace ",namespace," already exists",!
    }

    Halt
EOF

    # Copy files to container
    docker cp /tmp/iris_namespace.cos ${CONTAINER_NAME}:/tmp/
    docker cp /tmp/iris_schema.sql ${CONTAINER_NAME}:/tmp/

    # Execute ObjectScript to create namespace
    log_info "Creating namespace $IRIS_NAMESPACE..."
    docker exec -i "$CONTAINER_NAME" iris session IRIS -U%SYS << EOF
$IRIS_PASSWORD
do \$system.OBJ.Load("/tmp/iris_namespace.cos","ck")
halt
EOF

    # Execute SQL to create tables
    log_info "Creating vector tables..."
    docker exec -i "$CONTAINER_NAME" iris sql IRIS -U${IRIS_NAMESPACE} << EOF
$IRIS_PASSWORD
$(cat /tmp/iris_schema.sql)
EOF

    # Cleanup temp files
    rm -f /tmp/iris_schema.sql /tmp/iris_namespace.cos

    log_success "Schema created successfully"

    # Verify tables exist
    log_info "Verifying tables..."
    docker exec -i "$CONTAINER_NAME" iris sql IRIS -U${IRIS_NAMESPACE} << EOF > /tmp/iris_verify.txt
$IRIS_PASSWORD
SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = '${IRIS_NAMESPACE}';
EOF

    if grep -q "ClinicalNoteVectors" /tmp/iris_verify.txt && grep -q "MedicalImageVectors" /tmp/iris_verify.txt; then
        log_success "Tables verified"
    else
        log_warn "Table verification inconclusive - check manually"
    fi

    rm -f /tmp/iris_verify.txt
}

# Function to deploy on remote host
deploy_iris_remote() {
    local host="$1"
    local ssh_key="$2"

    log_info "Deploying IRIS on remote host: $host"

    if [[ -z "$ssh_key" ]]; then
        log_error "SSH key required for remote deployment"
        return 1
    fi

    if [[ ! -f "$ssh_key" ]]; then
        log_error "SSH key not found: $ssh_key"
        return 1
    fi

    # Execute deployment on remote host
    ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i "$ssh_key" "ubuntu@${host}" << ENDSSH
set -e

CONTAINER_NAME="$CONTAINER_NAME"
IRIS_IMAGE="$IRIS_IMAGE"
IRIS_PASSWORD="$IRIS_PASSWORD"
IRIS_NAMESPACE="$IRIS_NAMESPACE"
FORCE_RECREATE="$FORCE_RECREATE"
SKIP_SCHEMA="$SKIP_SCHEMA"

echo "→ Deploying InterSystems IRIS..."

# Check if container exists
if docker ps -a --format '{{.Names}}' | grep -q "^\${CONTAINER_NAME}\$"; then
    if [[ "\$FORCE_RECREATE" == "true" ]]; then
        echo "! Removing existing container..."
        docker stop \$CONTAINER_NAME 2>/dev/null || true
        docker rm \$CONTAINER_NAME 2>/dev/null || true
    else
        echo "! Container already exists"
        if docker ps --format '{{.Names}}' | grep -q "^\${CONTAINER_NAME}\$"; then
            echo "✓ Container is running"
            exit 0
        else
            echo "→ Starting existing container..."
            docker start \$CONTAINER_NAME
            echo "✓ Container started"
            exit 0
        fi
    fi
fi

echo "→ Pulling IRIS image..."
docker pull \$IRIS_IMAGE

echo "→ Creating persistent volume..."
docker volume create iris-data 2>/dev/null || true

echo "→ Starting IRIS container..."
docker run -d \
    --name \$CONTAINER_NAME \
    --restart unless-stopped \
    -p 1972:1972 \
    -p 52773:52773 \
    -v iris-data:/usr/irissys/mgr \
    -e IRIS_PASSWORD="\$IRIS_PASSWORD" \
    -e IRIS_USERNAME="_SYSTEM" \
    \$IRIS_IMAGE

echo "✓ IRIS container started"

echo "→ Waiting for IRIS to initialize..."
sleep 30

# Verify running
if ! docker ps | grep -q "\$CONTAINER_NAME"; then
    echo "✗ Container failed to start"
    docker logs \$CONTAINER_NAME --tail 20
    exit 1
fi

echo "✓ IRIS is running"

# Create schema if not skipped
if [[ "\$SKIP_SCHEMA" != "true" ]]; then
    echo ""
    echo "→ Creating namespace and schema..."

    # Create namespace ObjectScript
    cat > /tmp/iris_namespace.cos << 'EOFCOS'
    Set namespace = "$IRIS_NAMESPACE"
    If '##class(Config.Namespaces).Exists(namespace) {
        Write "Creating namespace ",namespace,!
        Set properties("Globals") = "$IRIS_NAMESPACE"
        Set properties("Library") = "IRISLIB"
        Set properties("Routines") = "$IRIS_NAMESPACE"
        Set sc = ##class(Config.Namespaces).Create(namespace, .properties)
        If \$\$\$ISOK^%apiOBJ(sc) {
            Write "Namespace created",!
        }
        Set dbProperties("Directory") = "/usr/irissys/mgr/demo"
        Set sc = ##class(Config.Databases).Create("$IRIS_NAMESPACE", .dbProperties)
    } Else {
        Write "Namespace exists",!
    }
    Halt
EOFCOS

    # Create SQL schema
    cat > /tmp/iris_schema.sql << 'EOFSQL'
CREATE TABLE IF NOT EXISTS ClinicalNoteVectors (
    ResourceID VARCHAR(255) PRIMARY KEY,
    PatientID VARCHAR(255),
    DocumentType VARCHAR(100),
    TextContent VARCHAR(10000),
    Embedding VECTOR(DOUBLE, 1024),
    EmbeddingModel VARCHAR(100),
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_clinical_patient ON ClinicalNoteVectors(PatientID);
CREATE INDEX IF NOT EXISTS idx_clinical_doctype ON ClinicalNoteVectors(DocumentType);

CREATE TABLE IF NOT EXISTS MedicalImageVectors (
    ResourceID VARCHAR(255) PRIMARY KEY,
    PatientID VARCHAR(255),
    ImageType VARCHAR(100),
    Modality VARCHAR(50),
    ImagePath VARCHAR(500),
    Embedding VECTOR(DOUBLE, 1024),
    EmbeddingModel VARCHAR(100),
    Metadata VARCHAR(2000),
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_image_patient ON MedicalImageVectors(PatientID);
CREATE INDEX IF NOT EXISTS idx_image_modality ON MedicalImageVectors(Modality);
CREATE INDEX IF NOT EXISTS idx_image_type ON MedicalImageVectors(ImageType);
EOFSQL

    # Copy to container
    docker cp /tmp/iris_namespace.cos \${CONTAINER_NAME}:/tmp/
    docker cp /tmp/iris_schema.sql \${CONTAINER_NAME}:/tmp/

    # Create namespace
    echo "→ Creating namespace..."
    docker exec -i \$CONTAINER_NAME iris session IRIS -U%SYS << EOFEXEC
\$IRIS_PASSWORD
do \\\$system.OBJ.Load("/tmp/iris_namespace.cos","ck")
halt
EOFEXEC

    # Create tables
    echo "→ Creating tables..."
    docker exec -i \$CONTAINER_NAME iris sql IRIS -U\${IRIS_NAMESPACE} << EOFEXEC
\$IRIS_PASSWORD
\$(cat /tmp/iris_schema.sql)
EOFEXEC

    echo "✓ Schema created"

    rm -f /tmp/iris_namespace.cos /tmp/iris_schema.sql
fi

echo ""
echo "✓ IRIS deployment complete"
ENDSSH

    return $?
}

# Function to verify deployment
verify_deployment() {
    local host="${1:-localhost}"
    local is_remote="${2:-false}"

    log_info "Verifying IRIS deployment..."

    if [[ "$is_remote" == "true" ]]; then
        ssh -o StrictHostKeyChecking=no -i "$SSH_KEY" "ubuntu@${host}" << 'ENDSSH'
# Check container status
if docker ps | grep -q iris-vector-db; then
    echo "✓ Container is running"
    echo ""
    docker ps | grep iris-vector-db
    echo ""
    echo "Ports:"
    echo "  SQL:        1972"
    echo "  Management: 52773 (http://$(curl -s ifconfig.me):52773/csp/sys/UtilHome.csp)"
else
    echo "✗ Container is not running"
    exit 1
fi
ENDSSH
    else
        if docker ps | grep -q "$CONTAINER_NAME"; then
            log_success "Container is running"
            echo ""
            docker ps | grep "$CONTAINER_NAME"
            echo ""
            log_info "Ports:"
            log_info "  SQL:        localhost:${IRIS_PORT_SQL}"
            log_info "  Management: http://localhost:${IRIS_PORT_WEB}/csp/sys/UtilHome.csp"
        else
            log_error "Container is not running"
            return 1
        fi
    fi
}

# Main execution
main() {
    log_info "InterSystems IRIS Vector Database Deployment"
    echo ""

    if [[ -n "$REMOTE_HOST" ]]; then
        # Remote deployment
        if deploy_iris_remote "$REMOTE_HOST" "$SSH_KEY"; then
            log_success "Remote deployment complete"
            verify_deployment "$REMOTE_HOST" true
        else
            log_error "Remote deployment failed"
            exit 1
        fi
    else
        # Local deployment
        deploy_iris_local
        verify_deployment
    fi

    echo ""
    log_success "=========================================="
    log_success "IRIS Vector Database Deployed"
    log_success "=========================================="
    echo ""
    log_info "Connection details:"
    log_info "  Host:      ${REMOTE_HOST:-localhost}"
    log_info "  SQL Port:  $IRIS_PORT_SQL"
    log_info "  Web Port:  $IRIS_PORT_WEB"
    log_info "  Namespace: $IRIS_NAMESPACE"
    log_info "  Username:  _SYSTEM"
    log_info "  Password:  $IRIS_PASSWORD"
    echo ""
    log_info "Tables created:"
    log_info "  - ClinicalNoteVectors (1024-dim VECTOR)"
    log_info "  - MedicalImageVectors (1024-dim VECTOR)"
    echo ""
    log_info "Management Portal:"
    if [[ -n "$REMOTE_HOST" ]]; then
        log_info "  http://${REMOTE_HOST}:${IRIS_PORT_WEB}/csp/sys/UtilHome.csp"
    else
        log_info "  http://localhost:${IRIS_PORT_WEB}/csp/sys/UtilHome.csp"
    fi
    echo ""
    log_info "Next steps:"
    log_info "  1. Test connection with Python client"
    log_info "  2. Run: ./scripts/aws/deploy-nim-llm.sh"
    echo ""
}

# Run main function
main
