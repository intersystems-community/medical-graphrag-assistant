# Feature Specification: OpenAI → NIM Embeddings Migration Strategy

**Feature Branch**: `002-nim-embeddings-integration`
**Created**: 2025-11-06
**Status**: Draft
**Input**: Implement pluggable embeddings architecture to support OpenAI (development) and NVIDIA NIM (production demo) with minimal code changes. Enable fast iteration with OpenAI API during development, then seamless switch to self-hosted NIM on AWS EC2 for HIPAA-compliant production demos.

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.

  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Developer Uses OpenAI for Fast Development Iteration (Priority: P1)

As a **developer**, I want to use OpenAI's embeddings API during development so that I can rapidly iterate on GraphRAG features without setting up GPU infrastructure, keeping costs minimal ($1-5/month) and working efficiently on my MacBook.

**Why this priority**: This is P1 because it enables immediate development work. Without this, the team is blocked from any progress. It delivers value instantly by unblocking feature development and allows validating the architecture before investing in production infrastructure.

**Independent Test**: Can be fully tested by running `python src/setup/vectorize_documents.py` with `EMBEDDINGS_PROVIDER=openai` environment variable set, successfully vectorizing all 51 DocumentReference resources, and executing vector similarity search queries. Delivers immediate value by enabling development without AWS costs.

**Acceptance Scenarios**:

1. **Given** I have set `EMBEDDINGS_PROVIDER=openai` and `OPENAI_API_KEY` environment variables, **When** I run the vectorization script, **Then** all 51 DocumentReference resources are vectorized using OpenAI text-embedding-3-large (3072-dim) and stored in VectorSearch.FHIRTextVectors table.

2. **Given** the database contains OpenAI-generated vectors, **When** I query for "chest pain and shortness of breath", **Then** I receive semantically relevant clinical notes ranked by cosine similarity within 2 seconds.

3. **Given** I am developing a new feature, **When** I make code changes and re-run vectorization, **Then** the system completes in under 30 seconds for 51 documents, enabling rapid iteration.

---

### User Story 2 - Operations Team Switches to Self-Hosted NIM for Production Demo (Priority: P2)

As an **operations engineer**, I want to seamlessly switch from OpenAI to self-hosted NVIDIA NIM on AWS EC2 by changing a single environment variable, so that I can demonstrate HIPAA-compliant, private deployment to healthcare customers without code changes.

**Why this priority**: This is P2 because it's the core business value - demonstrating private, on-premise capability for sensitive healthcare customers. However, it can wait until after P1 validates the architecture. It delivers the key differentiator for customer demos.

**Independent Test**: Can be fully tested by:
1. Launching EC2 g5.xlarge with NIM container
2. Setting `EMBEDDINGS_PROVIDER=nim` and `NIM_ENDPOINT` environment variables
3. Running the same vectorization script (no code changes)
4. Verifying identical query results compared to OpenAI baseline
Delivers value by proving production-ready private deployment capability.

**Acceptance Scenarios**:

1. **Given** I have launched an EC2 g5.xlarge instance with NIM container running, **When** I set `EMBEDDINGS_PROVIDER=nim` and `NIM_ENDPOINT=http://ec2-xx-xx-xx-xx.amazonaws.com:8000/v1/embeddings`, **Then** the system automatically uses NIM for all embedding operations without code changes.

2. **Given** the system is using NIM embeddings, **When** I vectorize the same 51 DocumentReference resources, **Then** the system generates 1024-dimensional vectors using NV-EmbedQA-E5-v5 model and stores them with provider metadata.

3. **Given** I have vectors from both OpenAI (3072-dim) and NIM (1024-dim) in the database, **When** I query using the current active provider, **Then** the system uses only vectors matching the current provider's dimension to ensure consistent results.

4. **Given** I am demonstrating to a HIPAA-concerned customer, **When** I show the NIM deployment, **Then** I can prove all medical data stays within our EC2 infrastructure (no external API calls) and meets compliance requirements.

---

### User Story 3 - Finance Team Controls Infrastructure Costs (Priority: P3)

As a **finance manager**, I want automated EC2 start/stop scripts so that GPU instances only run during demos (8 hours/day × 20 days/month = $160/month) instead of 24/7 ($720/month), saving $560/month (78% reduction).

**Why this priority**: This is P3 because cost optimization can wait until after proving the technical architecture works. However, it delivers significant ROI and makes the solution economically sustainable. It's independent because scripts can be developed and tested separately from the core embeddings system.

