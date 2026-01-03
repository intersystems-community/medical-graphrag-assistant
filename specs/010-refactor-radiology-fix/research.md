# Research: Pragmatic Refactor and Radiology Fix

## Decision: Leverage `FHIRGraphRAGQuery` for Service Layer
- **Rationale**: `src/query/fhir_graphrag_query.py` already contains a class-based implementation of the RRF fusion and search logic. Instead of reinventing it, we should refactor this class into the `src/search/` package to be the core of our service layer.
- **Alternatives considered**: Writing new functional search modules. Rejected because the class-based approach in `src/query/` is already well-tested and structured.

## Decision: Extend `HealthCheckResult` in `src.validation.health_checks`
- **Rationale**: The existing `health_checks.py` has a clean `HealthCheckResult` dataclass and infrastructure for running checks. Adding a `schema_check()` function is more consistent than creating a new validation module.
- **Alternatives considered**: New CLI-specific health logic. Rejected for consistency.

## Decision: Pragmatic Refactor of `fhir_graphrag_mcp_server.py`
- **Rationale**: The file is 2000+ lines. A full rewrite would be too risky and token-expensive. We will focus only on refactoring the `search_fhir_documents`, `search_knowledge_graph`, and `hybrid_search` tool implementations to call the new service layer.
- **Alternatives considered**: Splitting the MCP server into multiple files. Rejected to keep changes minimal and "pragmatic" as per user request.
