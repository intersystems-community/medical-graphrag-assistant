# Tasks: Enhanced Medical Image Search

**Input**: Design documents from `/specs/004-medical-image-search-v2/`
**Prerequisites**: ✅ plan.md, ✅ spec.md, ✅ research.md, ✅ C1-C3-INVESTIGATION.md

**Scope**: Phase 2 (P1 Implementation) - Semantic Search with Scoring
**Tests**: Included per specification requirements (pytest + Playwright)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[US1]**: User Story 1 (Semantic Search with Relevance Scoring)

---

## Phase 1: Setup & Infrastructure

**Purpose**: Project initialization and shared infrastructure before P1 implementation

- [ ] **T001** [P] Create `src/search/` module structure (`__init__.py`, `scoring.py`, `cache.py`, `filters.py`)
- [ ] **T002** [P] Create `src/db/` module structure (`__init__.py`, `connection.py`)
- [ ] **T003** [P] Create `tests/unit/search/` directory for search module tests
- [ ] **T004** [P] Create `tests/e2e/` directory structure for Playwright tests (already exists, verify)
- [ ] **T005** Add dependencies to `requirements.txt`: `functools` (built-in), `pytest-cov` for coverage

---

## Phase 2: Foundational (Critical Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before US1 implementation

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] **T006** Create database connection module in `src/db/connection.py`:
  - Environment variable support (`IRIS_HOST`, `IRIS_PORT`, `IRIS_NAMESPACE`, `IRIS_USERNAME`, `IRIS_PASSWORD`)
  - `get_connection()` function using env vars with defaults
  - Auto-detect dev (`localhost:32782`) vs prod (`3.84.250.46:1972`)
  - Document usage in docstring

- [ ] **T007** Update `mcp-server/fhir_graphrag_mcp_server.py`:
  - Replace hard-coded `AWS_CONFIG` with `from src.db.connection import get_connection`
  - Test connection to local IRIS (`localhost:32782/DEMO`)
  - Verify existing tools still work

- [ ] **T008** [P] Update `.env` file (or create if missing):
  - Add `IRIS_HOST=localhost` 
  - Add `IRIS_PORT=32782`
  - Add `IRIS_NAMESPACE=DEMO`
  - Add `IRIS_USERNAME=_SYSTEM`
  - Add `IRIS_PASSWORD=ISCDEMO`
  - Document prod values in comments

- [ ] **T009** [P] Create `.env.example` template:
  - Copy structure from `.env` with placeholder values
  - Document which vars are required vs optional
  - Add to git (safe for sharing, no secrets)

**Checkpoint**: Foundation ready - database connection abstracted, environment configured

---

## Phase 3: User Story 1 - Semantic Search with Relevance Scoring (Priority: P1) 🎯 MVP

**Goal**: Users can search for chest X-rays using natural language and see similarity scores for each result

**Independent Test**: Search "chest X-ray showing pneumonia" → see results with scores ≥0.5, color-coded badges

### Tests for User Story 1 (TDD - Write First)

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] **T010** [P] [US1] Unit test `src/search/scoring.py` in `tests/unit/search/test_scoring.py`:
  - Test `calculate_similarity(emb1, emb2)` returns float 0-1
  - Test `get_score_color(score)` returns 'green'/'yellow'/'gray'
  - Test `get_confidence_level(score)` returns 'strong'/'moderate'/'weak'
  - Mock numpy arrays for embeddings

- [ ] **T011** [P] [US1] Unit test `src/search/cache.py` in `tests/unit/search/test_cache.py`:
  - Test `@cached_embedding` decorator caches results
  - Test cache hit for identical queries
  - Test cache miss for new queries
  - Verify LRU eviction behavior

- [ ] **T012** [US1] Integration test `mcp-server/fhir_graphrag_mcp_server.py` `search_medical_images` tool in `tests/integration/test_nvclip_search_integration.py`:
  - Mock IRIS database connection
  - Mock NV-CLIP embedder with sample vectors
  - Test query "pneumonia" returns images with scores
  - Test response includes `similarity_score` field
  - Test fallback to keyword search when embedder unavailable

- [ ] **T013** [US1] E2E Playwright test in `tests/e2e/test_streamlit_image_search.py`:
  - Navigate to Streamlit app at `localhost:8502`
  - Enter query "chest X-ray"
  - Click search (or detect tool execution)
  - Verify image results display
  - Verify similarity score badges visible
  - Verify score color coding (green/yellow/gray)

