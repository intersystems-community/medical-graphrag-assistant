#!/usr/bin/env python3
"""
Clinical Note Vectorization Pipeline

Main entry point for vectorizing clinical notes into IRIS vector database.
Uses NVIDIA NIM embeddings API and resumable batch processing with SQLite checkpoints.

Usage:
    # Initial run
    python text_vectorizer.py --input synthea_clinical_notes.json --batch-size 50

    # Resume from checkpoint
    python text_vectorizer.py --input synthea_clinical_notes.json --resume

    # Test search after vectorization
    python text_vectorizer.py --input synthea_clinical_notes.json --test-search

Dependencies:
    - src/vectorization/embedding_client.py (NVIDIA NIM embeddings)
    - src/vectorization/vector_db_client.py (IRIS vector database)
    - src/vectorization/batch_processor.py (resumable batch processing)

Environment Variables:
    - NVIDIA_API_KEY: NVIDIA NGC API key for embeddings
    - IRIS_HOST: IRIS server host (default: localhost)
    - IRIS_PORT: IRIS SQL port (default: 1972)
    - IRIS_NAMESPACE: IRIS namespace (default: DEMO)
    - IRIS_USERNAME: IRIS username (default: _SYSTEM)
    - IRIS_PASSWORD: IRIS password (default: SYS)
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from vectorization.embedding_client import NVIDIAEmbeddingsClient
from vectorization.vector_db_client import IRISVectorDBClient
from vectorization.batch_processor import BatchProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ClinicalNoteVectorizer:
    """
    Main vectorization pipeline for clinical notes.

    Coordinates embedding generation, vector storage, and checkpoint management.
    """

    def __init__(
        self,
        embedding_client: NVIDIAEmbeddingsClient,
        vector_db_client: IRISVectorDBClient,
        checkpoint_db: str = "vectorization_state.db",
        error_log: str = "vectorization_errors.log"
    ):
        """
        Initialize vectorization pipeline.

        Args:
            embedding_client: NVIDIA NIM embeddings client
            vector_db_client: IRIS vector database client
            checkpoint_db: Path to SQLite checkpoint database
            error_log: Path to error log file
        """
        self.embedding_client = embedding_client
        self.vector_db_client = vector_db_client
        self.checkpoint_db = checkpoint_db
        self.error_log = error_log

        # Statistics
        self.stats = {
            "total_documents": 0,
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "validation_errors": 0,
            "start_time": None,
            "end_time": None
        }

        logger.info("Initialized ClinicalNoteVectorizer")

    def load_documents(self, input_file: str) -> List[Dict[str, Any]]:
        """
        Load clinical notes from JSON file.

        Args:
            input_file: Path to JSON file with clinical notes

        Returns:
            List of document dictionaries

        Raises:
            FileNotFoundError: If input file doesn't exist
            json.JSONDecodeError: If file is not valid JSON
        """
        input_path = Path(input_file)

        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")

        logger.info(f"Loading documents from {input_file}")

        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                documents = json.load(f)

            if not isinstance(documents, list):
                raise ValueError("Input file must contain a JSON array of documents")

            self.stats["total_documents"] = len(documents)
            logger.info(f"✓ Loaded {len(documents):,} documents")

            return documents

        except json.JSONDecodeError as e:
            logger.error(f"✗ Invalid JSON in {input_file}: {e}")
            raise

    def validate_document(self, doc: Dict[str, Any]) -> Optional[str]:
        """
        Validate document has required fields.

        Args:
            doc: Document dictionary

        Returns:
            None if valid, error message if invalid
        """
        required_fields = ["resource_id", "patient_id", "document_type", "text_content"]

        for field in required_fields:
            if field not in doc or not doc[field]:
                return f"Missing required field: {field}"

        # Validate text content is not empty
        if not doc["text_content"].strip():
            return "Empty text_content"

        return None

    def preprocess_document(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Preprocess document for vectorization.

        Args:
            doc: Raw document dictionary

        Returns:
            Preprocessed document
        """
        # Make a copy to avoid modifying original
        processed = doc.copy()

        # Normalize whitespace in text content
        text = processed["text_content"]
        text = " ".join(text.split())  # Collapse multiple whitespace

        # Store truncated version for TextContent field (32000 chars max)
        processed["text_content"] = text[:32000]

        return processed

    def vectorize(
        self,
        input_file: str,
        batch_size: int = 50,
        resume: bool = False,
        show_progress: bool = True,
        table_name: str = "ClinicalNoteVectors"
    ) -> Dict[str, Any]:
        """
        Vectorize clinical notes from input file.

        Args:
            input_file: Path to JSON file with clinical notes
            batch_size: Number of documents per batch
            resume: Whether to resume from checkpoint
            show_progress: Whether to show progress updates
            table_name: Name of the IRIS table to insert into
        """
        # Load documents
        documents = self.load_documents(input_file)
        self.stats["total_documents"] = len(documents)

        # Validate and preprocess
        valid_documents = []
        validation_errors = []

        for doc in documents:
            # Validate
            error = self.validate_document(doc)
            if error:
                validation_errors.append({
                    "resource_id": doc.get("resource_id", "unknown"),
                    "error": error
                })
                self.stats["validation_errors"] += 1
                continue

            # Preprocess
            processed = self.preprocess_document(doc)
            valid_documents.append(processed)

        # Log validation errors to file
        if validation_errors:
            self._log_validation_errors(validation_errors)
            logger.warning(f"! {len(validation_errors)} validation errors (see {self.error_log})")

        logger.info(f"✓ {len(valid_documents):,} valid documents ready for vectorization")

        # Initialize batch processor
        with BatchProcessor(
            embedding_client=self.embedding_client,
            vector_db_client=self.vector_db_client,
            checkpoint_db=self.checkpoint_db,
            table_name=table_name
        ) as processor:

            self.stats["start_time"] = datetime.utcnow()

            # Process or resume
            if resume:
                logger.info("Resuming from checkpoint...")
                result_stats = processor.resume(
                    documents=valid_documents,
                    batch_size=batch_size,
                    show_progress=show_progress
                )
            else:
                result_stats = processor.process_documents(
                    documents=valid_documents,
                    batch_size=batch_size,
                    show_progress=show_progress,
                    on_batch_complete=self._on_batch_complete if show_progress else None
                )

            self.stats["end_time"] = datetime.utcnow()
            self.stats["processed"] = result_stats["total_processed"]
            self.stats["successful"] = result_stats["successful"]
            self.stats["failed"] = result_stats["failed"]

        return self.stats

    def _on_batch_complete(
        self,
        batch_num: int,
        total_batches: int,
        stats: Dict[str, Any]
    ) -> None:
        """
        Callback invoked after each batch completes.

        Args:
            batch_num: Current batch number
            total_batches: Total number of batches
            stats: Current processing statistics
        """
        # Calculate throughput
        if stats.get("start_time"):
            elapsed = (datetime.utcnow() - stats["start_time"]).total_seconds()
            if elapsed > 0:
                docs_per_min = (stats["successful"] / elapsed) * 60

                # Estimate time remaining
                remaining_batches = total_batches - batch_num
                remaining_time = (remaining_batches / batch_num) * elapsed if batch_num > 0 else 0

                logger.info(
                    f"Progress: {batch_num}/{total_batches} batches | "
                    f"{stats['successful']:,} successful | "
                    f"{stats['failed']} failed | "
                    f"{docs_per_min:.1f} docs/min | "
                    f"ETA: {remaining_time/60:.1f} min"
                )

    def _log_validation_errors(self, errors: List[Dict[str, str]]) -> None:
        """
        Log validation errors to error log file.

        Args:
            errors: List of validation error dictionaries
        """
        error_log_path = Path(self.error_log)

        with open(error_log_path, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"Validation Errors - {datetime.utcnow().isoformat()}\n")
            f.write(f"{'='*80}\n")

            for error in errors:
                f.write(f"Resource ID: {error['resource_id']}\n")
                f.write(f"Error: {error['error']}\n")
                f.write("-" * 80 + "\n")

    def test_search(self, query: str = "diabetes", top_k: int = 3) -> None:
        """
        Test vector similarity search with sample query.

        Args:
            query: Search query text
            top_k: Number of results to return
        """
        logger.info(f"\nTesting vector search: '{query}'")

        # Generate query embedding
        query_embedding = self.embedding_client.embed(query)

        # Search
        results = self.vector_db_client.search_similar(
            query_vector=query_embedding,
            top_k=top_k
        )

        # Display results
        logger.info(f"\nTop {len(results)} results:")
        for i, result in enumerate(results, 1):
            logger.info(f"\n{i}. Similarity: {result['similarity']:.3f}")
            logger.info(f"   Patient ID: {result['patient_id']}")
            logger.info(f"   Doc Type: {result['document_type']}")
            logger.info(f"   Content: {result['text_content'][:200]}...")

    def print_summary(self) -> None:
        """Print final processing summary."""
        elapsed = 0
        if self.stats["start_time"] and self.stats["end_time"]:
            elapsed = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()

        logger.info("\n" + "="*80)
        logger.info("Vectorization Summary")
        logger.info("="*80)
        logger.info(f"Total documents:      {self.stats['total_documents']:,}")
        logger.info(f"Validation errors:    {self.stats['validation_errors']:,}")
        logger.info(f"Processed:            {self.stats['processed']:,}")
        logger.info(f"Successful:           {self.stats['successful']:,}")
        logger.info(f"Failed:               {self.stats['failed']:,}")
        logger.info(f"Elapsed time:         {elapsed:.1f}s ({elapsed/60:.1f} min)")

        if elapsed > 0 and self.stats["successful"] > 0:
            docs_per_min = (self.stats["successful"] / elapsed) * 60
            logger.info(f"Throughput:           {docs_per_min:.1f} docs/min")

        logger.info("="*80)


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Vectorize clinical notes into IRIS vector database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Initial vectorization
  %(prog)s --input synthea_clinical_notes.json --batch-size 50

  # Resume from checkpoint
  %(prog)s --input synthea_clinical_notes.json --resume

  # Test search after vectorization
  %(prog)s --input synthea_clinical_notes.json --test-search "diabetes"
