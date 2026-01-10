"""
CLI Chat module for medical GraphRAG.
Provides a terminal-based interface to perform queries and see tool traces.
"""

import sys
import os
import json
import asyncio
import time
from typing import List, Dict, Any, Optional

# Load .env file
try:
    from dotenv import load_dotenv
    # Look for .env in project root
    env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
except ImportError:
    pass

# Ensure project root is in path
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

# Import search services directly for some logic if needed
from src.search.fhir_search import FHIRSearchService
from src.search.kg_search import KGSearchService
from src.search.hybrid_search import HybridSearchService

class ChatCLI:
    """Terminal-based chat interface with tool trace visibility."""
    
    def __init__(self, provider: str = "nim", model: Optional[str] = None):
        self.provider = provider
        self.model = model or os.getenv("NIM_LLM_MODEL", "meta/llama-3.1-8b-instruct")
        self.messages = []
        self.memory = VectorMemory(embedding_model=get_embedder())
        
    def _print_trace(self, iteration: int, tool_name: str, tool_input: Dict[str, Any], result: Any):
        """Print a formatted tool trace."""
        print(f"\n[TRACE] Iteration {iteration}: Executing {tool_name}")
        print(f"  Input: {json.dumps(tool_input, indent=2)}")
        
        # Format result summary
        result_str = str(result)
        if len(result_str) > 500:
            result_str = result_str[:500] + "... (truncated)"
        print(f"  Result: {result_str}")

    async def _call_llm(self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Call the configured LLM provider."""
        if self.provider == "nim" or self.provider == "openai":
            return await self._call_openai_compatible(messages, tools)
        elif self.provider == "bedrock":
            return await self._call_bedrock(messages, tools)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    async def _call_openai_compatible(self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Call NIM or OpenAI API."""
        from openai import OpenAI
        
        base_url = os.getenv("NIM_LLM_URL", "http://localhost:8001/v1")
        api_key = os.getenv("NVIDIA_API_KEY", "not-needed")
        
        client = OpenAI(base_url=base_url, api_key=api_key)
        
        # Prepare system prompt
        full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
        
        # Convert tools to OpenAI format
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
            params["tool_choice"] = "auto"
            
        response = client.chat.completions.create(**params)
        message = response.choices[0].message
        
        # Map OpenAI response to Converse-like format for uniformity
        content = []
        if message.content:
            content.append({"text": message.content})
            
        stop_reason = "end_turn"
        if message.tool_calls:
            stop_reason = "tool_use"
            for tc in message.tool_calls:
                content.append({
                    "toolUse": {
                        "name": tc.function.name,
                        "input": json.loads(tc.function.arguments),
                        "toolUseId": tc.id
                    }
                })
                
        return {
            "stopReason": stop_reason,
            "output": {"message": {"content": content}}
        }

    async def _call_bedrock(self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Call AWS Bedrock Converse API via CLI or boto3."""
        # Simple implementation for now - replicate the CLI approach from streamlit_app.py
        import subprocess
        
        # Reformat messages for Bedrock
        converse_messages = []
        for msg in messages:
            content = []
            if isinstance(msg["content"], str):
                content.append({"text": msg["content"]})
            else:
                # Handle tool results etc if needed
                pass
            converse_messages.append({"role": msg["role"], "content": content})
            
        model_id = self.model or "anthropic.claude-3-5-sonnet-20240620-v1:0"
        
        cmd = [
            "aws", "bedrock-runtime", "converse",
            "--model-id", model_id,
            "--messages", json.dumps(converse_messages),
            "--system", json.dumps([{"text": SYSTEM_PROMPT}])
        ]
        
        # Simplified: tools not included in this basic CLI implementation for now
        # to focus on getting it running.
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Bedrock CLI error: {result.stderr}")
            
        return json.loads(result.stdout)

    async def query(self, user_query: str, verbose: bool = True):
        """Execute a full agentic query loop."""
        print(f"\n>>> Query: {user_query}")
        
        # 1. Memory Recall
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
        
        # 2. Main Loop
        current_query = memory_context + user_query
        self.messages.append({"role": "user", "content": current_query})
        
        max_iterations = 10
        for i in range(max_iterations):
            # Define tools (get them from the server list)
            from mcp_server.fhir_graphrag_mcp_server import list_tools
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
            
            # Call LLM
            response = await self._call_llm(self.messages, converse_tools)
            
            stop_reason = response.get('stopReason')
            output_message = response.get('output', {}).get('message', {})
            content = output_message.get('content', [])
            
            # Add assistant message to history (standard format)
            # LLM response content might need flattening for simple history
            assistant_text = ""
            for block in content:
                if "text" in block:
                    assistant_text += block["text"]
            
            if stop_reason == "end_turn":
                print(f"\nAssistant: {assistant_text}")
                return
            
            if stop_reason == "tool_use":
                if assistant_text:
                    print(f"\nAssistant (thinking): {assistant_text}")
                
                tool_results = []
                for block in content:
                    if "toolUse" in block:
                        tool_use = block["toolUse"]
                        t_name = tool_use["name"]
                        t_input = tool_use["input"]
                        t_id = tool_use["toolUseId"]
                        
                        # Execute tool
                        result = await call_tool(t_name, t_input)
                        result_data = json.loads(result[0].text)
                        
                        if verbose:
                            self._print_trace(i+1, t_name, t_input, result_data)
                        
                        tool_results.append({
                            "toolUseId": t_id,
                            "content": [{"json": result_data}]
                        })
                
                # Add tool results to messages
                # Bedrock format for tool results
                self.messages.append({"role": "assistant", "content": content})
                self.messages.append({"role": "user", "content": tool_results})
                
        print("\nReached maximum iterations.")

async def run_chat_cli(query: str, provider: str = "nim", verbose: bool = True):
    """Entry point for CLI chat."""
    cli = ChatCLI(provider=provider)
    await cli.query(query, verbose=verbose)
