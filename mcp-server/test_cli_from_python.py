#!/usr/bin/env python3
"""Test calling AWS CLI from Python as workaround"""

import subprocess
import json
import os

os.environ['AWS_PROFILE'] = 'AWS_ACCOUNT_ID_PowerUserPlusAccess'

def call_claude_via_cli(user_message: str, tools=None):
    """Call Claude via AWS CLI instead of boto3"""

    messages = [{"role": "user", "content": [{"text": user_message}]}]

    cmd = [
        "aws", "bedrock-runtime", "converse",
        "--model-id", "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "--messages", json.dumps(messages)
    ]

    if tools:
        tool_config = {"tools": tools}
        cmd.extend(["--tool-config", json.dumps(tool_config)])

    cmd.extend(["--inference-config", json.dumps({"maxTokens": 4000})])

    print(f"Calling: {' '.join(cmd[:6])}...")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=os.environ.copy()
    )

    if result.returncode != 0:
        print(f"✗ ERROR: {result.stderr}")
        return None

    return json.loads(result.stdout)

# Test without tools
print("=== Test 1: Simple message without tools ===")
response = call_claude_via_cli("Hello, can you help me?")
if response:
    print(f"✓ SUCCESS!")
    print(f"Stop reason: {response.get('stopReason')}")
    print(f"Response: {response.get('output', {}).get('message', {}).get('content', [{}])[0].get('text', '')[:100]}...")

print("\n=== Test 2: Message with tools ===")
test_tools = [{
    "toolSpec": {
        "name": "search_fhir_documents",
        "description": "Search FHIR clinical documents",
        "inputSchema": {"json": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search terms"}
            },
            "required": ["query"]
        }}
    }
}]

response = call_claude_via_cli("Search for chest pain cases", tools=test_tools)
if response:
    print(f"✓ SUCCESS with tools!")
    print(f"Stop reason: {response.get('stopReason')}")
    content = response.get('output', {}).get('message', {}).get('content', [])
    for block in content:
        if 'text' in block:
            print(f"Text: {block['text'][:100]}...")
        elif 'toolUse' in block:
            print(f"Tool call: {block['toolUse']['name']}")
