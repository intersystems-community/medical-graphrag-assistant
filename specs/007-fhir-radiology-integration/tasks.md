# Tasks: FHIR Radiology Integration

**Input**: Design documents from `/specs/007-fhir-radiology-integration/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Required per Constitution Principle VI - TDD with Playwright UX tests included.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `mcp-server/` at repository root
- **Setup scripts**: `src/setup/`
- **Adapters**: `src/adapters/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and database schema setup

- [ ] T001 Create feature branch `007-fhir-radiology-integration` from main
- [ ] T002 [P] Create src/setup/create_patient_mapping.py skeleton with IRIS connection
- [ ] T003 [P] Create src/adapters/fhir_radiology_adapter.py skeleton with base class

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Database schema and FHIR adapter that MUST be complete before ANY user story

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Implement PatientImageMapping table DDL in src/setup/create_patient_mapping.py
- [ ] T005 Add FHIR ImagingStudy resource builder in src/adapters/fhir_radiology_adapter.py
- [ ] T006 [P] Add FHIR DiagnosticReport resource builder in src/adapters/fhir_radiology_adapter.py
- [ ] T007 Add FHIR resource POST/PUT methods for IRIS FHIR repository in src/adapters/fhir_radiology_adapter.py
- [ ] T008 Run create_patient_mapping.py to create VectorSearch.PatientImageMapping table

**Checkpoint**: Foundation ready - PatientImageMapping table exists, FHIR adapter can create resources

---

## Phase 2.5: Test Setup (TDD - Write Tests Before Implementation)

**Purpose**: Create failing tests per TDD methodology before implementing user stories

### Integration Tests (tests/integration/)

- [ ] T004a [TEST] Write failing test for PatientImageMapping table schema in tests/integration/test_fhir_radiology.py
- [ ] T005a [TEST] Write failing test for ImagingStudy resource builder in tests/integration/test_fhir_radiology.py
- [ ] T006a [TEST] Write failing test for DiagnosticReport resource builder in tests/integration/test_fhir_radiology.py
- [ ] T007a [TEST] Write failing test for FHIR POST/PUT methods in tests/integration/test_fhir_radiology.py

### Contract Tests (tests/contract/)

- [ ] T023a [P] [TEST] Write contract test for get_patient_imaging_studies in tests/contract/test_radiology_mcp_tools.py
- [ ] T024a [P] [TEST] Write contract test for get_imaging_study_details in tests/contract/test_radiology_mcp_tools.py
- [ ] T025a [P] [TEST] Write contract test for get_radiology_reports in tests/contract/test_radiology_mcp_tools.py
- [ ] T026a [P] [TEST] Write contract test for search_patients_with_imaging in tests/contract/test_radiology_mcp_tools.py
- [ ] T027a [P] [TEST] Write contract test for list_radiology_queries in tests/contract/test_radiology_mcp_tools.py
- [ ] T022a [P] [TEST] Write contract test for get_encounter_imaging in tests/contract/test_radiology_mcp_tools.py

### Playwright UX Tests (tests/ux/playwright/)

- [ ] T015a [TEST] [UX] Write Playwright test for patient name display in image search results in tests/ux/playwright/test_radiology_ui.py
- [ ] T016a [TEST] [UX] Write Playwright test for "Unlinked" fallback display in tests/ux/playwright/test_radiology_ui.py
- [ ] T014a [TEST] [UX] Write Playwright test for patient record navigation from search results in tests/ux/playwright/test_radiology_ui.py

**Checkpoint**: All tests written and verified to FAIL (red phase). Ready for implementation.

---

## Phase 3: User Story 1 - Link Radiology Images to FHIR Patients (Priority: P1)

**Goal**: Display patient name/identifier in image search results instead of "Unknown Patient"

**Independent Test**: Search for an image (e.g., "pneumonia X-ray") and verify results show valid patient identifiers linked to FHIR Patient resources

### Implementation for User Story 1

