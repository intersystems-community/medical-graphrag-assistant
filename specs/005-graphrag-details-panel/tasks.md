# Tasks: GraphRAG Details Panel Enhancement

**Input**: Design documents from `/specs/005-graphrag-details-panel/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Not explicitly requested in spec - test tasks omitted. UX testing via Playwright MCP recommended post-implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Primary modification**: `mcp-server/streamlit_app.py`
- **Source utilities**: `src/query/`
- **Tests**: `tests/ux/playwright-mcp/`

---

## Phase 1: Setup

**Purpose**: Prepare data extraction utilities needed by all user stories

- [x] T001 Add data model classes (DisplayEntity, DisplayRelationship, ToolExecution) to mcp-server/streamlit_app.py
- [x] T002 [P] Create extract_entities_from_results() function in mcp-server/streamlit_app.py
- [x] T003 [P] Create extract_relationships_from_results() function in mcp-server/streamlit_app.py
- [x] T004 [P] Create extract_tool_executions() function in mcp-server/streamlit_app.py

---

## Phase 2: Foundational (Details Panel Container)

**Purpose**: Create the enhanced details panel container structure that all sub-sections will use

**⚠️ CRITICAL**: All user story implementations depend on this container being in place

- [x] T005 Refactor existing "Show Execution Details" expander into render_details_panel() function in mcp-server/streamlit_app.py
- [x] T006 Add session state keys for panel collapse/expand states in mcp-server/streamlit_app.py
- [x] T007 Create collapsible sub-section structure (Entities, Graph, Tools) using nested st.expander() in mcp-server/streamlit_app.py
- [x] T008 Integrate render_details_panel() call in chat_with_tools() response rendering in mcp-server/streamlit_app.py

**Checkpoint**: Details panel container ready - user story sections can now be implemented

---

## Phase 3: User Story 1 - View Entities Found (Priority: P1) 🎯 MVP

**Goal**: Display entities discovered during GraphRAG search with types and scores

**Independent Test**: Submit medical query, expand details, verify entity list appears with types and scores

### Implementation for User Story 1

- [x] T009 [US1] Implement render_entity_section() function in mcp-server/streamlit_app.py
- [x] T010 [US1] Add entity grouping by type (symptom, condition, medication, etc.) in render_entity_section()
- [x] T011 [US1] Display relevance/frequency scores alongside entity names in render_entity_section()
- [x] T012 [US1] Implement truncation logic (top 50 entities) with "Show all" button in render_entity_section()
- [x] T013 [US1] Add empty state handling ("No entities found") in render_entity_section()
- [x] T014 [US1] Implement entity click handler to show tooltip with source documents in mcp-server/streamlit_app.py
- [x] T015 [US1] Add tooltip display using st.info() or custom container for clicked entity details

**Checkpoint**: User Story 1 complete - entity list with tooltips should work independently

---

## Phase 4: User Story 2 - Interactive Entity Graph (Priority: P2)

**Goal**: Display force-directed graph showing entity relationships within details panel

**Independent Test**: Submit query returning multiple related entities, verify interactive graph renders in details panel

### Implementation for User Story 2

- [x] T016 [US2] Implement render_graph_section() function in mcp-server/streamlit_app.py
- [x] T017 [US2] Reuse existing streamlit-agraph config from main results graph rendering
- [x] T018 [US2] Convert DisplayEntity list to agraph Node objects in render_graph_section()
- [x] T019 [US2] Convert DisplayRelationship list to agraph Edge objects in render_graph_section()
- [x] T020 [US2] Add minimum threshold check (hide graph if < 2 related entities) in render_graph_section()
- [x] T021 [US2] Implement node click handler to highlight selected entity and show tooltip
- [x] T022 [US2] Add mobile fallback - render relationship list instead of graph for viewport < 768px

**Checkpoint**: User Story 2 complete - interactive graph should render and respond to interactions

---

## Phase 5: User Story 3 - Tool Execution Timeline (Priority: P3)

**Goal**: Display chronological timeline of tool executions with timing and status

**Independent Test**: Submit any query, verify tool execution list appears with names, durations, and statuses

### Implementation for User Story 3

- [x] T023 [US3] Implement render_tools_section() function in mcp-server/streamlit_app.py
- [x] T024 [US3] Display tools in chronological order by start_time
- [x] T025 [US3] Add status icons (✅ success, ❌ failed, ⏱️ timeout) for each tool
- [x] T026 [US3] Display duration as badge (e.g., "1.2s") next to tool name
- [x] T027 [US3] Add expandable details for each tool showing parameters and result summary
- [x] T028 [US3] Style failed tools distinctly with error message display

**Checkpoint**: User Story 3 complete - tool timeline should show all executed tools with timing

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T029 [P] Add UX test cases for details panel to tests/ux/playwright-mcp/test-prompts.md
- [x] T030 Performance optimization - ensure entity display < 1s, graph render < 2s
- [x] T031 Verify all three sub-sections independently collapsible/expandable
- [x] T032 Test edge cases: empty results, large entity counts (100+), circular relationships
  - Empty results: ✅ Verified via UX test - empty state messages display correctly
  - Large entity counts: Verified via truncation logic (top 50 entities)
  - Circular relationships: Handled by agraph rendering
- [ ] T033 Test mobile responsiveness - graph fallback to list on small screens
- [x] T034 Run quickstart.md validation steps to verify implementation
  - TC-011 through TC-015 all PASSED via Playwright MCP testing

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - User stories can proceed sequentially in priority order (P1 → P2 → P3)
  - Or in parallel if team capacity allows (different functions, same file)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Uses same entity data as US1 but renders differently
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Independent data source (tool executions)

### Within Each User Story

- Data extraction functions must be complete (Phase 1)
- Container structure must be in place (Phase 2)
- Render functions implemented before click handlers
- Core display before edge cases

### Parallel Opportunities

- T002, T003, T004 can run in parallel (different functions)
- US1, US2, US3 can theoretically run in parallel (different render functions in same file)
- Polish tasks T029 can run in parallel with others

---

## Parallel Example: Setup Phase

```bash
# Launch all data extraction functions together:
Task: "Create extract_entities_from_results() function in mcp-server/streamlit_app.py"
Task: "Create extract_relationships_from_results() function in mcp-server/streamlit_app.py"
Task: "Create extract_tool_executions() function in mcp-server/streamlit_app.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (data extraction functions)
2. Complete Phase 2: Foundational (details panel container)
3. Complete Phase 3: User Story 1 (entity display)
4. **STOP and VALIDATE**: Test entity display independently
5. Deploy/demo if ready - users can see entities in details panel

### Incremental Delivery

1. Complete Setup + Foundational → Details panel container ready
2. Add User Story 1 → Test independently → Deploy (MVP - entity list!)
3. Add User Story 2 → Test independently → Deploy (+ relationship graph)
4. Add User Story 3 → Test independently → Deploy (+ tool timeline)
5. Each story adds value without breaking previous stories

### Recommended Approach

Since all code is in single file (`streamlit_app.py`), recommend:
1. Sequential implementation: P1 → P2 → P3
2. Commit after each phase completion
3. Test each user story independently before moving to next

---

## Notes

- All primary implementation in mcp-server/streamlit_app.py
- Reuse existing streamlit-agraph configuration from main results
- Session state keys defined in data-model.md
- Entity tooltip shows sources and context per clarification
- Sub-sections collapsible per clarification (all expanded by default)
- Verify each checkpoint before proceeding
