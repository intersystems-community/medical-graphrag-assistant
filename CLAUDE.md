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
