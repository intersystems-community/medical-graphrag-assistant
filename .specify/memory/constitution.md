# Medical GraphRAG Assistant Constitution

## Core Principles

### I. IRIS-Native
The system MUST prioritize InterSystems IRIS native features (SQL, Vector Search, Graph traversals) over external logic. Database logic MUST be parameterized to prevent injection.

### II. Agent-Centric Design
All features MUST be exposed via the Model Context Protocol (MCP) as tools. Tools MUST return structured JSON to ensure predictable LLM consumption.

### III. Medical Data Integrity
The system MUST respect FHIR R4 resource structures. Clinical data retrieved via tools MUST be verifiable against the source IRIS database.

### IV. Observability & Memory
Agent corrections and preferences MUST be persisted in the semantic memory system. Every search execution MUST log its retrieval strategy (e.g., RRF scores) for transparency.

### V. Browser-First Verification
UX features MUST be verified via browser automation (Playwright) to ensure the Streamlit frontend correctly renders complex reactive visualizations.

## Governance
All implementation tasks must verify compliance with these principles. Complexity must be justified in the feature plan.

**Version**: 1.0.0 | **Ratified**: 2026-01-02
