"""
Embedding cache module for medical image search.

Provides LRU (Least Recently Used) caching for NV-CLIP text embeddings
to improve search performance by avoiding redundant API calls.
"""

from functools import lru_cache
from typing import Tuple
import sys


# Import embedder getter from MCP server
# Note: This creates a circular dependency that we handle carefully
def get_embedder():
    """
    Get NV-CLIP embedder instance.
    
    Imports from fhir_graphrag_mcp_server to get the global embedder.
    Returns None if embedder is not available.
    """
    try:
        # Add mcp-server to path if not already there
        import os
        mcp_path = os.path.join(os.path.dirname(__file__), '../../mcp-server')
        if mcp_path not in sys.path:
            sys.path.insert(0, mcp_path)
        
        from fhir_graphrag_mcp_server import get_embedder as _get_embedder
        return _get_embedder()
    except (ImportError, AttributeError):
        # Fall back to creating embedder directly
        try:
            from src.embeddings.nvclip_embeddings import NVCLIPEmbeddings
            return NVCLIPEmbeddings()
        except Exception:
            return None


@lru_cache(maxsize=1000)
def get_cached_embedding(query_text: str) -> Tuple[float, ...]:
    """
    Get or compute embedding for query text with LRU caching.
    
    This function caches text embeddings to avoid redundant calls to
    the NV-CLIP API. Identical queries return cached results instantly.
    
    Cache behavior:
    - Max size: 1000 queries
    - Eviction: Least Recently Used (LRU)
    - Thread-safe: functools.lru_cache is thread-safe
    
    Args:
        query_text: Natural language search query
        
    Returns:
        Tuple of floats representing the 1024-dim embedding vector.
        Returns tuple (not list) because tuples are hashable and
        can be used as cache keys.
        
    Raises:
        AttributeError: If embedder is None
        TypeError: If embedder.embed_text fails
        
    Example:
        >>> # First call - cache miss, calls NV-CLIP API
        >>> emb1 = get_cached_embedding("chest X-ray showing pneumonia")
        >>> 
        >>> # Second call - cache hit, returns instantly
        >>> emb2 = get_cached_embedding("chest X-ray showing pneumonia")
        >>> 
        >>> assert emb1 == emb2  # Same result
        >>> assert emb1 is emb2  # Same object (cached)
        
    Performance:
        - Cache miss: 500-2000ms (NV-CLIP API call)
        - Cache hit: <1ms (memory lookup)
        - Speedup: 500-2000x for cached queries
    """
    embedder = get_embedder()
    
    if embedder is None:
        raise AttributeError(
            "NV-CLIP embedder not available. "
            "Set NVIDIA_API_KEY environment variable or check embedder initialization."
        )
    
    # Get embedding from NV-CLIP
    # This returns a list of floats
    embedding_list = embedder.embed_text(query_text)
    
    # Convert list to tuple for hashability
    # (functools.lru_cache requires hashable return values)
    embedding_tuple = tuple(embedding_list)
    
    return embedding_tuple


def cache_info():
    """
    Get cache statistics.
    
    Returns CacheInfo named tuple with fields:
    - hits: Number of cache hits
    - misses: Number of cache misses
    - maxsize: Maximum cache size (1000)
    - currsize: Current number of cached items
    
    Returns:
        CacheInfo: Named tuple with cache statistics
        
    Example:
        >>> info = cache_info()
        >>> print(f"Hit rate: {info.hits / (info.hits + info.misses):.2%}")
        >>> print(f"Cache usage: {info.currsize}/{info.maxsize}")
    """
    return get_cached_embedding.cache_info()


def clear_cache():
    """
    Clear all cached embeddings and reset statistics.
    
    This resets:
    - All cached query→embedding mappings
    - Hit/miss counters
    - Current size counter
    
    Use this:
    - Before running tests (to ensure clean state)
    - When switching environments (dev→prod)
    - When RAM usage needs to be reduced
    
    Example:
        >>> clear_cache()
        >>> info = cache_info()
        >>> assert info.currsize == 0
        >>> assert info.hits == 0
        >>> assert info.misses == 0
    """
    get_cached_embedding.cache_clear()


