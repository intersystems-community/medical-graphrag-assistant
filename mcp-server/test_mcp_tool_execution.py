#!/usr/bin/env python3
"""
Test FHIR + GraphRAG MCP Server Tool Execution

Tests actual tool execution against AWS IRIS database.
"""

import asyncio
import json
from fhir_graphrag_mcp_server import call_tool

async def test_tool_execution():
    """Test executing MCP tools."""
    print("Testing MCP Tool Execution...")
    print("=" * 60)

    # Test 1: Knowledge graph statistics
    print("\n1. Testing get_entity_statistics...")
    print("-" * 60)
    try:
        result = await call_tool("get_entity_statistics", {})
        data = json.loads(result[0].text)
        print(f"✓ Total entities: {data['total_entities']}")
        print(f"✓ Total relationships: {data['total_relationships']}")
        print(f"✓ Entity types: {len(data['entity_distribution'])}")
        print("\nTop entity types:")
        for entity_type in data['entity_distribution'][:5]:
            print(f"  • {entity_type['type']}: {entity_type['count']}")
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False

    # Test 2: Search knowledge graph
    print("\n2. Testing search_knowledge_graph...")
    print("-" * 60)
    try:
        result = await call_tool("search_knowledge_graph", {
            "query": "fever",
            "limit": 3
        })
        data = json.loads(result[0].text)
        print(f"✓ Found {data['entities_found']} entities")
        print(f"✓ Related to {data['documents_found']} documents")
        print("\nTop entities:")
        for entity in data['entities'][:3]:
            print(f"  • {entity['text']} ({entity['type']}) - confidence: {entity['confidence']:.2f}")
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False

    # Test 3: Search FHIR documents
    print("\n3. Testing search_fhir_documents...")
    print("-" * 60)
    try:
        result = await call_tool("search_fhir_documents", {
            "query": "chest pain",
            "limit": 2
        })
        data = json.loads(result[0].text)
        print(f"✓ Found {data['results_count']} documents")
        if data['documents']:
            print("\nFirst document preview:")
            doc = data['documents'][0]
            print(f"  FHIR ID: {doc['fhir_id']}")
            print(f"  Relevance: {doc['relevance']}")
            print(f"  Preview: {doc['preview'][:100]}...")
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False

    # Test 4: Hybrid search
    print("\n4. Testing hybrid_search...")
    print("-" * 60)
    try:
        result = await call_tool("hybrid_search", {
            "query": "respiratory infection",
            "top_k": 3
        })
        data = json.loads(result[0].text)
        print(f"✓ FHIR results: {data['fhir_results']}")
        print(f"✓ GraphRAG results: {data['graphrag_results']}")
        print(f"✓ Fused results: {data['fused_results']}")
        print("\nTop fused documents:")
        for doc in data['top_documents'][:3]:
            print(f"  • {doc['fhir_id']} (RRF score: {doc['rrf_score']:.4f})")
            print(f"    Sources: {', '.join(doc['sources'])}")
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False

    print("\n" + "=" * 60)
    print("✓ All tool execution tests PASSED!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = asyncio.run(test_tool_execution())
    exit(0 if success else 1)
