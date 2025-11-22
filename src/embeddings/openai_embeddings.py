"""
OpenAI embeddings adapter for development use.

Uses OpenAI API for fast development iteration without GPU infrastructure.
Cost: ~$1-5/month for 51 documents.
"""

import os
import logging
from typing import List
from openai import OpenAI

from .base_embeddings import BaseEmbeddings

logger = logging.getLogger(__name__)


class OpenAIEmbeddings(BaseEmbeddings):
    """OpenAI embeddings adapter."""

    def __init__(self, model: str = "text-embedding-3-large"):
        """
        Initialize OpenAI embeddings.

        Args:
            model: OpenAI embedding model
                - text-embedding-3-small (1536-dim, $0.00002/1K tokens)
                - text-embedding-3-large (3072-dim, $0.00013/1K tokens)

        Raises:
            ValueError: If OPENAI_API_KEY environment variable not set
        """
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable not set.\n"
                "To fix:\n"
                "  1. Get API key from https://platform.openai.com/api-keys\n"
                "  2. export OPENAI_API_KEY='sk-...'\n"
                "  3. Try again"
            )

        self.client = OpenAI(api_key=api_key)
        self._model_name = model

        # Dimension based on model
        self._dimension = 3072 if "large" in model else 1536

        logger.info(f"OpenAI embeddings initialized: model={model}, dimension={self._dimension}")

    def embed_query(self, text: str) -> List[float]:
        """
        Embed a single query.

        Args:
            text: Query text to embed

        Returns:
            Embedding vector as list of floats

        Raises:
            ValueError: If text is empty
            ConnectionError: If OpenAI API is unreachable
        """
        if not text or not text.strip():
            raise ValueError("Cannot embed empty text")

        try:
            response = self.client.embeddings.create(
                input=text,
                model=self._model_name
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise ConnectionError(f"OpenAI API error: {e}") from e

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed multiple documents (batch).

        Args:
            texts: List of document texts to embed

        Returns:
            List of embedding vectors

        Raises:
            ValueError: If texts list is empty
            ConnectionError: If OpenAI API is unreachable
        """
        if not texts:
            raise ValueError("Cannot embed empty document list")

        # Filter out empty strings
        valid_texts = [t for t in texts if t and t.strip()]
        if not valid_texts:
            raise ValueError("All texts are empty")

        try:
            response = self.client.embeddings.create(
                input=valid_texts,
                model=self._model_name
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"OpenAI API batch error: {e}")
            raise ConnectionError(f"OpenAI API batch error: {e}") from e

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return self._dimension

    @property
    def provider(self) -> str:
        """Get provider name."""
        return "openai"

    @property
    def model_name(self) -> str:
        """Get model name."""
        return self._model_name
