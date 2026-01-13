# Implementation Tasks: AWS GPU-based NVIDIA NIM RAG Deployment

**Feature**: 003-aws-nim-deployment
**Branch**: `003-aws-nim-deployment`
**Generated**: 2025-11-09
**Input Documents**: [spec.md](./spec.md), [plan.md](./plan.md), [research.md](./research.md), [data-model.md](./data-model.md), [quickstart.md](./quickstart.md)

---

## Task Execution Guide

### Checklist Format
Each task follows this format:
```
- [ ] [TaskID] [P?] [Story?] Description with file path
```

- `TaskID`: Unique identifier (e.g., SETUP-001, US1-001)
- `[P]`: Marks tasks that can be executed in parallel with others in the same phase
- `[Story]`: References user story (US1-US5) if applicable
- File paths indicate where implementation should occur

### Recommended Workflow
1. Complete all **Phase 1: Setup** tasks first (foundational)
2. Complete all **Phase 2: Shared Infrastructure** tasks (blocking dependencies)
3. Execute **Phase 3-7** in priority order: P1 stories (US1, US5), P2 stories (US2, US4), P3 stories (US3)
4. Within each phase, tasks marked `[P]` can run in parallel
5. Complete **Phase 8: Polish** after all user stories implemented

---

## Phase 1: Setup & Project Initialization

**Purpose**: Establish project structure, configuration templates, and development environment prerequisites.

**Blocking Tasks**: None (can start immediately)

**Dependencies**: None

### Tasks

- [ ] [SETUP-001] [P] Create project directory structure with scripts/aws/, src/vectorization/, src/validation/, config/, docs/, tests/ directories in repository root
- [ ] [SETUP-002] [P] Create config/.env.template with required environment variables (AWS_REGION, AWS_INSTANCE_TYPE, SSH_KEY_NAME, SSH_KEY_PATH, NVIDIA_API_KEY, NGC_API_KEY, IRIS_USERNAME, IRIS_PASSWORD) and placeholder values
- [ ] [SETUP-003] [P] Create config/aws-config.yaml template with EC2 instance configuration (instance type: g5.xlarge, AMI: Ubuntu 24.04 LTS, security group rules, EBS volume config)
- [ ] [SETUP-004] [P] Create config/nim-config.yaml template with NVIDIA NIM service settings (LLM model: meta/llama-3.1-8b-instruct, port: 8001, GPU allocation, health check endpoints)
- [ ] [SETUP-005] [P] Create config/iris-config.yaml template with IRIS database configuration (port: 1972, management port: 52773, namespace: DEMO, default credentials, volume mount paths)
- [ ] [SETUP-006] [P] Create .gitignore entries for .env files, SSH keys (*.pem), and SQLite state databases (vectorization_state.db)
- [ ] [SETUP-007] [P] Create README.md in repository root with overview, prerequisites, quick start reference, and links to full documentation in docs/ directory
- [ ] [SETUP-008] Create docs/deployment-guide.md skeleton with sections for prerequisites, step-by-step deployment, validation, and troubleshooting (content filled in later phases)
- [ ] [SETUP-009] Create docs/troubleshooting.md skeleton with common issues template and solution format
- [ ] [SETUP-010] Create docs/architecture.md skeleton for system architecture diagrams and component descriptions

**Parallel Execution Example**:
```bash
# All SETUP tasks can run in parallel except SETUP-008/009/010 which depend on directory structure
# Execute SETUP-001 to SETUP-007 concurrently, then SETUP-008 to SETUP-010
```

---

## Phase 2: Shared Infrastructure & Utilities

**Purpose**: Implement reusable components and utilities used across multiple user stories.

**Blocking Tasks**: Phase 1 must complete first

**Dependencies**: Project structure (SETUP-001), configuration templates (SETUP-002 to SETUP-005)

### Tasks

