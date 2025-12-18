# Feature Specification: MIMIC-CXR Vector Search Table Setup

**Feature Branch**: `009-mimic-cxr-vector-setup`
**Created**: 2025-12-18
**Status**: Draft
**Input**: User description: "set up mimic-cxr vector search tables and populate them as part of our system for ingesting data for system setup"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automated Vector Table Creation on System Setup (Priority: P1)

When deploying the medical-graphrag-assistant system (via Docker container startup or setup script), the VectorSearch.MIMICCXRImages table should be automatically created if it doesn't exist, ensuring the medical image search feature has its required database schema ready.

**Why this priority**: Without the table, the medical_image_search tool fails with "table does not exist" error. This blocks all medical image search functionality.

**Independent Test**: After running the IRIS container setup, verify table exists by executing `SELECT COUNT(*) FROM VectorSearch.MIMICCXRImages` - query should return 0 (empty table) without error.

**Acceptance Scenarios**:

1. **Given** a fresh IRIS container with no VectorSearch schema, **When** the container starts and runs initialization scripts, **Then** the VectorSearch.MIMICCXRImages table exists with correct schema (columns: ImageID, SubjectID, StudyID, DicomID, ImagePath, ViewPosition, Vector, EmbeddingModel, Provider, CreatedAt)

2. **Given** an existing IRIS container with the table already created, **When** the initialization script runs again, **Then** the script skips creation (idempotent) and preserves existing data

---

### User Story 2 - Batch Image Ingestion Script (Priority: P2)

A Python script that processes MIMIC-CXR DICOM files, generates NV-CLIP embeddings via the embedding service, and inserts records into the VectorSearch.MIMICCXRImages table. Supports batch processing with progress reporting and error recovery.

**Why this priority**: Once the table exists, we need a way to populate it with actual medical image vectors. This enables the semantic search functionality.

**Independent Test**: Run the ingestion script with a small subset of DICOM files (e.g., 10 images). Verify records appear in the table with valid 1024-dimensional vectors.

**Acceptance Scenarios**:

1. **Given** a directory containing MIMIC-CXR DICOM files and a running NV-CLIP service, **When** the ingestion script runs with `--source /path/to/mimic-cxr --limit 100`, **Then** 100 images are vectorized and inserted into the table with progress output

2. **Given** the ingestion script has already processed some images, **When** running again with `--skip-existing`, **Then** only new images are processed (avoiding duplicate work)

3. **Given** a DICOM file that cannot be read (corrupted), **When** the ingestion script encounters it, **Then** an error is logged, the file is skipped, and processing continues with remaining files

---

### User Story 3 - Integration with Docker Compose Setup (Priority: P3)

The table creation SQL and sample data population are integrated into the Dockerfhir/docker-compose.yaml workflow, so a developer can run `docker compose up` and have a working medical image search with sample data.

**Why this priority**: Reduces friction for new developers and demo setups. Not strictly required for production deployments where data is ingested separately.

**Independent Test**: Run `docker compose down -v && docker compose up -d` from Dockerfhir/, wait for initialization, then execute a medical image search query through the Streamlit UI.

**Acceptance Scenarios**:

1. **Given** a clean Docker environment, **When** running `docker compose up -d` in Dockerfhir/, **Then** within 5 minutes, the VectorSearch.MIMICCXRImages table exists with at least 50 sample images vectorized

2. **Given** the docker-compose setup completed, **When** using the Streamlit UI to search for "chest X-ray with pneumonia", **Then** results are returned with similarity scores

---

### Edge Cases

- What happens when NV-CLIP embedding service is unavailable during ingestion?
  - Script should fail gracefully with clear error message suggesting to check NVCLIP_BASE_URL

- What happens when IRIS database connection fails during ingestion?
  - Script should retry connection 3 times with exponential backoff, then fail with connection details

- What happens with very large DICOM files (>100MB)?
  - Should log warning and skip, or process with memory limits

- What happens when disk space is insufficient for batch processing?
  - Check available space before starting, warn if <1GB available

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST create VectorSearch schema if it doesn't exist on IRIS startup
- **FR-002**: System MUST create MIMICCXRImages table with correct DDL on IRIS startup
- **FR-003**: Table creation MUST be idempotent (safe to run multiple times)
- **FR-004**: Ingestion script MUST support batch size configuration (default: 32 images)
- **FR-005**: Ingestion script MUST report progress (images processed, time elapsed, estimated remaining)
- **FR-006**: Ingestion script MUST log errors for individual files without stopping entire process
- **FR-007**: Ingestion script MUST validate NV-CLIP service availability before starting
- **FR-008**: Ingestion script MUST support `--dry-run` mode to show what would be processed
- **FR-009**: System MUST store 1024-dimensional vectors from NV-CLIP embeddings
- **FR-010**: Each image record MUST include SubjectID, StudyID, ImageID, ViewPosition, and ImagePath

### Key Entities

- **MIMICCXRImage**: A chest X-ray image record with vector embedding
  - ImageID (PK): Unique DICOM identifier
  - SubjectID: Patient identifier (anonymized)
  - StudyID: Study/session identifier
  - ViewPosition: PA, AP, LATERAL, LL, SWIMMERS
  - Vector: 1024-dimensional NV-CLIP embedding
  - EmbeddingModel: 'nvidia/nvclip'
  - Provider: 'nvclip'

- **IngestionJob**: Represents a batch processing run
  - Source directory
  - Total files found
  - Files processed/skipped/failed
  - Start/end timestamps

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Fresh `docker compose up` creates VectorSearch.MIMICCXRImages table within 60 seconds of container start
- **SC-002**: Ingestion script processes at least 10 images/second with GPU-enabled NV-CLIP, 1 image/second with CPU
- **SC-003**: After ingestion, `medical_image_search` tool returns results with similarity scores for any text query
- **SC-004**: Table supports at least 100,000 image records without performance degradation on vector search (< 500ms query time)
- **SC-005**: System handles re-runs gracefully - no duplicate records, no data loss
