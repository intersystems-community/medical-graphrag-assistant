# Feature Specification: Reproducible FHIR + VectorSearch Server Setup

**Feature Branch**: `008-fhir-vectorsearch-setup`
**Created**: 2025-12-16
**Status**: Draft
**Input**: User description: "Implement proper reproducible FHIR+VectorSearch server setup" with critical constraint: "the iris-fhir-licensed container should be one and the same container that has the vector search functionality!!! this is one monolithic server!!!!!!!!"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One-Command Server Deployment (Priority: P1)

A developer needs to deploy the complete Medical GraphRAG infrastructure from scratch. With a single docker-compose command, they should get a fully functional server that includes FHIR R4 endpoints, VectorSearch tables, knowledge graph tables, and pre-populated sample data. No manual SQL execution or separate container orchestration required.

**Why this priority**: This is the core value proposition - reproducibility. Without this, every deployment requires manual intervention, making the system fragile and hard to maintain. The user explicitly stated the server must be "one monolithic server" combining FHIR and VectorSearch.

**Independent Test**: Run `docker-compose up` on a fresh EC2 instance and verify both FHIR API (`/fhir/r4/metadata`) and VectorSearch queries work within 5 minutes of container startup.

**Acceptance Scenarios**:

1. **Given** a fresh EC2 instance with Docker installed, **When** running `docker-compose -f docker-compose-fhir.yaml up`, **Then** the iris-fhir container starts with both FHIR and VectorSearch functionality enabled
2. **Given** the container is running, **When** querying `http://localhost:52773/fhir/r4/metadata`, **Then** the FHIR capability statement is returned
3. **Given** the container is running, **When** connecting via IRIS SQL and running `SELECT * FROM VectorSearch.MIMICCXRImages LIMIT 1`, **Then** the query succeeds (table exists)
4. **Given** a fresh deployment, **When** checking database schemas, **Then** all required tables exist: VectorSearch.MIMICCXRImages, VectorSearch.PatientImageMapping, SQLUser.Entities, SQLUser.EntityRelationships, SQLUser.FHIRDocuments

---

### User Story 2 - Automated Schema Initialization (Priority: P1)

When the IRIS container starts, all required database schemas and tables should be automatically created via init scripts. No manual SQL execution should be required. This ensures every deployment is identical and reduces human error.

**Why this priority**: Schema initialization is fundamental to reproducibility. Without it, the "one-command deployment" in User Story 1 cannot work.

**Independent Test**: Delete all VectorSearch tables, restart the container, and verify tables are recreated automatically.

**Acceptance Scenarios**:

1. **Given** the container's init-scripts directory contains schema SQL files, **When** the container starts, **Then** IRIS executes all .sql files in alphabetical order
2. **Given** init scripts exist for VectorSearch and SQLUser schemas, **When** the container starts for the first time, **Then** both schemas are created with all required tables
3. **Given** tables already exist from a previous run, **When** the container restarts, **Then** init scripts use CREATE IF NOT EXISTS semantics (idempotent)

---

### User Story 3 - Automated Data Population (Priority: P2)

After schemas are created, the system should automatically populate sample data including MIMIC-CXR image metadata with vectors, patient mappings, and knowledge graph entities. This enables immediate testing and demonstration without manual data import steps.

**Why this priority**: While schemas are essential, pre-populated data dramatically improves developer experience and enables immediate testing of the application.

**Independent Test**: Start fresh container, wait for initialization, query for sample images and verify at least 100 image records with valid vectors exist.

**Acceptance Scenarios**:

1. **Given** schema init completes, **When** data population scripts run, **Then** at least 100 MIMIC-CXR image records are inserted into MIMICCXRImages
2. **Given** image data is populated, **When** querying PatientImageMapping, **Then** mappings exist linking MIMIC subjects to FHIR patients
3. **Given** data population completes, **When** querying SQLUser.Entities, **Then** medical entities exist with types SYMPTOM, CONDITION, MEDICATION, etc.
4. **Given** entities exist, **When** querying EntityRelationships, **Then** relationships between entities exist

---

### User Story 4 - Configuration via Environment Variables (Priority: P2)

All server configuration (FHIR base URL, database credentials, NV-CLIP endpoint) should be configurable via environment variables in docker-compose.yaml. No hardcoded values that require source code changes.

**Why this priority**: Flexibility is essential for deploying to different environments (dev, staging, prod) without code changes.

**Independent Test**: Change IRIS_PASSWORD environment variable, restart container, verify the new password is required for connections.

**Acceptance Scenarios**:

1. **Given** docker-compose.yaml defines IRIS_PASSWORD, **When** connecting to IRIS, **Then** the specified password must be used
2. **Given** FHIR_BASE_URL is configurable, **When** the MCP server reads config, **Then** it uses the environment variable value
3. **Given** NVCLIP_BASE_URL is configurable, **When** searching images, **Then** embeddings are requested from the configured endpoint

---

### User Story 5 - Health Check and Readiness (Priority: P3)

The container should expose health check endpoints that indicate when all services are ready (FHIR, VectorSearch, data populated). This enables orchestration tools to know when the server is truly ready to serve requests.

**Why this priority**: Important for production deployments and CI/CD pipelines, but not required for basic functionality.

**Independent Test**: Query health endpoint, verify it returns "ready" only after all initialization completes.

**Acceptance Scenarios**:

1. **Given** the container is starting, **When** querying health endpoint, **Then** it returns "initializing" status
2. **Given** all init scripts complete, **When** querying health endpoint, **Then** it returns "ready" status
3. **Given** any init script fails, **When** querying health endpoint, **Then** it returns "unhealthy" status with error details

---

### Edge Cases