- [ ] [INFRA-001] [P] Implement scripts/aws/utils/check-gpu.sh to verify GPU availability using nvidia-smi and return device information (GPU model, memory, driver version, CUDA version)
- [ ] [INFRA-002] [P] Implement scripts/aws/utils/wait-for-service.sh utility accepting service URL and timeout, polling until service responds with 200 status or timeout expires
- [ ] [INFRA-003] [P] Implement scripts/aws/utils/cleanup.sh script to safely terminate EC2 instances, remove Docker containers, and clean up resources based on deployment tags
- [ ] [INFRA-004] [P] Implement src/vectorization/vector_db_client.py as Python class wrapping IRIS database operations using intersystems-iris driver and rag-templates utilities from ./rag-templates/common/vector_sql_utils.py
- [ ] [INFRA-005] [P] Implement src/vectorization/embedding_client.py as Python class for NVIDIA NIM Cloud API (nvidia/nv-embedqa-e5-v5) with batch request support, retry logic with exponential backoff, and rate limiting
- [ ] [INFRA-006] Create src/vectorization/batch_processor.py with resumable batch processing logic using SQLite state tracking (see data-model.md VectorizationState schema) and checkpoint recovery
- [ ] [INFRA-007] Implement tests/unit/test_vector_db_client.py with unit tests for IRIS connection, vector insertion, and similarity search using mock database
- [ ] [INFRA-008] Implement tests/unit/test_embedding_client.py with unit tests for API client including mock API responses, retry scenarios, and rate limit handling
- [ ] [INFRA-009] Implement tests/unit/test_batch_processor.py with unit tests for checkpoint creation, resumption after interruption, and state transitions

**Parallel Execution Example**:
```bash
# INFRA-001, INFRA-002, INFRA-003, INFRA-004, INFRA-005 can run in parallel (independent utilities)
# INFRA-006 depends on INFRA-004 being complete
# INFRA-007, INFRA-008, INFRA-009 can run in parallel after their respective implementation tasks
```

---

## Phase 3: User Story 1 - Complete RAG System Deployment (P1)

**Purpose**: Implement core deployment automation from infrastructure provisioning to service validation.

**Blocking Tasks**: Phase 2 (INFRA-001, INFRA-002, INFRA-003)

**Dependencies**: GPU check utility (INFRA-001), service wait utility (INFRA-002), cleanup utility (INFRA-003)

### Tasks

- [ ] [US1-001] Implement scripts/aws/provision-instance.sh to launch g5.xlarge EC2 instance using AWS CLI with tags for resource tracking, security group creation allowing SSH (port 22) and service ports (1972, 52773, 8000, 8001), EBS volume attachment (500GB gp3), and idempotency check for existing instances
- [ ] [US1-002] Implement scripts/aws/install-gpu-drivers.sh to install nvidia-driver-535 and nvidia-utils-535 using apt-get on Ubuntu 24.04, verify installation with nvidia-smi, and log driver version information
- [ ] [US1-003] Implement scripts/aws/setup-docker-gpu.sh to install NVIDIA Container Toolkit, configure Docker daemon with GPU runtime, restart Docker service, and verify GPU accessibility in containers using docker run --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
- [ ] [US1-004] Implement scripts/aws/deploy-iris.sh to pull intersystemsdc/iris-community:2025.1 container, create Docker volume for persistent storage, run container with port mappings (1972:1972, 52773:52773), configure namespace DEMO, and execute data-model.md SQL schema creation (ClinicalNoteVectors and MedicalImageVectors tables)
- [ ] [US1-005] Implement scripts/aws/deploy-nim-llm.sh to pull nvcr.io/nim/meta/llama-3.1-8b-instruct:latest container, run with GPU allocation (--gpus all), set NGC_API_KEY environment variable, map port 8001:8000, configure shared memory (--shm-size=16g), and wait for service health endpoint
- [ ] [US1-006] Implement scripts/aws/deploy.sh as main orchestration script calling provision-instance.sh, waiting for SSH availability, installing GPU drivers, rebooting instance if required, setting up Docker GPU runtime, deploying IRIS, deploying NIM LLM, and running validation with progress logging to console
- [ ] [US1-007] Update docs/deployment-guide.md with detailed step-by-step instructions for running deploy.sh, expected timing for each phase (per quickstart.md estimates), and success indicators
- [ ] [US1-008] Add troubleshooting entries to docs/troubleshooting.md for common deployment issues: GPU driver not loading (solution: reboot required), NGC API key validation failures (solution: verify environment variable), Docker permission errors (solution: add user to docker group)