- [ ] T009 [US1] Create src/setup/import_radiology_fhir.py with main import flow skeleton
- [ ] T010 [US1] Implement patient lookup/match logic in import_radiology_fhir.py (query existing FHIR Patients)
- [ ] T011 [US1] Implement Synthea patient generation for unmatched MIMIC subjects in import_radiology_fhir.py
- [ ] T012 [US1] Implement PatientImageMapping insert logic in import_radiology_fhir.py
- [ ] T013 [US1] Modify search_medical_images MCP tool in mcp-server/fhir_graphrag_mcp_server.py to join with PatientImageMapping
- [ ] T014 [US1] Update search_medical_images response to include patient_name, patient_mrn, fhir_patient_id fields
- [ ] T015 [US1] Update mcp-server/streamlit_app.py image display to show patient name instead of "Unknown Patient"
- [ ] T016 [US1] Add "Unlinked" fallback display for images without patient mapping in streamlit_app.py
- [ ] T017 [US1] Run import_radiology_fhir.py to populate PatientImageMapping for existing MIMIC images

**Checkpoint**: Image search results now display linked patient names. Unlinked images show "Unlinked - Source ID: [subject_id]"

---

## Phase 4: User Story 2 - Associate Studies with Patient Encounters (Priority: P2)

**Goal**: Link ImagingStudy resources to FHIR Encounter resources based on study date

**Independent Test**: Query a patient's encounters and verify linked imaging studies appear under appropriate encounters

### Implementation for User Story 2

- [ ] T018 [US2] Add Encounter lookup by patient and date range in src/adapters/fhir_radiology_adapter.py
- [ ] T019 [US2] Implement 24-hour window encounter matching logic in import_radiology_fhir.py
- [ ] T020 [US2] Update ImagingStudy resource builder to include encounter reference
- [ ] T021 [US2] Create FHIR ImagingStudy resources with encounter links during import in import_radiology_fhir.py
- [ ] T022 [US2] Add get_encounter_imaging MCP tool in mcp-server/fhir_graphrag_mcp_server.py per contracts/get_encounter_imaging.json

**Checkpoint**: ImagingStudy resources have encounter references. Can query imaging by encounter.

---

## Phase 5: User Story 4 - Query FHIR Radiology Data via MCP Tools (Priority: P2)

**Goal**: Provide 6 MCP tools for querying integrated FHIR radiology data

**Independent Test**: Ask chat assistant "Show me imaging studies for patient John Smith" and verify response includes linked ImagingStudy resources

### Implementation for User Story 4

- [ ] T023 [P] [US4] Implement get_patient_imaging_studies MCP tool in mcp-server/fhir_graphrag_mcp_server.py per contracts/get_patient_imaging_studies.json
- [ ] T024 [P] [US4] Implement get_imaging_study_details MCP tool in mcp-server/fhir_graphrag_mcp_server.py per contracts/get_imaging_study_details.json
- [ ] T025 [P] [US4] Implement get_radiology_reports MCP tool in mcp-server/fhir_graphrag_mcp_server.py per contracts/get_radiology_reports.json
- [ ] T026 [P] [US4] Implement search_patients_with_imaging MCP tool in mcp-server/fhir_graphrag_mcp_server.py per contracts/search_patients_with_imaging.json
- [ ] T027 [US4] Implement list_radiology_queries MCP tool in mcp-server/fhir_graphrag_mcp_server.py per contracts/list_radiology_queries.json
- [ ] T028 [US4] Register all 6 radiology MCP tools with FastMCP server in fhir_graphrag_mcp_server.py
- [ ] T029 [US4] Add FHIR query helper methods (ImagingStudy, DiagnosticReport) in src/adapters/fhir_radiology_adapter.py

**Checkpoint**: All 6 MCP radiology tools are discoverable and callable from chat interface

---

## Phase 6: User Story 3 - Create Consistent Patient Narratives (Priority: P3)

