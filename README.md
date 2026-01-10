# Medical GraphRAG Assistant

[![GitHub](https://img.shields.io/badge/GitHub-isc--tdyar%2Fmedical--graphrag--assistant-blue?logo=github)](https://github.com/isc-tdyar/medical-graphrag-assistant)

A production-ready medical AI assistant platform built on Model Context Protocol (MCP), featuring GraphRAG multi-modal search, FHIR integration, NVIDIA NIM embeddings, and AWS Bedrock Claude Sonnet 4.5.

**GitHub Repository**: [https://github.com/isc-tdyar/medical-graphrag-assistant](https://github.com/isc-tdyar/medical-graphrag-assistant)

**Originally forked from**: [FHIR-AI-Hackathon-Kit](https://github.com/gabriel-ing/FHIR-AI-Hackathon-Kit)

**Current Version**: v2.16.0 (Decoupled Services & Health CLI)

## What This Is

An **agentic medical chat platform** with advanced capabilities:
- 🤖 **Model Context Protocol (MCP)** - Claude autonomously calls medical search tools
- 🧠 **GraphRAG** - Knowledge graph-based retrieval with decoupled service logic
- 🖼️ **Medical Image Search** - Semantic search over chest X-rays using NV-CLIP embeddings
- 💾 **Agent Memory System** - Persistent semantic memory with vector search
- 🏥 **FHIR Integration** - Full-text search of clinical documents
- 🛠️ **System Health CLI** - Comprehensive environment validation and auto-fixing
- ☁️ **AWS Deployment** - Production deployment on AWS EC2 with NVIDIA A10G GPU
- 📊 **Interactive UI** - Streamlit interface with execution transparency
- 🗄️ **InterSystems IRIS** - Vector database with native VECTOR(DOUBLE, 1024) support

## Quick Start

### 1. Verify Environment

```bash
# Verify database, GPU, and schema integrity
python -m src.cli check-health --smoke-test

# If tables are missing or authentication fails (HTTP 401):
python -m src.cli fix-environment

# Or reset security settings specifically:
python -m src.cli reset-security
```

### 2. Run the Streamlit Chat Interface

```bash
# Install dependencies
pip install -r requirements.txt

# Set AWS credentials
export AWS_PROFILE=your-profile

# Configure NV-CLIP endpoint (for medical images and memory)
export NVCLIP_BASE_URL="http://localhost:8002/v1"  # Local NIM via SSH tunnel

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

### System Overview

```mermaid
flowchart TB
    subgraph UI["🖥️ Presentation Layer"]
        ST[Streamlit Chat UI<br/>v2.15.0]
    end

    subgraph LLM["🧠 AI/LLM Layer"]
        direction LR
        NIM[NVIDIA NIM<br/>Llama 3.1 8B]
        OAI[OpenAI<br/>GPT-4o]
        BED[AWS Bedrock<br/>Claude Sonnet 4.5]
    end

    subgraph MCP["⚡ MCP Server Layer"]
        MCPS[FHIR + GraphRAG MCP Server<br/>14+ Medical Tools]
    end

    subgraph DATA["🗄️ Data Layer"]
        direction LR
        IRIS[(InterSystems IRIS<br/>Vector Database)]
        FHIR[FHIR Documents<br/>51 Clinical Notes]
        GRAPH[Knowledge Graph<br/>83 Entities • 540 Relations]
        IMG[Medical Images<br/>50 Chest X-rays]
        MEM[Agent Memory<br/>Semantic Store]
    end

    subgraph EMB["🔢 Embedding Layer"]
        NVCLIP[NVIDIA NV-CLIP<br/>1024-dim Multimodal]
    end

    ST <-->|Multi-LLM Support| LLM
    LLM <-->|MCP Protocol| MCPS
    MCPS <-->|IRIS Native API| IRIS
    IRIS --- FHIR
    IRIS --- GRAPH
    IRIS --- IMG
    IRIS --- MEM
    MCPS <-->|Embedding API| NVCLIP
```

### GraphRAG Data Flow

```mermaid
flowchart LR
    subgraph INPUT["📥 Input"]
        Q[User Query]
    end

    subgraph RECALL["🔄 Auto-Recall"]
        MR[Memory Recall<br/>Past Corrections]
    end

    subgraph SEARCH["🔍 Multi-Modal Search"]
        direction TB
        VS[Vector Search<br/>FHIR Documents]
        GS[Graph Search<br/>Entities & Relations]
        IS[Image Search<br/>NV-CLIP Similarity]
    end

    subgraph FUSION["⚗️ Fusion"]
        RRF[Reciprocal Rank Fusion<br/>RRF Algorithm]
    end

    subgraph OUTPUT["📤 Output"]
        R[Ranked Results +<br/>Knowledge Graph Viz]
    end

    Q --> MR
    MR --> VS
    MR --> GS
    MR --> IS
    VS --> RRF
    GS --> RRF
    IS --> RRF
    RRF --> R
```

### Component Interaction

```mermaid
sequenceDiagram
    participant U as User
    participant S as Streamlit UI
    participant L as LLM (Claude/GPT/NIM)
    participant M as MCP Server
    participant I as IRIS DB
    participant N as NV-CLIP

    U->>S: "Find pneumonia X-rays"
    S->>L: Query + Tools
    L->>M: search_medical_images()
    M->>N: embed_text(query)
    N-->>M: 1024-dim vector
    M->>I: VECTOR_COSINE search
    I-->>M: Top-K results
    M-->>L: Images + metadata
    L->>M: search_knowledge_graph()
    M->>I: Entity/relation query
    I-->>M: Graph data
    M-->>L: Entities + relations
    L-->>S: Response + visualizations
    S-->>U: Display results
```

### IRIS Vector Package Architecture

This project uses the **InterSystems IRIS Vector** ecosystem:

```mermaid
flowchart TB
    subgraph APP["🏥 Medical GraphRAG Assistant"]
        MCP[MCP Server<br/>14+ Medical Tools]
        CFG[YAML Config<br/>CloudConfiguration API]
    end

    subgraph IRIS_PKG["📦 InterSystems IRIS Vector Packages"]
        direction TB
        RAG["<a href='https://pypi.org/project/iris-vector-rag/'>iris-vector-rag</a><br/>RAG Framework"]
        GRAPH["<a href='https://pypi.org/project/iris-vector-graph/'>iris-vector-graph</a><br/>Graph Toolkit"]

        subgraph RAG_DETAIL["iris-vector-rag Features"]
            BYOT[BYOT Storage<br/>Bring Your Own Tables]
            PIPE[RAG Pipelines<br/>basic • graphrag • crag]
            SCHEMA[SchemaManager<br/>Table Validation]
        end

        subgraph GRAPH_DETAIL["iris-vector-graph Features"]
            ENT[Entity Storage<br/>Type-Tagged Nodes]
            REL[Relationship Store<br/>Typed Edges]
            TRAV[Graph Traversal<br/>Path Queries]
        end
    end

    subgraph IRIS_DB["🗄️ InterSystems IRIS"]
        VEC[(VECTOR Column<br/>DOUBLE, 1024)]
        SQL[(SQL Tables<br/>ClinicalNoteVectors)]
        KG[(Knowledge Graph<br/>Entities • Relations)]
    end

    MCP --> RAG
    MCP --> GRAPH
    CFG --> RAG
    RAG --> BYOT
    RAG --> PIPE
    RAG --> SCHEMA
    GRAPH --> ENT
    GRAPH --> REL
    GRAPH --> TRAV
    BYOT --> VEC
    SCHEMA --> SQL
    ENT --> KG
    REL --> KG
```

**Package Links:**
- [`iris-vector-rag`](https://pypi.org/project/iris-vector-rag/) - Production RAG framework with multiple pipelines (basic, graphrag, crag, multi_query_rrf)
- [`iris-vector-graph`](https://pypi.org/project/iris-vector-graph/) - Graph-oriented vector toolkit for GraphRAG workloads

### NVIDIA NIM Architecture

This project uses **[NVIDIA NIM](https://developer.nvidia.com/nim)** (Inference Microservices) for GPU-accelerated AI inference, deployed on AWS EC2 with NVIDIA A10G GPUs.

```mermaid
flowchart TB
    subgraph AWS["☁️ AWS EC2 g5.xlarge"]
        subgraph GPU["🎮 NVIDIA A10G GPU (24GB)"]
            direction TB
            NIM_LLM["<a href='https://build.nvidia.com'>NIM Container</a><br/>Port 8001<br/>meta/llama-3.1-8b-instruct"]
            NIM_CLIP["<a href='https://build.nvidia.com/nvidia/nvclip'>NV-CLIP Container</a><br/>Port 8002<br/>nvidia/nvclip"]
        end

        subgraph SERVICES["🔧 Application Services"]
            MCP[MCP Server<br/>Medical Tools]
            ST[Streamlit UI<br/>Port 8501]
            IRIS[(IRIS DB<br/>Port 1972)]
        end
    end

    subgraph CLIENT["💻 Client"]
        TUNNEL[SSH Tunnel<br/>localhost:8002 → AWS:8002]
        APP[Local Development]
    end

    APP --> |NVCLIP_BASE_URL| TUNNEL
    TUNNEL --> NIM_CLIP
    ST --> MCP
    MCP --> |Text Embeddings| NIM_LLM
    MCP --> |Image Embeddings| NIM_CLIP
    MCP --> |Vector Search| IRIS
    NIM_LLM --> GPU
    NIM_CLIP --> GPU
```

**NIM Services:**

| Service | Model | Port | Purpose | Dimension |
|---------|-------|------|---------|-----------|
| **NIM LLM** | `meta/llama-3.1-8b-instruct` | 8001 | Text generation, entity extraction | N/A |
| **NV-CLIP** | `nvidia/nvclip` | 8002 | Multimodal embeddings (text + images) | 1024-dim |
| **NV-EmbedQA** | `nvidia/nv-embedqa-e5-v5` | Cloud API | Text embeddings for RAG | 1024-dim |

**Deployment Options:**
- **Self-hosted NIM** (Production): Docker containers on GPU instances with HIPAA compliance
- **NVIDIA Cloud API** (Development): `https://integrate.api.nvidia.com/v1` with API key

### Knowledge Graph: Entity & Relationship Extraction

The knowledge graph is built from FHIR DocumentReference resources using **regex-based entity extraction** with confidence scoring. No external medical ontology is currently used - entities are extracted using curated regex patterns.

```mermaid
flowchart LR
    subgraph FHIR["📄 FHIR Repository"]
        DOC[DocumentReference<br/>Clinical Notes]
    end

    subgraph EXTRACT["🔬 Entity Extraction"]
        direction TB
        REGEX[Regex Patterns<br/>Confidence-Scored]
        TYPES[Entity Types:<br/>SYMPTOM • CONDITION<br/>MEDICATION • PROCEDURE<br/>BODY_PART • TEMPORAL]
    end

    subgraph RELATE["🔗 Relationship Inference"]
        direction TB
        HEUR[Heuristic Rules:<br/>Proximity + Context]
        REL_TYPES[Relationship Types:<br/>TREATS • CAUSES<br/>LOCATED_IN • CO_OCCURS]
    end

    subgraph STORE["🗄️ Knowledge Graph Tables"]
        ENT_TBL[(RAG.Entities<br/>83 entities)]
        REL_TBL[(RAG.EntityRelationships<br/>540 relationships)]
    end

    DOC --> REGEX
    REGEX --> TYPES
    TYPES --> HEUR
    HEUR --> REL_TYPES
    REL_TYPES --> ENT_TBL
    REL_TYPES --> REL_TBL
```

**Entity Types Extracted:**

| Type | Examples | Confidence Range |
|------|----------|-----------------|
| `SYMPTOM` | chest pain, shortness of breath, fever | 0.80 - 0.95 |
| `CONDITION` | hypertension, diabetes, pneumonia | 0.75 - 0.95 |
| `MEDICATION` | aspirin, metformin, insulin | 0.85 - 0.95 |
| `PROCEDURE` | CT scan, MRI, blood test | 0.85 - 0.92 |
| `BODY_PART` | chest, abdomen, heart | 0.75 - 0.90 |
| `TEMPORAL` | 3 days ago, last week | 0.75 - 0.95 |

**Relationship Types:**

| Relationship | Pattern | Example |
|-------------|---------|---------|
| `TREATS` | MEDICATION → CONDITION/SYMPTOM | aspirin → chest pain |
| `CAUSES` | CONDITION → SYMPTOM | hypertension → headache |
| `LOCATED_IN` | SYMPTOM → BODY_PART | pain → chest |
| `CO_OCCURS` | SYMPTOM ↔ SYMPTOM (within window) | fever ↔ cough |

**Current Limitations & Future Work:**
- **No medical ontology** (SNOMED-CT, ICD-10, RxNorm) - extraction is pattern-based
- **No FHIR native queries** - clinical notes are hex-decoded from DocumentReference.content
- Future: LLM-based entity extraction for improved coverage and ontology mapping

### MCP Tools Architecture

The MCP server exposes **14+ tools** that Claude (or other LLMs) can autonomously call to search medical data.

```mermaid
flowchart TB
    subgraph LLM["🧠 LLM (Claude/GPT/NIM)"]
        AGENT[Agentic Chat]
    end

    subgraph MCP["⚡ MCP Server Tools"]
        direction TB
        subgraph SEARCH["🔍 Search Tools"]
            T1[search_fhir_documents<br/>Full-text clinical notes]
            T2[search_knowledge_graph<br/>Entity-based search]
            T3[hybrid_search<br/>RRF fusion of all sources]
            T4[search_medical_images<br/>NV-CLIP similarity]
        end

        subgraph DETAIL["📋 Detail Tools"]
            T5[get_document_details<br/>Full document content]
            T6[get_entity_relationships<br/>Graph traversal]
            T7[get_entity_statistics<br/>Graph stats]
        end

        subgraph MEMORY["💾 Memory Tools"]
            T8[remember_information<br/>Store corrections/prefs]
            T9[recall_information<br/>Semantic memory search]
            T10[get_memory_stats<br/>Memory statistics]
        end

        subgraph VIZ["📊 Visualization Tools"]
            T11[plot_symptom_frequency]
            T12[plot_entity_distribution]
            T13[plot_patient_timeline]
            T14[plot_entity_network]
        end
    end

    subgraph DATA["🗄️ Data Sources"]
        FHIR[(FHIR Documents)]
        KG[(Knowledge Graph)]
        IMG[(Medical Images)]
        MEM[(Agent Memory)]
    end

    AGENT -->|MCP Protocol| MCP
    T1 --> FHIR
    T2 --> KG
    T3 --> FHIR
    T3 --> KG
    T3 --> IMG
    T4 --> IMG
    T8 --> MEM
    T9 --> MEM
```

**Tool Categories:**

| Category | Tools | Data Source | Query Type |
|----------|-------|-------------|------------|
| **FHIR Search** | `search_fhir_documents`, `get_document_details` | ClinicalNoteVectors | Full-text SQL LIKE |
| **GraphRAG** | `search_knowledge_graph`, `get_entity_relationships`, `hybrid_search` | Entities, EntityRelationships | Entity + Vector + RRF |
| **Medical Images** | `search_medical_images` | MIMICCXRImages | VECTOR_COSINE (NV-CLIP) |
| **Agent Memory** | `remember_information`, `recall_information` | AgentMemoryVectors | VECTOR_COSINE (NV-CLIP) |
| **Visualization** | `plot_*` tools | All sources | Plotly/NetworkX charts |

**Note:** FHIR queries are performed via SQL on pre-ingested data in IRIS tables. The system does **not** make live FHIR REST API calls - documents are batch-loaded during setup and stored with their embeddings in IRIS vector columns.

### Data Pipeline: Ingestion → Storage → Query

> **Note:** Current implementation uses **batch vectorization** on initial data load. Vectors are stored in standard VECTOR columns and require manual re-vectorization when source documents change. See [Future Enhancements](#future-enhancements) for planned automatic sync capabilities.

```mermaid
flowchart LR
    subgraph INGEST["📥 Data Ingestion (Batch)"]
        direction TB
        FHIR_SRC[FHIR Bundles<br/>JSON Resources]
        CXR[MIMIC-CXR<br/>Chest X-rays]
        PARSE[fhirpy Parser<br/>Resource Extraction]
    end

    subgraph EMBED["🔢 Vectorization"]
        direction TB
        NIM_EMB[NVIDIA NIM<br/>NV-EmbedQA-E5-v5]
        NVCLIP_EMB[NV-CLIP<br/>Multimodal 1024-dim]
        NER[Entity Extraction<br/>Symptoms • Conditions]
    end

    subgraph STORE["🗄️ IRIS FHIR Repository"]
        direction TB
        subgraph FHIR_TABLES["FHIR Tables"]
            DOC[(ClinicalNoteVectors<br/>51 Documents)]
            IMG[(MIMICCXRImages<br/>50 X-rays)]
        end
        subgraph GRAPH_TABLES["Knowledge Graph"]
            ENT_TBL[(Entities<br/>83 Nodes)]
            REL_TBL[(EntityRelationships<br/>540 Edges)]
        end
        subgraph MEM_TABLES["Agent Memory"]
            MEM_TBL[(AgentMemoryVectors<br/>Semantic Store)]
        end
    end

    subgraph QUERY["🔍 Query Processing"]
        direction TB
        VEC_SEARCH[Vector Search<br/>VECTOR_COSINE]
        GRAPH_TRAV[Graph Traversal<br/>Entity → Relations]
        RRF_FUSE[RRF Fusion<br/>Rank Combination]
    end

    subgraph OUTPUT["📤 Results"]
        RANKED[Ranked Documents<br/>+ Knowledge Graph]
    end

    FHIR_SRC --> PARSE
    CXR --> NVCLIP_EMB
    PARSE --> NIM_EMB
    PARSE --> NER
    NIM_EMB --> DOC
    NVCLIP_EMB --> IMG
    NER --> ENT_TBL
    NER --> REL_TBL
    DOC --> VEC_SEARCH
    IMG --> VEC_SEARCH
    ENT_TBL --> GRAPH_TRAV
    REL_TBL --> GRAPH_TRAV
    MEM_TBL --> VEC_SEARCH
    VEC_SEARCH --> RRF_FUSE
    GRAPH_TRAV --> RRF_FUSE
    RRF_FUSE --> RANKED
```

### IRIS Database Schema

```mermaid
erDiagram
    ClinicalNoteVectors {
        int ID PK
        string ResourceID UK
        string PatientID
        string DocumentType
        text TextContent
        vector Embedding "VECTOR(DOUBLE,1024)"
        string EmbeddingModel
        string SourceBundle
    }

    MIMICCXRImages {
        int ID PK
        string DicomID UK
        string PatientID
        string StudyID
        string ViewPosition
        text Findings
        vector Embedding "VECTOR(DOUBLE,1024)"
        string ImagePath
    }

    Entities {
        int ID PK
        string EntityText
        string EntityType
        float Confidence
        string SourceDocID FK
    }

    EntityRelationships {
        int ID PK
        int SourceEntityID FK
        int TargetEntityID FK
        string RelationType
        float Confidence
        string SourceText
        string TargetText
    }

    AgentMemoryVectors {
        int ID PK
        string MemoryType
        text Content
        vector Embedding "VECTOR(DOUBLE,1024)"
        datetime CreatedAt
    }

    ClinicalNoteVectors ||--o{ Entities : "extracts"
    Entities ||--o{ EntityRelationships : "source"
    Entities ||--o{ EntityRelationships : "target"
```

## Features

### MCP Tools (10+ available)

**FHIR & GraphRAG:**
1. **search_fhir_documents** - Full-text search of clinical notes
2. **get_document_details** - Retrieve complete clinical notes by ID
3. **search_knowledge_graph** - Search medical entities (symptoms, conditions, medications)
4. **hybrid_search** - Combined vector + graph search with RRF fusion
5. **get_entity_statistics** - Knowledge graph statistics and insights

**Medical Images:**
6. **search_medical_images** - Semantic search over chest X-rays with NV-CLIP

**Agent Memory:**
7. **remember_information** - Store semantic memories (corrections, knowledge, preferences, feedback)
8. **recall_information** - Semantic search over agent memories
9. **get_memory_stats** - Memory system statistics

**Visualizations:**
10. **plot_symptom_frequency** - Chart of most common symptoms
11. **plot_entity_distribution** - Entity type distribution charts
12. **plot_patient_timeline** - Patient encounter timeline
13. **plot_entity_network** - Knowledge graph relationship visualization
14. **visualize_graphrag_results** - Interactive GraphRAG search results

### Chat Interface Features

- ✅ **Multi-Modal Search** - Search clinical text, medical images, and knowledge graph
- ✅ **Agent Memory** - Persistent semantic memory with vector search
- ✅ **Medical Image Display** - View chest X-rays with DICOM support
- ✅ **Execution Transparency** - See which tools Claude calls and its reasoning
- ✅ **Interactive Charts** - Generate visualizations from data
- ✅ **Conversation History** - Multi-turn conversations with context
- ✅ **Memory Editor** - Browse, search, add, and delete agent memories in sidebar
- ✅ **Error Handling** - Graceful handling of API issues with detailed logs
- ✅ **Max Iterations Control** - Prevents infinite loops (10 iteration limit)

**Recent Features (v2.16.0):**
- ✅ **Decoupled Search Services**: Search logic extracted from MCP server into `src/search/` for testability.
- ✅ **System Health CLI**: New `python -m src.cli` tool for environment validation and fixing.
- ✅ **Radiology Fix**: Ensured `SQLUser.FHIRDocuments` table is correctly initialized on EC2.

**Previous Updates (v2.14.0):**
- ✅ **Auto Memory Recall**: Memories automatically recalled before each query to guide tool selection
- ✅ **Interactive Graph Viz**: Force-directed, draggable graphs with `streamlit-agraph`
- ✅ **Memory in Execution Log**: See recalled memories in "Show Execution Details" pane
- ✅ NetworkX-powered graph layouts with physics simulation

**Previous Updates:**
- v2.13.0: Multi-LLM provider support (NIM > OpenAI > Bedrock), OneDrive backup
- v2.12.0: Agent memory system with pure IRIS vector storage
- v2.10.2: Fixed content processing errors, increased max iterations
- v2.10.0: GraphRAG multi-modal search with RRF fusion
- v2.0.0: AWS deployment with NVIDIA NIM integration

## Configuration

### Required Environment Variables

```bash
# AWS Credentials
export AWS_PROFILE=your-profile  # or set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY

# IRIS Database (defaults to local Docker container)
export IRIS_HOST=localhost    # Default; set to your EC2 IP for remote
export IRIS_PORT=32782        # Docker port (1972 for native IRIS)
export IRIS_NAMESPACE=%SYS
export IRIS_USERNAME=_SYSTEM
export IRIS_PASSWORD=SYS      # Default Docker password

# NVIDIA NV-CLIP (for medical images and memory)
export NVCLIP_BASE_URL="http://localhost:8002/v1"  # Local NIM via SSH tunnel
# or use cloud API:
# export NVCLIP_BASE_URL="https://integrate.api.nvidia.com/v1"
# export NVIDIA_API_KEY="your-api-key"
```

### Config Files

- `config/fhir_graphrag_config.yaml` - Local development config
- `config/fhir_graphrag_config.aws.yaml` - **AWS production config (active)**
- `config/aws-config.yaml` - AWS infrastructure settings

## Project Structure

```
medical-graphrag-assistant/
├── mcp-server/                      # MCP server and Streamlit app
│   ├── fhir_graphrag_mcp_server.py  # MCP server (Tool Wrappers)
│   ├── streamlit_app.py             # Chat UI v2.12.0 with memory editor
│   └── test_*.py                    # Integration tests
├── src/
│   ├── cli/                         # System Management CLI
│   ├── db/                          # IRIS database clients
│   ├── embeddings/                  # NVIDIA NIM integration
│   ├── memory/                      # Agent memory system
│   ├── search/                      # Decoupled Search Services (Business Logic)
│   │   ├── fhir_search.py           # Document search
│   │   ├── kg_search.py             # Knowledge graph search
│   │   └── hybrid_search.py         # Multi-modal fusion
│   ├── vectorization/               # Document vectorization
│   └── validation/                  # Data validation & Health checks
├── config/                          # Configuration files
│   └── fhir_graphrag_config.aws.yaml  # Active AWS config
├── docs/                            # Documentation
│   ├── architecture.md              # System architecture
│   ├── deployment-guide.md          # AWS deployment
│   └── troubleshooting.md           # Common issues
├── scripts/                         # Deployment and utility scripts
│   └── aws/                         # AWS-specific scripts
├── tests/                           # Test suite
└── archive/                         # Historical implementations and docs
```

## Technology Stack

**AI/ML:**
- AWS Bedrock (Claude Sonnet 4.5)
- NVIDIA NV-CLIP (1024-dim multimodal embeddings)
- NVIDIA NIM (Inference Microservices)
- Model Context Protocol (MCP)

**Database & Vector Storage:**
- InterSystems IRIS Community Edition (AWS EC2)
- Native VECTOR(DOUBLE, 1024) support
- VECTOR_COSINE similarity search
- Tables: ClinicalNoteVectors, MIMICCXRImages, Entities, EntityRelationships, AgentMemoryVectors

**InterSystems IRIS Vector Packages:**
- [`iris-vector-rag`](https://pypi.org/project/iris-vector-rag/) - Production RAG framework with BYOT storage, GraphRAG pipelines, and CloudConfiguration API
- [`iris-vector-graph`](https://pypi.org/project/iris-vector-graph/) - Graph-oriented vector toolkit for entity storage and relationship traversal
- `intersystems-irispython` - Native IRIS database driver

**Infrastructure:**
- AWS EC2 g5.xlarge (NVIDIA A10G GPU)
- Python 3.10+
- Streamlit for UI
- Docker for containerization

**Key Libraries:**
- `fhirpy` - FHIR resource parsing and handling
- `boto3` - AWS SDK
- `streamlit` - Chat UI
- `streamlit-agraph` - Interactive graph visualization
- `mcp` - Model Context Protocol SDK
- `pydicom` - DICOM medical image processing
- `networkx` - Graph algorithms and layout

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

**Medical Images:**
- "Show me chest X-rays of pneumonia"
- "Find chest X-rays showing cardiomegaly"
- "Search for lateral view chest X-rays"

**Agent Memory:**
- "Remember that I prefer concise clinical summaries"
- "What do you know about my preferences?"
- "Recall any corrections I've given you about medical terminology"

**Hybrid Search:**
- "Find treatment options for chronic pain" (combines vector + graph + image search)

**Visualization:**
- "Show a chart of conditions by frequency"
- "Visualize the knowledge graph for chest pain"
- "Graph the entity relationships"

## Backup

The project uses OneDrive for automatic cloud backup:

```bash
# Run backup (rsync to OneDrive folder)
./scripts/backup-to-onedrive.sh
```

Backup includes all code, configs, and medical images (~195 MB). OneDrive automatically syncs to cloud.

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

### AWS Deployment

The system is deployed on AWS EC2 with:
- **Instance**: g5.xlarge (NVIDIA A10G GPU)
- **Region**: us-east-1
- **Database**: InterSystems IRIS Community Edition
- **GPU Services**: NVIDIA NIM for NV-CLIP embeddings
- **Data**: 50 medical images, 51 clinical notes, 83 entities, 540 relationships

See [docs/deployment-guide.md](docs/deployment-guide.md) for detailed deployment instructions.

## Troubleshooting

See [docs/troubleshooting.md](docs/troubleshooting.md) for common issues.

**Common Issues:**
- AWS credentials not configured → Set AWS_PROFILE or AWS env vars
- IRIS connection failed → Check IRIS_HOST and credentials
- NV-CLIP not responding → Check NVCLIP_BASE_URL and SSH tunnel
- Medical images not found → Verify image paths and DICOM support
- Memory search returning 0 results → Check embeddings with magnitude test
- Max iterations reached → Query may be too complex, try simplifying

## Documentation

### Core Documentation
- [Architecture Overview](docs/architecture.md) - System design and data flow
- [Deployment Guide](docs/deployment-guide.md) - AWS deployment instructions
- [Troubleshooting Guide](docs/troubleshooting.md) - Common issues and solutions

### Current Session Docs
- [EMBEDDINGS_FIXED.md](EMBEDDINGS_FIXED.md) - Image and memory embeddings fix
- [MEMORY_SEARCH_BROWSE_FIX.md](MEMORY_SEARCH_BROWSE_FIX.md) - Memory search UI fix
- [PROGRESS.md](PROGRESS.md) - Development history and achievements
- [TODO.md](TODO.md) - Current tasks and roadmap

### Historical Documentation
- [archive/](archive/) - Old implementations, scripts, and session docs

## Future Enhancements

### Automatic Vector Synchronization

**Current State:** Vectors are generated via batch processing during initial data load. When FHIR documents are updated in the repository, embeddings must be manually re-generated.

**Planned Enhancement:** Leverage IRIS EMBEDDING column type for automatic vector synchronization:

```sql
-- Future: Auto-computed embeddings on INSERT/UPDATE
CREATE TABLE ClinicalNoteVectors (
    ID INT PRIMARY KEY,
    TextContent TEXT,
    Embedding EMBEDDING[MODEL='NV-EmbedQA-E5-v5'](TextContent)  -- Auto-computed
);
```

**Benefits:**
- Automatic re-vectorization when `TextContent` changes
- No manual batch re-processing required
- Real-time sync between FHIR repository and vector store

### Additional Planned Features

- **FHIR Subscription Hooks** - Trigger vectorization on resource create/update events
- **Incremental Knowledge Graph Updates** - Update entities/relationships without full rebuild
- **IRIS HealthShare Integration** - Direct FHIR R4 repository connection
- **Vector Index Optimization** - HNSW index tuning for larger datasets
- **Multi-tenant Support** - Namespace isolation for multiple healthcare organizations

## Contributing

This project is based on the FHIR-AI-Hackathon-Kit. The original tutorial content remains in the `tutorial/` directory.

## License

Inherits license from upstream FHIR-AI-Hackathon-Kit repository.

## Acknowledgments

- **Original Project**: [FHIR-AI-Hackathon-Kit](https://github.com/gabriel-ing/FHIR-AI-Hackathon-Kit) by gabriel-ing
- **InterSystems IRIS** for the vector database platform
- **AWS Bedrock** for Claude Sonnet 4.5 access
- **NVIDIA NIM** for NV-CLIP multimodal embeddings
- **Model Context Protocol** by Anthropic
- **MIMIC-CXR** dataset for medical imaging data
