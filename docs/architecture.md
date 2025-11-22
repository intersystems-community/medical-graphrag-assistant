# System Architecture

## Overview

The FHIR AI Hackathon Kit provides a production-grade RAG (Retrieval Augmented Generation) system for medical data, combining FHIR-based clinical data with GPU-accelerated AI services.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         AWS EC2 g5.xlarge                        │
│                    (NVIDIA A10G GPU, 24GB VRAM)                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────┐    ┌──────────────────┐                   │
│  │   NVIDIA NIM     │    │   NVIDIA NIM     │                   │
│  │   LLM Container  │    │  Vision (future) │                   │
│  │  Llama 3.1 8B    │    │   NV-CLIP-ViT    │                   │
│  │   Port: 8001     │    │   Port: 8002     │                   │
│  │   GPU: ~8GB      │    │   GPU: ~6GB      │                   │
│  └────────┬─────────┘    └────────┬─────────┘                   │
│           │                       │                              │
│  ┌────────┴──────────────────────┴──────────┐                   │
│  │      InterSystems IRIS 2025.1            │                   │
│  │      Vector Database + FHIR Server       │                   │
│  │                                           │                   │
│  │  ┌─────────────────────────────────────┐ │                   │
│  │  │  ClinicalNoteVectors                │ │                   │
│  │  │  - Embedding VECTOR(DOUBLE, 1024)   │ │                   │
│  │  │  - COSINE similarity search         │ │                   │
│  │  │  - 50K+ clinical note vectors       │ │                   │
│  │  └─────────────────────────────────────┘ │                   │
│  │                                           │                   │
│  │  ┌─────────────────────────────────────┐ │                   │
│  │  │  MedicalImageVectors (future)       │ │                   │
│  │  │  - ImageEmbedding VECTOR(DOUBLE,..) │ │                   │
│  │  │  - MIMIC-CXR radiology images       │ │                   │
│  │  └─────────────────────────────────────┘ │                   │
│  │                                           │                   │
│  │  Ports: 1972 (SQL), 52773 (Management)  │                   │
│  └───────────────────────────────────────────┘                   │
│                                                                   │
│  ┌───────────────────────────────────────────┐                   │
│  │     Python Vectorization Pipelines        │                   │
│  │  - Clinical note processing               │                   │
│  │  - NVIDIA embeddings API calls            │                   │
│  │  - Batch processing with checkpointing    │                   │
│  │  - Image vectorization (future)           │                   │
│  └───────────────────────────────────────────┘                   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTPS
                              ▼
                    ┌──────────────────┐
                    │  NVIDIA Cloud    │
                    │  Embeddings API  │
                    │  nv-embedqa-e5   │
                    │  1024 dimensions │
                    └──────────────────┘
```

## Component Details

### 1. Infrastructure Layer

#### AWS EC2 g5.xlarge Instance
- **GPU:** NVIDIA A10G (24GB VRAM, Ampere architecture)
- **CPU:** 4 vCPUs (AMD EPYC 7R32)
- **RAM:** 16GB DDR4
- **Storage:** 500GB gp3 EBS (3000 IOPS, 125 MB/s)
- **OS:** Ubuntu 24.04 LTS
- **Region:** us-east-1 (configurable)

**Why g5.xlarge?**
- Optimal cost/performance: $1.006/hour
- Sufficient GPU memory for Llama 8B + Vision models
- Good network bandwidth for API calls
- General availability across regions

#### NVIDIA Software Stack
- **Driver:** nvidia-driver-535 (LTS branch)
- **CUDA:** 12.2 (provided by driver)
- **Container Toolkit:** nvidia-container-toolkit
- **Docker:** 24+ with GPU runtime

### 2. Database Layer: InterSystems IRIS

#### Why IRIS?
- **Native vector support:** VECTOR(DOUBLE, n) datatype (since 2024.1)
- **FHIR server:** Built-in HL7 FHIR R4 support
- **Performance:** Optimized for high-dimensional vector search
- **SQL interface:** Standard SQL + vector functions
- **Multi-model:** Relational + vector + document + graph

#### IRIS Configuration
```yaml
Container: intersystemsdc/iris-community:2025.1
Namespace: DEMO
Ports:
  - 1972:  SQL port (JDBC/ODBC/Python)
  - 52773: Management portal (Web UI)
  - 51773: SuperServer port

