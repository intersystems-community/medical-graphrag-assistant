# Implementation Plan: GraphRAG Details Panel Enhancement

**Branch**: `005-graphrag-details-panel` | **Date**: 2025-12-10 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-graphrag-details-panel/spec.md`

## Summary

Enhance the existing "Show Execution Details" dropdown in the Streamlit chat interface to display GraphRAG information including discovered entities, their relationships via interactive force-directed graph, and tool execution timeline. The implementation will reuse the existing `streamlit-agraph` component for visual consistency with main results.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: Streamlit, streamlit-agraph, Plotly (fallback)
**Storage**: InterSystems IRIS (existing - no changes required)
**Testing**: pytest, Playwright MCP for UX tests
**Target Platform**: AWS EC2 (Linux), Web browser clients
**Project Type**: Single project (Streamlit application)
**Performance Goals**: Entity display <1s, graph render <2s for 50 nodes, interaction response <100ms
**Constraints**: Mobile-responsive (graph fallback to list <768px width)
**Scale/Scope**: Up to 50 entities displayed by default, expandable to full set

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Authorship & Attribution | ✅ PASS | No AI attribution in any artifacts |
| II. MCP-First Architecture | ✅ PASS | Using existing MCP tools for GraphRAG data |
| III. Vector Database Purity | ✅ PASS | No new databases; using existing IRIS |
| IV. Medical Data Integrity | ✅ PASS | Display-only; no modification of medical data |
| V. Graceful Degradation | ✅ PASS | Empty state handling, graph fallback to list |

**Gate Result**: PASS - All principles satisfied

## Project Structure

### Documentation (this feature)

```text
specs/005-graphrag-details-panel/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (internal component contracts)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
mcp-server/
├── streamlit_app.py     # Primary modification target
│   ├── render_details_panel()      # NEW: Render enhanced details
│   ├── render_entity_section()     # NEW: Entity list with tooltips
│   ├── render_graph_section()      # NEW: Force-directed graph in details
│   └── render_tools_section()      # NEW: Tool execution timeline
└── components/
    └── details_panel.py            # NEW: Extracted component (optional refactor)

src/
├── query/
│   └── fhir_graphrag_query.py      # Minor: Ensure entity/relationship data exposed
└── [existing structure unchanged]

tests/
├── ux/
│   └── playwright-mcp/
│       └── test-prompts.md         # Add details panel test cases
└── unit/
    └── test_details_panel.py       # NEW: Unit tests for details rendering
```

**Structure Decision**: Single project modification to existing Streamlit app. No new projects or services required. Component extraction to `components/details_panel.py` is optional refactoring if the code becomes too large.

## Complexity Tracking

> No violations - all changes align with existing architecture patterns.

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| Graph library | streamlit-agraph (existing) | Visual consistency with main results |
| Tooltip implementation | Streamlit native + custom CSS | No new dependencies |
| Collapsible sections | st.expander() | Standard Streamlit pattern |
