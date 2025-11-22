#!/usr/bin/env python3
"""
Agentic Medical Chat with Tool Use
Claude calls MCP tools autonomously based on user questions
"""

import streamlit as st
import asyncio
import json
import subprocess
import os
import sys
import plotly.graph_objects as go

# Add parent directory to sys.path for src module imports  
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from fhir_graphrag_mcp_server import call_tool

st.set_page_config(page_title="Agentic Medical Chat", page_icon="🤖", layout="wide")

# Set AWS profile


# Initialize
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'bedrock_available' not in st.session_state:
    # Test if AWS CLI Bedrock works
    try:
        test_cmd = [
            "aws", "bedrock-runtime", "converse",
            "--model-id", "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
            "--messages", json.dumps([{"role": "user", "content": [{"text": "test"}]}])
        ]
        result = subprocess.run(test_cmd, capture_output=True, text=True, env=os.environ.copy(), timeout=10)
        st.session_state.bedrock_available = (result.returncode == 0)
        if not st.session_state.bedrock_available:
            st.warning(f"⚠️ AWS Bedrock not available. Running in demo mode without Claude synthesis.")
    except Exception as e:
        st.session_state.bedrock_available = False
        st.warning(f"⚠️ AWS Bedrock not available ({str(e)}). Running in demo mode without Claude synthesis.")

# Define MCP tools for Claude
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
    },
    {
        "name": "search_knowledge_graph",
        "description": "Search medical knowledge graph for entities (symptoms, conditions, medications, etc.)",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Entity search terms"},
                "limit": {"type": "integer", "description": "Max entities", "default": 5}
            },
            "required": ["query"]
        }
    },
    {
        "name": "hybrid_search",
        "description": "Combined FHIR + Knowledge Graph search with ranking fusion. Best for complex queries.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Medical search query"},
                "top_k": {"type": "integer", "description": "Number of results", "default": 5}
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_document_details",
        "description": "Retrieve full clinical note from a FHIR document by ID",
        "input_schema": {
            "type": "object",
            "properties": {
                "fhir_id": {"type": "string", "description": "Document ID (e.g., '1474')"}
            },
            "required": ["fhir_id"]
        }
    },
    {
        "name": "get_entity_statistics",
        "description": "Get knowledge graph statistics - entity counts, types, distribution",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "plot_symptom_frequency",
        "description": "Generate bar chart data showing most frequent symptoms",
        "input_schema": {
            "type": "object",
            "properties": {
                "top_n": {"type": "integer", "description": "Number of top symptoms", "default": 10}
            }
        }
    },
    {
        "name": "plot_entity_distribution",
        "description": "Generate chart data showing distribution of entity types",
        "input_schema": {
            "type": "object",
            "properties": {
                "chart_type": {"type": "string", "enum": ["pie", "bar"], "default": "bar"}
            }
        }
    },
    {
        "name": "plot_patient_timeline",
        "description": "Generate timeline chart data of patient encounters over time",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "plot_entity_network",
        "description": "Generate network graph visualization of entity relationships",
        "input_schema": {
            "type": "object",
            "properties": {
                "entity": {"type": "string", "description": "Entity to center the network around (optional)"},
                "max_nodes": {"type": "integer", "description": "Maximum number of nodes", "default": 50}
            }
        }
    },
    {
        "name": "visualize_graphrag_results",
        "description": "Visualize GraphRAG search results showing query, entities found, and their relationships",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query used"},
                "limit": {"type": "integer", "description": "Number of results to visualize", "default": 10}
            },
            "required": ["query"]
        }

    },
    {
        "name": "search_medical_images",
        "description": "Search for medical images (X-rays) using text query or metadata.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (e.g., 'chest X-ray of pneumonia')"},
                "limit": {"type": "integer", "description": "Max images", "default": 5}
            },
            "required": ["query"]
        }
    }
]

def execute_mcp_tool(tool_name: str, tool_input: dict):
    """Execute an MCP tool and return results"""
    try:
        result = asyncio.run(call_tool(tool_name, tool_input))
        return json.loads(result[0].text)
    except Exception as e:
        return {"error": str(e)}

