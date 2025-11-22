#!/usr/bin/env python3
"""Test Bedrock Converse API with exact same code as Streamlit app"""

import boto3
import os
import json

# Set AWS profile exactly as in streamlit_app.py
os.environ['AWS_PROFILE'] = '122293094970_PowerUserPlusAccess'

print("Creating boto3 session...")
session = boto3.Session(profile_name='122293094970_PowerUserPlusAccess')

print("Creating bedrock-runtime client...")
bedrock_client = session.client('bedrock-runtime', region_name='us-east-1')

print("Testing get_caller_identity...")
sts = session.client('sts')
identity = sts.get_caller_identity()
print(f"✓ Identity: {identity['Arn']}")

# Test with exact MCP tools format from streamlit_app.py
MCP_TOOLS = [
    {
        "name": "search_fhir_documents",
        "description": "Search FHIR clinical documents by text. Returns relevant medical records.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search terms"},
                "limit": {"type": "integer", "description": "Max results", "default": 5}
            },
            "required": ["query"]
        }
    }
]

# Convert to Converse API format exactly as in streamlit_app.py
converse_tools = []
for tool in MCP_TOOLS:
    converse_tools.append({
        "toolSpec": {
            "name": tool["name"],
            "description": tool["description"],
            "inputSchema": {"json": tool["input_schema"]}
        }
    })

# Test message
converse_messages = [{
    "role": "user",
    "content": [{"text": "Hello, can you help me search for chest pain cases?"}]
}]

print("\nCalling Converse API...")
print(f"Model ID: global.anthropic.claude-sonnet-4-5-20250929-v1:0")
print(f"Tools: {len(converse_tools)}")

try:
    response = bedrock_client.converse(
        modelId='global.anthropic.claude-sonnet-4-5-20250929-v1:0',
        messages=converse_messages,
        toolConfig={"tools": converse_tools} if converse_tools else None,
        inferenceConfig={"maxTokens": 4000}
    )

    print("\n✓ SUCCESS!")
    print(f"Stop reason: {response.get('stopReason')}")
    print(f"Output: {response.get('output', {}).get('message', {})}")

except Exception as e:
    print(f"\n✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
