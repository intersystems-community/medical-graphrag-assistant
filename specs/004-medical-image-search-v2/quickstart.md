# Quickstart: Enhanced Medical Image Search

**Feature**: 004-medical-image-search-v2  
**Target Users**: Developers implementing P1 (Semantic Search with Scoring)  
**Prerequisites**: FHIR AI Hackathon Kit repository cloned, Python 3.12+

---

## Table of Contents

1. [Environment Setup](#environment-setup)
2. [Database Configuration](#database-configuration)
3. [Running Locally](#running-locally)
4. [Testing the Feature](#testing-the-feature)
5. [Example Queries](#example-queries)
6. [Troubleshooting](#troubleshooting)
7. [API Reference](#api-reference)

---

## Environment Setup

### 1. Install Dependencies

```bash
cd /Users/tdyar/ws/FHIR-AI-Hackathon-Kit

# Use Miniconda Python (verified working)
/opt/homebrew/Caskroom/miniconda/base/bin/pip install -r requirements.txt
```

**Key Dependencies** (already in `requirements.txt`):
- `intersystems-irispython` - IRIS database driver
- `openai` - NV-CLIP client
- `streamlit` - Web UI framework
- `plotly` - Visualizations
- `sentence-transformers` - Text embeddings (backup)

### 2. Set Environment Variables

Create or update `.env` file in project root:

```bash
# Development Configuration (Local IRIS)
IRIS_HOST=localhost
IRIS_PORT=32782
IRIS_NAMESPACE=DEMO
IRIS_USERNAME=_SYSTEM
IRIS_PASSWORD=ISCDEMO

# NV-CLIP Configuration (Required for Semantic Search)
NVIDIA_API_KEY=nvapi-xxxxxxxxxxxxxxxxxxxxxxxxxxxx  # Get from https://build.nvidia.com/nvidia/nvclip

# Optional: AWS Bedrock for Claude (already working per debug)
# AWS credentials via ~/.aws/credentials or AWS_PROFILE env var
```

**Load environment**:
```bash
set -a && source .env && set +a
```

### 3. Verify NV-CLIP Access

```bash
# Test NV-CLIP embedding
/opt/homebrew/Caskroom/miniconda/base/bin/python3 debug_nvclip.py
```

**Expected Output**:
```
Successfully imported NVCLIPEmbeddings
```

**If Error** (`No module named 'openai'`):
```bash
/opt/homebrew/Caskroom/miniconda/base/bin/pip install openai
```

---

## Database Configuration

### Local Development Database (Recommended)

**Option A: Use Existing Local IRIS** (if already running):
```bash
# Check if local IRIS is running
docker ps | grep iris

# If running, verify connection
/opt/homebrew/Caskroom/miniconda/base/bin/python3 -c "
import intersystems_iris.dbapi._DBAPI as iris
conn = iris.connect(hostname='localhost', port=32782, namespace='DEMO', username='_SYSTEM', password='ISCDEMO')
print('✅ Connected to local IRIS')
conn.close()
"
```

**Option B: Start Local IRIS Container**:
```bash
# Using iris-devtester (recommended per constitution.md)
cd ../iris-devtester
# Follow iris-devtester setup instructions

# OR manually with Docker
docker run -d \
  --name iris-demo \
  -p 32782:1972 \
  -p 52782:52773 \
  -e IRIS_PASSWORD=ISCDEMO \
  intersystems/iris-community:latest
```

### Production Database (AWS)

```bash
# Production configuration (.env)
IRIS_HOST=3.84.250.46
IRIS_PORT=1972
IRIS_NAMESPACE=%SYS
IRIS_USERNAME=_SYSTEM
IRIS_PASSWORD=SYS
```

**Note**: Ensure network access to AWS IRIS (may require VPN/bastion host)

### Verify Database Schema

```bash
# Check if MIMICCXRImages table exists with vectors
/opt/homebrew/Caskroom/miniconda/base/bin/python3 check_db_images.py
```

**Expected Output**:
```
Total images in VectorSearch.MIMICCXRImages: 10,234

Sample images:
- PA: ../mimic-cxr/physionet.org/files/mimic-cxr/2.1.0/files/p10/p10045779/s53819164/4b369dbe.dcm
```

**If No Images**: Run image ingestion (see [Data Ingestion](#data-ingestion) below)

---

## Running Locally

### 1. Start MCP Server (Optional - for standalone testing)

```bash
cd mcp-server
/opt/homebrew/Caskroom/miniconda/base/bin/python3 fhir_graphrag_mcp_server.py
```

**Expected Output**:
```
MCP Server started
Available tools: search_fhir_documents, search_medical_images, ...
```

### 2. Start Streamlit App

```bash
# From project root
/opt/homebrew/Caskroom/miniconda/base/bin/streamlit run mcp-server/streamlit_app.py --server.port 8502 --server.headless true
```

**Access**: Navigate to `http://localhost:8502`

**Expected UI**:
- Chat interface with "Agentic Medical Chat" title
- Sidebar showing available MCP tools (including `search_medical_images`)
- Input box for queries

---

## Testing the Feature

### Manual Testing via Streamlit UI

1. **Load Streamlit** at `http://localhost:8502`

2. **Enter Test Query** in chat input:
   ```
   Search for chest X-rays showing pneumonia
   ```

3. **Expected Behavior**:
   - Claude calls `search_medical_images` tool automatically
   - Status message: "🔧 Claude is calling tools..."
   - Results display with:
     - Image thumbnails in 3-column grid
     - **Similarity score badges** (green/yellow/gray)
     - View position labels (PA/AP/Lateral)
     - Patient identifiers

4. **Verify Scoring**:
   - Scores should be visible as badges (e.g., "Score: 0.87")
   - Colors: Green (≥0.7), Yellow (0.5-0.7), Gray (<0.5)
   - Tooltip showing confidence level on hover

### Automated Testing

```bash
# Run unit tests
pytest tests/unit/search/ -v --cov=src/search

# Run integration tests
pytest tests/integration/test_nvclip_search_integration.py -v

# Run E2E tests (requires Streamlit running)
pytest tests/e2e/test_streamlit_image_search.py -v --headed  # --headed for visible browser
```

---

## Example Queries

### Semantic Search Examples

| Query | Expected Results | Min Score |
|-------|-----------------|-----------|
| "chest X-ray showing pneumonia" | Images with infiltrates, consolidation | ≥0.6 |
| "bilateral lung infiltrates with pleural effusion" | Bilateral findings, fluid | ≥0.5 |
| "cardiomegaly" | Enlarged heart shadow | ≥0.7 |
| "normal frontal chest radiograph" | Clear lungs, normal heart size | ≥0.6 |
| "pneumothorax" | Collapsed lung, air in pleural space | ≥0.5 |

### Using via Python (Direct MCP Tool Call)

```python
import asyncio
import json
from mcp-server.fhir_graphrag_mcp_server import call_tool

# Prepare query
query_input = {
    "query": "chest X-ray showing pneumonia",
    "limit": 10,
    "min_score": 0.5
}

# Call tool
result = asyncio.run(call_tool("search_medical_images", query_input))
response = json.loads(result[0].text)

# Print results
print(f"Query: {response['query']}")
print(f"Results: {response['results_count']}")
print(f"Search Mode: {response['search_mode']}")
print(f"Avg Score: {response.get('avg_score', 'N/A')}")

for img in response['images']:
    print(f"- {img['image_id']} | Score: {img.get('similarity_score', 'N/A')} | {img['score_color']}")
```

### Expected Response Format

```json
{
  "query": "chest X-ray showing pneumonia",
  "results_count": 5,
  "total_results": 127,
  "search_mode": "semantic",
  "execution_time_ms": 1247,
  "cache_hit": true,
  "avg_score": 0.74,
  "max_score": 0.89,
  "min_score": 0.61,
  "images": [
    {
      "image_id": "4b369dbe-417168fa-7e2b5f04-00582488-c50504e7",
      "study_id": "53819164",
      "subject_id": "10045779",
      "view_position": "PA",
      "image_path": "../mimic-cxr/.../4b369dbe.dcm",
      "similarity_score": 0.89,
      "score_color": "green",
      "confidence_level": "strong",
      "description": "Chest X-ray (PA) for patient 10045779",
      "embedding_model": "nvidia/nvclip"
    }
  ]
}
```

---

## Troubleshooting

### Issue: "AWS Bedrock not available"

**Symptom**: Warning banner in Streamlit UI

**Cause**: AWS credentials not configured (this is OK - Bedrock is for Claude, not image search)

**Solution**: Image search works independently. Claude synthesis is optional for this feature.

---

### Issue: "Could not import NVCLIPEmbeddings"

**Symptom**: Warning in Streamlit logs: `Warning: Could not import NVCLIPEmbeddings`

**Root Cause**: Missing `openai` package

**Solution**:
```bash
/opt/homebrew/Caskroom/miniconda/base/bin/pip install openai
```

**Verify**:
```bash
/opt/homebrew/Caskroom/miniconda/base/bin/python3 debug_nvclip.py
# Should print: "Successfully imported NVCLIPEmbeddings"
```

---

### Issue: Database Connection Timeout

**Symptom**: `check_db_images.py` times out or errors

**Possible Causes**:
1. **Wrong Python interpreter** (using system Python instead of Miniconda)
2. **Local IRIS not running**
3. **Wrong DATABASE config** (pointing to AWS but VPN not connected)
4. **Firewall blocking port 32782** or **1972**

**Solutions**:

**Check 1: Verify Python**
```bash
which python3  # Should be /opt/homebrew/Caskroom/miniconda/base/bin/python3
```

**Check 2: Verify IRIS Running**
```bash
docker ps | grep iris
# OR
psport 32782  # Should show IRIS process
```

**Check 3: Test Connection**
```bash
nc -zv localhost 32782  # Should connect
# OR
nc -zv 3.84.250.46 1972  # If using AWS
```

**Check 4: Verify .env Loaded**
```bash
echo $IRIS_HOST  # Should print "localhost" or "3.84.250.46"
```

---

### Issue: "No images found matching your query"

**Symptom**: Search returns 0 results

**Possible Causes**:
1. **Database empty** (no images vectorized yet)
2. **Query too specific** (no matches above min_score threshold)
3. **NV-CLIP service down**

**Solutions**:

**Check 1: Verify Data Exists**
```bash
python3 check_db_images.py
# Should show count > 0
```

**Check 2: Lower min_score**
```python
query_input = {
    "query": "chest X-ray",
    "limit": 10,
    "min_score": 0.0  # Remove threshold
}
```

**Check 3: Try Broader Query**
```
"chest X-ray"  # Instead of "chest X-ray showing rare disease"
```

---

### Issue: Fallback to Keyword Search

**Symptom**: Response has `"search_mode": "keyword"` and warning banner

**Cause**: NV-CLIP unavailable (expected if `NVIDIA_API_KEY` not set)

**Solution**: Set API key in `.env`:
```bash
NVIDIA_API_KEY=nvapi-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Get key from: https://build.nvidia.com/nvidia/nvclip (free tier available)

**Note**: Keyword search is intentional fallback - feature still works, just less accurate

---

### Issue: Image Files Not Found

**Symptom**: Streamlit shows "Image not available" placeholders

**Cause**: `ImagePath` in database points to non-existent files

**Check**:
```bash
# Verify mimic-cxr directory exists
ls -la ../mimic-cxr/physionet.org/files/mimic-cxr/2.1.0/files/
```

**Solution**:
1. **If missing**: Download MIMIC-CXR dataset (requires PhysioNet credentialed access)
2. **If exists**: Verify paths in database match actual file locations

---

## Data Ingestion

If database is empty, ingest MIMIC-CXR images:

```bash
# Ingest 10 images (test)
/opt/homebrew/Caskroom/miniconda/base/bin/python3 ingest_mimic_cxr_images.py 10

# Ingest all images (takes hours, requires NVIDIA_API_KEY)
/opt/homebrew/Caskroom/miniconda/base/bin/python3 ingest_mimic_cxr_images.py 0
```

**Expected Output**:
```
MIMIC-CXR Image Ingestion with NV-CLIP
========================================
Found 377,110 DICOM files
Processing 10 images...
[1/10] Processing: 4b369dbe...
  ✅ Inserted (1024-dim vector)
...
Ingestion Complete!
Processed: 10
Time: 2.3 minutes
Rate: 0.07 images/sec
```

---

## API Reference

### MCP Tool: `search_medical_images`

**Input** (see `contracts/search-request.json`):
```python
{
    "query": str,              # Required: natural language query
    "limit": int,              # Optional: max results (default 5, max 100)
    "min_score": float,        # Optional: threshold 0.0-1.0 (default 0.0)
    "view_positions": [str],   # Optional: filter by view (P2 feature)
    "patient_id_pattern": str, # Optional: SQL LIKE pattern (P2 feature)
    "page": int,               # Optional: pagination (default 1)
    "page_size": int           # Optional: results per page (default 50)
}
```

**Output** (see `contracts/search-response.json`):
```python
{
    "query": str,
    "results_count": int,
    "total_results": int,
    "search_mode": "semantic"|"keyword"|"hybrid",
    "execution_time_ms": int,
    "cache_hit": bool,
    "avg_score": float | null,
    "max_score": float | null,
    "min_score": float | null,
    "fallback_reason": str | null,
    "images": [
        {
            "image_id": str,
            "study_id": str,
            "subject_id": str,
            "view_position": str | null,
            "image_path": str,
            "similarity_score": float | null,
            "score_color": "green"|"yellow"|"gray",
            "confidence_level": "strong"|"moderate"|"weak",
            "description": str,
            "embedding_model": str
        }
    ]
}
```

---

## Performance Benchmarks

**Target Latencies** (from research.md):

| Metric | Target | Actual (Expected) |
|--------|--------|-------------------|
| Search (cold cache) | <10s p95 | 1-3s typical |
| Search (warm cache) | <1s p95 | 100-300ms typical |
| NV-CLIP embed_text() | <2s | 500-1500ms |
| IRIS VECTOR_COSINE() | <200ms | 50-150ms |

**Cache Statistics**:
```python
from src.search.cache import EmbeddingCache
print(EmbeddingCache.cache_info())
# CacheInfo(hits=342, misses=158, maxsize=1000, currsize=158)
# Hit rate: 68.4%
```

---

## Next Steps

After verifying local setup:

1. **Run Task T001-T005** (Setup phase from tasks.md)
2. **Implement T006-T009** (Foundational database config)
3. **Write Tests** (T010-T013 - TDD approach)
4. **Implement Backend** (T014-T018 - scoring + MCP server)
5. **Implement Frontend** (T019-T021 - Streamlit UI)

**Reference**: See `specs/004-medical-image-search-v2/tasks.md` for complete task breakdown

---

## Support

- **Spec**: `/specs/004-medical-image-search-v2/spec.md`
- **Plan**: `/specs/004-medical-image-search-v2/plan.md`
- **Research**: `/specs/004-medical-image-search-v2/research.md`
- **Tasks**: `/specs/004-medical-image-search-v2/tasks.md`
- **GitHub Issues**: (link to issue tracker if available)

---

**Version**: 1.0  
**Last Updated**: 2025-11-21  
**Validated On**: macOS, Python 3.12, Miniconda
