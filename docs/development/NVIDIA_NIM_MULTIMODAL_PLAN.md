# NVIDIA NIM Multimodal Integration Plan

## Executive Summary

This document outlines the plan for integrating NVIDIA NIM (NVIDIA Inference Microservices) into the FHIR GraphRAG system to enable **true multimodal medical search** combining:

1. **Text data** from clinical notes (DocumentReference resources)
2. **Medical images** from chest X-rays, CT scans, MRIs (ImagingStudy/Media resources)
3. **Knowledge graph entities** from existing GraphRAG implementation

## Current State Analysis

### Existing System
- ✅ 51 DocumentReference resources with clinical notes
- ✅ GraphRAG knowledge graph (171 entities, 10 relationships)
- ✅ Multi-modal search (Vector + Text + Graph) using SentenceTransformer
- ✅ Integration tests passing (13/13)
- ❌ **No medical imaging data** (0 ImagingStudy, 0 Media resources)
- ❌ **Small dataset** (2,739 resources total)

### Limitations
1. **Text-only embeddings**: Current SentenceTransformer (384-dim) only processes clinical notes
2. **No image processing**: Cannot search radiology images, CT scans, X-rays, pathology slides
3. **Limited scalability testing**: Only 51 documents, need 10K+ for benchmarking
4. **Generic embeddings**: Not optimized for medical domain

## Multimodal Architecture Vision

### What "Multimodal" Means in This Context

**NOT**: Using multimodal LLMs that process both text and images together

**YES**:
- Different FHIR data types (text vs images vs structured data)
- Different embedding models for each modality
- Filters to detect data type
- Fusion strategy to merge cross-modal results at query time

### Target Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      FHIR Repository                            │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐│
│  │ DocumentReference│  │ ImagingStudy     │  │ DiagnosticRpt ││
│  │ (Clinical Notes) │  │ (X-rays, CT, MRI)│  │ (Lab Results) ││
│  └────────┬─────────┘  └────────┬─────────┘  └───────┬───────┘│
└───────────┼─────────────────────┼─────────────────────┼────────┘
            │                     │                     │
            ▼                     ▼                     │
   ┌────────────────┐    ┌────────────────┐           │
   │  MODALITY      │    │  MODALITY      │           │
   │  DETECTION     │    │  DETECTION     │           │
   │  (Text)        │    │  (Image)       │           │
   └────────┬───────┘    └────────┬───────┘           │
            │                     │                     │
            ▼                     ▼                     │
   ┌────────────────┐    ┌────────────────┐           │
   │ NIM TEXT       │    │ NIM VISION     │           │
   │ EMBEDDINGS     │    │ EMBEDDINGS     │           │
   │ NV-EmbedQA-E5  │    │ Nemotron Nano  │           │
   │ (1024-dim)     │    │ VL (TBD-dim)   │           │
   └────────┬───────┘    └────────┬───────┘           │
            │                     │                     │
            ▼                     ▼                     ▼
   ┌────────────────┐    ┌────────────────┐    ┌─────────────┐
   │ VectorSearch.  │    │ VectorSearch.  │    │ RAG.        │
   │ FHIRText       │    │ FHIRImage      │    │ Entities    │
   │ Vectors        │    │ Vectors        │    │ (Graph KG)  │
   └────────┬───────┘    └────────┬───────┘    └──────┬──────┘
            │                     │                     │
            └─────────────┬───────┴─────────────────────┘
                          │
                          ▼
                 ┌────────────────────┐
                 │  CROSS-MODAL       │
                 │  QUERY FUSION      │
                 │  RRF(text, image,  │
                 │      graph)        │
                 └────────────────────┘
