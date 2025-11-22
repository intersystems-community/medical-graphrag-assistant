#!/usr/bin/env python3
"""
Test AI Hub MCP Server Integration with FHIR + GraphRAG Tools

This script tests the complete integration by:
1. Importing the AI Hub MCP server
2. Verifying FHIR + GraphRAG tools are registered
3. Testing tool discovery via MCP protocol
"""

import sys
import json
from pathlib import Path

# Add AI Hub to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "aigw_mockup" / "python"))

# Test imports
print("Testing AI Hub MCP Server Integration...")
print("=" * 60)

try:
    from aihub.mcp.server import MCPServer, MCPServerConfig
    print("✓ Successfully imported MCPServer from AI Hub")
except ImportError as e:
    print(f"✗ Failed to import MCPServer: {e}")
    sys.exit(1)

try:
    from aihub.mcp.tools.fhir_graphrag import register_fhir_graphrag_tools
    print("✓ Successfully imported FHIR + GraphRAG tools")
except ImportError as e:
    print(f"✗ Failed to import FHIR + GraphRAG tools: {e}")
    sys.exit(1)

# Test server initialization
print("\nTesting server initialization...")
try:
    config = MCPServerConfig(
        iris_host="3.84.250.46",
        iris_port=1972,
        iris_namespace="USER",
        iris_username="_SYSTEM",
        iris_password="SYS",
        transport="stdio",
        pool_size=5
    )
    print(f"✓ Created server config: {config.iris_host}:{config.iris_port}/{config.iris_namespace}")
except Exception as e:
    print(f"✗ Failed to create config: {e}")
    sys.exit(1)

try:
    server = MCPServer(config)
    print(f"✓ Initialized MCP server with {len(server.mcp._tools)} registered tools")
except Exception as e:
    print(f"✗ Failed to initialize server: {e}")
    sys.exit(1)

# List registered tools
print("\nRegistered MCP Tools:")
print("-" * 60)
for tool_name in sorted(server.mcp._tools.keys()):
    tool = server.mcp._tools[tool_name]
    print(f"  • {tool_name}")
    if hasattr(tool, '__doc__') and tool.__doc__:
        # Get first line of docstring
        doc_first_line = tool.__doc__.strip().split('\n')[0]
        print(f"    {doc_first_line}")

# Verify FHIR + GraphRAG tools
print("\nVerifying FHIR + GraphRAG tools...")
expected_tools = [
    "fhir_search_documents",
    "fhir_get_document",
    "graphrag_search_entities",
    "graphrag_traverse_relationships",
    "graphrag_hybrid_search",
    "graphrag_get_statistics"
]

missing_tools = []
for tool_name in expected_tools:
    if tool_name in server.mcp._tools:
        print(f"  ✓ {tool_name}")
    else:
        print(f"  ✗ {tool_name} (MISSING)")
        missing_tools.append(tool_name)

if missing_tools:
    print(f"\n⚠ Warning: {len(missing_tools)} tools are missing!")
    sys.exit(1)
else:
    print(f"\n✓ All {len(expected_tools)} FHIR + GraphRAG tools registered successfully!")

# Test tool metadata
print("\nTool Metadata:")
print("-" * 60)
for tool_name in expected_tools:
    tool = server.mcp._tools[tool_name]
    print(f"\n{tool_name}:")
    if hasattr(tool, '__doc__') and tool.__doc__:
        doc_lines = [line.strip() for line in tool.__doc__.strip().split('\n') if line.strip()]
        for line in doc_lines[:3]:  # First 3 lines
            print(f"  {line}")

print("\n" + "=" * 60)
print("✓ AI Hub MCP Server integration test PASSED")
print("=" * 60)

# Cleanup
server.close()
