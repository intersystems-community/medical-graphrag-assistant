# Image Vectorization Plan
## MIMIC-CXR Chest X-Ray Embeddings

### Current Status
- **Text Reports**: 149,400/227,835 vectorized with OpenAI ✅
- **Images**: 764 DICOM files downloaded (12 GB/~450 GB)
- **Image Embeddings**: Ready to start with NVIDIA NV-CLIP

---

## Architecture Decision

### ❌ Option 1: OpenAI Vision
OpenAI has vision in ChatGPT but **no embedding API for images**
- Only text embeddings available (text-embedding-3-large)

### ❌ Option 2: BiomedCLIP
Attempted but **model files not available** on HuggingFace
- Model: `microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224`
- Error: `OSError: does not appear to have a file named pytorch_model.bin...`
- Status: Model repository incomplete/unavailable

### ✅ Option 3: NVIDIA NV-CLIP (SELECTED)
**Simple drop-in replacement for BiomedCLIP**

**Key Features**:
- **Multimodal**: Both image and text embeddings
- **Dimension**: 1024 (ViT-H variant)
- **API Access**: NVIDIA NIM cloud API
- **Training**: 700M proprietary images
- **Cross-Modal**: Text queries can find images and vice versa

**Pros**:
- ✅ Available immediately (no model download)
- ✅ Multimodal (text + image in same embedding space)
- ✅ Simple API (similar to OpenAI)
- ✅ No GPU required locally
- ✅ Drop-in replacement architecture

**Cons**:
- ⚠️ API costs (paid service)
- ⚠️ Not medical-specific (general-purpose CLIP)
- ⚠️ Requires NVIDIA API key

**Alternative**: NV-DINOv2 (1024/1536-dim, image-only, no text cross-modal)

---

## Implementation Plan (NV-CLIP)

### 1. Get NVIDIA API Key
```bash
# Visit: https://build.nvidia.com/nvidia/nv-clip
# Sign up / log in
# Generate API key
# Add to .env:
echo 'NVIDIA_API_KEY=nvapi-xxxx...' >> .env
```

### 2. NV-CLIP Setup (Already Complete ✅)
```python
from src.embeddings.nvclip_embeddings import NVCLIPEmbeddings

# Initialize (loads from NVIDIA_API_KEY env var)
embedder = NVCLIPEmbeddings()

# Embed image (supports DICOM, PIL Image, numpy array, file path)
image_embedding = embedder.embed_image("path/to/image.dcm")  # 1024-dim

# Embed text query (for cross-modal search)
text_embedding = embedder.embed_text("pneumonia chest infiltrate")  # 1024-dim

# Calculate similarity
similarity = embedder.similarity(image_embedding, text_embedding)
```

### 3. DICOM to Embedding Pipeline
```python
# Already integrated in nvclip_embeddings.py
import pydicom
from PIL import Image

# NV-CLIP handles DICOM automatically:
embedding = embedder.embed_image("scan.dcm")

# Behind the scenes:
# 1. Reads DICOM with pydicom
# 2. Normalizes pixel values (16-bit → 8-bit)
# 3. Converts to RGB PIL Image
# 4. Resizes to NV-CLIP range (224-518px)
# 5. Calls NVIDIA API
# 6. Returns 1024-dim vector
```

### 4. Database Schema
```sql
CREATE TABLE VectorSearch.MIMICCXRImages (
    SubjectID VARCHAR(50) NOT NULL,
    StudyID VARCHAR(50) NOT NULL,
    ImageID VARCHAR(50) NOT NULL,
    ImagePath VARCHAR(500),
    DicomFile VARCHAR(255),
    ViewPosition VARCHAR(20),  -- PA, AP, LATERAL
    Vector VECTOR(DOUBLE, 1024),  -- NV-CLIP: 1024-dim (was 512)
    EmbeddingModel VARCHAR(100),
    Provider VARCHAR(50),  -- 'nvclip'
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ImageID, Provider),
    FOREIGN KEY (StudyID) REFERENCES VectorSearch.MIMICCXRReports(StudyID)
)
```

### 4. Cross-Modal Search Capabilities