**Goal**: Create coherent clinical "stories" by linking radiology findings to patient conditions

**Independent Test**: Select a patient with pneumonia diagnosis and verify they have appropriately linked chest X-ray with matching findings

### Implementation for User Story 3

- [ ] T030 [US3] Add condition-to-imaging matching logic in import_radiology_fhir.py (map pneumonia conditions to pneumonia X-rays)
- [ ] T031 [US3] Create FHIR DiagnosticReport resources from MIMIC radiology report text in import_radiology_fhir.py
- [ ] T032 [US3] Link DiagnosticReport to ImagingStudy during import
- [ ] T033 [US3] Add SNOMED conclusion codes extraction from report text in src/adapters/fhir_radiology_adapter.py
- [ ] T034 [US3] Create 5 demo patient narratives with coherent diagnoses, encounters, and imaging

**Checkpoint**: At least 5 patient stories available with linked diagnoses and radiology findings

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T035 [P] Add idempotent import support (re-running import doesn't create duplicates) in import_radiology_fhir.py
- [ ] T036 [P] Add unlinked images report generation in import_radiology_fhir.py (FR-007)
- [ ] T037 Add error handling and logging across all new MCP tools
- [ ] T038 [P] Update quickstart.md with actual import commands and validation steps
- [ ] T039 Run end-to-end validation per quickstart.md scenarios
- [ ] T040 Deploy and verify on EC2 instance

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **Test Setup (Phase 2.5)**: Depends on Foundational - MUST complete before implementation phases
- **US1 (Phase 3)**: Depends on Test Setup - Core patient linking (tests written first)
- **US2 (Phase 4)**: Depends on Test Setup - Can run parallel to US1
- **US4 (Phase 5)**: Depends on Test Setup - Can run parallel to US1/US2
- **US3 (Phase 6)**: Depends on US1 completion (needs patient mappings)
- **Polish (Phase 7)**: Depends on US1, US2, US4 being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Independent of US1
- **User Story 4 (P2)**: Can start after Foundational (Phase 2) - Independent of US1/US2
- **User Story 3 (P3)**: Depends on US1 completion (needs PatientImageMapping populated)

### Within Each User Story

- Database/adapter work before MCP tools
- MCP tools before UI updates
- Import scripts before validation

### Parallel Opportunities

- T002, T003 (Setup skeletons)
- T005, T006 (FHIR resource builders)
- T023, T024, T025, T026 (MCP tools in US4)
- T035, T036, T038 (Polish tasks)

---

## Parallel Example: User Story 4 (MCP Tools)

```bash
# Launch all independent MCP tool implementations together:
Task: "Implement get_patient_imaging_studies MCP tool in mcp-server/fhir_graphrag_mcp_server.py"
Task: "Implement get_imaging_study_details MCP tool in mcp-server/fhir_graphrag_mcp_server.py"
Task: "Implement get_radiology_reports MCP tool in mcp-server/fhir_graphrag_mcp_server.py"
Task: "Implement search_patients_with_imaging MCP tool in mcp-server/fhir_graphrag_mcp_server.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test image search shows patient names
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test patient linking → Deploy/Demo (MVP!)
3. Add User Story 4 → Test MCP tools → Deploy/Demo (adds AI query capability)
4. Add User Story 2 → Test encounter linking → Deploy/Demo
5. Add User Story 3 → Test patient narratives → Deploy/Demo

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (patient linking + UI)
   - Developer B: User Story 4 (MCP tools)
   - Developer C: User Story 2 (encounter linking)
3. User Story 3 waits for US1 completion

---

## Notes

- [P] tasks = different files, no dependencies
- [TEST] label indicates test tasks that MUST be completed before corresponding implementation
- [UX] label indicates Playwright tests per Constitution Principle VI
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Total tasks: 53 (40 implementation + 13 test tasks)
- Tasks by story: Setup=3, Foundational=5, Tests=13, US1=9, US2=5, US4=7, US3=5, Polish=6
