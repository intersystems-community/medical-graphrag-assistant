# Research: FHIR Radiology Integration

**Feature**: 007-fhir-radiology-integration
**Date**: 2025-12-15
**Status**: Complete

## Research Questions

### 1. Patient Matching Strategy

**Question**: How should MIMIC-CXR subject_ids be mapped to FHIR Patient resources?

**Decision**: Create new synthetic FHIR patients using Synthea for unmatched MIMIC subject_ids

**Rationale**:
- Synthea generates internally consistent patient records (demographics, conditions, encounters)
- Existing synthetic FHIR data can be safely modified for demo purposes
- Ensures referential integrity - every image links to a valid Patient resource

**Alternatives Considered**:
- Manual mapping file: Rejected - doesn't scale, requires maintenance
- Random assignment: Rejected - creates incoherent patient stories
- Leave unlinked: Rejected - defeats the purpose of the feature

### 2. FHIR Server Implementation

**Question**: What FHIR server is currently deployed?

**Decision**: InterSystems IRIS for Health FHIR repository

**Rationale**:
- Already deployed on EC2 with existing FHIR Patient resources
- Native vector support in same database as image embeddings
- REST API access for FHIR resource queries

**Implementation Notes**:
- FHIR R4 standard
- REST endpoint pattern: `GET /fhir/r4/[ResourceType]?[params]`
- Supports `_include` and `_revinclude` for linked resources

### 3. FHIR ImagingStudy Resource Structure

**Decision**: Use FHIR R4 ImagingStudy with standard fields for MIMIC-CXR integration

**Key Fields for Patient Linking**:
```json
{
  "resourceType": "ImagingStudy",
  "id": "study-s50414267",
  "status": "available",
  "subject": { "reference": "Patient/p10002428" },
  "encounter": { "reference": "Encounter/enc-123" },
  "started": "2024-01-15T10:30:00Z",
  "identifier": [
    {
      "system": "urn:mimic-cxr:study",
      "value": "s50414267"
    }
  ],
  "modality": [
    { "system": "http://dicom.nema.org/resources/ontology/DCM", "code": "CR" }
  ],
  "numberOfSeries": 1,
  "numberOfInstances": 1,
  "series": [
    {
      "uid": "1.2.3.4.5",
      "modality": { "code": "CR" },
      "instance": [
        {
          "uid": "1.2.3.4.5.1",
          "sopClass": { "code": "1.2.840.10008.5.1.4.1.1.1.1" },
          "number": 1
        }
      ]
    }
  ]
}
```

**Rationale**:
- `subject` links to FHIR Patient via reference
- `encounter` enables temporal context
- `identifier` preserves MIMIC study_id for traceability
- Standard DICOM modality codes (CR = Computed Radiography)

### 4. FHIR DiagnosticReport for Radiology Reports

**Decision**: Store MIMIC-CXR report text as FHIR DiagnosticReport with presentedForm

**Key Fields**:
```json
{
  "resourceType": "DiagnosticReport",
  "id": "report-s50414267",
  "status": "final",
  "code": {
    "coding": [
      {
        "system": "http://loinc.org",
        "code": "18748-4",
        "display": "Diagnostic imaging study"
      }
    ]
  },
  "subject": { "reference": "Patient/p10002428" },
  "encounter": { "reference": "Encounter/enc-123" },
  "effectiveDateTime": "2024-01-15T11:00:00Z",
  "imagingStudy": [
    { "reference": "ImagingStudy/study-s50414267" }
  ],
  "conclusion": "No acute cardiopulmonary process.",
  "conclusionCode": [
    {
      "coding": [
        {
          "system": "http://snomed.info/sct",
          "code": "373067005",
          "display": "No abnormality detected"
        }
      ]
    }
  ],
  "presentedForm": [
    {
      "contentType": "text/plain",
      "data": "RklORElOR1M6IE5vIGFjdXRlIGNhcmRpb3B1bG1vbmFyeSBwcm9jZXNzLg=="
    }
  ]
}
```

**Rationale**:
- `presentedForm` stores full report text (base64 encoded)
- `conclusion` provides human-readable summary
- `imagingStudy` links report to ImagingStudy resource
- Standard LOINC codes for diagnostic imaging

### 5. MCP Tool Architecture

**Decision**: Follow existing MCP server patterns with 6 new radiology-specific tools

**Tools to Implement**:
| Tool Name | Description | FHIR Query |
|-----------|-------------|------------|
| `get_patient_imaging_studies` | All ImagingStudy for a patient | `ImagingStudy?subject=Patient/{id}` |
| `get_imaging_study_details` | Single study with full metadata | `ImagingStudy/{id}?_include=*` |
| `get_radiology_reports` | DiagnosticReport for imaging | `DiagnosticReport?imaging-study={id}` |
| `search_patients_with_imaging` | Patients with imaging by criteria | `ImagingStudy?_include=ImagingStudy:subject` |
| `get_encounter_imaging` | Studies for an encounter | `ImagingStudy?encounter=Encounter/{id}` |
| `list_radiology_queries` | Available query templates | N/A (metadata tool) |

**Rationale**:
- Follows existing MCP tool patterns in `fhir_graphrag_mcp_server.py`
- Uses IRIS for Health REST API for FHIR queries
- Returns JSON for LLM consumption

### 6. Patient-Image Mapping Table

**Decision**: Create new IRIS table `VectorSearch.PatientImageMapping`

**Schema**:
```sql
CREATE TABLE VectorSearch.PatientImageMapping (
    MIMICSubjectID VARCHAR(255) PRIMARY KEY,
    FHIRPatientID VARCHAR(255) NOT NULL,
    FHIRPatientName VARCHAR(500),
    MatchConfidence DECIMAL(3,2),
    MatchType VARCHAR(50),  -- 'exact', 'synthea_generated', 'manual'
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Rationale**:
- Enables fast lookups during image search
- Preserves match metadata for auditing
- Supports idempotent import operations

### 7. UI Enhancement for Image Search

**Decision**: Modify `search_medical_images` response to include patient context

**Current Response** (showing "Unknown Patient"):
```json
{
  "images": [
    {
      "image_id": "p10002428_s50414267_view1",
      "study_type": "Unknown Study",
      "patient_id": "Unknown Patient"
    }
  ]
}
```

**Enhanced Response**:
```json
{
  "images": [
    {
      "image_id": "p10002428_s50414267_view1",
      "study_id": "s50414267",
      "patient_name": "John Smith",
      "patient_mrn": "MRN-12345",
      "fhir_patient_id": "Patient/p10002428",
      "view_position": "PA",
      "similarity_score": 0.87
    }
  ]
}
```

**Rationale**:
- Addresses FR-003: Display patient name in search results
- Enables FR-009: Navigation to patient record

## Dependencies

| Dependency | Purpose | Status |
|------------|---------|--------|
| InterSystems IRIS for Health | FHIR repository + vector storage | Deployed |
| Synthea | Generate synthetic patients | Available (external) |
| MCP SDK | Tool exposure | Installed |
| NV-CLIP | Image embeddings | Deployed |

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| MIMIC subject_ids have no FHIR match | Images show "Unlinked" | Generate Synthea patients for unmatched |
| FHIR API rate limits | Slow queries | Batch operations, caching |
| Data inconsistency | Orphaned resources | Idempotent import with validation |

## Next Steps

1. Create `VectorSearch.PatientImageMapping` table
2. Implement FHIR resource generation scripts
3. Add 6 new MCP tools to server
4. Update UI to display patient context
5. Write tests (contract, integration, UX)
