"""
Unit tests for src/search/cache.py

Tests embedding caching functionality with LRU (Least Recently Used) eviction.
Following TDD: These tests should FAIL initially until cache.py is implemented.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from src.search.cache import (
    EmbeddingCache,
    get_cached_embedding,
    clear_cache,
    cache_info
)


class TestEmbeddingCache:
    """Test the EmbeddingCache class."""
    
    def setup_method(self):
        """Clear cache before each test."""
        clear_cache()
    
    def test_cache_hit_for_identical_query(self):
        """Same query text should return cached result on second call."""
        query = "chest X-ray showing pneumonia"
        
        # First call - cache miss
        embedding1 = get_cached_embedding(query)
        
        # Second call - should be cache hit
        embedding2 = get_cached_embedding(query)
        
        # Results should be identical (same object)
        assert embedding1 == embedding2
        assert embedding1 is embedding2  # Same object in memory
    
    def test_cache_miss_for_different_query(self):
        """Different query text should miss cache."""
        query1 = "chest X-ray showing pneumonia"
        query2 = "bilateral lung infiltrates"
        
        embedding1 = get_cached_embedding(query1)
        embedding2 = get_cached_embedding(query2)
        
        # Results should be different
        assert embedding1 != embedding2
    
    def test_returns_tuple_not_list(self):
        """Cache should return tuple (hashable) not list."""
        query = "chest X-ray"
        
        embedding = get_cached_embedding(query)
        
        assert isinstance(embedding, tuple)
        assert not isinstance(embedding, list)
    
    def test_cache_statistics_track_hits_and_misses(self):
        """Cache info should track hits and misses correctly."""
        clear_cache()
        
        query1 = "pneumonia"
        query2 = "cardiomegaly"
        
        # First calls - 2 misses
        get_cached_embedding(query1)
        get_cached_embedding(query2)
        
        # Repeat calls - 2 hits
        get_cached_embedding(query1)
        get_cached_embedding(query2)
        
        info = cache_info()
        
        assert info.hits == 2
        assert info.misses == 2
        assert info.currsize == 2  # 2 unique queries cached
    
    def test_cache_info_returns_named_tuple(self):
        """cache_info() should return CacheInfo named tuple."""
        info = cache_info()
        
        # Should have standard cache_info attributes
        assert hasattr(info, 'hits')
        assert hasattr(info, 'misses')
        assert hasattr(info, 'maxsize')
        assert hasattr(info, 'currsize')
    
    def test_maxsize_is_1000(self):
        """Cache should have maxsize of 1000."""
        info = cache_info()
        assert info.maxsize == 1000
    
    def test_lru_eviction_when_maxsize_exceeded(self):
        """Least recently used items should be evicted when cache is full."""
        clear_cache()
        
        # Fill cache to maxsize (1000)
        for i in range(1000):
            get_cached_embedding(f"query_{i}")
        
        info = cache_info()
        assert info.currsize == 1000
        
        # Add one more - should evict oldest
        get_cached_embedding("query_1000")
        
        info = cache_info()
        assert info.currsize == 1000  # Still at maxsize
        
        # Oldest query (query_0) should have been evicted
        # Accessing it should be a cache miss
        initial_misses = cache_info().misses
        get_cached_embedding("query_0")
        assert cache_info().misses == initial_misses + 1  # New miss
    
    def test_clear_cache_resets_all_stats(self):
        """clear_cache() should reset all cached items and statistics."""
        # Populate cache
        get_cached_embedding("query1")
        get_cached_embedding("query2")
        get_cached_embedding("query1")  # Hit
        
        # Verify cache has items
        assert cache_info().currsize > 0
        assert cache_info().hits > 0
        
        # Clear cache
        clear_cache()
        
        # Verify reset
        info = cache_info()
        assert info.hits == 0
        assert info.misses == 0
        assert info.currsize == 0
    
    def test_case_sensitive_caching(self):
        """Cache should be case-sensitive (different cases = different cache entries)."""
        query_lower = "chest x-ray"
        query_upper = "Chest X-Ray"
        
        embedding1 = get_cached_embedding(query_lower)
        embedding2 = get_cached_embedding(query_upper)
        
        # Should be different cache entries
        info = cache_info()
        assert info.currsize == 2  # Two separate entries
    
    def test_whitespace_matters_for_caching(self):
        """Cache should treat different whitespace as different queries."""
        query1 = "chest X-ray"
        query2 = "chest  X-ray"  # Extra space
        
        embedding1 = get_cached_embedding(query1)
        embedding2 = get_cached_embedding(query2)
        
        info = cache_info()
        assert info.currsize == 2  # Two separate entries


class TestGetCachedEmbedding:
    """Test the get_cached_embedding function."""
    
    def setup_method(self):
        """Clear cache before each test."""
        clear_cache()
    
    @patch('src.search.cache.get_embedder')
    def test_calls_embedder_on_cache_miss(self, mock_get_embedder):
        """Should call NV-CLIP embedder on cache miss."""
        # Setup mock embedder
        mock_embedder = Mock()
        mock_embedder.embed_text.return_value = [0.1, 0.2, 0.3]
        mock_get_embedder.return_value = mock_embedder
        
        query = "test query"
        get_cached_embedding(query)
        
        # Verify embedder was called
        mock_embedder.embed_text.assert_called_once_with(query)
    
    @patch('src.search.cache.get_embedder')
    def test_does_not_call_embedder_on_cache_hit(self, mock_get_embedder):
        """Should NOT call embedder on cache hit (performance optimization)."""
        # Setup mock embedder
        mock_embedder = Mock()
        mock_embedder.embed_text.return_value = [0.1, 0.2, 0.3]
        mock_get_embedder.return_value = mock_embedder
        
        query = "test query"
        
        # First call - cache miss
        get_cached_embedding(query)
        assert mock_embedder.embed_text.call_count == 1
        
        # Second call - cache hit, should not call embedder
        get_cached_embedding(query)
        assert mock_embedder.embed_text.call_count == 1  # Still 1, not 2
    
    @patch('src.search.cache.get_embedder')
    def test_converts_list_to_tuple(self, mock_get_embedder):
        """Should convert embedder's list output to tuple for hashing."""
        # Embedder returns list
        mock_embedder = Mock()
        mock_embedder.embed_text.return_value = [0.1, 0.2, 0.3, 0.4, 0.5]
        mock_get_embedder.return_value = mock_embedder
        
        query = "test"
        result = get_cached_embedding(query)
        
        # Result should be tuple
        assert isinstance(result, tuple)
        assert result == (0.1, 0.2, 0.3, 0.4, 0.5)
    
    @patch('src.search.cache.get_embedder')
    def test_handles_large_embeddings(self, mock_get_embedder):
        """Should handle 1024-dim embeddings (NV-CLIP size)."""
        # Create 1024-dim embedding
        large_embedding = [float(i) for i in range(1024)]
        
        mock_embedder = Mock()
        mock_embedder.embed_text.return_value = large_embedding
        mock_get_embedder.return_value = mock_embedder
        
        query = "large embedding test"
        result = get_cached_embedding(query)
        
        assert len(result) == 1024
        assert isinstance(result, tuple)
    
    @patch('src.search.cache.get_embedder')
    def test_caches_none_embedder(self, mock_get_embedder):
        """Should handle case when embedder is None gracefully."""
        mock_get_embedder.return_value = None
        
        query = "test"
        
        # Should raise an error or return None
        with pytest.raises((AttributeError, TypeError)):
            get_cached_embedding(query)


