# Quickstart: Fixing Test Failures

Follow these steps to resolve the 16 remaining test failures.

## 1. Verify Connectivity
Ensure the EC2 IRIS instance is reachable:
```bash
ssh -i ~/.ssh/fhir-ai-key-recovery.pem ubuntu@44.200.206.67 'docker ps'
```

## 2. Run Tests
Run only the failing tests to see the current state:
```bash
# RAG Pipeline failures (12)
pytest tests/integration/test_end_to_end_rag.py -v

# Vectorization failures (2)
pytest tests/integration/test_vectorization_pipeline.py -v

# MCP Async failures (2)
pytest tests/unit/mcp/test_tool_wrappers.py -v
```

## 3. Apply Fixes
Follow the detailed guide in `FIXME.md`. The primary tasks are:
- Updating import paths to use `src.` prefix.
- Adding default values to `os.getenv()` in `src/query/rag_pipeline.py`.
- Adding `@pytest.mark.asyncio` and `await` to MCP tool tests.
- Switching legacy `iris` module calls to `intersystems-irispython` patterns.

## 4. Final Verification
Run all tests (excluding UX tests that require a running browser):
```bash
pytest tests/ --ignore=tests/ux -v
```
Target: **220+ passed, 0 failed.**
