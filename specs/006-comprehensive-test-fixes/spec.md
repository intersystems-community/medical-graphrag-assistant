# Feature Specification: Comprehensive Test Fixes

**Feature Branch**: `006-comprehensive-test-fixes`
**Created**: 2025-12-11
**Status**: Draft
**Input**: User description: "update/fix all tests so we have comprehensive passing tests!"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Fix Playwright E2E Test Locators (Priority: P1)

A developer runs the Playwright E2E test suite and all UI tests pass reliably. The tests use specific, unique locators that don't match multiple elements (avoiding "strict mode" violations). When tests interact with elements, they target exactly the intended component.

**Why this priority**: E2E tests validate the entire user experience. Currently 6 tests fail due to locator issues, not actual application bugs. Fixing these provides confidence that UI changes don't break functionality.

**Independent Test**: Run `npx playwright test` and verify all 15 tests pass with no "strict mode violation" errors.

**Acceptance Scenarios**:

1. **Given** the Playwright test suite, **When** TC-006 (Symptom Chart) runs, **Then** the chart locator matches exactly one Plotly element
2. **Given** the Playwright test suite, **When** TC-007 (Knowledge Graph) runs, **Then** the graph locator matches exactly the network visualization, not sidebar icons
3. **Given** the Playwright test suite, **When** Details Panel tests (TC-011 to TC-015) run, **Then** locators target specific expander sections without ambiguity

---

### User Story 2 - Fix Python Unit Test Mocks (Priority: P2)

A developer runs Python unit tests and the cache infrastructure tests pass with proper mocking. Tests that previously failed due to missing mock configurations now have the correct test fixtures and mock setups.

**Why this priority**: Unit tests catch regressions early. The 26 failing tests in cache/infrastructure modules need proper mock isolation to pass without requiring actual database/service connections.

**Independent Test**: Run `pytest tests/unit/` and verify all tests pass without external dependencies.

**Acceptance Scenarios**:

1. **Given** test_cache.py tests, **When** cache operations are tested, **Then** mock cache backends are properly configured
2. **Given** test_batch_processor.py tests, **When** batch processing is tested, **Then** mock data sources provide test fixtures
3. **Given** test_embedding_client.py tests, **When** embedding calls are tested, **Then** mock responses simulate real API behavior

---

### User Story 3 - Ensure Test Infrastructure Reliability (Priority: P3)

A developer can run the complete test suite repeatedly with consistent results. Tests don't have timing issues, flaky assertions, or environmental dependencies that cause intermittent failures.

**Why this priority**: Reliable tests enable continuous integration. Flaky tests erode confidence and waste developer time investigating false failures.

**Independent Test**: Run the full test suite 3 times consecutively and verify identical pass/fail results each time.

**Acceptance Scenarios**:

1. **Given** any test in the suite, **When** run multiple times, **Then** it produces the same result
2. **Given** Playwright tests with timeouts, **When** network latency varies, **Then** appropriate wait strategies prevent false failures
3. **Given** unit tests with mocks, **When** test order changes, **Then** tests remain independent and isolated

---

### Edge Cases

- What happens when the test target application (Streamlit) is not running? Tests should fail gracefully with clear error messages.
- How does the test suite handle slow CI environments? Timeout values should be configurable.
- What if a test creates data that persists? Cleanup hooks should ensure test isolation.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Playwright tests MUST use locators that uniquely identify single elements (use `.first()`, specific test IDs, or more targeted selectors)
- **FR-002**: Playwright tests for charts MUST use `[data-testid="stPlotlyChart"]` with appropriate specificity
- **FR-003**: Playwright tests for network graphs MUST target the specific graph container, not generic SVG elements
- **FR-004**: Python unit tests MUST mock all external dependencies (database, cache, API clients)
- **FR-005**: Test timeouts MUST be sufficient for CI environments (minimum 30 seconds for UI interactions)
- **FR-006**: Each test MUST be independent and not rely on state from other tests
- **FR-007**: Test assertions MUST include clear failure messages indicating expected vs actual values

### Key Entities

- **Test Suite**: Collection of test files organized by type (unit, integration, E2E)
- **Test Locator**: Playwright selector string used to find UI elements
- **Mock Fixture**: Test double that replaces external dependencies
- **Test Result**: Pass/fail status with optional error context

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of Playwright E2E tests pass (15/15 tests)
- **SC-002**: 100% of Python unit tests pass (109+ tests currently passing, plus 26 currently failing = 135 total)
- **SC-003**: Complete test suite runs in under 5 minutes locally
- **SC-004**: Test suite can be run 3 consecutive times with identical results (no flaky tests)
- **SC-005**: All test failures provide actionable error messages indicating root cause

## Assumptions

- The application code is correct; only test code needs updating
- Streamlit test server is available at the configured URL for E2E tests
- Python test environment has all required dependencies installed
- Test database fixtures are available for unit tests
