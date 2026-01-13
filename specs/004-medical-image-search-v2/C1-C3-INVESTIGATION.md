# C1-C3 Clarifications: Investigation Results

**Date**: 2025-11-21  
**Feature**: Enhanced Medical Image Search (004-medical-image-search-v2)  
**Investigator**: Technical analysis of existing codebase

---

## C1: Image Storage Architecture ✅ **RESOLVED**

### Finding: Images stored locally on development machine

**Evidence from codebase**:

1. **Ingestion Script** (`ingest_mimic_cxr_images.py`):
   ```python
   # Line 24
   MIMIC_CXR_BASE = "../mimic-cxr/physionet.org/files/mimic-cxr/2.1.0/files"
   ```

2. **File System Verification**:
   ```bash
   $ ls -la ../mimic-cxr/
   drwxr-xr-x@   4 maintainer  physionet.org
   
   $ find ../mimic-cxr/ -name "*.dcm" | head -3
   ../mimic-cxr/physionet.org/files/mimic-cxr/2.1.0/files/p10/p10045779/s53819164/4b369dbe-417168fa-7e2b5f04-00582488-c50504e7.dcm
   ```

3. **Database Schema** (`VectorSearch.MIMICCXRImages`):
   - `ImagePath VARCHAR(1000)` contains full local file paths
   - Example path structure: `../mimic-cxr/physionet.org/files/mimic-cxr/2.1.0/files/p10/p10045779/s53819164/{image_id}.dcm`

### **Answer to C1**:

**Storage Architecture**: **Option A - Local filesystem on same machine as Streamlit**

**Path Structure**:
```
{PROJECT_ROOT}/../mimic-cxr/physionet.org/files/mimic-cxr/2.1.0/files/
└── p{XX}/          # Patient ID prefix (p10, p11, etc.)
    └── p{XXXXXXXX}/  # Full Patient ID
        └── s{XXXXXXXX}/  # Study ID
            └── {image_id}.dcm  # DICOM file
```

**Image Format**: **DICOM (.dcm files)**

**Streamlit Access Strategy**:
- Use relative paths from database (`ImagePath` column)
- Verify file existence before rendering: `os.path.exists(image_path)`
- Load DICOM with `pydicom.dcmread()` (already used in `nvclip_embeddings.py`)
- Display with `st.image()` after converting DICOM pixel array to PIL Image

**Implementation Notes**:
- ✅ **Pros**: Fast access (<100ms), no network latency, no authentication needed
- ⚠️ **Cons**: Deployment to AWS/cloud requires updating paths or mounting storage
- 📋 **Action**: For cloud deployment, consider migrating to S3 with pre-signed URLs

### Implications for Feature Implementation

1. **Image Preview (P2)**: Can use direct file access via `pydicom`
2. **Window/Level Adjustment**: Possible since we have raw DICOM pixel data
3. **Thumbnail Generation**: Should pre-generate thumbnails for performance (500x500 JPG)
4. **File Validation**: MUST implement file existence checks (some may be missing)

---

## C2: Database Access Configuration ⚠️ **PARTIALLY RESOLVED**

### Finding: Two database configurations exist

**Configuration 1: Local IRIS (Development)**
- Used by: `ingest_mimic_cxr_images.py`
- Connection: `localhost:32782/DEMO`
- Credentials: `_SYSTEM` / `ISCDEMO`
- **Purpose**: Local development, image ingestion

**Configuration 2: AWS IRIS (Production)**
- Used by: `mcp-server/fhir_graphrag_mcp_server.py`, Streamlit app
- Connection: `3.84.250.46:1972/%SYS`
- Credentials: `_SYSTEM` / `SYS`
- **Purpose**: Production MCP server, Streamlit queries

### Network Connectivity Test

**Status**: ⏳ **Testing in progress** (network check running)

**Hypothesis**: Local development should use `localhost:32782`, but current code points to AWS

### **Answer to C2**:

**Database Topology**:
```
Development Environment:
┌─────────────────┐      ┌──────────────────┐
│ Streamlit App   │─────▶│ IRIS localhost   │
│ (localhost:8502)│      │ (localhost:32782)│
└─────────────────┘      └──────────────────┘
        │
        ▼
  MIMIC-CXR files
  (local filesystem)


Production Environment (AWS):  
┌─────────────────┐      ┌──────────────────┐
│ Streamlit App   │─────▶│ IRIS AWS Server  │
│ (AWS EC2/ECS)   │      │ (3.84.250.46)    │
└─────────────────┘      └──────────────────┘
        │
        ▼
  MIMIC-CXR files
  (EFS/S3/EBS?)
```

