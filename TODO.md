# TODO: Medical GraphRAG Assistant

**Last Updated**: November 22, 2025
**Current Version**: v2.12.0

---

## Current Sprint ✅ COMPLETE

### Documentation Review & Cleanup (November 22, 2025)
- [x] Clean up root directory (moved to archive/)
- [x] Review and update README.md with v2.12.0 features
- [x] Create STATUS.md with current system state
- [x] Update TODO.md to reflect actual priorities
- [x] Organize historical documentation

---

## High Priority 🔴

### Production Operations
- [ ] Set up automated health monitoring for AWS deployment
  - Cron job for database health checks
  - Alert on embedding failures
  - Monitor GPU utilization
  - Track query performance

- [ ] Expand Agent Memory Dataset
  - Let agent accumulate memories through conversations
  - Test semantic recall with larger dataset (50+ memories)
  - Evaluate memory search quality

- [ ] Medical Image Dataset Expansion
  - Download and ingest additional MIMIC-CXR images
  - Current: 50 images → Target: 1000+ images
  - Test search quality at scale

### GraphRAG Improvements
- [ ] Enhanced entity extraction with NIM LLM
  - Replace regex-based extraction with LLM-powered extraction
  - Deploy NVIDIA NIM LLM container on AWS
  - Improve entity relationship detection

- [ ] Multi-hop reasoning
  - Implement graph traversal for complex queries
  - Support queries like "medications that treat conditions caused by X"

---

## Medium Priority 🟡

### Testing & Quality
- [ ] Add unit tests for new v2.12.0 features
  - Memory system tests
  - Medical image search tests
  - Embeddings quality tests

- [ ] Performance benchmarking at scale
  - Test with 1000+ images
  - Test with 100+ memories
  - Measure query latency under load

### Documentation
- [ ] Create end-user documentation
  - "Getting Started" guide for medical professionals
  - Example queries with expected outputs
  - Troubleshooting common user issues

- [ ] API documentation
  - MCP tool specifications
  - Configuration options
  - Deployment guide for other AWS regions

---

## Low Priority ⚪

### Code Quality
- [ ] Add type hints to all functions
- [ ] Comprehensive docstrings for all modules
- [ ] Code coverage analysis

### Features (Nice to Have)
- [ ] Export conversation history
- [ ] Batch image upload via UI
- [ ] Custom memory tags/categories
- [ ] GraphRAG visualization in UI

---

## Completed (Recent) ✅

### v2.12.0: Agent Memory & Medical Image Search (November 22, 2025)
- [x] Pure IRIS vector memory system (no SQLite)
- [x] Medical image search with NV-CLIP embeddings
- [x] Memory editor UI in Streamlit sidebar
- [x] Fixed embeddings (real NV-CLIP vectors, not mocks)
- [x] Memory search UI session state persistence
- [x] Empty search string support (browse all memories)
- [x] Type conversion for similarity scores

### Infrastructure & Deployment
- [x] AWS EC2 g5.xlarge deployment
- [x] NVIDIA NIM NV-CLIP integration (port 8002)
- [x] IRIS database with vector tables
- [x] GraphRAG knowledge graph (83 entities, 540 relationships)
- [x] SSH tunnel setup for local development

### GraphRAG Implementation
- [x] Direct FHIR table integration (no SQL Builder)
- [x] Companion vector table pattern
- [x] Medical entity extraction (6 types)
- [x] Relationship mapping
- [x] Multi-modal search with RRF fusion
- [x] Integration tests (13/13 passing)

---

## Deferred / Not Planned ⏸️

### Large-Scale Dataset (Blocked: PhysioNet Access)
- ⏸️ MIMIC-CXR full dataset (377K images)
  - Requires PhysioNet credentialed access
  - May take days/weeks to obtain
  - Can proceed with current 50 images for development

### Performance Optimization
- ⏸️ Batch processing for entity extraction
- ⏸️ Parallel extraction with workers
- ⏸️ Additional query performance tuning
  - Current performance acceptable (0.006s - 0.242s queries)
  - Optimize only when scale demands it

### Licensed IRIS Upgrade
- ⏸️ Upgrade from Community to Licensed IRIS
  - ACORN=1 HNSW optimization (10-50x faster vector search)
  - Deferred to production deployment phase
  - Current performance sufficient for development

---

## Feedback Items (For Upstream Projects)

### FHIR-AI-Hackathon-Kit Tutorial Feedback
**Status**: Documented in archive/docs/FEEDBACK_SUMMARY.md

**Tutorial 2 Issues**:
- Remove unused `import base64`
- Add explanation about Utils module location
- Add `DROP TABLE IF EXISTS` pattern
- Fix naming inconsistency: "Notes_Vector" vs "NotesVector"

**Tutorial 3 Issues**:
- Fix SQL injection vulnerability in vector_search function
- Add error handling for when Ollama isn't running
- Add clear instructions to pull gemma3 model
- Clarify which model to use (gemma3:1b vs gemma3:4b)

### iris-vector-rag Improvements
**Status**: Tested v0.5.2-v0.5.4, feedback documented

- ✅ ConfigurationManager works excellently
- ✅ Environment variable support functional
- ⚠️ ConnectionManager ignores config (uses legacy IRIS_* env vars)
- ⚠️ SchemaManager dot/colon notation mismatch
- ✅ v0.5.4 connection bug fixed

---

## Notes & Context

### Current System State
- **Version**: v2.12.0
- **AWS Deployment**: ✅ Operational
- **Local Development**: ✅ Active (via SSH tunnel)
- **Integration Tests**: 13/13 passing
- **Data Scale**: 51 documents, 50 images, 83 entities, ~5 memories

### Performance Benchmarks
- Vector search: 1.038s (30 results)
- Text search: 0.018s (23 results)
- Graph search: 0.014s (9 results)
- Full multi-modal: 0.242s
- Fast query: 0.006s

### Technical Debt
- Minimal - codebase is clean after recent refactoring
- Archive directory contains historical implementations
- Configuration could be more unified (YAML + env vars)

---

## References

- **STATUS.md**: Current system health and metrics
- **PROGRESS.md**: Development history (1400+ lines, consider archiving old content)
- **README.md**: Main project documentation (updated v2.12.0)
- **docs/**: Architecture, deployment, troubleshooting guides
- **archive/**: Historical implementations and session docs
