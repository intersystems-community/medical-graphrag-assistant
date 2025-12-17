"""
Unit Tests for IRISVectorDBClient

Tests IRIS database operations with mocked database connections.
Validates vector insertion, similarity search, and connection management.

Usage:
    pytest tests/unit/test_vector_db_client.py -v
    pytest tests/unit/test_vector_db_client.py::TestIRISVectorDBClient::test_connect -v

Dependencies:
    pytest, unittest.mock
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
from typing import List

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from vectorization.vector_db_client import IRISVectorDBClient


class TestIRISVectorDBClient:
    """Test suite for IRISVectorDBClient class."""

    @pytest.fixture
    def mock_iris_module(self):
        """Mock the iris module to avoid requiring IRIS installation."""
        with patch('vectorization.vector_db_client.iris') as mock_iris:
            # Mock connection
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_iris.connect.return_value = mock_conn

            yield mock_iris, mock_conn, mock_cursor

    @pytest.fixture
    def client(self):
        """Create a test client instance."""
        return IRISVectorDBClient(
            host="localhost",
            port=1972,
            namespace="DEMO",
            username="_SYSTEM",
            password="ISCDEMO",
            vector_dimension=1024
        )

    def test_initialization(self, client):
        """Test client initialization with default parameters."""
        assert client.host == "localhost"
        assert client.port == 1972
        assert client.namespace == "DEMO"
        assert client.username == "_SYSTEM"
        assert client.password == "ISCDEMO"
        assert client.vector_dimension == 1024
        assert client.connection is None
        assert client.cursor is None

    def test_connect_success(self, client, mock_iris_module):
        """Test successful database connection."""
        mock_iris, mock_conn, mock_cursor = mock_iris_module

        client.connect()

        # Verify connection was established
        mock_iris.connect.assert_called_once_with(
            "localhost:1972/DEMO",
            "_SYSTEM",
            "ISCDEMO"
        )
        assert client.connection == mock_conn
        assert client.cursor == mock_cursor

    def test_connect_failure(self, client, mock_iris_module):
        """Test connection failure handling."""
        mock_iris, _, _ = mock_iris_module
        mock_iris.connect.side_effect = Exception("Connection failed")

        with pytest.raises(Exception, match="Connection failed"):
            client.connect()

    def test_disconnect(self, client, mock_iris_module):
        """Test disconnect closes cursor and connection."""
        mock_iris, mock_conn, mock_cursor = mock_iris_module

        client.connect()
        client.disconnect()

        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    def test_context_manager(self, client, mock_iris_module):
        """Test using client as context manager."""
        mock_iris, mock_conn, mock_cursor = mock_iris_module

        with client as ctx_client:
            assert ctx_client == client
            assert ctx_client.connection == mock_conn

        # Verify cleanup was called
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    def test_create_table_success(self, client, mock_iris_module):
        """Test creating ClinicalNoteVectors table."""
        mock_iris, mock_conn, mock_cursor = mock_iris_module
        client.connect()

        client.create_clinical_note_vectors_table(
            table_name="ClinicalNoteVectors",
            drop_if_exists=False
        )

        # Verify table creation SQL was executed
        assert mock_cursor.execute.call_count >= 1  # At least CREATE TABLE
        mock_conn.commit.assert_called()

        # Check that CREATE TABLE was called with VECTOR column
        create_call = mock_cursor.execute.call_args_list[0]
        create_sql = create_call[0][0]
        assert "CREATE TABLE" in create_sql
        assert "VECTOR(DOUBLE, 1024)" in create_sql

    def test_create_table_drop_if_exists(self, client, mock_iris_module):
        """Test dropping existing table before creation."""
        mock_iris, mock_conn, mock_cursor = mock_iris_module
        client.connect()

        client.create_clinical_note_vectors_table(
            table_name="ClinicalNoteVectors",
            drop_if_exists=True
        )

        # Verify DROP TABLE was called first
        drop_call = mock_cursor.execute.call_args_list[0]
        drop_sql = drop_call[0][0]
        assert "DROP TABLE IF EXISTS" in drop_sql

    def test_insert_vector_success(self, client, mock_iris_module):
        """Test successful vector insertion."""
        mock_iris, mock_conn, mock_cursor = mock_iris_module
        client.connect()

        # Create a sample 1024-dim vector
        embedding = [0.1] * 1024

        client.insert_vector(
            resource_id="doc-123",
            patient_id="patient-456",
            document_type="Progress Note",
            text_content="Patient presents with acute symptoms",
            embedding=embedding,
            embedding_model="nvidia/nv-embedqa-e5-v5",
            source_bundle="bundle-001.json"
        )

        # Verify INSERT was executed
        mock_cursor.execute.assert_called_once()
        insert_call = mock_cursor.execute.call_args
        insert_sql = insert_call[0][0]

        assert "INSERT INTO" in insert_sql
        assert "TO_VECTOR" in insert_sql

        # Verify parameters
        params = insert_call[0][1]
        assert params[0] == "doc-123"
        assert params[1] == "patient-456"
        assert params[2] == "Progress Note"

        mock_conn.commit.assert_called_once()

    def test_insert_vector_dimension_mismatch(self, client, mock_iris_module):
        """Test vector insertion with wrong dimension."""
        mock_iris, mock_conn, mock_cursor = mock_iris_module
        client.connect()

        # Create a vector with wrong dimension
        wrong_embedding = [0.1] * 512  # Should be 1024

        with pytest.raises(ValueError, match="Vector dimension mismatch"):
            client.insert_vector(
                resource_id="doc-123",
                patient_id="patient-456",
                document_type="Progress Note",
                text_content="Test content",
                embedding=wrong_embedding,
                embedding_model="test-model"
            )

    def test_insert_vectors_batch(self, client, mock_iris_module):
        """Test batch vector insertion."""
        mock_iris, mock_conn, mock_cursor = mock_iris_module
        client.connect()

        vectors = [
            {
                "resource_id": f"doc-{i}",
                "patient_id": "patient-123",
                "document_type": "Progress Note",
                "text_content": f"Content {i}",
                "embedding": [0.1] * 1024,
                "embedding_model": "nvidia/nv-embedqa-e5-v5",
                "source_bundle": f"bundle-{i}.json"
            }
            for i in range(3)
        ]

        success_count, failed_count = client.insert_vectors_batch(vectors)

        assert success_count == 3
        assert failed_count == 0
        assert mock_cursor.execute.call_count == 3

    def test_search_similar_success(self, client, mock_iris_module):
        """Test successful similarity search."""
        mock_iris, mock_conn, mock_cursor = mock_iris_module
        client.connect()

        # Mock query results
        mock_cursor.fetchall.return_value = [
            ("doc-1", "patient-123", "Progress Note", "Content 1", "bundle-1.json", 0.95),
            ("doc-2", "patient-123", "Discharge Summary", "Content 2", "bundle-2.json", 0.87)
        ]

        query_vector = [0.1] * 1024
        results = client.search_similar(query_vector, top_k=2)

        # Verify results
        assert len(results) == 2
        assert results[0]["resource_id"] == "doc-1"
        assert results[0]["similarity"] == 0.95
        assert results[1]["resource_id"] == "doc-2"
        assert results[1]["similarity"] == 0.87

        # Verify query was executed
        mock_cursor.execute.assert_called_once()
        query_sql = mock_cursor.execute.call_args[0][0]
        assert "SELECT TOP" in query_sql
        assert "VECTOR_COSINE" in query_sql

    def test_search_similar_with_filters(self, client, mock_iris_module):
        """Test similarity search with patient and document type filters."""
        mock_iris, mock_conn, mock_cursor = mock_iris_module
        client.connect()

        mock_cursor.fetchall.return_value = [
            ("doc-1", "patient-123", "Progress Note", "Content 1", None, 0.92)
        ]

        query_vector = [0.1] * 1024
        results = client.search_similar(
            query_vector,
            top_k=10,
            patient_id="patient-123",
            document_type="Progress Note"
        )

        # Verify filters were applied in SQL
        query_sql = mock_cursor.execute.call_args[0][0]
        assert "WHERE" in query_sql
        assert "PatientID = ?" in query_sql
        assert "DocumentType = ?" in query_sql

        # Verify filter parameters
        params = mock_cursor.execute.call_args[0][1]
        assert "patient-123" in params
        assert "Progress Note" in params

    def test_search_similar_dimension_mismatch(self, client, mock_iris_module):
        """Test search with wrong vector dimension."""
        mock_iris, mock_conn, mock_cursor = mock_iris_module
        client.connect()

        wrong_query_vector = [0.1] * 512  # Should be 1024

        with pytest.raises(ValueError, match="Query vector dimension mismatch"):
            client.search_similar(wrong_query_vector)

    def test_count_vectors(self, client, mock_iris_module):
        """Test counting vectors in table."""
        mock_iris, mock_conn, mock_cursor = mock_iris_module
        client.connect()

        mock_cursor.fetchone.return_value = (1500,)

        count = client.count_vectors("ClinicalNoteVectors")

        assert count == 1500
        mock_cursor.execute.assert_called_once()
        query_sql = mock_cursor.execute.call_args[0][0]
        assert "SELECT COUNT(*)" in query_sql

    def test_get_vector_stats(self, client, mock_iris_module):
        """Test retrieving vector statistics."""
        mock_iris, mock_conn, mock_cursor = mock_iris_module
        client.connect()

        # Mock count query
        mock_cursor.fetchone.side_effect = [
            (1500,),  # total count
            (250,)    # unique patients
        ]

        # Mock document type breakdown
        mock_cursor.fetchall.return_value = [
            ("Progress Note", 800),
            ("Discharge Summary", 400),
            ("Consultation", 300)
        ]

        stats = client.get_vector_stats("ClinicalNoteVectors")

        assert stats["total_vectors"] == 1500
        assert stats["unique_patients"] == 250
        assert stats["unique_document_types"] == 3
        assert stats["document_type_counts"]["Progress Note"] == 800
        assert stats["document_type_counts"]["Discharge Summary"] == 400


class TestIRISVectorDBClientIntegration:
    """
    Integration-style tests that verify workflow patterns.
    These still use mocks but test end-to-end scenarios.
    """

    @pytest.fixture
    def mock_iris_module(self):
        """Mock the iris module."""
        with patch('vectorization.vector_db_client.iris') as mock_iris:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_iris.connect.return_value = mock_conn
            yield mock_iris, mock_conn, mock_cursor

    def test_full_workflow(self, mock_iris_module):
        """Test complete workflow: connect, create table, insert, search, stats, disconnect."""
        mock_iris, mock_conn, mock_cursor = mock_iris_module

        # Initialize client
        client = IRISVectorDBClient()

        with client:
            # Create table
            client.create_clinical_note_vectors_table(drop_if_exists=True)

            # Insert vector
            embedding = [0.1] * 1024
            client.insert_vector(
                resource_id="doc-001",
                patient_id="patient-123",
                document_type="Progress Note",
                text_content="Test content",
                embedding=embedding,
                embedding_model="nvidia/nv-embedqa-e5-v5"
            )

            # Search similar
            mock_cursor.fetchall.return_value = [
                ("doc-001", "patient-123", "Progress Note", "Test content", None, 1.0)
            ]
            results = client.search_similar(embedding, top_k=5)
            assert len(results) == 1

            # Get stats
            mock_cursor.fetchone.side_effect = [(1,), (1,)]
            mock_cursor.fetchall.return_value = [("Progress Note", 1)]
            stats = client.get_vector_stats()
            assert stats["total_vectors"] == 1

        # Verify cleanup
        mock_cursor.close.assert_called()
        mock_conn.close.assert_called()

    def test_batch_insert_with_partial_failure(self, mock_iris_module):
        """Test batch insertion where some vectors fail."""
        mock_iris, mock_conn, mock_cursor = mock_iris_module

        client = IRISVectorDBClient()
        client.connect()

        # Mock execute to fail on second insert
        mock_cursor.execute.side_effect = [
            None,  # First insert succeeds
            Exception("Duplicate key"),  # Second insert fails
            None   # Third insert succeeds
        ]

        vectors = [
            {
                "resource_id": f"doc-{i}",
                "patient_id": "patient-123",
                "document_type": "Progress Note",
                "text_content": f"Content {i}",
                "embedding": [0.1] * 1024,
                "embedding_model": "nvidia/nv-embedqa-e5-v5"
            }
            for i in range(3)
        ]

        success_count, failed_count = client.insert_vectors_batch(vectors)

        assert success_count == 2
        assert failed_count == 1


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
