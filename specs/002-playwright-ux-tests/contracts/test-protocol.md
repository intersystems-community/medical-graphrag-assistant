# Test Protocol Contract

**Version**: 1.0.0
**Date**: 2025-12-10

## Test Execution Contract

### Prerequisites

Before running the test suite:
1. Playwright MCP server must be connected (`claude mcp list` shows `playwright: ✓ Connected`)
2. Target application must be accessible at http://54.209.84.148:8501
3. Network connectivity from test machine to AWS instance

### Execution Interface

Tests are executed as a single Claude Code conversation. The conversation prompt follows this structure:

```
Run UX tests for Medical GraphRAG Assistant at http://54.209.84.148:8501

Execute these tests in order, stopping on first failure (fail-fast):

1. [TC-001] Navigate to URL, verify page loads within 10s
2. [TC-002] Verify page title contains "Agentic Medical Chat"
3. [TC-003] Verify sidebar is visible with "Available Tools" header
4. [TC-004] Verify chat input area is present
5. [TC-005] Click "Common Symptoms" button, wait for response (30s timeout)
6. [TC-006] Click "Symptom Chart" button, verify chart appears
7. [TC-007] Click "Knowledge Graph" button, verify network graph appears
8. [TC-008] Type "What are common symptoms?" in chat, verify response
9. [TC-009] Verify tool list contains: search_fhir_documents, hybrid_search, plot_entity_network
10. [TC-010] Click "Clear" button, verify chat history cleared

For each test:
- Report PASS/FAIL status
- On failure: capture screenshot, report error, stop execution
- On success: proceed to next test

At end: Report summary (X/10 passed, total time)
```

### Response Contract

Claude Code will respond with structured output:

```yaml
TestSuiteResult:
  suiteName: "Medical GraphRAG UX Tests"
  targetUrl: string
  totalTests: number
  passed: number
  failed: number
  skipped: number
  totalDuration: number  # milliseconds
  results:
    - testId: string
      name: string
      status: PASS | FAIL | SKIP
      duration: number
      error: string | null
      screenshot: string | null
```

### Playwright MCP Tool Usage

| Test Action | Playwright MCP Tool | Parameters |
|------------|---------------------|------------|
| Navigate | `browser_navigate` | `{url: "http://54.209.84.148:8501"}` |
| Click button | `browser_click` | `{element: "button", ref: "button text"}` |
| Type text | `browser_type` | `{element: "input", text: "query"}` |
| Wait for element | `browser_wait` | `{selector: "...", timeout: N}` |
| Capture screenshot | `browser_screenshot` | `{}` |
| Get page snapshot | `browser_snapshot` | `{}` |

### Timeout Specifications

| Test Category | Default Timeout | Override Allowed |
|--------------|-----------------|------------------|
| Navigation | 10000ms | No |
| Element location | 5000ms | No |
| AI response wait | 30000ms | No |
| Screenshot capture | 3000ms | No |

### Failure Handling

1. **On Test Failure**:
   - Immediately capture screenshot
   - Log error message with selector/action details
   - Report FAIL status with diagnostic info
   - Skip remaining tests (fail-fast per FR-009)

2. **On Timeout**:
   - Treat as FAIL
   - Capture screenshot of current state
   - Report which element/action timed out

3. **On Network Error**:
   - Report ERROR status
   - Include network error details
   - Recommend checking application availability
