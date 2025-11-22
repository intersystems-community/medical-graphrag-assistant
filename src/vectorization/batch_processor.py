"""
Batch Vectorization Processor with SQLite Checkpointing

Provides resumable batch processing for vectorizing clinical documents and medical images.
Uses SQLite for lightweight state tracking to enable checkpoint/resume functionality.

Usage:
    from batch_processor import BatchProcessor

    processor = BatchProcessor(
        embedding_client=embedding_client,
        vector_db_client=vector_db_client,
        checkpoint_db="vectorization_state.db"
    )

    # Process documents with automatic checkpointing
    processor.process_documents(documents, batch_size=50)

    # Resume from checkpoint
    processor.resume()

Dependencies:
    sqlite3 (built-in), embedding_client, vector_db_client
"""

import sqlite3
import time
import logging
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BatchProcessor:
    """
    Resumable batch processor with SQLite checkpointing.

    Tracks processing state for documents and enables recovery from failures
    without re-processing already completed items.
    """

    def __init__(
        self,
        embedding_client,
        vector_db_client,
        checkpoint_db: str = "vectorization_state.db",
        auto_commit_interval: int = 10
    ):
        """
        Initialize batch processor with checkpointing.

        Args:
            embedding_client: Client for generating embeddings
            vector_db_client: Client for storing vectors in IRIS
            checkpoint_db: Path to SQLite checkpoint database
            auto_commit_interval: Commit checkpoint every N successful documents
        """
        self.embedding_client = embedding_client
        self.vector_db_client = vector_db_client
        self.checkpoint_db = checkpoint_db
        self.auto_commit_interval = auto_commit_interval

        self.connection = None
        self.cursor = None

        # Statistics
        self.stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "start_time": None,
            "end_time": None
        }

        logger.info(f"Initialized batch processor with checkpoint DB: {checkpoint_db}")

    def connect(self) -> None:
        """Establish connection to checkpoint database."""
        self.connection = sqlite3.connect(self.checkpoint_db)
        self.cursor = self.connection.cursor()
        logger.info(f"✓ Connected to checkpoint DB: {self.checkpoint_db}")

    def disconnect(self) -> None:
        """Close checkpoint database connection."""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
            logger.info("✓ Disconnected from checkpoint DB")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        self._create_checkpoint_table()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()

    def _create_checkpoint_table(self) -> None:
        """Create VectorizationState table if it doesn't exist."""
        create_sql = """
        CREATE TABLE IF NOT EXISTS VectorizationState (
            DocumentID TEXT PRIMARY KEY,
            DocumentType TEXT NOT NULL,
            Status TEXT NOT NULL CHECK(Status IN ('pending', 'processing', 'completed', 'failed')),
            ProcessingStartedAt TEXT,
            ProcessingCompletedAt TEXT,
            ErrorMessage TEXT,
            RetryCount INTEGER DEFAULT 0
        )
        """

        # Create indexes for efficient queries
        index_sql_status = "CREATE INDEX IF NOT EXISTS StatusIdx ON VectorizationState(Status)"
        index_sql_type = "CREATE INDEX IF NOT EXISTS DocumentTypeIdx ON VectorizationState(DocumentType)"

        try:
            self.cursor.execute(create_sql)
            self.cursor.execute(index_sql_status)
            self.cursor.execute(index_sql_type)
            self.connection.commit()
            logger.info("✓ Checkpoint table ready")
        except sqlite3.Error as e:
            logger.error(f"✗ Failed to create checkpoint table: {e}")
            raise

    def register_documents(
        self,
        documents: List[Dict[str, Any]],
        document_type: str = "clinical_note"
    ) -> int:
        """
        Register documents in checkpoint database.

        Args:
            documents: List of document dictionaries with 'resource_id' key
            document_type: Type of document ('clinical_note' or 'medical_image')

        Returns:
            Number of new documents registered
        """
        if not self.connection:
            self.connect()

        new_count = 0

        for doc in documents:
            doc_id = doc.get("resource_id") or doc.get("document_id")

            if not doc_id:
                logger.warning(f"Skipping document without ID: {doc}")
                continue

            try:
                # Insert only if not exists (ignore duplicates)
                insert_sql = """
                INSERT OR IGNORE INTO VectorizationState
                (DocumentID, DocumentType, Status)
                VALUES (?, ?, 'pending')
                """

                result = self.cursor.execute(insert_sql, (doc_id, document_type))
                if result.rowcount > 0:
                    new_count += 1

            except sqlite3.Error as e:
                logger.error(f"Failed to register {doc_id}: {e}")

        self.connection.commit()
        logger.info(f"✓ Registered {new_count} new documents")
        return new_count

    def get_pending_documents(
        self,
        document_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[str]:
        """
        Get list of pending document IDs.

        Args:
            document_type: Optional filter by document type
            limit: Optional limit number of results

        Returns:
            List of pending document IDs
        """
        if not self.connection:
            self.connect()

        where_clause = "WHERE Status = 'pending'"
        if document_type:
            where_clause += f" AND DocumentType = '{document_type}'"

        limit_clause = f"LIMIT {limit}" if limit else ""

        query = f"""
        SELECT DocumentID FROM VectorizationState
        {where_clause}
        ORDER BY DocumentID
        {limit_clause}
        """

        self.cursor.execute(query)
        return [row[0] for row in self.cursor.fetchall()]

    def mark_processing(self, document_id: str) -> None:
        """Mark document as currently processing."""
        update_sql = """
        UPDATE VectorizationState
        SET Status = 'processing',
            ProcessingStartedAt = ?
        WHERE DocumentID = ?
        """

        self.cursor.execute(update_sql, (datetime.utcnow().isoformat(), document_id))

    def mark_completed(self, document_id: str) -> None:
        """Mark document as successfully completed."""
        update_sql = """
        UPDATE VectorizationState
        SET Status = 'completed',
            ProcessingCompletedAt = ?,
            ErrorMessage = NULL
        WHERE DocumentID = ?
        """

        self.cursor.execute(update_sql, (datetime.utcnow().isoformat(), document_id))

    def mark_failed(self, document_id: str, error_message: str) -> None:
        """Mark document as failed with error message."""
        update_sql = """
        UPDATE VectorizationState
        SET Status = 'failed',
            ProcessingCompletedAt = ?,
            ErrorMessage = ?,
            RetryCount = RetryCount + 1
        WHERE DocumentID = ?
        """

        self.cursor.execute(
            update_sql,
            (datetime.utcnow().isoformat(), error_message[:500], document_id)
        )

    def process_documents(
        self,
        documents: List[Dict[str, Any]],
        batch_size: int = 50,
        document_type: str = "clinical_note",
        show_progress: bool = True,
        on_batch_complete: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Process documents with automatic checkpointing.

        Args:
            documents: List of document dictionaries containing:
                - resource_id: Unique identifier
                - patient_id: Patient identifier
                - document_type: Type of clinical document
                - text_content: Text to vectorize
                - source_bundle: Optional source reference
            batch_size: Number of texts to embed per API call
            document_type: Document type for checkpoint tracking
            show_progress: Whether to log progress updates
            on_batch_complete: Optional callback after each batch

        Returns:
            Dictionary with processing statistics
        """
        if not self.connection:
            raise RuntimeError("Must call connect() or use context manager")

        # Register all documents first
        self.register_documents(documents, document_type)

        # Get pending documents
        pending_ids = set(self.get_pending_documents(document_type))

        # Filter to only pending documents
        docs_to_process = [
            doc for doc in documents
            if (doc.get("resource_id") or doc.get("document_id")) in pending_ids
        ]

        if not docs_to_process:
            logger.info("No pending documents to process")
            return self.stats

        logger.info(f"Processing {len(docs_to_process)} pending documents")
        self.stats["start_time"] = datetime.utcnow()

        # Process in batches for embedding API
        for i in range(0, len(docs_to_process), batch_size):
            batch = docs_to_process[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(docs_to_process) + batch_size - 1) // batch_size

            if show_progress:
                logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} documents)")

            self._process_batch(batch, batch_num, show_progress)

            # Auto-commit checkpoint
            if batch_num % (self.auto_commit_interval // batch_size or 1) == 0:
                self.connection.commit()
                logger.debug("Checkpoint committed")

            # Callback
            if on_batch_complete:
                on_batch_complete(batch_num, total_batches, self.stats)

        # Final commit
        self.connection.commit()
        self.stats["end_time"] = datetime.utcnow()

        # Log summary
        self._log_summary()

        return self.stats

    def _process_batch(
        self,
        batch: List[Dict[str, Any]],
        batch_num: int,
        show_progress: bool
    ) -> None:
        """Process a single batch of documents."""

        # Extract texts for embedding
        texts = [doc["text_content"] for doc in batch]
        doc_ids = [doc.get("resource_id") or doc.get("document_id") for doc in batch]

        # Mark all as processing
        for doc_id in doc_ids:
            self.mark_processing(doc_id)

        try:
            # Generate embeddings for entire batch
            embeddings = self.embedding_client.embed_batch(texts, show_progress=False)

            # Insert each document into vector database
            for doc, embedding in zip(batch, embeddings):
                doc_id = doc.get("resource_id") or doc.get("document_id")

                try:
                    self.vector_db_client.insert_vector(
                        resource_id=doc_id,
                        patient_id=doc["patient_id"],
                        document_type=doc["document_type"],
                        text_content=doc["text_content"],
                        embedding=embedding,
                        embedding_model=self.embedding_client.model,
                        source_bundle=doc.get("source_bundle")
                    )

                    self.mark_completed(doc_id)
                    self.stats["successful"] += 1

                except Exception as e:
                    error_msg = f"Vector insert failed: {str(e)}"
                    self.mark_failed(doc_id, error_msg)
                    self.stats["failed"] += 1
                    logger.error(f"✗ Failed to insert {doc_id}: {e}")

            self.stats["total_processed"] += len(batch)

        except Exception as e:
            # Batch embedding failed - mark all as failed
            for doc_id in doc_ids:
                error_msg = f"Batch embedding failed: {str(e)}"
                self.mark_failed(doc_id, error_msg)
                self.stats["failed"] += 1

            logger.error(f"✗ Batch {batch_num} embedding failed: {e}")

    def resume(
        self,
        documents: List[Dict[str, Any]],
        batch_size: int = 50,
        document_type: str = "clinical_note",
        show_progress: bool = True
    ) -> Dict[str, Any]:
        """
        Resume processing from checkpoint.

        Same as process_documents but emphasizes resuming from previous run.

        Args:
            documents: Full list of documents (will filter to pending)
            batch_size: Batch size for embedding API
            document_type: Document type filter
            show_progress: Whether to show progress logs

        Returns:
            Processing statistics
        """
        pending_count = len(self.get_pending_documents(document_type))
        logger.info(f"Resuming from checkpoint: {pending_count} pending documents")

        return self.process_documents(
            documents,
            batch_size=batch_size,
            document_type=document_type,
            show_progress=show_progress
        )

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get processing statistics from checkpoint database.

        Returns:
            Dictionary with counts by status
        """
        if not self.connection:
            self.connect()

        stats_sql = """
        SELECT
            Status,
            COUNT(*) as Count,
            SUM(RetryCount) as TotalRetries
        FROM VectorizationState
        GROUP BY Status
        """

        self.cursor.execute(stats_sql)

        stats = {}
        for row in self.cursor.fetchall():
            status, count, retries = row
            stats[status] = {
                "count": count,
                "retries": retries or 0
            }

        return stats

    def reset_failed(self, max_retries: int = 3) -> int:
        """
        Reset failed documents to pending for retry.

        Args:
            max_retries: Maximum retry count before giving up

        Returns:
            Number of documents reset
        """
        if not self.connection:
            self.connect()

        reset_sql = """
        UPDATE VectorizationState
        SET Status = 'pending',
            ErrorMessage = NULL
        WHERE Status = 'failed'
        AND RetryCount < ?
        """

        self.cursor.execute(reset_sql, (max_retries,))
        reset_count = self.cursor.rowcount
        self.connection.commit()

        logger.info(f"✓ Reset {reset_count} failed documents to pending")
        return reset_count

    def _log_summary(self) -> None:
        """Log processing summary."""
        elapsed = (
            (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
            if self.stats["start_time"] and self.stats["end_time"]
            else 0
        )

        logger.info("=" * 60)
        logger.info("Batch Processing Summary")
        logger.info("=" * 60)
        logger.info(f"  Total processed:  {self.stats['total_processed']:,}")
        logger.info(f"  Successful:       {self.stats['successful']:,}")
        logger.info(f"  Failed:           {self.stats['failed']:,}")
        logger.info(f"  Skipped:          {self.stats['skipped']:,}")
        logger.info(f"  Elapsed time:     {elapsed:.1f}s")

        if elapsed > 0 and self.stats["successful"] > 0:
            rate = self.stats["successful"] / elapsed
            logger.info(f"  Processing rate:  {rate:.1f} docs/sec")

        logger.info("=" * 60)

    def clear_checkpoint(self, document_type: Optional[str] = None) -> int:
        """
        Clear checkpoint database (use with caution).

        Args:
            document_type: Optional filter to clear only specific type

        Returns:
            Number of records deleted
        """
        if not self.connection:
            self.connect()

        if document_type:
            delete_sql = "DELETE FROM VectorizationState WHERE DocumentType = ?"
            self.cursor.execute(delete_sql, (document_type,))
        else:
            delete_sql = "DELETE FROM VectorizationState"
            self.cursor.execute(delete_sql)

        deleted_count = self.cursor.rowcount
        self.connection.commit()

        logger.warning(f"⚠ Cleared {deleted_count} checkpoint records")
        return deleted_count


# Example usage
if __name__ == "__main__":
    # Example: Process documents with checkpointing
    from embedding_client import NVIDIAEmbeddingsClient
    from vector_db_client import IRISVectorDBClient

    # Initialize clients
    embedding_client = NVIDIAEmbeddingsClient()
    vector_db_client = IRISVectorDBClient()

    # Sample documents
    documents = [
        {
            "resource_id": "doc-001",
            "patient_id": "patient-123",
            "document_type": "Progress Note",
            "text_content": "Patient presents with acute respiratory symptoms...",
            "source_bundle": "bundle-001.json"
        },
        {
            "resource_id": "doc-002",
            "patient_id": "patient-456",
            "document_type": "Discharge Summary",
            "text_content": "Patient discharged in stable condition...",
            "source_bundle": "bundle-002.json"
        }
    ]

    # Process with checkpointing
    with BatchProcessor(embedding_client, vector_db_client) as processor:
        stats = processor.process_documents(documents, batch_size=50)

        print(f"\nProcessed {stats['successful']} documents")

        # Resume if needed
        # stats = processor.resume(documents)
