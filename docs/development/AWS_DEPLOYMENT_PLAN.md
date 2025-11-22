# AWS Deployment Plan - FHIR AI Hackathon Kit

**Status**: Ready to Deploy 🚀
**Target**: Production FHIR multimodal search with IRIS + NIM
**Date**: 2025-11-07

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        AWS VPC (us-east-1)                      │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ EC2 Instance (m5.2xlarge or g5.xlarge)                   │  │
│  │                                                           │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │  │
│  │  │ IRIS         │  │ Python API   │  │ NIM           │  │  │
│  │  │ Community    │  │ Flask/FastAPI│  │ NV-CLIP       │  │  │
│  │  │ Port: 1972   │  │ Port: 5000   │  │ Port: 8000    │  │  │
│  │  │              │  │              │  │               │  │  │
│  │  │ • 50K texts  │  │ • Vector     │  │ • Text embed  │  │  │
│  │  │ • 944 images │  │   search API │  │ • Image embed │  │  │
│  │  │ • GraphRAG   │  │ • FHIR query │  │ • 1024-dim    │  │  │
│  │  └──────────────┘  └──────────────┘  └───────────────┘  │  │
│  │                                                           │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │ EBS Volume (100 GB gp3)                            │  │  │
│  │  │ - IRIS database (iris-data)                        │  │  │
│  │  │ - MIMIC-CXR images                                 │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Security Group: fhir-ai-stack                            │  │
│  │ • 22 (SSH)       - Your IP only                          │  │
│  │ • 1972 (IRIS)    - VPC only                              │  │
│  │ • 5000 (API)     - Public (or ALB)                       │  │
│  │ • 8000 (NIM)     - VPC only                              │  │
│  │ • 52773 (Portal) - Your IP only (optional)               │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Cost Estimate

### Instance Types (Monthly, 24/7)

| Instance Type | vCPU | RAM   | GPU       | Hourly  | Monthly  | Use Case              |
|---------------|------|-------|-----------|---------|----------|-----------------------|
| m5.2xlarge    | 8    | 32 GB | None      | $0.384  | $280     | IRIS + API (no NIM)   |
| g5.xlarge     | 4    | 16 GB | A10G 24GB | $1.006  | $735     | IRIS + API + NIM      |
| g5.2xlarge    | 8    | 32 GB | A10G 24GB | $1.212  | $885     | Full stack, best perf |

### Cost-Saving Strategy (8hrs/day, 20 days/month)

| Instance Type | 8hrs/day Cost | Savings vs 24/7 |
|---------------|---------------|-----------------|
| m5.2xlarge    | $61/month     | 78% ($219)      |
| g5.xlarge     | $161/month    | 78% ($574)      |
| g5.2xlarge    | $194/month    | 78% ($691)      |

**Recommended**: g5.xlarge with auto-stop scripts = **$161/month**

### Storage Costs

- EBS gp3 (100 GB): ~$8/month
- S3 (MIMIC-CXR backup): ~$2.30/month (100 GB)

**Total Monthly (Smart Usage)**: ~$171

---

## Deployment Options

### Option 1: Single EC2 Instance (Recommended) ✅

**Pros**:
- ✅ Simplest deployment
- ✅ Lowest cost
- ✅ Easy to manage
- ✅ Works for demos/POCs

**Cons**:
- ❌ Single point of failure
- ❌ Can't scale horizontally

**Best For**: Demos, hackathons, development

---

### Option 2: ECS/Fargate (Future)

**Pros**:
- ✅ Auto-scaling
- ✅ High availability
- ✅ Managed infrastructure

**Cons**:
- ❌ More complex
- ❌ Higher cost
- ❌ Requires RDS for IRIS (or separate EC2)

**Best For**: Production at scale

---

## Phase 1: Infrastructure Setup ☐

### 1.1 Prerequisites

```bash
# AWS CLI configured
aws configure
# AWS Access Key ID: [YOUR_KEY]
# AWS Secret Access Key: [YOUR_SECRET]
# Default region: us-east-1
# Default output format: json

# EC2 Key Pair created
aws ec2 create-key-pair \
  --key-name fhir-ai-key \
  --query 'KeyMaterial' \
  --output text > fhir-ai-key.pem
chmod 400 fhir-ai-key.pem

# Environment variables
export AWS_REGION="us-east-1"
export NVIDIA_API_KEY="nvapi-..."  # From build.nvidia.com
export NGC_API_KEY="..."           # From ngc.nvidia.com
```

