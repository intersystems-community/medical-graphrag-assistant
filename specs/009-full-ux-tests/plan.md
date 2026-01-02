# Implementation Plan: Full UX Verification Tests

**Branch**: `009-full-ux-tests` | **Date**: 2026-01-02 | **Spec**: [specs/009-full-ux-tests/spec.md](specs/009-full-ux-tests/spec.md)
**Input**: Feature specification from `/specs/009-full-ux-tests/spec.md`

## Summary

The primary requirement is to implement a comprehensive automated verification suite using Playwright and Chrome DevTools protocols to validate the production-readiness of the Medical GraphRAG Assistant on EC2. The technical approach involves creating a standalone verification package that targets the live Streamlit UI and verifies end-to-end flows including FHIR search, knowledge graph interactions, medical image retrieval, and agent memory persistence.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: Playwright, pytest, pytest-playwright, requests, intersystems-iris  
**Storage**: InterSystems IRIS (Target environment validation)  
**Testing**: pytest (Playwright integration)  
**Target Platform**: EC2 (Linux) / Chrome DevTools MCP  
**Project Type**: Single (Verification Suite package)  
**Performance Goals**: Full suite execution < 15 minutes  
**Constraints**: Must run against remote URL provided via `TARGET_URL` env var  
**Scale/Scope**: 14+ MCP tools, multi-modal search, memory editor, interactive viz  

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

1. **Library-First**: The verification suite will be implemented as a standalone test package. (Pass)
2. **CLI Interface**: The suite will be invokable via a simple `pytest` command with environment variables. (Pass)
3. **Test-First**: The test cases themselves serve as the definitive specification for "implemented features". (Pass)
4. **Integration Testing**: This feature *is* the integration testing framework for the project. (Pass)
5. **Observability**: The suite will produce structured HTML/JSON reports for easy debugging. (Pass)

## Project Structure

### Documentation (this feature)

```text
specs/009-full-ux-tests/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```text
tests/
└── ux/
    ├── playwright/      # Playwright test scripts
    │   ├── conftest.py  # Shared fixtures (browser, auth)
    │   ├── test_search.py # Multi-modal search tests
    │   ├── test_memory.py # Agent memory tests
    │   └── test_viz.py    # Visualization tests
    ├── utils/           # Test helpers (IRIS queries, etc.)
    └── config/          # Environment-specific test configs
```

**Structure Decision**: Single project structure within the existing `tests/ux/` directory to maintain consistency with the repository's testing pattern while providing a clean separation for Playwright-based tests.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Playwright Dependency | Browser automation required for Streamlit | Manual verification is non-repeatable |
| Chrome DevTools MCP | Required for deep inspection | Standard HTTP checks miss client-side rendering |
