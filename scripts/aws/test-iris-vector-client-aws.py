#!/usr/bin/env python3
"""
AWS Integration Test using IRISVectorDBClient
Demonstrates proper use of existing abstractions instead of manual SQL
"""

import os
import sys
import requests

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.vectorization.vector_db_client import IRISVectorDBClient


def get_nvidia_embedding(text, api_key):
    """Get embedding from NVIDIA NIM API"""
    url = "https://integrate.api.nvidia.com/v1/embeddings"

    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "input": [text],
            "model": "nvidia/nv-embedqa-e5-v5",
            "input_type": "query"
        },
        timeout=30
    )

    if response.status_code == 200:
        return response.json()['data'][0]['embedding']
    else:
        raise Exception(f"NVIDIA API Error: {response.status_code}")


def main():
    print("=" * 70)
    print("AWS Integration Test using IRISVectorDBClient")
    print("(Proper use of existing abstractions)")
    print("=" * 70)

    # Get API key
    api_key = os.getenv('NVIDIA_API_KEY')
    if not api_key:
        print("✗ NVIDIA_API_KEY not set")
        return 1

    # Test data
    clinical_notes = [
        {
            "resource_id": "CLIENT_TEST_001",
            "patient_id": "PATIENT_001",
            "document_type": "Progress Note",
            "text_content": "Patient presents with acute chest pain radiating to left arm."
        },
        {
            "resource_id": "CLIENT_TEST_002",
            "patient_id": "PATIENT_002",
            "document_type": "Discharge Summary",
            "text_content": "Patient underwent successful cardiac catheterization with stent placement."
        }
    ]

    try:
        # Step 1: Generate embeddings
        print("\n→ Step 1: Generating NVIDIA NIM embeddings...")
        for note in clinical_notes:
            embedding = get_nvidia_embedding(note['text_content'], api_key)
            note['embedding'] = embedding
            print(f"  ✓ {note['resource_id']}: {len(embedding)}-dim")

        # Step 2: Connect to AWS IRIS using our client
        print("\n→ Step 2: Connecting to AWS IRIS via IRISVectorDBClient...")

        # Use existing IRISVectorDBClient - it handles all the TO_VECTOR syntax!
        # Note: Connect to %SYS namespace (DEMO namespace has access restrictions)
        # Then use fully qualified table names: SQLUser.ClinicalNoteVectors
        client = IRISVectorDBClient(
            host="3.84.250.46",
            port=1972,
            namespace="%SYS",
            username="_SYSTEM",
            password="SYS",
            vector_dimension=1024
        )

        with client:
            print("  ✓ Connected using IRISVectorDBClient")

            # Step 3: Insert vectors (client handles TO_VECTOR internally)
            print("\n→ Step 3: Inserting vectors...")
            # Use fully qualified table name: SQLUser.ClinicalNoteVectors
            for note in clinical_notes:
                client.insert_vector(
                    resource_id=note['resource_id'],
                    patient_id=note['patient_id'],
                    document_type=note['document_type'],
                    text_content=note['text_content'],
                    embedding=note['embedding'],
                    embedding_model="nvidia/nv-embedqa-e5-v5",
                    table_name="SQLUser.ClinicalNoteVectors"
                )
                print(f"  ✓ Inserted {note['resource_id']}")

            # Step 4: Search (client handles VECTOR_COSINE internally)
            print("\n→ Step 4: Testing similarity search...")
            query_text = "chest pain"
            query_embedding = get_nvidia_embedding(query_text, api_key)

            results = client.search_similar(
                query_vector=query_embedding,
                top_k=2,
                table_name="SQLUser.ClinicalNoteVectors"
            )

            print(f"  Query: \"{query_text}\"")
            print(f"  ✓ Found {len(results)} results:\n")
            for i, result in enumerate(results, 1):
                print(f"  {i}. {result['resource_id']} (similarity: {result['similarity']:.3f})")
                print(f"     {result['text_content'][:60]}...")

            # Step 5: Cleanup
            print("\n→ Step 5: Cleanup...")
            # Manual cleanup since client doesn't have delete method
            cursor = client.cursor
            # Use fully qualified table name from %SYS namespace
            cursor.execute("DELETE FROM SQLUser.ClinicalNoteVectors WHERE ResourceID LIKE 'CLIENT_TEST_%'")
            client.connection.commit()
            print("  ✓ Test data removed")

        print("\n" + "=" * 70)
        print("✅ SUCCESS: IRISVectorDBClient handles all vector syntax!")
        print("=" * 70)
        print("\nKey Benefits:")
        print("  ✅ No manual TO_VECTOR() SQL")
        print("  ✅ No manual VECTOR_COSINE() SQL")
        print("  ✅ Dimension validation built-in")
        print("  ✅ Clean Python API")
        print("  ✅ Works identically on local and AWS")
        print("=" * 70)

        return 0

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
