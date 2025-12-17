# Component Contract: Details Panel

**Feature**: 005-graphrag-details-panel
**Date**: 2025-12-10
**Type**: Internal UI Component

## Overview

This contract defines the interface for the enhanced Details Panel component within the Streamlit chat interface.

## Component: `render_details_panel`

### Signature

```python
def render_details_panel(
    tool_results: List[Dict[str, Any]],
    thinking_blocks: List[str],
    memory_recalls: List[str],
    response_time_ms: int
) -> None:
    """
    Render the enhanced execution details panel with entities, graph, and tools.

    Args:
        tool_results: List of tool call results from the AI response
        thinking_blocks: List of thinking/reasoning text blocks
        memory_recalls: List of recalled memory items
        response_time_ms: Total response generation time

    Returns:
        None (renders directly to Streamlit)

    Side Effects:
        - Updates st.session_state for collapse/selection state
        - Renders UI components to current Streamlit container
    """
```

### Behavior

1. **Container**: Renders within `st.expander("🔍 Show Execution Details")`
2. **Sub-sections**: Creates three nested expanders (Entities, Graph, Tools)
3. **State Management**: Uses session state keys defined in data-model.md
4. **Error Handling**: Gracefully handles missing/malformed data

### Dependencies

- `streamlit` >= 1.28.0
- `streamlit-agraph` >= 0.0.45
- Internal: `parse_tool_results()`, `extract_entities()`, `extract_relationships()`

---

## Component: `render_entity_section`

### Signature

```python
def render_entity_section(
    entities: List[DisplayEntity],
    total_count: int,
    on_entity_click: Callable[[str], None]
) -> Optional[str]:
    """
    Render the entity list with tooltips and truncation.

    Args:
        entities: List of entities to display
        total_count: Total entity count before truncation
        on_entity_click: Callback when entity is clicked

    Returns:
        Selected entity ID or None
    """
```

### Behavior

1. **Display Format**: Grouped by entity type, sorted by score within type
2. **Truncation**: Shows max 50 entities with "Show all" button if truncated
3. **Click Handling**: Clicking entity shows tooltip with sources and context
4. **Empty State**: Shows "No entities found in this query" message

### Visual Specification

```
📋 Entities Found (23)                    [▼]
├── 🩺 Conditions (5)
│   ├── Hypertension (0.95) [click for details]
│   ├── Diabetes Type 2 (0.87)
│   └── ...
├── 💊 Medications (8)
│   ├── Metformin (0.92)
│   └── ...
└── 🔬 Symptoms (10)
    └── ...

[Show all 47 entities]  (if truncated)
```

---

## Component: `render_graph_section`

### Signature

```python
def render_graph_section(
    entities: List[DisplayEntity],
    relationships: List[DisplayRelationship],
    selected_entity_id: Optional[str]
) -> Optional[str]:
    """
    Render the force-directed relationship graph.

    Args:
        entities: List of entities as nodes
        relationships: List of relationships as edges
        selected_entity_id: Currently selected entity to highlight

    Returns:
        Clicked node ID or None
    """
```

### Behavior

1. **Minimum Threshold**: Only renders if 2+ related entities exist
2. **Graph Library**: Uses `streamlit-agraph` with same config as main results
3. **Interaction**: Nodes draggable, graph zoomable/pannable
4. **Highlighting**: Selected entity highlighted with different color
5. **Fallback**: On mobile (<768px) or if agraph unavailable, shows relationship list

### Graph Configuration

```python
config = Config(
    width=600,
    height=400,
    directed=False,
    physics=True,
    hierarchical=False,
    nodeHighlightBehavior=True,
    highlightColor="#F7A7A6",
    collapsible=False,
    node={"labelProperty": "label", "renderLabel": True},
    link={"labelProperty": "label", "renderLabel": False}
)
```

---

## Component: `render_tools_section`

### Signature

```python
def render_tools_section(
    tool_executions: List[ToolExecution]
) -> None:
    """
    Render the tool execution timeline.

    Args:
        tool_executions: List of tool executions in chronological order

    Returns:
        None
    """
```

### Behavior

1. **Order**: Chronological by start_time
2. **Status Icons**: ✅ success, ❌ failed, ⏱️ timeout, ⏭️ skipped
3. **Duration**: Displayed as badge (e.g., "1.2s")
4. **Expandable**: Each tool entry expandable to show parameters/result

### Visual Specification

```
⚙️ Tool Execution (3 tools, 2.4s total)   [▼]
│
├── ✅ search_knowledge_graph              1.2s
│   └── Parameters: query="chest pain", limit=20
│       Result: Found 23 entities
│
├── ✅ plot_entity_network                 0.8s
│   └── Result: Rendered graph with 15 nodes
│
└── ❌ get_document_details                0.4s
    └── Error: Document not found (ID: doc-123)
```

---

## Error Handling Contract

| Scenario | Behavior |
|----------|----------|
| No tool results | Show "No execution data available" |
| Malformed entity data | Skip invalid entities, log warning |
| Graph rendering failure | Fall back to relationship list |
| Session state corruption | Reset to default expanded state |

## Performance Contract

| Metric | Target | Measurement |
|--------|--------|-------------|
| Entity section render | < 500ms | Time from expand to visible |
| Graph render (50 nodes) | < 2s | Time from expand to interactive |
| Click response | < 100ms | Time from click to tooltip visible |

## Testing Contract

Each component must have:
1. Unit test for data transformation logic
2. Integration test verifying Streamlit rendering
3. UX test via Playwright MCP for user interactions
