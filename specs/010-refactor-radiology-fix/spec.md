# Feature Specification: Pragmatic Refactor and Radiology Fix

**Feature Branch**: `010-refactor-radiology-fix`  
**Created**: 2026-01-02  
**Status**: Draft  
**Input**: User description: "refactor pragmatically based on recommendations, and fix radiology stuff - this is a demo app so I don't want to burn too many tokens on optimizing it, though"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Logic Decoupling for Testability (Priority: P1)

As a developer, I want core search and fusion logic to reside in dedicated service modules so that I can verify business logic using fast CLI/API tests without spawning a full browser or complex MCP server instance.

**Why this priority**: High. Current coupling makes the app fragile and slow to verify. Decoupling is the foundational step for stable development.

**Independent Test**: Can be verified by running a Python script that imports the search service and returns results directly from the terminal.

**Acceptance Scenarios**:

1. **Given** a medical search query, **When** executed via a standalone service module, **Then** it must return structured results equivalent to the current MCP tool output.
2. **Given** the MCP server, **When** a search tool is called, **Then** it must delegate execution to the new service layer.

---

### User Story 2 - System Health & Smoke Test CLI (Priority: P1)

As a system administrator, I want a simple CLI tool to verify database connectivity and schema integrity so that I can quickly diagnose environment issues like "missing tables" on EC2.

**Why this priority**: High. This directly addresses the "breaking breakthroughs" issue where environment discrepancies are discovered too late in the UX test cycle.

**Independent Test**: Can be tested by running `python -m src.cli check-health` and seeing a green report for all required IRIS tables.

**Acceptance Scenarios**:

1. **Given** an EC2 instance, **When** the CLI health check is run, **Then** it must verify the existence of `SQLUser.FHIRDocuments`, `VectorSearch.MIMICCXRImages`, and `SQLUser.Entities`.
2. **Given** a missing table, **When** the health check is run, **Then** it must output a specific error message identifying the missing resource.

---

### User Story 3 - Radiology Integration Stability (Priority: P1)

As a medical researcher, I want the radiology tools to work reliably on the production EC2 instance so that I can retrieve imaging studies and reports without encountering "table not found" errors.

**Why this priority**: High. This fixes the specific regression identified in the UX verification suite (Feature 009).

**Independent Test**: Can be tested by running the `test_radiology.py` Playwright suite and seeing all cases pass.

**Acceptance Scenarios**:

1. **Given** the application is running on EC2, **When** a radiology study is requested, **Then** the system must successfully query the `SQLUser.FHIRDocuments` table.
2. **Given** a fresh deployment, **When** the system initializes, **Then** it must ensure the `SQLUser.FHIRDocuments` table is created if it does not exist.

---

### Edge Cases

- **Environment Drift**: How does the system handle cases where IRIS is running but the FHIR namespace is missing?
- **Partial Schema**: What happens if some vector tables exist but the mapping table (`VectorSearch.PatientImageMapping`) is missing?
- **CLI Connectivity**: How does the CLI handle AWS SSO session expiration gracefully?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST decouple search logic (FHIR, KG, Hybrid) from `fhir_graphrag_mcp_server.py` into a reusable service layer in `src/search/`.
- **FR-002**: System MUST implement a Command Line Interface (CLI) for system administration tasks (health checks, smoke tests).
- **FR-003**: System MUST verify and ensure the existence of `SQLUser.FHIRDocuments` table on startup or via a setup command.
- **FR-004**: System MUST provide a mechanism to test MCP tool logic directly via Python unit tests without starting the Stdio server.
- **FR-005**: System MUST preserve existing Streamlit UX and MCP tool signatures while delegating logic to the service layer.

### Key Entities *(include if feature involves data)*

- **Service Layer**: A collection of Python modules in `src/` that encapsulate IRIS SQL and vector search logic.
- **Health Manifest**: A data structure returned by the CLI identifying the status of all required database tables and services.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 90% of code in the main tool execution handler (`call_tool`) is delegated to service modules.
- **SC-002**: System health check CLI command completes in under 3 seconds.
- **SC-003**: 100% of Radiology UX tests pass on the EC2 instance.
- **SC-004**: Implementation of a single "Smoke Test" that verifies the end-to-end search pipeline via CLI without a browser.