def render_chart(tool_name: str, data, unique_id: str = None):
    """Render visualization if tool returns chart data"""
    # Debug logging
    import sys
    import traceback
    import time

    # Generate unique key for this chart instance
    if unique_id is None:
        unique_id = f"{tool_name}_{int(time.time() * 1000000)}"

    print(f"DEBUG render_chart: tool_name={tool_name}, data type={type(data)}, unique_id={unique_id}", file=sys.stderr)
    if isinstance(data, str):
        print(f"DEBUG: data is string, first 200 chars: {data[:200]}", file=sys.stderr)
    elif isinstance(data, dict):
        print(f"DEBUG: data is dict, keys: {data.keys()}", file=sys.stderr)

    try:
        # Handle case where data might be a string (JSON)
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError as e:
                st.error(f"Failed to parse chart data: {e}")
                st.code(data[:500], language="text")
                print(f"ERROR: JSON decode failed: {e}", file=sys.stderr)
                print(f"ERROR: Full traceback:\n{traceback.format_exc()}", file=sys.stderr)
                return False

        # Check if data is a dict
        if not isinstance(data, dict):
            st.error(f"Chart data is not a dict: {type(data)}")
            print(f"ERROR: Data is not dict: {type(data)}", file=sys.stderr)
            return False

        if tool_name == "plot_symptom_frequency":
            fig = go.Figure(data=[go.Bar(
                x=data["data"]["symptoms"],
                y=data["data"]["frequencies"],
                marker_color='lightcoral'
            )])
            fig.update_layout(title="Most Frequent Symptoms", height=400)
            st.plotly_chart(fig, key=unique_id, use_container_width=True)
            return True

        elif tool_name == "plot_entity_distribution":
            if data.get("chart_type") == "pie":
                fig = go.Figure(data=[go.Pie(
                    labels=data["data"]["labels"],
                    values=data["data"]["values"]
                )])
            else:
                fig = go.Figure(data=[go.Bar(
                    x=data["data"]["labels"],
                    y=data["data"]["values"],
                    marker_color='steelblue'
                )])
            fig.update_layout(title="Entity Type Distribution", height=400)
            st.plotly_chart(fig, key=unique_id, use_container_width=True)
            return True

        elif tool_name == "plot_patient_timeline":
            fig = go.Figure(data=[go.Scatter(
                x=data["data"]["dates"],
                y=data["data"]["counts"],
                mode='lines+markers',
                line=dict(color='green', width=2)
            )])
            fig.update_layout(title="Patient Timeline", height=400)
            st.plotly_chart(fig, key=unique_id, use_container_width=True)
            return True

        elif tool_name == "plot_entity_network":
            # Create network graph visualization
            nodes = data["data"]["nodes"]
            edges = data["data"]["edges"]

            # Extract node and edge data
            node_x = [n["x"] for n in nodes]
            node_y = [n["y"] for n in nodes]
            node_text = [f"{n['name']}<br>Type: {n['type']}" for n in nodes]

            # Create edge traces
            edge_traces = []
            for edge in edges:
                x0, y0 = nodes[edge["source"]]["x"], nodes[edge["source"]]["y"]
                x1, y1 = nodes[edge["target"]]["x"], nodes[edge["target"]]["y"]
                edge_traces.append(go.Scatter(
                    x=[x0, x1, None],
                    y=[y0, y1, None],
                    mode='lines',
                    line=dict(width=0.5, color='#888'),
                    hoverinfo='none',
                    showlegend=False
                ))

            # Create node trace
            node_trace = go.Scatter(
                x=node_x,
                y=node_y,
                mode='markers+text',
                text=[n["name"] for n in nodes],
                textposition="top center",
                hovertext=node_text,
                hoverinfo='text',
                marker=dict(
                    size=10,
                    color=[n.get("color", "lightblue") for n in nodes],
                    line=dict(width=2, color='white')
                )
            )

            # Create figure
            fig = go.Figure(data=edge_traces + [node_trace])
            fig.update_layout(
                title="Entity Relationship Network",
                showlegend=False,
                hovermode='closest',
                margin=dict(b=0, l=0, r=0, t=40),
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                height=600
            )
            st.plotly_chart(fig, key=unique_id, use_container_width=True)
            return True

        elif tool_name == "visualize_graphrag_results":
            # Create GraphRAG results visualization with query node at center
            nodes = data["data"]["nodes"]
            edges = data["data"]["edges"]

            # Extract node and edge data
            node_x = [n["x"] for n in nodes]
            node_y = [n["y"] for n in nodes]
            node_text = [f"{n['name']}<br>Type: {n['type']}" for n in nodes]

            # Different sizes for query node vs entity nodes
            node_sizes = [20 if n.get("type") == "QUERY" else 12 for n in nodes]

            # Create edge traces - different styles for MATCHES vs CO_OCCURS_WITH
            edge_traces = []
            for edge in edges:
                x0, y0 = nodes[edge["source"]]["x"], nodes[edge["source"]]["y"]
                x1, y1 = nodes[edge["target"]]["x"], nodes[edge["target"]]["y"]

                # MATCHES edges (query to entities) are thicker and darker
                if edge.get("type") == "MATCHES":
                    edge_traces.append(go.Scatter(
                        x=[x0, x1, None],
                        y=[y0, y1, None],
                        mode='lines',
                        line=dict(width=1.5, color='#444'),
                        hoverinfo='none',
                        showlegend=False
                    ))
                else:
                    edge_traces.append(go.Scatter(
                        x=[x0, x1, None],
                        y=[y0, y1, None],
                        mode='lines',
                        line=dict(width=0.5, color='#888'),
                        hoverinfo='none',
                        showlegend=False
                    ))

            # Create node trace
            node_trace = go.Scatter(
                x=node_x,
                y=node_y,
                mode='markers+text',
                text=[n["name"] for n in nodes],
                textposition="top center",
                hovertext=node_text,
                hoverinfo='text',
                marker=dict(
                    size=node_sizes,
                    color=[n.get("color", "lightblue") for n in nodes],
                    line=dict(width=2, color='white')
                )
            )

            # Create figure
            fig = go.Figure(data=edge_traces + [node_trace])
            fig.update_layout(
                title=f"GraphRAG Search Results: {data.get('query', 'Unknown Query')} ({data.get('entities_found', 0)} entities found)",
                showlegend=False,
                hovermode='closest',
                margin=dict(b=0, l=0, r=0, t=40),
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                height=600
            )
            st.plotly_chart(fig, key=unique_id, use_container_width=True)

            return True

        elif tool_name == "search_medical_images":
            # T020: Check for fallback and show warning
            search_mode = data.get("search_mode", "unknown")
            fallback_reason = data.get("fallback_reason")
            
            if search_mode == "keyword" and fallback_reason:
                st.warning(f"⚠️ Semantic search unavailable. Using keyword search.")
                st.info(f"Reason: {fallback_reason}")
            
            # Show search statistics
            exec_time = data.get("execution_time_ms", 0)
            cache_hit = data.get("cache_hit", False)
            avg_score = data.get("avg_score")
            
            # Display search metadata
            meta_cols = st.columns(4)
            with meta_cols[0]:
                st.metric("Search Mode", search_mode.title())
            with meta_cols[1]:
                st.metric("Execution Time",  f"{exec_time}ms")
            if search_mode == "semantic":
                with meta_cols[2]:
                    st.metric("Cache", "Hit ✓" if cache_hit else "Miss")
                if avg_score is not None:
                    with meta_cols[3]:
                        st.metric("Avg Score", f"{avg_score:.2f}")
            
            # Render images grid
            images = data.get("images", [])
            if not images:
                st.warning("No images found matching your query.")
                return False
            
            st.subheader(f"Found {len(images)} Images for '{data.get('query', '')}'")
            
            # T019: Create columns for grid layout with score badges
            cols = st.columns(3)
            for idx, img in enumerate(images):
                with cols[idx % 3]:
                    # Get scoring metadata
                    similarity_score = img.get("similarity_score")
                    score_color = img.get("score_color", "gray")
                    confidence_level = img.get("confidence_level", "unknown")
                    
                    # Map color names to hex
                    color_map = {
                        "green": "#28a745",
                        "yellow": "#ffc107",
                        "gray": "#6c757d"
                    }
                    hex_color = color_map.get(score_color, "#6c757d")
                    
                    # Use image path if available, or placeholder
                    img_path = img.get("image_path")
                    view_pos = img.get('view_position', 'Unknown View')
                    subject_id = img.get('subject_id', 'Unknown Patient')
                    
                    # Build caption with score badge
                    caption_html = f"""
                    <div style='text-align: center; margin-bottom: 8px;'>
                        <strong>{view_pos}</strong> - Patient {subject_id}
                    </div>
                    """
                    
                    # Add score badge if available
                    if similarity_score is not None:
                        caption_html += f"""
                        <div style='
                            background-color: {hex_color}; 
                            color: white;  
                            padding: 6px 12px; 
                            border-radius: 4px; 
                            text-align: center;
                            font-weight: bold;
                            margin-top: 4px;
                        '>
                            Score: {similarity_score:.2f} ({confidence_level})
                        </div>
                        """
                    
                    # Display caption with HTML
                    st.markdown(caption_html, unsafe_allow_html=True)
                    
                    try:
                        if img_path and os.path.exists(img_path):
                            st.image(img_path, use_container_width=True)
                        else:
                            # Fallback if local path not found
                            st.warning(f"Image not found: {os.path.basename(img_path) if img_path else 'N/A'}")
                            st.info(f"{view_pos} - Patient {subject_id}")
                    except Exception as e:
                        st.error(f"Error loading image: {e}")
            return True

        return False

    except Exception as e:
        error_msg = f"❌ RENDER ERROR: {str(e)}"
        st.error(error_msg)
        print(f"\n{'='*60}", file=sys.stderr)
        print(f"FATAL ERROR in render_chart:", file=sys.stderr)
        print(f"Tool: {tool_name}", file=sys.stderr)
        print(f"Error: {e}", file=sys.stderr)
        print(f"Full traceback:\n{traceback.format_exc()}", file=sys.stderr)
        print(f"{'='*60}\n", file=sys.stderr)
        return False

