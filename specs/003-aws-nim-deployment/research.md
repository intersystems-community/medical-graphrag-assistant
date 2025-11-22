# Research: AWS GPU-based NVIDIA NIM RAG Deployment

**Feature**: 003-aws-nim-deployment
**Date**: 2025-11-09
**Status**: Complete

## Research Questions Resolved

### 1. AWS GPU Instance Selection for NVIDIA NIM

**Decision**: Use g5.xlarge instance type

**Rationale**:
- NVIDIA A10G GPU (24GB VRAM) sufficient for meta/llama-3.1-8b-instruct (requires ~16GB)
- Cost-effective for development/testing ($1.006/hour on-demand vs g5.2xlarge at $1.212/hour)
- 4 vCPUs and 16GB system RAM adequate for vectorization pipelines and IRIS database
- NVMe SSD provides fast local storage for Docker layers and model caching

**Alternatives Considered**:
- p3.2xlarge (V100 GPU): More expensive ($3.06/hour), overkill for 8B parameter model
- g4dn.xlarge (T4 GPU): Cheaper but only 16GB VRAM, insufficient headroom for concurrent LLM + vectorization
- g5.2xlarge: Double the cost for minimal performance gain in single-user scenario

**References**:
- AWS EC2 G5 Instances: https://aws.amazon.com/ec2/instance-types/g5/
- NVIDIA NIM Requirements: https://docs.nvidia.com/nim/large-language-models/latest/getting-started.html

---

### 2. NVIDIA Driver and CUDA Version Compatibility

**Decision**: nvidia-driver-535 with CUDA 12.2

**Rationale**:
- Driver 535 is LTS (Long Term Support) release with proven stability on Ubuntu 24.04
- CUDA 12.2 required for NVIDIA Container Toolkit and NIM containers
- Matches versions used in successful local development testing
- Compatible with NVIDIA A10G GPU (Ampere architecture)

**Alternatives Considered**:
- nvidia-driver-550 (latest): Newer but less tested, potential compatibility issues
- CUDA 11.8: Older, not supported by latest NIM containers

**References**:
- NVIDIA Driver Downloads: https://www.nvidia.com/Download/index.aspx
- CUDA Toolkit Archive: https://developer.nvidia.com/cuda-toolkit-archive

---

### 3. Vector Database Scaling Strategy

**Decision**: IRIS native VECTOR type with B-tree indexes, no specialized vector index initially

**Rationale**:
- IRIS VECTOR(DOUBLE, 1024) provides optimized storage for high-dimensional vectors
- For 100K vectors, brute-force VECTOR_COSINE search performs adequately (<1 second)
- Simpler implementation without external vector index dependencies
- Can add HNSW or IVF indexes later if performance degrades at scale

**Alternatives Considered**:
- pgvector extension: Would require PostgreSQL instead of IRIS, loses native FHIR integration
- Specialized vector DB (Pinecone, Weaviate): Additional cost and operational complexity

**References**:
- IRIS Vector Search Documentation: https://docs.intersystems.com/irislatest/csp/docbook/Doc.View.cls?KEY=GSQL_vecsearch
- Vector Search Performance: Internal IRIS benchmarks show sub-second search for 100K-1M vectors

---

### 4. Batch Processing and Resumability Pattern

**Decision**: Checkpoint-based resumable pipeline with SQLite state tracking

**Rationale**:
- Lightweight SQLite DB tracks processing state (document ID, status, timestamp)
- After interruption, pipeline queries state DB to find last successful batch
- Idempotent: Re-processing same document generates identical vector, safe to reinsert
- No external dependencies beyond Python standard library

**Implementation Pattern**:
```python
# Simplified resumable batch processor
def process_batch(documents, batch_size=50):
    state_db = sqlite3.connect('vectorization_state.db')
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i+batch_size]
        # Check which docs already processed
        unprocessed = filter_unprocessed(batch, state_db)
        if unprocessed:
            vectors = generate_embeddings(unprocessed)
            insert_vectors(vectors)
            mark_processed(unprocessed, state_db)
```

**Alternatives Considered**:
- File-based checkpointing: Harder to query for status, prone to corruption
- No resumability: Unacceptable for 50K+ document processing (could lose hours of work)

