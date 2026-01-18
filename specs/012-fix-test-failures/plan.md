# Implementation Plan: Address remaining test failures and LSP errors

**Branch**: `012-fix-test-failures` | **Date**: 2026-01-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/012-fix-test-failures/spec.md`

## Summary

The primary goal is to resolve 16 failing tests and multiple LSP diagnostics to stabilize the medical assistant's core RAG and vectorization pipelines. The approach involves normalizing import paths, providing sensible environment variable fallbacks for the EC2 environment, remediating async test issues, and pivoting radiology e2e tests to use direct IRIS SQL instead of the unavailable FHIR REST API.

## Technical Context

**Language/Version**: Python 3.12+  
**Primary Dependencies**: `intersystems-irispython`, `pytest-asyncio`, `ruff`  
**Storage**: InterSystems IRIS (SQL + Vector)  
**Testing**: `pytest`, `playwright`  
**Target Platform**: AWS EC2 (g5.xlarge)  
**Project Type**: Single project  
**Performance Goals**: Sub-second vector search response time (verified via integration tests)  
**Constraints**: Must run against live EC2 IRIS instance without mocks  
**Scale/Scope**: ~220 tests total, focused on 16 specific failure points  

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. IRIS-Native**: Using `intersystems-irispython` and parameterized SQL. (PASS)
- **II. Agent-Centric**: Fixing MCP tool wrapper tests to ensure reliable agent interaction. (PASS)
- **III. Medical Data Integrity**: Verifying clinical note vectorization against IRIS schemas. (PASS)
- **IV. Observability & Memory**: Ensuring memory vector tests pass. (PASS)
- **V. Browser-First Verification**: Excluding Playwright tests from backend fix runs but maintaining their integrity. (PASS)

## Project Structure

### Documentation (this feature)

```text
specs/012-fix-test-failures/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── checklists/          # Validation checklists
└── spec.md              # Feature specification
```

### Source Code (repository root)

```text
src/
├── adapters/            # FHIR and database adapters
├── db/                  # Connection management
├── query/               # RAG pipeline logic
└── vectorization/       # Document processing and embedding

tests/
├── e2e/                 # Radiology and UI tests
├── integration/         # Database and pipeline tests
├── unit/                # Component logic and tool wrapper tests
└── conftest.py          # Global test configuration
```

**Structure Decision**: Single project structure. Core logic remains in `src/` and tests are organized in `tests/` by type (unit, integration, e2e).

## Complexity Tracking

*No violations detected.*