**Text → Image Search**:
```python
# Query: "pneumonia chest infiltrate"
text_embedding = embed_text_query(query)  # OpenAI 3072-dim

# Search reports first (same embedding space)
matching_reports = vector_search(text_embedding, VectorSearch.MIMICCXRReports)

# Find images for matching studies
images = get_images_for_studies(matching_reports.study_ids)
```

**Image → Text Search**:
```python
# Upload chest X-ray image
image_embedding = embed_image(uploaded_xray)  # BiomedCLIP 512-dim

# Find similar images
similar_images = vector_search(image_embedding, VectorSearch.MIMICCXRImages)

# Get associated radiology reports
reports = get_reports_for_studies(similar_images.study_ids)
```

**Multimodal Fusion** (Future):
- Combine text and image embeddings
- Joint embedding space training
- GraphRAG integration

---

## Performance Estimates

### With CPU (M1/M2 Mac)
- DICOM read: 0.05s
- Image preprocessing: 0.02s
- Embedding generation: 1-2s
- Database insert: 0.01s
- **Total: ~2s per image**
- **377K images: ~210 hours (9 days)**

### With GPU (NVIDIA)
- Embedding generation: 0.05-0.1s
- **Total: ~0.2s per image**
- **377K images: ~21 hours**

### Batch Processing
- Process 32 images/batch
- GPU: ~0.01s per image (batch)
- **377K images: ~1-2 hours with batching**

---

## Cost Analysis

### BiomedCLIP (Local)
- Model download: Free (1.5 GB)
- Inference: Free (runs locally)
- Storage: IRIS database (existing infrastructure)
- **Total: $0**

### vs NVIDIA NIM (Cloud)
- EC2 g5.xlarge: $1.006/hour
- 2 hours batched processing: ~$2
- Plus AWS setup overhead
- **BiomedCLIP saves $2 + setup time**

---

## Dependencies

```bash
pip install transformers torch torchvision pydicom pillow
```

### Model Download Size
- BiomedCLIP: ~1.5 GB
- PyTorch: ~2 GB (if not installed)

---

## Next Steps

### Immediate (Ready Now!)
1. ✅ Install dependencies (pydicom, PIL, requests)
2. ✅ Create NV-CLIP wrapper (`src/embeddings/nvclip_embeddings.py`)
3. ✅ Update embeddings factory to support NV-CLIP
4. ✅ Create test script (`test_nvclip.py`)
5. ⏳ **Get NVIDIA API key** from https://build.nvidia.com/nvidia/nv-clip
6. ⏳ **Test with sample DICOM**: `python3 test_nvclip.py`
7. ⏳ Create image vectorization script (764 DICOMs available)

### Short Term (Once API Key Set)
1. Test NV-CLIP with 10 sample DICOMs
2. Create VectorSearch.MIMICCXRImages table (1024-dim)
3. Vectorize 764 available DICOM files
4. Test cross-modal search (text → find X-rays)
5. Performance benchmarking

### Medium Term (As Download Continues)
1. Process images in batches as they download
2. Build cross-modal search demo
3. Integrate with existing 149,400 radiology reports
4. Clinical search interface prototype

### Long Term
1. Full dataset vectorization (377K images)
2. GraphRAG medical knowledge graph integration
3. Multi-hop reasoning (reports + images + entities)
4. Clinical decision support UI

---

## Files Created

**Core Scripts** ✅:
- `src/embeddings/nvclip_embeddings.py` - NV-CLIP wrapper (DONE)
- `test_nvclip.py` - Test script with sample DICOM (DONE)
- `src/embeddings/embeddings_factory.py` - Updated with NV-CLIP support (DONE)

**To Create** ⏳:
- `ingest_mimic_cxr_images.py` - DICOM to vector pipeline (batch processing)
- `create_image_table.py` - Create VectorSearch.MIMICCXRImages schema
- `test_cross_modal_search.py` - Text→Image and Image→Text demos

**Utils**:
- `src/utils/dicom_utils.py` - DICOM processing helpers (optional, functionality already in NV-CLIP wrapper)

---

**Last Updated**: 2025-11-07
**Status**: NV-CLIP wrapper complete, awaiting NVIDIA API key for testing
**Selected Path**: NVIDIA NV-CLIP (cloud API, multimodal, 1024-dim)
**Available Images**: 764 DICOM files (12 GB downloaded so far)