```

## Phase 1: Large-Scale Test Dataset Generation

### Objective
Generate a realistic, nontrivially large FHIR dataset for scalability testing

### Dataset Components

#### 1. Synthetic Patient Data (Synthea)
- **Tool**: Synthea synthetic patient generator
- **Scale**: 10,000 patients (recommended starting point)
- **Format**: FHIR R4 (NDJSON)
- **Content**:
  - Patient demographics
  - Conditions (diabetes, hypertension, etc.)
  - Medications
  - Procedures
  - Laboratory results
  - Vital signs
  - Immunizations
- **Estimated size**: 2-10 GB
- **Source**: Download pre-generated 1M dataset and subset, OR generate custom

#### 2. Medical Imaging Data (MIMIC-CXR)
- **Tool**: MIMIC-CXR chest X-ray dataset
- **Scale**: 500-2,000 radiographic studies
- **Format**: DICOM + Radiology reports (text)
- **Content**:
  - Chest X-rays (frontal, lateral views)
  - Radiology reports (free-text interpretations)
  - Study metadata (patient ID, study date, modality)
- **Estimated size**: 5-50 GB
- **Source**: PhysioNet (requires credentialed access)

#### 3. Integration Strategy
- Create ImagingStudy FHIR resources for each DICOM study
- Link ImagingStudy to synthetic Synthea patients via subject reference
- Create DocumentReference for radiology reports
- Maintain temporal coherence (imaging dates align with patient timeline)

### Implementation Steps

**Step 1.1: Install Synthea**
```bash
git clone https://github.com/synthetichealth/synthea.git
cd synthea
./gradlew build check test
```

**Step 1.2: Generate 10K Patients**
```bash
# Option A: Download pre-generated dataset
wget https://synthea.mitre.org/downloads/synthea_sample_data_fhir_latest.zip
unzip synthea_sample_data_fhir_latest.zip

# Option B: Generate custom
./run_synthea -p 10000 Massachusetts Boston
```

**Step 1.3: Access MIMIC-CXR**
```bash
# Requires PhysioNet credentialed access
# 1. Create account at https://physionet.org
# 2. Complete CITI training
# 3. Sign data use agreement
# 4. Download MIMIC-CXR-JPG (227GB) or DICOM (480GB)
```

**Step 1.4: Create FHIR ImagingStudy Resources**
```python
# Python script to convert MIMIC-CXR to FHIR ImagingStudy
# Map each DICOM study to ImagingStudy resource
# Link to synthetic patient via subject reference
# Store in IRIS FHIR repository
```

**Step 1.5: Load into IRIS**
```bash
# Use FHIR Bulk Data import
# Or direct SQL insertion
# Verify counts: 10K patients, 500+ ImagingStudy
```

### Expected Outcome
- 10,000+ Patient resources
- 500-2,000 ImagingStudy resources (with actual DICOM images)
- 500-2,000 DocumentReference resources (radiology reports)
- 20,000+ total FHIR resources (conditions, medications, procedures, etc.)
- Total dataset size: 30-150 GB

## Phase 2: Multimodal Architecture Design

### Vector Table Schema

#### Text Vectors Table
```sql
CREATE TABLE VectorSearch.FHIRTextVectors (
    VectorID BIGINT PRIMARY KEY AUTO_INCREMENT,
    ResourceID BIGINT NOT NULL,
    ResourceType VARCHAR(50) NOT NULL,  -- 'DocumentReference'
    TextContent VARCHAR(MAX),  -- Decoded clinical note
    Vector VECTOR(DOUBLE, 1024),  -- NIM NV-EmbedQA-E5-v5
    EmbeddingModel VARCHAR(100) DEFAULT 'nvidia/nv-embedqa-e5-v5',
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ResourceID) REFERENCES HSFHIR_X0001_R.Rsrc(ID)
);