**Sequential Execution Required**:
```bash
# These tasks must execute in strict order within US1:
# US1-001 → US1-002 → US1-003 → US1-004, US1-005 (parallel) → US1-006 → US1-007, US1-008 (parallel)
```

---

## Phase 4: User Story 5 - Deployment Validation & Health Monitoring (P1)

**Purpose**: Implement comprehensive validation and monitoring for deployed system.

**Blocking Tasks**: Phase 3 (US1-004, US1-005) - requires IRIS and NIM services deployed

**Dependencies**: Deployed services (US1-004, US1-005), GPU check utility (INFRA-001), service wait utility (INFRA-002)

### Tasks

- [ ] [US5-001] Implement scripts/aws/validate-deployment.sh as comprehensive validation script checking GPU availability (nvidia-smi), Docker GPU runtime (docker run --gpus all test), IRIS database connectivity (Python connection test), IRIS table existence (query DEMO.ClinicalNoteVectors schema), NIM LLM service health (curl health endpoint on port 8001), and test inference query (simple prompt/response)
- [ ] [US5-002] Implement src/validation/health_checks.py as Python module with functions for each health check (gpu_check(), docker_gpu_check(), iris_connection_check(), iris_tables_check(), nim_llm_health_check(), nim_llm_inference_test()) returning structured results with pass/fail status and diagnostic messages
- [ ] [US5-003] Implement src/validation/test_deployment.py as pytest test suite wrapping health_checks.py functions with assertions for each validation criterion and proper test fixture setup
- [ ] [US5-004] Add GPU utilization monitoring to health_checks.py using nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv to collect metrics during active workloads
- [ ] [US5-005] Update scripts/aws/deploy.sh to call validate-deployment.sh as final step and fail deployment if any validation check does not pass
- [ ] [US5-006] Add validation section to docs/deployment-guide.md documenting expected validation output format, interpretation of health check results, and next steps if validation fails
- [ ] [US5-007] Add health monitoring section to docs/troubleshooting.md with diagnostic procedures for common failure modes: no GPU detected (check driver install, reboot), IRIS connection refused (check container running, port mapping), NIM service not responding (check container logs, API key)

**Parallel Execution Example**:
```bash
# US5-002, US5-003 can run in parallel
# US5-001 depends on US5-002 being complete
# US5-006, US5-007 can run in parallel after US5-005
```

---

## Phase 5: User Story 2 - Clinical Note Vectorization Pipeline (P2)

**Purpose**: Implement text vectorization pipeline for processing clinical documents at scale.

**Blocking Tasks**: Phase 2 (INFRA-004, INFRA-005, INFRA-006), Phase 3 (US1-004 for IRIS), Phase 4 (US5-001 for validation)

**Dependencies**: IRIS deployed (US1-004), vector DB client (INFRA-004), embedding client (INFRA-005), batch processor (INFRA-006)

### Tasks

- [ ] [US2-001] Implement src/vectorization/text_vectorizer.py as main pipeline script accepting CLI arguments (--input for JSON file path, --batch-size for documents per batch, --resume for checkpoint recovery) and using batch_processor.py for resumable execution
- [ ] [US2-002] Add document validation logic to text_vectorizer.py checking required fields (resource_id, patient_id, document_type, text_content per data-model.md) and logging validation failures to separate error log file
- [ ] [US2-003] Add text preprocessing to text_vectorizer.py for handling special characters, normalizing whitespace, and truncating content to first 10000 characters for TextContent field while using full text for embedding generation
- [ ] [US2-004] Implement batch embedding generation in text_vectorizer.py by grouping documents into batches of batch_size, calling embedding_client.py for batch embedding requests, and handling API retry logic for failed batches
- [ ] [US2-005] Implement vector storage logic in text_vectorizer.py using vector_db_client.py to insert embeddings into DEMO.ClinicalNoteVectors table with execute_safe_vector_search() utility from rag-templates for parameterized inserts
- [ ] [US2-006] Add progress tracking to text_vectorizer.py with console output showing batch X/Y, documents processed, throughput (docs/min), errors encountered, and estimated time remaining
- [ ] [US2-007] Implement SQLite state database initialization in text_vectorizer.py creating VectorizationState table per data-model.md schema and tracking document processing status for resumability
- [ ] [US2-008] Add vector similarity search test to text_vectorizer.py as optional --test-search flag performing sample query after vectorization completes and displaying top 3 results to verify database functionality
- [ ] [US2-009] Create tests/fixtures/sample_clinical_notes.json with 100 sample Synthea-format clinical notes for unit testing vectorization pipeline
- [ ] [US2-010] Implement tests/integration/test_vectorization_pipeline.py as pytest integration test running full pipeline on sample fixture data, verifying vector insertion, checkpoint creation, and resumption after simulated interruption
- [ ] [US2-011] Update docs/deployment-guide.md with vectorization section documenting command syntax, expected throughput (≥100 docs/min per SC-004), progress output format, and error log interpretation
- [ ] [US2-012] Add vectorization troubleshooting to docs/troubleshooting.md covering GPU memory exhaustion (reduce batch size), API rate limits (adjust request timing), checkpoint corruption (reset state DB), and embedding dimension mismatches

