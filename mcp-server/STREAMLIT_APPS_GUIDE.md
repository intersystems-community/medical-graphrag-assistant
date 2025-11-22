# Streamlit Medical Chat Applications Guide

## Overview
We have created 4 different Streamlit applications, each demonstrating different approaches to medical data visualization and AI-powered chat. They all connect to the AWS IRIS database with FHIR documents and GraphRAG knowledge graph.

## Available Applications

### 1. streamlit_agentic_chat.py ⭐ **RECOMMENDED**
**Port**: 8504
**URL**: http://localhost:8504

**What Makes It Special**:
- Uses Claude's **tool use** capability for autonomous decision-making
- Claude decides which MCP tools to call based on user questions
- Proper agentic architecture - no pattern matching

**How It Works**:
1. User asks a question
2. Claude autonomously chooses which MCP tools to call
3. System executes those tools
4. Claude synthesizes natural language answer
5. Interactive charts appear IN the chat when visualization tools are called

**Example Queries**:
- "What are the most common symptoms?" → Claude calls `search_knowledge_graph` or `plot_symptom_frequency`
- "Show me a chart of symptom frequency" → Claude calls `plot_symptom_frequency` and chart renders
- "Search for chest pain cases" → Claude calls `hybrid_search` and `get_document_details`

**MCP Tools Available** (Claude decides when to use them):
- search_fhir_documents
- search_knowledge_graph
- hybrid_search
- get_document_details
- get_entity_statistics
- plot_symptom_frequency
- plot_entity_distribution
- plot_patient_timeline

---

### 2. streamlit_ultimate_medical_chat.py
**Port**: Not currently running (can be started)

**What Makes It Special**:
- Simplest implementation with GraphRAG + Claude synthesis
- Good for understanding the basic RAG flow
- Clean, minimal interface

**How It Works**:
1. Uses pattern matching to detect if user wants visualization
2. Calls MCP tools based on keywords
3. For search queries: retrieves documents + entities, then Claude synthesizes answer
4. Shows sources in expandable section

**Limitations**:
- Manual pattern matching (not agentic)
- Limited to pre-defined query patterns

---

### 3. streamlit_medical_chat_viz.py
**Port**: 8502
**URL**: http://localhost:8502

**What Makes It Special**:
- Three-tab interface: Chat, Visualizations, Analytics
- Static dashboard with pre-rendered charts
- Good for exploring data without asking questions

**How It Works**:
- **Chat Tab**: Similar to ultimate chat - pattern matching for queries
- **Visualizations Tab**: Always-on dashboard with entity distribution, symptom frequency, timeline
- **Analytics Tab**: Knowledge graph statistics, entity distribution table

**Use Case**: When you want to see data visualizations without needing to ask for them

---

### 4. streamlit_graphrag_chat.py
**Port**: 8503
**URL**: http://localhost:8503

**What Makes It Special**:
- Focus on GraphRAG retrieval + Claude synthesis
- Shows sources with document previews
- Sidebar with search strategy selector

**How It Works**:
1. User asks question
2. Retrieves using selected strategy (Hybrid / FHIR Only / Knowledge Graph Only)
3. Gets full document details
4. Claude synthesizes answer from context
5. Shows sources in expandable section

**Settings**:
- Switch between search strategies
- Adjust max results (3-20)

---

## Which One Should You Use?

### For Production/Demo: **streamlit_agentic_chat.py** ⭐
- Most sophisticated
- Proper agentic behavior
- Claude autonomously decides what tools to call
- Charts appear naturally in conversation

### For Data Exploration: **streamlit_medical_chat_viz.py**
- Three-tab interface
- Pre-rendered dashboards
- Good for browsing data

### For Understanding RAG: **streamlit_ultimate_medical_chat.py**
- Simplest code
- Clear RAG pipeline
- Good for learning

### For Testing Search Strategies: **streamlit_graphrag_chat.py**
- Compare Hybrid vs FHIR vs GraphRAG
- See what each strategy retrieves
- Useful for tuning

---

## Architecture Comparison

### Agentic (streamlit_agentic_chat.py)
```
User Question
    ↓
Claude with MCP Tools → Decides to call tool
    ↓
Execute MCP Tool → Return results
    ↓
Claude uses results → Decides next action
    ↓
Final Answer (or call more tools)
```

### Manual RAG (others)
```
User Question
    ↓
Pattern Matching → Decide which tool
    ↓
Execute Tool → Get results
    ↓
Claude Synthesis → Answer
```

---

## MCP Server Tools

All apps use the same MCP server (`fhir_graphrag_mcp_server.py`) with these tools:

### Search Tools
- **search_fhir_documents**: Full-text search of FHIR clinical notes
- **search_knowledge_graph**: Entity-based search (symptoms, conditions, medications)
- **hybrid_search**: Combined FHIR + GraphRAG with RRF fusion