CREATE INDEX idx_text_resource ON VectorSearch.FHIRTextVectors(ResourceID);
CREATE INDEX idx_text_type ON VectorSearch.FHIRTextVectors(ResourceType);
```

#### Image Vectors Table
```sql
CREATE TABLE VectorSearch.FHIRImageVectors (
    VectorID BIGINT PRIMARY KEY AUTO_INCREMENT,
    ResourceID BIGINT NOT NULL,
    ResourceType VARCHAR(50) NOT NULL,  -- 'ImagingStudy', 'Media'
    ImagePath VARCHAR(500),  -- Path to DICOM/JPEG file
    ImageMetadata VARCHAR(MAX),  -- JSON: modality, body site, etc.
    Vector VECTOR(DOUBLE, ???),  -- NIM Nemotron Nano VL (dimension TBD)
    EmbeddingModel VARCHAR(100) DEFAULT 'nvidia/nemotron-nano-vl-12b',
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ResourceID) REFERENCES HSFHIR_X0001_R.Rsrc(ID)
);

CREATE INDEX idx_image_resource ON VectorSearch.FHIRImageVectors(ResourceID);
CREATE INDEX idx_image_type ON VectorSearch.FHIRImageVectors(ResourceType);
```

### Modality Detection Layer

```python
class FHIRModalityDetector:
    """Detect modality type for FHIR resources."""

    def detect_modality(self, resource_type: str, resource_data: dict) -> str:
        """
        Detect modality type based on FHIR resource.

        Returns: 'text', 'image', 'structured', or 'unknown'
        """
        if resource_type == 'DocumentReference':
            # Check if it has clinical note attachment
            if 'content' in resource_data:
                content = resource_data['content'][0]
                if 'attachment' in content:
                    attachment = content['attachment']
                    content_type = attachment.get('contentType', '')

                    # Text document
                    if content_type in ['text/plain', 'text/html']:
                        return 'text'
                    # Image attachment
                    elif content_type.startswith('image/'):
                        return 'image'
                    # Hex-encoded clinical note
                    elif 'data' in attachment:
                        return 'text'
            return 'text'  # Default for DocumentReference

        elif resource_type in ['ImagingStudy', 'Media']:
            return 'image'

        elif resource_type in ['Observation', 'DiagnosticReport']:
            return 'structured'

        else:
            return 'unknown'
```

### Cross-Modal Fusion Strategy

Extend current RRF fusion to handle three modalities:

```python
def multimodal_rrf_fusion(
    text_results: List[dict],
    image_results: List[dict],
    graph_results: List[dict],
    top_k: int = 10,
    k_constant: int = 60
) -> List[dict]:
    """
    Reciprocal Rank Fusion across text, image, and graph modalities.

    RRF formula: score = sum(1 / (k + rank_i)) across all modalities

    Args:
        text_results: Results from NIM text embedding search
        image_results: Results from NIM vision embedding search
        graph_results: Results from knowledge graph entity search
        top_k: Number of final results to return
        k_constant: RRF constant (default 60)

    Returns:
        Fused results ranked by combined RRF score
    """
    # Build lookup: resource_id -> {text_score, image_score, graph_score}
    resource_scores = {}

    # Text modality scores
    for rank, result in enumerate(text_results, start=1):
        rid = result['resource_id']
        if rid not in resource_scores:
            resource_scores[rid] = {
                'resource_id': rid,
                'text_score': 0.0,
                'image_score': 0.0,
                'graph_score': 0.0,
                'resource_data': result.get('resource_data', {})
            }
        resource_scores[rid]['text_score'] = 1.0 / (k_constant + rank)

    # Image modality scores
    for rank, result in enumerate(image_results, start=1):
        rid = result['resource_id']
        if rid not in resource_scores:
            resource_scores[rid] = {
                'resource_id': rid,
                'text_score': 0.0,
                'image_score': 0.0,
                'graph_score': 0.0,
                'resource_data': result.get('resource_data', {})
            }
        resource_scores[rid]['image_score'] = 1.0 / (k_constant + rank)

    # Graph modality scores
    for rank, result in enumerate(graph_results, start=1):
        rid = result['resource_id']
        if rid not in resource_scores:
            resource_scores[rid] = {
                'resource_id': rid,
                'text_score': 0.0,
                'image_score': 0.0,
                'graph_score': 0.0,
                'resource_data': result.get('resource_data', {})
            }
        resource_scores[rid]['graph_score'] = 1.0 / (k_constant + rank)

    # Calculate RRF score
    for rid in resource_scores:
        resource_scores[rid]['rrf_score'] = (
            resource_scores[rid]['text_score'] +
            resource_scores[rid]['image_score'] +
            resource_scores[rid]['graph_score']
        )

    # Sort by RRF score
    fused = sorted(
        resource_scores.values(),
        key=lambda x: x['rrf_score'],
        reverse=True
    )

    return fused[:top_k]