class EmbeddingCache:
    """
    Static wrapper class for embedding cache operations.
    
    Provides object-oriented interface to the @lru_cache-decorated
    get_cached_embedding function. This class exists for better
    organization and discoverability.
    
    All methods are static/class methods since caching is global.
    
    Example:
        >>> # Using class interface
        >>> embedding = EmbeddingCache.get(query)
        >>> stats = EmbeddingCache.info()
        >>> EmbeddingCache.clear()
        >>> 
        >>> # Or using module-level functions directly
        >>> embedding = get_cached_embedding(query)
        >>> stats = cache_info()
        >>> clear_cache()
    """
    
    @staticmethod
    def get(query_text: str) -> Tuple[float, ...]:
        """
        Get cached embedding for query text.
        
        Alias for get_cached_embedding().
        
        Args:
            query_text: Search query
            
        Returns:
            Tuple of embedding floats
        """
        return get_cached_embedding(query_text)
    
    @staticmethod
    def info():
        """
        Get cache statistics.
        
        Alias for cache_info().
        
        Returns:
            CacheInfo named tuple
        """
        return cache_info()
    
    @staticmethod
    def clear():
        """
        Clear cache and reset statistics.
        
        Alias for clear_cache().
        """
        clear_cache()
    
    @staticmethod
    def hit_rate() -> float:
        """
        Calculate cache hit rate as percentage.
        
        Returns:
            float: Hit rate from 0.0 to 1.0
                   Returns 0.0 if no queries cached yet
                   
        Example:
            >>> rate = EmbeddingCache.hit_rate()
            >>> print(f"Cache hit rate: {rate:.1%}")
        """
        info = cache_info()
        total = info.hits + info.misses
        
        if total == 0:
            return 0.0
        
        return info.hits / total
    
    @staticmethod
    def size() -> int:
        """
        Get current number of cached items.
        
        Returns:
            int: Number of unique queries currently cached
        """
        return cache_info().currsize
    
    @staticmethod
    def maxsize() -> int:
        """
        Get maximum cache size.
        
        Returns:
            int: Maximum number of queries that can be cached (1000)
        """
        return cache_info().maxsize
    
    @staticmethod
    def is_full() -> bool:
        """
        Check if cache is at maximum capacity.
        
        Returns:
            bool: True if cache is full
        """
        info = cache_info()
        return info.currsize >= info.maxsize


if __name__ == '__main__':
    # Demo usage
    print("Embedding Cache Demo")
    print("=" * 50)
    
    # Clear cache for clean demo
    clear_cache()
    
    test_queries = [
        "chest X-ray showing pneumonia",
        "bilateral lung infiltrates",
        "cardiomegaly",
        "chest X-ray showing pneumonia",  # Duplicate - should hit cache
        "bilateral lung infiltrates",      # Duplicate
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\nQuery {i}: {query[:40]}...")
        
        try:
            embedding = get_cached_embedding(query)
            print(f"  Embedding dimension: {len(embedding)}")
            print(f"  First 5 values: {embedding[:5]}")
            
            info = cache_info()
            print(f"  Cache stats: {info.hits} hits, {info.misses} misses, {info.currsize} cached")
            print(f"  Hit rate: {EmbeddingCache.hit_rate():.1%}")
            
        except Exception as e:
            print(f"  Error: {e}")
            print("  (This is expected if NVIDIA_API_KEY not set)")
    
    print("\n" + "=" * 50)
    print("Final cache statistics:")
    info = cache_info()
    print(f"  Total queries: {info.hits + info.misses}")
    print(f"  Cache hits: {info.hits}")
    print(f"  Cache misses: {info.misses}")
    print(f"  Hit rate: {EmbeddingCache.hit_rate():.1%}")
    print(f"  Cached items: {info.currsize}/{info.maxsize}")
    print(f"  Cache full: {EmbeddingCache.is_full()}")
