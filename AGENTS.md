# AGENTS.md - Agentic Development Guide

This guide provides essential information for AI agents (like Claude, GPT-4, or specialized coding assistants) working on the **Medical GraphRAG Assistant** repository.

## 📂 Project Structure

```text
medical-graphrag-assistant/
├── mcp-server/          # MCP server and Streamlit app
│   ├── fhir_graphrag_mcp_server.py  # MCP server logic
│   └── streamlit_app.py             # Streamlit Chat UI
├── src/                 # Core logic and source code
│   ├── db/              # Database connection and clients
│   ├── embeddings/      # Embedding generation (NIM/NV-CLIP)
│   ├── memory/          # Agent memory system
│   ├── query/           # Search query processing
│   └── search/          # RAG and GraphRAG implementations
├── tests/               # Test suite
│   ├── unit/            # Unit tests
│   ├── integration/     # Integration tests
│   ├── e2e/             # End-to-end tests
│   └── ux/              # Playwright UI tests
├── config/              # YAML configuration files
├── scripts/             # Deployment and utility scripts
└── docs/                # Project documentation
```

## 🚀 Commands & Workflow

### 📦 Setup & Dependencies
- **Install**: `pip install -r requirements.txt`
- **AWS Profile**: Use `PowerUserPlusAccess-122293094970` for all AWS operations.
- **AWS Login**: `aws sso login --profile PowerUserPlusAccess-122293094970`
- **Environment Variables**: Required keys: `AWS_PROFILE`, `IRIS_HOST`, `IRIS_PORT`, `IRIS_NAMESPACE`, `IRIS_USERNAME`, `IRIS_PASSWORD`, `NVCLIP_BASE_URL`, `NVIDIA_API_KEY`.

### 🖥️ EC2 Environment
- **Instance Name**: `fhir-ai-hackathon`
- **Instance ID**: `i-0432eba10b98c4949` (us-east-1)
- **Public IP**: `13.218.19.254` (Verified 2026-01-02)
- **Streamlit URL**: `http://13.218.19.254:8501`
- **IRIS Port**: `1972` (SQL), `52773` (Portal)

### 🛠️ Development & Execution
- **Run Streamlit UI**: `cd mcp-server && streamlit run streamlit_app.py`
- **Run MCP Server**: `python mcp-server/fhir_graphrag_mcp_server.py`
- **Linting**: `ruff check .` or `ruff check . --fix`
- **Type Checking**: `mypy .` (if configured)

### 🧪 Testing
- **Run all tests**: `pytest`
- **Run unit tests**: `pytest tests/unit/`
- **Run integration tests**: `pytest tests/integration/`
- **Run E2E tests**: `pytest tests/e2e/`
- **Run a single test file**: `pytest tests/unit/search/test_hybrid_search.py`
- **Run a specific test function**: `pytest tests/unit/search/test_hybrid_search.py::test_rrf_fusion`

---

## 🎨 Code Style & Conventions

