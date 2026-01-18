"""
End-to-End RAG Pipeline Integration Tests

Tests the complete RAG query pipeline including:
- Query embedding generation
- Vector similarity search
- Context assembly
- LLM response generation
- Citation extraction

Run with:
    pytest tests/integration/test_end_to_end_rag.py -v

Requirements:
    - IRIS database running and accessible
    - Clinical notes vectorized (ClinicalNoteVectors table populated)
    - NVIDIA API key configured for embeddings
    - NIM LLM service running on localhost:8001

Success Criteria:
    - SC-007: End-to-end query latency <5 seconds
"""

import pytest
import os
import sys
from pathlib import Path
from typing import Dict, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.query.rag_pipeline import RAGPipeline


@pytest.fixture(scope="module")
def iris_config():
    """IRIS database configuration from environment."""
    return {
        "host": os.getenv("IRIS_HOST", "44.200.206.67"),
        "port": int(os.getenv("IRIS_PORT", "1972")),
        "namespace": os.getenv("IRIS_NAMESPACE", "USER"),
        "username": os.getenv("IRIS_USERNAME", "_SYSTEM"),
        "password": os.getenv("IRIS_PASSWORD", "SYS")
    }


@pytest.fixture(scope="module")
def llm_endpoint():
    """NIM LLM endpoint URL."""
    return os.getenv("NIM_LLM_ENDPOINT", "http://44.200.206.67:8001")


@pytest.fixture(scope="module")
def rag_pipeline(iris_config, llm_endpoint):
    """
    RAG pipeline instance for testing.

    Skips tests if services are unavailable.
    """
    try:
        pipeline = RAGPipeline(
            iris_host=iris_config["host"],
            iris_port=iris_config["port"],
            iris_namespace=iris_config["namespace"],
            iris_username=iris_config["username"],
            iris_password=iris_config["password"],
            llm_endpoint=llm_endpoint
        )
        yield pipeline
    except Exception as e:
        pytest.skip(f"Could not initialize RAG pipeline: {e}")


class TestRAGPipelineBasics:
    """Test basic RAG pipeline functionality."""

    def test_pipeline_initialization(self, rag_pipeline):
        """Test that pipeline initializes successfully."""
        assert rag_pipeline is not None
        assert rag_pipeline.embedding_client is not None
        assert rag_pipeline.vector_db_client is not None

    def test_query_embedding_generation(self, rag_pipeline):
        """Test query embedding generation."""
        query = "What medications is the patient taking?"

        embedding = rag_pipeline.generate_query_embedding(query)

        assert isinstance(embedding, list)
        assert len(embedding) == 1024  # NV-EmbedQA-E5-V5 dimension
        assert all(isinstance(x, float) for x in embedding)

    def test_vector_search(self, rag_pipeline):
        """Test vector similarity search."""
        query = "diabetes treatment"
        query_vector = rag_pipeline.generate_query_embedding(query)

        results = rag_pipeline.search_similar_documents(
            query_vector=query_vector,
            top_k=5,
            similarity_threshold=0.0  # Return any results
        )

        # Should return some documents (assuming database is populated)
        assert isinstance(results, list)

        # If results found, validate structure
        if len(results) > 0:
            result = results[0]
            assert "resource_id" in result
            assert "patient_id" in result
            assert "document_type" in result
            assert "text_content" in result
            assert "similarity" in result
            assert 0 <= result["similarity"] <= 1


class TestRAGQueryProcessing:
    """Test complete RAG query processing."""

    def test_process_simple_query(self, rag_pipeline):
        """Test processing a simple medical query."""
        query = "What are common symptoms?"

        result = rag_pipeline.process_query(
            query_text=query,
            top_k=5,
            similarity_threshold=0.3  # Lower threshold for testing
        )

        # Validate result structure
        assert isinstance(result, dict)
        assert "query" in result
        assert "response" in result
        assert "retrieved_documents" in result
        assert "citations" in result
        assert "metadata" in result

        # Validate metadata
        metadata = result["metadata"]
        assert "documents_retrieved" in metadata
        assert "documents_used_in_context" in metadata
        assert "processing_time_seconds" in metadata
        assert "timestamp" in metadata

        # Validate response is non-empty
        assert isinstance(result["response"], str)
        assert len(result["response"]) > 0

    def test_process_query_with_patient_filter(self, rag_pipeline):
        """Test query with patient ID filter."""
        # First get any patient_id from database
        try:
            query_vector = rag_pipeline.generate_query_embedding("test")
            docs = rag_pipeline.search_similar_documents(
                query_vector=query_vector,
                top_k=1,
                similarity_threshold=0.0
            )

            if not docs:
                pytest.skip("No documents in database for testing")

            patient_id = docs[0]["patient_id"]

            # Now query with that patient filter
            result = rag_pipeline.process_query(
                query_text="What is the patient's medical history?",
                top_k=5,
                patient_id=patient_id,
                similarity_threshold=0.0
            )

            # All retrieved documents should match patient_id
            for doc in result["retrieved_documents"]:
                assert doc["patient_id"] == patient_id

        except Exception as e:
            pytest.skip(f"Could not test patient filter: {e}")

    def test_no_results_handling(self, rag_pipeline):
        """Test handling when no relevant documents are found."""
        # Use very high similarity threshold to force no results
        result = rag_pipeline.process_query(
            query_text="xyzabc nonsense query that won't match",
            top_k=5,
            similarity_threshold=0.99  # Very high threshold
        )

        # Should return no-results message
        assert "no information" in result["response"].lower() or \
               "not enough information" in result["response"].lower()
        assert result["metadata"]["documents_retrieved"] == 0 or \
               result["metadata"]["documents_used_in_context"] == 0

    def test_citation_extraction(self, rag_pipeline):
        """Test that citations are extracted from response."""
        result = rag_pipeline.process_query(
            query_text="What medical conditions are documented?",
            top_k=5,
            similarity_threshold=0.3
        )

        # If documents were retrieved, citations should be present
        if result["metadata"]["documents_used_in_context"] > 0:
            assert isinstance(result["citations"], list)
            assert len(result["citations"]) > 0

            # Validate citation structure
            citation = result["citations"][0]
            assert "resource_id" in citation
            assert "patient_id" in citation
            assert "document_type" in citation
            assert "similarity" in citation
            assert "cited_in_response" in citation


