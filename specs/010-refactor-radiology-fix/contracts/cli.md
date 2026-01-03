# CLI Contract: System Health Check

## Command
`python -m src.cli check-health`

## Success Response (JSON)
```json
{
  "status": "pass",
  "checks": [
    {
      "component": "IRIS Connection",
      "status": "pass",
      "message": "..."
    },
    {
      "component": "Schema: SQLUser.FHIRDocuments",
      "status": "pass",
      "message": "Table exists"
    }
  ]
}
```

## Failure Response (JSON)
```json
{
  "status": "fail",
  "checks": [
    {
      "component": "Schema: SQLUser.FHIRDocuments",
      "status": "fail",
      "message": "Table not found",
      "details": {
        "suggestion": "Run: python src/setup/create_text_vector_table.py"
      }
    }
  ]
}
```

## Exit Codes
- `0`: Success
- `1`: Failure