- What happens if IRIS fails to start (license issues, port conflicts)?
  - Container logs the specific error and exits with non-zero status
  - docker-compose shows the error in logs

- What happens if init scripts fail partway through?
  - Failed script is logged with full error message
  - Subsequent scripts still attempt to run (best effort)
  - Health check reports "unhealthy" with failed script names

- How are existing databases handled on container restart?
  - All CREATE statements use IF NOT EXISTS
  - Data population scripts check for existing data before bulk insert
  - No data is deleted on restart (append-only for idempotency)

- What if the VectorSearch license is missing or expired?
  - Container logs license error clearly
  - FHIR functionality continues to work
  - VectorSearch queries return appropriate error

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST use a single Docker container (iris-fhir) for both FHIR R4 and VectorSearch functionality
- **FR-002**: System MUST automatically create all required database schemas on container startup
- **FR-003**: System MUST create VectorSearch.MIMICCXRImages table with VECTOR(DOUBLE, 1024) column for embeddings
- **FR-004**: System MUST create VectorSearch.PatientImageMapping table for MIMIC-to-FHIR patient links
- **FR-005**: System MUST create SQLUser.Entities table for knowledge graph entities
- **FR-006**: System MUST create SQLUser.EntityRelationships table for entity relationships
- **FR-007**: System MUST create SQLUser.FHIRDocuments table for FHIR document storage
- **FR-008**: System MUST execute init scripts in alphabetical order during container startup
- **FR-009**: System MUST support idempotent schema creation (CREATE IF NOT EXISTS)
- **FR-010**: System MUST expose FHIR R4 endpoints at standard path (/fhir/r4)
- **FR-011**: System MUST allow SQL connections on standard IRIS port (1972)
- **FR-012**: System MUST support configuration via environment variables

### Data Population Requirements

- **FR-013**: System SHOULD pre-populate sample MIMIC-CXR image metadata with vectors
- **FR-014**: System SHOULD pre-populate sample patient mappings
- **FR-015**: System SHOULD pre-populate sample knowledge graph entities and relationships
- **FR-016**: Data population MUST be idempotent (re-running doesn't create duplicates)

### Key Entities

- **iris-fhir Container**: Single Docker container running InterSystems IRIS for Health with FHIR and VectorSearch
- **Init Scripts**: SQL files executed on container startup to create schemas and tables
- **VectorSearch Schema**: Database schema containing image vectors and patient mappings
- **SQLUser Schema**: Database schema containing knowledge graph tables and FHIR documents

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Fresh deployment completes in under 5 minutes from `docker-compose up` to all services ready
- **SC-002**: Zero manual SQL commands required for basic deployment
- **SC-003**: All 5 required database tables created automatically on startup
- **SC-004**: FHIR metadata endpoint responds within 30 seconds of container start
- **SC-005**: VectorSearch queries work within 60 seconds of container start
- **SC-006**: Container restart preserves existing data (no data loss)
- **SC-007**: Same docker-compose.yaml works identically on any EC2 instance with Docker
- **SC-008**: E2E tests pass when run against freshly deployed container

### Application Integration Requirements

- **FR-017**: Streamlit application MUST connect to the iris-fhir container for all database operations
- **FR-018**: MCP server (fhir_graphrag_mcp_server.py) MUST connect to the iris-fhir container for FHIR and VectorSearch queries
- **FR-019**: Connection configuration (host, port, credentials) MUST be shared via environment variables between all services
- **FR-020**: The application stack MUST support running Streamlit on the same host or a different host from IRIS

### Key Entities

- **iris-fhir Container**: Single Docker container running InterSystems IRIS for Health with FHIR and VectorSearch
- **Init Scripts**: SQL files executed on container startup to create schemas and tables
- **VectorSearch Schema**: Database schema containing image vectors and patient mappings
- **SQLUser Schema**: Database schema containing knowledge graph tables and FHIR documents
- **Streamlit Application**: Web UI that connects to IRIS for medical chat interface
- **MCP Server**: Model Context Protocol server providing tools that query IRIS

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Fresh deployment completes in under 5 minutes from `docker-compose up` to all services ready
- **SC-002**: Zero manual SQL commands required for basic deployment
- **SC-003**: All 5 required database tables created automatically on startup
- **SC-004**: FHIR metadata endpoint responds within 30 seconds of container start
- **SC-005**: VectorSearch queries work within 60 seconds of container start
- **SC-006**: Container restart preserves existing data (no data loss)
- **SC-007**: Same docker-compose.yaml works identically on any EC2 instance with Docker
- **SC-008**: E2E tests pass when run against freshly deployed container
- **SC-009**: Streamlit app successfully connects and displays data from IRIS after fresh deployment
- **SC-010**: MCP tools return valid results when querying the freshly deployed IRIS container

## Assumptions

- InterSystems IRIS for Health 2025.1 Community Edition is used (irishealth-community image)
- VectorSearch functionality is available in the community edition with appropriate licensing
- Docker and docker-compose are available on the deployment target
- Network access is available to pull Docker images from container registry
- Sufficient disk space (10GB+) and memory (4GB+) for IRIS container
- The init-scripts directory mounting mechanism is available in IRIS container
- Streamlit application runs on the same EC2 host as IRIS (localhost connection) or uses IRIS_HOST env var for remote
- MCP server uses src/db/connection.py which reads IRIS_HOST, IRIS_PORT, IRIS_PASSWORD from environment

## Clarifications

### Session 2025-12-16
- Q: Should FHIR and VectorSearch be in separate containers? → A: NO - User explicitly stated "one monolithic server" - single container for both
- Q: What base image should be used? → A: intersystemsdc/irishealth-community:latest (or specific 2025.1 tag)
- Q: Where should init scripts be placed? → A: In a mounted volume at container startup (Dockerfhir/init-scripts/)
