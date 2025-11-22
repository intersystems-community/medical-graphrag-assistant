# Requirements Clarifications (CLARIFY)

**Feature**: Enhanced Medical Image Search (004-medical-image-search-v2)  
**Date**: 2025-11-21  
**Status**: Awaiting Stakeholder Input

This document identifies unclear, ambiguous, or missing requirements from the feature specification that must be clarified before full implementation.

---

## Critical Clarifications (Blocking Implementation)

### C1: Image Storage Architecture

**Requirement**: FR-005 states "System MUST provide image preview with zoom controls"

**Unclear**:
- Where are MIMIC-CXR image files physically stored?
  - Local disk on Streamlit server?
  - Remote IRIS server file system?
  - Cloud storage (S3, Azure Blob)?
  - Network-mounted drive?

**Impact**:
- Affects how Streamlit renders images (`st.image(path)` vs `st.image(url)` vs `st.image(blob)`)
- Determines if we need pre-signed URLs, authentication, or direct file access
- Impacts performance (local disk: <100ms, S3: 500-2000ms)

**Proposed Resolution**:
- **Option A**: Images stored locally on same machine as Streamlit → Simple `st.image(file_path)`
- **Option B**: Images on remote IRIS server → Need file transfer API or mounting
- **Option C**: Images in S3 → Need pre-signed URL generation

**Decision Needed**: Which option matches current deployment?

---

### C2: Database Access Configuration

**Requirement**: System connects to IRIS at `3.84.250.46:1972` (from existing code)

**Unclear**:
- Connection from `check_db_images.py` times out - is this expected?
- Does Streamlit app need VPN or special network access?
- Are there IP whitelist restrictions?
- Is the database connection working in production but not locally?

**Impact**:
- Blocks Phase 0 research validation
- Cannot test image path existence
- Cannot verify FHIR clinical note integration

**Proposed Resolution**:
- Verify network connectivity (`telnet 3.84.250.46 1972`)
- Check if VPN/bastion host required
- Test from Streamlit server environment vs local dev machine

**Decision Needed**: What is the expected network topology? Should local development use a different DB instance?

---

### C3: FHIR-to-Image Linking

**Requirement**: FR-004 states "System MUST retrieve and display associated FHIR DocumentReference clinical notes for each image when available"

**Unclear**:
- How are clinical notes linked to images?
  - Foreign key relationship (ImageID → FHIRResourceId)?
  - Fuzzy matching via SubjectID/StudyID in FHIR JSON?
  - Pre-computed mapping table?
  - Knowledge graph entity relationships?

**Impact**:
- Determines JOIN query complexity
- Affects query performance (indexed FK vs full-text search)
- Influences data model design

**Current Best Guess** (from code inspection):
```sql
-- Option 1: Fuzzy match via SubjectID
SELECT doc.ResourceString
FROM SQLUser.FHIRDocuments doc
WHERE doc.ResourceString LIKE '%SubjectID%'

-- Option 2: Via knowledge graph
SELECT e.ResourceID
FROM SQLUser.Entities e
WHERE e.EntityText = 'SubjectID'
```

**Decision Needed**: Which approach is correct? Can we add a proper foreign key?

---

## Important Clarifications (Affects UX)

### C4: Similarity Score Thresholds

**Requirement**: SC-002 states "Semantic search returns top-5 results with ≥0.6 similarity scores for 80% of common clinical queries"

**Unclear**:
- Is 0.6 threshold based on empirical testing, or arbitrary?
- Should thresholds vary by query type?
  - Complex queries ("bilateral infiltrates with effusion"): lower threshold (0.5)?
  - Simple queries ("chest X-ray"): higher threshold (0.7)?
- Should we use absolute scores or query-relative percentiles?

**Impact**:
- Affects user perception of result relevance
- Determines color coding logic (green/yellow/gray zones)
- May require A/B testing to optimize

**Proposed Resolution**:
- Start with fixed thresholds: ≥0.7 (green), 0.5-0.7 (yellow), <0.5 (gray)
- Log all scores for first 1000 queries
- Adjust thresholds based on user feedback and radiologist review

**Decision Needed**: Should we make thresholds user-configurable (advanced settings)?

---

### C5: Image Format & DICOM Support

**Requirement**: FR-005 mentions "image preview with window/level adjustment controls"

**Unclear**:
- Are images stored as DICOM (.dcm) or pre-converted JPEG/PNG?
- If DICOM:
  - Do we need `pydicom` for parsing?
  - Do we need specialized viewer (Cornerstone.js, OHIF)?
  - Window/level adjustment implies DICOM - but spec says "controls" may just be zoom/pan
- If JPEG/PNG:
  - Window/level adjustment not applicable
  - Standard image viewer sufficient

**Impact**:
- Determines frontend library choices
- Affects complexity (DICOM viewer is 7+ complexity vs simple image tag)
- Influences performance (DICOM parsing overhead)

**Current Code Evidence**:
- `nvclip_embeddings.py` has `_load_image()` that handles both DICOM and JPEG:
  ```python
  if image_input.lower().endswith('.dcm'):
      ds = pydicom.dcmread(image_input)
      img_array = ds.pixel_array
  ```

**Decision Needed**: What image format should Streamlit display? If DICOM, is full viewer needed or just basic preview?

---

### C6: Anonymization Requirements

**Requirement**: FR-012 states "System SHOULD anonymize patient data in exports [NEEDS CLARIFICATION]"

**Unclear**:
- Is anonymization required for MVP or future?
- What constitutes "anonymized"?
  - Remove patient IDs completely?
  - Hash patient IDs (irrevers ible)?
  - Replace with sequential numbers?