### Data Retrieval
- **get_document_details**: Get full clinical note for a FHIR document
- **get_entity_relationships**: Traverse knowledge graph from seed entity
- **get_entity_statistics**: Knowledge graph stats and distribution

### Visualization (returns Plotly chart data)
- **plot_entity_distribution**: Pie/bar chart of entity types
- **plot_symptom_frequency**: Top N symptoms bar chart
- **plot_patient_timeline**: Timeline of patient encounters over time
- **plot_entity_network**: Network graph of entity relationships

---

## AWS IRIS Connection

All apps connect to:
- **Host**: 3.84.250.46
- **Port**: 1972
- **Namespace**: %SYS
- **Tables**:
  - SQLUser.FHIRDocuments (51 documents)
  - SQLUser.Entities (83 entities)
  - SQLUser.EntityRelationships (540 relationships)

---

## LLM Configuration

Using **Claude Sonnet 4.5** via AWS Bedrock:
- **Model ID**: anthropic.claude-sonnet-4-5-20250929-v1:0
- **Region**: us-east-1
- **Temperature**: 0.3 (for medical accuracy)
- **Max Tokens**: 2000-4000

---

## Quick Start

```bash
# Start the recommended agentic chat
streamlit run streamlit_agentic_chat.py --server.headless true --server.port 8504

# Or start all apps in background
streamlit run streamlit_agentic_chat.py --server.port 8504 &
streamlit run streamlit_medical_chat_viz.py --server.port 8502 &
streamlit run streamlit_graphrag_chat.py --server.port 8503 &
```

Then visit:
- http://localhost:8504 for agentic chat ⭐
- http://localhost:8502 for visualization dashboard
- http://localhost:8503 for GraphRAG chat

---

## Next Steps

### Potential Enhancements:
1. **Medical Image Integration**: Add thumbnails from SQLUser.MIMICImages
2. **Authentication**: Add user login for production
3. **Query History**: Save and replay past queries
4. **Export**: Download chat transcripts or chart data
5. **Multi-Modal**: Handle medical images with CLIP/NVEmbed
6. **Fine-tuning**: Customize Claude's medical knowledge

### Current Limitations:
- No medical image display yet (images are in database)
- No query caching (every query hits database)
- No user sessions (all users share state)
- Limited to text-based clinical notes

---

## Testing Checklist

### For streamlit_agentic_chat.py:

✅ **Tool Use Tests**:
- [ ] Ask "What are the most common symptoms?" → Should call search_knowledge_graph or plot_symptom_frequency
- [ ] Ask "Show me a chart of symptom frequency" → Should call plot_symptom_frequency and render chart
- [ ] Ask "Search for chest pain" → Should call hybrid_search
- [ ] Ask "Tell me about document 1474" → Should call get_document_details
- [ ] Ask "Show entity distribution" → Should call plot_entity_distribution

✅ **Preset Button Tests**:
- [ ] Click "What are the most common symptoms?" → Should work
- [ ] Click "Show symptom frequency chart" → Should render chart
- [ ] Click "Plot entity distribution" → Should render chart

✅ **Multi-Turn Tests**:
- [ ] Ask follow-up questions
- [ ] Claude should maintain context
- [ ] Charts should appear in appropriate places

✅ **Error Handling**:
- [ ] Ask about non-existent entity
- [ ] Ask for unsupported visualization
- [ ] Network interruption

---

## Files Reference

- `fhir_graphrag_mcp_server.py` - MCP server with all tools
- `streamlit_agentic_chat.py` - Agentic chat (recommended)
- `streamlit_ultimate_medical_chat.py` - Simple RAG chat
- `streamlit_medical_chat_viz.py` - Three-tab interface
- `streamlit_graphrag_chat.py` - Search strategy comparison

---

## Troubleshooting

### Charts Not Appearing
- Check if tool is returning proper JSON format
- Verify Plotly is installed: `pip install plotly`
- Check browser console for JavaScript errors

### Connection Errors
- Verify AWS IRIS is accessible: `python3 -c "import intersystems_iris.dbapi._DBAPI as iris; conn = iris.connect(hostname='3.84.250.46', port=1972, namespace='%SYS', username='_SYSTEM', password='SYS'); print('✓ Connected')"`
- Check if on public network (not corporate firewall)

### Claude Not Calling Tools
- Check if tools are properly defined in MCP_TOOLS list
- Verify tool descriptions are clear
- Check stop_reason in response (should be "tool_use")
- Review tool execution logs

### Preset Buttons Not Working
- Check for pending_query pattern in code
- Verify st.rerun() is called after button click
- Check session state initialization
