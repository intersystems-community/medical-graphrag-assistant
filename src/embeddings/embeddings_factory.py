"""
Factory for creating embeddings providers.

Allows seamless switching between OpenAI and NIM by changing
a single environment variable.
"""

import os
import logging
from typing import Optional

from .base_embeddings import BaseEmbeddings
from .openai_embeddings import OpenAIEmbeddings
from .nim_embeddings import NIMEmbeddings
from .nvclip_embeddings import NVCLIPEmbeddings

logger = logging.getLogger(__name__)


class EmbeddingsFactory:
    """Factory for creating embeddings providers."""

    @staticmethod
    def create(provider: Optional[str] = None) -> BaseEmbeddings:
        """
        Create embeddings provider.

        Args:
            provider: 'openai', 'nim', or None (auto-detect from env)

        Returns:
            BaseEmbeddings instance

        Raises:
            ValueError: If provider is unknown

        Environment Variables:
            EMBEDDINGS_PROVIDER: 'openai', 'nim', or 'nvclip' (default: 'openai')
            OPENAI_API_KEY: Required for OpenAI
            NVIDIA_API_KEY: Required for NV-CLIP
            NIM_ENDPOINT: Optional for NIM (default: http://localhost:8000/v1/embeddings)

        Examples:
            # Development mode (OpenAI)
            export EMBEDDINGS_PROVIDER="openai"
            export OPENAI_API_KEY="sk-..."
            embedder = EmbeddingsFactory.create()

            # Production mode (NIM)
            export EMBEDDINGS_PROVIDER="nim"
            export NIM_ENDPOINT="http://ec2-xx-xx-xx-xx.amazonaws.com:8000/v1/embeddings"
            embedder = EmbeddingsFactory.create()
        """
        # Auto-detect from environment
        if provider is None:
            provider = os.environ.get('EMBEDDINGS_PROVIDER', 'openai')

            # Warn if not explicitly set
            if 'EMBEDDINGS_PROVIDER' not in os.environ:
                logger.warning(
                    f"EMBEDDINGS_PROVIDER not set, defaulting to '{provider}'. "
                    f"Set explicitly for production use."
                )

        provider = provider.lower()

        # Create provider instance
        if provider == 'openai':
            logger.info("Creating OpenAI embeddings provider")
            return OpenAIEmbeddings(model='text-embedding-3-large')

        elif provider == 'nim':
            logger.info("Creating NIM embeddings provider")
            # NIM endpoint from env or default
            endpoint = os.environ.get('NIM_ENDPOINT')
            return NIMEmbeddings(endpoint=endpoint)

        elif provider == 'nvclip':
            logger.info("Creating NVIDIA NV-CLIP embeddings provider")
            api_key = os.environ.get('NVIDIA_API_KEY')
            return NVCLIPEmbeddings(api_key=api_key)

        else:
            raise ValueError(
                f"Unknown embeddings provider: '{provider}'\n"
                f"Valid options: 'openai', 'nim', 'nvclip'\n"
                f"Set EMBEDDINGS_PROVIDER environment variable."
            )

    @staticmethod
    def list_providers():
        """
        List available embeddings providers.

        Returns:
            List of provider names
        """
        return ['openai', 'nim', 'nvclip']

    @staticmethod
    def get_provider_info(provider: str) -> dict:
        """
        Get information about a provider.

        Args:
            provider: Provider name ('openai' or 'nim')

        Returns:
            Dictionary with provider info
        """
        info = {
            'openai': {
                'name': 'OpenAI',
                'model': 'text-embedding-3-large',
                'dimension': 3072,
                'cost': '~$1-5/month for development',
                'use_case': 'Fast development iteration without GPU',
                'requires': 'OPENAI_API_KEY environment variable',
            },
            'nim': {
                'name': 'NVIDIA NIM',
                'model': 'nvidia/nv-embedqa-e5-v5',
                'dimension': 1024,
                'cost': '~$160/month (EC2 8hrs/day)',
                'use_case': 'HIPAA-compliant production demos',
                'requires': 'NIM_ENDPOINT environment variable (optional)',
            },
            'nvclip': {
                'name': 'NVIDIA NV-CLIP',
                'model': 'nvidia/nv-clip (ViT-H)',
                'dimension': 1024,
                'cost': 'API usage costs (paid)',
                'use_case': 'Multimodal image+text embeddings for medical imaging',
                'requires': 'NVIDIA_API_KEY environment variable',
            }
        }

        provider = provider.lower()
        if provider not in info:
            raise ValueError(f"Unknown provider: {provider}")

        return info[provider]
