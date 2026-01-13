# FHIR + GraphRAG Medical Chat System

Complete implementation of MCP-based medical search with interactive chat interface.

## 🎯 Quick Start

### 1. Run MCP Server

The MCP server exposes 6 medical search tools via stdio transport:

```bash
cd ./mcp-server
python3 fhir_graphrag_mcp_server.py
```

### 2. Run Streamlit Chat Interface

Interactive chat UI for medical search:

```bash
cd ./mcp-server
streamlit run streamlit_medical_chat.py
```

Access at: http://localhost:8501

### 3. Connect to Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "fhir-graphrag": {
      "command": "python3",
      "args": ["./mcp-server/fhir_graphrag_mcp_server.py"]
    }
  }
}
```

## 📊 System Architecture

```
┌────────────────────────────────────┐
│  Frontend Options:                  │
│  • Streamlit Chat UI                │
│  • Claude Desktop                   │
│  • Continue (VSCode)                │
│  • Custom MCP clients               │
└──────────────┬─────────────────────┘
               │ MCP Protocol (JSON-RPC 2.0)
┌──────────────▼─────────────────────┐
│  MCP Server (fhir_graphrag_mcp_server.py) │
│  • 6 medical search tools           │
│  • stdio transport                  │
│  • 563 lines Python                 │
└──────────────┬─────────────────────┘
               │ IRIS Native API (TCP)
┌──────────────▼─────────────────────┐
│  AWS IRIS (3.84.250.46:1972)       │
│  • SQLUser.FHIRDocuments (51 docs) │
│  • SQLUser.Entities (83)            │
│  • SQLUser.EntityRelationships (540)│
└────────────────────────────────────┘
```

## 🔧 MCP Tools

### 1. search_fhir_documents
Full-text search of FHIR clinical notes

**Parameters**:
- `query` (string): Search terms
- `limit` (integer): Max results (default: 10)

**Example**:
```python
result = await call_tool("search_fhir_documents", {
    "query": "chest pain",
    "limit": 5
})
```

**Returns**:
```json
{
  "query": "chest pain",
  "results_count": 2,
  "documents": [
    {
      "fhir_id": "1474",
      "preview": "Otitis Media Evaluation...",
      "relevance": "matches: pain"
    }
  ]
}
```

### 2. search_knowledge_graph
Search medical entities in knowledge graph

**Parameters**:
- `query` (string): Entity search terms
- `limit` (integer): Max entities (default: 5)

**Example**:
```python
result = await call_tool("search_knowledge_graph", {
    "query": "fever vomiting",
    "limit": 3
})
```

**Returns**:
```json
{
  "query": "fever vomiting",
  "entities_found": 2,
  "entities": [
    {
      "id": 42,
      "text": "fever",
      "type": "SYMPTOM",
      "confidence": 0.75
    },
    {
      "id": 58,
      "text": "vomiting",
      "type": "SYMPTOM",
      "confidence": 0.85
    }
  ],
  "documents_found": 3,
  "documents": [...]
}
```

### 3. hybrid_search
Combined FHIR + GraphRAG with RRF fusion

**Parameters**:
- `query` (string): Medical search query
- `top_k` (integer): Number of results (default: 5)

**Example**:
```python
result = await call_tool("hybrid_search", {
    "query": "respiratory infection",
    "top_k": 5
})
```

**Returns**:
```json
{
  "query": "respiratory infection",
  "fhir_results": 5,
  "graphrag_results": 1,
  "fused_results": 5,
  "top_documents": [
    {
      "fhir_id": "1474",
      "rrf_score": 0.0328,
      "sources": ["fhir", "graphrag"]
    }
  ]
}
```

### 4. get_entity_relationships
Multi-hop graph traversal

**Parameters**:
- `entity_text` (string): Starting entity
- `max_depth` (integer): Max depth 1-3 (default: 2)

### 5. get_document_details
Retrieve full FHIR document

**Parameters**:
- `fhir_id` (string): Document ID

### 6. get_entity_statistics
Knowledge graph statistics

**Parameters**: None

**Returns**:
```json
{
  "total_entities": 83,
  "total_relationships": 540,
  "entity_distribution": [
    {"type": "TEMPORAL", "count": 43},
    {"type": "SYMPTOM", "count": 21},
    {"type": "BODY_PART", "count": 10},
    {"type": "CONDITION", "count": 6},
    {"type": "MEDICATION", "count": 2},
    {"type": "PROCEDURE", "count": 1}
  ]
}
```

## 💬 Streamlit Chat Interface

### Features

- **Intelligent Tool Selection**: Automatically chooses the right tool based on query
- **Interactive UI**: Chat-style interface with example queries
- **Real-time Stats**: Live knowledge graph statistics
- **Tool Results**: View raw JSON responses
- **Entity Visualization**: Color-coded entity type badges
- **Document Previews**: Clinical note snippets

### Example Queries

- "Search for patients with chest pain"
- "Find entities related to fever"
- "What respiratory conditions are in the knowledge graph?"
- "Show me document 1474"
- "Use hybrid search for respiratory infection"

### Query Patterns

The chat interface intelligently routes queries:

- Contains "hybrid" or "combined" → `hybrid_search`
- Contains "entity" or "knowledge graph" → `search_knowledge_graph`
- Contains "document" + numbers → `get_document_details`
- Default → `search_fhir_documents`

## 📦 Installation

### Prerequisites

```bash
# Python 3.11+
python3 --version