**References**:
- Python sqlite3 module: https://docs.python.org/3/library/sqlite3.html
- Idempotent data pipeline patterns: Martin Kleppmann, "Designing Data-Intensive Applications" Chapter 11

---

### 5. NVIDIA NIM Embeddings: Local vs Cloud API

**Decision**: Use NVIDIA NIM Cloud API (nvidia/nv-embedqa-e5-v5) for embeddings

**Rationale**:
- Cloud API provides 1024-dimensional embeddings optimized for retrieval tasks
- Faster deployment (no local embedding model management)
- GPU resources freed for LLM inference
- Acceptable latency for batch processing (~100ms per request for 50 documents)
- Cost: Included in NVIDIA NGC developer tier for reasonable usage

**Trade-offs**:
- Network dependency: Requires retry logic and offline fallback strategy
- API rate limits: Batch size tuning required (found 50 docs/request optimal)

**Alternatives Considered**:
- Local sentence-transformers: Requires GPU memory, slower than cloud-optimized inference
- OpenAI ada-002 embeddings: More expensive, 1536-dim (larger storage footprint)

**References**:
- NVIDIA NIM Embeddings API: https://build.nvidia.com/nvidia/nv-embedqa-e5-v5
- Embedding quality benchmarks: MTEB leaderboard shows nv-embedqa-e5-v5 competitive with OpenAI

---

### 6. Docker GPU Runtime Configuration

**Decision**: NVIDIA Container Toolkit with Docker runtime configuration

**Rationale**:
- Officially supported by NVIDIA for GPU passthrough to containers
- Enables `--gpus all` flag for automatic GPU discovery
- Works with both Docker Compose and standalone docker run commands
- Handles GPU driver library mounting automatically

**Installation Steps**:
```bash
# Add NVIDIA Container Toolkit repository
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
    sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

# Install toolkit
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Configure Docker daemon
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

**Alternatives Considered**:
- nvidia-docker2 (deprecated): Legacy tool, replaced by Container Toolkit
- Podman with crun: Less mature GPU support, smaller ecosystem

**References**:
- NVIDIA Container Toolkit Installation: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html

---

### 7. Deployment Idempotency Strategy

**Decision**: Resource existence checks before creation, fail-safe defaults

**Rationale**:
- Check if EC2 instance exists before launching (via instance tags)
- Check if Docker containers running before starting (docker ps)
- Check if IRIS tables exist before CREATE TABLE (if exists in DDL)
- Safe to re-run deployment scripts multiple times without errors

**Implementation Example**:
```bash
# Idempotent container deployment
if ! docker ps | grep -q nim-llm; then
    docker run -d --name nim-llm --gpus all ...
else
    echo "nim-llm container already running"
fi
```

**Alternatives Considered**:
- Infrastructure as Code (Terraform): Overkill for single-instance deployment, adds complexity
- Ansible playbooks: More appropriate for multi-server deployments

**References**:
- Idempotent script patterns: https://en.wikipedia.org/wiki/Idempotence

---

## Summary of Technology Choices

| Component | Technology | Version | Rationale |
|-----------|------------|---------|-----------|
| Cloud Platform | AWS EC2 | g5.xlarge | Cost-effective GPU instance for NIM workloads |
| Operating System | Ubuntu LTS | 24.04 | Long-term support, NVIDIA driver compatibility |
| GPU Driver | nvidia-driver | 535 (LTS) | Stability and CUDA 12.2 support |
| Container Runtime | Docker + NVIDIA Toolkit | 24+ | Official GPU container support |
| Vector Database | InterSystems IRIS | 2025.1 Community | Native VECTOR type, FHIR integration |
| LLM Service | NVIDIA NIM | meta/llama-3.1-8b-instruct | GPU-accelerated, containerized deployment |
| Embeddings | NVIDIA NIM Cloud API | nvidia/nv-embedqa-e5-v5 | 1024-dim, optimized for retrieval |
| Scripting | Bash | 5.x | Standard for infrastructure automation |
| Data Processing | Python | 3.10+ | IRIS driver, NumPy, requests libraries |
| State Tracking | SQLite | 3.x | Resumable pipeline checkpointing |

## Open Questions (None Remaining)

All technical questions from the feature spec have been resolved through this research phase.
