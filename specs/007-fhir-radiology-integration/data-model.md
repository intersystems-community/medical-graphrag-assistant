# Data Model: FHIR Radiology Integration

**Feature**: 007-fhir-radiology-integration
**Date**: 2025-12-15

## Entity Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Data Model Relationships                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────┐     ┌──────────────────┐                         │
│  │  MIMIC-CXR       │     │  FHIR Patient    │                         │
│  │  Images Table    │     │  Resource        │                         │
│  │  (IRIS Vector)   │     │  (IRIS FHIR)     │                         │
│  └────────┬─────────┘     └────────┬─────────┘                         │
│           │                        │                                    │
│           │   ┌────────────────────┼────────────────────┐              │
│           │   │                    │                    │              │
│           ▼   ▼                    ▼                    ▼              │
│  ┌──────────────────┐     ┌──────────────────┐  ┌──────────────────┐  │
│  │  Patient-Image   │────►│  FHIR            │  │  FHIR Encounter  │  │
│  │  Mapping Table   │     │  ImagingStudy    │◄─│  Resource        │  │
│  │  (NEW)           │     │  Resource (NEW)  │  │  (Existing)      │  │
│  └──────────────────┘     └────────┬─────────┘  └──────────────────┘  │
│                                    │                                    │
│                                    ▼                                    │
│                           ┌──────────────────┐                         │
│                           │  FHIR            │                         │
│                           │  DiagnosticReport│                         │
│                           │  Resource (NEW)  │                         │
│                           └──────────────────┘                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Entities

### 1. VectorSearch.PatientImageMapping (NEW)

**Purpose**: Links MIMIC-CXR subject_ids to FHIR Patient resource IDs

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| MIMICSubjectID | VARCHAR(255) | PRIMARY KEY | MIMIC-CXR subject identifier (e.g., "p10002428") |
| FHIRPatientID | VARCHAR(255) | NOT NULL | FHIR Patient resource ID |
| FHIRPatientName | VARCHAR(500) | | Patient display name |
| MatchConfidence | DECIMAL(3,2) | DEFAULT 1.0 | Confidence score (0.00-1.00) |
| MatchType | VARCHAR(50) | | 'exact', 'synthea_generated', 'manual' |
| CreatedAt | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Record creation time |
| UpdatedAt | TIMESTAMP | | Last modification time |

**Indexes**:
- PRIMARY KEY on MIMICSubjectID
- INDEX on FHIRPatientID for reverse lookups

**Validation Rules**:
- MIMICSubjectID must match pattern `p[0-9]+`
- FHIRPatientID must be non-empty
- MatchConfidence must be between 0 and 1

### 2. VectorSearch.MIMICCXRImages (EXISTS - Modified)

**Purpose**: Stores MIMIC-CXR image vectors with metadata

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| ImageID | VARCHAR(255) | PRIMARY KEY | Unique image identifier |
| StudyID | VARCHAR(255) | NOT NULL | MIMIC study identifier (e.g., "s50414267") |
| SubjectID | VARCHAR(255) | NOT NULL | MIMIC subject identifier |
| ViewPosition | VARCHAR(50) | | PA, AP, LATERAL, LL |
| ImagePath | VARCHAR(1000) | | Path to DICOM file |
| Vector | VECTOR(DOUBLE, 1024) | | NV-CLIP embedding |
| Metadata | VARCHAR(4000) | | JSON metadata |
| CreatedAt | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | |
| UpdatedAt | TIMESTAMP | | |

**Note**: No schema changes - uses existing table structure.

### 3. FHIR ImagingStudy Resource (NEW)

**Purpose**: FHIR R4 representation of radiology study

**Key Fields**:
```json
{
  "resourceType": "ImagingStudy",
  "id": "string (study-{study_id})",
  "identifier": [{ "system": "urn:mimic-cxr:study", "value": "{study_id}" }],
  "status": "available | registered | cancelled",
  "subject": { "reference": "Patient/{fhir_patient_id}" },
  "encounter": { "reference": "Encounter/{encounter_id}" },
  "started": "datetime",
  "modality": [{ "system": "http://dicom.nema.org/resources/ontology/DCM", "code": "CR" }],
  "numberOfSeries": "integer",
  "numberOfInstances": "integer",
  "series": [
    {
      "uid": "string",
      "modality": { "code": "CR" },
      "instance": [{ "uid": "string", "sopClass": {...}, "number": "integer" }]
    }
  ],
  "note": [{ "text": "MIMIC-CXR imported study" }]
}
```

**Validation Rules**:
- `subject` reference MUST resolve to valid Patient
- `identifier` MUST contain original MIMIC study_id
- `status` MUST be one of: registered, available, cancelled

### 4. FHIR DiagnosticReport Resource (NEW)

**Purpose**: FHIR R4 representation of radiology report

