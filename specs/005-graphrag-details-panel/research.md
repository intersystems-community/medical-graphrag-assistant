# Research: GraphRAG Details Panel Enhancement

**Feature**: 005-graphrag-details-panel
**Date**: 2025-12-10
**Status**: Complete

## Research Questions

### 1. How does the existing details dropdown work?

**Decision**: Extend the existing `st.expander()` pattern in `streamlit_app.py`

**Rationale**: The current implementation (lines 1310-1327 in `streamlit_app.py`) uses Streamlit's native expander component with a caption. This provides:
- Consistent UX with existing app behavior
- Built-in collapse/expand state management
- Accessible keyboard navigation

**Alternatives Considered**:
- Custom JavaScript accordion: Rejected - unnecessary complexity, breaks Streamlit conventions
- Third-party component: Rejected - adds dependency, no clear benefit over native

### 2. How to implement entity tooltips on click?

**Decision**: Use `streamlit-agraph` node click events combined with Streamlit session state for tooltip display

**Rationale**: The `streamlit-agraph` library already supports node click events. When a node is clicked:
1. Store clicked node ID in `st.session_state`
2. Render tooltip content below the graph using `st.info()` or custom styled container
3. Include source document references and context

**Alternatives Considered**:
- Native browser tooltips (title attribute): Rejected - limited styling, poor mobile support
- External tooltip library (tippy.js): Rejected - complex integration with Streamlit
- Plotly hover: Available as fallback but not as interactive as agraph

### 3. How to organize collapsible sub-sections?

**Decision**: Nested `st.expander()` components within the main details expander

**Rationale**: Streamlit supports nested expanders. Structure:
```python
with st.expander("Show Execution Details"):
    with st.expander("📋 Entities Found", expanded=True):
        # Entity list
    with st.expander("🕸️ Entity Relationships", expanded=True):
        # Graph
    with st.expander("⚙️ Tool Execution", expanded=True):
        # Timeline
```

**Alternatives Considered**:
- Tabs (`st.tabs`): Rejected - hides content by default, contradicts spec requirement
- Single scrollable view: Rejected - doesn't meet collapsible sub-section requirement

### 4. How to extract entity data from GraphRAG results?

**Decision**: Parse existing tool result structure from `search_knowledge_graph` and `hybrid_search` tools

**Rationale**: The MCP tools already return structured data including:
- Entity text and type from knowledge graph nodes
- Relationship data from graph edges
- Confidence/relevance scores

Data extraction approach:
```python
def extract_entities_from_results(tool_results: List[dict]) -> List[Entity]:
    entities = []
    for result in tool_results:
        if result.get("tool_name") in ["search_knowledge_graph", "hybrid_search"]:
            # Parse entities from result content
            pass
    return entities
```

**Alternatives Considered**:
- Separate API call for entities: Rejected - data already available in tool results
- Cache entities in database: Rejected - over-engineering for display-only feature

### 5. How to implement mobile-responsive graph fallback?

**Decision**: Use CSS media query detection via JavaScript and Streamlit's `st.components.v1`

**Rationale**: Detect viewport width and conditionally render:
- Width >= 768px: Full interactive `streamlit-agraph` graph
- Width < 768px: Simple entity list with indentation showing relationships

**Implementation**:
```python
# Inject JavaScript to detect viewport
viewport_width = st.components.v1.html("""
    <script>window.parent.postMessage({width: window.innerWidth}, '*')</script>
""", height=0)

# Or simpler: always render both, hide with CSS
```

**Alternatives Considered**:
- Server-side detection: Not possible - server doesn't know client viewport
- Always show list: Rejected - loses graph value on larger screens

### 6. How to handle large entity counts (50+ entities)?

**Decision**: Default display limited to top 50 by relevance score, with "Show all N entities" button

**Rationale**: Performance and usability balance:
- 50 nodes render quickly (<2s per spec)
- Graph remains readable
- Users can expand if needed

**Implementation**:
```python
MAX_DISPLAY_ENTITIES = 50
if len(entities) > MAX_DISPLAY_ENTITIES:
    displayed = sorted(entities, key=lambda e: e.score, reverse=True)[:MAX_DISPLAY_ENTITIES]
    if st.button(f"Show all {len(entities)} entities"):
        displayed = entities
```

**Alternatives Considered**:
- Pagination: Rejected - complex for graph visualization
- Virtual scrolling: Rejected - not well supported in Streamlit

### 7. How to display tool execution timeline?

**Decision**: Simple chronological list with duration badges and status indicators

**Rationale**: The existing implementation already tracks tool calls. Enhance display with:
- Tool name as header
- Duration as badge (e.g., "1.2s")
- Status icon (✅ success, ❌ failed)
- Expandable parameters/result preview

**Visual Design**:
```
⚙️ Tool Execution Timeline
├── ✅ search_knowledge_graph (1.2s)
│   └── Found 23 entities
├── ✅ plot_entity_network (0.8s)
│   └── Rendered graph with 15 nodes
└── ❌ get_document_details (timeout)
    └── Error: Connection timeout after 30s
```

**Alternatives Considered**:
- Gantt chart: Rejected - over-engineering for sequential calls
- Table view: Rejected - less scannable than timeline

## Dependencies Confirmed

| Dependency | Version | Status |
|------------|---------|--------|
| streamlit | >=1.28.0 | Existing |
| streamlit-agraph | >=0.0.45 | Existing |
| plotly | >=5.0.0 | Existing (fallback) |

No new dependencies required.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Graph performance with 50+ nodes | Medium | Medium | Limit default display, lazy loading |
| Mobile viewport detection unreliable | Low | Low | Graceful fallback to list always available |
| Nested expanders cause layout issues | Low | Medium | Test across browsers, have flat fallback |

## Conclusion

All technical unknowns resolved. Implementation can proceed with:
1. Existing Streamlit patterns (expanders, session state)
2. Existing graph library (streamlit-agraph)
3. No new dependencies
4. Clear data extraction from existing tool results
