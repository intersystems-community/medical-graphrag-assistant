#!/usr/bin/env python3
"""Test Bedrock Converse API WITHOUT tools"""

import boto3
import os

os.environ['AWS_PROFILE'] = '122293094970_PowerUserPlusAccess'
session = boto3.Session(profile_name='122293094970_PowerUserPlusAccess')
bedrock_client = session.client('bedrock-runtime', region_name='us-east-1')

# Test WITHOUT tools
converse_messages = [{
    "role": "user",
    "content": [{"text": "Hello, can you help me?"}]
}]

print("Testing Converse API WITHOUT tools...")
try:
    response = bedrock_client.converse(
        modelId='global.anthropic.claude-sonnet-4-5-20250929-v1:0',
        messages=converse_messages,
        inferenceConfig={"maxTokens": 4000}
        # NO toolConfig parameter
    )
    print("✓ SUCCESS without tools!")
    print(f"Stop reason: {response.get('stopReason')}")
except Exception as e:
    print(f"✗ ERROR without tools: {e}")

print("\n" + "="*50 + "\n")

# Test WITH tools
converse_tools = [{
    "toolSpec": {
        "name": "search_fhir_documents",
        "description": "Search FHIR clinical documents",
        "inputSchema": {"json": {
            "type": "object",
            "properties": {
                "query": {"type": "string"}
            },
            "required": ["query"]
        }}
    }
}]

print("Testing Converse API WITH tools...")
try:
    response = bedrock_client.converse(
        modelId='global.anthropic.claude-sonnet-4-5-20250929-v1:0',
        messages=converse_messages,
        toolConfig={"tools": converse_tools},
        inferenceConfig={"maxTokens": 4000}
    )
    print("✓ SUCCESS with tools!")
except Exception as e:
    print(f"✗ ERROR with tools: {e}")