### 1.2 Security Group

```bash
# Create security group
aws ec2 create-security-group \
  --group-name fhir-ai-stack \
  --description "FHIR AI Hackathon Kit - IRIS + NIM"

# Get your IP
MY_IP=$(curl -s ifconfig.me)

# Allow SSH from your IP
aws ec2 authorize-security-group-ingress \
  --group-name fhir-ai-stack \
  --protocol tcp --port 22 --cidr ${MY_IP}/32

# Allow API access (public)
aws ec2 authorize-security-group-ingress \
  --group-name fhir-ai-stack \
  --protocol tcp --port 5000 --cidr 0.0.0.0/0

# Allow IRIS portal (your IP only, optional)
aws ec2 authorize-security-group-ingress \
  --group-name fhir-ai-stack \
  --protocol tcp --port 52773 --cidr ${MY_IP}/32
```

### 1.3 Launch Script Created

See: `scripts/aws/launch-fhir-stack.sh`

---

## Phase 2: Application Deployment ☐

### 2.1 Docker Compose on EC2

```yaml
# docker-compose.aws.yml
version: '3.8'

services:
  iris-fhir:
    image: intersystemsdc/iris-community:latest
    container_name: iris-fhir
    ports:
      - "1972:1972"
      - "52773:52773"
    environment:
      - IRISNAMESPACE=DEMO
      - ISC_DEFAULT_PASSWORD=ISCDEMO
    volumes:
      - iris-data:/usr/irissys/mgr
    restart: unless-stopped

  fhir-api:
    build: .
    container_name: fhir-api
    ports:
      - "5000:5000"
    environment:
      - IRIS_HOST=iris-fhir
      - IRIS_PORT=1972
      - IRIS_NAMESPACE=DEMO
      - NVIDIA_API_KEY=${NVIDIA_API_KEY}
      - NIM_ENDPOINT=${NIM_ENDPOINT}
    depends_on:
      - iris-fhir
    restart: unless-stopped

  nim-embeddings:
    image: nvcr.io/nim/nvidia/nv-embedqa-e5-v5:latest
    container_name: nim-embeddings
    ports:
      - "8000:8000"
    environment:
      - NGC_API_KEY=${NGC_API_KEY}
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    restart: unless-stopped

volumes:
  iris-data:
```

### 2.2 Data Migration

**Option A: Export/Import** (Clean)
```bash
# Local: Export IRIS database
docker exec iris-fhir iris export /tmp/iris-backup.gof DEMO

# Copy to EC2
scp -i fhir-ai-key.pem /tmp/iris-backup.gof ubuntu@<EC2_IP>:/tmp/

# EC2: Import into IRIS
docker exec iris-fhir iris import /tmp/iris-backup.gof DEMO
```

**Option B: Volume Snapshot** (Faster for large data)
```bash
# Local: Create tarball of IRIS volume
docker run --rm \
  -v fhir-server_iris-fhir-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/iris-data-backup.tar.gz /data

# Upload to S3
aws s3 cp iris-data-backup.tar.gz s3://fhir-ai-backups/

# EC2: Download and restore
aws s3 cp s3://fhir-ai-backups/iris-data-backup.tar.gz .
docker run --rm \
  -v iris-data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/iris-data-backup.tar.gz -C /
```

**Option C: Re-vectorize** (Most reliable)
```bash
# EC2: Run vectorization scripts
python3 ingest_mimic_cxr_reports.py 0  # All reports
python3 ingest_mimic_cxr_images.py 0   # All images
```

---

## Phase 3: Testing & Validation ☐

### 3.1 Health Checks

```bash
# IRIS connectivity
curl http://<EC2_IP>:52773/csp/sys/UtilHome.csp

# NIM health
curl http://<EC2_IP>:8000/health

# API health
curl http://<EC2_IP>:5000/health

# Vector search test
curl -X POST http://<EC2_IP>:5000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "chest pain", "limit": 5}'
```

### 3.2 Performance Benchmarks

