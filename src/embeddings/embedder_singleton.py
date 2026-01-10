"""
Global singleton for NV-CLIP embedder to break circular dependencies.
"""

import sys
import os
from typing import Optional

# Add project root to path for imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Lazy import to avoid initialization issues
_embedder = None

def get_embedder():
    """
    Get or initialize the global NV-CLIP embedder using configuration.
    
    This singleton breaks the circular dependency between search services,
    caching modules, and the MCP server.
    """
    global _embedder
    
    if _embedder is None:
        try:
            # Local imports to avoid circular issues
            from src.embeddings.nvclip_embeddings import NVCLIPEmbeddings
            from src.search.base import BaseSearchService
            
            # Load config via base service
            base_service = BaseSearchService()
            config = base_service.config
            
            nvclip_config = config.get('nvclip', {})
            base_url = nvclip_config.get('base_url')
            
            if base_url:
                print(f"Initializing NV-CLIP Singleton with base_url: {base_url}", file=sys.stderr)
                _embedder = NVCLIPEmbeddings(base_url=base_url)
            else:
                _embedder = NVCLIPEmbeddings()
                
        except ImportError as e:
            print(f"Warning: Could not import NVCLIPEmbeddings: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Warning: Failed to initialize NV-CLIP Singleton: {e}", file=sys.stderr)
            
    return _embedder
