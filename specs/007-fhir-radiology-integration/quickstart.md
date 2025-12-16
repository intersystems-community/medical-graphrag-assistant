# Quickstart: FHIR Radiology Integration

**Feature**: 007-fhir-radiology-integration
**Date**: 2025-12-15

## Overview

This feature integrates MIMIC-CXR radiology images with the FHIR repository, enabling:
- Patient-linked image search results (no more "Unknown Patient")
- 6 new MCP tools for querying FHIR radiology data
- FHIR ImagingStudy and DiagnosticReport resources for radiology

## Prerequisites

- InterSystems IRIS for Health running (FHIR repository)
- MIMIC-CXR images loaded in `VectorSearch.MIMICCXRImages` table
- NV-CLIP embedding service available
- Python 3.11+ with MCP SDK

## Quick Start

### 1. Create Patient Mapping Table

```bash
cd src/setup
python create_patient_mapping.py
```

This creates `VectorSearch.PatientImageMapping` to link MIMIC subject_ids to FHIR Patient IDs.

### 2. Import Radiology FHIR Resources

```bash
cd src/setup
python import_radiology_fhir.py --batch-size 50
```

This:
- Maps MIMIC subjects to FHIR Patients (or creates Synthea patients for unmatched)
- Creates FHIR ImagingStudy resources for each radiology study
- Creates FHIR DiagnosticReport resources from MIMIC report text

#### Synthea Patient Generation (for unmatched subjects)

When a MIMIC subject_id cannot be matched to an existing FHIR Patient, the import script uses Synthea to generate a synthetic patient:

```bash
# Synthea is invoked automatically by import_radiology_fhir.py
# Manual invocation if needed:
java -jar synthea-with-dependencies.jar \
  --exporter.fhir.export true \
  --exporter.baseDirectory ./output \
  -p 1 \
  --generate.demographics.default_file custom_demographics.json
```

The generated FHIR Bundle is then POSTed to the IRIS FHIR repository.

### 3. Verify Integration

```python
# Test via MCP tool
from mcp_server import get_patient_imaging_studies

result = await get_patient_imaging_studies(patient_id="p10002428")
print(f"Found {result['total_count']} studies")
```

### 4. Use in Chat Interface

Ask natural language questions:
- "Show me imaging studies for patient John Smith"
- "What X-rays has this patient had?"
- "Get the radiology report for study s50414267"
- "Find patients with pneumonia on chest X-ray"

## MCP Tools

| Tool | Description |
|------|-------------|
| `get_patient_imaging_studies` | All studies for a patient |
| `get_imaging_study_details` | Detailed study info with series/instances |
| `get_radiology_reports` | DiagnosticReport with clinical findings |
| `search_patients_with_imaging` | Find patients by imaging criteria |
| `get_encounter_imaging` | Studies for a specific encounter |
| `list_radiology_queries` | Available query templates |

## Key Files

```
src/
├── adapters/fhir_radiology_adapter.py    # FHIR resource adapter
├── setup/
│   ├── create_patient_mapping.py         # Create mapping table
│   └── import_radiology_fhir.py          # Import FHIR resources

mcp-server/
├── fhir_graphrag_mcp_server.py           # MCP tools (6 new radiology tools)
└── streamlit_app.py                      # UI with patient context
```

## Troubleshooting

**"Unknown Patient" still showing in search results**
- Verify `PatientImageMapping` table has entries: `SELECT COUNT(*) FROM VectorSearch.PatientImageMapping`
- Re-run import script: `python import_radiology_fhir.py`

**MCP tool returns empty results**
- Check FHIR endpoint connectivity
- Verify ImagingStudy resources exist: `GET /fhir/r4/ImagingStudy?_count=1`

**Import fails with "Patient not found"**
- Synthea patient generation may have failed
- Check Synthea output directory and logs

## Environment Variables

```bash
export IRIS_HOST=localhost
export IRIS_PORT=1972
export IRIS_NAMESPACE=FHIRSERVER
export FHIR_BASE_URL=http://localhost:52773/fhir/r4
```

## Performance

- Image search with patient context: <2s
- Single patient lookup: <1s
- Batch import: ~49 images in <30s