def demo_mode_search(user_message: str):
    """Demo mode without Claude - directly execute MCP tools based on keywords"""
    query_lower = user_message.lower()

    status = st.empty()
    status.write("🔍 Running in demo mode (no Claude) - executing direct search...")

    try:
        # Check for visualization requests
        if "plot" in query_lower or "chart" in query_lower or "visualize" in query_lower:
            if "symptom" in query_lower and ("frequency" in query_lower or "common" in query_lower):
                result = asyncio.run(call_tool("plot_symptom_frequency", {"top_n": 10}))
                data = json.loads(result[0].text)
                fig = go.Figure(data=[go.Bar(
                    x=data["data"]["symptoms"],
                    y=data["data"]["frequencies"],
                    marker_color='lightcoral'
                )])
                fig.update_layout(title="Most Frequent Symptoms", height=400)
                st.plotly_chart(fig, use_container_width=True)
                status.empty()
                return "Chart displayed above showing top 10 symptoms."

            elif "entity" in query_lower or "distribution" in query_lower:
                result = asyncio.run(call_tool("plot_entity_distribution", {"chart_type": "bar"}))
                data = json.loads(result[0].text)
                fig = go.Figure(data=[go.Bar(
                    x=data["data"]["labels"],
                    y=data["data"]["values"],
                    marker_color='steelblue'
                )])
                fig.update_layout(title="Entity Type Distribution", height=400)
                st.plotly_chart(fig, use_container_width=True)
                status.empty()
                return "Chart displayed above showing entity distribution."

        # Check for image search
        if "image" in query_lower or "x-ray" in query_lower or "scan" in query_lower:
            result = asyncio.run(call_tool("search_medical_images", {"query": user_message, "limit": 3}))
            data = json.loads(result[0].text)
            
            # Render images manually for demo mode since we return text here
            # But wait, chat_with_tools expects text return from demo_mode_search
            # And it doesn't render charts/images from the return value of demo_mode_search
            # demo_mode_search renders charts directly using st.plotly_chart
            # So we should render images directly here too
            
            images = data.get("images", [])
            if images:
                st.subheader(f"Found {len(images)} Images (Demo Mode)")
                cols = st.columns(3)
                for idx, img in enumerate(images):
                    with cols[idx % 3]:
                        img_path = img.get("image_path")
                        caption = f"{img.get('view_position', 'Unknown')} - {img.get('subject_id', 'Unknown')}"
                        if img_path and os.path.exists(img_path):
                            st.image(img_path, caption=caption, use_container_width=True)
                        else:
                            st.info(f"Image: {caption}")
                
                status.empty()
                return f"Found {len(images)} images for your query."
            else:
                return "No images found matching your query."

        # Otherwise do hybrid search
        result = asyncio.run(call_tool("hybrid_search", {"query": user_message, "top_k": 5}))
        data = json.loads(result[0].text)

        status.empty()
        response = f"**Search Results** (Demo Mode)\n\n"
        response += f"- FHIR results: {data['fhir_results']}\n"
        response += f"- GraphRAG results: {data['graphrag_results']}\n"
        response += f"- Fused results: {data['fused_results']}\n\n"

        if data['top_documents']:
            response += "**Top Documents:**\n"
            for doc in data['top_documents']:
                sources = ", ".join(doc['sources'])
                response += f"- Document {doc['fhir_id']} (score: {doc['rrf_score']:.4f}, sources: {sources})\n"

        return response

    except Exception as e:
        status.empty()
        return f"❌ Error in demo mode: {str(e)}"

