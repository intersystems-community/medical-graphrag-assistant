# Implementation Plan: Pragmatic Refactor and Radiology Fix

**Branch**: `010-refactor-radiology-fix` | **Date**: 2026-01-02 | **Spec**: [spec.md](./spec.md)

## Summary

This feature addresses the tight coupling between business logic and the MCP/UI layers by extracting search and fusion logic into a dedicated service layer in `src/search/`. It also introduces a CLI health check tool to proactively identify environment issues (like missing tables on EC2) and fixes the radiology integration regression.

## Technical Context

**Language/Version**: Python 3.10+  
**Primary Dependencies**: mcp, intersystems-iris, streamlit, boto3, networkx  
**Storage**: InterSystems IRIS (SQLUser and VectorSearch schemas)  
**Testing**: pytest, playwright  
**Target Platform**: AWS EC2 g5.xlarge (13.218.19.254)  
**Project Type**: Single project (MCP Server + Streamlit UI)  
**Performance Goals**: CLI health check < 3 seconds  
**Constraints**: Demo app - pragmatic refactoring, minimize token usage

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. IRIS-Native | ✅ Pass | Service layer uses parameterized SQL via src.db.connection |
| II. Agent-Centric Design | ✅ Pass | MCP tool signatures preserved; logic delegated to services |
| III. Medical Data Integrity | ✅ Pass | Schema verified by CLI health checks |
| IV. Observability & Memory | ✅ Pass | Health check returns detailed diagnostic JSON |
| V. Browser-First Verification | ✅ Pass | Radiology fix verified by existing Playwright UX suite |

## Project Structure

### Documentation (this feature)

```text
specs/010-refactor-radiology-fix/
├── plan.md              # This file
├── research.md          # Research findings and decisions
├── data-model.md        # Table schema verification requirements
├── quickstart.md        # Test scenarios and usage
├── contracts/           # CLI and Service layer API definitions
└── tasks.md             # Implementation tasks
```

### Source Code (repository root)

```text
src/
├── cli/                          # CLI entry point
│   ├── __init__.py
│   └── __main__.py
├── search/                       # Service layer
│   ├── fhir_search.py           # FHIR search logic
│   ├── kg_search.py             # Knowledge graph search logic
│   └── hybrid_search.py         # RRF fusion logic
├── validation/
│   └── health_checks.py         # Extended health check functions
└── db/
    └── connection.py            # (Existing)

mcp-server/
└── fhir_graphrag_mcp_server.py  # (Modified) Delegate to src/search/

tests/
├── unit/
│   └── search/                  # Service unit tests
└── integration/
    └── test_cli.py              # CLI integration tests
```

**Structure Decision**: Single project structure (Option 1). We are extending the existing `src/` hierarchy and adding a `src/cli/` package.
