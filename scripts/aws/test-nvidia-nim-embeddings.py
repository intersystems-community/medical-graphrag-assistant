#!/usr/bin/env python3
"""
Test NVIDIA NIM Embeddings API
Verifies NV-EmbedQA-E5-v5 generates 1024-dimensional embeddings
"""

import os
import sys
import requests
import json

def test_nvidia_nim_api():
    """Test NVIDIA NIM embeddings via API"""

    # Get API key from environment
    api_key = os.getenv('NVIDIA_API_KEY')
    if not api_key:
        print("✗ NVIDIA_API_KEY not found in environment")
        return False

    print(f"→ Using API key: {api_key[:20]}...")

    # NVIDIA NIM API endpoint (corrected)
    url = "https://integrate.api.nvidia.com/v1/embeddings"

    # Test queries
    test_texts = [
        "Patient presents with chest pain and shortness of breath",
        "Cardiac catheterization performed successfully",
        "Atrial fibrillation management consultation"
    ]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    print("\n→ Testing NV-EmbedQA-E5-v5 embeddings...")

    for i, text in enumerate(test_texts, 1):
        print(f"\n  Test {i}: {text[:50]}...")

        payload = {
            "input": [text],  # API expects a list
            "model": "nvidia/nv-embedqa-e5-v5",
            "input_type": "query"
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)

            if response.status_code == 200:
                data = response.json()

                if 'data' in data and len(data['data']) > 0:
                    embedding = data['data'][0]['embedding']
                    dimension = len(embedding)

                    # Get first/last few values
                    preview = embedding[:3] + ['...'] + embedding[-3:]

                    print(f"  ✓ Received {dimension}-dimensional embedding")
                    print(f"    Preview: {preview}")

                    if dimension != 1024:
                        print(f"  ⚠️  Warning: Expected 1024 dimensions, got {dimension}")
                        return False
                else:
                    print(f"  ✗ Invalid response format: {data}")
                    return False
            else:
                print(f"  ✗ API Error {response.status_code}: {response.text}")
                return False

        except Exception as e:
            print(f"  ✗ Request failed: {e}")
            return False

    print("\n✅ NVIDIA NIM API working correctly!")
    print("   - All embeddings are 1024-dimensional")
    print("   - Ready for AWS integration")

    return True

def main():
    print("=" * 60)
    print("NVIDIA NIM Embeddings API Test")
    print("=" * 60)

    success = test_nvidia_nim_api()

    if success:
        print("\n" + "=" * 60)
        print("Next Steps:")
        print("  1. Update AWS config to use NVIDIA NIM")
        print("  2. Re-vectorize clinical notes with 1024-dim embeddings")
        print("  3. Update similarity search queries")
        print("=" * 60)
        return 0
    else:
        print("\n✗ NVIDIA NIM API test failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())