def call_claude_via_cli(messages, tools=None):
    """Call Claude via AWS CLI instead of boto3"""

    # Convert to Converse API format
    converse_messages = []
    for msg in messages:
        if msg["role"] == "user":
            if isinstance(msg["content"], str):
                converse_messages.append({
                    "role": "user",
                    "content": [{"text": msg["content"]}]
                })
            elif isinstance(msg["content"], list):
                # Tool results
                content_blocks = []
                for block in msg["content"]:
                    if block.get("type") == "tool_result":
                        content_blocks.append({
                            "toolResult": {
                                "toolUseId": block["tool_use_id"],
                                "content": [{"text": block["content"]}]
                            }
                        })
                if content_blocks:
                    converse_messages.append({"role": "user", "content": content_blocks})
        elif msg["role"] == "assistant":
            # Convert assistant content
            content_blocks = []

            # Handle case where content is a string (error messages or simple text)
            if isinstance(msg["content"], str):
                content_blocks.append({"text": msg["content"]})
            elif isinstance(msg["content"], dict) and "text" in msg["content"]:
                # Handle dict with text key (from our chart responses)
                content_blocks.append({"text": msg["content"]["text"]})
            elif isinstance(msg["content"], list):
                # Handle list of content blocks (standard Messages API format)
                for block in msg["content"]:
                    # Type check first before any dict operations
                    if isinstance(block, str):
                        # Handle string content blocks
                        content_blocks.append({"text": block})
                    elif isinstance(block, dict):
                        # Safe to use .get() now that we've confirmed it's a dict
                        block_type = block.get("type")
                        if block_type == "text":
                            content_blocks.append({"text": block.get("text", "")})
                        elif block_type == "tool_use":
                            content_blocks.append({
                                "toolUse": {
                                    "toolUseId": block.get("id", ""),
                                    "name": block.get("name", ""),
                                    "input": block.get("input", {})
                                }
                            })
                    else:
                        # Log unexpected block type and skip
                        print(f"Warning: Unexpected block type in assistant message: {type(block)}", file=sys.stderr)

            if content_blocks:
                converse_messages.append({"role": "assistant", "content": content_blocks})

    cmd = [
        "aws", "bedrock-runtime", "converse",
        "--model-id", "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "--messages", json.dumps(converse_messages)
    ]

    if tools:
        cmd.extend(["--tool-config", json.dumps({"tools": tools})])

    cmd.extend(["--inference-config", json.dumps({"maxTokens": 4000})])

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=os.environ.copy(),
        timeout=30
    )

    if result.returncode != 0:
        raise Exception(f"AWS CLI error: {result.stderr}")

    return json.loads(result.stdout)