```

## Phase 3: NIM Text Embeddings Integration

### Objective
Replace SentenceTransformer with NVIDIA NIM text embeddings for improved medical domain accuracy

### NIM Text Embedding Models

**Option 1: NV-EmbedQA-E5-v5** (Recommended)
- Dimensions: 1024
- Optimized for: Question-answering, retrieval
- Best for: Clinical note search, symptom queries
- API endpoint: `nvidia/nv-embedqa-e5-v5`

**Option 2: NV-EmbedQA-Mistral7B-v2**
- Dimensions: 4096
- Parameters: 7B
- Optimized for: Complex medical domains, long documents
- Best for: Radiology reports, discharge summaries
- API endpoint: `nvidia/nv-embedqa-mistral-7b-v2`

### Implementation

**Step 3.1: Set Up NVIDIA API Key**
```bash
# Get API key from https://build.nvidia.com/
export NVIDIA_API_KEY="nvapi-..."

# Test access
curl https://integrate.api.nvidia.com/v1/embeddings \
  -H "Authorization: Bearer $NVIDIA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "What are the symptoms of hypertension?",
    "model": "nvidia/nv-embedqa-e5-v5"
  }'
```

**Step 3.2: Install LangChain NVIDIA Integration**
```bash
pip install langchain-nvidia-ai-endpoints
```

**Step 3.3: Create NIM Text Embedding Module**
```python
# src/embeddings/nim_text_embeddings.py

from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
import os

class NIMTextEmbeddings:
    """NVIDIA NIM text embeddings for medical search."""

    def __init__(self, model: str = "nvidia/nv-embedqa-e5-v5"):
        """
        Initialize NIM text embeddings.

        Args:
            model: NIM embedding model ID
        """
        api_key = os.environ.get('NVIDIA_API_KEY')
        if not api_key:
            raise ValueError("NVIDIA_API_KEY environment variable not set")

        self.embeddings = NVIDIAEmbeddings(model=model)
        self.model_name = model
        self.dimension = 1024 if "e5-v5" in model else 4096

    def embed_query(self, text: str) -> list:
        """Embed a single query."""
        return self.embeddings.embed_query(text)

    def embed_documents(self, texts: list) -> list:
        """Embed multiple documents."""
        return self.embeddings.embed_documents(texts)
```

**Step 3.4: Re-vectorize Existing DocumentReferences**
```python
# src/setup/nim_text_vectorize.py

import iris
from src.embeddings.nim_text_embeddings import NIMTextEmbeddings
import json

def vectorize_documents():
    """Vectorize all DocumentReference resources with NIM embeddings."""

    # Connect to IRIS
    conn = iris.connect('localhost', 32782, 'DEMO', '_SYSTEM', 'ISCDEMO')
    cursor = conn.cursor()

    # Initialize NIM embeddings
    embedder = NIMTextEmbeddings(model="nvidia/nv-embedqa-e5-v5")

    # Get all DocumentReference resources
    cursor.execute("""
        SELECT ID, ResourceString
        FROM HSFHIR_X0001_R.Rsrc
        WHERE ResourceType = 'DocumentReference'
        AND (Deleted = 0 OR Deleted IS NULL)
    """)

    documents = cursor.fetchall()
    print(f"Found {len(documents)} DocumentReference resources")

    for resource_id, resource_string in documents:
        # Parse FHIR JSON
        fhir_data = json.loads(resource_string)

        # Decode clinical note
        try:
            hex_data = fhir_data['content'][0]['attachment']['data']
            clinical_note = bytes.fromhex(hex_data).decode('utf-8', errors='replace')
        except:
            print(f"  Skipping resource {resource_id}: No clinical note")
            continue

        # Generate embedding
        print(f"  Vectorizing resource {resource_id}...")
        vector = embedder.embed_query(clinical_note)

        # Insert into FHIRTextVectors table
        cursor.execute("""
            INSERT INTO VectorSearch.FHIRTextVectors
            (ResourceID, ResourceType, TextContent, Vector, EmbeddingModel)
            VALUES (?, ?, ?, TO_VECTOR(?), ?)
        """, (resource_id, 'DocumentReference', clinical_note, str(vector), embedder.model_name))

    conn.commit()
    cursor.close()
    conn.close()

    print(f"✅ Vectorized {len(documents)} documents")

