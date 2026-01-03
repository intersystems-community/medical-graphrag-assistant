"""
Unit tests for Hybrid Search Service.
Mocks IRIS connection to verify RRF fusion and service delegation logic.
"""

import pytest
from unittest.mock import MagicMock, patch
from src.search.hybrid_search import HybridSearchService

@pytest.fixture
def mock_search_services():
    """Fixture to mock sub-search services."""
    with patch('src.search.hybrid_search.FHIRSearchService') as mock_fhir, \
         patch('src.search.hybrid_search.KGSearchService') as mock_kg:
        
        # Setup mock FHIR results
        mock_fhir_instance = mock_fhir.return_value
        mock_fhir_instance.search_documents.return_value = [
            {"fhir_id": "1", "preview": "doc 1", "relevance": 10},
            {"fhir_id": "2", "preview": "doc 2", "relevance": 5}
        ]
        
        # Setup mock KG results
        mock_kg_instance = mock_kg.return_value
        mock_kg_instance.search_entities.return_value = {
            "entities": [
                {"text": "fever", "resource_id": "2", "confidence": 0.9},
                {"text": "chills", "resource_id": "3", "confidence": 0.8}
            ]
        }
        
        yield mock_fhir_instance, mock_kg_instance

def test_rrf_fusion_logic(mock_search_services):
    """Verify that RRF correctly fuses results from multiple sources."""
    mock_fhir, mock_kg = mock_search_services
    
    # Initialize service (will use mocked sub-services)
    service = HybridSearchService()
    
    # Execute search
    results = service.search("fever")
    
    # Verify top results
    top_docs = results["top_documents"]
    assert len(top_docs) > 0
    
    # Document 2 should be boosted because it's in both FHIR and KG
    # RRF score for Doc 2: 1/(60+2) [FHIR rank 2] + 1/(60+1) [KG rank 1]
    doc2 = next(d for d in top_docs if d["fhir_id"] == "2")
    assert "fhir" in doc2["sources"]
    assert "kg" in doc2["sources"]
    
    # Document 1 only in FHIR
    doc1 = next(d for d in top_docs if d["fhir_id"] == "1")
    assert "fhir" in doc1["sources"]
    assert "kg" not in doc1["sources"]

def test_service_closure():
    """Verify that close() delegates to sub-services."""
    with patch('src.search.hybrid_search.FHIRSearchService') as mock_fhir, \
         patch('src.search.hybrid_search.KGSearchService') as mock_kg:
        
        service = HybridSearchService()
        service.close()
        
        mock_fhir.return_value.close.assert_called_once()
        mock_kg.return_value.close.assert_called_once()
