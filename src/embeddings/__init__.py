"""
Pluggable embeddings module for FHIR GraphRAG.

Provides abstract interface for swapping between OpenAI (development)
and NVIDIA NIM (production) embedding providers.
"""

from .base_embeddings import BaseEmbeddings
from .openai_embeddings import OpenAIEmbeddings
from .nim_embeddings import NIMEmbeddings
from .embeddings_factory import EmbeddingsFactory

__all__ = [
    'BaseEmbeddings',
    'OpenAIEmbeddings',
    'NIMEmbeddings',
    'EmbeddingsFactory',
]
