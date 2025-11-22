# Feature Specification: Enhanced Medical Image Search

**Feature Branch**: `001-medical-image-search-v2`  
**Created**: 2025-11-21  
**Status**: Draft  
**Input**: User description: "Create a feature spec for improving the medical image search functionality"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Semantic Search with Relevance Scoring (Priority: P1)

Clinicians need to find chest X-rays using natural language queries like "pneumonia with pleural effusion" rather than rigid keywords, and see why each result was matched.

**Why this priority**: This is the core value proposition of the feature. Without semantic search working reliably, users will fall back to manual browsing, making the tool unusable for its intended purpose.

**Independent Test**: Can be fully tested by submitting a natural language query (e.g., "chest X-ray showing fluid in lungs") and verifying that:
1. Results are returned ranked by semantic relevance
2. Each result displays a similarity score
3. Results include images matching the clinical description

**Acceptance Scenarios**:

1. **Given** the image database has X-rays with various findings, **When** a clinician searches "chest X-ray of pneumonia", **Then** the system returns images with pneumonia findings ranked by semantic similarity scores (0-1), with scores > 0.7 indicating strong matches

2. **Given** a query "bilateral infiltrates", **When** the search executes, **Then** results include textual explanations of why each image matched (e.g., "matched: bilateral pattern detected, opacity in both lung fields")

3. **Given** the NV-CLIP embedding service is unavailable, **When** a search is performed, **Then** the system gracefully falls back to keyword search and displays a warning message

---

### User Story 2 - Filter and Refine Results (Priority: P2)

Users need to filter search results by view position (PA, AP, Lateral), patient demographics, or study date to narrow down findings.

**Why this priority**: Once semantic search works (P1), filtering becomes essential for clinical workflows where radiologists need specific views or timeframes.

**Independent Test**: After searching "chest X-ray pneumonia", apply filters for:
- View position: "PA" only
- Date range: Last 30 days
- Verify only matching results are displayed

**Acceptance Scenarios**:

1. **Given** search results contain mixed view positions, **When** user selects "PA View" filter, **Then** only PA (posteroanterior) chest X-rays are displayed

2. **Given** results span multiple months, **When** user sets date range filter "2024-01-01 to 2024-03-31", **Then** only images from Q1 2024 are shown

3. **Given** multiple filters are active, **When** user clicks "Clear Filters", **Then** all filters reset and full result set displays

---

### User Story 3 - Image Preview with Clinical Context (Priority: P2)

Radiologists need to preview images with associated clinical notes, patient history, and diagnostic reports before opening the full DICOM viewer.

**Why this priority**: Saves time by allowing quick assessment without loading full medical records. Enhances existing search results.

**Independent Test**: Click on any search result and verify:
- Thumbnail enlarges to full preview
- Associated FHIR clinical note displays
- Patient demographics shown (ID, age, sex)
- Study metadata visible (date, view, technique)

**Acceptance Scenarios**:

1. **Given** a search result list, **When** user clicks on an X-ray thumbnail, **Then** a modal displays the full-resolution image with zoom/pan controls

2. **Given** an image preview is open, **When** clinical notes exist for that study, **Then** the notes display alongside the image with symptoms, indications, and findings sections highlighted

3. **Given** a preview modal is open, **When** user presses ESC or clicks outside, **Then** modal closes and returns to search results

---

### User Story 4 - Batch Export and Comparison (Priority: P3)

Researchers need to export multiple images matching specific criteria for analysis, and compare images side-by-side.

**Why this priority**: Supports research workflows but not critical for initial clinical adoption.

**Independent Test**: 
1. Select 5 images from search results using checkboxes
2. Click "Export Selected" and verify ZIP download contains all images with metadata JSON
3. Click "Compare" and verify side-by-side view with synchronized zoom

**Acceptance Scenarios**:

1. **Given** search results displayed, **When** user selects multiple images via checkboxes, **Then** a "Export Selected (N)" button appears in the toolbar

2. **Given** 10 images are selected, **When** user clicks "Export Selected", **Then** a ZIP file downloads containing JPG images and a metadata.json file with patient IDs, study dates, and finding descriptions

3. **Given** 2-4 images are selected, **When** user clicks "Compare", **Then** a comparison view displays images side-by-side with synchronized zoom/pan and synchronized window/level adjustment

---

### User Story 5 - Search History and Saved Queries (Priority: P3)

Clinicians frequently repeat queries for their specialty (e.g., pulmonologists always searching lung conditions) and need quick access to previous searches.

**Why this priority**: Improves efficiency for power users but not essential for MVP.

**Independent Test**: 
1. Perform 3 different searches
2. Navigate to "History" tab
3. Verify all 3 queries listed with timestamps
4. Click "Save Query" on one search
5. Verify it appears in "Saved Searches" with custom name

**Acceptance Scenarios**:

1. **Given** a user has performed searches this session, **When** user clicks "Recent Searches" dropdown, **Then** last 10 queries display in reverse chronological order

2. **Given** a query "bilateral pneumothorax view:PA", **When** user clicks "Save This Query" and enters name "PTX Surveillance", **Then** query saves and appears in "Saved Searches" list

3. **Given** saved query exists, **When** user clicks it from sidebar, **Then** search executes immediately with saved parameters

---

### Edge Cases

- What happens when a query contains medical terms not in the embedding model's vocabulary (e.g., rare disease names)?
  - **Expected**: System should tokenize and attempt partial matches, explaining "limited semantic understanding for term: [rare-term]"

- How does system handle very long queries (>500 characters)?
  - **Expected**: Truncate to 500 chars with warning message "Query truncated to 500 characters for processing"