**Key Fields**:
```json
{
  "resourceType": "DiagnosticReport",
  "id": "string (report-{study_id})",
  "identifier": [{ "system": "urn:mimic-cxr:report", "value": "{study_id}" }],
  "status": "final | preliminary | amended",
  "code": {
    "coding": [{ "system": "http://loinc.org", "code": "18748-4", "display": "Diagnostic imaging study" }]
  },
  "subject": { "reference": "Patient/{fhir_patient_id}" },
  "encounter": { "reference": "Encounter/{encounter_id}" },
  "effectiveDateTime": "datetime",
  "issued": "datetime",
  "imagingStudy": [{ "reference": "ImagingStudy/{study_id}" }],
  "conclusion": "string (report summary)",
  "conclusionCode": [{ "coding": [{ "system": "http://snomed.info/sct", "code": "...", "display": "..." }] }],
  "presentedForm": [{ "contentType": "text/plain", "data": "base64-encoded-report-text" }]
}
```

**Validation Rules**:
- `subject` reference MUST resolve to valid Patient
- `imagingStudy` reference MUST resolve to valid ImagingStudy
- `presentedForm.data` MUST be valid base64

### 5. FHIR Patient Resource (EXISTS)

**Purpose**: Person receiving healthcare

**Relevant Fields for Integration**:
```json
{
  "resourceType": "Patient",
  "id": "string",
  "identifier": [{ "system": "urn:mimic-cxr:subject", "value": "{subject_id}" }],
  "name": [{ "family": "string", "given": ["string"] }],
  "gender": "male | female | other | unknown",
  "birthDate": "date"
}
```

**Integration Note**: Existing patients receive new identifier with MIMIC subject_id when linked.

### 6. FHIR Encounter Resource (EXISTS)

**Purpose**: Healthcare visit/interaction

**Relevant Fields for Integration**:
```json
{
  "resourceType": "Encounter",
  "id": "string",
  "status": "planned | in-progress | finished",
  "subject": { "reference": "Patient/{id}" },
  "period": { "start": "datetime", "end": "datetime" }
}
```

**Integration Note**: ImagingStudy links to Encounter via 24-hour window matching on study date.

## Relationships

| Source | Target | Cardinality | Description |
|--------|--------|-------------|-------------|
| PatientImageMapping | Patient | N:1 | Many MIMIC subjects can map to one FHIR patient |
| MIMICCXRImages | PatientImageMapping | N:1 | Many images per subject |
| ImagingStudy | Patient | N:1 | Many studies per patient |
| ImagingStudy | Encounter | N:1 | Study occurs during encounter |
| DiagnosticReport | ImagingStudy | 1:1 | One report per study |
| DiagnosticReport | Patient | N:1 | Many reports per patient |

## State Transitions

### Image Linking State
```
┌─────────────┐    import    ┌─────────────┐    link     ┌─────────────┐
│  UNLINKED   │─────────────►│  MATCHING   │────────────►│   LINKED    │
│             │              │             │             │             │
│ SubjectID   │              │ Searching   │             │ PatientID   │
│ only        │              │ for match   │             │ resolved    │
└─────────────┘              └──────┬──────┘             └─────────────┘
                                    │
                                    │ no match
                                    ▼
                             ┌─────────────┐
                             │  SYNTHEA    │
                             │  GENERATED  │
                             │             │
                             │ New patient │
                             │ created     │
                             └─────────────┘
```

## Data Flow

1. **Import Flow**:
   - Read MIMIC-CXR metadata from images table
   - Lookup or create patient mapping
   - Generate FHIR ImagingStudy resource
   - Import MIMIC radiology report text
   - Generate FHIR DiagnosticReport resource

2. **Query Flow**:
   - MCP tool receives query
   - Join PatientImageMapping with MIMICCXRImages
   - Enrich with FHIR Patient data
   - Return structured response

## Report Formats

### Unlinked Images Report (FR-007)

**Purpose**: Report of images that could not be linked to FHIR Patient resources after import

**Output Format**: JSON file + optional CSV summary

```json
{
  "report_type": "unlinked_images",
  "generated_at": "2025-12-15T10:30:00Z",
  "total_images": 49,
  "linked_count": 45,
  "unlinked_count": 4,
  "link_rate_percent": 91.8,
  "unlinked_images": [
    {
      "image_id": "img_001",
      "study_id": "s12345678",
      "subject_id": "p99999999",
      "view_position": "PA",
      "failure_reason": "no_patient_match",
      "match_attempts": [
        {
          "method": "exact_subject_id",
          "result": "no_match"
        },
        {
          "method": "synthea_generation",
          "result": "failed",
          "error": "Synthea process timeout"
        }
      ]
    }
  ],
  "summary_by_reason": {
    "no_patient_match": 2,
    "synthea_generation_failed": 1,
    "fhir_post_failed": 1
  }
}
```

**CSV Summary Format** (`unlinked_report.csv`):
```csv
image_id,study_id,subject_id,view_position,failure_reason,error_message
img_001,s12345678,p99999999,PA,no_patient_match,
img_002,s23456789,p88888888,AP,synthea_generation_failed,Process timeout
```

**Output Location**: `output/reports/unlinked_images_{timestamp}.json`

**Validation Rules**:
- `total_images` = `linked_count` + `unlinked_count`
- `link_rate_percent` = `linked_count` / `total_images` * 100
- Each unlinked image MUST have at least one `match_attempt` entry
- `failure_reason` MUST be one of: `no_patient_match`, `synthea_generation_failed`, `fhir_post_failed`, `invalid_metadata`
