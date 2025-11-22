#!/usr/bin/env python3
"""
Test FHIR + GraphRAG MCP Server Tool Discovery

Tests the standalone MCP server by simulating tool list request.
"""

import asyncio
import json
from fhir_graphrag_mcp_server import server, list_tools

async def test_tools():
    """Test tool discovery."""
    print("Testing FHIR + GraphRAG MCP Server...")
    print("=" * 60)

    # Get list of available tools
    tools = await list_tools()

    print(f"Found {len(tools)} tools:")
    print("-" * 60)

    for tool in tools:
        print(f"\n• {tool.name}")
        print(f"  Description: {tool.description[:100]}...")

        # Show input schema
        if "properties" in tool.inputSchema:
            props = tool.inputSchema["properties"]
            print(f"  Parameters: {', '.join(props.keys())}")

    # Verify expected tools
    expected_tools = {
        "search_fhir_documents",
        "search_knowledge_graph",
        "hybrid_search",
        "get_entity_relationships",
        "get_document_details",
        "get_entity_statistics"
    }

    tool_names = {t.name for t in tools}

    print("\n" + "=" * 60)
    print("Tool Verification:")
    print("-" * 60)

    for expected in sorted(expected_tools):
        if expected in tool_names:
            print(f"  ✓ {expected}")
        else:
            print(f"  ✗ {expected} (MISSING)")

    missing = expected_tools - tool_names
    extra = tool_names - expected_tools

    if missing:
        print(f"\n⚠ Missing tools: {missing}")
        return False

    if extra:
        print(f"\n⚠ Unexpected tools: {extra}")

    print("\n✓ All expected tools found!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = asyncio.run(test_tools())
    exit(0 if success else 1)
