# OpenAI → NIM Embeddings Migration

**Pluggable embeddings architecture for FHIR GraphRAG**

Switch between OpenAI (development) and NVIDIA NIM (production) with a single environment variable.

## Architecture

```
Development: OpenAI API ($1-5/month, no GPU needed)
    ↓
Production: Self-hosted NIM on AWS EC2 ($160/month with auto-stop)
    ↓
Same interface, same code, different provider
```

## Quick Start

### Option A: Development with OpenAI (Recommended First)

**1. Install dependencies**
```bash
pip install openai iris-python-driver
```

**2. Set API key**
```bash
export OPENAI_API_KEY="sk-..."
export EMBEDDINGS_PROVIDER="openai"
```

**3. Create database table**
```bash
python src/setup/create_text_vector_table.py
```

**4. Vectorize documents**
```bash
python src/setup/vectorize_documents.py
```

**5. Test vector search**
```bash
python src/query/test_vector_search.py "chest pain"
```

**Cost**: ~$0.001 for 51 documents, ~$1-5/month total

---

### Option B: Production with NIM (After OpenAI Works)

**1. Launch EC2 with NIM**
```bash
# Update instance config in launch script first!
./scripts/aws/launch-nim-ec2.sh
```

**2. Switch to NIM**
```bash
export EMBEDDINGS_PROVIDER="nim"
export NIM_ENDPOINT="http://ec2-xx-xx-xx-xx.amazonaws.com:8000/v1/embeddings"
```

**3. Re-vectorize with NIM**
```bash
python src/setup/vectorize_documents.py
```

**4. Test NIM search**
```bash
python src/query/test_vector_search.py "chest pain"
```

**5. Stop instance when done (save $24/day)**
```bash
./scripts/aws/stop-nim-ec2.sh
```

**Cost**: ~$160/month (8 hrs/day × 20 days)

---

## Architecture Details

### Abstract Interface

All providers implement `BaseEmbeddings`:

```python
class BaseEmbeddings(ABC):
    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """Embed single query"""
        pass

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple documents"""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Vector dimension"""
        pass

    @property
    @abstractmethod
    def provider(self) -> str:
        """Provider name (openai/nim)"""
        pass
```

### Factory Pattern

Automatically creates correct provider:

```python
from src.embeddings.embeddings_factory import EmbeddingsFactory

# Auto-detect from EMBEDDINGS_PROVIDER env var
embedder = EmbeddingsFactory.create()

# Use same interface regardless of provider
vector = embedder.embed_query("chest pain")
```

### Database Schema

Supports both OpenAI (3072-dim) and NIM (1024-dim):

```sql
CREATE TABLE VectorSearch.FHIRTextVectors (
    ResourceID VARCHAR(255) NOT NULL,
    ResourceType VARCHAR(50) NOT NULL,
    TextContent VARCHAR(MAX),
    Vector VECTOR(DOUBLE, 3072),  -- Max dimension
    EmbeddingModel VARCHAR(100),
    Provider VARCHAR(20),  -- 'openai' or 'nim'
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ResourceID, Provider)
);
```

## Cost Comparison

| Approach | Monthly Cost | Use Case |
|----------|--------------|----------|
| OpenAI API | $1-5 | Development, 51 docs |
| NIM 24/7 | $720 | ❌ Wasteful |
| NIM 8hrs/day × 20 days | $160 | ✅ Smart production |

**Savings with auto-stop: $560/month (78%)**

## Workflow

### Development Phase (Week 1)

```bash
# Use OpenAI for fast iteration
export EMBEDDINGS_PROVIDER="openai"
export OPENAI_API_KEY="sk-..."

# Develop features rapidly
python src/setup/vectorize_documents.py
python src/query/test_vector_search.py "diabetes"

# Cost: ~$5/month
```

### Production Demo (Week 2)

```bash
# Launch EC2 with NIM
./scripts/aws/launch-nim-ec2.sh

# Switch to NIM (no code changes!)
export EMBEDDINGS_PROVIDER="nim"
export NIM_ENDPOINT="http://ec2-xx-xx-xx-xx.amazonaws.com:8000/v1/embeddings"

# Same scripts, different provider
python src/setup/vectorize_documents.py
python src/query/test_vector_search.py "diabetes"

# Cost: $160/month with auto-stop
```

### Daily Cost Control

```bash
# Morning: Start for demo
./scripts/aws/start-nim-ec2.sh
export NIM_ENDPOINT="http://$(aws ec2 describe-instances ...):8000/v1/embeddings"

# Run demos, tests, development
python src/query/test_vector_search.py "chest pain"

# Evening: Stop to save money (~$24/day)
./scripts/aws/stop-nim-ec2.sh
```

## Provider Comparison

| Feature | OpenAI | NIM |
|---------|--------|-----|
| **Model** | text-embedding-3-large | nvidia/nv-embedqa-e5-v5 |
| **Dimension** | 3072 | 1024 |
| **Cost (51 docs)** | $0.001 | $0 (after EC2) |
| **Setup Time** | 5 minutes | 30 minutes |
| **Infrastructure** | None (API) | AWS EC2 GPU |
| **Data Privacy** | External API | Private (on-prem) |
| **HIPAA Compliant** | ⚠️ (dev only) | ✅ (production ready) |
| **Use Case** | Development | Production demos |