### 🐍 Python Guidelines
- **Naming**: 
    - Variables/Functions/Methods: `snake_case` (e.g., `get_patient_records`)
    - Classes: `PascalCase` (e.g., `GraphRAGManager`)
    - Constants: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_LIMIT`)
- **Types**: Always use type hints for function arguments and return values.
    - `from typing import Any, Dict, List, Optional, Union`
    - `def process_results(results: List[Dict[str, Any]]) -> Optional[int]:`
- **Path Handling**: Prefer `os.path` for path manipulations to match existing codebase patterns, though `pathlib` is acceptable for new standalone utilities.
- **Imports**: Organize in three blocks separated by blank lines:
    1. Standard library imports (e.g., `os`, `sys`, `json`)
    2. Third-party library imports (e.g., `iris`, `streamlit`, `boto3`)
    3. Local application imports using `src.` prefix (e.g., `from src.db.connection import get_connection`)
- **Error Handling**: 
    - Use specific exception types where possible (e.g., `ValueError`, `ConnectionError`).
    - Provide descriptive error messages that include relevant IDs or values.
    - Log errors with context: `logger.error(f"Failed to fetch {doc_id}: {e}", exc_info=True)`
- **Docstrings**: Use Google-style docstrings for classes and public methods. Include "Args", "Returns", and "Raises" sections.

---

## 🗄️ Database (InterSystems IRIS)
- **Native API**: Use `src.db.connection.get_connection()` for IRIS DBAPI access.
- **Vector Search**: Use `VECTOR_COSINE` for similarity queries.
- **SQL Schema**: 
    - `SQLUser`: General FHIR resources and Knowledge Graph tables.
    - `VectorSearch`: Vector-enabled tables for images and memory.
- **Parametrization**: ALWAYS use `?` placeholders in SQL queries to prevent injection. Never use f-strings to build SQL queries with user input.

### 📦 IRIS Vector Packages
This project leverages the following InterSystems IRIS Vector packages for RAG and Graph workloads:
- **`iris-vector-rag`**: Provides production RAG pipelines (basic, graphrag, crag), BYOT (Bring Your Own Table) storage, and `CloudConfiguration` API for seamless environment switching.
- **`iris-vector-graph`**: Specialized toolkit for GraphRAG, handling entity storage, relationship management, and high-performance graph traversals.

---

## 🏗️ Architectural Patterns

### 🤖 Model Context Protocol (MCP)
- The core logic is exposed via an MCP server in `mcp-server/fhir_graphrag_mcp_server.py`.
- **Tool Definition**: Tools are defined in the `list_tools` handler. Each tool must have a clear description and a strictly defined `inputSchema`.
- **Tool Execution**: Implementation resides in the `call_tool` handler. 
- **Response Format**: Tools should return a `List[TextContent]` where the text is a JSON-formatted string.

### 🧠 GraphRAG & RRF
- **Graph Search**: Traverses medical entities (Symptoms, Conditions, Medications) and their relationships in IRIS.
- **Vector Search**: Semantic search over clinical notes or images using 1024-dimensional embeddings.
- **Fusion**: Uses Reciprocal Rank Fusion (RRF) with a constant `k=60` to merge disparate search results from text and graph modalities.
- **Entity Extraction**: Currently uses regex-based patterns with confidence scoring; future work includes moving to LLM-based extraction.

### 🖼️ NVIDIA NIM Architecture
The system uses **NVIDIA NIM** (Inference Microservices) for high-performance, GPU-accelerated inference:
- **NIM LLM**: Deployed on port 8001 (e.g., `meta/llama-3.1-8b-instruct`) for text generation and entity extraction.
- **NV-CLIP**: Deployed on port 8002 (`nvidia/nvclip`) for generating 1024-dimensional multimodal embeddings.
- **Self-hosted vs Cloud**: Local development often uses SSH tunnels to g5.xlarge instances, while production uses direct container access.

### 🖼️ Imaging & Multimodal
- **NV-CLIP**: Use the `NVCLIPEmbeddings` class in `src/embeddings/nvclip_embeddings.py` for multimodal tasks.
- **DICOM**: Use `pydicom` for handling medical imaging files. Images are converted to base64 for embedding generation.
- **Search**: Image search is performed via `search_medical_images` which uses vector similarity in the `VectorSearch.MIMICCXRImages` table.

### 💾 Agent Memory
- Semantic memory is stored in the `AgentMemoryVectors` table.
- **Memory Types**: `correction`, `knowledge`, `preference`, `feedback`.
- **VectorMemory**: Use `VectorMemory` class in `src/memory/vector_memory.py` for persistent agent knowledge. Memories are automatically recalled before queries to guide tool selection.

---

## 🤖 Model Tiering & Tool Usage

This project optimizes for cost and performance using model tiering:

| Model | Recommended Use |
|-------|-----------------|
| **Haiku** | Clarifying specs, small edits, task breakdown, quick Q&A. |
| **Sonnet** | Planning, validating, coordinating, code review. |
| **Gemini Flash** | Heavy code implementation, refactors, multi-file edits via `gemini_implement`. |
| **Opus** | High-level architecture, complex reasoning, final reviews. |

### 🖼️ Frontend Delegation Rule
- **VISUAL changes** (CSS, layout, colors, animations): Delegate to `frontend-ui-ux-engineer`.
- **LOGIC changes** (API calls, state, data processing): Handle directly in the component.
- **Mixed changes**: Split the work or delegate and supervise.

---

## 🧪 Testing & Validation

### Testing Conventions
- **Location**: All tests reside in the `tests/` directory.
- **Framework**: `pytest` is the standard test runner.
- **Categories**:
    - `tests/unit/`: Logic-only tests (no external services).
    - `tests/integration/`: Tests involving IRIS, AWS, or NIM services.
    - `tests/e2e/`: Full system tests including MCP tool execution.
    - `tests/ux/`: Playwright-based browser automation tests for the Streamlit UI.

### Validation Requirements
- **LSP Diagnostics**: Before completing a task, ensure `lsp_diagnostics` are clean on all modified files.
- **Build**: Ensure `streamlit run` starts without errors if frontend changes were made.

---

## 📋 Best Practices
1. **Minimize Refactoring**: When fixing a bug, focus on the fix. Do not refactor unrelated code.
2. **Type Safety**: Avoid `as Any` or ignoring type errors unless absolutely necessary for library compatibility.
3. **Evidence-Based Completion**: A task is only complete if `lsp_diagnostics` are clean and relevant tests pass.
4. **Secrets**: NEVER commit or log AWS keys, IRIS passwords, or NVIDIA API keys. Use environment variables.
5. **FHIR Compliance**: Respect FHIR R4 resource structures (e.g., `DocumentReference`, `ImagingStudy`, `Patient`) when interacting with clinical data.
6. **Logging**: Use the `logging` module. Avoid `print()` in production code except for CLI-facing scripts.
7. **Performance**: Be mindful of vector search latency. Use caching for embeddings where appropriate (see `src/search/cache.py`).
8. **Documentation**: Keep `STATUS.md` and `PROGRESS.md` updated as you complete major features or milestones.

## Recent Changes
- 009-full-ux-tests: Added Python 3.11 + Playwright, pytest, pytest-playwright, requests, intersystems-iris
- 009-full-ux-tests: Added [if applicable, e.g., PostgreSQL, CoreData, files or N/A]

## Active Technologies
- Python 3.11 + Playwright, pytest, pytest-playwright, requests, intersystems-iris (009-full-ux-tests)
- InterSystems IRIS (Target environment validation) (009-full-ux-tests)
