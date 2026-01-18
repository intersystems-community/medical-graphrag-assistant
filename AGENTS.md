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
- **AWS Profile**: Use `PowerUserPlusAccess-AWS_ACCOUNT_ID` for all AWS operations.
- **AWS Login**: `aws sso login --profile PowerUserPlusAccess-AWS_ACCOUNT_ID`
- **Environment Variables**: Required keys: `AWS_PROFILE`, `IRIS_HOST`, `IRIS_PORT`, `IRIS_NAMESPACE`, `IRIS_USERNAME`, `IRIS_PASSWORD`, `NVCLIP_BASE_URL`, `NVIDIA_API_KEY`.
- **Python Driver**: ALWAYS use `intersystems-irispython` (NOT `iris` or `intersystems-iris`).

### 🖥️ EC2 Environment
- **Instance Name**: `fhir-graphrag-spot`
- **Instance ID**: `i-0fee5f32e867e65c1` (us-east-1)
- **Public IP**: `44.200.206.67` (Verified 2026-01-17)
- **Streamlit URL**: `http://44.200.206.67:8501`
- **IRIS Port**: `1972` (SQL), `52773` (Portal)
- **Status**: ✅ Up, Tables Created, Hosted NIM Active.

### 🛠️ Development & Execution
- **Run Streamlit UI**: `cd mcp-server && streamlit run streamlit_app.py`
- **Run MCP Server**: `python mcp-server/fhir_graphrag_mcp_server.py`
- **System Health Check**: `EC2_HOST=44.200.206.67 python -m src.cli --env aws check-health`
- **Fix Environment**: `python -m src.cli fix-environment`
- **Spot Instances**: Use `scripts/aws/launch-spot.sh` to save 60% on EC2 costs.
- **Docker Storage**: Uses ephemeral drive `/opt/dlami/nvme/docker` for large NIM images.
- **Linting**: `ruff check .` or `ruff check . --fix`
- **Type Checking**: `mypy .` (if configured)

### 🔑 Secrets & Keys
- **NVIDIA API Key**: `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` (Used for NIM and Hosted API).
- **IRIS Password**: Default is `SYS`.
- **AWS Profile**: `PowerUserPlusAccess-122293094970` (Latest verified).

### 🧪 Testing
- **Run all tests (against EC2)**: `pytest tests/ --ignore=tests/ux -v`
- **Current status**: 204 passed, 16 failed, 44 skipped (see FIXME.md)
- **Environment auto-configured** via `tests/conftest.py` (defaults to EC2 44.200.206.67)
- **Search Services**: `pytest tests/unit/search/`
- **MCP Wrappers**: `pytest tests/unit/mcp/`
- **Integration**: `pytest tests/integration/`
- **E2E**: `pytest tests/e2e/`
- **UX (Playwright)**: `pytest tests/ux/playwright/` (Requires `TARGET_URL` env var)
- **Single file**: `pytest tests/unit/search/test_hybrid_search.py -v`
- **Single test**: `pytest tests/unit/search/test_hybrid_search.py::test_rrf_fusion -v`
- **See FIXME.md** for detailed fix plan for remaining failures

---

## 🎨 Code Style & Conventions

### 🐍 Python Guidelines
- **Service Layer**: Business logic (SQL, fusion, graph traversal) MUST reside in `src/search/` services. The MCP server SHOULD only contain tool definitions and input validation, delegating execution to services.
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
    - `SQLUser`: General FHIR resources, Knowledge Graph tables, and migrated documents.
    - `VectorSearch`: Vector-enabled tables for images and memory.
- **Parametrization**: ALWAYS use `?` placeholders in SQL queries to prevent injection (Principle I). Never use f-strings to build SQL queries with user input.

### 📦 IRIS Vector Packages
This project leverages the following InterSystems IRIS Vector packages for RAG and Graph workloads:
- **`iris-vector-rag`**: Provides production RAG pipelines (basic, graphrag, crag), BYOT (Bring Your Own Table) storage, and `CloudConfiguration` API for seamless environment switching.
- **`iris-vector-graph`**: Specialized toolkit for GraphRAG, handling entity storage, relationship management, and high-performance graph traversals.

---

## 🏗️ Architectural Patterns

### 🤖 Model Context Protocol (MCP)
- The core logic is exposed via an MCP server in `mcp-server/fhir_graphrag_mcp_server.py`.
- **Tool Definition**: Tools are defined in the `list_tools` handler. Each tool must have a clear description and a strictly defined `inputSchema`.
- **Service Delegation**: Implementation resides in `src/search/` services. The `call_tool` handler should be a thin wrapper. 
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
- 012-fix-test-failures: Added [if applicable, e.g., PostgreSQL, CoreData, files or N/A]
- 011-reset-fhir-security: Added Python 3.11+ + `intersystems-irispython`, `requests`
- 009-full-ux-tests: Added Python 3.11 + Playwright, pytest, pytest-playwright, requests, intersystems-irispython

## Active Technologies
