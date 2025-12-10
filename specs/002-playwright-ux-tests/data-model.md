# Data Model: Playwright UX Tests

**Date**: 2025-12-10
**Feature**: 002-playwright-ux-tests

## Test Case Entity

```yaml
TestCase:
  id: string                    # Unique identifier (e.g., "TC-001")
  name: string                  # Human-readable name
  priority: enum[P1, P2, P3]    # Execution priority
  userStory: string             # Reference to spec user story
  preconditions: string[]       # Required state before test
  steps: TestStep[]             # Ordered execution steps
  expectedResult: string        # What success looks like
  timeout: number               # Max duration in milliseconds
```

## Test Step Entity

```yaml
TestStep:
  action: enum[navigate, click, type, wait, screenshot, verify]
  selector: string | null       # Element selector (if applicable)
  value: string | null          # Input value (if applicable)
  timeout: number               # Step-specific timeout
  description: string           # Human-readable step description
```

## Test Result Entity

```yaml
TestResult:
  testCaseId: string
  status: enum[PASS, FAIL, SKIP, ERROR]
  duration: number              # Actual execution time (ms)
  error: string | null          # Error message if failed
  screenshot: string | null     # Path to screenshot (if captured)
  timestamp: datetime
```

## Test Suite Entity

```yaml
TestSuite:
  name: string                  # "Medical GraphRAG UX Tests"
  version: string               # Test suite version
  targetUrl: string             # http://54.209.84.148:8501
  tests: TestCase[]
  executionMode: "sequential"
  failFast: true
```

## Defined Test Cases

| ID | Name | Priority | User Story | Timeout |
|----|------|----------|------------|---------|
| TC-001 | Page Load | P1 | Story 1 | 10000ms |
| TC-002 | Title Verification | P1 | Story 1 | 5000ms |
| TC-003 | Sidebar Visible | P1 | Story 1 | 5000ms |
| TC-004 | Chat Input Present | P1 | Story 1 | 5000ms |
| TC-005 | Common Symptoms Button | P1 | Story 2 | 30000ms |
| TC-006 | Symptom Chart Button | P1 | Story 2 | 30000ms |
| TC-007 | Knowledge Graph Button | P1 | Story 2 | 30000ms |
| TC-008 | Manual Chat Input | P2 | Story 3 | 30000ms |
| TC-009 | Tool List Verification | P2 | Story 4 | 5000ms |
| TC-010 | Clear Chat | P3 | Story 5 | 5000ms |

## State Transitions

```
[Not Started] --> [Running] --> [Passed]
                     |
                     +--> [Failed] --> (screenshot captured)
                     |
                     +--> [Error] --> (exception logged)
```
