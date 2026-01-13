#!/usr/bin/env python3
"""Test NVIDIA Hosted NIM API for embeddings"""

import requests

API_KEY = "NVIDIA_API_KEY_PLACEHOLDER"
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
