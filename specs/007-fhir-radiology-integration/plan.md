# Implementation Plan: FHIR Radiology Integration

**Branch**: `007-fhir-radiology-integration` | **Date**: 2025-12-15 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/007-fhir-radiology-integration/spec.md`

## Summary

Integrate MIMIC-CXR radiology images with the FHIR repository by creating linkages between existing image vectors in IRIS and FHIR Patient/Encounter resources. This involves:
1. Creating a patient mapping table to connect MIMIC subject_ids to FHIR Patient IDs
2. Generating FHIR ImagingStudy and DiagnosticReport resources for radiology data
3. Adding 6 new MCP tools for querying FHIR radiology data
4. Updating the Streamlit UI to display patient context in image search results

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: MCP SDK, InterSystems IRIS DB-API, boto3 (AWS Bedrock), Synthea (patient generation)
**Storage**: InterSystems IRIS for Health (FHIR repository + vector tables)
**Testing**: pytest (unit/integration), Playwright MCP (UX tests)
**Target Platform**: AWS EC2 (g5.xlarge with NVIDIA GPU)
**Project Type**: Single project with MCP server + Streamlit UI
**Performance Goals**: <2s image search, <1s single-patient lookups
**Constraints**: Must use existing IRIS vector tables, MCP-first architecture
**Scale/Scope**: ~49 MIMIC-CXR images, ~1000 synthetic FHIR patients

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Authorship & Attribution | PASS | No AI attribution in any artifacts |
| II. MCP-First Architecture | PASS | All 6 new radiology tools exposed via MCP |
| III. Vector Database Purity | PASS | Using IRIS native vectors, no external DBs |
| IV. Medical Data Integrity | PASS | Preserving MIMIC metadata, using FHIR R4 standards |
| V. Graceful Degradation | PASS | Unlinked images show "Unlinked" status |
| VI. Test-Driven Development | PASS | 13 test tasks in Phase 2.5: 4 integration, 6 contract, 3 Playwright UX |

**Gate Status**: PASS - Proceed to Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/007-fhir-radiology-integration/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (MCP tool schemas)
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── adapters/
│   └── fhir_radiology_adapter.py    # NEW: FHIR ImagingStudy/DiagnosticReport adapter
├── setup/
│   ├── create_mimic_images_table.py # EXISTS: Vector table setup
│   ├── create_patient_mapping.py    # NEW: MIMIC-FHIR patient mapping table
│   └── import_radiology_fhir.py     # NEW: Generate FHIR resources from MIMIC
├── db/
│   └── connection.py                # EXISTS: IRIS connection
└── embeddings/
    └── nvclip_embeddings.py         # EXISTS: NV-CLIP embeddings

mcp-server/
├── fhir_graphrag_mcp_server.py      # MODIFY: Add 6 new radiology MCP tools
└── streamlit_app.py                 # MODIFY: Display patient context in images

tests/
├── contract/
│   └── test_radiology_mcp_tools.py  # NEW: MCP tool contract tests
├── integration/
│   └── test_fhir_radiology.py       # NEW: FHIR-image linking tests
└── ux/playwright/
    └── test_radiology_ui.py         # NEW: Playwright tests for image-patient UX
```

**Structure Decision**: Single project pattern. Extends existing MCP server with new radiology tools. No new services or packages required.

## Complexity Tracking

> No constitution violations requiring justification.

| Decision | Rationale |
|----------|-----------|
| Extend existing MCP server | Simpler than new server; follows existing patterns |
| Use IRIS SQL for patient mapping | Consistent with existing architecture |
| Synthea for unmatched patients | Ensures internally consistent patient records |
