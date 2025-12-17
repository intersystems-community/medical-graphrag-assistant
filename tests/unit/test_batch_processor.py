"""
Unit Tests for BatchProcessor

Tests resumable batch processing with SQLite checkpointing.
Validates checkpoint creation, state transitions, and resume functionality.

Usage:
    pytest tests/unit/test_batch_processor.py -v
    pytest tests/unit/test_batch_processor.py::TestBatchProcessor::test_register_documents -v

Dependencies:
    pytest, unittest.mock
"""

import pytest
import sys
import sqlite3
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from vectorization.batch_processor import BatchProcessor


class TestBatchProcessor:
    """Test suite for BatchProcessor class."""

    @pytest.fixture
    def mock_clients(self):
        """Create mock embedding and vector DB clients."""
        embedding_client = Mock()
        embedding_client.model = "nvidia/nv-embedqa-e5-v5"
        embedding_client.embed_batch.return_value = [[0.1] * 1024, [0.2] * 1024]

        vector_db_client = Mock()
        vector_db_client.insert_vector = Mock()

        return embedding_client, vector_db_client

    @pytest.fixture
    def temp_db(self):
        """Create a temporary SQLite database for testing."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        # Cleanup
        if os.path.exists(path):
            os.remove(path)

    @pytest.fixture
    def processor(self, mock_clients, temp_db):
        """Create a test BatchProcessor instance."""
        embedding_client, vector_db_client = mock_clients
        return BatchProcessor(
            embedding_client=embedding_client,
            vector_db_client=vector_db_client,
            checkpoint_db=temp_db,
            auto_commit_interval=2
        )

    def test_initialization(self, processor, temp_db):
        """Test processor initialization."""
        assert processor.checkpoint_db == temp_db
        assert processor.auto_commit_interval == 2
        assert processor.connection is None
        assert processor.cursor is None
        assert processor.stats["total_processed"] == 0

    def test_connect_creates_database(self, processor):
        """Test connect creates checkpoint database."""
        processor.connect()

        assert processor.connection is not None
        assert processor.cursor is not None

        # Verify database file exists
        assert os.path.exists(processor.checkpoint_db)

        processor.disconnect()

    def test_create_checkpoint_table(self, processor):
        """Test checkpoint table creation with correct schema."""
        processor.connect()
        processor._create_checkpoint_table()

        # Verify table was created
        processor.cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='VectorizationState'"
        )
        result = processor.cursor.fetchone()
        assert result is not None

        # Verify columns
        processor.cursor.execute("PRAGMA table_info(VectorizationState)")
        columns = {row[1] for row in processor.cursor.fetchall()}
        expected_columns = {
            "DocumentID", "DocumentType", "Status",
            "ProcessingStartedAt", "ProcessingCompletedAt",
            "ErrorMessage", "RetryCount"
        }
        assert expected_columns.issubset(columns)

        processor.disconnect()

    def test_context_manager(self, mock_clients, temp_db):
        """Test using processor as context manager."""
        embedding_client, vector_db_client = mock_clients

        with BatchProcessor(embedding_client, vector_db_client, temp_db) as proc:
            assert proc.connection is not None
            # Table should be created
            proc.cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='VectorizationState'"
            )
            assert proc.cursor.fetchone() is not None

        # Connection should be closed
        # Attempting to use cursor after disconnect should fail
        with pytest.raises(sqlite3.ProgrammingError):
            proc.cursor.execute("SELECT 1")

    def test_register_documents_new(self, processor):
        """Test registering new documents."""
        with processor:
            documents = [
                {"resource_id": "doc-001", "document_type": "Progress Note"},
                {"resource_id": "doc-002", "document_type": "Discharge Summary"},
                {"resource_id": "doc-003", "document_type": "Consultation"}
            ]

            new_count = processor.register_documents(documents, "clinical_note")

            assert new_count == 3

            # Verify documents were inserted
            processor.cursor.execute(
                "SELECT DocumentID, DocumentType, Status FROM VectorizationState ORDER BY DocumentID"
            )
            rows = processor.cursor.fetchall()

            assert len(rows) == 3
            assert rows[0] == ("doc-001", "clinical_note", "pending")
            assert rows[1] == ("doc-002", "clinical_note", "pending")
            assert rows[2] == ("doc-003", "clinical_note", "pending")

    def test_register_documents_duplicates_ignored(self, processor):
        """Test that duplicate documents are ignored."""
        with processor:
            documents = [
                {"resource_id": "doc-001", "document_type": "Progress Note"}
            ]

            # Register first time
            count1 = processor.register_documents(documents, "clinical_note")
            assert count1 == 1

            # Register again (duplicate)
            count2 = processor.register_documents(documents, "clinical_note")
            assert count2 == 0  # No new documents

            # Verify only one record exists
            processor.cursor.execute("SELECT COUNT(*) FROM VectorizationState")
            total = processor.cursor.fetchone()[0]
            assert total == 1

    def test_get_pending_documents(self, processor):
        """Test retrieving pending documents."""
        with processor:
            # Register documents
            documents = [
                {"resource_id": f"doc-{i:03d}", "document_type": "Note"}
                for i in range(5)
            ]
            processor.register_documents(documents, "clinical_note")

            # Mark some as completed
            processor.mark_processing("doc-001")
            processor.mark_completed("doc-001")
            processor.mark_processing("doc-002")
            processor.mark_completed("doc-002")

            # Get pending
            pending = processor.get_pending_documents("clinical_note")

            assert len(pending) == 3
            assert "doc-000" in pending
            assert "doc-003" in pending
            assert "doc-004" in pending
            assert "doc-001" not in pending
            assert "doc-002" not in pending

    def test_get_pending_documents_with_limit(self, processor):
        """Test retrieving pending documents with limit."""
        with processor:
            documents = [
                {"resource_id": f"doc-{i:03d}", "document_type": "Note"}
                for i in range(10)
            ]
            processor.register_documents(documents, "clinical_note")

            pending = processor.get_pending_documents("clinical_note", limit=3)

            assert len(pending) == 3

    def test_mark_processing(self, processor):
        """Test marking document as processing."""
        with processor:
            processor.register_documents(
                [{"resource_id": "doc-001", "document_type": "Note"}],
                "clinical_note"
            )

            processor.mark_processing("doc-001")
            processor.connection.commit()

            # Verify status changed
            processor.cursor.execute(
                "SELECT Status, ProcessingStartedAt FROM VectorizationState WHERE DocumentID = 'doc-001'"
            )
            row = processor.cursor.fetchone()
            assert row[0] == "processing"
            assert row[1] is not None  # timestamp should be set

    def test_mark_completed(self, processor):
        """Test marking document as completed."""
        with processor:
            processor.register_documents(
                [{"resource_id": "doc-001", "document_type": "Note"}],
                "clinical_note"
            )

            processor.mark_processing("doc-001")
            processor.mark_completed("doc-001")
            processor.connection.commit()

            # Verify status changed
            processor.cursor.execute(
                "SELECT Status, ProcessingCompletedAt, ErrorMessage FROM VectorizationState WHERE DocumentID = 'doc-001'"
            )
            row = processor.cursor.fetchone()
            assert row[0] == "completed"
            assert row[1] is not None  # completion timestamp
            assert row[2] is None  # no error message

    def test_mark_failed(self, processor):
        """Test marking document as failed."""
        with processor:
            processor.register_documents(
                [{"resource_id": "doc-001", "document_type": "Note"}],
                "clinical_note"
            )

            processor.mark_processing("doc-001")
            processor.mark_failed("doc-001", "API rate limit exceeded")
            processor.connection.commit()

            # Verify status and error
            processor.cursor.execute(
                "SELECT Status, ErrorMessage, RetryCount FROM VectorizationState WHERE DocumentID = 'doc-001'"
            )
            row = processor.cursor.fetchone()
            assert row[0] == "failed"
            assert "API rate limit" in row[1]
            assert row[2] == 1  # retry count incremented

    def test_process_documents_success(self, processor, mock_clients):
        """Test successful document processing."""
        embedding_client, vector_db_client = mock_clients

        # Mock successful embedding and insertion
        embedding_client.embed_batch.return_value = [
            [0.1] * 1024,
            [0.2] * 1024
        ]

        with processor:
            documents = [
                {
                    "resource_id": "doc-001",
                    "patient_id": "patient-123",
                    "document_type": "Progress Note",
                    "text_content": "Patient presents with symptoms",
                    "source_bundle": "bundle-001.json"
                },
                {
                    "resource_id": "doc-002",
                    "patient_id": "patient-456",
                    "document_type": "Discharge Summary",
                    "text_content": "Patient discharged in stable condition",
                    "source_bundle": "bundle-002.json"
                }
            ]

            stats = processor.process_documents(
                documents,
                batch_size=2,
                document_type="clinical_note",
                show_progress=False
            )

            assert stats["successful"] == 2
            assert stats["failed"] == 0
            assert stats["total_processed"] == 2

            # Verify embeddings were generated
            embedding_client.embed_batch.assert_called_once()

            # Verify vectors were inserted
            assert vector_db_client.insert_vector.call_count == 2

    def test_process_documents_with_failures(self, processor, mock_clients):
        """Test document processing with some failures."""
        embedding_client, vector_db_client = mock_clients

        # Mock successful embeddings
        embedding_client.embed_batch.return_value = [
            [0.1] * 1024,
            [0.2] * 1024
        ]

        # Mock vector insertion to fail on second document
        vector_db_client.insert_vector.side_effect = [
            None,  # First succeeds
            Exception("Database connection lost")  # Second fails
        ]

        with processor:
            documents = [
                {
                    "resource_id": "doc-001",
                    "patient_id": "patient-123",
                    "document_type": "Note",
                    "text_content": "Content 1"
                },
                {
                    "resource_id": "doc-002",
                    "patient_id": "patient-456",
                    "document_type": "Note",
                    "text_content": "Content 2"
                }
            ]

            stats = processor.process_documents(
                documents,
                batch_size=2,
                document_type="clinical_note",
                show_progress=False
            )

            assert stats["successful"] == 1
            assert stats["failed"] == 1

            # Check database state
            processor.cursor.execute(
                "SELECT DocumentID, Status FROM VectorizationState WHERE Status='failed'"
            )
            failed = processor.cursor.fetchall()
            assert len(failed) == 1
            assert failed[0][0] == "doc-002"

    def test_process_documents_batch_embedding_failure(self, processor, mock_clients):
        """Test handling of batch embedding failure."""
        embedding_client, vector_db_client = mock_clients

        # Mock embedding to fail
        embedding_client.embed_batch.side_effect = Exception("API unavailable")

        with processor:
            documents = [
                {
                    "resource_id": "doc-001",
                    "patient_id": "patient-123",
                    "document_type": "Note",
                    "text_content": "Content"
                }
            ]

            stats = processor.process_documents(
                documents,
                batch_size=1,
                document_type="clinical_note",
                show_progress=False
            )

            # All documents should fail
            assert stats["successful"] == 0
            assert stats["failed"] == 1

            # Verify status in database
            processor.cursor.execute(
                "SELECT Status, ErrorMessage FROM VectorizationState WHERE DocumentID='doc-001'"
            )
            row = processor.cursor.fetchone()
            assert row[0] == "failed"
            assert "API unavailable" in row[1]

    def test_resume_from_checkpoint(self, processor, mock_clients):
        """Test resuming processing from checkpoint."""
        embedding_client, vector_db_client = mock_clients

        with processor:
            # Register documents
            documents = [
                {
                    "resource_id": f"doc-{i:03d}",
                    "patient_id": "patient-123",
                    "document_type": "Note",
                    "text_content": f"Content {i}"
                }
                for i in range(5)
            ]

            processor.register_documents(documents, "clinical_note")

            # Manually mark some as completed (simulating previous run)
            processor.mark_processing("doc-000")
            processor.mark_completed("doc-000")
            processor.mark_processing("doc-001")
            processor.mark_completed("doc-001")
            processor.connection.commit()

            # Mock embeddings for remaining documents
            embedding_client.embed_batch.return_value = [
                [0.1] * 1024,
                [0.2] * 1024,
                [0.3] * 1024
            ]

            # Resume processing
            stats = processor.resume(
                documents,
                batch_size=3,
                document_type="clinical_note",
                show_progress=False
            )

            # Should only process 3 remaining documents
            assert stats["successful"] == 3
            assert stats["total_processed"] == 3

    def test_get_statistics(self, processor):
        """Test retrieving processing statistics."""
        with processor:
            # Create documents with different statuses
            documents = [
                {"resource_id": f"doc-{i:03d}", "document_type": "Note"}
                for i in range(10)
            ]
            processor.register_documents(documents, "clinical_note")

            # Mark various statuses
            processor.mark_processing("doc-000")
            processor.mark_completed("doc-000")

            processor.mark_processing("doc-001")
            processor.mark_completed("doc-001")

            processor.mark_processing("doc-002")
            processor.mark_failed("doc-002", "Error 1")

            processor.mark_processing("doc-003")
            processor.mark_failed("doc-003", "Error 2")
            processor.mark_failed("doc-003", "Error 2 retry")  # increment retry

            processor.connection.commit()

            stats = processor.get_statistics()

            assert stats["completed"]["count"] == 2
            assert stats["failed"]["count"] == 2
            assert stats["failed"]["retries"] == 3  # doc-002: 1 retry, doc-003: 2 retries
            assert stats["pending"]["count"] == 6

    def test_reset_failed_documents(self, processor):
        """Test resetting failed documents to pending."""
        with processor:
            documents = [
                {"resource_id": f"doc-{i:03d}", "document_type": "Note"}
                for i in range(5)
            ]
            processor.register_documents(documents, "clinical_note")

            # Mark all as failed
            for doc in documents:
                processor.mark_processing(doc["resource_id"])
                processor.mark_failed(doc["resource_id"], "Temporary error")

            processor.connection.commit()

            # Reset failed documents
            reset_count = processor.reset_failed(max_retries=3)

            assert reset_count == 5

            # Verify all are now pending
            processor.cursor.execute(
                "SELECT COUNT(*) FROM VectorizationState WHERE Status='pending'"
            )
            pending_count = processor.cursor.fetchone()[0]
            assert pending_count == 5

    def test_reset_failed_respects_max_retries(self, processor):
        """Test that reset_failed respects max retry limit."""
        with processor:
            processor.register_documents(
                [{"resource_id": "doc-001", "document_type": "Note"}],
                "clinical_note"
            )

            # Fail document multiple times
            for i in range(4):
                processor.mark_processing("doc-001")
                processor.mark_failed("doc-001", f"Error {i}")

            processor.connection.commit()

            # Verify retry count is 4
            processor.cursor.execute(
                "SELECT RetryCount FROM VectorizationState WHERE DocumentID='doc-001'"
            )
            assert processor.cursor.fetchone()[0] == 4

            # Try to reset with max_retries=3
            reset_count = processor.reset_failed(max_retries=3)

            assert reset_count == 0  # Should not reset (retry count >= 3)

            # With max_retries=5, should reset
            reset_count = processor.reset_failed(max_retries=5)
            assert reset_count == 1

    def test_clear_checkpoint(self, processor):
        """Test clearing checkpoint database."""
        with processor:
            # Register documents
            documents = [
                {"resource_id": f"doc-{i:03d}", "document_type": "Note"}
                for i in range(5)
            ]
            processor.register_documents(documents, "clinical_note")

            # Clear all
            deleted_count = processor.clear_checkpoint()

            assert deleted_count == 5

            # Verify database is empty
            processor.cursor.execute("SELECT COUNT(*) FROM VectorizationState")
            assert processor.cursor.fetchone()[0] == 0

    def test_clear_checkpoint_by_type(self, processor):
        """Test clearing checkpoint for specific document type."""
        with processor:
            # Register different types
            processor.register_documents(
                [{"resource_id": "doc-001", "document_type": "Note"}],
                "clinical_note"
            )
            processor.register_documents(
                [{"resource_id": "img-001", "document_type": "Image"}],
                "medical_image"
            )
            processor.connection.commit()

            # Clear only clinical notes
            deleted_count = processor.clear_checkpoint("clinical_note")

            assert deleted_count == 1

            # Verify only medical_image remains
            processor.cursor.execute(
                "SELECT DocumentID, DocumentType FROM VectorizationState"
            )
            rows = processor.cursor.fetchall()
            assert len(rows) == 1
            assert rows[0] == ("img-001", "medical_image")


class TestBatchProcessorIntegration:
    """Integration-style tests for full workflows."""

    @pytest.fixture
    def mock_clients(self):
        """Create mock clients with realistic behavior."""
        embedding_client = Mock()
        embedding_client.model = "nvidia/nv-embedqa-e5-v5"

        vector_db_client = Mock()

        return embedding_client, vector_db_client

    @pytest.fixture
    def temp_db(self):
        """Create temporary database."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.remove(path)

    def test_full_workflow_with_interruption(self, mock_clients, temp_db):
        """Test complete workflow with simulated interruption and resume."""
        embedding_client, vector_db_client = mock_clients

        documents = [
            {
                "resource_id": f"doc-{i:03d}",
                "patient_id": "patient-123",
                "document_type": "Note",
                "text_content": f"Clinical note {i}"
            }
            for i in range(10)
        ]

        # First run: process first 5 documents
        with BatchProcessor(embedding_client, vector_db_client, temp_db) as proc:
            # Mock embeddings
            embedding_client.embed_batch.return_value = [[0.1] * 1024] * 5

            # Register all documents
            proc.register_documents(documents, "clinical_note")

            # Process only first 5 (simulate interruption)
            first_five = documents[:5]
            for doc in first_five:
                proc.mark_processing(doc["resource_id"])
                proc.mark_completed(doc["resource_id"])
            proc.connection.commit()

        # Second run: resume and process remaining
        with BatchProcessor(embedding_client, vector_db_client, temp_db) as proc:
            embedding_client.embed_batch.return_value = [[0.2] * 1024] * 5

            stats = proc.resume(
                documents,
                batch_size=5,
                document_type="clinical_note",
                show_progress=False
            )

            # Should only process remaining 5
            assert stats["successful"] == 5
            assert stats["total_processed"] == 5

        # Verify all documents are completed
        with BatchProcessor(embedding_client, vector_db_client, temp_db) as proc:
            proc.cursor.execute(
                "SELECT COUNT(*) FROM VectorizationState WHERE Status='completed'"
            )
            assert proc.cursor.fetchone()[0] == 10


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