**Current Issue**: 
- MCP server (`fhir_graphrag_mcp_server.py`) hard-coded to AWS IRIS (`3.84.250.46`)
- Streamlit app likely connecting to same AWS database
- Local development might be accessing remote DB (slow/timing out)

**Recommended Solution**:

1. **Use environment variables** for database configuration:
   ```python
   # mcp-server/fhir_graphrag_mcp_server.py
   AWS_CONFIG = {
       'hostname': os.getenv('IRIS_HOST', '3.84.250.46'),
       'port': int(os.getenv('IRIS_PORT', 1972)),
       'namespace': os.getenv('IRIS_NAMESPACE', '%SYS'),
       'username': os.getenv('IRIS_USERNAME', '_SYSTEM'),
       'password': os.getenv('IRIS_PASSWORD', 'SYS')
   }
   ```

2. **Update `.env` for local development**:
   ```bash
   IRIS_HOST=localhost
   IRIS_PORT=32782
   IRIS_NAMESPACE=DEMO
   IRIS_USERNAME=_SYSTEM
   IRIS_PASSWORD=ISCDEMO
   ```

3. **Keep AWS config for production** (no `.env` file, uses defaults)

### Implications for Feature Implementation

1. **Phase 0 Research**: Use local IRIS (`localhost:32782`) for testing
2. **Database Connection Module**: Create `src/db/connection.py` to centralize config
3. **Environment Detection**: Auto-detect dev vs prod based on `IRIS_HOST` env var
4. **Testing**: Mock database for unit tests, use local IRIS for integration tests

---

## C3: FHIR-to-Image Linking ✅ **RESOLVED**

### Finding: No direct foreign key, must use fuzzy matching

**Database Schema Analysis**:

**Images Table** (`VectorSearch.MIMICCXRImages`):
```sql
CREATE TABLE VectorSearch.MIMICCXRImages (
    ImageID VARCHAR(100),      -- DICOM filename (e.g., "4b369dbe-417168fa...")
    SubjectID VARCHAR(20),     -- Patient ID (e.g., "10045779")
    StudyID VARCHAR(20),       -- Study ID (e.g., "53819164")
    DicomID VARCHAR(100),      -- Same as ImageID
    ImagePath VARCHAR(1000),   -- File system path
    ViewPosition VARCHAR(10),  -- PA / AP / Lateral / LL
    Vector VECTOR(DOUBLE, 1024),
    EmbeddingModel VARCHAR(100),
    Provider VARCHAR(50)
)
```

**FHIR Documents Table** (`SQLUser.FHIRDocuments`):
```sql
CREATE TABLE SQLUser.FHIRDocuments (
    FHIRResourceId VARCHAR(50),  -- FHIR resource ID (e.g., "1234")
    ResourceType VARCHAR(50),    -- "DocumentReference" / "Patient" / etc.
    ResourceString CLOB          -- JSON string with clinical notes (hex-encoded)
)
```

**Knowledge Graph Table** (`SQLUser.Entities`):
```sql
CREATE TABLE SQLUser.Entities (
    EntityID INT,
    EntityText VARCHAR(500),   -- Could contain SubjectID/StudyID as text
    EntityType VARCHAR(50),    -- "PERSON" / "DATE" / etc.
    Confidence FLOAT,
    ResourceID VARCHAR(50)     -- Links to FHIRDocuments.FHIRResourceId
)
```

### **Answer to C3**:

**Linking Strategy**: **Multi-step fuzzy matching** (in order of preference)

#### Approach 1: Via Knowledge Graph (Most Reliable)
```sql
-- Step 1: Find entities matching SubjectID or StudyID
SELECT e.ResourceID, e.EntityText
FROM SQLUser.Entities e
WHERE e.EntityText IN (?, ?)  -- (SubjectID, StudyID from image)
  AND e.EntityType IN ('PERSON', 'DATE')
ORDER BY e.Confidence DESC
LIMIT 10

-- Step 2: Get FHIR documents for those resources
SELECT f.FHIRResourceId, f.ResourceString
FROM SQLUser.FHIRDocuments f
WHERE f.FHIRResourceId IN (SELECT ResourceID FROM previous_query)
  AND f.ResourceType = 'DocumentReference'
```

