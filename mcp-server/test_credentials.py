#!/usr/bin/env python3
"""Debug credential resolution"""

import boto3
import os
import json

os.environ['AWS_PROFILE'] = '122293094970_PowerUserPlusAccess'

print("Creating session...")
session = boto3.Session(profile_name='122293094970_PowerUserPlusAccess')

print("\n=== Credential Source ===")
credentials = session.get_credentials()
print(f"Access Key: {credentials.access_key[:20]}...")
print(f"Method: {credentials.method}")
print(f"Token present: {credentials.token is not None}")

print("\n=== Creating bedrock-runtime client ===")
bedrock_client = session.client('bedrock-runtime', region_name='us-east-1')

print(f"Client region: {bedrock_client.meta.region_name}")
print(f"Client endpoint: {bedrock_client.meta.endpoint_url}")

# Try to get credentials that client is using
print("\n=== Client credentials ===")
client_credentials = bedrock_client._client_config.__dict__
print(json.dumps({k: str(v) for k, v in client_credentials.items() if not k.startswith('_')}, indent=2))
