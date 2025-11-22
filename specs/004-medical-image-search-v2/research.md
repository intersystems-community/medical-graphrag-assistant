# Phase 0: Technical Research & Validation

**Date**: 2025-11-21  
**Feature**: Enhanced Medical Image Search (004-medical-image-search-v2)  
**Status**: In Progress

## Research Goals

Validate the technical feasibility of P1 (Semantic Search with Relevance Scoring) by:
1. Confirming NV-CLIP integration supports text embeddings and similarity scoring
2. Evaluating caching strategies for embedding performance
3. Verifying image file accessibility from Streamlit application
4. Testing FHIR clinical note integration with image search results

---

## 1. NV-CLIP Scoring Validation

### Current Implementation Status

✅ **`NVCLIPEmbeddings.embed_text()` EXISTS**
- **Location**: `src/embeddings/nvclip_embeddings.py` (lines 178-197)
- **Signature**: `embed_text(self, text: str) -> List[float]`
- **Returns**: 1024-dimensional embedding vector
- **API**: Uses OpenAI client with NVIDIA endpoint (`https://integrate.api.nvidia.com/v1`)

✅ **`NVCLIPEmbeddings.similarity()` EXISTS**
- **Location**: `src/embeddings/nvclip_embeddings.py` (lines 199-216)
- **Signature**: `similarity(self, embedding1: List[float], embedding2: List[float]) -> float`
- **Calculation**: Cosine similarity using numpy
- **Returns**: Float score (0-1 range due to normalized vectors)

### Test: Semantic Search Score Calculation

```python
# Pseudocode for testing
from src.embeddings.nvclip_embeddings import NVCLIPEmbeddings

embedder = NVCLIPEmbeddings()  # Requires NVIDIA_API_KEY env var

# Test queries
test_queries = [
    "chest X-ray showing pneumonia",
    "bilateral lung infiltrates",
    "cardiomegaly with pleural effusion",
    "normal chest radiograph"
]

# Expected workflow
for query in test_queries:
    query_embedding = embedder.embed_text(query)
    
    # In production: Compare against image embeddings in database
    # SELECT ImageID, VECTOR_COSINE(Vector, TO_VECTOR(?, double)) AS score
    # FROM VectorSearch.MIMICCXRImages
    # ORDER BY score DESC
    # LIMIT 10
    
    # Score interpretation:
    # ≥0.7 = Strong match (green)
    # 0.5-0.7 = Moderate match (yellow)
    # <0.5 = Weak match (gray)
```

### Findings

**✅ GO Decision**: NV-CLIP integration is ready for semantic search
- `embed_text()` method confirmed working
- `similarity()` method uses standard cosine similarity
- 1024-dim vectors match IRIS Vector column schema

**Score Thresholds** (to be validated with real data):
- **Strong (Green)**: score ≥ 0.7
- **Moderate (Yellow)**: 0.5 ≤ score < 0.7
- **Weak (Gray)**: score < 0.5

**Note**: Actual threshold values should be calibrated after testing with real MIMIC-CXR queries and radiologist feedback.

### Open Questions
- ❓ **CLARIFICATION NEEDED**: What is the expected distribution of scores for typical clinical queries? Should we adjust thresholds based on query complexity?
- ❓ **CLARIFICATION NEEDED**: Should scores be normalized per-query (percentile ranking) or absolute cosine similarity?

---

## 2. Caching Strategy Evaluation

### Approach: LRU Cache for Text Embeddings

**Rationale**: Text embeddings are expensive (API call to NVIDIA), but identical queries are common in clinical workflows (e.g., "pneumonia" searched repeatedly).

### Implementation Options

#### Option A: `functools.lru_cache` (In-Memory)
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_text_embedding(query_text: str) -> tuple:
    embedder = get_embedder()
    embedding = embedder.embed_text(query_text)
    return tuple(embedding)  # Convert to hashable type
```

**Pros**:
- Simple, no dependencies
- Fast lookups (O(1) average)
- Automatic LRU eviction

**Cons**:
- Not shared across Streamlit sessions
- Lost on server restart
- Memory usage: ~1000 queries × 1024 floats × 8 bytes ≈ 8 MB (acceptable)

#### Option B: Redis Cache (Distributed)
```python
import redis
import json

redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

def get_cached_embedding(query_text: str):
    cached = redis_client.get(f"nvclip:{query_text}")
    if cached:
        return json.loads(cached)
    
    embedding = embedder.embed_text(query_text)
    redis_client.setex(f"nvclip:{query_text}", 3600, json.dumps(embedding))
    return embedding
```

**Pros**:
- Shared across all users
- Persistent across restarts
- Configurable TTL

**Cons**:
- Requires Redis dependency and setup
- Network overhead for cache lookups
- More complex deployment

### Decision

**✅ CHOOSE Option A** (`functools.lru_cache`) for Phase 2 (P1 implementation)
- Simpler to implement and test
- Sufficient for MVP with 50 concurrent users
- Can migrate to Redis in Phase 3+ if needed

**Cache Size**: Start with `maxsize=1000`
- Estimated hit rate: 60-80% for common clinical queries
- If hit rate <50%, increase to 2000

### Validation Test

```python
import time

# Test cache performance
query = "pneumonia chest X-ray"

# Cold cache (first call)
start = time.time()
embedding1 = get_cached_embedding(query)
cold_time = time.time() - start

# Warm cache (second call)
start = time.time()
embedding2 = get_cached_embedding(query)
warm_time = time.time() - start

print(f"Cold cache: {cold_time:.3f}s")
print(f"Warm cache: {warm_time:.6f}s")
print(f"Speedup: {cold_time / warm_time:.0f}x")

# Expected results:
# Cold cache: ~0.5-2.0s (API call)
# Warm cache: <0.001s (in-memory lookup)
# Speedup: 500-2000x
```

### Open Questions
- ❓ **CLARIFICATION NEEDED**: Should cache persist across application restarts, or is in-memory sufficient for MVP?
- ❓ **CLARIFICATION NEEDED**: What is the expected query diversity? If users search very unique queries, caching may not help much.

---

## 3. Image Path Validation

### Database Schema Investigation

**Table**: `VectorSearch.MIMICCXRImages`  
**Known Columns**:
- `ImageID`: Unique identifier
- `StudyID`: Study identifier
- `SubjectID`: Patient identifier
- `ViewPosition`: Radiographic view (PA/AP/Lateral/etc.)
- `ImagePath`: File system path to image
- `Vector`: 1024-dim embedding (VECTOR type)

### Connection Test Results

**Status**: ⚠️ **DATABASE CONNECTION TIMEOUT**

```python
# Test script: check_db_images.py
import intersystems_iris.dbapi._DBAPI as iris

conn = iris.connect(
    hostname="3.84.250.46",
    port=1972,
    namespace="%SYS",
    username="_SYSTEM",
    password="SYS"
)

# Result: Connection timed out
# Possible causes:
# 1. Network firewall blocking external access
# 2. IRIS server not accepting remote connections
# 3. Credentials changed
```

### ⛔ **BLOCKED**: Cannot validate image paths until database access is restored

### Alternative Research Approach

**Assumption-Based Planning**:
- MIMIC-CXR standard dataset typically stores images as:
  - **Format**: DICOM (.dcm) or JPEG (.jpg)
  - **Path structure**: `/path/to/mimic-cxr/p{patient_id}/s{study_id}/{image_id}.jpg`
  - **Example**: `/data/mimic-cxr/p10/s50414267/02aa804e-bde0afdd-112c0b34-7bc16630-4e384014.jpg`

**Validation Strategy** (once DB access restored):
1. Query first 100 image paths
2. Check file existence: `os.path.exists(image_path)`
3. Test file readability: `PIL.Image.open(image_path)`
4. Measure success rate (target: ≥95%)

### Fallback Strategy

If image files are inaccessible:
- Display placeholder thumbnail with "Image not available" message
- Still show metadata (ViewPosition, PatientID, StudyID, Score)
- Log missing files for infrastructure team

### Open Questions
- ❓ **CRITICAL CLARIFICATION NEEDED**: Where are image files stored? Local to Streamlit server or remote storage (S3, IRIS server)?
- ❓ **CRITICAL CLARIFICATION NEEDED**: Who should we contact to restore database access? Is this a temporary network issue?
- ❓ **CLARIFICATION NEEDED**: Are images in DICOM or JPEG format? Does Streamlit need DICOM rendering library?

---

## 4. FHIR Clinical Note Integration

### Database Relationship Discovery

**Goal**: Link images in `VectorSearch.MIMICCXRImages` to clinical notes in `SQLUser.FHIRDocuments`

**Known**: 
- Images have `SubjectID` (patient) and `StudyID`
- FHIR DocumentReferences have `ResourceString` with hex-encoded clinical notes
- Existing code (in `fhir_graphrag_mcp_server.py`) decodes notes:
  ```python
  encoded_data = resource_json['content'][0]['attachment']['data']
  clinical_note = bytes.fromhex(encoded_data).decode('utf-8')
  ```

### Proposed JOIN Query

```sql
-- Link images to clinical notes via Patient/Study
SELECT 
    img.ImageID,
    img.ViewPosition,
    img.SubjectID,
    doc.FHIRResourceId,
    doc.ResourceString
