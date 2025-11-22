#!/usr/bin/env python3
"""Test NVIDIA Hosted NIM API for embeddings"""

import requests

API_KEY = "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"
MODEL = "nvidia/nv-embedqa-e5-v5"

response = requests.post(
    "https://integrate.api.nvidia.com/v1/embeddings",
    headers={
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    },
    json={
        "input": ["test clinical note about patient health"],
        "model": MODEL,
        "input_type": "passage"  # Required for asymmetric models
    }
)

data = response.json()

if "data" in data:
    print("✅ NVIDIA NIM Hosted API Working!")
    print(f"   Model: {data['model']}")
    print(f"   Dimensions: {len(data['data'][0]['embedding'])}")
    print(f"   Usage: {data['usage']}")
    print(f"\n✅ Can use hosted NIM instead of self-hosted!")
else:
    print(f"❌ Error: {data}")