def chat_with_tools(user_message: str):
    """Chat with Claude using tool use"""

    # If no Claude, run in demo mode
    if not st.session_state.bedrock_available:
        return demo_mode_search(user_message)

    # Enhance user message if it's asking for visualization
    viz_keywords = ['plot', 'chart', 'graph', 'visualize', 'show me', 'display']
    if any(keyword in user_message.lower() for keyword in viz_keywords):
        # Add explicit instruction to use visualization tools
        user_message = user_message + "\n\n[IMPORTANT: Use the appropriate plot_* tool to create a visualization. Available: plot_entity_network, plot_symptom_frequency, plot_entity_distribution, plot_patient_timeline]"

    # Build conversation history from session state, converting to simple format for API
    messages = []
    for msg in st.session_state.messages:
        # Skip malformed messages
        if not isinstance(msg, dict) or "role" not in msg:
            continue

        # Extract just the text content for conversation history
        if msg["role"] == "user":
            messages.append({"role": "user", "content": msg["content"]})
        elif msg["role"] == "assistant":
            # Extract text from assistant messages
            if isinstance(msg["content"], dict) and "text" in msg["content"]:
                messages.append({"role": "assistant", "content": msg["content"]["text"]})
            else:
                messages.append({"role": "assistant", "content": msg["content"]})

    # Add the new user message
    messages.append({"role": "user", "content": user_message})

    status = st.empty()
    chart_container = st.container()
    text_container = st.container()

    # Track charts rendered in this conversation
    rendered_charts = []

    # Track tool execution details for transparency
    tool_execution_log = []

    max_iterations = 10  # Increased from 5 to handle complex multi-tool queries
    iteration = 0

    while iteration < max_iterations:
        iteration += 1

        try:
            # Convert MCP tools to Converse API format
            converse_tools = []
            for tool in MCP_TOOLS:
                converse_tools.append({
                    "toolSpec": {
                        "name": tool["name"],
                        "description": tool["description"],
                        "inputSchema": {"json": tool["input_schema"]}
                    }
                })

            # Call Claude via AWS CLI
            response = call_claude_via_cli(messages, converse_tools if converse_tools else None)

            # Process response
            stop_reason = response.get('stopReason')
            output_message = response.get('output', {}).get('message', {})
            content = output_message.get('content', [])

            # Add assistant response to messages
            messages.append({"role": "assistant", "content": content})

            # Handle tool use
            if stop_reason == "tool_use":
                status.write(f"🔧 Claude is calling tools... (iteration {iteration})")

                # Convert Converse API format back to Messages API format for internal processing
                messages_api_content = []
                tool_results = []

                for block in content:
                    if 'toolUse' in block:
                        tool_use_block = block['toolUse']
                        tool_name = tool_use_block['name']
                        tool_input = tool_use_block['input']
                        tool_use_id = tool_use_block['toolUseId']

                        status.write(f"⚙️ Executing: {tool_name}")

                        # Execute the MCP tool
                        result = execute_mcp_tool(tool_name, tool_input)

                        # Log tool execution
                        tool_execution_log.append({
                            "iteration": iteration,
                            "tool_name": tool_name,
                            "tool_input": tool_input,
                            "result_summary": str(result)[:200] + "..." if len(str(result)) > 200 else str(result)
                        })

                        # Render chart if applicable and track it (only for visualization tools)
                        visualization_tools = ["plot_symptom_frequency", "plot_entity_distribution",
                                             "plot_patient_timeline", "plot_entity_network", 
                                             "visualize_graphrag_results", "search_medical_images"]
                        if tool_name in visualization_tools:
                            with chart_container:
                                was_chart = render_chart(tool_name, result)
                                if was_chart:
                                    # Save chart data for re-rendering
                                    rendered_charts.append({
                                        "tool_name": tool_name,
                                        "data": result
                                    })

                        # Store in Messages API format for next iteration
                        messages_api_content.append({
                            "type": "tool_use",
                            "id": tool_use_id,
                            "name": tool_name,
                            "input": tool_input
                        })

                        # Add tool result
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": json.dumps(result)
                        })
                    elif 'text' in block:
                        # Capture thinking/reasoning text
                        thinking_text = block['text']
                        if thinking_text.strip():
                            tool_execution_log.append({
                                "iteration": iteration,
                                "type": "thinking",
                                "content": thinking_text
                            })
                        messages_api_content.append({
                            "type": "text",
                            "text": thinking_text
                        })

                # Update last assistant message with Messages API format
                if messages and messages[-1]["role"] == "assistant":
                    messages[-1]["content"] = messages_api_content

                # Add tool results to conversation
                messages.append({"role": "user", "content": tool_results})

            elif stop_reason == "end_turn":
                # Claude is done - extract final text
                status.empty()
                final_text = ""
                for block in content:
                    if 'text' in block:
                        final_text += block['text']

                with text_container:
                    st.write(final_text)

                # Return text with chart data and execution log
                result = {"text": final_text}

                if rendered_charts:
                    result["chart_data"] = rendered_charts[0] if len(rendered_charts) == 1 else rendered_charts

                if tool_execution_log:
                    result["execution_log"] = tool_execution_log

                return result if len(result) > 1 else final_text

            else:
                status.empty()
                return "Unexpected stop reason: " + stop_reason

        except Exception as e:
            status.empty()
            import sys
            import traceback
            error_msg = f"❌ Error: {str(e)}"
            st.error(error_msg)
            print(f"\n{'='*60}", file=sys.stderr)
            print(f"EXCEPTION in chat_with_tools:", file=sys.stderr)
            print(f"Error: {e}", file=sys.stderr)
            print(f"Full traceback:\n{traceback.format_exc()}", file=sys.stderr)
            print(f"{'='*60}\n", file=sys.stderr)
            return error_msg

    # Max iterations reached - return what we have so far
    status.empty()
    error_msg = f"⚠️ Query exceeded maximum iterations ({max_iterations}). Claude called too many tools without completing. This may indicate the query is too complex or ambiguous."

    result = {"text": error_msg}
    if tool_execution_log:
        result["execution_log"] = tool_execution_log

    return result

