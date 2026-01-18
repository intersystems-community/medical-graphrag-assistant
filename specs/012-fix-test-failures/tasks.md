# Tasks: Address remaining test failures and LSP errors

**Input**: Design documents from `/specs/012-fix-test-failures/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 [P] Ensure EC2 IRIS instance (44.200.206.67) is reachable via port 1972
- [X] T002 [P] Verify `intersystems-irispython` is installed in the local environment
- [X] T003 [P] Verify `pytest-asyncio` is installed for async tool testing

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

- [X] T004 [P] Verify all 8 IRIS tables exist on EC2 per `OPS.md`
- [X] T005 [P] Setup `NVIDIA_API_KEY` environment variable for integration tests

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Stable RAG Pipeline (Priority: P1) 🎯 MVP

**Goal**: Resolve 12 failing RAG tests by fixing imports and providing fallbacks.

**Independent Test**: `pytest tests/integration/test_end_to_end_rag.py -v` passes 100%.

### Implementation for User Story 1

- [X] T006 [P] [US1] Update import path to `from src.query.rag_pipeline import RAGPipeline` in `tests/integration/test_end_to_end_rag.py`
- [X] T007 [US1] Implement environment fallbacks (EC2 IP `44.200.206.67`) for all `os.getenv()` calls in `src/query/rag_pipeline.py`
- [X] T008 [US1] Verify RAG pipeline initialization works without environment variables set

**Checkpoint**: User Story 1 fully functional and testable independently.

---

## Phase 4: User Story 2 - Automated Vectorization (Priority: P1)

**Goal**: Resolve 2 failing vectorization tests by fixing imports and ensuring NIM connectivity.

**Independent Test**: `pytest tests/integration/test_vectorization_pipeline.py -v` passes 100%.

### Implementation for User Story 2

- [X] T009 [P] [US2] Update import paths to use `src.` prefix in `tests/integration/test_vectorization_pipeline.py`
- [X] T010 [US2] Verify connection to NV-CLIP NIM on EC2 port 8002 via `curl` health check
- [X] T011 [US2] Run vectorization pipeline tests against live EC2 environment
- [X] T011a [US2] Implement character-based truncation (32k limit) for long notes in src/vectorization/text_vectorizer.py

---

## Phase 5: User Story 3 - Reliable Tool Integration (Priority: P2)

**Goal**: Resolve async test warnings and failures in MCP tool wrappers.

**Independent Test**: `pytest tests/unit/mcp/test_tool_wrappers.py -v` passes without event loop warnings.

### Implementation for User Story 3

- [ ] T012 [US3] Add `@pytest.mark.asyncio` decorator to all test functions in `tests/unit/mcp/test_tool_wrappers.py`
- [ ] T013 [US3] Replace `run_until_complete()` with `await` for all `call_tool` invocations in `tests/unit/mcp/test_tool_wrappers.py`
- [X] T014 [US3] Refactor radiology e2e tests in `tests/e2e/test_radiology_mcp_tools.py` to use direct IRIS SQL instead of FHIR REST API
- [X] T014a [US3] Ensure `FHIRRadiologyAdapter` SQL fallbacks return standard-compliant FHIR R4 JSON (ImagingStudy/DiagnosticReport)
- [X] T014b [US3] Standardize IRIS_HOST fallback to use centralized `44.200.206.67` across all services

---

## Phase 6: User Story 4 - Clean Development Environment (Priority: P3)

**Goal**: Eliminate LSP errors and refactor legacy driver usage.

**Independent Test**: `ruff check .` and IDE diagnostics show zero errors in modified files.

### Implementation for User Story 4

- [X] T015 [P] [US4] Add type guards and assertions to ensure `self.cursor` is not None in `src/vectorization/vector_db_client.py`
- [X] T016 [US4] Replace legacy `iris` module calls with `DatabaseConnection.get_connection()` in `src/setup/reset_fhir_security.py`
- [X] T017 [US4] Remove any remaining references to `iris.createIRIS()` or `iris.IRISReference` in the codebase

**Checkpoint**: Codebase is clean, type-safe, and uses modern drivers.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final verification and documentation

- [ ] T018 [P] Update `FIXME.md` status to "RESOLVED"
- [ ] T019 [P] Verify `AGENTS.md` accurately reflects the new passing test counts
- [ ] T020 Run full test suite `pytest tests/ --ignore=tests/ux -v` and confirm 220+ passes

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Phase 1.
- **User Stories (Phases 3-6)**: Depend on Phase 2.
- **Polish (Phase 7)**: Depends on all stories being complete.

### User Story Dependencies

- **US1 (RAG)**: Independent.
- **US2 (Vectorization)**: Independent.
- **US3 (Tools)**: Independent.
- **US4 (Cleanup)**: Independent.

### Parallel Opportunities

- T006, T009, T015 can run in parallel (different files).
- US1, US2, and US3 can be implemented in parallel once Foundational phase is complete.

---

## Parallel Example: Setup & Foundation

```bash
# Verify environment together:
Task: "Ensure EC2 IRIS instance is reachable"
Task: "Verify intersystems-irispython is installed"
Task: "Verify pytest-asyncio is installed"
```

---

## Implementation Strategy

### MVP First (User Story 1 & 2)

1. Complete Setup + Foundational.
2. Fix RAG Pipeline (US1).
3. Fix Vectorization (US2).
4. **STOP and VALIDATE**: Confirm core pipelines are stable.

### Incremental Delivery

1. Fix RAG & Vectorization (MVP).
2. Remediate Async/Tool tests.
3. Pivot Radiology tests to SQL.
4. Clean up LSP and Legacy code.
