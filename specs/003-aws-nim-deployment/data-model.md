# Data Model: AWS GPU-based NVIDIA NIM RAG Deployment

**Feature**: 003-aws-nim-deployment
**Date**: 2025-11-09
**Status**: Complete

## Overview

This deployment automation manages three primary data domains:

1. **Vector Storage**: Clinical document and medical image embeddings in IRIS
2. **Processing State**: Vectorization job tracking and resumability
3. **Deployment State**: Infrastructure and service status

---

## Vector Storage Schema (IRIS Database)

### ClinicalNoteVectors Table

Stores vectorized representations of clinical text documents.

```sql
CREATE TABLE DEMO.ClinicalNoteVectors (
    ResourceID VARCHAR(255) PRIMARY KEY,
    PatientID VARCHAR(255) NOT NULL,
    DocumentType VARCHAR(255) NOT NULL,
    TextContent VARCHAR(10000),
    SourceBundle VARCHAR(500),
    Embedding VECTOR(DOUBLE, 1024) NOT NULL,
    EmbeddingModel VARCHAR(100) NOT NULL,
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX PatientIdx ON DEMO.ClinicalNoteVectors(PatientID);
CREATE INDEX DocumentTypeIdx ON DEMO.ClinicalNoteVectors(DocumentType);
CREATE INDEX CreatedAtIdx ON DEMO.ClinicalNoteVectors(CreatedAt);
```

**Field Descriptions**:
- `ResourceID`: Unique identifier from source FHIR bundle (e.g., "urn:uuid:abc123...")
- `PatientID`: FHIR Patient resource ID for filtering by patient
- `DocumentType`: Type of clinical document (e.g., "History and physical note", "Discharge summary")
- `TextContent`: Truncated text content (first 10000 chars) for result display
- `SourceBundle`: Path/reference to original FHIR bundle file
- `Embedding`: 1024-dimensional vector from NVIDIA NIM embeddings API
- `EmbeddingModel`: Model identifier (e.g., "nvidia/nv-embedqa-e5-v5") for version tracking
- `CreatedAt`, `UpdatedAt`: Timestamps for audit trail

**Validation Rules**:
- Embedding must be exactly 1024 dimensions
- PatientID and ResourceID cannot be null
- EmbeddingModel must match approved model list

---

### MedicalImageVectors Table

Stores vectorized representations of medical images (chest X-rays, etc.).

```sql
CREATE TABLE DEMO.MedicalImageVectors (
    ImageID VARCHAR(255) PRIMARY KEY,
    PatientID VARCHAR(255) NOT NULL,
    StudyID VARCHAR(255),
    ImageFormat VARCHAR(50) NOT NULL,
    ImagePath VARCHAR(500) NOT NULL,
    RelatedReportID VARCHAR(255),
    Embedding VECTOR(DOUBLE, 1024) NOT NULL,
    EmbeddingModel VARCHAR(100) NOT NULL,
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (RelatedReportID) REFERENCES ClinicalNoteVectors(ResourceID)
);

CREATE INDEX ImagePatientIdx ON DEMO.MedicalImageVectors(PatientID);
CREATE INDEX ImageStudyIdx ON DEMO.MedicalImageVectors(StudyID);
```

**Field Descriptions**:
- `ImageID`: Unique identifier for the medical image
- `StudyID`: DICOM Study Instance UID or similar grouping identifier
- `ImageFormat`: File format (e.g., "DICOM", "PNG", "JPG")
- `ImagePath`: Storage location (S3 path, local filesystem, etc.)
- `RelatedReportID`: Foreign key to associated clinical report in ClinicalNoteVectors
- `Embedding`: 1024-dimensional visual embedding from NVIDIA NIM Vision model

**Relationships**:
- One-to-many: Patient → MedicalImageVectors
- Optional one-to-one: MedicalImageVector → ClinicalNoteVector (for report linkage)

---

## Processing State Schema (SQLite)

### VectorizationState Table

Tracks which documents have been processed for resumable pipelines.

```sql
CREATE TABLE VectorizationState (
    DocumentID TEXT PRIMARY KEY,
    DocumentType TEXT NOT NULL,  -- 'clinical_note' or 'medical_image'
    Status TEXT NOT NULL,  -- 'pending', 'processing', 'completed', 'failed'
    ProcessingStartedAt TEXT,
    ProcessingCompletedAt TEXT,
    ErrorMessage TEXT,
    RetryCount INTEGER DEFAULT 0
);

CREATE INDEX StatusIdx ON VectorizationState(Status);
CREATE INDEX DocumentTypeIdx ON VectorizationState(DocumentType);
```

**State Transitions**:
```
pending → processing → completed
            ↓
          failed → pending (on retry)
```

**Usage**:
- Before processing batch: SELECT documents WHERE Status != 'completed'
- On processing start: UPDATE Status = 'processing', ProcessingStartedAt = NOW()
- On success: UPDATE Status = 'completed', ProcessingCompletedAt = NOW()
- On failure: UPDATE Status = 'failed', ErrorMessage = '...', RetryCount += 1

