# Tasks: Playwright UX Tests

**Input**: Design documents from `/specs/002-playwright-ux-tests/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/test-protocol.md, quickstart.md

**Tests**: This feature IS a test suite. Tasks create test prompts, not code tests.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Based on plan.md structure:
- Documentation: `specs/002-playwright-ux-tests/`
- Test prompts: `tests/ux/playwright-mcp/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and test prompt directory structure

- [X] T001 Create test directory structure at tests/ux/playwright-mcp/
- [X] T002 Verify Playwright MCP server is connected via `claude mcp list`
- [X] T003 Verify target application is accessible at http://54.209.84.148:8501

---

## Phase 2: Foundational (Core Test Infrastructure)

**Purpose**: Create the master test prompt file and verification framework

**⚠️ CRITICAL**: No user story test prompts can be created until this phase is complete

- [X] T004 Create master test suite prompt in tests/ux/playwright-mcp/test-prompts.md with header, execution instructions, and screenshot-on-failure behavior
- [X] T005 Define test result reporting format (PASS/FAIL/SKIP) in tests/ux/playwright-mcp/test-prompts.md (sequential after T004)
- [X] T006 Document fail-fast behavior in tests/ux/playwright-mcp/test-prompts.md (sequential after T005)

**Checkpoint**: Foundation ready - user story test prompts can now be added

---

## Phase 3: User Story 1 - Application Accessibility Test (Priority: P1) 🎯 MVP

**Goal**: Verify the Medical GraphRAG Assistant web application loads and displays correctly

**Independent Test**: Navigate to URL, verify page title "Agentic Medical Chat" and sidebar are present

### Implementation for User Story 1

- [X] T007 [US1] Add TC-001 prompt: Navigate to http://54.209.84.148:8501 and verify page loads within 10s in tests/ux/playwright-mcp/test-prompts.md
- [X] T008 [US1] Add TC-002 prompt: Verify page title contains "Agentic Medical Chat" in tests/ux/playwright-mcp/test-prompts.md
- [X] T009 [US1] Add TC-003 prompt: Verify sidebar is visible with "Available Tools" header in tests/ux/playwright-mcp/test-prompts.md
- [X] T010 [US1] Add TC-004 prompt: Verify chat input area is present and enabled in tests/ux/playwright-mcp/test-prompts.md
- [ ] T011 [US1] Execute US1 tests independently and verify all pass

**Checkpoint**: User Story 1 complete - application accessibility verified

---

## Phase 4: User Story 2 - Example Button Functionality Test (Priority: P1)

**Goal**: Verify quick-start example buttons trigger correct responses and visualizations

**Independent Test**: Click each example button and verify appropriate response appears

### Implementation for User Story 2

- [X] T012 [US2] Add TC-005 prompt: Click "Common Symptoms" button and verify response within 30s in tests/ux/playwright-mcp/test-prompts.md
- [X] T013 [US2] Add TC-006 prompt: Click "Symptom Chart" button and verify chart renders in tests/ux/playwright-mcp/test-prompts.md
- [X] T014 [US2] Add TC-007 prompt: Click "Knowledge Graph" button and verify network graph appears in tests/ux/playwright-mcp/test-prompts.md
- [ ] T015 [US2] Execute US2 tests independently and verify all pass

**Checkpoint**: User Story 2 complete - example buttons work correctly

---

## Phase 5: User Story 3 - Chat Input and Response Test (Priority: P2)

**Goal**: Verify manual chat input produces relevant AI responses

**Independent Test**: Type a query into chat input and verify response appears

### Implementation for User Story 3

- [X] T016 [US3] Add TC-008 prompt: Type "What are common symptoms?" in chat input and verify response in tests/ux/playwright-mcp/test-prompts.md
- [ ] T017 [US3] Execute US3 tests independently and verify pass

**Checkpoint**: User Story 3 complete - manual chat input works

---