**Independent Test**: Can be fully tested by:
1. Running `./scripts/aws/start-nim-ec2.sh` and verifying instance starts + NIM container accessible
2. Running `./scripts/aws/stop-nim-ec2.sh` and verifying instance stops (billing paused)
3. Calculating monthly costs: 8hrs/day × 20 days × $1.006/hr = $160.96/month
Delivers value by reducing monthly infrastructure costs by 78%.

**Acceptance Scenarios**:

1. **Given** the NIM EC2 instance is stopped, **When** I run `./scripts/aws/start-nim-ec2.sh`, **Then** the instance starts, NIM container becomes available, and the script outputs the NIM endpoint URL to set in environment variables.

2. **Given** the NIM EC2 instance is running, **When** I run `./scripts/aws/stop-nim-ec2.sh`, **Then** the instance stops gracefully, billing is paused, and I see a confirmation message showing estimated daily savings (~$24/day).

3. **Given** I need to do a demo at 10am, **When** I start the instance at 9:50am, **Then** the NIM container is fully ready and accepting requests within 5 minutes (instance start + Docker container warmup).

---

### User Story 4 - Data Scientist Validates Embedding Quality (Priority: P2)

As a **data scientist**, I want to benchmark OpenAI vs NIM embedding quality using the same test queries, so that I can quantify any accuracy differences and make data-driven decisions about which provider to use for production.

**Why this priority**: This is P2 because it validates that switching providers doesn't degrade the user experience. It's critical for ensuring NIM is production-ready, but can only be tested after both providers are implemented. It delivers confidence in the production switch.

**Independent Test**: Can be fully tested by:
1. Creating test query set: ["chest pain", "respiratory symptoms", "diabetes management"]
2. Generating vectors with OpenAI (3072-dim)
3. Generating vectors with NIM (1024-dim)
4. Running identical search queries against both vector sets
5. Comparing top-K results precision and recall
Delivers value by quantifying embedding quality tradeoffs.

**Acceptance Scenarios**:

1. **Given** I have vectorized the same 51 documents with both OpenAI and NIM, **When** I run the benchmark script with 20 test queries, **Then** I get a comparison report showing precision@5, recall@10, and NDCG scores for both providers.

2. **Given** the benchmark results, **When** NIM achieves >90% precision compared to OpenAI baseline, **Then** I can confidently recommend NIM for production use.

3. **Given** I find a query where NIM performs poorly, **When** I investigate the root cause, **Then** I can determine if it's due to dimension difference (1024 vs 3072) or model architecture, and adjust expectations accordingly.

---

### Edge Cases

- **What happens when EMBEDDINGS_PROVIDER is not set?** System defaults to 'openai' for development convenience, but logs a warning suggesting explicit configuration.

- **What happens when switching providers mid-deployment (vectors exist from both providers)?** System filters vectors by provider metadata to ensure consistent dimension matching during queries. Warns if mixed provider vectors detected.

- **What happens when OpenAI API key is invalid or rate-limited?** System raises clear error message with troubleshooting steps (check key validity, check rate limits, consider upgrade).

- **What happens when NIM endpoint is unreachable (EC2 stopped)?** System attempts health check first, raises ConnectionError with clear message to start EC2 instance using provided script path.

- **What happens when vectorizing a large dataset (10K+ documents)?** System processes in batches (100 docs/batch for OpenAI, 50 docs/batch for NIM) with progress indicators and resume capability on failure.

- **What happens when a document has no clinical note content?** System logs warning, skips vectorization for that document, continues processing remaining documents without failure.

- **What happens when vector dimensions don't match during query?** System validates query vector dimension matches stored vectors, raises descriptive error if mismatch (e.g., "Query uses OpenAI (3072-dim) but database contains NIM vectors (1024-dim)").

- **What happens when EC2 instance type is insufficient for NIM model?** NIM container fails to start with out-of-memory error. Documentation clearly specifies minimum requirements: g5.xlarge (24GB GPU VRAM) for NV-EmbedQA-E5-v5.

- **What happens during cost calculation if instance runs 24/7 by mistake?** Monitoring script detects >12 hours uptime, sends alert to stop instance, provides cost warning in daily reports.

- **What happens when migrating between vector dimensions (OpenAI 3072 → NIM 1024)?** System provides migration script that re-vectorizes all documents with new provider, maintains both for comparison period, then archives old vectors.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide an abstract BaseEmbeddings interface with methods: embed_query(text), embed_documents(texts), dimension (property), provider (property).

