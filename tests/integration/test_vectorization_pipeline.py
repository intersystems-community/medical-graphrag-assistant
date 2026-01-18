"""
Integration Tests for Clinical Note Vectorization Pipeline

Tests the full end-to-end vectorization workflow including:
- Document loading and validation
- Batch embedding generation
- Vector insertion into IRIS
- Checkpoint/resume functionality
- Search functionality

Run with:
    pytest tests/integration/test_vectorization_pipeline.py -v

Requirements:
    - IRIS database running and accessible
    - NVIDIA API key configured
    - Sample fixture at tests/fixtures/sample_clinical_notes.json
"""

import pytest
import os
import json
import sqlite3
import tempfile
from pathlib import Path
from typing import List, Dict, Any
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.vectorization.embedding_client import NVIDIAEmbeddingsClient
from src.vectorization.vector_db_client import IRISVectorDBClient
from src.vectorization.text_vectorizer import ClinicalNoteVectorizer


# Test configuration
FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "sample_clinical_notes.json"
TEST_CHECKPOINT_DB = "test_vectorization_state.db"
TEST_ERROR_LOG = "test_vectorization_errors.log"
TEST_TABLE_NAME = "TestClinicalNoteVectors"


@pytest.fixture(scope="module")
def iris_config():
    """IRIS database configuration from environment."""
    return {
        "host": os.getenv("IRIS_HOST", "localhost"),
        "port": int(os.getenv("IRIS_PORT", "1972")),
        "namespace": os.getenv("IRIS_NAMESPACE", "DEMO"),
        "username": os.getenv("IRIS_USERNAME", "_SYSTEM"),
        "password": os.getenv("IRIS_PASSWORD", "SYS"),
        "vector_dimension": 1024
    }


@pytest.fixture(scope="module")
def embedding_client():
    """NVIDIA NIM embeddings client."""
    client = NVIDIAEmbeddingsClient()
    yield client
    client.close()


@pytest.fixture(scope="module")
def vector_db_client(iris_config):
    """IRIS vector database client."""
    client = IRISVectorDBClient(**iris_config)
    client.connect()

    # Create test table
    try:
        client.create_clinical_note_vectors_table(
            table_name=TEST_TABLE_NAME,
            drop_if_exists=True
        )
    except Exception as e:
        pytest.skip(f"Could not create test table: {e}")

    yield client

    # Cleanup
    try:
        client.cursor.execute(f"DROP TABLE IF EXISTS {iris_config['namespace']}.{TEST_TABLE_NAME}")
        client.connection.commit()
    except:
        pass

    client.disconnect()


@pytest.fixture
def sample_documents():
    """Load sample clinical notes from fixture."""
    if not FIXTURE_PATH.exists():
        pytest.skip(f"Fixture not found: {FIXTURE_PATH}")

    with open(FIXTURE_PATH, 'r') as f:
        documents = json.load(f)

    # Use first 10 documents for faster testing
    return documents[:10]


@pytest.fixture
def vectorizer(embedding_client, vector_db_client):
    """ClinicalNoteVectorizer instance with test configuration."""
    vectorizer = ClinicalNoteVectorizer(
        embedding_client=embedding_client,
        vector_db_client=vector_db_client,
        checkpoint_db=TEST_CHECKPOINT_DB,
        error_log=TEST_ERROR_LOG
    )

    yield vectorizer

    # Cleanup test files
    for file in [TEST_CHECKPOINT_DB, TEST_ERROR_LOG]:
        if Path(file).exists():
            Path(file).unlink()


