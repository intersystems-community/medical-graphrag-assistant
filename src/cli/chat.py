"""
CLI Chat module for medical GraphRAG.
Provides a terminal-based interface to perform queries and see tool traces.
"""

import sys
import os
import json
import asyncio
from typing import List, Dict, Any, Optional

# Load .env file
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
except ImportError:
    pass

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

MCP_SERVER_PATH = os.path.join(PROJECT_ROOT, 'mcp-server')
if MCP_SERVER_PATH not in sys.path:
    sys.path.insert(0, MCP_SERVER_PATH)

from src.embeddings.embedder_singleton import get_embedder
from src.memory import VectorMemory
from fhir_graphrag_mcp_server import call_tool

SYSTEM_PROMPT = """You are a helpful and accurate medical assistant. 
You have access to a variety of tools to search FHIR documents, query a knowledge graph, and generate visualizations.

CRITICAL INSTRUCTIONS:
1. ALWAYS use the provided tools to answer medical questions. Do not speculate or assume data doesn't exist without searching.
2. For any request involving visualization, charts, graphs, or timelines, you MUST use the appropriate `plot_*` tool. 
3. NEVER generate Python code, matplotlib code, SVG, or Markdown-based charts yourself. Only use the plotting tools.
4. If a query is complex (e.g., 'allergies or radiology images'), call MULTIPLE tools in sequence to gather all necessary information.
5. For image-related queries (X-rays, scans, radiology), use `search_medical_images`.
6. Use `get_entity_statistics` only for a high-level overview. To check if a SPECIFIC entity (like 'allergies') exists, use `search_knowledge_graph` or `search_fhir_documents`.
7. When summarizing results, be concise and refer to the specific data returned by the tools.
"""

class ChatCLI:
    def __init__(self, provider: str = "nim", model: Optional[str] = None):
        self.provider = provider
        self.model = model or os.getenv("NIM_LLM_MODEL", "meta/llama-3.1-8b-instruct")
        self.messages = []
        self.memory = VectorMemory(embedding_model=get_embedder())
        
    def _print_trace(self, iteration: int, tool_name: str, tool_input: Dict[str, Any], result: Any):
        print(f"\n[TRACE] Iteration {iteration}: Executing {tool_name}")
        print(f"  Input: {json.dumps(tool_input, indent=2)}")
        result_str = str(result)
        if len(result_str) > 500:
            result_str = result_str[:500] + "... (truncated)"
        print(f"  Result: {result_str}")

    async def _call_llm(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> Any:
        from openai import OpenAI
        base_url = os.getenv("NIM_LLM_URL", "http://localhost:8001/v1")
        api_key = os.getenv("NVIDIA_API_KEY", "not-needed")
        client = OpenAI(base_url=base_url, api_key=api_key)
        
        full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
        
        openai_tools = []
        if tools:
            for tool in tools:
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool["toolSpec"]["name"],
                        "description": tool["toolSpec"]["description"],
                        "parameters": tool["toolSpec"]["inputSchema"]["json"]
                    }
                })
        
        params = {
            "model": self.model,
            "messages": full_messages,
            "temperature": 0.0,
        }
        if openai_tools:
            params["tools"] = openai_tools
            
        response = client.chat.completions.create(**params)
        return response.choices[0].message

    async def query(self, user_query: str, verbose: bool = True):
        print(f"\n>>> Query: {user_query}")
        
        memories = self.memory.recall(user_query, top_k=3)
        memory_context = ""
        if memories:
            memory_context = "\n[RECALLED MEMORY]\n"
            for m in memories:
                if m['similarity'] > 0.3:
                    memory_context += f"- {m['text']}\n"
            memory_context += "[END MEMORY]\n\n"
            if verbose:
                print(memory_context)
        
        current_query = memory_context + user_query
        self.messages.append({"role": "user", "content": current_query})
        
        max_iterations = 10
        for i in range(max_iterations):
            from fhir_graphrag_mcp_server import list_tools
            available_tools = await list_tools()
            converse_tools = []
            for t in available_tools:
                converse_tools.append({
                    "toolSpec": {
                        "name": t.name,
                        "description": t.description,
                        "inputSchema": {"json": t.inputSchema}
                    }
                })
            
            message = await self._call_llm(self.messages, converse_tools)
            self.messages.append(message)
            
            if not message.tool_calls:
                print(f"\nAssistant: {message.content}")
                return
            
            if message.content:
                print(f"\nAssistant (thinking): {message.content}")
            
            for tc in message.tool_calls:
                t_name = tc.function.name
                t_input = json.loads(tc.function.arguments)
                
                result = await call_tool(t_name, t_input)
                result_data = json.loads(result[0].text)
                
                if verbose:
                    self._print_trace(i+1, t_name, t_input, result_data)
                
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": t_name,
                    "content": json.dumps(result_data)
                })
                
        print("\nReached maximum iterations.")

async def run_chat_cli(query: str, provider: str = "nim", verbose: bool = True):
    cli = ChatCLI(provider=provider)
    await cli.query(query, verbose=verbose)