**Sequential Dependencies**:
```bash
# US2-001 foundation for all other tasks
# US2-002, US2-003 can run in parallel (both extend US2-001)
# US2-004 depends on US2-002, US2-003
# US2-005, US2-006, US2-007 can run in parallel after US2-004
# US2-008 depends on US2-005 (needs DB populated)
# US2-009, US2-010 can run in parallel after US2-008
# US2-011, US2-012 can run in parallel (documentation)
```

---

## Phase 6: User Story 4 - Multi-Modal RAG Query Processing (P2)

**Purpose**: Implement end-to-end RAG query functionality with context retrieval and LLM generation.

**Blocking Tasks**: Phase 2 (INFRA-004), Phase 3 (US1-005 for NIM LLM), Phase 5 (US2-005 for vectorized data)

**Dependencies**: Vectorized clinical notes (US2-005), NIM LLM deployed (US1-005), vector DB client (INFRA-004)

### Tasks

- [ ] [US4-001] Implement src/query/rag_pipeline.py as main query processing module with function process_query(query_text: str, top_k: int = 10) returning response and citations
- [ ] [US4-002] Add query embedding generation to rag_pipeline.py using embedding_client.py (INFRA-005) to convert query text to 1024-dim vector using same NVIDIA NIM embeddings API as vectorization pipeline
- [ ] [US4-003] Implement vector similarity search in rag_pipeline.py using vector_db_client.py (INFRA-004) with execute_safe_vector_search() utility to retrieve top_k most similar clinical notes from DEMO.ClinicalNoteVectors
- [ ] [US4-004] Add result filtering and ranking to rag_pipeline.py applying optional patient_id filter, minimum similarity threshold (e.g., 0.5), and re-ranking by document recency if timestamps are close
- [ ] [US4-005] Implement context assembly in rag_pipeline.py concatenating retrieved document TextContent fields with metadata (patient_id, document_type) and formatting for LLM prompt template
- [ ] [US4-006] Add LLM prompt template to rag_pipeline.py with system prompt instructing model to answer based only on provided context, user query, and retrieved context passages with source identifiers
- [ ] [US4-007] Implement NIM LLM API client in rag_pipeline.py calling http://localhost:8001/v1/completions with assembled prompt and parsing response to extract generated text
- [ ] [US4-008] Add citation extraction to rag_pipeline.py mapping LLM response back to source documents and formatting citations as list of (ResourceID, PatientID, DocumentType, similarity_score) tuples
- [ ] [US4-009] Add no-results handling to rag_pipeline.py detecting when vector search returns no results above threshold and returning explicit "no relevant information found" message instead of hallucinated response
- [ ] [US4-010] Implement src/validation/test_rag_query.py as CLI tool accepting --query argument, calling rag_pipeline.py, and displaying formatted output with retrieved documents, generated response, and source citations
- [ ] [US4-011] Create tests/integration/test_end_to_end_rag.py as pytest integration test with predefined queries, expected document retrievals, and validation that responses cite correct sources
- [ ] [US4-012] Update docs/deployment-guide.md with RAG query section documenting test_rag_query.py usage, example queries, expected response format (per quickstart.md example output), and performance expectations (SC-007: <5 seconds)
- [ ] [US4-013] Add RAG query troubleshooting to docs/troubleshooting.md covering slow query response (check GPU utilization, reduce top_k), irrelevant results (adjust similarity threshold), LLM errors (check NIM service logs, API connectivity)

