# Research: Address remaining test failures and LSP errors

## Decision: Import Path Normalization
- **Choice**: Use `src.` prefix for all internal module imports in test files.
- **Rationale**: Ensures consistency and avoids `ModuleNotFoundError` when running pytest from the project root.
- **Alternatives considered**: Adding subdirectories to `PYTHONPATH` (rejected as it's less explicit and harder to maintain across environments).

## Decision: Environment Variable Defaults
- **Choice**: Hardcode EC2 IP `44.200.206.67` as the fallback default in `RAGPipeline` and tests.
- **Rationale**: Provides a "works out of the box" experience for developers without requiring complex environment setup for every run.
- **Alternatives considered**: Requiring a `.env` file (rejected for simplicity in this specific "fix-it" phase).

## Decision: Async Test Handling
- **Choice**: Use `@pytest.mark.asyncio` and `await` for all MCP tool wrapper tests.
- **Rationale**: `asyncio.get_event_loop().run_until_complete()` is deprecated or causes issues with modern pytest-asyncio versions.
- **Alternatives considered**: None, this is the standard modern practice.

## Decision: Radiology Test Strategy
- **Choice**: Rewrite skipped radiology e2e tests to use direct IRIS SQL queries.
- **Rationale**: Pragmatic choice given the absence of a configured FHIR REST server on the EC2 instance and the existing reliance on IRIS SQL for other data types.
- **Alternatives considered**: Configuring the FHIR server (too complex for current scope).