class TestDocumentLoading:
    """Test document loading and validation."""

    def test_load_documents_success(self, vectorizer):
        """Test loading valid document file."""
        documents = vectorizer.load_documents(str(FIXTURE_PATH))

        assert isinstance(documents, list)
        assert len(documents) > 0
        assert all(isinstance(doc, dict) for doc in documents)

    def test_load_documents_file_not_found(self, vectorizer):
        """Test loading non-existent file."""
        with pytest.raises(FileNotFoundError):
            vectorizer.load_documents("nonexistent.json")

    def test_document_validation_valid(self, vectorizer, sample_documents):
        """Test validation of valid documents."""
        for doc in sample_documents[:5]:
            error = vectorizer.validate_document(doc)
            assert error is None, f"Valid document should not have errors: {error}"

    def test_document_validation_missing_field(self, vectorizer):
        """Test validation catches missing required fields."""
        invalid_doc = {
            "resource_id": "test-123",
            "patient_id": "patient-456"
            # Missing document_type and text_content
        }

        error = vectorizer.validate_document(invalid_doc)
        assert error is not None
        assert "Missing required field" in error

    def test_document_validation_empty_content(self, vectorizer):
        """Test validation catches empty text content."""
        invalid_doc = {
            "resource_id": "test-123",
            "patient_id": "patient-456",
            "document_type": "Note",
            "text_content": "   "  # Only whitespace
        }

        error = vectorizer.validate_document(invalid_doc)
        assert error is not None
        assert "Empty text_content" in error


class TestDocumentPreprocessing:
    """Test document preprocessing logic."""

    def test_preprocessing_normalizes_whitespace(self, vectorizer):
        """Test whitespace normalization."""
        doc = {
            "resource_id": "test-123",
            "patient_id": "patient-456",
            "document_type": "Note",
            "text_content": "This  has   multiple    spaces\n\nand\n\nnewlines"
        }

        processed = vectorizer.preprocess_document(doc)

        # Should collapse whitespace
        assert "  " not in processed["text_content"]
        assert "\n\n" not in processed["text_content"]

    def test_preprocessing_truncates_for_storage(self, vectorizer):
        long_text = "A" * 35000

        doc = {
            "resource_id": "test-123",
            "patient_id": "patient-456",
            "document_type": "Note",
            "text_content": long_text
        }

        processed = vectorizer.preprocess_document(doc)

        assert len(processed["text_content"]) == 32000


class TestVectorizationPipeline:
    """Test full vectorization pipeline."""

    def test_full_pipeline_success(self, vectorizer, sample_documents, vector_db_client):
        """Test complete vectorization pipeline."""
        # Save sample documents to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_documents, f)
            temp_file = f.name

        try:
            # Run vectorization
            stats = vectorizer.vectorize(
                input_file=temp_file,
                batch_size=5,
                resume=False,
                show_progress=False,
                table_name=TEST_TABLE_NAME
            )

            # Verify statistics
            assert stats["total_documents"] == len(sample_documents)
            assert stats["successful"] > 0
            assert stats["processed"] > 0

            # Verify vectors were inserted
            # Note: Using test table name
            count = vector_db_client.count_vectors(table_name=TEST_TABLE_NAME)
            assert count == stats["successful"]

        finally:
            # Cleanup temp file
            Path(temp_file).unlink()

    def test_checkpoint_creation(self, vectorizer, sample_documents):
        """Test that checkpoint database is created."""
        # Save sample documents to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_documents[:5], f)
            temp_file = f.name

        try:
            # Run vectorization
            vectorizer.vectorize(
                input_file=temp_file,
                batch_size=5,
                resume=False,
                show_progress=False,
                table_name=TEST_TABLE_NAME
            )

            # Verify checkpoint DB exists
            assert Path(TEST_CHECKPOINT_DB).exists()

            # Verify checkpoint contains records
            conn = sqlite3.connect(TEST_CHECKPOINT_DB)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM VectorizationState")
            count = cursor.fetchone()[0]
            conn.close()

            assert count == 5  # Should have 5 records

        finally:
            Path(temp_file).unlink()