```bash
# Text vector search (3072-dim, 50K docs)
time python3 -c "
from src.query.test_vector_search import test_search
test_search('chest pain')
"

# Image vector search (1024-dim, 944 images)
time python3 -c "
from src.query.test_image_search import test_image_search
test_image_search('pneumonia infiltrate')
"

# Expected: <500ms for community IRIS
# Expected: <50ms for licensed IRIS with ACORN=1
```

---

## Phase 4: Production Readiness ☐

### 4.1 Monitoring

```bash
# CloudWatch metrics
aws cloudwatch put-metric-data \
  --namespace FHIR-AI \
  --metric-name VectorSearchLatency \
  --value <latency_ms>

# Docker stats
docker stats --no-stream
```

### 4.2 Backups

```bash
# Daily IRIS backup (cron)
0 2 * * * docker exec iris-fhir iris export /backups/daily-$(date +\%Y\%m\%d).gof DEMO

# Sync to S3
0 3 * * * aws s3 sync /backups s3://fhir-ai-backups/
```

### 4.3 Auto-Start/Stop Scripts

See existing:
- `scripts/aws/start-nim-ec2.sh`
- `scripts/aws/stop-nim-ec2.sh`

Adapt for full stack.

---

## Phase 5: Upgrade to Licensed IRIS (Future) ☐

### When to Upgrade

- ✅ Need <50ms vector search (vs ~500ms)
- ✅ Dataset grows beyond 100K documents
- ✅ Production demos require fast response
- ✅ iris-devtester docker-compose support ready

### Upgrade Steps

1. Use `docker-compose.licensed.x64.yml`
2. Copy `iris.x64.key` to EC2
3. Export data from community IRIS
4. Launch licensed IRIS container
5. Import data
6. Enable CallIn service (iris-devtester)
7. Benchmark performance improvement

**Expected Gains**:
- Text search: <50ms (vs ~500ms) = 10x faster
- Image search: <10ms (vs ~100ms) = 10x faster
- Throughput: 1000+ queries/sec (vs ~100)

---

## Quick Start Checklist

### Local Preparation
- [ ] AWS CLI configured
- [ ] EC2 key pair created
- [ ] Environment variables set (NVIDIA_API_KEY, NGC_API_KEY)
- [ ] IRIS data exported or ready to re-vectorize

### AWS Deployment
- [ ] Security group created
- [ ] EC2 instance launched
- [ ] Docker + docker-compose installed
- [ ] Containers running (IRIS, API, NIM)
- [ ] Data migrated/vectorized

### Testing
- [ ] IRIS accessible (port 1972, 52773)
- [ ] NIM health check passing
- [ ] API health check passing
- [ ] Vector search working

### Production
- [ ] CloudWatch monitoring enabled
- [ ] Daily backups configured
- [ ] Auto-stop scripts in place
- [ ] DNS/domain configured (optional)

---

## Files to Create

### Deployment Scripts
1. ✅ `scripts/aws/launch-nim-ec2.sh` (exists)
2. ☐ `scripts/aws/launch-fhir-stack.sh` (new)
3. ☐ `scripts/aws/start-fhir-stack.sh` (new)
4. ☐ `scripts/aws/stop-fhir-stack.sh` (new)

### Docker Files
5. ☐ `docker-compose.aws.yml` (new)
6. ✅ `docker-compose.licensed.x64.yml` (exists)
7. ☐ `Dockerfile` for API (new)

### Documentation
8. ✅ `AWS_DEPLOYMENT_PLAN.md` (this file)
9. ☐ `docs/aws-deployment-guide.md` (step-by-step)

---

## Current Status

**Decision**: Deploy community IRIS first, upgrade to licensed later

**Reason**:
- Community IRIS working perfectly locally
- 50K+ text vectors, 944 image vectors loaded
- Licensed IRIS has connectivity issues (iris-devtester team working on it)
- Performance acceptable for demos (<500ms vs <50ms)

**Timeline**:
- Phase 1-2: 1-2 hours (infrastructure + deployment)
- Phase 3: 30 minutes (testing)
- Phase 4: 1 hour (production setup)
- Phase 5: Deferred (future upgrade)

**Total Estimated Time**: 3-4 hours to production

---

## Next Steps

1. Create `scripts/aws/launch-fhir-stack.sh`
2. Create `docker-compose.aws.yml`
3. Test deployment on EC2
4. Benchmark performance
5. Document results in PROGRESS.md
