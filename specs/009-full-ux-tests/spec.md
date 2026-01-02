# Feature Specification: Full UX Verification Tests

**Feature Branch**: `009-full-ux-tests`  
**Created**: 2026-01-02  
**Status**: Draft  
**Input**: User description: "full-ux-tests implement strong playwright/chrome devtool mcp/etc tests to comprehensively determine whether all the purported features are properly implemented. This app is running on EC2 (or should be while testing)"

## Clarifications

### Session 2026-01-02
- Q: Should the UX tests run against the existing "production" dataset in IRIS on EC2, or should they initialize/use a isolated "test" dataset? → A: Use existing production data (verify real environment state).
- Q: How should the test suite handle environment-specific configurations (like the EC2 URL, API keys, and timeouts) to ensure it can run against different instances? → A: Dedicated "Test Mode" env var (configures remote URL/timeouts).
- Q: Which user role(s) should the automated tests prioritize when logging in to verify feature implementation? → A: Prioritize a standard "Admin" user (access to all features), reflecting the POC nature of the app where role-based access is not yet a primary concern.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Full System Health Check (Priority: P1)

As a system administrator or developer, I want to run a comprehensive automated test suite against the EC2 instance so that I can verify all medical search and agentic features are working correctly with existing production data after a deployment.

**Why this priority**: High. This is the primary value of the feature—ensuring that the complex multi-service architecture (IRIS, NIM, Bedrock) is correctly integrated and reachable in the production environment.

**Independent Test**: Can be fully tested by triggering the test suite against a known EC2 endpoint and observing a structured pass/fail report for all core features.

**Acceptance Scenarios**:

1. **Given** the application is running on an EC2 instance with production data, **When** the comprehensive UX test suite is executed using the "Test Mode" environment variable as an Admin user, **Then** it must successfully connect to the Streamlit UI and verify the presence of core UI elements (sidebar, chat input, memory editor).
2. **Given** the test suite is running, **When** it executes a multi-modal search (text + graph + image), **Then** it must verify that results are returned from the IRIS database and displayed correctly in the UI.

---

### User Story 2 - Visual and Interactive Verification (Priority: P2)

As a QA engineer, I want the automated tests to interact with charts and graphs so that I can confirm interactive visualizations are rendering correctly on the remote server.

**Why this priority**: Medium. Interactive visualizations are a key part of the "GraphRAG" value proposition, and their rendering can be fragile across different deployment environments.

**Independent Test**: Can be tested by running specific visualization test cases that wait for Plotly/NetworkX elements to appear and become interactive.

**Acceptance Scenarios**:

1. **Given** a chart generation request, **When** the Plotly graph is rendered, **Then** the test must verify the presence of the graph container and its accessibility.
2. **Given** a knowledge graph visualization, **When** the interactive network graph is displayed, **Then** the test must verify that nodes and edges are rendered.

---

### User Story 3 - Agent Memory Integrity Check (Priority: P2)

As a developer, I want to verify that the agent memory system (remember/recall) is correctly persisting data to the IRIS database on EC2.

**Why this priority**: Medium. Memory is a critical feature for the "agentic" nature of the assistant.

**Independent Test**: Can be tested by a test case that "remembers" a unique string and then "recalls" it, verifying the match in the UI.

**Acceptance Scenarios**:

1. **Given** the Memory Sidebar is open, **When** a new memory is added via the UI, **Then** it must appear in the memory list and be searchable.
2. **Given** a user correction has been stored, **When** a subsequent related query is made, **Then** the test must verify the "Execution Details" show that memory recall was triggered.

---

### Edge Cases

- **Connectivity Issues**: What happens when the EC2 instance is unreachable or the SSH tunnel to NIM is down? (The tests must fail gracefully with specific diagnostic messages).
- **Empty Datasets**: How does the system handle tests when the IRIS database is empty or the MIMIC dataset is missing?
- **LLM Rate Limiting**: How does the test suite handle transient failures from Bedrock or NVIDIA NIM APIs?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Verification suite MUST cover core search modalities: FHIR Document Search, Knowledge Graph Search, and Hybrid Search.
- **FR-002**: Verification suite MUST cover Medical Image Search, verifying that DICOM-derived images are displayed correctly in the UI.
- **FR-003**: Verification suite MUST cover Agent Memory operations, including storage, retrieval, and the Sidebar Memory Editor.
- **FR-004**: Verification suite MUST cover Interactive Visualizations (Plotly charts and `streamlit-agraph` network graphs).
- **FR-005**: Tests MUST be executable against a remote URL (EC2 instance) provided via a dedicated "Test Mode" environment variable.
- **FR-006**: Verification suite MUST utilize browser automation to interact with the UI.
- **FR-007**: Verification suite MUST provide a comprehensive report detailing the pass/fail status of each feature.
- **FR-008**: System MUST verify that all configured medical tools are functional and return valid data in the UI context using existing datasets as an Admin user.

### Key Entities *(include if feature involves data)*

- **Test Report**: A structured document containing results, timestamps, and screenshots for failed cases.
- **Verification Suite**: The collection of automated scripts and configurations.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of core features defined in the project documentation are covered by automated verification tests.
- **SC-002**: Verification suite can be initiated with a single command and runs to completion without manual intervention.
- **SC-003**: 100% of tests pass on a correctly configured and running environment.
- **SC-004**: Total execution time for a full system sweep (all P1 and P2 stories) is under 15 minutes.
- **SC-005**: Test suite successfully identifies and reports 100% of critical failures (e.g., database disconnect, API unreachable).
