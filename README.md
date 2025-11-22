# Medical GraphRAG Assistant

A production-ready medical AI assistant platform built on Model Context Protocol (MCP), featuring GraphRAG multi-modal search, FHIR integration, and AWS Bedrock Claude Sonnet 4.5.

**Originally forked from**: [FHIR-AI-Hackathon-Kit](https://github.com/gabriel-ing/FHIR-AI-Hackathon-Kit)

## What This Is

This is an **agentic medical chat platform** that uses:
- 🤖 **Model Context Protocol (MCP)** - Claude autonomously calls medical search tools
- 🧠 **GraphRAG** - Knowledge graph-based retrieval with entity and relationship extraction
- 🏥 **FHIR Integration** - Full-text search of clinical documents
- ☁️ **AWS Bedrock** - Claude Sonnet 4.5 with multi-iteration tool use
- 📊 **Interactive UI** - Streamlit interface with execution transparency
- 🗄️ **InterSystems IRIS** - Vector database with GraphRAG tables

## Quick Start

### 1. Run the Streamlit Chat Interface

```bash
# Install dependencies
pip install -r requirements.txt

# Set AWS credentials
export AWS_PROFILE=your-profile

# Run the chat app
cd mcp-server
streamlit run streamlit_app.py
```

Visit http://localhost:8501 and start chatting!

### 2. Use as MCP Server (Claude Desktop, etc.)

```bash
# Configure MCP client to point to:
python mcp-server/fhir_graphrag_mcp_server.py
```

## Architecture

```
┌─────────────────────────────────────┐
│  Streamlit Chat UI                  │
│  - Conversation history             │
│  - Chart visualization              │
│  - Execution log display            │
└──────────────┬──────────────────────┘
               │ AWS Bedrock Converse API
┌──────────────▼──────────────────────┐
│  Claude Sonnet 4.5                  │
│  - Agentic tool calling             │
│  - Multi-iteration reasoning        │
└──────────────┬──────────────────────┘
               │ MCP Protocol (stdio)
┌──────────────▼──────────────────────┐
│  FHIR + GraphRAG MCP Server         │
│  - 6 medical search tools           │
│  - FHIR document search             │
│  - GraphRAG entity/relationship     │
│  - Hybrid search                    │
└──────────────┬──────────────────────┘
               │ IRIS Native API (TCP)
┌──────────────▼──────────────────────┐
│  AWS IRIS Database                  │
│  - FHIR documents (migrated)        │
│  - GraphRAG entities (83)           │
│  - Relationships (540)              │
└──────────────────────────────────────┘
```

## Features

### MCP Tools (6 total)

1. **search_fhir_documents** - Full-text search of clinical notes
2. **get_entity** - Retrieve specific medical entities by ID
3. **search_entities_by_type** - Find entities by type (Condition, Medication, etc.)
4. **get_entity_relationships** - Get all relationships for an entity
5. **search_relationships_by_type** - Find relationships by type (treats, causes, etc.)
6. **hybrid_search** - Combined vector + graph search with relevance ranking

### Chat Interface Features

- ✅ **Execution Transparency** - See which tools Claude calls and its reasoning
- ✅ **Interactive Charts** - Generate visualizations from data
- ✅ **Conversation History** - Multi-turn conversations with context
- ✅ **Error Handling** - Graceful handling of API issues with detailed logs
- ✅ **Max Iterations Control** - Prevents infinite loops (10 iteration limit)
- ✅ **Type-Safe Content Processing** - Robust handling of mixed content formats

### Current Version: v2.10.2

**Recent Improvements:**
- Fixed "'str' object has no attribute 'get'" error with proper type checking
- Increased max iterations from 5 → 10 for complex queries
- Added execution details with expandable UI
- Improved error messages with context

## Configuration

### Required Environment Variables

```bash
# AWS Credentials
export AWS_PROFILE=your-profile  # or set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY

# IRIS Database (AWS)
export IRIS_HOST=your-iris-host
export IRIS_PORT=1972
export IRIS_NAMESPACE=USER
export IRIS_USERNAME=SQLAdmin
export IRIS_PASSWORD=your-password
```

### Config Files

- `config/fhir_graphrag_config.yaml` - Local development config
- `config/fhir_graphrag_config.aws.yaml` - AWS deployment config
- `config/aws-config.yaml` - AWS infrastructure settings

## Project Structure

```
medical-graphrag-assistant/
├── mcp-server/                      # MCP server and Streamlit app
│   ├── fhir_graphrag_mcp_server.py  # MCP server implementation (45KB)
│   ├── streamlit_app.py             # Chat UI (39KB)
│   └── test_*.py                    # Integration tests
├── src/
│   ├── db/                          # IRIS database clients
│   ├── embeddings/                  # NVIDIA NIM embedding integration
│   ├── search/                      # Search implementations
│   ├── vectorization/               # Document vectorization
│   └── validation/                  # Data validation
├── config/                          # Configuration files
├── docs/                            # Documentation
│   ├── architecture.md              # System architecture
│   ├── deployment-guide.md          # AWS deployment
│   └── development/                 # Development history
├── scripts/                         # Deployment scripts
└── tests/                           # Test suite
```

## Technology Stack

**AI/ML:**
- AWS Bedrock (Claude Sonnet 4.5)
- NVIDIA NIM Embeddings (1024-dim vectors)
- Model Context Protocol (MCP)

**Database:**
- InterSystems IRIS (Vector DB + GraphRAG tables)
- Native VECTOR(DOUBLE, 1024) support
- COSINE similarity search

**Infrastructure:**
- AWS EC2 (for IRIS database)
- Python 3.10+
- Streamlit for UI

**Key Libraries:**
- `intersystems-irispython` - IRIS native client
- `boto3` - AWS SDK
- `streamlit` - Chat UI
- `mcp` - Model Context Protocol SDK

## Example Queries

Try these in the chat interface:

**FHIR Search:**
- "Find patients with chest pain"
- "Search for diabetes cases"
- "Show recent emergency visits"

**GraphRAG:**
- "What medications treat hypertension?"
- "Show me the relationship between conditions and procedures"
- "What are the side effects of metformin?"

**Hybrid Search:**
- "Find treatment options for chronic pain" (combines vector + graph search)

**Visualization:**
- "Show a chart of conditions by frequency"
- "Graph the most common medications"

## Development

### Running Tests

```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# E2E tests
pytest tests/e2e/
```

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Troubleshooting

See [docs/troubleshooting.md](docs/troubleshooting.md) for common issues.

**Common Issues:**
- AWS credentials not configured → Set AWS_PROFILE or AWS env vars
- IRIS connection failed → Check IRIS_HOST and credentials
- Max iterations reached → Query may be too complex, try simplifying

## Documentation

- [Architecture Overview](docs/architecture.md) - System design and data flow
- [Deployment Guide](docs/deployment-guide.md) - AWS deployment instructions
- [MCP Server Complete](docs/development/MCP_SERVER_COMPLETE.md) - MCP implementation details
- [Development History](docs/development/) - Session notes and findings

## Contributing

This project is based on the FHIR-AI-Hackathon-Kit. The original tutorial content remains in the `tutorial/` directory.

## License

Inherits license from upstream FHIR-AI-Hackathon-Kit repository.

## Acknowledgments

- **Original Project**: [FHIR-AI-Hackathon-Kit](https://github.com/gabriel-ing/FHIR-AI-Hackathon-Kit) by gabriel-ing
- **InterSystems IRIS** for the vector database platform
- **AWS Bedrock** for Claude Sonnet 4.5 access
- **Model Context Protocol** by Anthropic