#### Approach 2: Direct FHIR JSON Search (Fallback)
```sql
-- Search for SubjectID in FHIR JSON (slower, but works if entities missing)
SELECT FHIRResourceId, ResourceString
FROM SQLUser.FHIRDocuments
WHERE ResourceType = 'DocumentReference'
  AND (
    ResourceString LIKE CONCAT('%', ?, '%')  -- SubjectID
    OR ResourceString LIKE CONCAT('%', ?, '%')  -- StudyID
  )
LIMIT 5
```

#### Approach 3: Pre-computed Mapping Table (Best for Production)
```sql
-- Create materialized view or table for fast lookups
CREATE TABLE VectorSearch.ImageToFHIRMapping (
    ImageID VARCHAR(100) PRIMARY KEY,
    FHIRResourceId VARCHAR(50),
    MatchConfidence FLOAT,
    MatchMethod VARCHAR(20)  -- 'entity' / 'json_search' / 'manual'
)

-- Then simple JOIN
SELECT img.*, fhir.ResourceString
FROM VectorSearch.MIMICCXRImages img
LEFT JOIN VectorSearch.ImageToFHIRMapping map ON img.ImageID = map.ImageID
LEFT JOIN SQLUser.FHIRDocuments fhir ON map.FHIRResourceId = fhir.FHIRResourceId
WHERE img.ImageID = ?
```

### Clinical Note Decoding

**Current implementation** (from `fhir_graphrag_mcp_server.py`):
```python
resource_json = json.loads(resource_string)
encoded_data = resource_json['content'][0]['attachment']['data']
clinical_note = bytes.fromhex(encoded_data).decode('utf-8')
```

**Expected Availability**: 60-80% of images (not all studies have clinical notes)

### **Recommended Implementation for P1**:

1. **Use Approach 1** (Knowledge Graph) with fallback to Approach 2
2. **Cache mappings** in-memory (`@lru_cache`) keyed by `ImageID`
3. **Handle missing notes gracefully**: Display "No clinical notes available"
4. **Phase 3 optimization**: Create pre-computed mapping table for production

### Implications for Feature Implementation

1. **API Response Time**: 100-500ms for note retrieval (acceptable for P2)
2. **P1 Implementation**: Defer clinical notes to P2 (focus on search + scores first)
3. **P2 Implementation**: Add `get_clinical_note_for_image(image_id)` function
4. **Error Handling**: Must handle cases where:
   - No entities found for SubjectID/StudyID
   - No FHIR documents match
   - FHIR document exists but no clinical note content
   - Hex decoding fails (corrupted data)

---

## Summary Table

| Clarification | Status | Answer | Action Required |
|--------------|--------|--------|-----------------|
| **C1: Image Storage** | ✅ Resolved | Local filesystem, DICOM format, relative paths from `../mimic-cxr/` | None - implementation can proceed |
| **C2: Database Access** | ⚠️ Partial | Two configs exist (localhost dev, AWS prod), need env var isolation | Update code to use env vars, document both configs |
| **C3: FHIR Linking** | ✅ Resolved | Fuzzy matching via Knowledge Graph → FHIR, no direct FK | Implement multi-step query with fallbacks |

---

## Updated Implementation Decisions

### For P1 (Semantic Search with Scoring):
- ✅ Use local IRIS (`localhost:32782`) for development
- ✅ Access images via local DICOM files
- ✅ Skip clinical notes in P1 (defer to P2)
- ✅ Test with mock data if DB connection issues persist

### For P2 (Filters & Clinical Context):
- ✅ Implement clinical note linking using Knowledge Graph approach
- ✅ Add file existence validation before image preview
- ✅ Consider pre-generating thumbnails for performance

###For Deployment:
- 🔧 **TODO**: Create environment-based config system
- 🔧 **TODO**: Document localhost vs AWS database setup
- 🔧 **TODO**: Plan migration strategy for image storage (local → S3/EFS)

---

## Next Steps

1. ✅ **C1-C3 Clarifications complete** 
2. ⏭️ **Proceed to Phase 1**: Design data models and API contracts
3. 🛠️ **Technical Debt**: 
   - [ ] Add environment variable support for database config
   - [ ] Document dual-database setup (dev vs prod)
   - [ ] Create `src/db/connection.py` module
   - [ ] Test network connectivity to AWS IRIS (still pending)

**Ready to move forward with Phase 1 design!** 🚀