# UI
st.title("🤖 Agentic Medical Chat")
st.caption("Claude autonomously calls MCP tools to answer your questions")
st.caption("🔧 **Build: v2.10.2** (Fixed 'str' object has no attribute 'get' error with proper type checking)")

# Sidebar
with st.sidebar:
    st.header("🔧 Available Tools")
    for tool in MCP_TOOLS:
        st.write(f"• {tool['name']}")

    st.divider()
    if st.button("🗑️ Clear"):
        st.session_state.messages = []
        st.rerun()

# Display chat
for idx, msg in enumerate(st.session_state.messages):
    # Debug logging
    import sys
    print(f"\n=== MESSAGE {idx} ===", file=sys.stderr)
    print(f"Type: {type(msg)}", file=sys.stderr)
    print(f"Value: {msg}", file=sys.stderr)

    # Skip malformed messages
    if not isinstance(msg, dict) or "role" not in msg:
        print(f"SKIPPING malformed message {idx}", file=sys.stderr)
        continue

    with st.chat_message(msg["role"]):
        # Check if message has chart data - need to safely handle old message formats
        content = msg.get("content") if isinstance(msg, dict) else None
        if isinstance(content, dict) and "chart_data" in content:
            chart_data = content["chart_data"]

            # Handle single or multiple charts
            if isinstance(chart_data, list):
                for i, chart_info in enumerate(chart_data):
                    unique_id = f"{chart_info['tool_name']}_msg{idx}_chart{i}"
                    render_chart(chart_info["tool_name"], chart_info["data"], unique_id)
            else:
                unique_id = f"{chart_data['tool_name']}_msg{idx}"
                render_chart(chart_data["tool_name"], chart_data["data"], unique_id)

            # Also show the text if present
            if "text" in content:
                st.write(content["text"])

            # Show execution log in expandable section if present
            if "execution_log" in content:
                with st.expander("🔍 **Show Execution Details** (Tools & Thinking)", expanded=False):
                    st.caption("Click to see what tools Claude used and how it reasoned through your question")
                    execution_log = content["execution_log"]

                    for i, log_entry in enumerate(execution_log):
                        if log_entry.get("type") == "thinking":
                            st.markdown(f"**💭 Iteration {log_entry['iteration']} - Thinking:**")
                            st.info(log_entry["content"])
                        else:
                            st.markdown(f"**⚙️ Iteration {log_entry['iteration']} - Tool Call:**")
                            st.markdown(f"**Tool:** `{log_entry['tool_name']}`")
                            st.markdown(f"**Input:** `{json.dumps(log_entry['tool_input'], indent=2)}`")
                            with st.expander(f"Result preview (first 200 chars)", expanded=False):
                                st.code(log_entry['result_summary'], language='json')
        else:
            # Display content safely - it might be a string or None
            if content is not None:
                st.write(content)

# Examples
st.write("**💡 Examples:**")
examples = [
    "What are the most common symptoms?",
    "Show me a chart of symptom frequency",
    "Search for chest pain cases",
    "What's in the knowledge graph?",
    "Plot entity distribution",
    "Show me chest X-rays of pneumonia"
]

cols = st.columns(len(examples))
for idx, (col, ex) in enumerate(zip(cols, examples)):
    with col:
        if st.button(ex[:12] + "...", key=f"ex_{idx}", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": ex})
            st.rerun()

st.divider()

# Process last user message if not yet answered
if st.session_state.messages and isinstance(st.session_state.messages[-1], dict) and st.session_state.messages[-1].get("role") == "user":
    last_msg = st.session_state.messages[-1]["content"]

    with st.chat_message("user"):
        st.write(last_msg)

    with st.chat_message("assistant"):
        answer = chat_with_tools(last_msg)
        st.session_state.messages.append({"role": "assistant", "content": answer})
        st.rerun()

# Chat input
if prompt := st.chat_input("Ask anything..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()