- What if image files referenced in database no longer exist on disk?
  - **Expected**: Display placeholder image with "Image not available" message, but still show metadata and allow user to report broken link

- How does system behave when database contains 10,000+ images and user doesn't apply filters?
  - **Expected**: Paginate results (50 per page), display processing time, suggest using filters for faster results

- What happens when user's browser doesn't support WebGL for image rendering?
  - **Expected**: Fall back to standard IMG tags, disable zoom features, show compatibility notice

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST generate semantic embeddings for text queries using NV-CLIP model and return results ranked by cosine similarity score
- **FR-002**: System MUST display similarity scores (0.00 to 1.00) for each search result with visual indicators (color coding: green ≥0.7, yellow 0.5-0.7, gray <0.5)
- **FR-003**: System MUST support filtering results by: view position (PA/AP/Lateral/LL), study date range, patient ID pattern, and similarity score threshold
- **FR-004**: System MUST retrieve and display associated FHIR DocumentReference clinical notes for each image when available
- **FR-005**: System MUST provide image preview with zoom (1x-5x), pan, and window/level adjustment controls
- **FR-006**: System MUST implement graceful degradation when NV-CLIP service is unavailable, falling back to keyword search on ViewPosition and StudyID fields
- **FR-007**: System MUST support batch export of selected images (max 100) as ZIP containing JPG files and metadata JSON
- **FR-008**: System MUST paginate results (default 50 per page) for queries returning >50 images
- **FR-009**: System MUST cache embedding computations for common queries to improve response time
- **FR-010**: System MUST log all searches with query text, result count, and execution time for analytics

**Uncertain Requirements**:

- **FR-011**: System SHOULD support DICOM viewer integration [NEEDS CLARIFICATION: Which DICOM viewer? Cornerstonejs? OHIF? Embedded or external launch?]
- **FR-012**: System SHOULD anonymize patient data in exports [NEEDS CLARIFICATION: Remove patient IDs? Hash them? Requires HIPAA compliance review]

### Key Entities

- **ImageSearchQuery**: User's search request with text, filters (view position, date range), and pagination parameters
- **ImageSearchResult**: Individual matched image with metadata (ImageID, StudyID, SubjectID, ViewPosition, file path), similarity score, and optional thumbnail
- **NVCLIPEmbedding**: 1024-dimensional vector representation of query text or image content
- **ClinicalContext**: Associated FHIR DocumentReference with clinical notes, findings, and patient demographics
- **SearchSession**: User's search history with queries, timestamps, and result counts
- **SavedQuery**: Named search with predefined filters and parameters for repeated use

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can find relevant chest X-rays in under 10 seconds for natural language queries (measured from query submission to first result display)
- **SC-002**: Semantic search returns top-5 results with ≥0.6 similarity scores for 80% of common clinical queries (e.g., "pneumonia", "cardiomegaly", "pleural effusion")
- **SC-003**: System handles 50 concurrent users performing image searches without degradation (response time <5s for p95)
- **SC-004**: Fallback keyword search activates within 2 seconds when NV-CLIP service fails
- **SC-005**: 90% of users successfully apply at least one filter to refine results (telemetry tracked)
- **SC-006**: Image preview loads in <3 seconds for p95 of requests
- **SC-007**: Zero patient data leaks in exported files when anonymization enabled (validated via automated tests)

## Technical Considerations

### Current Implementation Gaps

1. **No relevance scoring**: Current implementation returns images but doesn't expose similarity scores to users
2. **No filtering UI**: Database supports ViewPosition, StudyID, etc., but no UI controls exist
3. **No clinical context integration**: Images returned without associated FHIR clinical notes
4. **Image paths may be invalid**: Database has file paths but no validation if files exist or are accessible from Streamlit
5. **No caching**: Every query recomputes embeddings even for identical searches
6. **Error handling**: Current fallback to keyword search happens silently without user notification

### Database Schema (VectorSearch.MIMICCXRImages)

Based on code inspection, table contains:
- `ImageID`: Unique identifier
- `StudyID`: Study identifier
- `SubjectID`: Patient identifier  
- `ViewPosition`: Radiographic view (PA/AP/Lateral/LL/etc.)
- `ImagePath`: File system path to image
- `Vector`: 1024-dim embedding vector for semantic search

### Dependencies

- **NV-CLIP**: NVIDIA multimodal embedding service (requires NVIDIA_API_KEY)
- **IRIS Vector Search**: InterSystems IRIS vector database with VECTOR_COSINE function
- **FHIR Resources**: DocumentReference resources in SQLUser.FHIRDocuments table
- **Streamlit**: Frontend framework (currently used)
- **Plotly**: Not directly needed for images, but could support result visualizations

### Open Questions

1. **Image Storage**: Are images stored locally on Streamlit server or on remote IRIS server at 3.84.250.46?
2. **Image Format**: Are files DICOM (.dcm) or converted to JPG/PNG?
3. **Thumbnail Generation**: Should system pre-generate thumbnails or create on-the-fly?
4. **Authentication**: Does search need user authentication to comply with HIPAA?
5. **Audit Trail**: Should system log which user accessed which patient images?

## Next Steps

1. **Review & Approval**: Share spec with stakeholders (clinicians, compliance team)
2. **Technical Design**: Create implementation plan addressing:
   - UI mockups for search results with filters
   - API endpoint design for image retrieval 
   - Caching strategy for embeddings
   - Error handling and fallback UX
3. **Prototyping**: Build P1 user story (semantic search with scoring) as proof-of-concept
4. **Testing Strategy**: Define test datasets and expected results for semantic search accuracy
