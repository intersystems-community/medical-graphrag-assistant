# Medical GraphRAG Assistant UX Test Suite

**Target**: http://54.209.84.148:8501
**Version**: 1.0.0
**Date**: 2025-12-10

## Execution Instructions

Run this test suite via a single Claude Code conversation with Playwright MCP tools connected.

### Prerequisites

1. Playwright MCP server connected: `claude mcp list` shows `playwright: ✓ Connected`
2. Target application accessible: `curl http://54.209.84.148:8501` returns 200

### Execution Behavior

- **Fail-fast**: Stop execution on first test failure
- **Screenshot on failure**: Capture screenshot immediately when any test fails
- **Sequential execution**: Run tests in order TC-001 through TC-010
- **Single browser context**: All tests share the same browser session

### Reporting Format

For each test, report status as:
- `[PASS] TC-XXX Test Name (duration)`
- `[FAIL] TC-XXX Test Name` with error details and screenshot
- `[SKIP] TC-XXX Test Name` (only if prior test failed)

Final summary: `X/10 passed | Total: Xs`

---

## Test Suite Prompt

Copy and paste this prompt into a Claude Code conversation:

```
Run UX tests for Medical GraphRAG Assistant at http://54.209.84.148:8501

Execute these tests in order, stopping on first failure (fail-fast):

1. [TC-001] Navigate to URL, verify page loads within 10s
2. [TC-002] Verify page title contains "Agentic Medical Chat"
3. [TC-003] Verify sidebar is visible with "Available Tools" header
4. [TC-004] Verify chat input area is present
5. [TC-005] Click "Common Symptoms" button, wait for response (30s timeout)
6. [TC-006] Click "Symptom Chart" button, verify chart appears (30s timeout)
7. [TC-007] Click "Knowledge Graph" button, verify network graph appears (30s timeout)
8. [TC-008] Type "What are common symptoms?" in chat, verify response (30s timeout)
9. [TC-009] Verify tool list contains: search_fhir_documents, hybrid_search, plot_entity_network
10. [TC-010] Click "Clear" button, verify chat history cleared

For each test:
- Report PASS/FAIL status with timing
- On failure: capture screenshot, report error, STOP execution
- On success: proceed to next test

At end: Report summary (X/10 passed, total time)
```

---

## Individual Test Definitions

### TC-001: Page Load Verification (User Story 1)

**Objective**: Verify the application loads successfully

**Steps**:
1. Use `browser_navigate` to go to http://54.209.84.148:8501
2. Wait up to 10 seconds for page to load
3. Take a `browser_snapshot` to verify content is present

**Pass Criteria**: Page loads without error, content visible

**Timeout**: 10000ms

---

### TC-002: Title Verification (User Story 1)

**Objective**: Verify the page displays the correct title

**Steps**:
1. Take `browser_snapshot` of current page
2. Search for text "Agentic Medical Chat" in page content

**Pass Criteria**: Title "Agentic Medical Chat" is visible on page

**Timeout**: 5000ms

---

### TC-003: Sidebar Visible (User Story 1)

**Objective**: Verify sidebar with tools section is visible

**Steps**:
1. Take `browser_snapshot` of current page
2. Locate sidebar element
3. Search for "Available Tools" header text

**Pass Criteria**: Sidebar visible with "Available Tools" header

**Timeout**: 5000ms

---

### TC-004: Chat Input Present (User Story 1)

**Objective**: Verify chat input area exists and is functional

**Steps**:
1. Take `browser_snapshot` of current page
2. Locate chat input element (textarea or input with chat-related placeholder)

**Pass Criteria**: Chat input element is present and visible

**Timeout**: 5000ms

---

### TC-005: Common Symptoms Button (User Story 2)

**Objective**: Verify "Common Symptoms" example button triggers AI response

**Steps**:
1. Take `browser_snapshot` to locate example buttons
2. Click element containing "Common Symptoms" text using `browser_click`
3. Wait up to 30 seconds for response to appear
4. Verify response contains medical/symptom-related content

**Pass Criteria**: Button click triggers response with medical content

**Timeout**: 30000ms

---

### TC-006: Symptom Chart Button (User Story 2)

**Objective**: Verify "Symptom Chart" button renders a visualization

**Steps**:
1. Take `browser_snapshot` to locate the button
2. Click element containing "Symptom Chart" text using `browser_click`
3. Wait up to 30 seconds for chart to render
4. Verify a chart/visualization element appears (Plotly chart container)

**Pass Criteria**: Chart visualization renders on page

**Timeout**: 30000ms

---

### TC-007: Knowledge Graph Button (User Story 2)

**Objective**: Verify "Knowledge Graph" button renders network visualization

**Steps**:
1. Take `browser_snapshot` to locate the button
2. Click element containing "Knowledge Graph" text using `browser_click`
3. Wait up to 30 seconds for graph to render
4. Verify network graph element appears (nodes/edges visualization)

**Pass Criteria**: Network graph visualization renders on page

**Timeout**: 30000ms

---

### TC-008: Manual Chat Input (User Story 3)

**Objective**: Verify manual text input produces AI response

**Steps**:
1. Locate chat input element
2. Type "What are common symptoms?" using `browser_type`
3. Submit the query (press Enter or click send)
4. Wait up to 30 seconds for response
5. Verify response contains relevant medical information