- **FR-002**: System MUST implement OpenAIEmbeddings class supporting text-embedding-3-large (3072-dim) and text-embedding-3-small (1536-dim) models via OpenAI API.

- **FR-003**: System MUST implement NIMEmbeddings class supporting NV-EmbedQA-E5-v5 (1024-dim) model via HTTP POST to configurable NIM endpoint.

- **FR-004**: System MUST implement EmbeddingsFactory.create() that auto-detects provider from EMBEDDINGS_PROVIDER environment variable (values: 'openai', 'nim').

- **FR-005**: System MUST default to OpenAI provider when EMBEDDINGS_PROVIDER is not set, with warning logged.

- **FR-006**: System MUST test NIM endpoint connectivity with health check before attempting embedding operations, raising ConnectionError with actionable message if unreachable.

- **FR-007**: System MUST create VectorSearch.FHIRTextVectors table with columns: ResourceID, ResourceType, TextContent, Vector (VECTOR type), EmbeddingModel, Provider, CreatedAt.

- **FR-008**: System MUST store provider metadata ('openai' or 'nim') alongside each vector for filtering during queries.

- **FR-009**: System MUST filter query results to match only vectors created by the current active provider (dimension consistency).

- **FR-010**: System MUST vectorize all DocumentReference resources by decoding hex-encoded clinical notes from FHIR JSON ResourceString.

- **FR-011**: System MUST support batch embedding operations (embed_documents) to optimize API usage and reduce latency.

- **FR-012**: System MUST handle API errors gracefully with retry logic (3 retries with exponential backoff) for transient failures.

- **FR-013**: System MUST provide EC2 launch automation script (scripts/aws/launch-nim-ec2.sh) that provisions g5.xlarge instance, installs NIM container, and outputs endpoint URL.

- **FR-014**: System MUST provide EC2 start script (scripts/aws/start-nim-ec2.sh) that starts stopped instance, waits for readiness, retrieves public IP, and displays NIM endpoint.

- **FR-015**: System MUST provide EC2 stop script (scripts/aws/stop-nim-ec2.sh) that gracefully stops instance and displays daily cost savings message (~$24).

- **FR-016**: System MUST provide benchmark script (scripts/benchmark_embeddings.py) that compares OpenAI vs NIM on test query set with precision, recall, and NDCG metrics.

- **FR-017**: System MUST provide migration script (scripts/migrate_provider.py) that re-vectorizes all documents when switching providers, with progress tracking and resume capability.

- **FR-018**: System MUST support environment variable configuration: EMBEDDINGS_PROVIDER, OPENAI_API_KEY, NIM_ENDPOINT (with sensible defaults).

- **FR-019**: System MUST validate OPENAI_API_KEY is set when using OpenAI provider, raising ValueError with setup instructions if missing.

- **FR-020**: System MUST log all embedding operations with provider, model, dimension, and timestamp for debugging and cost tracking.

### Key Entities *(include if feature involves data)*

- **BaseEmbeddings**: Abstract interface defining contract for embedding providers. Key attributes: embed_query() method, embed_documents() method, dimension property (int), provider property (string).

- **OpenAIEmbeddings**: Concrete implementation using OpenAI API. Relationships: inherits BaseEmbeddings, uses OpenAI client library. Key attributes: api_key (from env), model_name (text-embedding-3-large), dimension (3072).

- **NIMEmbeddings**: Concrete implementation using self-hosted NIM. Relationships: inherits BaseEmbeddings, makes HTTP requests to NIM endpoint. Key attributes: endpoint URL, model_name (nvidia/nv-embedqa-e5-v5), dimension (1024).

- **EmbeddingsFactory**: Factory class for creating provider instances. Relationships: creates BaseEmbeddings subclasses based on environment configuration. Key behavior: auto-detection, sensible defaults, clear error messages.

- **FHIRTextVector**: Database entity storing vectorized clinical notes. Relationships: links to FHIR Rsrc via ResourceID. Key attributes: ResourceID (FK), TextContent (decoded clinical note), Vector (VECTOR type), Provider (openai/nim), EmbeddingModel (model identifier), CreatedAt (timestamp).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developer can vectorize all 51 DocumentReference resources using OpenAI in under 60 seconds (measured end-to-end including API calls).

- **SC-002**: Operations engineer can switch from OpenAI to NIM by changing a single environment variable without any code changes, verified by successful re-vectorization.

- **SC-003**: Finance team achieves 78% cost reduction ($560/month savings) by running EC2 instance only 8 hours/day using automated scripts, verified by AWS billing reports.

