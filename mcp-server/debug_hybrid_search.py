#!/usr/bin/env python3
import asyncio
import json
from fhir_graphrag_mcp_server import call_tool

async def test():
    result = await call_tool("hybrid_search", {"query": "respiratory infection", "top_k": 3})
    print(result[0].text)

asyncio.run(test())
