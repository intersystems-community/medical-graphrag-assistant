# Feature Specification: FHIR Radiology Integration

**Feature Branch**: `007-fhir-radiology-integration`
**Created**: 2025-12-15
**Status**: Draft
**Input**: User description: "Incorporate radiology info (images, notes, reports) into FHIR repo so that the data is linked to existing patients (best effort matching, perhaps modify some of the existing FHIR data to create a consistent 'story' per patient)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Link Radiology Images to FHIR Patients (Priority: P1)

A clinician searching for medical images needs to see the associated patient context. When they find a chest X-ray through semantic search, they should see which patient the image belongs to and be able to navigate to that patient's complete medical record.

**Why this priority**: This is the core value proposition - making disconnected radiology data useful by linking it to patient records. Without patient linkage, radiology images are orphaned data with limited clinical utility.

**Independent Test**: Can be fully tested by searching for an image (e.g., "pneumonia X-ray") and verifying the results display valid patient identifiers that link to existing FHIR Patient resources.

**Acceptance Scenarios**:

1. **Given** a MIMIC-CXR image with a subject_id of "p10002428", **When** the image is displayed in search results, **Then** it shows the linked FHIR patient name/identifier instead of "Unknown Patient"
2. **Given** an image search result, **When** the user views image details, **Then** they see the patient's name, MRN, and a link to view the full patient record
3. **Given** a radiology image without a matching FHIR patient, **When** displayed, **Then** the system shows "Unlinked" with the original source ID rather than hiding the data

---

### User Story 2 - Associate Studies with Patient Encounters (Priority: P2)

When radiology studies (a collection of images from one examination) are imported, they should be associated with a patient Encounter in FHIR. This enables clinicians to see imaging in the context of a specific hospital visit.

**Why this priority**: Encounter association provides temporal context, allowing clinicians to understand when imaging was performed relative to other clinical events.

**Independent Test**: Can be tested by querying a patient's encounters and verifying that linked imaging studies appear under the appropriate encounter.

**Acceptance Scenarios**:

1. **Given** a MIMIC-CXR study with study_id "s50414267", **When** imported, **Then** a corresponding FHIR ImagingStudy resource is created with a reference to a patient Encounter
2. **Given** a patient with multiple encounters, **When** viewing encounter details, **Then** associated radiology studies are visible under each relevant encounter
3. **Given** a study date/time, **When** no exact encounter match exists, **Then** the system links to the nearest encounter within 24 hours (assumption documented)

---

### User Story 3 - Create Consistent Patient Narratives (Priority: P3)

For demonstration and testing purposes, modify existing synthetic FHIR patient data to create coherent clinical "stories" that incorporate radiology findings. A patient with pneumonia diagnosis should have a chest X-ray showing pneumonia-related findings.

**Why this priority**: Creates realistic demo scenarios and enables end-to-end testing of the integrated workflow, but is not required for basic functionality.

**Independent Test**: Can be tested by selecting a patient with a respiratory diagnosis and verifying they have appropriately linked radiology images with matching findings.

**Acceptance Scenarios**:

1. **Given** an existing FHIR patient with a pneumonia Condition, **When** radiology integration runs, **Then** at least one chest X-ray with pneumonia findings is linked to that patient
2. **Given** a FHIR patient without respiratory conditions, **When** viewing their record, **Then** only non-respiratory imaging (if any) is linked
3. **Given** the need to create a demo patient story, **When** a clinician requests it, **Then** the system can generate a coherent patient with linked diagnoses, encounters, and imaging

---

### User Story 4 - Query FHIR Radiology Data via MCP Tools (Priority: P2)

Users of the agentic chat interface need MCP tools to query integrated FHIR radiology data. This enables Claude to autonomously fetch patient imaging information, radiology reports, and related clinical context when answering questions.

**Why this priority**: MCP tools are the primary integration point for AI agents. Without these tools, the linked radiology-FHIR data cannot be accessed through natural language queries in the chat interface.

**Independent Test**: Can be tested by asking the chat assistant "Show me imaging studies for patient John Smith" and verifying the response includes linked ImagingStudy resources with correct patient references.

**Acceptance Scenarios**:

1. **Given** a FHIR Patient with linked ImagingStudy resources, **When** a user asks "What X-rays does this patient have?", **Then** the MCP tool returns all associated imaging studies with dates and findings
2. **Given** a query for radiology reports, **When** the user asks "Show me the radiology report for study s50414267", **Then** the MCP tool returns the linked DiagnosticReport with clinical findings
3. **Given** a patient encounter query, **When** the user asks "What imaging was done during the January 2024 hospital visit?", **Then** the MCP tool returns ImagingStudy resources linked to that Encounter
4. **Given** a complex clinical query, **When** the user asks "Find patients with pneumonia diagnoses who have chest X-rays", **Then** the MCP tool queries across Patient, Condition, and ImagingStudy resources

---

### Edge Cases

- What happens when a radiology image's subject_id doesn't match any existing FHIR patient?
  - The image remains searchable but displays "Unlinked - Source ID: [subject_id]"
  - A report tracks unlinked images for manual review
- How does the system handle multiple patients with similar identifiers?
  - Matching uses exact ID matching first; fuzzy matching requires confidence threshold > 90%
  - Ambiguous matches are flagged for manual review
- What if MIMIC-CXR metadata is missing or malformed?
  - Images with missing subject_id are imported but flagged as "Unknown Source"
  - Study associations default to "Unknown Study" until corrected
