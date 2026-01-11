# Implementation Plan: Reset FHIR Security Configuration

**Branch**: `011-reset-fhir-security` | **Date**: 2026-01-10 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/011-reset-fhir-security/spec.md`

## Summary

Implement a security reset utility to resolve FHIR 401 Unauthorized errors by programmatically reconfiguring InterSystems IRIS user credentials, CSP application security settings, and role assignments. This will be exposed via the `fix-environment` CLI command and potentially a new standalone script.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: `intersystems-irispython`, `requests`
**Storage**: InterSystems IRIS (System Configuration)
**Testing**: `pytest`, `curl`
**Target Platform**: Docker container (Linux)
**Project Type**: Python CLI / Utility
**Performance Goals**: Reset operation < 30 seconds
**Constraints**: Must run within the container or via robust remote connection; requires SuperUser/`_SYSTEM` access initially (or ability to reset it).
**Scale/Scope**: Single instance configuration reset.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance Check |
|-----------|------------------|
| **I. IRIS-Native** | **PASS**: Will use `intersystems-irispython` native API for system management classes (`Security.Users`, `Security.Applications`). |
| **II. Agent-Centric** | **PASS**: Enhances agent reliability by fixing underlying auth issues. |
| **III. Medical Data Integrity** | **N/A**: Infrastructure task, does not modify clinical data structure. |
| **IV. Observability** | **PASS**: Will log configuration changes and verification results. |
| **V. Browser-First Verification** | **N/A**: Backend configuration task, verified via API/CLI. |

## Project Structure

### Documentation (this feature)

```text
specs/011-reset-fhir-security/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (Configuration entities)
├── quickstart.md        # Phase 1 output
└── contracts/           # Phase 1 output (N/A for CLI, but maybe internal API)
```

### Source Code

```text
src/
├── setup/
│   └── reset_fhir_security.py  # New script for security reset logic
├── cli/
│   └── __main__.py             # Update to include reset logic in fix-environment
└── validation/
    └── health_checks.py        # Update to include stricter auth check
```

## Complexity Tracking

No violations anticipated.