Volumes:
  - iris-data:   /usr/irissys/mgr (database files)
  - iris-config: /usr/irissys/config (configuration)

Memory:
  - Global buffers: 4GB
  - Routine buffers: 256MB
  - Lock table: 64MB
```

#### Vector Table Schema

**ClinicalNoteVectors:**
```sql
CREATE TABLE DEMO.ClinicalNoteVectors (
    ResourceID VARCHAR(255) PRIMARY KEY,
    PatientID VARCHAR(255) NOT NULL,
    DocumentType VARCHAR(255) NOT NULL,
    TextContent VARCHAR(10000),
    SourceBundle VARCHAR(500),
    Embedding VECTOR(DOUBLE, 1024) NOT NULL,
    EmbeddingModel VARCHAR(100) NOT NULL,
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Vector Search Query:**
```sql
-- Find top 10 most similar documents
SELECT TOP 10
    ResourceID,
    PatientID,
    DocumentType,
    TextContent,
    VECTOR_COSINE(Embedding, :queryVector) AS Similarity
FROM DEMO.ClinicalNoteVectors
ORDER BY Similarity DESC;
```

**Performance:**
- Query time: <1s for 100K vectors (without specialized index)
- With HNSW index (IRIS Standard Edition): <100ms for 1M vectors
- Index build time: ~2 minutes for 100K vectors

### 3. AI Services Layer

#### NVIDIA NIM LLM

**Container:** `nvcr.io/nim/meta/llama-3.1-8b-instruct`

**Model Details:**
- Architecture: Llama 3.1 (Meta)
- Parameters: 8 billion
- Context window: 128K tokens
- Quantization: FP16 (auto-selected)
- GPU memory: ~8GB

**API Endpoints:**
```
POST /v1/chat/completions  (OpenAI-compatible)
POST /v1/completions
GET  /v1/models
GET  /health
```

**Configuration:**
```yaml
Environment:
  NGC_API_KEY: ${NVIDIA_API_KEY}
  NIM_MODEL_PROFILE: auto  # fp16 for g5.xlarge

GPU Allocation: all (exclusive access)
Shared Memory: 16GB (--shm-size=16g)
Port: 8001 (maps to container port 8000)
```

**Performance:**
- Inference latency: ~2-4s for 500-token response
- Throughput: ~50 tokens/sec
- Concurrent requests: 2-4 (limited by GPU memory)

#### NVIDIA NIM Embeddings

**Service:** NVIDIA Cloud API (not containerized)

**Model:** `nvidia/nv-embedqa-e5-v5`
- Based on: E5-large-v2
- Dimensions: 1024
- Max input: 512 tokens
- Optimized for: Question-answering, semantic search

**API Endpoint:**
```
POST https://api.nvcf.nvidia.com/v2/nvcf/pexec/functions/...
```

**Rate Limits (Free Tier):**
- Requests: 60/minute
- Tokens: 1M/month
- Concurrent: 3 requests

**Why Cloud API?**
- No GPU memory required
- Always latest model version
- High availability
- Free for development

**Alternative:** Local embedding model (sentence-transformers)
- Pros: No rate limits, offline capable
- Cons: Uses ~2GB GPU memory, different dimensions (768)

#### NVIDIA NIM Vision (Future)

**Container:** `nvcr.io/nim/nvidia/nv-clip-vit`

**Model:** NVIDIA CLIP (Contrastive Language-Image Pre-training)
- Image encoder: ViT-L/14
- Text encoder: Transformer
- Embedding dimension: 768
- GPU memory: ~6GB

**Use Case:** Vectorize MIMIC-CXR radiology images for multi-modal search

### 4. Data Processing Layer

#### Vectorization Pipeline

**Input:** `synthea_clinical_notes.json` (50K+ clinical notes)

**Process:**
```
1. Read JSON file (clinical notes)
2. Batch documents (50 per batch)
3. Call NVIDIA embeddings API
4. Insert vectors into IRIS
5. Checkpoint progress (SQLite)
6. Repeat until complete
```

**Code:** `src/vectorization/vectorize_documents.py`

**Features:**
- Resumable (checkpoint every batch)
- Rate limiting (60 req/min)
- Progress tracking (ETA, throughput)
- Error handling (retry with backoff)
- Batch optimization (minimize API calls)

**Performance:**
- Target: ≥100 docs/sec
- Actual: ~20-50 docs/sec (API rate limited)
- Bottleneck: NVIDIA API rate limits
- Improvement: Upgrade to paid tier or use local embeddings

#### RAG Query Pipeline

**Process:**
```
1. User query (text)
2. Generate query vector (embeddings API)
3. Vector similarity search (IRIS)
4. Retrieve top-k documents
5. Construct LLM prompt (system + context + query)
6. Call NIM LLM
7. Return response
```

**Code:** `src/query/rag_query.py`

**Prompt Template:**
```
System: You are a medical assistant with access to a patient's clinical notes.
Use ONLY the provided clinical notes to answer questions. If the information
is not in the notes, say "Information not available in clinical notes."

Context (top 10 relevant notes):
{retrieved_clinical_notes}

User Question: {query}

Answer:
```

**Performance Breakdown:**
- Query vectorization: ~0.2s
- Vector search: ~0.3s
- Document retrieval: ~0.1s
- LLM generation: ~3s
- **Total:** <5s end-to-end

### 5. Deployment Automation

#### Deployment Workflow

```bash
./scripts/aws/deploy-all.sh
  ├── provision.sh         # EC2 instance + security group + EBS
  ├── setup-gpu.sh         # NVIDIA drivers + CUDA + Docker GPU
  ├── deploy-iris.sh       # IRIS container + volumes + health check
  ├── deploy-nim.sh        # NIM LLM + embeddings config
  ├── create_text_vector_table.py  # Vector table schema
  ├── vectorize_documents.py       # Vectorize 50K+ notes
  └── validate-deployment.sh       # End-to-end tests
```

**Total Time:** ~30 minutes
- Provision: 3 min
- GPU setup: 5 min (+ 2 min reboot)
- IRIS deploy: 2 min
- NIM LLM: 10 min (model download)
- Vectorization: 40 min (50K docs at 20/sec)
- Validation: 1 min

#### Validation Tests

**Infrastructure:**
- ✅ EC2 instance running
- ✅ GPU detected (nvidia-smi)
- ✅ Docker with GPU runtime

**Services:**
- ✅ IRIS healthy (port 1972, 52773)
- ✅ NIM LLM healthy (port 8001)
- ✅ Embeddings API reachable

**Data:**
- ✅ Vector tables exist
- ✅ Vectors inserted (count > 0)
- ✅ Sample vector search works

**RAG:**
- ✅ Query vectorization works
- ✅ Vector search returns results
- ✅ LLM generates response

## Data Flow

### 1. Vectorization Flow

```
synthea_clinical_notes.json
    │
    ▼
Python Script (vectorize_documents.py)
    │
    ├─► Read batch (50 docs)
    │
    ├─► Call NVIDIA Embeddings API
    │     Input: ["clinical note text 1", "note 2", ...]
    │     Output: [[0.23, 0.45, ...], [0.12, 0.67, ...]]  # 1024-dim vectors
    │
    ├─► Insert into IRIS
    │     SQL: INSERT INTO ClinicalNoteVectors VALUES (...)
    │
    ├─► Checkpoint progress
    │     SQLite: UPDATE processed SET status='complete'
    │
    └─► Repeat until done
```

### 2. RAG Query Flow

```
User Query: "What medications is the patient taking?"
    │
    ▼
Generate Query Vector
    │ NVIDIA Embeddings API
    ▼
Query Vector: [0.34, 0.12, 0.89, ...]  # 1024-dim
    │
    ▼
Vector Search (IRIS)
    │ SQL: SELECT TOP 10 ... ORDER BY VECTOR_COSINE(...) DESC
    ▼
Retrieved Documents (top 10 most similar):
    - "Patient on metformin 1000mg BID for diabetes..."
    - "Lisinopril 10mg daily for hypertension..."
    - ...
    │
    ▼
Construct Prompt
    │ System + Context + Query
    ▼
Call NIM LLM
    │ POST /v1/chat/completions
    ▼
LLM Response:
    "Based on the clinical notes, the patient is currently taking:
     1. Metformin 1000mg twice daily for diabetes
     2. Lisinopril 10mg once daily for hypertension
     ..."
    │
    ▼
Return to User
```

## Security Considerations

### Network Security

**Security Group Rules:**
```yaml
Inbound:
  - Port 22:    SSH (restrict to your IP)
  - Port 1972:  IRIS SQL (restrict to app servers)
  - Port 52773: IRIS Management (restrict to admin IPs)
  - Port 8001:  NIM LLM (restrict to app servers)
  - Port 8002:  NIM Vision (restrict to app servers)

Outbound:
  - All traffic allowed (for package downloads, API calls)
```

**Recommendations for Production:**
1. Use VPC with private subnets
2. Place IRIS in private subnet, only accessible via VPN
3. Use ALB/NLB with TLS termination
4. Restrict security groups to minimum required IPs

### Data Security

**At Rest:**
- EBS volumes: Enable encryption at rest
- IRIS database: Enable encryption (Standard Edition)
- Secrets: Use AWS Secrets Manager (not .env files)

**In Transit:**
- IRIS: Use SSL/TLS for connections
- NIM LLM: HTTPS with TLS 1.3
- Embeddings API: HTTPS (enforced by NVIDIA)

**Access Control:**
- IRIS: Change default password (_SYSTEM/ISCDEMO)
- SSH: Use key-based authentication only
- API keys: Rotate regularly, never commit to git

### HIPAA Compliance

**Requirements:**
- [ ] Sign BAA with AWS
- [ ] Sign BAA with NVIDIA (for embeddings API)
- [ ] Enable CloudTrail for audit logging
- [ ] Encrypt all data at rest and in transit
- [ ] Implement access controls (least privilege)
- [ ] Regular security assessments

**Note:** This deployment is for **development/demo only**. Production HIPAA compliance requires additional controls.

## Monitoring & Observability

### Metrics to Monitor

**Infrastructure:**
- EC2 instance status (CloudWatch)
- GPU utilization (nvidia-smi)
- GPU memory usage
- CPU usage
- Disk usage (EBS volume)
- Network I/O

**Services:**
- IRIS database connections
- IRIS query latency
- NIM LLM request rate
- NIM LLM response time
- Embeddings API rate limit status

**Application:**
- Vectorization throughput (docs/sec)
- Vector search latency (ms)
- RAG query latency (ms)
- Error rate (%)

### Logging

**Log Locations:**
```
Docker containers:
  docker logs iris-fhir
  docker logs nim-llm

System logs:
  journalctl -u docker

Application logs:
  logs/vectorization.log
  logs/rag_query.log
```

**Log Aggregation (Future):**
- CloudWatch Logs
- ELK Stack (Elasticsearch, Logstash, Kibana)
- Datadog, New Relic, etc.

## Scalability

### Vertical Scaling

**Current:** g5.xlarge (24GB GPU, 4 vCPU, 16GB RAM)

**Upgrade Path:**
- g5.2xlarge: 48GB GPU, 8 vCPU, 32GB RAM (~$1.21/hour)
  - Supports larger LLM models (Llama 70B quantized)
  - More concurrent requests

- g5.4xlarge: 96GB GPU (A10G x2), 16 vCPU, 64GB RAM (~$2.03/hour)
  - Multi-GPU support
  - Run LLM + Vision simultaneously

### Horizontal Scaling

**Read Scaling:**
1. Deploy IRIS replicas (read-only)
2. Load balance vector search queries
3. Cache frequent queries (Redis)

**Write Scaling:**
1. Partition vectorization by document type
2. Multiple embedding workers
3. Batch processing with queues (SQS)

**LLM Scaling:**
1. Deploy multiple NIM LLM containers
2. Load balance with ALB
3. Auto-scaling based on GPU utilization

## Cost Optimization

### Current Costs (24/7)

```
EC2 g5.xlarge: $1.006/hour × 730 hours = $734/month
EBS 500GB gp3: $0.08/GB × 500 = $40/month
Data Transfer: ~$50/month
Total: ~$824/month
```

### Optimization Strategies

**1. Use Spot Instances (70% savings):**
```
EC2 Spot: ~$0.30/hour × 730 = $219/month
Savings: ~$515/month
Risk: May be interrupted
```

**2. Stop When Not in Use (66% savings for 8hr/day):**
```
EC2: $1.006/hour × 243 hours = $244/month
EBS: $40/month (always charged)
Total: $284/month
Savings: ~$540/month
```

**3. Use Reserved Instances (30% savings, 1-year):**
```
EC2 Reserved: ~$0.70/hour × 730 = $511/month
Savings: ~$223/month
Commitment: 1 year
```

**4. Optimize Storage:**
```
Reduce EBS to 200GB: $16/month (save $24/month)
Use S3 for backups: $0.023/GB
```

**Recommendation for Development:**
- Use Spot instances with auto-stop (8hrs/day)
- Total: ~$150-200/month

## Future Enhancements

### 1. Multi-Modal Search (Phase 4)
- Add MIMIC-CXR image vectorization
- Deploy NIM Vision container
- Combine text + image search results
- Cross-modal retrieval (query text, retrieve images)

### 2. Advanced Indexing
- Upgrade to IRIS Standard Edition
- Implement HNSW index for faster search
- Benchmark: <100ms for 1M vectors

### 3. Federated Search
- Integrate with external FHIR servers
- Real-time data sync
- Multi-source vector search

### 4. Fine-Tuned Models
- Fine-tune embeddings on medical data
- Fine-tune LLM on clinical notes
- Improve domain-specific accuracy

### 5. Production Hardening
- Implement authentication (OAuth2, JWT)
- Add rate limiting (API Gateway)
- Set up monitoring (CloudWatch, Prometheus)
- Disaster recovery (automated backups)
- High availability (multi-AZ deployment)

## References

### Documentation
- [NVIDIA NIM Documentation](https://docs.nvidia.com/nim/)
- [InterSystems IRIS Vector Search](https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=GSQL_vecsearch)
- [AWS EC2 G5 Instances](https://aws.amazon.com/ec2/instance-types/g5/)

### Research Papers
- Llama 3: [Meta AI Blog](https://ai.meta.com/llama/)
- E5 Embeddings: [arXiv:2212.03533](https://arxiv.org/abs/2212.03533)
- CLIP: [arXiv:2103.00020](https://arxiv.org/abs/2103.00020)
- RAG: [arXiv:2005.11401](https://arxiv.org/abs/2005.11401)

### Related Projects
- [Synthea](https://synthetichealth.github.io/synthea/) - Synthetic patient data
- [MIMIC-CXR](https://physionet.org/content/mimic-cxr/2.0.0/) - Chest X-ray database
- [FHIR Server](https://github.com/microsoft/fhir-server) - Microsoft FHIR Server