## Phase 6: User Story 4 - Sidebar Tool List Verification (Priority: P2)

**Goal**: Verify sidebar displays all available MCP tools

**Independent Test**: Inspect sidebar and verify key tools are listed

### Implementation for User Story 4

- [X] T018 [US4] Add TC-009 prompt: Verify tool list contains search_fhir_documents, hybrid_search, plot_entity_network in tests/ux/playwright-mcp/test-prompts.md
- [ ] T019 [US4] Execute US4 tests independently and verify pass

**Checkpoint**: User Story 4 complete - tool discovery UI works

---

## Phase 7: User Story 5 - Clear Chat Functionality Test (Priority: P3)

**Goal**: Verify clear chat button resets conversation state

**Independent Test**: Send a message, click clear, verify history is cleared

### Implementation for User Story 5

- [X] T020 [US5] Add TC-010 prompt: Click "Clear" button and verify chat history is cleared in tests/ux/playwright-mcp/test-prompts.md
- [ ] T021 [US5] Execute US5 tests independently and verify pass

**Checkpoint**: User Story 5 complete - clear chat functionality works

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and documentation

- [ ] T022 Execute full test suite (all 10 tests) via single Claude Code conversation
- [ ] T023 Capture final test report with timing and pass/fail summary
- [ ] T024 Update quickstart.md with any corrections from actual test execution
- [ ] T025 [P] Document any selector changes needed based on actual UI in research.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - US1 and US2 are both P1 and can run in parallel
  - US3 and US4 are both P2 and can run in parallel (after P1s)
  - US5 is P3 and depends on earlier stories being complete
- **Polish (Phase 8)**: Depends on all user story phases being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - Independent of US1/US2
- **User Story 4 (P2)**: Can start after Foundational (Phase 2) - Independent of US1/US2/US3
- **User Story 5 (P3)**: Requires chat messages to exist first (soft dependency on US3)

### Within Each User Story

- Test prompt definition before test execution
- Story complete before moving to next priority

### Parallel Opportunities

- T002 and T003 can run in parallel (Setup verification)
- US1 and US2 can be worked on in parallel (both P1)
- US3 and US4 can be worked on in parallel (both P2)
- T024 and T025 can run in parallel (Polish phase)

---

## Parallel Example: Setup Phase

```bash
# Verify prerequisites in parallel:
Task: "Verify Playwright MCP server is connected via claude mcp list"
Task: "Verify target application is accessible at http://54.209.84.148:8501"
```

## Parallel Example: P1 User Stories

```bash
# After Foundational phase, launch P1 stories in parallel:
Task: "Add TC-001 prompt for US1..."
Task: "Add TC-005 prompt for US2..."
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1 (4 tests: TC-001 to TC-004)
4. **STOP and VALIDATE**: Run US1 tests independently
5. Deploy/demo if ready - basic accessibility verified

### Incremental Delivery

1. Complete Setup + Foundational → Test infrastructure ready
2. Add User Story 1 → Test independently → 4/10 tests working (MVP!)
3. Add User Story 2 → Test independently → 7/10 tests working
4. Add User Story 3 → Test independently → 8/10 tests working
5. Add User Story 4 → Test independently → 9/10 tests working
6. Add User Story 5 → Test independently → 10/10 tests working
7. Polish phase → Full suite validated

### Test Count per User Story

| User Story | Tests | Test IDs |
|------------|-------|----------|
| US1 - Accessibility | 4 | TC-001 to TC-004 |
| US2 - Example Buttons | 3 | TC-005 to TC-007 |
| US3 - Chat Input | 1 | TC-008 |
| US4 - Tool List | 1 | TC-009 |
| US5 - Clear Chat | 1 | TC-010 |
| **Total** | **10** | TC-001 to TC-010 |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Tests are executed via Claude Code conversation with Playwright MCP
- Fail-fast: Stop on first failure (FR-009)
- Single conversation: All tests in one session (FR-010)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
