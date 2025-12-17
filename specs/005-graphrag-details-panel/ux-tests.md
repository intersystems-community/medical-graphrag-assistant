# UX Tests: GraphRAG Details Panel Enhancement

**Feature**: 005-graphrag-details-panel
**Date**: 2025-12-10
**Target**: http://54.209.84.148:8501

## Implementation

Per project constitution (Principle VI), tests are designed for execution via **Playwright MCP server**.

**Test Files**:
- `tests/ux/playwright/medical-graphrag-mcp.spec.ts` - MCP-based test definitions (RECOMMENDED)
- `tests/ux/playwright/medical-graphrag.spec.ts` - Standalone Playwright tests (CI/CD fallback)
- `tests/ux/playwright/playwright.config.ts` - Playwright configuration

### Running Tests via Playwright MCP (Recommended)

In a Claude Code conversation with Playwright MCP connected:

```
Run UX tests for Medical GraphRAG Assistant at http://54.209.84.148:8501

Execute TC-011 through TC-015 in order using:
- browser_navigate for navigation
- browser_snapshot for page state
- browser_click for interactions
- browser_wait_for for timing

Report PASS/FAIL for each test. Stop on first failure.
```

### Running Tests via Standalone Playwright (CI/CD)

```bash
cd tests/ux/playwright
npm install
npx playwright install chromium
npm test
```

## Test Suite Overview

These tests validate the GraphRAG Details Panel feature using Playwright MCP. They should be run after the core application tests (TC-001 through TC-010).

## Prerequisites

1. Playwright MCP server connected (for MCP execution)
2. Target application accessible at http://54.209.84.148:8501
3. Core tests TC-001 through TC-010 passing

---

## Test Cases

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

## Test Suite Prompt

Copy and paste this prompt into a Claude Code conversation:

```
Run UX tests for GraphRAG Details Panel at http://54.209.84.148:8501

Execute these tests in order, stopping on first failure:

1. [TC-011] Click "Common Symptoms" button, wait for response, verify "Show Execution Details" expander visible
2. [TC-012] Click details expander, verify "Entities Found" section visible
3. [TC-013] Verify "Entity Relationships" section visible in details
4. [TC-014] Verify "Tool Execution" section visible with tools used
5. [TC-015] Verify sub-sections can be collapsed/expanded independently

For each test:
- Report PASS/FAIL status with timing
- On failure: capture screenshot, report error, STOP execution

At end: Report summary (X/5 passed for feature 005)
```

---

## Expected Results

### Success Output

```
TEST SUITE: GraphRAG Details Panel UX Tests
Target: http://54.209.84.148:8501

[PASS] TC-011 Details Expander Visible (12.5s)
[PASS] TC-012 Entity Section Visible (0.8s)
[PASS] TC-013 Graph Section Visible (0.3s)
[PASS] TC-014 Tool Execution Section Visible (0.3s)
[PASS] TC-015 Sub-Sections Collapsible (1.2s)

SUMMARY: 5/5 passed | Total: 15.1s
```

### Failure Output (Example)

```
TEST SUITE: GraphRAG Details Panel UX Tests
Target: http://54.209.84.148:8501

[PASS] TC-011 Details Expander Visible (12.5s)
[FAIL] TC-012 Entity Section Visible
  - Expected: "Entities Found" section header visible
  - Actual: Element not found within 5000ms
  - Screenshot: captured
  - Stopping execution (fail-fast)

SUMMARY: 1/5 passed, 1 failed, 3 skipped
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Details expander not found" | Check if response completed, may need longer timeout |
| "Entities Found not visible" | Verify details panel expanded, check for render errors |
| "Graph section missing" | May have < 2 entities with relationships, check data |
| "Tool section empty" | Verify execution_log is being passed to render function |
| "Sub-sections not toggling" | Check session state keys, verify st.expander behavior |

---

## Validation Checklist

After running tests, verify:

- [ ] All 5 tests pass
- [ ] Details panel renders within 1 second of expand
- [ ] Entity list shows grouped entities with scores
- [ ] Graph renders (if relationships exist) or shows fallback message
- [ ] Tool timeline shows executed tools with status icons
- [ ] Each sub-section collapses/expands independently