**Sequential Dependencies**:
```bash
# US4-001 foundation
# US4-002, US4-006 can run in parallel (query embedding and prompt template)
# US4-003 depends on US4-002
# US4-004, US4-005 depend on US4-003
# US4-007 depends on US4-005, US4-006
# US4-008, US4-009 depend on US4-007
# US4-010 depends on US4-008, US4-009
# US4-011, US4-012, US4-013 can run in parallel after US4-010
```

---

## Phase 7: User Story 3 - Medical Image Vectorization (P3)

**Purpose**: Implement image vectorization pipeline for multi-modal RAG capabilities.

**Blocking Tasks**: Phase 2 (INFRA-004, INFRA-006), Phase 3 (US1-004 for IRIS)

**Dependencies**: IRIS deployed (US1-004), vector DB client (INFRA-004), batch processor (INFRA-006)

### Tasks

- [ ] [US3-001] Implement scripts/aws/deploy-nim-vision.sh to pull NVIDIA NIM Vision container (nvcr.io/nim/nvidia/nv-clip-vit:latest or equivalent), run with GPU allocation, map port 8002:8000, and wait for health endpoint
- [ ] [US3-002] Implement src/vectorization/image_vectorizer.py as main image pipeline script accepting CLI arguments (--input for image directory path, --batch-size for images per batch, --resume for checkpoint recovery, --format for DICOM/PNG/JPG filtering)
- [ ] [US3-003] Add image validation logic to image_vectorizer.py checking file format, image corruption using PIL/Pillow library, and extracting metadata (patient_id, study_id from DICOM headers or filename conventions)
- [ ] [US3-004] Add image preprocessing to image_vectorizer.py for format conversion (DICOM to PNG if needed), resizing to standard dimensions required by NIM Vision model, and normalization
- [ ] [US3-005] Implement batch image embedding generation in image_vectorizer.py calling NIM Vision API (localhost:8002) with base64-encoded images and handling API retry logic for failed batches
- [ ] [US3-006] Implement vector storage logic in image_vectorizer.py using vector_db_client.py to insert image embeddings into DEMO.MedicalImageVectors table with foreign key linkage to related ClinicalNoteVectors if RelatedReportID is available
- [ ] [US3-007] Add progress tracking to image_vectorizer.py with console output showing images processed, throughput (images/sec), file format distribution, errors encountered, and estimated time remaining
- [ ] [US3-008] Add visual similarity search test to image_vectorizer.py as optional --test-search flag using sample query image to retrieve similar images and displaying results with similarity scores
- [ ] [US3-009] Create tests/fixtures/sample_medical_images/ directory with 50 sample chest X-ray images (PNG format) and associated metadata JSON file for testing
- [ ] [US3-010] Implement tests/integration/test_image_vectorization.py as pytest integration test running pipeline on sample images, verifying vector insertion, and testing visual similarity search
- [ ] [US3-011] Update docs/deployment-guide.md with image vectorization section documenting NIM Vision deployment, image_vectorizer.py usage, MIMIC-CXR dataset integration example, and expected performance (SC-005: <2 sec/image)
- [ ] [US3-012] Add image vectorization troubleshooting to docs/troubleshooting.md covering DICOM parsing errors (dependency installation), NIM Vision OOM errors (reduce batch size, image resolution), and format conversion issues

**Sequential Dependencies**:
```bash
# US3-001 must complete before US3-005 (needs NIM Vision service)
# US3-002 foundation for pipeline tasks
# US3-003, US3-004 can run in parallel
# US3-005 depends on US3-001, US3-003, US3-004
# US3-006, US3-007 depend on US3-005
# US3-008 depends on US3-006
# US3-009, US3-010 can run in parallel after US3-008
# US3-011, US3-012 can run in parallel (documentation)
```

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Finalize documentation, add architecture diagrams, and create comprehensive examples.

**Blocking Tasks**: All user story phases (3-7) must be complete

**Dependencies**: All functional implementation complete

### Tasks

