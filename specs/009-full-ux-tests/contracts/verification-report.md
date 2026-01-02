# Contracts: Full UX Verification Tests

## Verification Results JSON Schema

The verification suite outputs a structured `test-results.json` file for automated systems.

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "VerificationRun",
  "type": "object",
  "properties": {
    "run_info": {
      "type": "object",
      "properties": {
        "timestamp": { "type": "string", "format": "date-time" },
        "environment": { "type": "string" },
        "target_url": { "type": "string" },
        "status": { "enum": ["PASS", "FAIL"] }
      }
    },
    "results": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "requirement_id": { "type": "string", "pattern": "^FR-[0-9]{3}$" },
          "test_name": { "type": "string" },
          "status": { "enum": ["PASS", "FAIL", "SKIPPED"] },
          "duration_ms": { "type": "integer" },
          "error": { "type": "string" }
        },
        "required": ["requirement_id", "status"]
      }
    }
  },
  "required": ["run_info", "results"]
}
```

## CLI Contract

| Argument | Environment Var | Description |
|----------|-----------------|-------------|
| `--base-url` | `TARGET_URL` | Application endpoint to verify |
| `-k "memory"` | N/A | Filter tests by keyword |
| `--report-json` | N/A | Path to save JSON report |
