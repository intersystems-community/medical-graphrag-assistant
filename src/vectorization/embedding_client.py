"""
NVIDIA NIM Embeddings Client

Client for NVIDIA NIM Cloud API (nvidia/nv-embedqa-e5-v5) with batch processing,
retry logic with exponential backoff, and rate limiting.

Usage:
    from embedding_client import NVIDIAEmbeddingsClient

    client = NVIDIAEmbeddingsClient(api_key="nvapi-xxx")

    # Single text
    embedding = client.embed("This is a clinical note")

    # Batch
    embeddings = client.embed_batch(["text 1", "text 2", ...])

Dependencies:
    pip install requests tenacity
"""

import os
import time
from typing import List, Dict, Any, Optional
import logging

try:
    import requests
except ImportError:
    raise ImportError("requests package required. Install with: pip install requests")

try:
    from tenacity import (
        retry,
        stop_after_attempt,
        wait_exponential,
        retry_if_exception_type
    )
except ImportError:
    raise ImportError("tenacity package required. Install with: pip install tenacity")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    """Raised when API rate limit is exceeded."""
    pass


class NVIDIAEmbeddingsClient:
    """
    Client for NVIDIA NIM embeddings API with retry and rate limiting.

    Features:
    - Automatic retry with exponential backoff
    - Rate limiting (60 requests/minute default)
    - Batch processing support
    - Error handling and logging
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "nvidia/nv-embedqa-e5-v5",
        api_endpoint: str = "https://ai.api.nvidia.com/v1/retrieval/nvidia/nv-embedqa-e5-v5/embeddings",
        batch_size: int = 50,
        requests_per_minute: int = 60,
        max_retries: int = 3
    ):
        """
        Initialize NVIDIA embeddings client.

        Args:
            api_key: NVIDIA API key (or set NVIDIA_API_KEY env var)
            model: Model identifier
            api_endpoint: API endpoint URL
            batch_size: Maximum texts per batch request
            requests_per_minute: Rate limit for API calls
            max_retries: Maximum retry attempts for failed requests
        """
        self.api_key = api_key or os.getenv("NVIDIA_API_KEY")
        if not self.api_key:
            raise ValueError(
                "NVIDIA API key required. Set NVIDIA_API_KEY environment "
                "variable or pass api_key parameter"
            )

        self.model = model
        self.api_endpoint = api_endpoint
        self.batch_size = batch_size
        self.requests_per_minute = requests_per_minute
        self.max_retries = max_retries

        # Rate limiting
        self.min_interval = 60.0 / requests_per_minute  # seconds between requests
        self.last_request_time = 0.0

        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })

        logger.info(f"Initialized NVIDIA embeddings client: {model}")
        logger.info(f"  Rate limit: {requests_per_minute} req/min")
        logger.info(f"  Batch size: {batch_size}")

    def _wait_for_rate_limit(self) -> None:
        """Enforce rate limiting by waiting if necessary."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.min_interval:
            wait_time = self.min_interval - time_since_last
            logger.debug(f"Rate limit: waiting {wait_time:.2f}s")
            time.sleep(wait_time)

        self.last_request_time = time.time()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.exceptions.RequestException, RateLimitError)),
        reraise=True
    )
    def _make_request(self, texts: List[str]) -> List[List[float]]:
        """
        Make API request with retry logic.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors

        Raises:
            RateLimitError: If rate limit exceeded
            requests.exceptions.RequestException: For other API errors
        """
        self._wait_for_rate_limit()

        payload = {
            "input": texts,
            "model": self.model,
            "input_type": "passage"  # or "query" for search queries
        }

        try:
            response = self.session.post(
                self.api_endpoint,
                json=payload,
                timeout=30
            )

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning(f"Rate limit exceeded. Retry after {retry_after}s")
                time.sleep(retry_after)
                raise RateLimitError("API rate limit exceeded")

            # Handle other errors
            response.raise_for_status()

            # Parse response
            data = response.json()

            # Extract embeddings from response
            embeddings = []
            for item in data.get("data", []):
                embeddings.append(item["embedding"])

            return embeddings

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error: {e}")
            logger.error(f"Response: {e.response.text if e.response else 'N/A'}")
            raise

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise

    def embed(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Input text

        Returns:
            Embedding vector (1024-dim)
        """
        embeddings = self._make_request([text])
        return embeddings[0]

    def embed_batch(
        self,
        texts: List[str],
        show_progress: bool = False
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts with automatic batching.

        Args:
            texts: List of input texts
            show_progress: Whether to log progress

        Returns:
            List of embedding vectors
        """
        all_embeddings = []

        num_batches = (len(texts) + self.batch_size - 1) // self.batch_size

        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1

            if show_progress:
                logger.info(f"Processing batch {batch_num}/{num_batches} ({len(batch)} texts)")

            try:
                embeddings = self._make_request(batch)
                all_embeddings.extend(embeddings)

            except Exception as e:
                logger.error(f"Batch {batch_num} failed: {e}")
                # Re-raise to allow caller to handle
                raise

        logger.info(f"✓ Generated {len(all_embeddings)} embeddings")
        return all_embeddings

    def get_embedding_dimension(self) -> int:
        """
        Get the embedding dimension for this model.

        Returns:
            Embedding dimension (1024 for nv-embedqa-e5-v5)
        """
        return 1024

    def close(self) -> None:
        """Close the HTTP session."""
        self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Example usage
if __name__ == "__main__":
    # Example: Generate embeddings
    client = NVIDIAEmbeddingsClient()

    # Single text
    text = "Patient presents with acute respiratory symptoms"
    embedding = client.embed(text)
    print(f"\nGenerated embedding for text (dim={len(embedding)})")
    print(f"First 5 values: {embedding[:5]}")

    # Batch
    texts = [
        "Patient has diabetes",
        "Prescribed metformin 1000mg BID",
        "Follow-up in 2 weeks"
    ]

    embeddings = client.embed_batch(texts, show_progress=True)
    print(f"\nGenerated {len(embeddings)} embeddings")
