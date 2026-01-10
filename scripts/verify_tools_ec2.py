"""
Standalone verification script for medical image search and hybrid search.
Tests the tools directly without Streamlit to ensure backend stability.
"""

import sys
import os
import json
import asyncio

# Add project root to path for imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Set CONFIG_PATH if not set
if not os.getenv("CONFIG_PATH"):
    os.environ["CONFIG_PATH"] = "config/fhir_graphrag_config.aws.yaml"

async def verify_search_medical_images():
    print("\n--- Testing search_medical_images ---")
    try:
        from mcp_server.fhir_graphrag_mcp_server import call_tool
        
        result = await call_tool("search_medical_images", {"query": "pneumonia", "limit": 3})
        data = json.loads(result[0].text)
        
        print(f"Status: SUCCESS")
        print(f"Search Mode: {data.get('search_mode')}")
        print(f"Results Count: {data.get('results_count')}")
        
        if data.get('fallback_reason'):
            print(f"Note: Fallback reason: {data['fallback_reason']}")
            
        if data.get('images'):
            print("Top result:")
            img = data['images'][0]
            print(f"  - ID: {img['image_id']}")
            print(f"  - Path: {img['image_path']}")
            print(f"  - Linked: {img['patient_linked']} ({img.get('patient_display')})")
        else:
            print("Warning: No images found (Expected if dummy data not inserted yet or query doesn't match)")
            
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

async def verify_hybrid_search():
    print("\n--- Testing hybrid_search ---")
    try:
        from mcp_server.fhir_graphrag_mcp_server import call_tool
        
        result = await call_tool("hybrid_search", {"query": "fever and cough", "top_k": 3})
        data = json.loads(result[0].text)
        
        print(f"Status: SUCCESS")
        print(f"Results Count: {data.get('results_count')}")
        
        if data.get('top_documents'):
            print("Top result:")
            doc = data['top_documents'][0]
            print(f"  - ID: {doc['fhir_id']}")
            print(f"  - Sources: {doc['sources']}")
            print(f"  - Preview: {doc['preview'][:100]}...")
            
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")

async def main():
    print(f"Verification starting (CONFIG_PATH={os.getenv('CONFIG_PATH')})")
    await verify_search_medical_images()
    await verify_hybrid_search()
    print("\nVerification complete.")

if __name__ == '__main__':
    asyncio.run(main())
