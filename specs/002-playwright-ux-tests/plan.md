# Implementation Plan: Playwright UX Tests

**Branch**: `002-playwright-ux-tests` | **Date**: 2025-12-10 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-playwright-ux-tests/spec.md`

## Summary

Implement automated UX tests for the Medical GraphRAG Assistant Streamlit application using the Playwright MCP server integrated with Claude Code. Tests will run as a single conversation session, executing sequentially with fail-fast behavior. Coverage includes page load verification, example button functionality, chat input/response, sidebar tool listing, and clear chat functionality.

## Technical Context

**Language/Version**: Markdown (Claude Code prompts), Python 3.11 (target application)
**Primary Dependencies**: @playwright/mcp (MCP server), Claude Code (execution host)
**Storage**: N/A (stateless tests)
**Testing**: Playwright MCP tool calls via Claude Code conversation
**Target Platform**: Chromium browser via Playwright, targeting http://54.209.84.148:8501
**Project Type**: Single project (test suite only)
**Performance Goals**: All P1 tests complete within 2 minutes total (SC-001)
**Constraints**: 10s page load timeout, 30s AI response timeout, fail-fast on first failure
**Scale/Scope**: 5 user stories, ~12 acceptance scenarios, 10 functional requirements

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance | Notes |
|-----------|------------|-------|
| I. Authorship & Attribution | PASS | Test artifacts authored by Thomas Dyar |
| II. MCP-First Architecture | PASS | Using Playwright MCP server for all browser automation |
| III. Vector Database Purity | N/A | Tests do not interact directly with database |
| IV. Medical Data Integrity | PASS | Tests verify UI behavior, do not modify data |
| V. Graceful Degradation | PASS | Tests use fail-fast per spec, timeouts configured |

**Gate Status**: PASSED - No violations. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/002-playwright-ux-tests/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output (Playwright MCP capabilities)
├── data-model.md        # Phase 1 output (test case model)
├── quickstart.md        # Phase 1 output (how to run tests)
├── contracts/           # Phase 1 output (test protocol)
│   └── test-protocol.md # Test execution contract
├── checklists/
│   └── requirements.md  # Quality checklist
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
tests/
└── ux/
    └── playwright-mcp/
        └── test-prompts.md   # Claude Code prompts for each test
```

**Structure Decision**: Tests are executed via Claude Code conversation, not traditional test files. Test prompts define the verification steps. No compiled code required.

## Complexity Tracking

No constitution violations requiring justification.
