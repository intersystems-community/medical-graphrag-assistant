# Quickstart: GraphRAG Details Panel Enhancement

**Feature**: 005-graphrag-details-panel
**Date**: 2025-12-10

## Prerequisites

- Python 3.11+
- Existing Medical GraphRAG Assistant running
- Access to AWS deployment at http://54.209.84.148:8501 (for testing)

## Development Setup

```bash
# Navigate to project root
cd .

# Ensure on feature branch
git checkout 005-graphrag-details-panel

# Activate virtual environment
source .venv/bin/activate

# Verify dependencies (no new deps required)
pip list | grep -E "streamlit|agraph|plotly"
```

Expected output:
```
plotly                    5.x.x
streamlit                 1.28.x+
streamlit-agraph          0.0.45+
```

## Key Files to Modify

| File | Purpose |
|------|---------|
| `mcp-server/streamlit_app.py` | Main UI - add new render functions |
| `tests/ux/playwright-mcp/test-prompts.md` | Add details panel test cases |

## Implementation Order

### Step 1: Data Extraction Functions

Add to `streamlit_app.py`:

```python
def extract_entities_from_results(tool_results: List[dict]) -> List[dict]:
    """Extract entities from tool results for display."""
    entities = []
    for result in tool_results:
        if result.get("tool_name") in ["search_knowledge_graph", "hybrid_search"]:
            # Parse entities from result
            pass
    return entities

def extract_relationships_from_results(tool_results: List[dict]) -> List[dict]:
    """Extract relationships from tool results for graph."""
    relationships = []
    # Implementation
    return relationships
```

### Step 2: Entity Section Component

```python
def render_entity_section(entities: List[dict], total_count: int):
    """Render entity list with tooltips."""
    with st.expander("📋 Entities Found", expanded=True):
        if not entities:
            st.info("No entities found in this query")
            return

        # Group by type
        by_type = {}
        for e in entities:
            by_type.setdefault(e["type"], []).append(e)

        for entity_type, items in by_type.items():
            st.markdown(f"**{entity_type}** ({len(items)})")
            for item in items[:10]:  # Limit per type
                if st.button(f"{item['name']} ({item['score']:.2f})", key=item['id']):
                    st.session_state.selected_entity = item['id']

        if total_count > 50:
            st.button(f"Show all {total_count} entities")
```

### Step 3: Graph Section Component

```python
def render_graph_section(entities: List[dict], relationships: List[dict]):
    """Render force-directed graph of entity relationships."""
    with st.expander("🕸️ Entity Relationships", expanded=True):
        if len(relationships) < 1:
            st.info("Not enough relationships to display graph")
            return

        # Reuse existing graph rendering logic
        nodes = [Node(id=e['id'], label=e['name'], size=20) for e in entities]
        edges = [Edge(source=r['source_id'], target=r['target_id']) for r in relationships]

        config = Config(width=600, height=400, physics=True)
        agraph(nodes=nodes, edges=edges, config=config)
```

### Step 4: Tools Section Component

```python
def render_tools_section(tool_executions: List[dict]):
    """Render tool execution timeline."""
    with st.expander("⚙️ Tool Execution", expanded=True):
        for tool in tool_executions:
            status_icon = "✅" if tool['status'] == 'success' else "❌"
            duration = f"{tool['duration_ms']/1000:.1f}s"
            st.markdown(f"{status_icon} **{tool['tool_name']}** `{duration}`")
            if tool.get('error_message'):
                st.error(tool['error_message'])
```

### Step 5: Integration

Modify the existing details expander in `chat_with_tools()`:

```python
# Replace existing details rendering with:
with st.expander("🔍 Show Execution Details", expanded=False):
    entities = extract_entities_from_results(tool_results)
    relationships = extract_relationships_from_results(tool_results)

    render_entity_section(entities, len(all_entities))
    render_graph_section(entities, relationships)
    render_tools_section(tool_executions)
```

## Testing

### Local Testing

```bash
# Run Streamlit app locally
cd mcp-server
streamlit run streamlit_app.py

# In browser: Submit query, expand details, verify:
# 1. Entity list appears
# 2. Graph renders (if relationships exist)
# 3. Tool timeline shows
```

### UX Testing with Playwright MCP

```bash
# Run UX tests
claude

# In Claude Code, execute:
# Run UX tests for Medical GraphRAG Assistant details panel
```

Test cases to add:
- TC-011: Expand details, verify entity section visible
- TC-012: Click entity, verify tooltip appears
- TC-013: Verify graph renders with relationships
- TC-014: Collapse/expand sub-sections independently

## Deployment

```bash
# Commit changes
git add -A
git commit -m "Add GraphRAG details panel with entities, graph, and tools"

# Push to feature branch
git push origin 005-graphrag-details-panel

# Deploy to AWS (existing process)
# SSH to EC2, pull changes, restart Streamlit
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Graph not rendering | Check streamlit-agraph version, verify physics config |
| Entities empty | Verify tool_results contains search_knowledge_graph data |
| Tooltips not appearing | Check session_state key names match |
| Slow rendering | Reduce entity limit, check for N+1 loops |

## Success Criteria Verification

- [ ] Entities display within 1 second of expand
- [ ] Graph renders within 2 seconds for 50 nodes
- [ ] All three sub-sections independently collapsible
- [ ] Entity click shows tooltip with sources
- [ ] Tool timeline shows all executed tools