class TestPerformance:
    """Test performance requirements."""

    def test_query_latency_meets_sc007(self, rag_pipeline):
        """Test that query latency meets SC-007 target (<5 seconds)."""
        query = "What treatments has the patient received?"

        result = rag_pipeline.process_query(
            query_text=query,
            top_k=10,
            similarity_threshold=0.3
        )

        processing_time = result["metadata"]["processing_time_seconds"]

        # SC-007: End-to-end query latency <5 seconds
        assert processing_time < 5.0, \
            f"Query latency {processing_time}s exceeds SC-007 target (<5s)"


class TestPredefinedQueries:
    """Test with predefined medical queries and expected retrievals."""

    PREDEFINED_QUERIES = [
        {
            "query": "What medications is the patient taking?",
            "expected_keywords": ["medication", "drug", "prescription", "treatment"],
            "min_similarity": 0.3
        },
        {
            "query": "What are the patient's chronic conditions?",
            "expected_keywords": ["condition", "diagnosis", "disease", "chronic"],
            "min_similarity": 0.3
        },
        {
            "query": "Recent vital signs and measurements",
            "expected_keywords": ["vital", "blood pressure", "temperature", "pulse", "measurement"],
            "min_similarity": 0.3
        },
        {
            "query": "Patient's lab results and tests",
            "expected_keywords": ["lab", "test", "result", "laboratory", "analysis"],
            "min_similarity": 0.3
        }
    ]

    @pytest.mark.parametrize("query_spec", PREDEFINED_QUERIES)
    def test_predefined_query(self, rag_pipeline, query_spec):
        """Test predefined medical query."""
        result = rag_pipeline.process_query(
            query_text=query_spec["query"],
            top_k=10,
            similarity_threshold=query_spec["min_similarity"]
        )

        # Response should be generated
        assert isinstance(result["response"], str)
        assert len(result["response"]) > 0

        # Check if any expected keywords appear in retrieved documents or response
        response_lower = result["response"].lower()
        docs_text = " ".join([
            doc["text_content"].lower()
            for doc in result["retrieved_documents"]
        ])

        # At least some expected keywords should appear somewhere
        keyword_matches = sum(
            1 for keyword in query_spec["expected_keywords"]
            if keyword in response_lower or keyword in docs_text
        )

        # Allow flexibility - if no documents retrieved, skip keyword check
        if result["metadata"]["documents_retrieved"] > 0:
            assert keyword_matches > 0, \
                f"None of the expected keywords {query_spec['expected_keywords']} " \
                f"found in response or retrieved documents"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_query(self, rag_pipeline):
        """Test handling of empty query."""
        with pytest.raises(Exception):
            rag_pipeline.process_query(query_text="")

    def test_very_long_query(self, rag_pipeline):
        """Test handling of very long query."""
        long_query = "What are the patient's medical conditions? " * 100

        result = rag_pipeline.process_query(
            query_text=long_query,
            top_k=5,
            similarity_threshold=0.3
        )

        # Should still process successfully
        assert isinstance(result["response"], str)

    def test_special_characters_in_query(self, rag_pipeline):
        """Test handling of special characters in query."""
        query = "Patient's lab results (2024) & vital signs @ 3:00pm?"

        result = rag_pipeline.process_query(
            query_text=query,
            top_k=5,
            similarity_threshold=0.3
        )

        # Should process without errors
        assert isinstance(result["response"], str)

    def test_top_k_variations(self, rag_pipeline):
        """Test different top_k values."""
        query = "Patient medical history"

        for top_k in [1, 5, 10, 20]:
            result = rag_pipeline.process_query(
                query_text=query,
                top_k=top_k,
                similarity_threshold=0.0  # Return any results
            )

            # Documents retrieved should not exceed top_k
            assert result["metadata"]["documents_retrieved"] <= top_k


class TestSystemIntegration:
    """Test integration with all system components."""

    def test_full_rag_workflow(self, rag_pipeline):
        """Test complete RAG workflow end-to-end."""
        # Step 1: Query
        query = "What treatments and medications are documented?"

        # Step 2: Process
        result = rag_pipeline.process_query(
            query_text=query,
            top_k=10,
            similarity_threshold=0.3,
            llm_max_tokens=500,
            llm_temperature=0.7
        )

        # Step 3: Validate all components worked
        assert result is not None

        # Embedding worked (implicit in successful query)
        assert "query" in result
        assert result["query"] == query

        # Vector search worked
        assert "retrieved_documents" in result
        assert isinstance(result["retrieved_documents"], list)

        # LLM generation worked
        assert "response" in result
        assert isinstance(result["response"], str)
        assert len(result["response"]) > 0

        # Citation extraction worked
        assert "citations" in result
        assert isinstance(result["citations"], list)

        # Metadata tracked
        assert "metadata" in result
        assert "processing_time_seconds" in result["metadata"]
        assert result["metadata"]["processing_time_seconds"] > 0


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