class TestCachePerformance:
    """Test cache performance and behavior."""
    
    def setup_method(self):
        """Clear cache before each test."""
        clear_cache()
    
    @patch('src.search.cache.get_embedder')
    def test_cache_hit_is_faster_than_miss(self, mock_get_embedder):
        """Cache hit should be significantly faster than miss."""
        # Mock embedder with slight delay
        mock_embedder = Mock()
        
        def slow_embed(text):
            time.sleep(0.01)  # 10ms delay to simulate API call
            return [0.1, 0.2, 0.3]
        
        mock_embedder.embed_text = slow_embed
        mock_get_embedder.return_value = mock_embedder
        
        query = "performance test"
        
        # First call - cache miss (slow)
        start = time.time()
        get_cached_embedding(query)
        miss_time = time.time() - start
        
        # Second call - cache hit (fast)
        start = time.time()
        get_cached_embedding(query)
        hit_time = time.time() - start
        
        # Cache hit should be at least 10x faster
        assert hit_time < miss_time / 10
    
    @patch('src.search.cache.get_embedder')
    def test_concurrent_access_thread_safety(self, mock_get_embedder):
        """Cache should be thread-safe for concurrent access."""
        import threading
        
        mock_embedder = Mock()
        mock_embedder.embed_text.return_value = [0.1, 0.2, 0.3]
        mock_get_embedder.return_value = mock_embedder
        
        results = []
        
        def worker(query):
            embedding = get_cached_embedding(query)
            results.append(embedding)
        
        # Create 10 threads accessing same query
        threads = []
        query = "concurrent test"
        for _ in range(10):
            t = threading.Thread(target=worker, args=(query,))
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # All results should be identical (same cached value)
        assert len(results) == 10
        assert all(r == results[0] for r in results)


