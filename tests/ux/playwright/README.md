# Medical GraphRAG UX Tests

Playwright-based UX tests for the Medical GraphRAG Assistant Streamlit application.

**IMPORTANT**: Per project constitution (Principle VI), these tests are designed to be executed via the **Playwright MCP server** for consistency.

## Recommended: Execute via Playwright MCP Server

The preferred method is to run tests through Claude Code with Playwright MCP connected:

```bash
# In Claude Code conversation with Playwright MCP enabled:
# Copy the execution prompt from medical-graphrag-mcp.spec.ts
```

### Quick Execution Prompt

```
Run UX tests for Medical GraphRAG Assistant at http://54.209.84.148:8501

Execute TC-001 through TC-015 in order using:
- browser_navigate for navigation
- browser_snapshot for page state
- browser_click for interactions
- browser_type for input
- browser_wait_for for timing

Report PASS/FAIL for each test. Stop on first failure.
```

## Alternative: Standalone Playwright

If you need to run tests outside of MCP (e.g., CI/CD):

```bash
cd tests/ux/playwright
npm install
npx playwright install chromium
npm test
```

### Run with browser visible
```bash
npm run test:headed
```

### Run specific test
```bash
npx playwright test -g "TC-011"
```

## Test Target

Default target: `http://54.209.84.148:8501`

To test against a different URL:
```bash
TARGET_URL=http://localhost:8501 npm test
```

## Test Cases

### Core Application (TC-001 to TC-010)
- TC-001: Page loads successfully
- TC-002: Title contains "Agentic Medical Chat"
- TC-003: Sidebar visible with "Available Tools" header
- TC-004: Chat input area is present
- TC-005: Common Symptoms button triggers AI response
- TC-006: Symptom Chart button renders visualization
- TC-007: Knowledge Graph button renders network graph
- TC-008: Manual chat input produces AI response
- TC-009: Sidebar displays expected MCP tools
- TC-010: Clear button resets conversation

### Feature 005: GraphRAG Details Panel (TC-011 to TC-015)
- TC-011: Details expander visible after query response
- TC-012: Entity section visible when details panel expanded
- TC-013: Graph section visible in details panel
- TC-014: Tool execution section visible in details panel
- TC-015: Sub-sections are independently collapsible

## View Test Report

After running tests:
```bash
npm run report
```