- **SC-004**: Data scientist validates NIM achieves >85% precision@5 compared to OpenAI baseline on 20 test queries spanning symptoms, conditions, and medications.

- **SC-005**: System handles API failures gracefully with 3 retry attempts, recovering from 95% of transient errors without manual intervention.

- **SC-006**: EC2 instance start/stop scripts complete operations in under 5 minutes, enabling on-demand demos without long wait times.

- **SC-007**: Vector search queries return results within 2 seconds regardless of provider (OpenAI or NIM), maintaining acceptable user experience.

- **SC-008**: System maintains data integrity with 100% of 51 documents successfully vectorized without data loss or corruption when switching providers.

- **SC-009**: Documentation enables a new developer to set up OpenAI development environment in under 15 minutes following README instructions.

- **SC-010**: Production demo on NIM proves zero external API calls during embedding operations, verified by network monitoring, satisfying HIPAA compliance requirements.

## Implementation Guidance *(optional, technology-specific)*

### Recommended Technology Stack

- **Python SDK**: openai>=1.0.0 for OpenAI API client
- **HTTP Client**: requests>=2.31.0 for NIM API calls
- **AWS CLI**: aws-cli>=2.0.0 for EC2 automation scripts
- **Testing**: pytest>=7.0.0 for unit and integration tests

### File Structure

```
src/
  embeddings/
    base_embeddings.py       # Abstract interface
    openai_embeddings.py     # OpenAI implementation
    nim_embeddings.py        # NIM implementation
    embeddings_factory.py    # Provider factory
  setup/
    vectorize_documents.py   # Main vectorization script
scripts/
  aws/
    launch-nim-ec2.sh        # Initial EC2 setup
    start-nim-ec2.sh         # Daily startup
    stop-nim-ec2.sh          # Daily shutdown
  benchmark_embeddings.py    # Quality comparison
  migrate_provider.py        # Provider migration
tests/
  test_openai_embeddings.py
  test_nim_embeddings.py
  test_factory.py
  test_vectorization.py
```

### Environment Variables

```bash
# Development (default)
export EMBEDDINGS_PROVIDER="openai"
export OPENAI_API_KEY="sk-..."

# Production Demo
export EMBEDDINGS_PROVIDER="nim"
export NIM_ENDPOINT="http://ec2-xx-xx-xx-xx.amazonaws.com:8000/v1/embeddings"
```

### Database Migration

```sql
-- Create vector table supporting both providers
CREATE TABLE VectorSearch.FHIRTextVectors (
    ResourceID VARCHAR(255) NOT NULL,
    ResourceType VARCHAR(50) NOT NULL,
    TextContent VARCHAR(MAX),
    Vector VECTOR(DOUBLE, 3072),  -- Max dimension (OpenAI)
    EmbeddingModel VARCHAR(100),
    Provider VARCHAR(20),  -- 'openai' or 'nim'
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ResourceID, Provider)
);

-- Index for fast provider filtering
CREATE INDEX idx_provider ON VectorSearch.FHIRTextVectors(Provider);
```

### Cost Estimation

**Development (OpenAI)**:
- 51 documents × 100 tokens avg = 5,100 tokens
- Cost: $0.00013/1K tokens × 5.1 = $0.0007 (~$0.001)
- Monthly (with iterations): ~$1-5/month

**Production Demo (NIM on EC2)**:
- g5.xlarge: $1.006/hour
- 8 hours/day × 20 days/month = 160 hours
- Cost: 160 × $1.006 = $160.96/month
- Savings vs 24/7: $720 - $160 = $560/month (78%)

### Deployment Phases

**Phase 1: OpenAI Development** (Week 1)
- Implement abstract interface + OpenAI provider
- Vectorize 51 documents
- Develop all features with OpenAI
- Cost: ~$5/month

**Phase 2: NIM Production** (Week 2)
- Launch EC2 with NIM container
- Implement NIM provider
- Test provider switching
- Benchmark quality

**Phase 3: Cost Optimization** (Ongoing)
- Automated start/stop scripts
- Monitoring and alerts
- Production deployment checklist

## Assumptions

- OpenAI API key is readily available or can be obtained within 1 business day
- AWS account has permissions to launch EC2 g5.xlarge instances
- NVIDIA NIM container is available via NGC registry (may require NGC API key)
- Clinical notes are stored as hex-encoded strings in DocumentReference.content[0].attachment.data
- Existing GraphRAG query interface can accept pluggable embedding providers
- 51 DocumentReference resources is sufficient for validating architecture (larger datasets in future phases)
- Healthcare customers require HIPAA compliance proof (no data leaving infrastructure)

