# Quickstart: Running Playwright UX Tests

**Feature**: 002-playwright-ux-tests
**Date**: 2025-12-10

## Prerequisites

1. **Claude Code CLI** installed and authenticated
2. **Playwright MCP server** configured:
   ```bash
   claude mcp add playwright --transport stdio -- npx -y @playwright/mcp@latest
   ```
3. **Target application** running at http://54.209.84.148:8501

## Verify Setup

```bash
# Check Playwright MCP is connected
claude mcp list
# Should show: playwright: npx -y @playwright/mcp@latest - ✓ Connected
```

## Run All Tests

Start a new Claude Code conversation and paste:

```
Run the Medical GraphRAG Assistant UX test suite.

Target: http://54.209.84.148:8501

Execute tests in sequence (fail-fast):
1. TC-001: Page load verification (10s timeout)
2. TC-002: Title "Agentic Medical Chat" present
3. TC-003: Sidebar visible with "Available Tools"
4. TC-004: Chat input area present
5. TC-005: "Common Symptoms" button works (30s)
6. TC-006: "Symptom Chart" renders chart (30s)
7. TC-007: "Knowledge Graph" renders network (30s)
8. TC-008: Manual chat query works (30s)
9. TC-009: Tool list verification
10. TC-010: Clear chat functionality

On failure: screenshot + stop. Report final summary.
```

## Run Single Test

For debugging a specific test:

```
Test TC-005 only on http://54.209.84.148:8501:
1. Navigate to URL
2. Click "Common Symptoms" button
3. Wait up to 30 seconds for response
4. Verify response contains medical content
5. Take screenshot of result
```

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

### Failure Output

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

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Playwright MCP not connected" | Run `claude mcp add playwright...` command |
| "Page load timeout" | Check if app is running: `curl http://54.209.84.148:8501` |
| "Element not found" | Check selector in research.md, app may have updated |
| "AI response timeout" | LLM backend may be slow/unavailable, check AWS status |

## CI Integration

For automated pipelines, use Claude Code's `-p` (print) mode:

```bash
echo "Run UX test suite on http://54.209.84.148:8501..." | claude -p
```

Retry logic should be handled by the CI system (per FR-009).