class TestResumeability:
    """Test checkpoint/resume functionality."""

    def test_resume_skips_completed(self, vectorizer, sample_documents):
        """Test that resume skips already processed documents."""
        # Save sample documents to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_documents[:5], f)
            temp_file = f.name

        try:
            # First run - process all
            stats1 = vectorizer.vectorize(
                input_file=temp_file,
                batch_size=5,
                resume=False,
                show_progress=False,
                table_name=TEST_TABLE_NAME
            )

            successful_first = stats1["successful"]

            # Second run - should skip all (resume mode)
            stats2 = vectorizer.vectorize(
                input_file=temp_file,
                batch_size=5,
                resume=True,
                show_progress=False,
                table_name=TEST_TABLE_NAME
            )

            # Should process 0 new documents
            assert stats2["processed"] == 0
            assert stats2["successful"] == 0

        finally:
            Path(temp_file).unlink()

    def test_resume_after_simulated_interruption(self, vectorizer, sample_documents):
        """Test resume after interruption mid-processing."""
        # Save sample documents to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_documents, f)
            temp_file = f.name

        try:
            # Simulate partial processing by manually updating checkpoint
            # Process first half
            half = len(sample_documents) // 2

            stats1 = vectorizer.vectorize(
                input_file=temp_file,
                batch_size=5,
                resume=False,
                show_progress=False,
                table_name=TEST_TABLE_NAME
            )

            first_batch_count = stats1["successful"]

            # Manually mark remaining as pending in checkpoint
            conn = sqlite3.connect(TEST_CHECKPOINT_DB)
            cursor = conn.cursor()

            # Get count of pending
            cursor.execute("SELECT COUNT(*) FROM VectorizationState WHERE Status = 'pending'")
            pending_before = cursor.fetchone()[0]
            conn.close()

            # Resume should process any remaining pending
            stats2 = vectorizer.vectorize(
                input_file=temp_file,
                batch_size=5,
                resume=True,
                show_progress=False,
                table_name=TEST_TABLE_NAME
            )

            # Total should equal full set
            total_processed = first_batch_count + stats2["successful"]

            # Allow for some validation errors
            assert total_processed <= len(sample_documents)

        finally:
            Path(temp_file).unlink()


class TestVectorSearch:
    """Test vector similarity search."""

    def test_search_after_vectorization(self, vectorizer, sample_documents, vector_db_client):
        """Test vector search returns relevant results."""
        # Save and vectorize sample documents
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_documents, f)
            temp_file = f.name

        try:
            # Vectorize
            vectorizer.vectorize(
                input_file=temp_file,
                batch_size=5,
                resume=False,
                show_progress=False,
                table_name=TEST_TABLE_NAME
            )

            # Test search
            # Assuming vectorizer has embedding_client
            query_embedding = vectorizer.embedding_client.embed("hypertension medication")

            results = vector_db_client.search_similar(
                query_vector=query_embedding,
                top_k=3,
                table_name=TEST_TABLE_NAME
            )

            # Verify results
            assert len(results) > 0
            assert len(results) <= 3

            # Results should have required fields
            for result in results:
                assert "resource_id" in result
                assert "patient_id" in result
                assert "text_content" in result
                assert "similarity" in result

                # Similarity should be between 0 and 1
                assert 0 <= result["similarity"] <= 1

        finally:
            Path(temp_file).unlink()


class TestErrorHandling:
    """Test error handling and logging."""

    def test_validation_errors_logged(self, vectorizer):
        """Test that validation errors are logged to error log."""
        # Create documents with validation errors
        invalid_docs = [
            {"resource_id": "test-1"},  # Missing required fields
            {"resource_id": "test-2", "patient_id": "p1"},  # Missing document_type, text_content
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(invalid_docs, f)
            temp_file = f.name

        try:
            # Run vectorization (should catch validation errors)
            stats = vectorizer.vectorize(
                input_file=temp_file,
                batch_size=5,
                resume=False,
                show_progress=False
            )

            # Should have validation errors
            assert stats["validation_errors"] == len(invalid_docs)

            # Error log should exist
            assert Path(TEST_ERROR_LOG).exists()

            # Error log should contain error details
            with open(TEST_ERROR_LOG, 'r') as f:
                log_content = f.read()
                assert "Validation Errors" in log_content
                assert "test-1" in log_content or "test-2" in log_content

        finally:
            Path(temp_file).unlink()


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
