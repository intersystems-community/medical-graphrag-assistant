# NVIDIA NIM Deployment Options for FHIR GraphRAG

## Overview

NVIDIA NIM can be deployed in two fundamentally different ways:
1. **NVIDIA API Cloud** - Hosted inference via API calls (like OpenAI)
2. **Self-Hosted NIM** - Run NIM containers on your own GPU infrastructure

## Option 1: NVIDIA API Cloud (Recommended for Development)

### What It Is
- NVIDIA hosts the models on their infrastructure
- You make API calls over HTTPS
- Pay per API call (similar to OpenAI pricing)
- **No GPU needed locally**

### Architecture
```
Your MacBook/EC2 Instance
  └─→ HTTPS API Call
       └─→ NVIDIA Cloud (hosted models)
            └─→ Returns embeddings
```

### Pros
- ✅ **No GPU required** - works on MacBook, standard EC2
- ✅ **Fast setup** - just need API key
- ✅ **Zero infrastructure** - no Docker, Kubernetes, GPU drivers
- ✅ **Auto-scaling** - NVIDIA handles load
- ✅ **Always updated** - latest model versions
- ✅ **Low startup cost** - pay only for what you use

### Cons
- ❌ Data leaves your infrastructure (sent to NVIDIA cloud)
- ❌ Per-query costs (can add up at scale)
- ❌ Network latency (API call overhead)
- ❌ Dependent on NVIDIA service availability
- ❌ Rate limits on free tier

### Cost Model
**Free Tier:**
- Limited requests/day (check build.nvidia.com for current limits)
- Good for: Development, testing, small datasets

**Paid Tier:**
- ~$0.0002 per 1K tokens (estimate - check current pricing)
- Example: 10K queries/day × 100 tokens avg = 1M tokens/day = $0.20/day = $6/month

### When to Use
- ✅ Development and prototyping
- ✅ Low-volume production (<1K queries/day)
- ✅ Quick proof-of-concept
- ✅ Testing before committing to infrastructure
- ✅ **Phase 3 of our implementation**

### Setup
1. Get API key from build.nvidia.com
2. Install: `pip install langchain-nvidia-ai-endpoints`
3. Use in code:
```python
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
embeddings = NVIDIAEmbeddings(model="nvidia/nv-embedqa-e5-v5")
vector = embeddings.embed_query("chest pain")
```

---

## Option 2: Self-Hosted NIM (For Production)

### What It Is
- Download NIM Docker containers from NVIDIA
- Run on your own GPU infrastructure (AWS, GCP, Azure, on-prem)
- Models run locally on your GPUs
- You manage infrastructure and scaling

### Architecture Options

#### 2a. AWS EC2 with GPU (Simple)

```
AWS EC2 Instance (g5.xlarge)
  ├─→ NVIDIA A10G GPU (24GB VRAM)
  ├─→ Docker Engine
  │    └─→ NIM Container
  │         └─→ NV-EmbedQA-E5-v5 model
  └─→ Your FHIR App (localhost connection)
```

**Setup Steps:**
1. Launch EC2 instance (g5.xlarge, g4dn.xlarge, or p3.2xlarge)
2. Install NVIDIA drivers and Docker
3. Pull NIM container: `docker pull nvcr.io/nvidia/nv-embedqa-e5-v5`
4. Run container with GPU support
5. Connect your app to localhost:8000

**Pros:**
- ✅ Simple architecture
- ✅ Data stays in your infrastructure
- ✅ Unlimited queries (limited by GPU capacity)
- ✅ Low latency (local inference)
- ✅ Full control over model versions

**Cons:**
- ❌ Fixed cost (instance runs 24/7)
- ❌ Manual scaling (need multiple instances for high load)
- ❌ You manage GPU drivers, Docker, monitoring
- ❌ No auto-scaling

**Cost:**
- g5.xlarge: $1.006/hour = $24/day = $720/month
- g4dn.xlarge: $0.526/hour = $12.62/day = $380/month
- Break-even vs API: ~10K-20K queries/day

**Instance Types:**
| Instance | GPU | VRAM | $/hour | Best For |
|----------|-----|------|--------|----------|
| g4dn.xlarge | T4 | 16GB | $0.526 | Text embeddings |
| g5.xlarge | A10G | 24GB | $1.006 | Text + Vision |
| g5.2xlarge | A10G | 24GB | $1.212 | High throughput |
| p3.2xlarge | V100 | 16GB | $3.06 | Vision models |

#### 2b. AWS EKS with GPU Nodes (Production-Grade)

```
AWS EKS Cluster
  ├─→ Control Plane ($73/month)
  ├─→ GPU Node Group (g5.xlarge instances)
  │    ├─→ NIM Pods (auto-scaling)
  │    └─→ NVIDIA GPU Operator
  ├─→ Application Node Group (t3.large instances)
  │    └─→ FHIR GraphRAG App Pods
  ├─→ Application Load Balancer
  └─→ Auto Scaling Groups
```

**Setup Steps:**
1. Create EKS cluster with GPU node group
2. Install NVIDIA GPU Operator (manages drivers)
3. Deploy NIM as Kubernetes Deployment
4. Configure Horizontal Pod Autoscaler
5. Set up Ingress/Load Balancer

