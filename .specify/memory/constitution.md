<!--
Sync Impact Report
==================
Version change: 1.0.0 → 1.1.0
Added sections:
  - Principle VI: Test-Driven Development & UX Testing
Modified principles: None
Removed sections: None
Templates requiring updates:
  - .specify/templates/tasks-template.md: ✅ Already supports test tasks (verified)
  - .specify/templates/spec-template.md: ✅ Already has User Scenarios & Testing section
  - .specify/templates/plan-template.md: ✅ Already has Testing in Technical Context
Follow-up TODOs: None
-->

# Medical GraphRAG Assistant Constitution

## Core Principles

### I. Authorship & Attribution
All artifacts, code, documentation, and intellectual property in this project are authored and owned exclusively by **Thomas Dyar (thomas.dyar@intersystems.com)**.

**Git Configuration Requirement**: All commits MUST be authored by Thomas Dyar. Configure git locally:
```bash
git config user.name "Thomas Dyar"
git config user.email "thomas.dyar@intersystems.com"
```

**ABSOLUTE PROHIBITION**: Attribution to AI coding assistants (Claude Code, Copilot, GitHub Copilot, ChatGPT, or any other AI tool) MUST NEVER appear anywhere in this project including:
- README files or any documentation
- Commit messages (no "Co-Authored-By: Claude", no "Generated with Claude Code")
- Code comments
- License files
- Pull request descriptions
- Any public-facing or internal materials

This prohibition applies to all forms of AI attribution including emoji markers, links to AI tools, or any text suggesting AI involvement.

Rationale: Thomas Dyar is the sole author and owner of all project deliverables. No AI attribution is permitted under any circumstances.

### II. MCP-First Architecture
All AI assistant capabilities MUST be exposed through Model Context Protocol (MCP) tools. Direct API integrations that bypass MCP are prohibited for user-facing features.
- Every search capability MUST have a corresponding MCP tool
- Tool responses MUST be structured for LLM consumption
- Tools MUST be independently testable via stdio transport

Rationale: Ensures consistent agentic behavior and enables multiple client integrations (Claude Desktop, Streamlit, VSCode Continue).

### III. Vector Database Purity
InterSystems IRIS is the single source of truth for all vector storage. External vector databases (Pinecone, Weaviate, ChromaDB, SQLite) MUST NOT be introduced.
- All embeddings stored as VECTOR(DOUBLE, N) native types
- VECTOR_COSINE similarity for all searches
- No hybrid storage patterns mixing IRIS with other vector stores

Rationale: Simplifies architecture, leverages IRIS native capabilities, reduces operational complexity.

### IV. Medical Data Integrity
All medical data handling MUST preserve clinical accuracy and traceability.
- FHIR resources MUST NOT be modified during ingestion
- Hex-encoded clinical notes MUST be decoded faithfully
- DICOM metadata MUST be preserved alongside image vectors
- Entity extraction MUST use validated medical ontologies

Rationale: Medical applications require auditability and data integrity for clinical decision support.

### V. Graceful Degradation
System components MUST fail gracefully when dependencies are unavailable.
- Missing NVIDIA NIM endpoints MUST NOT crash the application
- Database connection failures MUST return informative errors
- API rate limits MUST trigger backoff, not exceptions
- Max iteration limits MUST prevent infinite tool loops

Rationale: Production medical systems require resilience; partial functionality is preferable to complete failure.

### VI. Test-Driven Development & UX Testing
All feature specifications MUST include robust test implementations following TDD principles. UX components MUST have automated Playwright tests.

**Test Requirements**:
- Specifications MUST define testable acceptance criteria for each user story
- Implementation plans MUST include test tasks written BEFORE implementation tasks
- Tests MUST be written and verified to FAIL before implementation begins
- Contract tests MUST verify API specifications
- Integration tests MUST cover user journeys end-to-end

**UX Testing Requirements**:
- Features with user interface components MUST include Playwright test implementations
- Playwright tests MUST be executed via the Playwright MCP server for consistency
- UX tests MUST be stored in `tests/ux/playwright/` directory
- Each user story with UI components MUST have corresponding Playwright test cases
- Test cases MUST verify:
  - Page load and accessibility
  - User interactions (clicks, inputs, navigation)
  - Component visibility and state changes
  - Error handling and edge cases

**Test Location Convention**:
- Contract tests: `tests/contract/`
- Integration tests: `tests/integration/`
- Unit tests: `tests/unit/`
- UX/Playwright tests: `tests/ux/playwright/`

Rationale: Test-first development catches defects early, ensures specifications are implementable, and provides regression safety. Automated UX testing via Playwright ensures consistent user experience across releases.

## Technology Constraints

**Required Stack:**
- Database: InterSystems IRIS Community Edition with native vector support
- LLM: AWS Bedrock (Claude Sonnet 4.5)
- Embeddings: NVIDIA NV-CLIP (1024-dim multimodal) via NIM
- Protocol: Model Context Protocol (MCP) for tool exposure
- UI: Streamlit for interactive interfaces
- UX Testing: Playwright via Playwright MCP server
- Deployment: AWS EC2 with NVIDIA GPU (g5.xlarge minimum)

**Prohibited:**
- External vector databases
- Non-MCP tool integrations for user features
- Hardcoded credentials in source files
- Synchronous blocking calls without timeouts
- Feature releases without corresponding test coverage

## Development Workflow

**Code Changes:**
1. All changes MUST be tested against AWS deployment
2. Configuration MUST support both local and AWS environments via YAML
3. Scripts MUST be idempotent (safe to run multiple times)

**Documentation:**
1. README MUST reflect current version and capabilities
2. PROGRESS.md tracks development history
3. Archive old implementations to archive/ directory

**Testing:**
1. Integration tests MUST verify IRIS connectivity
2. MCP tools MUST have stdio transport tests
3. Embeddings MUST be validated for non-zero magnitude
4. UX features MUST have Playwright tests before release
5. All tests MUST pass before merging to main branch

## Governance

This constitution supersedes all other development practices for this project. Amendments require:
1. Clear justification documented in commit message
2. Version increment following semantic versioning:
   - MAJOR: Principle removal or incompatible redefinition
   - MINOR: New principle or section added
   - PATCH: Clarifications and refinements
3. Update to dependent templates if principle changes affect them

All code reviews MUST verify compliance with these principles.

**Version**: 1.1.0 | **Ratified**: 2025-12-09 | **Last Amended**: 2025-12-10
