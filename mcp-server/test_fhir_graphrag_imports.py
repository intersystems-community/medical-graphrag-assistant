#!/usr/bin/env python3
"""
Test FHIR + GraphRAG Tools Import and Structure

Verifies that the tools can be imported and have correct structure
without requiring full server initialization.
"""

import sys
from pathlib import Path

# Add AI Hub to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "aigw_mockup" / "python"))

print("Testing FHIR + GraphRAG Tools Import...")
print("=" * 60)

# Test import of tool module
try:
    from aihub.mcp.tools import fhir_graphrag
    print("✓ Successfully imported fhir_graphrag module")
except ImportError as e:
    print(f"✗ Failed to import fhir_graphrag: {e}")
    sys.exit(1)

# Test import of registration function
try:
    from aihub.mcp.tools.fhir_graphrag import register_fhir_graphrag_tools
    print("✓ Successfully imported register_fhir_graphrag_tools")
except ImportError as e:
    print(f"✗ Failed to import register_fhir_graphrag_tools: {e}")
    sys.exit(1)

# Test import of tool class
try:
    from aihub.mcp.tools.fhir_graphrag import FHIRGraphRAGTool
    print("✓ Successfully imported FHIRGraphRAGTool class")
except ImportError as e:
    print(f"✗ Failed to import FHIRGraphRAGTool: {e}")
    sys.exit(1)

# Test import of parameter models
try:
    from aihub.mcp.tools.fhir_graphrag import (
        FHIRSearchParams,
        FHIRDocumentParams,
        GraphRAGEntityParams,
        GraphRAGTraversalParams,
        GraphRAGHybridParams
    )
    print("✓ Successfully imported all parameter models")
except ImportError as e:
    print(f"✗ Failed to import parameter models: {e}")
    sys.exit(1)

# Verify tool class methods
print("\nVerifying FHIRGraphRAGTool methods...")
expected_methods = [
    "search_fhir_documents",
    "get_fhir_document",
    "search_graphrag_entities",
    "traverse_graphrag_relationships",
    "hybrid_search",
    "get_graphrag_statistics"
]

for method_name in expected_methods:
    if hasattr(FHIRGraphRAGTool, method_name):
        method = getattr(FHIRGraphRAGTool, method_name)
        print(f"  ✓ {method_name} (async: {asyncio.iscoroutinefunction(method)})")
    else:
        print(f"  ✗ {method_name} (MISSING)")
        sys.exit(1)

# Verify parameter models
print("\nVerifying parameter models...")
param_models = [
    ("FHIRSearchParams", FHIRSearchParams, ["query", "limit"]),
    ("FHIRDocumentParams", FHIRDocumentParams, ["fhir_id"]),
    ("GraphRAGEntityParams", GraphRAGEntityParams, ["query", "limit"]),
    ("GraphRAGTraversalParams", GraphRAGTraversalParams, ["entity_text", "max_depth"]),
    ("GraphRAGHybridParams", GraphRAGHybridParams, ["query", "top_k"])
]

for model_name, model_class, expected_fields in param_models:
    print(f"  {model_name}:")
    for field in expected_fields:
        if field in model_class.model_fields:
            print(f"    ✓ {field}")
        else:
            print(f"    ✗ {field} (MISSING)")
            sys.exit(1)

print("\n" + "=" * 60)
print("✓ All FHIR + GraphRAG tool imports and structure verified!")
print("=" * 60)

# Test registration function signature
import inspect
sig = inspect.signature(register_fhir_graphrag_tools)
print(f"\nregistration function signature: {sig}")
print(f"Parameters: {list(sig.parameters.keys())}")

print("\n✓ Integration test PASSED - tools ready for AI Hub MCP server")
