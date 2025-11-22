"""
Vectorize FHIR DocumentReference resources using pluggable embeddings.

Automatically uses OpenAI (development) or NIM (production) based on
EMBEDDINGS_PROVIDER environment variable.
"""

import iris
import json
import logging
import sys
import time
from typing import List, Tuple

# Add src to path
sys.path.insert(0, '/Users/tdyar/ws/FHIR-AI-Hackathon-Kit')

from src.embeddings.embeddings_factory import EmbeddingsFactory

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_clinical_notes() -> List[Tuple[str, str]]:
    """
    Fetch all DocumentReference resources with clinical notes.

    Returns:
        List of (resource_id, clinical_note_text) tuples
    """
    conn = iris.connect('localhost', 32782, 'DEMO', '_SYSTEM', 'ISCDEMO')
    cursor = conn.cursor()

    logger.info("Fetching DocumentReference resources...")

    cursor.execute("""
        SELECT ID, ResourceString
        FROM HSFHIR_X0001_R.Rsrc
        WHERE ResourceType = 'DocumentReference'
        AND (Deleted = 0 OR Deleted IS NULL)
    """)

    documents = []

    for resource_id, resource_string in cursor.fetchall():
        try:
            # Parse FHIR JSON
            fhir_data = json.loads(resource_string)

            # Decode hex-encoded clinical note
            hex_data = fhir_data['content'][0]['attachment']['data']
            clinical_note = bytes.fromhex(hex_data).decode('utf-8', errors='replace')

            documents.append((resource_id, clinical_note))

        except (KeyError, ValueError) as e:
            logger.warning(f"Skipping resource {resource_id}: {e}")
            continue

    cursor.close()
    conn.close()

    logger.info(f"Found {len(documents)} DocumentReference resources with clinical notes")
    return documents


def vectorize_all_documents(batch_size: int = 50):
    """
    Vectorize all DocumentReference resources.

    Args:
        batch_size: Number of documents to process per batch
    """
    start_time = time.time()

    # Create embeddings provider (auto-detect from env)
    logger.info("Initializing embeddings provider...")
    embedder = EmbeddingsFactory.create()

    logger.info(f"Using embeddings provider: {embedder.provider}")
    logger.info(f"Model: {embedder.model_name}")
    logger.info(f"Embedding dimension: {embedder.dimension}")

    # Get all clinical notes
    documents = get_clinical_notes()

    if not documents:
        logger.warning("No documents to vectorize!")
        return

    # Connect to IRIS for insertion
    conn = iris.connect('localhost', 32782, 'DEMO', '_SYSTEM', 'ISCDEMO')
    cursor = conn.cursor()

    # Delete existing vectors for this provider (fresh start)
    logger.info(f"Deleting existing vectors for provider '{embedder.provider}'...")
    cursor.execute("""
        DELETE FROM VectorSearch.FHIRTextVectors
        WHERE Provider = ?
    """, (embedder.provider,))
    conn.commit()

    # Process documents in batches
    total_documents = len(documents)
    total_batches = (total_documents + batch_size - 1) // batch_size

    logger.info(f"Vectorizing {total_documents} documents in {total_batches} batches...")

    vectorized_count = 0

    for batch_idx in range(total_batches):
        batch_start = batch_idx * batch_size
        batch_end = min(batch_start + batch_size, total_documents)
        batch = documents[batch_start:batch_end]

        logger.info(f"Batch {batch_idx + 1}/{total_batches}: Processing documents {batch_start + 1}-{batch_end}...")

        # Extract texts for batch embedding
        batch_ids = [doc[0] for doc in batch]
        batch_texts = [doc[1] for doc in batch]

        try:
            # Generate embeddings (batch)
            batch_vectors = embedder.embed_documents(batch_texts)

            # Insert into database
            for resource_id, clinical_note, vector in zip(batch_ids, batch_texts, batch_vectors):
                cursor.execute("""
                    INSERT INTO VectorSearch.FHIRTextVectors
                    (ResourceID, ResourceType, TextContent, Vector, EmbeddingModel, Provider)
                    VALUES (?, ?, ?, TO_VECTOR(?), ?, ?)
                """, (
                    resource_id,
                    'DocumentReference',
                    clinical_note,
                    str(vector),
                    embedder.model_name,
                    embedder.provider
                ))

            conn.commit()
            vectorized_count += len(batch)
            logger.info(f"  ✅ Batch {batch_idx + 1} complete ({len(batch)} documents)")

        except Exception as e:
            logger.error(f"  ❌ Batch {batch_idx + 1} failed: {e}")
            conn.rollback()
            continue

    cursor.close()
    conn.close()

    elapsed_time = time.time() - start_time

    # Summary
    logger.info("=" * 60)
    logger.info("Vectorization Complete!")
    logger.info("=" * 60)
    logger.info(f"Provider: {embedder.provider}")
    logger.info(f"Model: {embedder.model_name}")
    logger.info(f"Dimension: {embedder.dimension}")
    logger.info(f"Documents vectorized: {vectorized_count}/{total_documents}")
    logger.info(f"Time elapsed: {elapsed_time:.2f} seconds")
    logger.info(f"Average: {elapsed_time/total_documents:.3f} seconds per document")
    logger.info("=" * 60)


if __name__ == '__main__':
    print()
    print("=" * 60)
    print("FHIR DocumentReference Vectorization")
    print("=" * 60)
    print()

    vectorize_all_documents()

    print()
    print("Next steps:")
    print("  1. Test vector search:")
    print("     python src/query/test_vector_search.py")
    print()
    print("  2. To switch providers:")
    print("     export EMBEDDINGS_PROVIDER='nim'  # or 'openai'")
    print("     python src/setup/vectorize_documents.py")