### Implementation for User Story 1

#### Backend Tasks

- [ ] **T014** [P] [US1] Create `src/search/scoring.py`:
  ```python
  def calculate_similarity(embedding1: List[float], embedding2: List[float]) -> float:
      """Calculate cosine similarity between two embeddings."""
      # Use numpy for cosine similarity
      # Return float 0-1
  
  def get_score_color(score: float) -> str:
      """Get color code for similarity score."""
      # ≥0.7 = 'green', 0.5-0.7 = 'yellow', <0.5 = 'gray'
  
  def get_confidence_level(score: float) -> str:
      """Get confidence level label."""
      # ≥0.7 = 'strong', 0.5-0.7 = 'moderate', <0.5 = 'weak'
  ```

- [ ] **T015** [P] [US1] Create `src/search/cache.py`:
  ```python
  from functools import lru_cache
  
  @lru_cache(maxsize=1000)
  def cached_embedding(query_text: str) -> tuple:
      """Cache text embeddings with LRU eviction."""
      # Call embedder.embed_text(query_text)
      # Return tuple (hashable) instead of list
  ```

- [ ] **T016** [US1] Update `mcp-server/fhir_graphrag_mcp_server.py` - Modify `search_medical_images` tool (lines ~1030-1097):
  - Import `from src.search.scoring import calculate_similarity, get_score_color, get_confidence_level`
  - Import `from src.search.cache import cached_embedding`
  - Add `min_score` parameter to tool input schema (optional, default 0.0)
  - In semantic search branch:
    - Use `cached_embedding(query)` instead of direct `emb.embed_text(query)`
    - After `VECTOR_COSINE()` query, add similarity score to each result:
      ```python
      for row in cursor.fetchall():
          image_id, study_id, subject_id, view_pos, image_path, score = row
          results.append({
              "image_id": image_id, 
              "study_id": study_id,
              "subject_id": subject_id,
              "view_position": view_pos,
              "image_path": image_path,
              "similarity_score": float(score),
              "score_color": get_score_color(float(score)),
              "confidence_level": get_confidence_level(float(score))
          })
      ```
  - Filter results by `min_score` if provided
  - Sort by `similarity_score` descending

- [ ] **T017** [US1] Update SQL query in `search_medical_images`:
  - Change `SELECT ImageID, StudyID, SubjectID, ViewPosition, ImagePath`
  - To `SELECT ImageID, StudyID, SubjectID, ViewPosition, ImagePath, VECTOR_COSINE(Vector, TO_VECTOR(?, double)) AS similarity`
  - Add similarity score to cursor fetch

- [ ] **T018** [US1] Add error handling in `search_medical_images`:
  - Wrap NV-CLIP calls in try-except
  - On `ImportError` or `Exception`, set `emb = None` and log warning
  - Ensure fallback keyword search activates smoothly
  - Return `{"search_mode": "keyword", "reason": "NV-CLIP unavailable"}` in response

#### Frontend Tasks

- [ ] **T019** [P] [US1] Update `mcp-server/streamlit_app.py` - Modify `render_chart()` function for `search_medical_images` tool (lines ~360-386):
  - Extract `similarity_score` and `score_color` from each image result
  - Display score badge on each image card:
    ```python
    for idx, img in enumerate(images):
        with cols[idx % 3]:
            # Existing image display code
            score = img.get("similarity_score", 0.0)
            color = img.get("score_color", "gray")
            
            # Add score badge
            st.markdown(
                f'<div style="background-color:{color}; padding:4px; border-radius:4px; text-align:center;">'
                f'Score: {score:.2f}</div>',
                unsafe_allow_html=True
            )
    ```
  - Add tooltip showing confidence level on hover (use `st.markdown` with `title` attribute)

- [ ] **T020** [US1] Add fallback warning in `mcp-server/streamlit_app.py` `render_chart()`:
  - Check if `data.get("search_mode") == "keyword"`
  - Display warning banner: `st.warning("⚠️ Semantic search unavailable. Using keyword search.")`
  - Show reason if provided: `st.info(f"Reason: {data.get('reason')}")`

