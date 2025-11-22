# Implementation Plan: Enhanced Medical Image Search

**Branch**: `004-medical-image-search-v2` | **Date**: 2025-11-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-medical-image-search-v2/spec.md`

## Summary

Enhance the existing medical image search functionality (`search_medical_images` MCP tool) to provide semantic search with relevance scoring, advanced filtering, clinical context integration, and improved user experience. Primary approach: extend NV-CLIP integration, expose similarity scores in UI, build Streamlit filtering controls, and integrate FHIR clinical notes alongside image results.

## Technical Context

**Language/Version**: Python 3.12/3.13 (Miniconda)  
**Primary Dependencies**: 
- Streamlit (web UI framework)
- NV-CLIP via OpenAI client (NVIDIA multimodal embeddings)
- InterSystems IRIS Vector DB (vector storage with VECTOR_COSINE)
- Plotly (visualizations)
- FHIR.resources (clinical data models)

**Storage**: 
- IRIS Database at 3.84.250.46:1972
  - `VectorSearch.MIMICCXRImages` table (images with 1024-dim vectors)
  - `SQLUser.FHIRDocuments` table (clinical notes)
  - `SQLUser.Entities` table (knowledge graph entities)

**Testing**: 
- pytest for backend/MCP server tests
- Playwright for E2E Streamlit UI tests (existing in `tests/e2e/`)

**Target Platform**: Web application (Streamlit running on localhost:8502, deployed to AWS eventually)  

**Project Type**: Web application (Python backend + Streamlit frontend, single repo)  

**Performance Goals**: 
- Search response time: <10s p95 for semantic queries
- Concurrent users: 50 without degradation
- Image preview load: <3s p95
- Fallback activation: <2s when NV-CLIP unavailable

**Constraints**: 
- AWS Bedrock required for Claude (already verified working)
- NVIDIA API key required for NV-CLIP embeddings
- Image files must be accessible from Streamlit server filesystem
- HIPAA compliance considerations for patient data (TBD on anonymization requirements)

**Scale/Scope**: 
- MIMIC-CXR dataset (~377k chest X-rays based on standard MIMIC-CXR)
- Current implementation: basic keyword search with no scoring
- Target: 5 user stories (P1-P3), focusing on P1 for MVP

## Constitution Check

*Based on `.specify/memory/constitution.md` - checking for complexity violations*

✅ **Single Project**: This is a feature enhancement within existing FHIR-AI-Hackathon-Kit project  
✅ **No New Architecture**: Extending existing MCP server + Streamlit pattern  
✅ **Minimal Dependencies**: Reusing existing NV-CLIP, IRIS, Streamlit stack  
✅ **Clear Testing Strategy**: Leveraging existing pytest + Playwright setup

**No violations** - proceeding without justification table.

## Project Structure

### Documentation (this feature)

```text
specs/004-medical-image-search-v2/
├── spec.md              # Feature specification (already created)
├── plan.md              # This file (implementation plan)
├── research.md          # Phase 0: Technical research on NV-CLIP scoring, caching strategies
├── data-model.md        # Phase 1: ImageSearchResult schema, filter parameter design
├── quickstart.md        # Phase 1: Setup guide for NV-CLIP API key, testing locally
├── contracts/           # Phase 1: API contracts for search_medical_images tool
│   ├── search-request.json
│   ├── search-response.json
│   └── filter-schema.json
└── tasks.md             # Phase 2: Detailed task breakdown (created by /speckit.tasks command)
```

### Source Code (repository root)

```text
# Existing structure - feature adds to these directories

mcp-server/
├── fhir_graphrag_mcp_server.py    # MODIFY: Enhance search_medical_images tool
├── streamlit_app.py                # MODIFY: Add filtering UI, score display, image preview
└── (new) image_search_service.py   # ADD: Encapsulate search logic, caching

src/
├── embeddings/
│   └── nvclip_embeddings.py        # EXISTING: Already integrated, may need .embed_text() method
├── (new) search/
│   ├── __init__.py
│   ├── filters.py                  # ADD: Filter models (ViewPositionFilter, DateRangeFilter)
│   ├── scoring.py                  # ADD: Similarity score utilities, color coding
│   └── cache.py                    # ADD: Query embedding cache (in-memory LRU or Redis)
└── (new) fhir/
    └── clinical_context.py         # ADD: Fetch clinical notes for image IDs

tests/
├── unit/
│   ├── test_image_search_service.py    # ADD: Unit tests for search logic
│   ├── test_filters.py                  # ADD: Filter validation tests
│   └── test_scoring.py                  # ADD: Scoring calculation tests
├── integration/
│   └── test_nvclip_search_integration.py  # ADD: End-to-end NV-CLIP search test
└── e2e/
    └── test_streamlit_image_search.py    # ADD: Playwright tests for UI filters, preview