if __name__ == '__main__':
    vectorize_documents()
```

**Step 3.5: Test Query Performance**
```python
# Compare 1024-dim NIM vs 384-dim SentenceTransformer
# Expected: Better medical domain accuracy with NIM
```

## Phase 4: NIM Vision Embeddings Integration

### Objective
Add medical image embedding capability using NVIDIA NIM vision models

### NIM Vision Models

**Option 1: Nemotron Nano 12B v2 VL** (Recommended)
- Parameters: 12B
- Capabilities: Multi-image understanding, OCR, medical document processing
- Best for: Chest X-rays, CT scans, radiology images
- API endpoint: TBD (check NVIDIA NIM catalog)

**Option 2: Llama 3.2 Vision**
- Parameters: 11B or 90B
- Capabilities: Image reasoning, OCR, document analysis
- Best for: Complex medical imaging, multi-frame sequences
- API endpoint: TBD

### Implementation

**Step 4.1: DICOM Image Extraction**
```python
# src/imaging/dicom_extractor.py

import pydicom
from PIL import Image
import numpy as np

class DICOMExtractor:
    """Extract images from DICOM files."""

    def extract_frame(self, dicom_path: str, frame_idx: int = 0) -> Image:
        """
        Extract a frame from DICOM file as PIL Image.

        Args:
            dicom_path: Path to DICOM file
            frame_idx: Frame index (0 for single-frame)

        Returns:
            PIL Image
        """
        ds = pydicom.dcmread(dicom_path)
        pixel_array = ds.pixel_array

        # Multi-frame DICOM
        if len(pixel_array.shape) == 3:
            pixel_array = pixel_array[frame_idx]

        # Normalize to 0-255
        pixel_array = ((pixel_array - pixel_array.min()) /
                       (pixel_array.max() - pixel_array.min()) * 255).astype(np.uint8)

        # Convert to PIL Image
        return Image.fromarray(pixel_array)
```

**Step 4.2: NIM Vision Embedding Module**
```python
# src/embeddings/nim_vision_embeddings.py

from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings  # Or appropriate vision API
import os
from PIL import Image

class NIMVisionEmbeddings:
    """NVIDIA NIM vision embeddings for medical images."""

    def __init__(self, model: str = "nvidia/nemotron-nano-vl-12b"):
        """
        Initialize NIM vision embeddings.

        Args:
            model: NIM vision model ID
        """
        api_key = os.environ.get('NVIDIA_API_KEY')
        if not api_key:
            raise ValueError("NVIDIA_API_KEY environment variable not set")

        self.model_name = model
        # Initialize vision API client (TBD based on NIM documentation)
        # self.client = ...

    def embed_image(self, image: Image.Image) -> list:
        """
        Embed a single image.

        Args:
            image: PIL Image

        Returns:
            Embedding vector (list of floats)
        """
        # TODO: Implement based on NIM vision API
        pass

    def embed_images(self, images: list) -> list:
        """Embed multiple images."""
        return [self.embed_image(img) for img in images]
```

**Step 4.3: Vectorize Medical Images**
```python
# src/setup/nim_image_vectorize.py

import iris
from src.imaging.dicom_extractor import DICOMExtractor
from src.embeddings.nim_vision_embeddings import NIMVisionEmbeddings
import json