- [ ] **T021** [US1] Update `mcp-server/streamlit_app.py` `demo_mode_search()` function (lines ~401-486):
  - For image search branch, add mock similarity scores to results:
    ```python
    images = data.get("images", [])
    # Add mock scores for demo mode
    for i, img in enumerate(images):
        img["similarity_score"] = 0.85 - (i * 0.05)  # Descending scores
        img["score_color"] = get_score_color(img["similarity_score"])
        img["confidence_level"] = get_confidence_level(img["similarity_score"])
    ```
  - Ensure demo mode renders scores like production mode

#### Documentation & Logging

- [ ] **T022** [US1] Add logging to `src/search/cache.py`:
  - Log cache hits vs misses
  - Log cache size periodically
  - Use `logging.info(f"Cache hit for query: {query_text[:50]}...")`

- [ ] **T023** [US1] Add logging to `mcp-server/fhir_graphrag_mcp_server.py` `search_medical_images`:
  - Log query text, search mode (semantic vs keyword), result count, execution time
  - Log score statistics (min, max, avg) for semantic searches
  - Use structured logging with timestamps:
    ```python
    import logging
    logging.info(f"ImageSearch: query='{query}' mode={search_mode} results={len(results)} avg_score={avg_score:.3f} time={elapsed:.2f}s")
    ```

- [ ] **T024** [US1] Update `specs/004-medical-image-search-v2/quickstart.md` (create if missing):
  - Document how to run US1 locally
  - Example query: `"chest X-ray showing pneumonia"`
  - Expected response format with scores
  - Troubleshooting guide for NV-CLIP issues

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: Validation & Refinement

**Purpose**: Validate US1 works as specified, tune parameters

- [ ] **T025** Run all US1 tests and verify they pass:
  - `pytest tests/unit/search/ -v --cov=src/search`
  - `pytest tests/integration/test_nvclip_search_integration.py -v`
  - `pytest tests/e2e/test_streamlit_image_search.py -v` (requires Streamlit running)

- [ ] **T026** Manual testing with test queries:
  - Query: "chest X-ray showing pneumonia" → expect scores ≥0.6
  - Query: "bilateral lung infiltrates" → expect scores ≥0.5
  - Query: "cardiomegaly with effusion" → expect varied scores
  - Query: "normal chest radiograph" → expect different results than pathological

- [ ] **T027** Tune score thresholds based on real query results:
  - Review first 20 search results and scores
  - Adjust thresholds in `src/search/scoring.py` if needed:
    - If scores cluster low (0.3-0.5): lower thresholds
    - If scores cluster high (0.8-0.95): raise thresholds
  - Document final thresholds in `research.md`

- [ ] **T028** Verify fallback keyword search:
  - Stop NV-CLIP service or set invalid `NVIDIA_API_KEY`
  - Search "chest X-ray" → should see warning + keyword results
  - Verify no crashes, graceful degradation

- [ ] **T029** Performance testing:
  - Measure search latency for 10 queries (cold cache)
  - Measure search latency for 10 repeated queries (warm cache)
  - Verify p95 latency <10s (cold), <1s (warm)
  - Document in `research.md`

---

## Phase 5: Polish & Documentation

**Purpose**: Code cleanup, final documentation, prepare for demo

- [ ] **T030** [P] Code review and refactoring:
  - Extract magic numbers (0.7, 0.5 thresholds) to constants
  - Add type hints to all functions
  - Add docstrings to all public functions
  - Run `black` formatter on all modified files

- [ ] **T031** [P] Update README.md with US1 feature:
  - Add "Semantic Image Search" section
  - Screenshot of score badges (use `generate_image` tool)
  - Link to quickstart guide

- [ ] **T032** Git commit best practices:
  - Commit T014-T015 (scoring + cache modules) as "feat: add scoring and caching modules for semantic search"
  - Commit T016-T018 (MCP server changes) as "feat: enhance search_medical_images with similarity scoring"
  - Commit T019-T021 (Streamlit UI) as "feat: display similarity scores in Streamlit UI"
  - Commit T022-T024 (logging + docs) as "docs: add logging and quickstart for image search"

- [ ] **T033** Update `specs/004-medical-image-search-v2/research.md`:
  - Add final score thresholds decided
  - Add performance metrics from T029
  - Add cache hit rate statistics
  - Mark as "COMPLETE - Phase 0 & P1"

