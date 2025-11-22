#!/usr/bin/env python3
"""Debug MCP tool response."""

import asyncio
import json
from fhir_graphrag_mcp_server import call_tool

async def debug():
    result = await call_tool("get_entity_statistics", {})
    print("Result type:", type(result))
    print("Result length:", len(result))
    print("\nFirst element:")
    print("  Type:", type(result[0]))
    print("  Text:", result[0].text)

    # Try to parse JSON
    try:
        data = json.loads(result[0].text)
        print("\nParsed JSON keys:", data.keys())
        print("Full data:")
        print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"\nFailed to parse JSON: {e}")

if __name__ == "__main__":
    asyncio.run(debug())
