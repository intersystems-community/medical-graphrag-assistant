"""
Unit tests for MCP tool wrappers.
Verifies that call_tool correctly delegates to service layer (FR-004).
"""

import pytest
import json
import sys
import os
import pytest
import json
from unittest.mock import MagicMock, patch, AsyncMock
from mcp.types import TextContent

mcp_server_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../mcp-server'))
if mcp_server_path not in sys.path:
    sys.path.insert(0, mcp_server_path)

mock_server = MagicMock()
mock_server.call_tool.return_value = lambda x: x 

with patch('mcp.server.Server', return_value=mock_server):
    import fhir_graphrag_mcp_server
    call_tool = fhir_graphrag_mcp_server.call_tool

@pytest.mark.asyncio
@patch('fhir_graphrag_mcp_server.FHIRSearchService')
@patch('fhir_graphrag_mcp_server.get_connection')
async def test_search_fhir_documents_wrapper(mock_conn, mock_service_class):
    """Verify search_fhir_documents tool calls the search service."""
    # Setup mocks
    mock_service_instance = mock_service_class.return_value
    mock_service_instance.search_documents.return_value = [
        {"fhir_id": "123", "preview": "test preview", "relevance": 5}
    ]
    
    # Execute tool
    arguments = {"query": "test query", "limit": 5}
    result = await call_tool("search_fhir_documents", arguments)
    
    # Verify result
    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    
    data = json.loads(result[0].text)
    assert data["query"] == "test query"
    assert len(data["documents"]) == 1
    assert data["documents"][0]["fhir_id"] == "123"

@pytest.mark.asyncio
@patch('fhir_graphrag_mcp_server.KGSearchService')
@patch('fhir_graphrag_mcp_server.get_connection')
async def test_search_knowledge_graph_wrapper(mock_conn, mock_service_class):
    """Verify search_knowledge_graph tool calls the KG service."""
    # Setup mocks
    mock_service_instance = mock_service_class.return_value
    mock_service_instance.search_entities.return_value = {
        "entities": [{"id": 1, "text": "entity", "type": "T", "confidence": 0.9}],
        "documents": []
    }
    
    # Execute tool
    arguments = {"query": "kg query"}
    result = await call_tool("search_knowledge_graph", arguments)
    
    # Verify
    assert len(result) == 1
    data = json.loads(result[0].text)
    assert "entities" in data
    assert data["entities"][0]["text"] == "entity"
