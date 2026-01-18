# FIXME.md - Detailed Fix Plan for Junior Developers

**Current Test Status**: 204 passed, 16 failed, 44 skipped

This document provides step-by-step instructions to fix the remaining test failures.

---

## Quick Reference

```bash
# Run all tests against EC2
pytest tests/ --ignore=tests/ux -v

# Environment is auto-configured via tests/conftest.py
# Default: EC2 IP 44.200.206.67, IRIS port 1972, namespace USER
```

---

## FAILURE GROUP 1: RAG Pipeline Tests (12 failures)

**Files**: `tests/integration/test_end_to_end_rag.py`

**Root Cause**: Import path issue - tests import `from query.rag_pipeline` but module is at `src.query.rag_pipeline`

### Fix Steps:

1. Open `tests/integration/test_end_to_end_rag.py`
2. Find line ~33: `from query.rag_pipeline import RAGPipeline`
3. Change to: `from src.query.rag_pipeline import RAGPipeline`
4. Verify fix: `python -c "from src.query.rag_pipeline import RAGPipeline; print('OK')"`

**Additional Issue**: `src/query/rag_pipeline.py` has type errors (lines 72-78) where `None` is passed to parameters expecting `str`. These are likely environment variable defaults.

5. Open `src/query/rag_pipeline.py`
6. Find the initialization around line 72-78
7. Replace `os.getenv("VAR")` with `os.getenv("VAR", "default_value")` for each parameter
8. Example fix:
   ```python
   # Before
   hostname=os.getenv("IRIS_HOST"),
   # After  
   hostname=os.getenv("IRIS_HOST", "44.200.206.67"),
   ```

---

## FAILURE GROUP 2: Vectorization Pipeline Tests (2 failures)

**Files**: `tests/integration/test_vectorization_pipeline.py`

**Root Cause**: Tests need NVIDIA NIM embeddings endpoint to generate vectors

### Fix Steps:

1. Ensure NV-CLIP is running on EC2:
   ```bash
   ssh -i ~/.ssh/fhir-ai-key-recovery.pem ubuntu@44.200.206.67 'docker ps | grep nvclip'
   ```

2. If not running, start it:
   ```bash
   ssh -i ~/.ssh/fhir-ai-key-recovery.pem ubuntu@44.200.206.67 'docker start nim-nvclip'
   ```

3. Verify endpoint works:
   ```bash
   curl http://44.200.206.67:8002/v1/health
   ```

4. If tests still fail, check `tests/integration/test_vectorization_pipeline.py` imports:
   - Line 32-34 imports from `vectorization.*` should be `src.vectorization.*`

---

## FAILURE GROUP 3: MCP Tool Wrapper Tests (2 failures)

**Files**: `tests/unit/mcp/test_tool_wrappers.py`

**Root Cause**: Async test framework issues - tests are async but not properly awaited

### Fix Steps:

1. Open `tests/unit/mcp/test_tool_wrappers.py`

2. Check if tests have `@pytest.mark.asyncio` decorator:
   ```python
   @pytest.mark.asyncio
   async def test_search_fhir_documents_wrapper():
   ```

3. If missing `async` keyword, add it to test function signature

4. If tests use `asyncio.get_event_loop().run_until_complete()`, replace with:
   ```python
   # Before
   result = asyncio.get_event_loop().run_until_complete(call_tool(...))
   
   # After
   result = await call_tool(...)
   ```

5. Ensure `pytest-asyncio` is in requirements:
   ```bash
   pip install pytest-asyncio
   ```

---

## FAILURE GROUP 4: Skipped Radiology E2E Tests (21 skipped)

**Files**: `tests/e2e/test_radiology_mcp_tools.py`

**Root Cause**: Tests require FHIR REST API endpoint which is NOT enabled on EC2

### Options:

**Option A: Skip these tests permanently** (recommended for now)
- These tests are already skipping gracefully
- FHIR REST API requires HealthShare license/setup

**Option B: Enable FHIR REST API on EC2** (complex)
1. SSH to EC2
2. Enable FHIR server in IRIS:
   ```
   docker exec -it iris-fhir iris session iris
   // In IRIS terminal:
   do ##class(HS.FHIRServer.Installer).InstallNamespace(...)
   ```
3. Configure endpoint at `/fhir/r4`
4. This requires significant IRIS HealthShare configuration

**Option C: Rewrite tests to use IRIS SQL instead of FHIR REST**
- Modify tests to query `SQLUser.ClinicalNoteVectors` or `SQLUser.MedicalImageVectors` directly
- **CRITICAL**: Use a transformation layer in the adapter to ensure SQL results are returned as valid FHIR R4 JSON structures. This maintains the contract with the agent even in SQL Fallback mode.

---

## FAILURE GROUP 5: LSP Type Errors (not test failures, but should fix)

### File: `src/vectorization/vector_db_client.py`

**Issue**: Type checker can't verify `self.cursor` isn't None

**Fix**: Add type guard or assertion after connect():
```python
def connect(self) -> None:
    # ... existing code ...
    self.cursor = self.connection.cursor()
    assert self.cursor is not None  # Type guard
```

### File: `src/setup/reset_fhir_security.py`

**Issue**: Uses `iris.createIRIS()` and `iris.IRISReference` which don't exist in `intersystems-irispython`

**Fix**: This file uses wrong IRIS API. Should use:
```python
# Instead of iris.createIRIS()
from src.db.connection import DatabaseConnection
conn = DatabaseConnection.get_connection(...)
```

---

## Verification Checklist

After making fixes, run these commands:

```bash
# 1. Syntax check
python -c "from src.query.rag_pipeline import RAGPipeline; print('RAG OK')"
python -c "from src.vectorization.text_vectorizer import ClinicalNoteVectorizer; print('Vectorizer OK')"

# 2. Quick test subset
pytest tests/integration/test_fhir_radiology.py -v  # Should be 12 passed

# 3. Full test run
pytest tests/ --ignore=tests/ux -q

# 4. Check EC2 connectivity
ssh -i ~/.ssh/fhir-ai-key-recovery.pem ubuntu@44.200.206.67 'docker ps'
```

---

## Files to Review

| File | Issue | Priority |
|------|-------|----------|
| `tests/integration/test_end_to_end_rag.py:33` | Wrong import path | HIGH |
| `src/query/rag_pipeline.py:72-78` | None passed to str params | HIGH |
| `tests/integration/test_vectorization_pipeline.py:32-34` | Wrong import path | HIGH |
| `tests/unit/mcp/test_tool_wrappers.py` | Async test issues | MEDIUM |
| `src/setup/reset_fhir_security.py` | Wrong IRIS API | LOW |
| `src/vectorization/vector_db_client.py` | Type hints | LOW |

---

## EC2 Infrastructure Notes

- **SSH**: `ssh -i ~/.ssh/fhir-ai-key-recovery.pem ubuntu@44.200.206.67`
- **IRIS SQL Port**: 1972
- **NV-CLIP Port**: 8002
- **Tables exist in**: `SQLUser.*` and `VectorSearch.*` schemas
- **See OPS.md** for full operational details

---

## When Tests Pass

Target: **220+ passed, 0 failed, ~20 skipped**

The skipped tests are acceptable - they require:
- FHIR REST API (not set up)
- Specific DICOM test files (not in repo)
- Running Streamlit server (TARGET_URL)
