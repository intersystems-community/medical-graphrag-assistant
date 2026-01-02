# Tasks: Full UX Verification Tests

Feature Branch: `009-full-ux-tests`

## Phase 1: Setup

- [ ] T001 Create project structure in tests/ux/playwright
- [ ] T002 Configure pytest-playwright with multi-reporter support in tests/ux/playwright/pytest.ini
- [ ] T003 [P] Implement environment variable validation (TARGET_URL) in tests/ux/playwright/conftest.py

## Phase 2: Foundational

- [ ] T004 Implement conditional login fixture in tests/ux/playwright/conftest.py
- [ ] T005 [P] Create Streamlit status monitor utility in tests/ux/utils/streamlit_helper.py
- [ ] T006 [P] Define reusable locators for core Streamlit components in tests/ux/playwright/locators.py

## Phase 3: User Story 1 - Full System Health Check (Priority: P1)

Goal: Verify core UI and multi-modal search on EC2.
Independent Test: `pytest tests/ux/playwright/test_search.py`

- [ ] T007 [US1] Implement UI element presence check (sidebar, input) in tests/ux/playwright/test_search.py
- [ ] T008 [US1] Implement verification for all 14+ medical tools (Search, Demographics, History, etc.) in tests/ux/playwright/test_search.py
- [ ] T009 [US1] Verify IRIS result decoding and preview display in tests/ux/playwright/test_search.py

## Phase 4: User Story 2 - Visual and Interactive Verification (Priority: P2)

Goal: Verify Plotly and streamlit-agraph rendering.
Independent Test: `pytest tests/ux/playwright/test_viz.py`

- [ ] T010 [P] [US2] Implement Plotly trace container verification in tests/ux/playwright/test_viz.py
- [ ] T011 [US2] Implement streamlit-agraph iframe/node rendering check in tests/ux/playwright/test_viz.py
- [ ] T012 [US2] Verify visualization interactivity (hover/click) in tests/ux/playwright/test_viz.py

## Phase 5: User Story 3 - Agent Memory Integrity Check (Priority: P2)

Goal: Verify memory persistence and recall on EC2.
Independent Test: `pytest tests/ux/playwright/test_memory.py`

- [ ] T013 [US3] Implement memory addition via Sidebar Memory Editor in tests/ux/playwright/test_memory.py
- [ ] T014 [US3] Verify memory persistence in sidebar list in tests/ux/playwright/test_memory.py
- [ ] T015 [US3] Verify memory recall triggering in Execution Details panel in tests/ux/playwright/test_memory.py

## Final Phase: Polish & Cross-Cutting

- [ ] T016 Finalize HTML/JSON/JUnit reporting configuration in tests/ux/playwright/conftest.py
- [ ] T017 [P] Create comprehensive README for verification suite in tests/ux/README.md
- [ ] T018 Run full system sweep and verify all pass on EC2
- [ ] T019 [US1] Verify failure reporting by running suite with an unreachable TARGET_URL

## Dependencies

1. **Foundational (Phase 2)** must complete before any User Story tasks.
2. **User Story 1 (Phase 3)** is the MVP and should be completed before P2 stories.
3. **User Story 2 & 3** are parallelizable once Phase 2 is complete.

## Parallel Execution Examples

### Parallel Track A: Visuals
- T010, T011 (Visualization rendering)

### Parallel Track B: Logic/Memory
- T013, T014 (Memory persistence)

## Implementation Strategy

1. **MVP First**: Complete Phase 1, Phase 2, and Phase 3 (US1) to establish basic connectivity and search verification.
2. **Incremental Delivery**: Complete Phase 4 (Visuals) and Phase 5 (Memory) independently.
3. **Final Pass**: Run the full suite against EC2 and verify reporting artifacts.