class TestCacheEdgeCases:
    """Test edge cases and error handling."""
    
    def setup_method(self):
        """Clear cache before each test."""
        clear_cache()
    
    def test_empty_string_query(self):
        """Should cache empty string queries."""
        query = ""
        
        embedding1 = get_cached_embedding(query)
        embedding2 = get_cached_embedding(query)
        
        assert embedding1 == embedding2
        assert cache_info().currsize >= 1
    
    def test_very_long_query(self):
        """Should cache very long queries."""
        query = "chest X-ray " * 100  # 1300+ characters
        
        embedding1 = get_cached_embedding(query)
        embedding2 = get_cached_embedding(query)
        
        assert embedding1 == embedding2
    
    def test_unicode_query(self):
        """Should handle Unicode characters in queries."""
        query = "chest X-ray with résumé café naïve"
        
        embedding1 = get_cached_embedding(query)
        embedding2 = get_cached_embedding(query)
        
        assert embedding1 == embedding2
    
    def test_special_characters_query(self):
        """Should handle special characters."""
        query = "chest X-ray: findings! (positive) - 50% opacity?"
        
        embedding1 = get_cached_embedding(query)
        embedding2 = get_cached_embedding(query)
        
        assert embedding1 == embedding2
    
    @patch('src.search.cache.get_embedder')
    def test_embedder_returns_empty_list(self, mock_get_embedder):
        """Should handle empty embedding from embedder."""
        mock_embedder = Mock()
        mock_embedder.embed_text.return_value = []
        mock_get_embedder.return_value = mock_embedder
        
        query = "test"
        result = get_cached_embedding(query)
        
        assert result == ()  # Empty tuple


# Fixtures
@pytest.fixture
def sample_queries():
    """Provide sample queries for testing."""
    return [
        "chest X-ray showing pneumonia",
        "bilateral lung infiltrates",
        "cardiomegaly with pleural effusion",
        "normal frontal chest radiograph",
        "pneumothorax on left side"
    ]


@pytest.fixture
def mock_embedder_1024():
    """Mock embedder returning 1024-dim vectors."""
    embedder = Mock()
    embedder.embed_text = lambda text: [float(hash(text) % 1000 + i) for i in range(1024)]
    return embedder


# Parametrized tests
@pytest.mark.parametrize("query", [
    "pneumonia",
    "chest X-ray",
    "bilateral infiltrates with effusion",
    "a" * 500,  # Long query
    "",  # Empty query
    "résumé café",  # Unicode
])
def test_cache_roundtrip(query):
    """Test cache roundtrip for various query types."""
    clear_cache()
    
    embedding1 = get_cached_embedding(query)
    embedding2 = get_cached_embedding(query)
    
    assert embedding1 == embedding2
    assert isinstance(embedding1, tuple)


@pytest.mark.parametrize("n_queries", [1, 10, 100, 500])
def test_cache_size_tracking(n_queries):
    """Test cache size tracking for different volumes."""
    clear_cache()
    
    for i in range(n_queries):
        get_cached_embedding(f"query_{i}")
    
    info = cache_info()
    assert info.currsize == n_queries
    assert info.misses == n_queries