def vectorize_images():
    """Vectorize all ImagingStudy/Media resources with NIM vision embeddings."""

    conn = iris.connect('localhost', 32782, 'DEMO', '_SYSTEM', 'ISCDEMO')
    cursor = conn.cursor()

    embedder = NIMVisionEmbeddings(model="nvidia/nemotron-nano-vl-12b")
    dicom_extractor = DICOMExtractor()

    # Get all ImagingStudy resources
    cursor.execute("""
        SELECT ID, ResourceString
        FROM HSFHIR_X0001_R.Rsrc
        WHERE ResourceType = 'ImagingStudy'
        AND (Deleted = 0 OR Deleted IS NULL)
    """)

    studies = cursor.fetchall()
    print(f"Found {len(studies)} ImagingStudy resources")

    for resource_id, resource_string in studies:
        fhir_data = json.loads(resource_string)

        # Extract image path from FHIR resource
        # (Implementation depends on how images are stored)
        image_path = extract_image_path(fhir_data)

        # Extract image from DICOM
        image = dicom_extractor.extract_frame(image_path)

        # Generate embedding
        print(f"  Vectorizing image {resource_id}...")
        vector = embedder.embed_image(image)

        # Insert into FHIRImageVectors table
        cursor.execute("""
            INSERT INTO VectorSearch.FHIRImageVectors
            (ResourceID, ResourceType, ImagePath, Vector, EmbeddingModel)
            VALUES (?, ?, ?, TO_VECTOR(?), ?)
        """, (resource_id, 'ImagingStudy', image_path, str(vector), embedder.model_name))

    conn.commit()
    cursor.close()
    conn.close()

    print(f"✅ Vectorized {len(studies)} images")
```

## Phase 5: Cross-Modal Query Implementation

### Multimodal Query Interface

```python
# src/query/fhir_multimodal_query.py

from src.embeddings.nim_text_embeddings import NIMTextEmbeddings
from src.embeddings.nim_vision_embeddings import NIMVisionEmbeddings
import iris

class FHIRMultimodalQuery:
    """Multimodal FHIR query combining text, images, and knowledge graph."""

    def __init__(self):
        self.text_embedder = NIMTextEmbeddings()
        self.image_embedder = NIMVisionEmbeddings()
        self.conn = iris.connect('localhost', 32782, 'DEMO', '_SYSTEM', 'ISCDEMO')
        self.cursor = self.conn.cursor()

    def query(self, text_query: str, image_query: Image = None, top_k: int = 10):
        """
        Multimodal query combining text and optional image.

        Args:
            text_query: Natural language query
            image_query: Optional query image (PIL Image)
            top_k: Number of results

        Returns:
            Fused results from all modalities
        """
        # Text search
        text_results = self.text_search(text_query, top_k=30)

        # Image search (if image provided)
        image_results = []
        if image_query:
            image_results = self.image_search(image_query, top_k=30)

        # Graph search
        graph_results = self.graph_search(text_query, top_k=10)

        # RRF fusion
        fused = self.rrf_fusion(text_results, image_results, graph_results, top_k)

        return fused

    def text_search(self, query: str, top_k: int = 30):
        """Search clinical notes using NIM text embeddings."""
        query_vector = self.text_embedder.embed_query(query)

        self.cursor.execute(f"""
            SELECT TOP {top_k}
                v.ResourceID,
                v.TextContent,
                VECTOR_DOT_PRODUCT(v.Vector, TO_VECTOR(?)) as Similarity
            FROM VectorSearch.FHIRTextVectors v
            ORDER BY Similarity DESC
        """, (str(query_vector),))

        results = []
        for rid, text, sim in self.cursor.fetchall():
            results.append({
                'resource_id': rid,
                'text_content': text,
                'score': float(sim)
            })
        return results

    def image_search(self, query_image: Image, top_k: int = 30):
        """Search medical images using NIM vision embeddings."""
        query_vector = self.image_embedder.embed_image(query_image)

        self.cursor.execute(f"""
            SELECT TOP {top_k}
                v.ResourceID,
                v.ImagePath,
                VECTOR_DOT_PRODUCT(v.Vector, TO_VECTOR(?)) as Similarity
            FROM VectorSearch.FHIRImageVectors v
            ORDER BY Similarity DESC
        """, (str(query_vector),))

        results = []
        for rid, path, sim in self.cursor.fetchall():
            results.append({
                'resource_id': rid,
                'image_path': path,
                'score': float(sim)
            })
        return results

    def graph_search(self, query: str, top_k: int = 10):
        """Search knowledge graph entities."""
        # Reuse existing graph search from GraphRAG implementation
        pass

    def rrf_fusion(self, text_results, image_results, graph_results, top_k):
        """Reciprocal Rank Fusion across modalities."""
        # Implementation from Phase 2
        pass