- [ ] **T034** Create demo video (optional):
  - Use browser agent to record search workflow
  - Show search query → results with scores → score explanation
  - Save to `~/.gemini/antigravity/brain/*/demo_image_search.webp`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Phase 2 completion
- **Validation (Phase 4)**: Depends on Phase 3 implementation
- **Polish (Phase 5)**: Depends on Phase 4 validation passing

### Within User Story 1 (Phase 3)

**Test-Driven Development Order**:
1. T010-T013 (Tests) FIRST - ensure they FAIL
2. T014-T015 (Backend modules) - make T010-T011 pass
3. T016-T018 (MCP server) - make T012 pass
4. T019-T021 (Streamlit UI) - make T013 pass
5. T022-T024 (Logging + docs) - parallel with above

**Backend Dependencies**:
- T014 (scoring.py) ← Must exist before T016 (MCP server uses it)
- T015 (cache.py) ← Must exist before T016 (MCP server uses it)
- T016 (MCP tool update) ← Depends on T014, T015
- T017 (SQL query) ← Part of T016
- T018 (Error handling) ← Part of T016

**Frontend Dependencies**:
- T019 (render scores) ← Depends on T016 (MCP returns scores)
- T020 (fallback warning) ← Depends on T018 (error structure)
- T021 (demo mode) ← Depends on T014 (score functions)

### Parallel Opportunities

**Phase 1 (Setup)**: All T001-T005 can run in parallel

**Phase 2 (Foundational)**:
- T006 (connection.py) in parallel with T008-T009 (env vars)
- T007 (update MCP server) must wait for T006

**Phase 3 (US1)**:
- **Tests** (T010-T013): All can run in parallel (write tests first)
- **Backend modules** (T014-T015): Can run in parallel
- **Backend integration** (T016-T018): Sequential (depends on T014-T015)
- **Frontend** (T019-T021): Can run in parallel AFTER T016 completes
- **Docs** (T022-T024): Can run in parallel with frontend

**Phase 5 (Polish)**: T030-T031 can run in parallel

---

## Implementation Strategy

### MVP First (User Story 1 Only - Recommended)

```bash
# Week 1: Foundation
Day 1: T001-T005 (Setup) → 2 hours
Day 2: T006-T009 (Foundational) → 4 hours  
Day 3: Test foundation works → 1 hour

# Week 2: US1 Implementation
Day 4: T010-T013 (Write failing tests) → 4 hours
Day 5: T014-T015 (Backend modules) → 3 hours
Day 6: T016-T018 (MCP server) → 5 hours
Day 7: T019-T021 (Streamlit UI) → 4 hours

# Week 3: Validation
Day 8: T025-T029 (Testing & tuning) → 6 hours
Day 9: T030-T034 (Polish & docs) → 4 hours
Day 10: Final demo & review → 2 hours
```

**Total Estimated Time**: ~35 hours for P1 MVP

### Success Criteria Checklist

After completing Phase 4, verify:

- [ ] ✅ Search "chest X-ray showing pneumonia" returns results in <10s
- [ ] ✅ Top-5 results have similarity scores ≥0.6 for 80% of test queries
- [ ] ✅ Similarity scores display as color-coded badges in Streamlit UI
- [ ] ✅ Fallback keyword search activates within 2s when NV-CLIP fails
- [ ] ✅ All unit tests pass with 90%+ coverage
- [ ] ✅ Integration test passes
- [ ] ✅ E2E Playwright test passes

---

## Notes

- **[P] tasks**: Different files, can run in parallel with team
- **[US1] label**: Maps task to User Story 1 for traceability
- **Test-First**: Write failing tests before implementation (T010-T013)
- **Checkpoint**: After Phase 3, US1 should work independently - STOP and validate
- **Commit often**: After each task or logical group (T032)
- **Environment**: Use local IRIS (`localhost:32782`) per C2 resolution
- **Image paths**: Use relative paths from database per C1 resolution
- **FHIR notes**: Deferred to Phase 2 (P2) per plan

---

## Next Steps After P1 Completion

If P1 MVP is successful and validated:

1. **Demo US1** to stakeholders
2. **Gather feedback** on score thresholds and UX
3. **Decide on P2** (Filters & Clinical Context) or iterate on P1
4. **Deploy US1** to production if ready
5. **Update plan.md** with lessons learned

**Ready to start Phase 1 (Setup)?** 🚀