- [ ] [POLISH-001] [P] Create docs/architecture.md with system architecture diagram showing EC2 instance, GPU layer, Docker containers (IRIS, NIM LLM, NIM Vision), Python services (vectorization, query), and data flow between components
- [ ] [POLISH-002] [P] Add API reference section to docs/api-reference.md documenting NVIDIA NIM LLM endpoints (/v1/completions), NIM embeddings Cloud API, NIM Vision API, and IRIS SQL vector search query patterns
- [ ] [POLISH-003] [P] Create comprehensive example in docs/deployment-guide.md walking through end-to-end workflow: deploy system, vectorize sample dataset, run test queries, interpret results, and shut down resources
- [ ] [POLISH-004] [P] Add cost optimization section to docs/deployment-guide.md documenting instance stop/start procedures, spot instance usage, storage cleanup, and monthly cost estimates (per quickstart.md: ~$810/month)
- [ ] [POLISH-005] [P] Create tests/integration/test_gpu_inference.py as performance test measuring GPU utilization during vectorization and inference workloads, validating SC-008 (≥70% GPU utilization)
- [ ] [POLISH-006] Create scripts/aws/monitor-system.sh as continuous monitoring script collecting GPU metrics, service health, IRIS database size, and logging to timestamped files for operational visibility
- [ ] [POLISH-007] Add scaling section to docs/architecture.md discussing future enhancements for multi-instance deployment, load balancing, and high-availability configurations (noted as out-of-scope but architecturally feasible)
- [ ] [POLISH-008] Create CHANGELOG.md in specs/003-aws-nim-deployment/ documenting implementation decisions, deviations from plan (if any), lessons learned, and future improvement recommendations
- [ ] [POLISH-009] Review all error messages across scripts and Python modules ensuring they provide actionable diagnostic information and reference relevant troubleshooting documentation sections
- [ ] [POLISH-010] Final validation pass running complete deployment on fresh AWS account, executing all test suites, and verifying all success criteria (SC-001 through SC-014) are met

**Parallel Execution Example**:
```bash
# POLISH-001, POLISH-002, POLISH-003, POLISH-004, POLISH-005 can all run in parallel
# POLISH-006 can run in parallel with documentation tasks
# POLISH-007 depends on POLISH-001 (extends architecture doc)
# POLISH-008, POLISH-009 can run in parallel
# POLISH-010 must be last (comprehensive validation)
```

---

## Task Summary

### By Phase
- **Phase 1 (Setup)**: 10 tasks
- **Phase 2 (Infrastructure)**: 9 tasks
- **Phase 3 (US1 - Deployment P1)**: 8 tasks
- **Phase 4 (US5 - Validation P1)**: 7 tasks
- **Phase 5 (US2 - Text Vectorization P2)**: 12 tasks
- **Phase 6 (US4 - RAG Query P2)**: 13 tasks
- **Phase 7 (US3 - Image Vectorization P3)**: 12 tasks
- **Phase 8 (Polish)**: 10 tasks

**Total**: 81 tasks

### By User Story
- **US1 (Deployment P1)**: 8 tasks
- **US2 (Text Vectorization P2)**: 12 tasks
- **US3 (Image Vectorization P3)**: 12 tasks
- **US4 (RAG Query P2)**: 13 tasks
- **US5 (Validation P1)**: 7 tasks
- **Setup/Infrastructure/Polish**: 29 tasks

### Parallelization Potential
- **Phase 1**: 7 tasks can run in parallel (SETUP-001 to SETUP-007)
- **Phase 2**: 5 tasks can run in parallel (INFRA-001 to INFRA-005)
- **Phase 3**: 2 tasks can run in parallel (US1-004, US1-005)
- **Phase 8**: 5 tasks can run in parallel (POLISH-001 to POLISH-005)

---

## Dependency Graph

```
Phase 1 (Setup)
    └─> Phase 2 (Infrastructure)
            ├─> Phase 3 (US1 - Deployment P1)
            │       ├─> Phase 4 (US5 - Validation P1)
            │       └─> Phase 5 (US2 - Text Vectorization P2)
            │               └─> Phase 6 (US4 - RAG Query P2)
            └─> Phase 7 (US3 - Image Vectorization P3)

Phase 3, 4, 5, 6, 7 (all user stories)
    └─> Phase 8 (Polish & Final Validation)
```

