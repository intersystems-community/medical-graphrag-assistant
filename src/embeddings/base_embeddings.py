"""
Abstract base class for embeddings providers.

This interface allows seamless switching between OpenAI (development)
and NVIDIA NIM (production) without code changes.
"""

from abc import ABC, abstractmethod
from typing import List


class BaseEmbeddings(ABC):
    """Abstract base class for embeddings providers."""

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """
        Embed a single query text.

        Args:
            text: Query text to embed

        Returns:
            List of floats representing the embedding vector

        Raises:
            ValueError: If text is empty or invalid
            ConnectionError: If provider is unreachable
        """
        pass

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed multiple documents in batch.

        Args:
            texts: List of document texts to embed

        Returns:
            List of embedding vectors (one per document)

        Raises:
            ValueError: If texts list is empty or contains invalid entries
            ConnectionError: If provider is unreachable
        """
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """
        Get embedding dimension.

        Returns:
            Integer dimension of embedding vectors
        """
        pass

    @property
    @abstractmethod
    def provider(self) -> str:
        """
        Get provider name.

        Returns:
            Provider identifier ('openai', 'nim', etc.)
        """
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """
        Get model name.

        Returns:
            Model identifier (e.g., 'text-embedding-3-large')
        """
        pass