```

## Performance Benchmarking

### Metrics to Track

1. **Query Latency**
   - Text-only query: < 500ms
   - Image-only query: < 2s
   - Multimodal query (text + image + graph): < 3s

2. **Embedding Quality**
   - Recall@10 for clinical note search
   - Precision@10 for image retrieval
   - MRR (Mean Reciprocal Rank) for multimodal fusion

3. **Scalability**
   - Query performance with 10K patients
   - Query performance with 50K patients
   - Query performance with 100K patients

4. **Cost**
   - NIM API calls per query
   - Estimated cost per 1,000 queries

## Risk Mitigation

### Risk 1: MIMIC-CXR Access Delays
- **Mitigation**: Use synthetic imaging data or public NIH chest X-ray samples
- **Alternative**: Start with text-only NIM integration, add images later

### Risk 2: NIM Vision API Not Available
- **Mitigation**: Use open-source vision models (CLIP, BiomedCLIP)
- **Alternative**: Focus on text embeddings first, vision later

### Risk 3: Large Dataset Storage Requirements
- **Mitigation**: Start with 1K patients, scale up incrementally
- **Alternative**: Use cloud storage (S3) for images

## Success Criteria

### Phase 1 Success
- ✅ 10,000+ patients loaded into FHIR repository
- ✅ 500+ ImagingStudy resources with actual images
- ✅ Database queries return expected counts

### Phase 2 Success
- ✅ Vector tables created for text and images
- ✅ Modality detection correctly identifies text vs. image resources
- ✅ Cross-modal fusion algorithm validated with sample data

### Phase 3 Success
- ✅ NIM text embeddings replace SentenceTransformer
- ✅ All 51 DocumentReferences re-vectorized
- ✅ Query accuracy improves over baseline

### Phase 4 Success
- ✅ Medical images vectorized with NIM vision model
- ✅ Image search returns relevant results
- ✅ DICOM extraction pipeline functional

### Phase 5 Success
- ✅ Multimodal query interface operational
- ✅ RRF fusion combines text + image + graph results
- ✅ Query latency meets performance targets
- ✅ Integration tests pass (20/20 expected)

## Timeline Estimate

- **Phase 1**: 1-2 weeks (dataset generation and loading)
- **Phase 2**: 3-5 days (architecture design and implementation)
- **Phase 3**: 1 week (NIM text integration and testing)
- **Phase 4**: 1-2 weeks (NIM vision integration and image vectorization)
- **Phase 5**: 1 week (multimodal query and fusion)

**Total**: 4-6 weeks for complete implementation

## Conclusion

This plan transforms the FHIR GraphRAG system from a text-only search system into a true multimodal medical search platform capable of:

1. **Searching clinical notes** with NVIDIA NIM medical-domain embeddings
2. **Searching medical images** with NVIDIA NIM vision models
3. **Searching knowledge graphs** with existing entity extraction
4. **Fusing results** across all three modalities for comprehensive search

The system will demonstrate scalability with 10,000+ patients and 500+ medical imaging studies, establishing it as a production-ready multimodal medical AI platform.