- Does this require HIPAA compliance review?
- Who is the compliance stakeholder?

**Impact**:
- If required for MVP: Adds significant scope (de-identification library, audit logging)
- If future feature: Can defer to Phase 4
- Legal/compliance risk if handled incorrectly

**Proposed Resolution**:
- **For MVP (P1-P2)**: Do NOT implement export feature (deferred to P3)
- **For P3**: Consult compliance team before implementing export
- **Interim**: Display warning "Do not export patient data without authorization"

**Decision Needed**: Is export feature required for MVP? If so, what is de-identification policy?

---

## Medium Priority Clarifications

### C7: Concurrent User Scale

**Requirement**: SC-003 states "System handles 50 concurrent users performing image searches without degradation"

**Unclear**:
- What is "degradation"? Response time increase? Error rate?
- Is this 50 concurrent searches or 50 active sessions?
- What is expected query rate (searches/sec)?

**Proposed Definition**:
- **50 concurrent users** = 50 simultaneous API calls to `search_medical_images`
- **Without degradation** = p95 response time stays <10s (vs 5s baseline)
- **Measurement**: Load test with Locust or JMeter

**Decision Needed**: Confirm definition or adjust target (e.g., 25 users for MVP)?

---

### C8: Filter Persistence

**Requirement**: User Story 2 mentions filters (view position, date range)

**Unclear**:
- Should filters persist across user sessions?
  - Session storage (cleared on browser close)?
  - User preferences (saved to database)?
  - No persistence (reset on every page load)?

**Impact**:
- Affects state management complexity
- User experience (convenience vs privacy)

**Proposed Resolution**:
- **P2 MVP**: Session storage only (Streamlit `st.session_state`)
- **P3 Enhancement**: User preferences with account system

**Decision Needed**: Is user account system in scope for this feature?

---

### C9: Image Preview Modal vs Inline

**Requirement**: User Story 3 mentions "modal displays the full-resolution image"

**Unclear**:
- Should preview be:
  - Modal dialog (overlay, requires click to close)?
  - Expandable accordion (inline, click to expand)?
  - Side panel (split view)?
  - New tab/window?

**Proposed Resolution**:
- **P2 MVP**: Streamlit expander (inline accordion) - simpler
- **P3 Enhancement**: True modal with `st.dialog()` or custom JS component

**Decision Needed**: Preference on UX pattern? (Modal preferred but more complex)

---

## Low Priority Clarifications (Nice-to-Have)

### C10: Search History Duration

**Requirement**: User Story 5 mentions "last 10 queries"

**Unclear**:
- Should history include:
  - Current session only?
  - Last 24 hours across sessions?
  - All-time until user clears?

**Proposed Resolution**: Session-only for MVP (simplest)

**Decision Needed**: Confirm or adjust scope

---

### C11: Saved Query Naming

**Requirement**: User Story 5 says "user enters name 'PTX Surveillance'"

**Unclear**:
- Character limit for saved query names?
- Duplicate name handling?
- Where to store (browser localStorage vs database)?

**Proposed Resolution**: 
- Max 50 characters
- Append number if duplicate ("PTX Surveillance (2)")
- Store in `st.session_state` (session-only for MVP)

**Decision Needed**: Acceptable?

---

## Assumptions to Validate

If clarifications cannot be obtained quickly, proceed with these assumptions (document as technical debt):

1. **Image Storage (C1)**: ASSUME images accessible via local file paths from Streamlit
2. **DB Access (C2)**: ASSUME temporary network issue, mock data for development
3. **FHIR Linking (C3)**: ASSUME fuzzy matching via SubjectID, optimize later
4. **Scores (C4)**: ASSUME fixed thresholds (0.7/0.5), tune post-MVP
5. **Image Format (C5)**: ASSUME JPEG/PNG for preview, DICOM support optional
6. **Anonymization (C6)**: ASSUME not required for MVP, defer to legal review
7. **Scale (C7)**: ASSUME 50 concurrent users with <10s p95 latency
8. **Filters (C8)**: ASSUME session-only persistence
9. **Preview (C9)**: ASSUME inline expander for MVP
10. **History (C10-C11)**: ASSUME session-only storage

---

## Action Items

- [ ] **USER**: Review C1-C3 (critical) and provide clarification
- [ ] **USER**: Confirm C4-C6 (important) decisions
- [ ] **TEAM**: Schedule clarification meeting for ambiguous requirements
- [ ] **ARCHITECT**: Document final decisions in `spec.md` updates
- [ ] **DEV**: Proceed with assumptions if clarifications delayed (document as TODO)

---

## Summary

| ID | Topic | Priority | Status |
|----|-------|----------|--------|
| C1 | Image Storage Architecture | Critical | ⏳ Awaiting User |
| C2 | Database Access | Critical | ⏳ Awaiting User |
| C3 | FHIR Linking | Critical | ⏳ Awaiting User |
| C4 | Score Thresholds | Important | 📋 Assumption OK |
| C5 | Image Format | Important | 📋 Assumption OK |
| C6 | Anonymization | Important | 📋Defer to P3 |
| C7 | Concurrent Scale | Medium | 📋 Assumption OK |
| C8 | Filter Persistence | Medium | 📋 Assumption OK |
| C9 | Preview Pattern | Medium | 📋 Assumption OK |
| C10 | History Duration | Low | 📋 Assumption OK |
| C11 | Query Naming | Low | 📋 Assumption OK |

**Next Step**: Address critical clarifications (C1-C3) before Phase 1, or proceed with assumptions and document as technical debt.