---

## Deployment State Model (In-Memory)

### DeploymentStatus

Not persisted to database, maintained as deployment script state.

```json
{
  "deployment_id": "deploy-20251109-123456",
  "status": "in_progress",
  "steps": [
    {
      "name": "provision_instance",
      "status": "completed",
      "started_at": "2025-11-09T12:34:56Z",
      "completed_at": "2025-11-09T12:36:30Z",
      "details": {
        "instance_id": "i-012abe9cf48fdc702",
        "instance_type": "g5.xlarge",
        "public_ip": "34.238.176.10"
      }
    },
    {
      "name": "install_gpu_drivers",
      "status": "in_progress",
      "started_at": "2025-11-09T12:36:31Z"
    },
    {
      "name": "deploy_iris",
      "status": "pending"
    }
  ]
}
```

**Step Status Values**:
- `pending`: Not started
- `in_progress`: Currently executing
- `completed`: Successfully finished
- `failed`: Error encountered
- `skipped`: Skipped due to idempotency check

---

## Entity Relationships

```
Patient (FHIR)
    ↓ 1:N
ClinicalNoteVectors
    ↓ 1:1 (optional)
MedicalImageVectors
```

### Relationship Cardinalities

- **Patient → ClinicalNoteVectors**: One-to-Many
  - One patient can have multiple clinical notes
  - Enforced by `PatientID` foreign key semantics (logical, not SQL FK)

- **ClinicalNoteVector → MedicalImageVectors**: One-to-Many (optional)
  - One clinical report may reference multiple images
  - Images may exist without associated reports
  - Enforced by `RelatedReportID` in MedicalImageVectors table

- **VectorizationJob → Documents**: One-to-Many
  - One vectorization job processes many documents
  - Tracked implicitly via batch timestamps in VectorizationState

---

## Vector Operations

### Similarity Search Query Pattern

Using `./rag-templates/common/vector_sql_utils.py` utilities:

```python
from common.vector_sql_utils import execute_safe_vector_search

# Search for similar clinical notes
results = execute_safe_vector_search(
    cursor=iris_cursor,
    table_name="DEMO.ClinicalNoteVectors",
    vector_column="Embedding",
    query_vector=query_embedding,  # 1024-dim numpy array
    top_k=10,
    additional_columns=["ResourceID", "PatientID", "DocumentType", "TextContent"]
)

# Results format:
# [
#   {
#     "ResourceID": "urn:uuid:...",
#     "PatientID": "patient-123",
#     "DocumentType": "History and physical note",
#     "TextContent": "Patient presents with...",
#     "similarity_score": 0.92
#   },
#   ...
# ]
```

**Why utilities required**:
- IRIS SQL does not support parameter markers in TO_VECTOR() function
- Direct string interpolation creates SQL injection risk
- Utilities validate vector format and use safe parameterization patterns

---

## Data Validation

### Vector Validation

```python
def validate_vector(embedding: List[float]) -> bool:
    """Validate embedding meets requirements"""
    if len(embedding) != 1024:
        raise ValueError(f"Expected 1024-dim vector, got {len(embedding)}")
    if not all(isinstance(v, (int, float)) for v in embedding):
        raise ValueError("Vector must contain only numeric values")
    if any(math.isnan(v) or math.isinf(v) for v in embedding):
        raise ValueError("Vector contains NaN or Inf values")
    return True
```

### Document Validation

```python
def validate_clinical_note(note: dict) -> bool:
    """Validate clinical note structure"""
    required_fields = ['resource_id', 'patient_id', 'document_type', 'text_content']
    if not all(field in note for field in required_fields):
        raise ValueError(f"Missing required fields: {required_fields}")
    if len(note['text_content']) < 10:
        raise ValueError("Text content too short (minimum 10 characters)")
    return True
```

---

## Migration and Schema Evolution

Since this is initial deployment, no migrations required. Future schema changes should:

1. Add new columns with DEFAULT values to maintain backward compatibility
2. Never drop columns (mark as deprecated instead)
3. Use ALTER TABLE for non-breaking changes
4. For breaking changes, create new table and migrate data

**Example Future Migration**:
```sql
-- Add optional metadata field (non-breaking)
ALTER TABLE DEMO.ClinicalNoteVectors
ADD COLUMN EncounterID VARCHAR(255) DEFAULT NULL;

-- Add index for new field
CREATE INDEX EncounterIdx ON DEMO.ClinicalNoteVectors(EncounterID);
```

---

## Summary

- **Vector Tables**: Store 1024-dim embeddings with metadata in IRIS using native VECTOR type
- **State Tracking**: SQLite for lightweight, resumable processing state
- **Deployment State**: JSON-formatted status tracking for deployment orchestration
- **Validation**: Strict input validation prevents data quality issues
- **Safe Vector Operations**: Always use rag-templates utilities to prevent SQL injection