**Pros:**
- ✅ Auto-scaling (scale GPU pods based on load)
- ✅ High availability (multi-instance)
- ✅ Rolling updates (zero-downtime deployments)
- ✅ Enterprise-grade orchestration
- ✅ Resource optimization (pack multiple services)

**Cons:**
- ❌ Complex setup (Kubernetes expertise required)
- ❌ Higher baseline cost (EKS + minimum nodes)
- ❌ More moving parts to manage
- ❌ Longer time to implement

**Cost:**
- EKS Control Plane: $73/month
- 2× g5.xlarge nodes: $1,440/month
- Load Balancer: $20/month
- **Total: ~$1,533/month**

**When to Use:**
- ✅ High query volume (>50K/day)
- ✅ Variable load patterns
- ✅ Multiple NIM models
- ✅ Enterprise production requirements

#### 2c. AWS SageMaker (Managed Inference)

```
AWS SageMaker
  ├─→ Model Registry (store NIM models)
  ├─→ Endpoint (managed inference)
  │    └─→ GPU instances (auto-scaling)
  └─→ Monitoring (CloudWatch)
```

**Pros:**
- ✅ Fully managed by AWS
- ✅ Built-in auto-scaling
- ✅ Integrated monitoring
- ✅ Pay-per-inference pricing option

**Cons:**
- ❌ May not support all NIM containers
- ❌ Less control than EKS
- ❌ Potential vendor lock-in

**Cost:**
- ml.g5.xlarge: $1.408/hour
- Plus data transfer costs

---

## Decision Matrix

### For Phase 3 (Text Embeddings - NOW)
**Recommendation: NVIDIA API Cloud**

| Requirement | API Cloud | EC2 GPU | EKS |
|-------------|-----------|---------|-----|
| Quick setup | ✅ Minutes | ⚠️ Hours | ❌ Days |
| No GPU needed | ✅ Yes | ❌ No | ❌ No |
| Cost to start | ✅ Free tier | ❌ $720/mo | ❌ $1500/mo |
| Good for 51 docs | ✅ Perfect | ⚠️ Overkill | ❌ Overkill |

### For Phase 4+ (Vision + Production)
**Consider: Self-Hosted if query volume justifies**

| Query Volume | Recommendation | Estimated Cost |
|--------------|----------------|----------------|
| <1K/day | API Cloud | $1-10/month |
| 1K-10K/day | API Cloud or EC2 | $50-100/month |
| 10K-50K/day | EC2 GPU | $400-800/month |
| >50K/day | EKS | $1500+/month |

---

## Hybrid Approach (Recommended Strategy)

**Phase 3 (Development):**
→ Use NVIDIA API Cloud
- Validate NIM embeddings work
- Test on 51 DocumentReferences
- Measure accuracy improvement
- **Cost: ~$5/month**

**Phase 4 (Scale Testing):**
→ Still use API Cloud initially
- Test with 10K patient dataset
- Measure query volume and costs
- Calculate break-even point
- **Cost: ~$50-100/month**

**Production Decision:**
→ Choose based on actual usage
- If <10K queries/day → Stay on API Cloud
- If >10K queries/day → Move to EC2 GPU
- If >50K queries/day → Consider EKS

---

## Implementation Plan Update

### Immediate (Phase 3): NVIDIA API Cloud ✅
```bash
# No AWS setup needed!
export NVIDIA_API_KEY="nvapi-xxx"
pip install langchain-nvidia-ai-endpoints
python src/setup/nim_text_vectorize.py
```

### Later (Phase 4+): Evaluate Self-Hosting
```bash
# If query volume justifies:
# 1. Launch AWS EC2 g5.xlarge
# 2. Install NVIDIA drivers + Docker
# 3. Pull NIM container
# 4. Deploy and benchmark
```

---

## Security Considerations

### API Cloud
- ✅ Data encrypted in transit (HTTPS)
- ⚠️ Data processed on NVIDIA servers
- ✅ SOC 2 compliant (NVIDIA)
- ⚠️ Check compliance requirements (HIPAA, etc.)

### Self-Hosted
- ✅ Data never leaves your infrastructure
- ✅ Full control over security
- ✅ HIPAA compliant (if configured properly)
- ⚠️ You responsible for security patches

---

## Recommendation for FHIR GraphRAG Project

**Start with NVIDIA API Cloud** because:
1. **Phase 3 focus**: Text embeddings on 51 documents
2. **MacBook friendly**: No GPU setup needed
3. **Fast iteration**: Validate approach quickly
4. **Low cost**: ~$5-10/month for testing
5. **Later optimization**: Move to self-hosted if needed

**Transition to self-hosted when:**
1. Query volume >10K/day
2. Cost exceeds $100/month on API
3. Data compliance requires on-prem
4. Vision models need local GPUs

---

## Next Steps

### Today: Get Started with API Cloud
1. Get NVIDIA API key from build.nvidia.com
2. Test API access
3. Implement NIM text embeddings
4. Re-vectorize 51 DocumentReferences
5. Measure accuracy improvement

### Later: Evaluate Self-Hosting
1. Monitor query volume over time
2. Calculate actual API costs
3. Compare to EC2 GPU costs
4. Make data-driven decision

**Bottom line: Use API Cloud now, optimize later!** 🚀