specs/004-medical-image-search-v2/
└── (documentation as shown above)
```

**Structure Decision**: 
- Using existing **single project structure** (not splitting frontend/backend) since Streamlit serves as both
- New modules organized under `src/search/` and `src/fhir/` to separate concerns
- MCP server (`mcp-server/fhir_graphrag_mcp_server.py`) remains the API layer, new service layer (`image_search_service.py`) handles business logic
- Streamlit app (`mcp-server/streamlit_app.py`) remains the presentation layer with enhanced UI components

## Implementation Phases

### Phase 0: Research & Technical Validation

**Goal**: Validate technical approach for P1 user story (semantic search with scoring)

**Deliverables**: `research.md` documenting:
1. **NV-CLIP Scoring**: 
   - Confirm `.embed_text()` method exists in `NVCLIPEmbeddings` (or add it)
   - Test cosine similarity calculation with sample queries
   - Establish score thresholds (≥0.7 strong, 0.5-0.7 moderate, <0.5 weak)

2. **Caching Strategy**:
   - Evaluate Python `functools.lru_cache` for embedding cache
   - Test cache hit rates with common medical queries
   - Determine cache size (start with 1000 queries)

3. **Image Path Validation**:
   - Verify if image paths in `VectorSearch.MIMICCXRImages` are accessible from Streamlit
   - Test file existence checks for first 100 images
   - Document fallback strategy for missing files

4. **FHIR Integration**:
   - Query `SQLUser.FHIRDocuments` to find clinical notes linked to image StudyIDs/SubjectIDs
   - Test JOIN query performance
   - Validate clinical note decoding (hex → UTF-8)

**Acceptance**: All 4 research items documented with code samples, performance metrics, and go/no-go decisions

---

### Phase 1: Design & Contracts

**Goal**: Define data models, API contracts, and UI mockups for P1

**Deliverables**:

1. **`data-model.md`**:
   - `ImageSearchQuery` model (query text, filters, pagination)
   - `ImageSearchResult` model (image metadata + similarity_score + clinical_note)
   - `SimilarityScore` model (value 0-1, confidence_level enum, color_code)
   - Filter models (ViewPositionFilter, DateRangeFilter, ScoreThresholdFilter)

2. **`contracts/`** (JSON schemas):
   - `search-request.json`: MCP tool input schema
   - `search-response.json`: MCP tool output schema with scores
   - `filter-schema.json`: Supported filter parameters

3. **UI Mockups** (embedded in `quickstart.md`):
   - Wireframe: Search bar + filter sidebar + results grid
   - Result card: Thumbnail + score badge + view position + patient ID
   - Score visualization: Color-coded badges (green/yellow/gray)

4. **`quickstart.md`**:
   - Setup instructions for NVIDIA_API_KEY
   - Test query examples
   - Expected response format with scores

**Acceptance**: All schemas validated with `jsonschema`, UI mockups reviewed, quickstart tested by team member

---

### Phase 2: Implementation (P1 Only - Semantic Search with Scoring)

**Goal**: Build working P1 user story - semantic search with relevance scores

**Task Breakdown** (to be created in `tasks.md` via `/speckit.tasks`):

#### Backend Tasks:
1. Extend `NVCLIPEmbeddings.embed_text()` method (if not exists)
2. Create `src/search/scoring.py` with `calculate_similarity`, `get_score_color`, `get_confidence_level`
3. Create `src/search/cache.py` with `@lru_cache` wrapper for embeddings
4. Update `fhir_graphrag_mcp_server.py`:
   - Modify `search_medical_images` tool to expose similarity scores in response
   - Add score threshold filtering (optional param: `min_score`)
5. Add unit tests for scoring module

#### Frontend Tasks:
6. Update `streamlit_app.py` `render_chart()` for `search_medical_images`:
   - Display similarity score badges on each image
   - Color-code badges based on score ranges
   - Show score value as tooltip
7. Add image grid layout (3-column)
8. Add fallback message when NV-CLIP unavailable
9. Add Playwright test for score display

**Acceptance**: 
- E2E test passes: search "pneumonia" → see results with scores ≥0.5
- Fallback test passes: mock NV-CLIP failure → see keyword results + warning
- Unit tests: 100% coverage for scoring module

---

### Phase 3: Implementation (P2 - Filters & Clinical Context)

*Deferred to `tasks.md` after P1 completion*

---

### Phase 4: Implementation (P3 - Export & History)

*Deferred to future iterations*

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Image files not accessible from Streamlit | Medium | High | Phase 0 research validates paths; implement file existence checks with clear error messages |
| NV-CLIP API rate limiting | Low | Medium | Implement request throttling (max 10/sec), cache aggressively |
| Low similarity scores for valid queries | Medium | Medium | Phase 0 establishes realistic thresholds; log queries with scores <0.3 for analysis |
| FHIR notes missing for images | High | Low | Handle gracefully - display "No clinical notes available" instead of failing |
| Performance degradation with 377k images | Low | High | Vector search with IRIS is optimized for this; add pagination (already planned) |

## Success Metrics (aligned with spec)

**Phase 2 (P1) Targets**:
- Search response time: <10s for 95% of queries
- Top-5 results with scores ≥0.6 for 80% of test queries (20-query test suite)
- Fallback activation: <2s when NV-CLIP fails
- Zero exceptions for valid queries

**Measurement**:
- Add logging to `search_medical_images` tool (query, result count, scores, execution time)
- Collect metrics for 100 real user queries
- Weekly review of logs to identify low-scoring queries

## Next Steps (Immediate)

1. ✅ Create feature branch: `004-medical-image-search-v2`
2. ✅ Create spec directory structure
3. ⬜ Run Phase 0 research (create `research.md`)
4. ⬜ Design data models (create `data-model.md`)
5. ⬜ Define API contracts (create `contracts/*.json`)
6. ⬜ Create quickstart (create `quickstart.md`)
7. ⬜ Run `/speckit.tasks` to generate detailed task breakdown
8. ⬜ Begin P1 implementation

**Ready to proceed with Phase 0 research?**