## Dependencies

- **External APIs**: OpenAI Embeddings API (text-embedding-3-large)
- **External Services**: NVIDIA NIM container from NGC registry
- **AWS Services**: EC2 (g5.xlarge instance type availability in target region)
- **Existing Components**:
  - HSFHIR_X0001_R.Rsrc table (FHIR native data)
  - Existing vector search functionality (VECTOR_COSINE similarity)
  - IRIS database with native VECTOR type support
- **Python Libraries**: openai, requests, iris-python-driver, sentence-transformers (for comparison baseline)

## Out of Scope

- **Vision embeddings**: NIM vision models for medical images (deferred to Phase 4 in NVIDIA_NIM_MULTIMODAL_PLAN.md)
- **Large-scale datasets**: 10K+ patient datasets (deferred to Phase 1 of multimodal plan)
- **Cross-modal fusion**: RRF combining text + image + graph (deferred to Phase 5)
- **Production auto-scaling**: Kubernetes EKS deployment with auto-scaling GPU nodes (future enhancement)
- **Multi-model support**: Testing multiple NIM embedding models (focus on NV-EmbedQA-E5-v5 only)
- **Embedding cache layer**: Redis caching for frequently queried embeddings (future optimization)
- **Monitoring dashboards**: Grafana/Prometheus monitoring for production (future enhancement)
- **A/B testing framework**: Side-by-side comparison in production traffic (future enhancement)

## Security & Compliance Considerations

- **API Key Security**:
  - OPENAI_API_KEY must never be committed to git
  - Store in environment variables or AWS Secrets Manager
  - Rotate keys every 90 days

- **HIPAA Compliance**:
  - OpenAI mode: Data sent to external API (development only, not for real PHI)
  - NIM mode: All data stays within EC2 infrastructure (production-ready for PHI)
  - Document data residency for customer audits

- **Network Security**:
  - EC2 security groups restrict NIM endpoint to authorized IPs only
  - Use VPC for production deployments
  - TLS/HTTPS for all API communications

- **Access Control**:
  - AWS IAM roles for EC2 instance management
  - Principle of least privilege for API keys
  - Audit logging for all embedding operations

## Risks & Mitigations

- **Risk**: OpenAI API rate limits during development
  - **Mitigation**: Implement exponential backoff, batch requests, monitor rate limits

- **Risk**: NIM container fails to start on EC2 (insufficient GPU memory)
  - **Mitigation**: Document minimum requirements (g5.xlarge 24GB VRAM), test before demo

- **Risk**: Embedding quality degradation when switching to NIM
  - **Mitigation**: Run comprehensive benchmarks before production, accept >85% precision threshold

- **Risk**: EC2 costs exceed budget if left running 24/7
  - **Mitigation**: Automated stop scripts, CloudWatch billing alarms, weekly cost reports

- **Risk**: Dimension mismatch bugs when mixing OpenAI (3072) and NIM (1024) vectors
  - **Mitigation**: Strict provider filtering in queries, clear error messages, integration tests

## Open Questions

- [NEEDS CLARIFICATION]: Should the system support running both OpenAI and NIM simultaneously (A/B testing), or always use a single active provider?
  - **Current assumption**: Single active provider at a time, determined by EMBEDDINGS_PROVIDER env var

- [NEEDS CLARIFICATION]: What is the acceptable quality threshold for NIM vs OpenAI? Is 85% precision sufficient or do we need >95%?
  - **Current assumption**: >85% precision@5 is acceptable, documented in SC-004

- [NEEDS CLARIFICATION]: Should the migration script preserve old vectors or replace them entirely when switching providers?
  - **Current assumption**: Keep both for comparison period (30 days), then archive old vectors

## References

- OpenAI Embeddings API: https://platform.openai.com/docs/guides/embeddings
- NVIDIA NIM Documentation: https://docs.nvidia.com/nim/
- NV-EmbedQA-E5-v5 Model Card: https://build.nvidia.com/nvidia/nv-embedqa-e5-v5
- AWS EC2 Pricing: https://aws.amazon.com/ec2/pricing/
- docs/openai-to-nim-migration.md (detailed implementation guide)
- docs/nvidia-nim-deployment-options.md (deployment comparison)
- docs/nvidia-api-key-setup.md (API key setup instructions)
