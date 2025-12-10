# Feature Specification: Playwright UX Tests

**Feature Branch**: `002-playwright-ux-tests`
**Created**: 2025-12-10
**Status**: Draft
**Input**: User description: "add a basic set of UX tests of this project using playwright mcp tools"

## Clarifications

### Session 2025-12-10

- Q: How should tests handle flaky/intermittent failures from network latency or slow AI responses? → A: Fail fast - tests fail immediately on first attempt, CI pipeline handles retry logic externally
- Q: How should tests be executed - single conversation or separate prompts per test? → A: Single conversation runs all tests sequentially (establishes browser context once, consolidated reporting)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Application Accessibility Test (Priority: P1)

A developer or QA engineer wants to verify that the Medical GraphRAG Assistant web application is accessible and loads correctly, ensuring the core infrastructure is working before running more detailed tests.

**Why this priority**: This is the foundational test - if the application doesn't load, no other tests can run. It validates deployment and basic connectivity.

**Independent Test**: Can be fully tested by navigating to the application URL and verifying the page title and main elements are present. Delivers immediate value by confirming the application is running.

**Acceptance Scenarios**:

1. **Given** the Streamlit application is deployed, **When** a user navigates to the application URL, **Then** the page loads successfully within 10 seconds and displays the title "Agentic Medical Chat"
2. **Given** the application has loaded, **When** inspecting the page structure, **Then** the sidebar with available tools is visible
3. **Given** the application has loaded, **When** inspecting the page structure, **Then** the chat input area is present and enabled

---

### User Story 2 - Example Button Functionality Test (Priority: P1)

A developer wants to verify that the quick-start example buttons work correctly, allowing users to initiate pre-defined queries without manual typing.

**Why this priority**: Example buttons are the primary onboarding experience for new users. Testing them ensures the core chat functionality works end-to-end.

**Independent Test**: Can be tested by clicking each example button and verifying a response is generated. Delivers value by confirming the LLM integration and tool calling pipeline works.

**Acceptance Scenarios**:

1. **Given** the application is loaded, **When** clicking the "Common Symptoms" example button, **Then** the system processes the query and displays search results within 30 seconds
2. **Given** the application is loaded, **When** clicking the "Symptom Chart" example button, **Then** a visualization chart is rendered on the page
3. **Given** the application is loaded, **When** clicking the "Knowledge Graph" example button, **Then** a network visualization with nodes and edges is displayed

---

### User Story 3 - Chat Input and Response Test (Priority: P2)

A user wants to verify that typing a custom query and submitting it produces a relevant response from the AI assistant.

**Why this priority**: After confirming buttons work, testing manual chat input validates the core conversational interface.

**Independent Test**: Can be tested by typing a query into the chat input and verifying a response appears. Delivers value by confirming bidirectional communication with the AI works.

**Acceptance Scenarios**:

1. **Given** the application is loaded with chat input visible, **When** a user types "What are the most common symptoms?" and submits, **Then** the assistant responds with relevant medical information
2. **Given** a query has been submitted, **When** waiting for the response, **Then** a loading indicator is shown during processing
3. **Given** the assistant has responded, **When** viewing the response, **Then** the response contains readable text without error messages

---

### User Story 4 - Sidebar Tool List Verification (Priority: P2)

A developer wants to verify that the sidebar correctly displays all available MCP tools, ensuring users can discover the system's capabilities.

**Why this priority**: The tool list helps users understand what the system can do. Testing it ensures the UI accurately reflects backend capabilities.

**Independent Test**: Can be tested by inspecting the sidebar content and verifying expected tools are listed. Delivers value by confirming the tool discovery UI works.

**Acceptance Scenarios**:

1. **Given** the application is loaded, **When** viewing the sidebar, **Then** a header "Available Tools" is visible
2. **Given** the sidebar is visible, **When** reading the tool list, **Then** key tools like "search_fhir_documents", "hybrid_search", and "plot_entity_network" are displayed

---

### User Story 5 - Clear Chat Functionality Test (Priority: P3)

A user wants to verify that the clear chat button resets the conversation state, allowing fresh starts.

**Why this priority**: Lower priority as it's a utility function, not core functionality. Still important for user experience during testing cycles.

**Independent Test**: Can be tested by sending a message, clicking clear, and verifying the conversation is reset. Delivers value by confirming state management works correctly.

**Acceptance Scenarios**:

1. **Given** the application has an ongoing conversation, **When** clicking the "Clear" button in the sidebar, **Then** the chat history is cleared
2. **Given** the chat has been cleared, **When** viewing the chat area, **Then** only the example buttons are shown without previous messages

---

### Edge Cases

- What happens when the application server is unreachable? (Test should timeout after 10s and report clear error)
- How does the system handle slow network conditions? (Tests use 30s timeout for AI responses per FR-005)
- What happens when a tool call returns an error? (Out of scope - tests verify happy path only)
- How does the system behave when charts fail to render? (Out of scope - tests verify happy path only)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide automated tests that can navigate to the application URL and verify page load success
- **FR-002**: System MUST provide tests that can interact with UI elements (buttons, input fields) and verify responses
- **FR-003**: System MUST provide tests that can capture screenshots for visual verification and debugging
- **FR-004**: System MUST provide tests that can verify the presence and content of specific page elements
- **FR-005**: System MUST provide tests that can wait for dynamic content (charts, AI responses) to appear
- **FR-006**: System MUST report clear pass/fail status for each test case
- **FR-007**: System MUST handle test timeouts gracefully without crashing
- **FR-008**: Tests MUST be executable via the Playwright MCP tools integrated with Claude Code
- **FR-009**: Tests MUST fail immediately on first failure (fail-fast); retry logic is delegated to external CI pipeline
- **FR-010**: All tests MUST run within a single Claude Code conversation session (single browser context, sequential execution, consolidated reporting)

### Key Entities

- **Test Suite**: Collection of related test cases organized by user story
- **Test Case**: Individual verification scenario with setup, action, and assertion
- **Page Element**: UI component that can be located and interacted with (buttons, inputs, text)
- **Test Result**: Pass/fail outcome with optional screenshot evidence

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All P1 tests complete execution within 2 minutes total
- **SC-002**: 100% of defined test cases produce clear pass/fail results
- **SC-003**: Failed tests provide actionable diagnostic information (screenshots, element not found messages)
- **SC-004**: Tests can be run repeatedly with consistent results (no flaky tests)
- **SC-005**: Test suite covers at least 5 core user interactions (page load, button clicks, chat input, visualization, clear)

## Assumptions

- The Streamlit application is deployed and accessible at a known URL (http://54.209.84.148:8501)
- Playwright MCP server is installed and configured in Claude Code
- Tests will be run from the developer's local machine with network access to the application
- The application has a stable UI structure that tests can rely on (element locators)
- LLM backend is available and responsive during test execution