"""
    )

    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Path to JSON file containing clinical notes"
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of documents to process per batch (default: 50)"
    )

    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from checkpoint (skip already processed documents)"
    )

    parser.add_argument(
        "--test-search",
        type=str,
        nargs='?',
        const="diabetes",
        help="Test vector search after vectorization with optional query (default: 'diabetes')"
    )

    parser.add_argument(
        "--checkpoint-db",
        type=str,
        default="vectorization_state.db",
        help="Path to SQLite checkpoint database (default: vectorization_state.db)"
    )

    parser.add_argument(
        "--error-log",
        type=str,
        default="vectorization_errors.log",
        help="Path to error log file (default: vectorization_errors.log)"
    )

    parser.add_argument(
        "--table-name",
        type=str,
        default="ClinicalNoteVectors",
        help="IRIS table name for storing vectors (default: ClinicalNoteVectors)"
    )

    parser.add_argument(
        "--iris-host",
        type=str,
        default=os.getenv("IRIS_HOST", "44.200.206.67"),
        help="IRIS database host (default: $IRIS_HOST or 44.200.206.67)"
    )

    parser.add_argument(
        "--iris-port",
        type=int,
        default=int(os.getenv("IRIS_PORT", "1972")),
        help="IRIS SQL port (default: $IRIS_PORT or 1972)"
    )

    parser.add_argument(
        "--iris-namespace",
        type=str,
        default=os.getenv("IRIS_NAMESPACE", "USER"),
        help="IRIS namespace (default: $IRIS_NAMESPACE or USER)"
    )

    parser.add_argument(
        "--iris-username",
        type=str,
        default=os.getenv("IRIS_USERNAME", "_SYSTEM"),
        help="IRIS username (default: $IRIS_USERNAME or _SYSTEM)"
    )

    parser.add_argument(
        "--iris-password",
        type=str,
        default=os.getenv("IRIS_PASSWORD", "SYS"),
        help="IRIS password (default: $IRIS_PASSWORD or SYS)"
    )

    return parser.parse_args()


def main() -> int:
    """
    Main entry point for vectorization pipeline.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    args = parse_arguments()

    try:
        # Initialize clients
        logger.info("Initializing NVIDIA NIM embeddings client...")
        embedding_client = NVIDIAEmbeddingsClient()

        logger.info("Initializing IRIS vector database client...")
        vector_db_client = IRISVectorDBClient(
            host=args.iris_host,
            port=args.iris_port,
            namespace=args.iris_namespace,
            username=args.iris_username,
            password=args.iris_password,
            vector_dimension=1024  # NV-EmbedQA-E5-V5 dimension
        )

        # Connect to IRIS
        vector_db_client.connect()

        # Initialize vectorizer
        vectorizer = ClinicalNoteVectorizer(
            embedding_client=embedding_client,
            vector_db_client=vector_db_client,
            checkpoint_db=args.checkpoint_db,
            error_log=args.error_log
        )

        # Vectorize documents
        logger.info(f"\nStarting vectorization pipeline...")
        logger.info(f"Input file: {args.input}")
        logger.info(f"Batch size: {args.batch_size}")
        logger.info(f"Resume mode: {args.resume}")
        logger.info("")

        vectorizer.vectorize(
            input_file=args.input,
            batch_size=args.batch_size,
            resume=args.resume,
            show_progress=True,
            table_name=args.table_name
        )

        # Print summary
        vectorizer.print_summary()

        # Test search if requested
        if args.test_search:
            vectorizer.test_search(query=args.test_search, top_k=3)

        # Cleanup
        vector_db_client.disconnect()
        embedding_client.close()

        logger.info("\n✅ Vectorization complete!")
        return 0

    except KeyboardInterrupt:
        logger.warning("\n⚠ Interrupted by user")
        return 1

    except Exception as e:
        logger.error(f"\n✗ Vectorization failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
