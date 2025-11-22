"""
Test vector search with pluggable embeddings.

Tests semantic search using OpenAI or NIM embeddings.
"""

import iris
import logging
import sys

# Add src to path
sys.path.insert(0, '/Users/tdyar/ws/FHIR-AI-Hackathon-Kit')

from src.embeddings.embeddings_factory import EmbeddingsFactory

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def vector_search(query: str, top_k: int = 5):
    """
    Perform vector similarity search.

    Args:
        query: Search query text
        top_k: Number of results to return
    """
    # Create embeddings provider
    logger.info("Initializing embeddings provider...")
    embedder = EmbeddingsFactory.create()

    logger.info(f"Provider: {embedder.provider}")
    logger.info(f"Model: {embedder.model_name}")
    logger.info(f"Dimension: {embedder.dimension}")

    # Generate query vector
    logger.info(f"\nGenerating embedding for query: '{query}'")
    query_vector = embedder.embed_query(query)

    # Connect to IRIS
    conn = iris.connect('localhost', 32782, 'DEMO', '_SYSTEM', 'ISCDEMO')
    cursor = conn.cursor()

    # Vector search (filter by provider to ensure dimension match)
    logger.info(f"\nSearching vectors (provider={embedder.provider})...")
    cursor.execute(f"""
        SELECT TOP {top_k}
            ResourceID,
            VECTOR_COSINE(Vector, TO_VECTOR(?)) AS similarity,
            SUBSTRING(TextContent, 1, 200) AS preview
        FROM VectorSearch.FHIRTextVectors
        WHERE Provider = ?
        ORDER BY similarity DESC
    """, (str(query_vector), embedder.provider))

    results = cursor.fetchall()

    # Display results
    print()
    print("=" * 80)
    print(f"Vector Search Results (Top {top_k})")
    print("=" * 80)
    print(f"Query: {query}")
    print(f"Provider: {embedder.provider} ({embedder.dimension}-dim)")
    print()

    if not results:
        print("No results found!")
        print()
        print("Troubleshooting:")
        print(f"  1. Check vectors exist for provider '{embedder.provider}':")
        print(f"     SELECT COUNT(*) FROM VectorSearch.FHIRTextVectors WHERE Provider = '{embedder.provider}'")
        print()
        print("  2. Re-run vectorization:")
        print("     python src/setup/vectorize_documents.py")
    else:
        for idx, (resource_id, similarity, preview) in enumerate(results, 1):
            print(f"{idx}. ResourceID: {resource_id}")
            print(f"   Similarity: {similarity:.4f}")
            print(f"   Preview: {preview}...")
            print()

    cursor.close()
    conn.close()


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        query = ' '.join(sys.argv[1:])
    else:
        query = "chest pain and shortness of breath"

    vector_search(query)

    print()
    print("=" * 80)
    print("Test Complete")
    print("=" * 80)
    print()
    print("Try different queries:")
    print("  python src/query/test_vector_search.py \"respiratory symptoms\"")
    print("  python src/query/test_vector_search.py \"diabetes management\"")
    print()
    print("Switch providers:")
    print("  export EMBEDDINGS_PROVIDER='nim'  # or 'openai'")
    print("  python src/query/test_vector_search.py \"chest pain\"")