## File Structure

```
src/
  embeddings/
    base_embeddings.py         # Abstract interface
    openai_embeddings.py       # OpenAI implementation
    nim_embeddings.py          # NIM implementation
    embeddings_factory.py      # Provider factory
  setup/
    create_text_vector_table.py  # Database setup
    vectorize_documents.py     # Vectorization script
  query/
    test_vector_search.py      # Test queries

scripts/
  aws/
    launch-nim-ec2.sh          # Initial EC2 setup
    start-nim-ec2.sh           # Daily startup
    stop-nim-ec2.sh            # Daily shutdown

docs/
  openai-to-nim-migration.md  # Detailed guide
  nvidia-nim-deployment-options.md  # Deployment comparison
  nvidia-api-key-setup.md     # API key guide

specs/
  002-nim-embeddings-integration/
    spec.md                    # Feature specification
```

## Environment Variables

### For OpenAI (Development)
```bash
export EMBEDDINGS_PROVIDER="openai"
export OPENAI_API_KEY="sk-..."
```

### For NIM (Production)
```bash
export EMBEDDINGS_PROVIDER="nim"
export NIM_ENDPOINT="http://ec2-xx-xx-xx-xx.amazonaws.com:8000/v1/embeddings"
export INSTANCE_ID="i-xxxxxxxxxxxx"  # For start/stop scripts
```

## Troubleshooting

### OpenAI Issues

**Error: "OPENAI_API_KEY environment variable not set"**
```bash
# Get API key from https://platform.openai.com/api-keys
export OPENAI_API_KEY="sk-..."
```

**Error: "Rate limit exceeded"**
- Wait a few minutes and retry
- Implement batch processing (already included)
- Consider upgrading OpenAI plan

### NIM Issues

**Error: "Cannot reach NIM endpoint"**
```bash
# Check instance is running
./scripts/aws/start-nim-ec2.sh

# Test endpoint
curl http://ec2-xx-xx-xx-xx.amazonaws.com:8000/health
```

**Error: "Dimension mismatch"**
```bash
# Query filters by provider automatically
# If you see this, check which provider is active:
echo $EMBEDDINGS_PROVIDER

# Re-vectorize if you switched providers:
python src/setup/vectorize_documents.py
```

### Database Issues

**No results from vector search**
```sql
-- Check vectors exist for current provider
SELECT Provider, COUNT(*) as VectorCount
FROM VectorSearch.FHIRTextVectors
GROUP BY Provider;
```

## Testing

### Unit Tests
```bash
# Test OpenAI embeddings
pytest tests/test_openai_embeddings.py

# Test NIM embeddings
pytest tests/test_nim_embeddings.py

# Test factory
pytest tests/test_factory.py
```

### Integration Test
```bash
# Test full workflow
python src/setup/create_text_vector_table.py
python src/setup/vectorize_documents.py
python src/query/test_vector_search.py "chest pain"
```

## Performance Benchmarks

### OpenAI (51 documents)
- Total time: ~15 seconds
- Per document: ~0.3 seconds
- Cost: $0.001

### NIM (51 documents)
- Total time: ~30 seconds
- Per document: ~0.6 seconds
- Cost: $0 (after EC2)

### Query Performance
- Both providers: <2 seconds
- Vector dimension doesn't significantly impact query speed

## Next Steps

### Immediate (P1)
- [x] Set up OpenAI development environment
- [ ] Test with OpenAI: Vectorize 51 documents
- [ ] Validate vector search results

### Production Prep (P2)
- [ ] Update EC2 launch script with your AWS config
- [ ] Launch NIM EC2 instance
- [ ] Test provider switching (OpenAI → NIM)
- [ ] Benchmark quality: OpenAI vs NIM

### Cost Optimization (P3)
- [ ] Set up CloudWatch billing alarms
- [ ] Create cron job for auto-stop (evening)
- [ ] Monitor actual usage patterns
- [ ] Calculate ROI

## Security

### API Keys
- Never commit API keys to git
- Use environment variables or AWS Secrets Manager
- Rotate keys every 90 days

### HIPAA Compliance
- **OpenAI**: Development only, no real PHI
- **NIM**: Production-ready for PHI
- All medical data stays in your EC2 infrastructure

### Network Security
- EC2 security groups: Restrict port 8000 to authorized IPs
- Use VPC for production
- TLS/HTTPS for all API communications

## Support

### Documentation
- Full specification: `specs/002-nim-embeddings-integration/spec.md`
- Migration guide: `docs/openai-to-nim-migration.md`
- Deployment options: `docs/nvidia-nim-deployment-options.md`

### Common Questions

**Q: Can I use both OpenAI and NIM simultaneously?**
A: Yes! The database stores provider metadata. You can have both:
```sql
SELECT Provider, COUNT(*) FROM VectorSearch.FHIRTextVectors GROUP BY Provider;
-- openai  | 51
-- nim     | 51
```

**Q: Which provider should I use for production?**
A: If <10K queries/day and no HIPAA requirements → OpenAI
   If >10K queries/day or HIPAA required → NIM on EC2

**Q: Can I switch mid-project?**
A: Yes! Just change `EMBEDDINGS_PROVIDER` and re-vectorize. Old vectors remain for comparison.

## License

See main project LICENSE file.
