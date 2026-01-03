# medical-graphrag-assistant Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-12-10

## Active Technologies
- Python 3.11 + Streamlit, streamlit-agraph, Plotly (fallback) (005-graphrag-details-panel)
- InterSystems IRIS (existing - no changes required) (005-graphrag-details-panel)
- Python 3.11 + MCP SDK, InterSystems IRIS DB-API, boto3 (AWS Bedrock), Synthea (patient generation) (007-fhir-radiology-integration)
- InterSystems IRIS for Health (FHIR repository + vector tables) (007-fhir-radiology-integration)
- Python 3.11 + MCP SDK, InterSystems IRIS DB-API, requests (FHIR REST), boto3 (Bedrock) (007-fhir-radiology-integration)
- InterSystems IRIS for Health (FHIR R4 repository + VectorSearch tables) (007-fhir-radiology-integration)

- TypeScript/JavaScript (Playwright MCP), Python 3.11 (target application) + @playwright/mcp (MCP server), Claude Code (execution host) (002-playwright-ux-tests)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

TypeScript/JavaScript (Playwright MCP), Python 3.11 (target application): Follow standard conventions

## Recent Changes
- 007-fhir-radiology-integration: Added Python 3.11 + MCP SDK, InterSystems IRIS DB-API, requests (FHIR REST), boto3 (Bedrock)
- 007-fhir-radiology-integration: Added Python 3.11 + MCP SDK, InterSystems IRIS DB-API, requests (FHIR REST), boto3 (Bedrock)
- 007-fhir-radiology-integration: Added Python 3.11 + MCP SDK, InterSystems IRIS DB-API, boto3 (AWS Bedrock), Synthea (patient generation)


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->

## Cost Optimization Strategy

This project uses model tiering to minimize costs:

### Model Tiers

| Model | Use For | Cost |
|-------|---------|------|
| **Haiku** | Clarifying specs, small edits, task breakdown, quick Q&A | Lowest |
| **Sonnet** | Planning, validating, coordinating, code review | Moderate |
| **Gemini Flash** (via `gemini_implement` MCP tool) | Code implementation, refactors, multi-file edits | Low |
| **Opus** | Cross-service architecture, complex reasoning | Highest - sparingly |

### MCP Tools

The Gemini MCP server provides cost-effective code generation:

```bash
# Use gemini_implement for code changes
mcp__gemini-impl__gemini_implement({
  instructions: "Add user authentication endpoint",
  target_files: ["api/routes.py"],
  base_dir: "/path/to/project"
})

# Review code without changes
mcp__gemini-impl__gemini_review({
  code: "...",
  focus: "security"
})

# Explain code
mcp__gemini-impl__gemini_explain({
  code: "...",
  question: "What does this function do?"
})

# Health check
mcp__gemini-impl__gemini_health()
```

### Workflow

1. Stay on **Sonnet** (or **opusplan**) for most work
2. Use **Haiku** for simple clarifications
3. Call **`gemini_implement`** for heavy code generation
4. Only use **Opus** for complex architecture decisions

### Configuration

- `.mcp.json` - Gemini MCP server registration
- `.specify/model-routing.yaml` - Phase-specific model routing
- `.claude/agents/spec-implementer.md` - Implementation agent

