# Medical GraphRAG Deployment Guide

## 🎉 System Status

✅ **NV-CLIP NIM**: Running on AWS (localhost:8002)
✅ **IRIS Vector DB**: Running on AWS (localhost:1972)
✅ **Medical Images**: 12 images loaded with real NV-CLIP embeddings
✅ **Semantic Search**: Tested and working (85% similarity)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  AWS g5.xlarge (NVIDIA A10G)                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌────────────────────┐        ┌──────────────────────┐   │
│  │ NV-CLIP NIM        │        │ IRIS Vector DB       │   │
│  │ (Docker)           │        │ (Docker)             │   │
│  │                    │        │                      │   │
│  │ Model: nvclip      │        │ MedicalImageVectors  │   │
│  │ Dims:  1024        │        │ 12 images loaded     │   │
│  │ Port:  8002        │        │ Port: 1972           │   │
│  └────────────────────┘        └──────────────────────┘   │
│           │                              │                 │
│           └──────────────┬───────────────┘                │
│                          │                                 │
│                  ┌───────▼──────────┐                     │
│                  │ Backend Services │                     │
│                  │ - Embeddings     │                     │
│                  │ - Search API     │                     │
│                  │ - MCP Server     │                     │
│                  └──────────────────┘                     │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ (Two deployment options)
                           │
        ┌──────────────────┴──────────────────┐
        │                                     │
        ▼                                     ▼
┌───────────────┐                  ┌──────────────────┐
│ Option A:     │                  │ Option B:        │
│ AWS Streamlit │                  │ Local Streamlit  │
│ (port 8501)   │                  │ (SSH tunnel)     │
└───────────────┘                  └──────────────────┘
```

## Deployment Options

### Option A: Streamlit on AWS (Fully Cloud)

**Pros:**
- Single endpoint to access
- Lower latency (everything co-located)
- No SSH tunneling needed

**Cons:**
- Need to configure AWS Security Group
- Uses more AWS resources

**Deploy:**
```bash
./deploy_streamlit_aws.sh
```

**Access:** http://3.84.250.46:8501

**Important:** You must configure AWS Security Group:
1. Go to AWS Console → EC2 → Security Groups
2. Find security group for instance `i-0432eba10b98c4949`
3. Add inbound rule:
   - Type: Custom TCP
   - Port: 8501
   - Source: 0.0.0.0/0 (or your IP for security)

### Option B: Streamlit Local (Hybrid) ⭐ RECOMMENDED

**Pros:**
- No AWS Security Group changes needed
- Faster UI iteration (local development)
- Run UI on your local machine with full IDE support

**Cons:**
- Requires SSH tunnel (auto-managed by script)
- Slightly higher latency (tunneled connections)

**Deploy:**
```bash
./deploy_streamlit_local.sh
```

**Access:** http://localhost:8501

**How it works:**
- Streamlit UI runs on your local machine
- SSH tunnels connect to AWS backend:
  - Port 1972: IRIS Database
  - Port 8002: NV-CLIP NIM
- All data stays on AWS, only UI is local

## Current System Configuration

### AWS Instance
- **Type**: g5.xlarge
- **GPU**: NVIDIA A10G (24GB VRAM)
- **IP**: 3.84.250.46
- **Instance ID**: i-0432eba10b98c4949
- **SSH Key**: `~/.ssh/medical-graphrag-key.pem`

### NV-CLIP NIM Container
```bash
# Container name: nim-nvclip
# Status: Running
# Port: 8002 (host) → 8000 (container)
# Model: nvcr.io/nim/nvidia/nvclip:2.0.0
# GPU: Full A10G access
```

**Verify:**
```bash
ssh -i ~/.ssh/medical-graphrag-key.pem ubuntu@3.84.250.46 "docker ps | grep nim-nvclip"
```

### IRIS Vector Database
```bash
# Container name: iris-vector-db
# Status: Running
# Port: 1972
# Database: USER
# Credentials: _SYSTEM/SYS
```

**Verify:**
```bash
ssh -i ~/.ssh/medical-graphrag-key.pem ubuntu@3.84.250.46 "docker ps | grep iris"
```

### Database Schema
```sql
CREATE TABLE SQLUser.MedicalImageVectors (
    ImageID VARCHAR,
    PatientID VARCHAR,
    StudyType VARCHAR,
    ImagePath VARCHAR,
    Embedding VECTOR(DOUBLE, 1024),  -- NV-CLIP embeddings
    CreatedAt TIMESTAMP,
    UpdatedAt TIMESTAMP
)
```

**Current data:**
- 12 medical images loaded
- 10 real MIMIC-CXR chest X-ray DICOM files
- 2 test images
- All with real NV-CLIP embeddings from local NIM

## Performance Metrics

| Operation | Latency | Notes |
|-----------|---------|-------|
| Text embedding (NIM) | ~100ms | Single query |
| Image embedding (NIM) | ~200ms | Includes preprocessing |
| Vector search (IRIS) | ~50ms | Cosine similarity |
| Total semantic search | ~150ms | End-to-end |

## Testing

### Test Semantic Search
```bash
ssh -i ~/.ssh/medical-graphrag-key.pem ubuntu@3.84.250.46 \
  "cd ~/medical-graphrag && source venv/bin/activate && python test_image_search.py"