**Pass Criteria**: Manual query produces AI response

**Timeout**: 30000ms

---

### TC-009: Tool List Verification (User Story 4)

**Objective**: Verify sidebar displays expected MCP tools

**Steps**:
1. Take `browser_snapshot` of sidebar section
2. Search for tool names in sidebar content:
   - search_fhir_documents
   - hybrid_search
   - plot_entity_network

**Pass Criteria**: All three tool names are visible in sidebar

**Timeout**: 5000ms

---

### TC-010: Clear Chat (User Story 5)

**Objective**: Verify Clear button resets conversation

**Steps**:
1. Locate "Clear" button in sidebar using `browser_snapshot`
2. Click the Clear button using `browser_click`
3. Verify chat history is cleared (no previous messages visible)

**Pass Criteria**: Chat history cleared, only example buttons remain

**Timeout**: 5000ms

---

## Expected Results

### Success Output

```
TEST SUITE: Medical GraphRAG UX Tests
Target: http://54.209.84.148:8501

[PASS] TC-001 Page Load (1.2s)
[PASS] TC-002 Title Verification (0.3s)
[PASS] TC-003 Sidebar Visible (0.2s)
[PASS] TC-004 Chat Input Present (0.2s)
[PASS] TC-005 Common Symptoms Button (8.5s)
[PASS] TC-006 Symptom Chart Button (12.1s)
[PASS] TC-007 Knowledge Graph Button (15.3s)
[PASS] TC-008 Manual Chat Input (9.8s)
[PASS] TC-009 Tool List Verification (0.4s)
[PASS] TC-010 Clear Chat (0.5s)

SUMMARY: 10/10 passed | Total: 48.5s
```

### Failure Output (Example)

```
TEST SUITE: Medical GraphRAG UX Tests
Target: http://54.209.84.148:8501

[PASS] TC-001 Page Load (1.2s)
[PASS] TC-002 Title Verification (0.3s)
[FAIL] TC-003 Sidebar Visible
  - Expected: "Available Tools" header visible
  - Actual: Element not found within 5000ms
  - Screenshot: captured
  - Stopping execution (fail-fast)

SUMMARY: 2/10 passed, 1 failed, 7 skipped
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Playwright MCP not connected" | Run `claude mcp add playwright...` command |
| "Page load timeout" | Check if app is running: `curl http://54.209.84.148:8501` |
| "Element not found" | Check selector in this file, app UI may have changed |
| "AI response timeout" | LLM backend may be slow/unavailable, check AWS status |
| "Chart not rendering" | May need longer timeout, check browser console for errors |

---

## Feature 005: GraphRAG Details Panel Tests

### TC-011: Details Expander Visible

**Objective**: Verify "Show Execution Details" expander appears after a query response

**Steps**:
1. Click "Common Symptoms" example button
2. Wait for AI response to complete (30s timeout)
3. Take `browser_snapshot`
4. Search for "Show Execution Details" text

**Pass Criteria**: Expander with "Show Execution Details" is visible

**Timeout**: 35000ms

---

### TC-012: Entity Section Visible

**Objective**: Verify entity section appears when details panel is expanded

**Steps**:
1. Complete TC-011 prerequisites (response visible)
2. Click the "Show Execution Details" expander using `browser_click`
3. Take `browser_snapshot`
4. Search for "Entities Found" text

**Pass Criteria**: "Entities Found" section header is visible

**Timeout**: 5000ms

---

### TC-013: Graph Section Visible

**Objective**: Verify relationship graph section appears in details panel

**Steps**:
1. Complete TC-012 prerequisites (details expanded)
2. Take `browser_snapshot`
3. Search for "Entity Relationships" text

**Pass Criteria**: "Entity Relationships" section is visible in details panel

**Timeout**: 5000ms

---

### TC-014: Tool Execution Section Visible

**Objective**: Verify tool execution timeline appears in details panel

**Steps**:
1. Complete TC-012 prerequisites (details expanded)
2. Take `browser_snapshot`
3. Search for "Tool Execution" text

**Pass Criteria**: "Tool Execution" section is visible showing tools used

**Timeout**: 5000ms

---

### TC-015: Sub-Sections Collapsible

**Objective**: Verify each sub-section can be independently collapsed

**Steps**:
1. Complete TC-012 prerequisites (details expanded)
2. Click "Entities Found" expander header
3. Verify it collapses (content hidden)
4. Click again to expand
5. Verify it expands (content visible)

**Pass Criteria**: Sub-sections toggle independently between collapsed/expanded states

**Timeout**: 5000ms

---

## Feature 005 Test Suite Prompt

```
Run UX tests for GraphRAG Details Panel at http://54.209.84.148:8501

Execute these tests after TC-001 to TC-010:

1. [TC-011] After response, verify "Show Execution Details" expander visible
2. [TC-012] Click details expander, verify "Entities Found" section visible
3. [TC-013] Verify "Entity Relationships" section visible in details
4. [TC-014] Verify "Tool Execution" section visible with tools used
5. [TC-015] Verify sub-sections can be collapsed/expanded independently

For each test:
- Report PASS/FAIL status with timing
- On failure: capture screenshot, report error, STOP execution

At end: Report summary (X/5 passed for feature 005)
```