# Required packages
pip install intersystems-iris streamlit mcp
```

### Database Access

The system connects to AWS IRIS:

- **Host**: 3.84.250.46
- **Port**: 1972
- **Namespace**: USER
- **Credentials**: _SYSTEM / SYS

## 📚 Data Contents

### FHIR Documents (51 total)
- Synthea-generated clinical notes
- Hex-encoded in DocumentReference resources
- Various medical encounters and conditions

### Knowledge Graph (83 entities, 540 relationships)
- **TEMPORAL** (43): Dates and time references
- **SYMPTOM** (21): fever, vomiting, diarrhea, pain, fatigue
- **BODY_PART** (10): respiratory, abdomen, chest
- **CONDITION** (6): infections, diseases
- **MEDICATION** (2): prescriptions
- **PROCEDURE** (1): medical procedures

### High-Confidence Entities
- discomfort, tenderness, vomiting, diarrhea
- respiratory, abdomen
- Various temporal markers

## 🧪 Testing

### Test Tool Discovery
```bash
python3 test_mcp_server_tools.py
```

Expected output:
```
Found 6 tools:
------------------------------------------------------------

• search_fhir_documents
• search_knowledge_graph
• hybrid_search
• get_entity_relationships
• get_document_details
• get_entity_statistics

✓ All expected tools found!
```

### Test Tool Execution
```bash
python3 test_mcp_tool_execution.py
```

Expected output:
```
Testing MCP Tool Execution...
============================================================

1. Testing get_entity_statistics...
✓ Total entities: 83
✓ Total relationships: 540

2. Testing search_knowledge_graph...
✓ Found 1 entities
✓ Related to 1 documents

3. Testing search_fhir_documents...
✓ Found 2 documents

4. Testing hybrid_search...
✓ FHIR results: 5
✓ GraphRAG results: 1
✓ Fused results: 5

✓ All tool execution tests PASSED!
```

## 🔍 Technical Details

### Reciprocal Rank Fusion (RRF)

Hybrid search combines rankings using RRF:

```python
k = 60  # RRF constant
rrf_score = 0.0
if fhir_rank:
    rrf_score += 1.0 / (k + fhir_rank)
if graph_rank:
    rrf_score += 1.0 / (k + graph_rank)
```

Documents appearing in both FHIR and GraphRAG results get boosted scores.

### Hex-Encoded Clinical Notes

FHIR DocumentReference stores notes as hex strings:

```python
encoded_data = resource_json['content'][0]['attachment']['data']
clinical_note = bytes.fromhex(encoded_data).decode('utf-8')
```

### Fuzzy Entity Matching

Entity search uses SQL LIKE for flexible matching:

```sql
WHERE LOWER(EntityText) LIKE '%fever%'
```

## 📁 Files

```
mcp-server/
├── fhir_graphrag_mcp_server.py          # Main MCP server (563 lines)
├── streamlit_medical_chat.py            # Chat interface
├── test_mcp_server_tools.py             # Tool discovery test
├── test_mcp_tool_execution.py           # Integration test
├── debug_mcp_response.py                # Debug helper
└── README.md                            # This file

./
├── MCP_SERVER_COMPLETE.md               # Detailed documentation
├── STATUS.md                            # Project status
├── PROGRESS.md                          # Development log
└── TODO.md                              # Task list
```

## 🚀 Next Steps

### 1. Medical Image Integration

Add MIMIC-CXR image support:

```python
# Query images
sql = """
    SELECT ImageID, StudyID, SubjectID, ViewPosition, ImagePath
    FROM SQLUser.MIMICImages
    WHERE StudyID = ?
"""

# Return image thumbnails in tool responses
{
    "fhir_id": "1474",
    "clinical_note": "...",
    "images": [
        {
            "image_id": "abc123",
            "view": "PA",
            "thumbnail_url": "/images/abc123_thumb.jpg"
        }
    ]
}
```

### 2. Knowledge Graph Visualization

Add interactive graph visualization using:
- Cytoscape.js
- vis.js
- D3.js force-directed graphs

### 3. Advanced Search

- Temporal queries (date ranges)
- Medication interactions
- Patient cohort identification
- Condition co-occurrence analysis

## 📝 License

Part of FHIR-AI-Hackathon-Kit - InterSystems demo project

## 🤝 Contributing

This is a demo/prototype system. For production use:
1. Add authentication/authorization
2. Implement rate limiting
3. Add comprehensive error handling
4. Set up monitoring and logging
5. Deploy with proper security configurations

## 📞 Support

For issues or questions:
- Check MCP_SERVER_COMPLETE.md for detailed documentation
- Review test scripts for usage examples
- Inspect tool responses with debug_mcp_response.py

---

**Status**: ✅ MCP server operational, Streamlit UI ready, 6 tools tested
**Last Updated**: 2025-11-18