### Critical Path
```
SETUP-001 → INFRA-004 → US1-001 → US1-002 → US1-003 → US1-004 → US2-001 → US2-004 → US2-005 → US4-001 → US4-010 → POLISH-010
```

**Estimated Critical Path Duration**: ~15-20 hours of development time (excluding automated deployment runtime which is ~30 minutes per quickstart.md)

---

## Testing Strategy

### Unit Tests (Isolated Component Testing)
- tests/unit/test_vector_db_client.py (INFRA-007)
- tests/unit/test_embedding_client.py (INFRA-008)
- tests/unit/test_batch_processor.py (INFRA-009)

### Integration Tests (Cross-Component Testing)
- tests/integration/test_vectorization_pipeline.py (US2-010)
- tests/integration/test_end_to_end_rag.py (US4-011)
- tests/integration/test_image_vectorization.py (US3-010)
- tests/integration/test_gpu_inference.py (POLISH-005)

### Validation Tests (System Health)
- src/validation/test_deployment.py (US5-003)
- src/validation/test_rag_query.py (US4-010)

### End-to-End Validation
- scripts/aws/validate-deployment.sh (US5-001)
- Final validation pass (POLISH-010)

---

## Success Criteria Validation

Each success criterion from spec.md is validated by specific tasks:

| Success Criterion | Validating Task | Measurement Method |
|-------------------|-----------------|-------------------|
| SC-001 (30-min deployment) | US1-006, POLISH-010 | Measure deploy.sh execution time from start to finish |
| SC-002 (95% success rate) | POLISH-010 | Run 20 fresh deployments, count successes |
| SC-003 (99.9% processing success) | US2-010 | Process sample dataset, measure success/failure ratio |
| SC-004 (100 docs/min throughput) | US2-006, US2-010 | Measure actual throughput during vectorization |
| SC-005 (2 sec/image) | US3-007, US3-010 | Time image processing during vectorization |
| SC-006 (<1 sec vector search) | US2-008, US4-003 | Measure query execution time against 100K+ vectors |
| SC-007 (<5 sec RAG response) | US4-010, US4-011 | Measure end-to-end query processing time |
| SC-008 (70% GPU utilization) | POLISH-005 | Measure nvidia-smi utilization during active workloads |
| SC-009 (99.9% uptime) | POLISH-006 | Monitor service health over 30-day period |
| SC-010 (3-min validation) | US5-001 | Measure validate-deployment.sh execution time |
| SC-011 (1-hour new user setup) | POLISH-003, POLISH-010 | Test with new team member following docs |
| SC-012 (100 concurrent queries) | US4-011 | Load test with concurrent requests |
| SC-013 (1-min resume) | US2-010 | Simulate interruption, measure restart time |
| SC-014 (<$50/month storage) | POLISH-004 | Calculate EBS costs for 100K vectors |

---

## Implementation Notes

### Constitution Compliance
- All vector SQL operations MUST use utilities from `./rag-templates/common/vector_sql_utils.py` (execute_safe_vector_search, build_safe_vector_dot_sql) per INFRA-004, US2-005, US3-006, US4-003
- Container management follows production deployment practices (not iris-devtester) per plan.md Constitution Check
- All changes are net new (no modifications to existing FHIR data or tables)

### Code Quality Standards
- All Bash scripts must include error handling (set -e, check command exit codes)
- All Python code must include docstrings and type hints
- All API clients must implement retry logic with exponential backoff
- All batch processors must support checkpoint-based resumability

### Documentation Requirements
- Every user-facing script must have --help output
- Every error message must reference troubleshooting documentation
- Every configuration template must include inline comments explaining each setting

---

## Next Steps

1. Review this task breakdown with team for validation
2. Create GitHub issues or project board with these tasks
3. Begin implementation starting with Phase 1: Setup
4. Execute phases sequentially (1 → 2 → 3/4/5/6/7 → 8)
5. Run continuous validation as components are completed
6. Final comprehensive validation (POLISH-010) before merging to main

---

**Ready for Implementation** ✅

This task breakdown provides clear, independently testable tasks organized by dependency and priority. Each task references specific files and acceptance criteria from the specification, enabling parallel development where possible while maintaining proper sequencing for blocking dependencies.