- How are FHIR resources updated if radiology data is re-imported?
  - Idempotent import: existing links are preserved, only new associations are added
  - Version tracking maintains audit trail of changes

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST create FHIR ImagingStudy resources for each unique radiology study imported
- **FR-002**: System MUST link ImagingStudy resources to existing FHIR Patient resources using subject_id matching
- **FR-003**: System MUST display patient name and identifier in image search results instead of "Unknown Patient"
- **FR-004**: System MUST create or update FHIR DiagnosticReport resources to contain radiology findings
- **FR-005**: System MUST associate ImagingStudy resources with FHIR Encounter resources based on study date
- **FR-006**: System MUST maintain a mapping table between MIMIC-CXR subject_ids and FHIR Patient resource IDs
- **FR-007**: System MUST provide a report of unlinked radiology data for manual review
- **FR-008**: System MUST support idempotent import operations (re-running import does not create duplicates)
- **FR-009**: Users MUST be able to navigate from an image search result to the linked patient's full record
- **FR-010**: System MUST preserve original source identifiers (MIMIC subject_id, study_id) for traceability

### MCP Tool Requirements (Inspired by FHIRMcpServer patterns)

- **FR-011**: System MUST provide an MCP tool to retrieve all ImagingStudy resources for a given patient identifier
- **FR-012**: System MUST provide an MCP tool to retrieve a specific ImagingStudy by study ID with full details
- **FR-013**: System MUST provide an MCP tool to retrieve DiagnosticReport resources linked to imaging studies
- **FR-014**: System MUST provide an MCP tool to query patients who have imaging studies (with optional filters)
- **FR-015**: System MUST provide an MCP tool to retrieve Encounter resources with associated imaging studies
- **FR-016**: MCP tools MUST support standard FHIR query parameters (e.g., `_include`, `_revinclude`, date ranges)
- **FR-017**: MCP tools MUST return results in a format consumable by the agentic chat interface
- **FR-018**: System MUST provide an MCP tool to list available radiology-related FHIR queries (similar to FHIRMcpServer's `getQueryList`)
- **FR-019**: MCP tools MUST support cross-resource queries (e.g., Patient with Condition and ImagingStudy)

### Key Entities

- **FHIR Patient**: The person receiving healthcare; linked to ImagingStudy via patient reference
- **FHIR ImagingStudy**: Represents a radiology study (one or more images); references Patient and Encounter
- **FHIR Encounter**: A healthcare interaction/visit; provides temporal context for when imaging occurred
- **FHIR DiagnosticReport**: Contains clinical interpretation/findings from radiology images
- **Patient-Image Mapping**: Lookup table connecting MIMIC subject_ids to FHIR Patient IDs
- **MIMIC-CXR Image**: Source chest X-ray with embedded metadata (subject_id, study_id, view_position)

### MCP Tool Entities (Reference Architecture from FHIRMcpServer)

- **get_patient_imaging_studies**: Tool to retrieve all ImagingStudy resources for a patient
- **get_imaging_study_details**: Tool to get detailed information for a specific imaging study
- **get_radiology_reports**: Tool to retrieve DiagnosticReport resources for imaging studies
- **search_patients_with_imaging**: Tool to find patients based on imaging criteria
- **get_encounter_imaging**: Tool to retrieve imaging studies associated with a specific encounter
- **list_radiology_queries**: Tool listing available pre-defined FHIR queries for radiology data

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 80% or more of imported radiology images display a valid patient name (not "Unknown Patient") in search results
- **SC-002**: Users can navigate from image search results to patient record in 2 clicks or fewer
- **SC-003**: Image search response time remains under 2 seconds after radiology-FHIR linking is implemented
- **SC-004**: All radiology imports are traceable back to source data (MIMIC subject_id visible in image details)
- **SC-005**: At least 5 "patient story" demonstrations available showing coherent clinical narratives with linked imaging
- **SC-006**: Zero duplicate FHIR resources created when import is run multiple times on the same data
- **SC-007**: All 6 MCP radiology tools are discoverable and callable from the agentic chat interface
- **SC-008**: MCP tool queries return results within 1 second for single-patient lookups
- **SC-009**: Users can ask natural language questions about patient imaging and receive accurate FHIR-sourced responses

## Clarifications

### Session 2025-12-15
- Q: When MIMIC-CXR subject_ids don't match existing FHIR patients, what is the preferred strategy? → A: Create new synthetic FHIR patients using Synthea to ensure internal consistency (demographics, conditions, encounters)
- Q: What FHIR server implementation is currently running? → A: InterSystems IRIS for Health FHIR repository
- Q: For FR-004 (creating FHIR DiagnosticReport resources), where will the clinical findings/interpretations come from? → A: Use existing MIMIC-CXR radiology report text files, stored as FHIR DiagnosticReport resources with standard representation in the FHIR repository

## Assumptions

- MIMIC-CXR subject_ids (e.g., p10002428) can be deterministically mapped to existing synthetic FHIR Patient resources
- For unmatched MIMIC subject_ids, new FHIR Patient resources will be generated using Synthea to ensure internally consistent patient records (demographics, conditions, encounters)
- Study-to-Encounter matching will use a 24-hour window when exact timestamps don't match
- The existing synthetic FHIR data can be modified to create coherent patient stories without compliance concerns (since it's synthetic data)
- FHIR R4 resource definitions will be used for ImagingStudy, DiagnosticReport, and related resources
- MCP tool architecture follows patterns from FHIRMcpServer reference implementation (3 core tools: getCapabilityResource, getQueryList, callQuery)
- InterSystems IRIS for Health FHIR repository (on EC2) will be extended to support ImagingStudy queries via REST API
- MIMIC-CXR radiology report text files will be imported and stored as FHIR DiagnosticReport resources with standard representation (conclusionCode, presentedForm)
