"""
NVIDIA NIM embeddings adapter for production use.

Uses self-hosted NIM on AWS EC2 for HIPAA-compliant private deployment.
All medical data stays within your infrastructure.
"""

import os
import logging
from typing import List
import requests

from .base_embeddings import BaseEmbeddings

logger = logging.getLogger(__name__)


class NIMEmbeddings(BaseEmbeddings):
    """Self-hosted NIM embeddings adapter."""

    def __init__(self,
                 endpoint: str = None,
                 model: str = "nvidia/nv-embedqa-e5-v5"):
        """
        Initialize NIM embeddings.

        Args:
            endpoint: NIM inference endpoint URL
                     If None, uses NIM_ENDPOINT env var or default localhost
            model: NIM model name (for metadata)

        Raises:
            ConnectionError: If NIM endpoint is unreachable
        """
        # Determine endpoint
        if endpoint is None:
            endpoint = os.environ.get(
                'NIM_ENDPOINT',
                'http://localhost:8000/v1/embeddings'
            )

        self.endpoint = endpoint
        self._model_name = model

        # NV-EmbedQA-E5-v5 is 1024-dimensional
        self._dimension = 1024

        # Test connection
        self._test_connection()

        logger.info(f"NIM embeddings initialized: endpoint={endpoint}, model={model}, dimension={self._dimension}")

    def _test_connection(self):
        """
        Test NIM endpoint is reachable.

        Raises:
            ConnectionError: If NIM endpoint unreachable
        """
        try:
            # Try health check endpoint
            health_url = self.endpoint.replace('/v1/embeddings', '/health')
            response = requests.get(health_url, timeout=5)

            if response.status_code != 200:
                raise ConnectionError(
                    f"NIM health check failed: {response.status_code}\n"
                    f"Endpoint: {health_url}\n"
                    f"Make sure NIM container is running.\n"
                    f"To start EC2: ./scripts/aws/start-nim-ec2.sh"
                )

            logger.info(f"NIM health check passed: {health_url}")

        except requests.exceptions.RequestException as e:
            raise ConnectionError(
                f"Cannot reach NIM endpoint: {self.endpoint}\n"
                f"Error: {e}\n"
                f"To start EC2: ./scripts/aws/start-nim-ec2.sh"
            ) from e

    def embed_query(self, text: str) -> List[float]:
        """
        Embed a single query.

        Args:
            text: Query text to embed

        Returns:
            Embedding vector as list of floats

        Raises:
            ValueError: If text is empty
            ConnectionError: If NIM endpoint is unreachable
        """
        if not text or not text.strip():
            raise ValueError("Cannot embed empty text")

        try:
            response = requests.post(
                self.endpoint,
                json={
                    "input": text,
                    "model": self._model_name,
                    "input_type": "query"
                },
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]

        except requests.exceptions.RequestException as e:
            logger.error(f"NIM API error: {e}")
            raise ConnectionError(f"NIM API error: {e}") from e

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed multiple documents (batch).

        Args:
            texts: List of document texts to embed

        Returns:
            List of embedding vectors

        Raises:
            ValueError: If texts list is empty
            ConnectionError: If NIM endpoint is unreachable
        """
        if not texts:
            raise ValueError("Cannot embed empty document list")

        # Filter out empty strings
        valid_texts = [t for t in texts if t and t.strip()]
        if not valid_texts:
            raise ValueError("All texts are empty")

        try:
            response = requests.post(
                self.endpoint,
                json={
                    "input": valid_texts,
                    "model": self._model_name,
                    "input_type": "passage"
                },
                headers={"Content-Type": "application/json"},
                timeout=60
            )
            response.raise_for_status()
            data = response.json()

            # Sort by index to maintain order
            sorted_data = sorted(data["data"], key=lambda x: x["index"])
            return [item["embedding"] for item in sorted_data]

        except requests.exceptions.RequestException as e:
            logger.error(f"NIM API batch error: {e}")
            raise ConnectionError(f"NIM API batch error: {e}") from e

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return self._dimension

    @property
    def provider(self) -> str:
        """Get provider name."""
        return "nim"

    @property
    def model_name(self) -> str:
        """Get model name."""
        return self._model_name
