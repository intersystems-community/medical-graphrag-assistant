# 🚀 Quick Start - Medical GraphRAG System

## ✅ System Status: DEPLOYED AND RUNNING

### Access the System

**Streamlit UI (Local):**
```
http://localhost:8501
```

Open this in your browser to use the medical image search system!

## What You Can Do

### 1. Search Medical Images
Try these queries in Streamlit:
- "Show me chest X-rays of pneumonia"
- "Find lung images"
- "Chest X-ray cardiomegaly"

### 2. Query Knowledge Graph
- "What are the most common symptoms?"
- "Show me a chart of symptom frequency"
- "Plot entity distribution"

### 3. Search Clinical Records
- "Search for chest pain cases"
- "Find patients with diabetes"

## System Architecture

```
┌──────────────────────┐
│   Your Browser       │
│  localhost:8501      │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐        SSH Tunnels
│  Streamlit (Local)   │◄─────────────────────┐
└──────────────────────┘                      │
                                              │
                                              ▼
                            ┌─────────────────────────────────┐
                            │    AWS g5.xlarge (GPU)          │
                            │                                 │
                            │  • NV-CLIP NIM (port 8002)     │
                            │  • IRIS VectorDB (port 1972)   │
                            │  • 12 medical images loaded     │
                            └─────────────────────────────────┘
```

## Current Data

- **Images Loaded**: 12 medical images
- **Source**: MIMIC-CXR chest X-rays (DICOM format)
- **Embeddings**: Real NV-CLIP 1024-dim vectors
- **Search Type**: Semantic vector search
- **Performance**: ~150ms end-to-end

## Verify Everything is Running

```bash
# Check SSH tunnels
ps aux | grep "ssh.*1972.*8002" | grep -v grep

# Check Streamlit
curl -s http://localhost:8501 | grep -q "Streamlit" && echo "✓ Running"

# Check AWS backend
python -c "from src.db.connection import get_connection; c = get_connection(); cursor = c.cursor(); cursor.execute('SELECT COUNT(*) FROM SQLUser.MedicalImageVectors'); print(f'✓ {cursor.fetchone()[0]} images available')"
```

## If Something's Not Working

### Restart SSH Tunnels
```bash
pkill -f "ssh.*1972.*8002"
ssh -i ~/.ssh/medical-graphrag-key.pem \
  -L 1972:localhost:1972 \
  -L 8002:localhost:8002 \
  -N -f \
  ubuntu@3.84.250.46
```

### Restart Streamlit
```bash
pkill -f "streamlit run"
cd mcp-server && streamlit run streamlit_app.py --server.port 8501 &
```

### Check AWS Services
```bash
ssh -i ~/.ssh/medical-graphrag-key.pem ubuntu@3.84.250.46 "docker ps"
```

## Next Steps

1. **Try the UI**: Open http://localhost:8501
2. **Search for images**: Use the example queries above
3. **Load more images**: See `upload_medical_images.sh`
4. **Read full guide**: See `DEPLOYMENT_GUIDE.md`

## Cost Management

Your AWS instance costs ~$1/hour. Stop it when not in use:
```bash
aws ec2 stop-instances --instance-ids i-0432eba10b98c4949
```

## Support

- **Full deployment guide**: `DEPLOYMENT_GUIDE.md`
- **Troubleshooting**: `DEPLOYMENT_GUIDE.md` → Troubleshooting section
- **AWS NIM details**: `/tmp/NIM_DEPLOYMENT_COMPLETE.md`

---

**You're all set!** Open http://localhost:8501 and start exploring your medical image search system. 🎉