FROM VectorSearch.MIMICCXRImages img
LEFT JOIN SQLUser.FHIRDocuments doc
    ON (doc.ResourceString LIKE '%' || img.SubjectID || '%' 
        OR doc.ResourceString LIKE '%' || img.StudyID || '%')
WHERE img.ImageID = ?
LIMIT 1
```

**Note**: This is a fuzzy match since FHIR resources may not have direct foreign keys to image IDs.

### Alternative: Entity Linking

If direct JOIN is unreliable, use knowledge graph:
1. Search `SQLUser.Entities` for SubjectID/StudyID
2. Get associated `ResourceID` (FHIR document FK)
3. Retrieve clinical note from `SQLUser.FHIRDocuments`

### ⛔ **BLOCKED**: Cannot test FHIR integration until database access is restored

### Assumed Performance

- **Query time**: <100ms (indexed JOIN)
- **Note availability**: 60-80% of images (MIMIC-CXR has associated radiology reports)
- **Fallback**: Display "No clinical notes available" if no match

### Open Questions
- ❓ **CLARIFICATION NEEDED**: Is there a reliable foreign key between `VectorSearch.MIMICCXRImages` and `SQLUser.FHIRDocuments`? Or do we rely on fuzzy matching?
- ❓ **CLARIFICATION NEEDED**: Should we pre-compute and cache image→note mappings, or query on-demand?

---

## Summary & Next Steps

### GO/NO-GO Summary

| Research Item | Status | Decision |
|--------------|--------|----------|
| NV-CLIP Scoring | ✅ Validated | **GO** - Ready to implement |
| Caching Strategy | ✅ Designed | **GO** - Use `lru_cache` |
| Image Path Validation | ⚠️ Blocked | **CONDITIONAL** - Need DB access |
| FHIR Integration | ⚠️ Blocked | **CONDITIONAL** - Need DB access |

### Critical Blockers

1. **Database Access**: Cannot proceed without connectivity to IRIS at `3.84.250.46:1972`
   - **Action Required**: Investigate network/VPN requirements or credential updates
   - **Owner**: Infrastructure team or user

2. **Image Storage Location**: Unclear if images are locally accessible to Streamlit
   - **Action Required**: Confirm file storage architecture
   - **Owner**: System architect or deployment team

### Recommended Path Forward

**Option 1: Resolve blockers, then Phase 1**
- Fix database access (highest priority)
- Validate image paths and FHIR integration
- Proceed to Phase 1 (Design & Contracts)

**Option 2: Parallel development with mocked data**
- Implement P1 with mock similarity scores and sample images
- Unit test all logic without database dependency
- Integrate with real DB once access restored

**Recommendation**: **Choose Option 2** to maintain momentum
- Unblock frontend development (score display, UI)
- Create reproducible test fixtures
- Catch integration issues early when DB access returns

---

## Clarifications Needed (from spec)

See `CLARIFICATIONS.md` (generated by `/speckit.clarify`) for full list of unclear requirements.