```

**Expected results:**
- Keyword search: ✓ PASS
- Semantic search: ✓ PASS (similarity ~85% for relevant queries)

### Test NIM Embeddings
```bash
ssh -i ~/.ssh/medical-graphrag-key.pem ubuntu@3.84.250.46 \
  "cd ~/medical-graphrag && source venv/bin/activate && python -c 'from src.embeddings.nvclip_embeddings import NVCLIPEmbeddings; e = NVCLIPEmbeddings(); print(e.embed_text(\"chest x-ray\")[:5])'"
```

## Adding More Images

### Upload Images
```bash
# Copy DICOM files to AWS
scp -i ~/.ssh/medical-graphrag-key.pem /path/to/images/*.dcm \
  ubuntu@3.84.250.46:~/medical-graphrag/medical_images/
```

### Load with Embeddings
```bash
ssh -i ~/.ssh/medical-graphrag-key.pem ubuntu@3.84.250.46 \
  "cd ~/medical-graphrag && source venv/bin/activate && python load_medical_images.py --limit 50"
```

## Troubleshooting

### NIM Container Not Responding
```bash
# Check logs
ssh -i ~/.ssh/medical-graphrag-key.pem ubuntu@3.84.250.46 "docker logs nim-nvclip --tail 50"

# Restart container
ssh -i ~/.ssh/medical-graphrag-key.pem ubuntu@3.84.250.46 "docker restart nim-nvclip"
```

### IRIS Connection Failed
```bash
# Check IRIS is running
ssh -i ~/.ssh/medical-graphrag-key.pem ubuntu@3.84.250.46 "docker ps | grep iris"

# Test connection
ssh -i ~/.ssh/medical-graphrag-key.pem ubuntu@3.84.250.46 \
  "cd ~/medical-graphrag && source venv/bin/activate && python -c 'from src.db.connection import get_connection; c = get_connection(); print(\"OK\")'"
```

### Streamlit Won't Start (Local)
```bash
# Kill existing SSH tunnels
pkill -f "ssh.*1972.*8002"

# Kill existing Streamlit
pkill -f "streamlit run"

# Try again
./deploy_streamlit_local.sh
```

### Streamlit Won't Start (AWS)
```bash
# Check logs
ssh -i ~/.ssh/medical-graphrag-key.pem ubuntu@3.84.250.46 "tail -50 ~/medical-graphrag/streamlit.log"

# Kill and restart
ssh -i ~/.ssh/medical-graphrag-key.pem ubuntu@3.84.250.46 "pkill -f streamlit"
./deploy_streamlit_aws.sh
```

## Cost Optimization

### AWS Instance Costs
- **g5.xlarge on-demand**: ~$1.00/hour
- **g5.xlarge spot**: ~$0.30/hour (70% savings)

### When to Use Spot Instances
- ✅ Development and testing
- ✅ Non-critical workloads
- ✅ Can tolerate interruptions
- ❌ Production with SLA requirements

### Stop Instance When Not in Use
```bash
# Stop (will lose ephemeral data, keep EBS)
aws ec2 stop-instances --instance-ids i-0432eba10b98c4949

# Start
aws ec2 start-instances --instance-ids i-0432eba10b98c4949

# Get new IP
aws ec2 describe-instances --instance-ids i-0432eba10b98c4949 \
  --query 'Reservations[0].Instances[0].PublicIpAddress'
```

## Next Steps

### 1. Load More Images
Upload and load more medical images from:
- MIMIC-CXR dataset (chest X-rays with radiology reports)
- Synthea generated synthetic patient data
- Your own medical image datasets

### 2. Improve Metadata Extraction
Enhance `load_medical_images.py` to extract:
- Patient demographics from DICOM headers
- Study descriptions and protocols
- Anatomical regions and view positions
- Clinical findings from associated reports

### 3. Add More Search Features
- Multi-modal search (text + image query)
- Filter by patient, study type, date range
- Clinical findings extraction and indexing
- Report generation from image findings

### 4. Production Hardening
- Authentication and authorization
- Rate limiting and quotas
- Monitoring and alerting (Prometheus/Grafana)
- Backup and disaster recovery
- HIPAA compliance measures

## Quick Reference

### SSH Access
```bash
ssh -i ~/.ssh/medical-graphrag-key.pem ubuntu@3.84.250.46
```

### View Logs
```bash
# NIM logs
ssh -i ~/.ssh/medical-graphrag-key.pem ubuntu@3.84.250.46 "docker logs -f nim-nvclip"

# IRIS logs
ssh -i ~/.ssh/medical-graphrag-key.pem ubuntu@3.84.250.46 "docker logs -f iris-vector-db"

# Streamlit logs (if on AWS)
ssh -i ~/.ssh/medical-graphrag-key.pem ubuntu@3.84.250.46 "tail -f ~/medical-graphrag/streamlit.log"
```

### Restart Services
```bash
# Restart NIM
ssh -i ~/.ssh/medical-graphrag-key.pem ubuntu@3.84.250.46 "docker restart nim-nvclip"

# Restart IRIS
ssh -i ~/.ssh/medical-graphrag-key.pem ubuntu@3.84.250.46 "docker restart iris-vector-db"

# Restart Streamlit
./deploy_streamlit_local.sh  # or deploy_streamlit_aws.sh
```

## Support

For issues or questions:
1. Check logs (see Quick Reference above)
2. Review troubleshooting section
3. Test individual components (NIM, IRIS, Streamlit)
4. Verify AWS instance is running and accessible

---

🎉 **System Ready!** Choose your deployment option and start using the medical image search system.
