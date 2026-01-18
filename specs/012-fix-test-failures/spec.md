# Feature Specification: Address remaining test failures and LSP errors documented in FIXME.md

**Feature Branch**: `012-fix-test-failures`  
**Created**: 2026-01-18  
**Status**: Draft  
**Input**: User description: "to address the items in FIXME.md."

## Clarifications

### Session 2026-01-18
- Q: How should the NVIDIA API key be managed for integration tests running against the EC2 NIM services? → A: Use `NVIDIA_API_KEY` environment variable.
- Q: Should we prioritize rewriting these skipped radiology tests to use direct IRIS SQL queries instead of the FHIR REST API? → A: Rewrite tests to use direct IRIS SQL queries.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Stable RAG Pipeline (Priority: P1)

As a developer, I want the RAG pipeline tests to pass so I can trust the search functionality when building agentic workflows.

**Why this priority**: The RAG pipeline is the core of the medical assistant. If tests are failing due to path issues or missing defaults, the system is fundamentally unreliable.

**Independent Test**: Can be fully tested by running `pytest tests/integration/test_end_to_end_rag.py` against the EC2 environment and delivers a stable search foundation.

**Acceptance Scenarios**:

1. **Given** the EC2 IRIS database is running, **When** I run the end-to-end RAG tests, **Then** all 12 tests in `test_end_to_end_rag.py` pass without import errors.
2. **Given** missing environment variables for IRIS connection, **When** the RAG pipeline initializes, **Then** it falls back to safe EC2 defaults instead of failing with NoneType errors.

---

### User Story 2 - Automated Vectorization (Priority: P1)

As a developer, I want the vectorization pipeline tests to pass so I know new clinical documents are correctly transformed into vectors and indexed.

**Why this priority**: Data ingestion is the first step in the pipeline. Failure here means the system cannot learn from new data.

**Independent Test**: Can be fully tested by running `pytest tests/integration/test_vectorization_pipeline.py` and delivers a functional data ingestion path.

**Acceptance Scenarios**:

1. **Given** the NV-CLIP service is active on EC2, **When** I run the vectorization pipeline tests, **Then** documents are correctly embedded and stored in IRIS.

---

### User Story 3 - Reliable Tool Integration (Priority: P2)

As a developer, I want the MCP tool wrappers to be properly tested for async behavior so that the agent can call tools without runtime hangs or race conditions.

**Why this priority**: The MCP server bridges the LLM and the medical data. Async issues can lead to difficult-to-debug production failures.

**Independent Test**: Can be fully tested by running `pytest tests/unit/mcp/test_tool_wrappers.py` using modern async test markers.

**Acceptance Scenarios**:

1. **Given** async unit tests for MCP tools, **When** I run the tests, **Then** they are properly awaited and finish without event loop errors.

---

### User Story 4 - Clean Development Environment (Priority: P3)

As a developer, I want the codebase to be free of LSP errors and legacy API calls so I can focus on new features instead of maintenance noise.

**Why this priority**: Clean code reduces the codebase's cognitive load for new contributors and prevents real bugs from being hidden by noise.

**Independent Test**: Can be fully tested by running `ruff check .` or checking IDE diagnostics and delivers a developer-friendly codebase.

**Acceptance Scenarios**:

1. **Given** `src/vectorization/vector_db_client.py`, **When** I check diagnostics, **Then** there are no "None" attribute errors.
2. **Given** `src/setup/reset_fhir_security.py`, **When** I run the script, **Then** it uses the current `intersystems-irispython` driver correctly.

---

### Edge Cases

- **What happens when the EC2 instance is unreachable?** Tests should skip gracefully with a clear "Environment not available" message rather than crashing with tracebacks.
- **How does the system handle extremely long clinical notes?** The vectorization pipeline should handle notes exceeding standard token limits by either chunking or reporting a controlled error.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support correct import paths for `RAGPipeline` (using `src.` prefix) across all test suites.
- **FR-002**: System MUST use valid default connection parameters (EC2 IP 44.200.206.67) for the RAG pipeline when environment variables are missing.
- **FR-003**: System MUST support vectorization of clinical notes using the NVIDIA NIM embeddings endpoint on EC2.
- **FR-004**: System MUST handle asynchronous MCP tool calls correctly in unit tests using `@pytest.mark.asyncio` and proper `await` keywords.
- **FR-005**: System MUST be compatible with the `intersystems-irispython` driver across all setup scripts, avoiding the legacy `iris` module attributes.
- **FR-006**: Integration tests MUST retrieve external service credentials (e.g., `NVIDIA_API_KEY`) from environment variables.
- **FR-007**: Radiology e2e tests MUST be updated to use direct IRIS SQL queries instead of the FHIR REST API.

### Key Entities *(include if feature involves data)*

- **RAGPipeline**: The central coordinator for embedding generation, vector search, and result fusion.
- **ClinicalNoteVectorizer**: Service responsible for batch processing FHIR documents into IRIS vectors.
- **IRISVectorDBClient**: Low-level client for IRIS SQL and vector operations.

## Architectural Strategy: SQL Fallback Mode

To ensure the assistant remains functional in environments without a full InterSystems HealthShare FHIR repository (like the current EC2 instance), the system implements a **SQL Fallback Mode**.

- **Pragmatic Choice**: When FHIR REST endpoints are unreachable, adapters MUST fallback to querying `SQLUser` or `VectorSearch` tables directly.
- **Contract Integrity**: Fallback results MUST be transformed into valid FHIR R4 JSON structures before being returned to the MCP server. This preserves the "Medical Data Integrity" principle for downstream agent logic.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of integration tests in `tests/integration/test_end_to_end_rag.py` pass against the EC2 environment.
- **SC-002**: 100% of integration tests in `tests/integration/test_vectorization_pipeline.py` pass against the EC2 environment.
- **SC-003**: 100% of unit tests in `tests/unit/mcp/test_tool_wrappers.py` pass without event loop warnings.
- **SC-004**: Zero LSP errors related to NoneType or missing attributes in the modified source files.
- **SC-005**: Total project test pass rate exceeds 220 tests (verified against LIVE EC2).

## Assumptions

- EC2 instance `44.200.206.67` is running and accessible via the specified ports (1972, 8002).
- The `FIXME.md` file correctly identifies the 16 primary failure points.
- Local developer machine has appropriate SSH keys (`~/.ssh/fhir-ai-key-recovery.pem`) for connectivity verification if needed.
