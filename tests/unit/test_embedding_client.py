"""
Unit Tests for NVIDIAEmbeddingsClient

Tests NVIDIA NIM embeddings API client with mocked HTTP requests.
Validates retry logic, rate limiting, and batch processing.

Usage:
    pytest tests/unit/test_embedding_client.py -v
    pytest tests/unit/test_embedding_client.py::TestNVIDIAEmbeddingsClient::test_embed -v

Dependencies:
    pytest, unittest.mock
"""

import pytest
import sys
import time
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
import os

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from vectorization.embedding_client import NVIDIAEmbeddingsClient, RateLimitError


class TestNVIDIAEmbeddingsClient:
    """Test suite for NVIDIAEmbeddingsClient class."""

    @pytest.fixture
    def api_key(self):
        """Test API key."""
        return "nvapi-test-key-1234567890"

    @pytest.fixture
    def client(self, api_key):
        """Create a test client instance."""
        return NVIDIAEmbeddingsClient(
            api_key=api_key,
            model="nvidia/nv-embedqa-e5-v5",
            batch_size=50,
            requests_per_minute=60,
            max_retries=3
        )

    @pytest.fixture
    def mock_response(self):
        """Create a mock successful API response."""
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [
                {"embedding": [0.1] * 1024},
                {"embedding": [0.2] * 1024}
            ]
        }
        return mock_resp

    def test_initialization_with_api_key(self, api_key):
        """Test client initialization with explicit API key."""
        client = NVIDIAEmbeddingsClient(api_key=api_key)

        assert client.api_key == api_key
        assert client.model == "nvidia/nv-embedqa-e5-v5"
        assert client.batch_size == 50
        assert client.requests_per_minute == 60
        assert client.max_retries == 3
        assert client.min_interval == 1.0  # 60/60 = 1 second

    def test_initialization_from_env(self, monkeypatch):
        """Test client initialization from environment variable."""
        test_api_key = "nvapi-env-key"
        monkeypatch.setenv("NVIDIA_API_KEY", test_api_key)

        client = NVIDIAEmbeddingsClient()

        assert client.api_key == test_api_key

    def test_initialization_missing_api_key(self, monkeypatch):
        """Test initialization fails without API key."""
        monkeypatch.delenv("NVIDIA_API_KEY", raising=False)

        with pytest.raises(ValueError, match="NVIDIA API key required"):
            NVIDIAEmbeddingsClient()

    def test_rate_limiting_interval(self):
        """Test rate limiting calculates correct interval."""
        # 60 requests per minute = 1 second interval
        client1 = NVIDIAEmbeddingsClient(
            api_key="test",
            requests_per_minute=60
        )
        assert client1.min_interval == 1.0

        # 30 requests per minute = 2 second interval
        client2 = NVIDIAEmbeddingsClient(
            api_key="test",
            requests_per_minute=30
        )
        assert client2.min_interval == 2.0

    @patch('vectorization.embedding_client.time.sleep')
    def test_wait_for_rate_limit(self, mock_sleep, client):
        """Test rate limiting waits when necessary."""
        # Set last request to recent time
        client.last_request_time = time.time() - 0.5  # 0.5 seconds ago

        client._wait_for_rate_limit()

        # Should have waited ~0.5 seconds (1.0 - 0.5)
        mock_sleep.assert_called_once()
        wait_time = mock_sleep.call_args[0][0]
        assert 0.4 < wait_time < 0.6

    @patch('vectorization.embedding_client.time.sleep')
    def test_no_wait_when_interval_passed(self, mock_sleep, client):
        """Test no waiting when rate limit interval has passed."""
        # Set last request to long ago
        client.last_request_time = time.time() - 2.0  # 2 seconds ago

        client._wait_for_rate_limit()

        # Should not have slept
        mock_sleep.assert_not_called()

    @patch('vectorization.embedding_client.requests.Session.post')
    @patch('vectorization.embedding_client.time.sleep')
    def test_make_request_success(self, mock_sleep, mock_post, client, mock_response):
        """Test successful API request."""
        mock_post.return_value = mock_response

        texts = ["Test text 1", "Test text 2"]
        embeddings = client._make_request(texts)

        assert len(embeddings) == 2
        assert len(embeddings[0]) == 1024
        assert embeddings[0] == [0.1] * 1024
        assert embeddings[1] == [0.2] * 1024

        # Verify request was made correctly
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["input"] == texts
        assert call_kwargs["json"]["model"] == "nvidia/nv-embedqa-e5-v5"
        assert call_kwargs["timeout"] == 30

    @patch('vectorization.embedding_client.requests.Session.post')
    @patch('vectorization.embedding_client.time.sleep')
    def test_make_request_rate_limit_429(self, mock_sleep, mock_post, client):
        """Test handling of 429 rate limit response."""
        # First call returns 429, second call succeeds
        rate_limit_response = Mock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {"Retry-After": "5"}

        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "data": [{"embedding": [0.1] * 1024}]
        }

        mock_post.side_effect = [rate_limit_response, success_response]

        texts = ["Test text"]
        embeddings = client._make_request(texts)

        # Should have slept for retry-after duration
        assert mock_sleep.call_count >= 1
        # First sleep is from rate limit response
        first_sleep = [c for c in mock_sleep.call_args_list if c[0][0] == 5]
        assert len(first_sleep) == 1

        # Should have retried and succeeded
        assert len(embeddings) == 1
        assert mock_post.call_count == 2

    @patch('vectorization.embedding_client.requests.Session.post')
    @patch('vectorization.embedding_client.time.sleep')
    def test_make_request_http_error(self, mock_sleep, mock_post, client):
        """Test handling of HTTP errors."""
        import requests

        error_response = Mock()
        error_response.status_code = 500
        error_response.text = "Internal Server Error"
        error_response.raise_for_status.side_effect = requests.exceptions.HTTPError()

        mock_post.return_value = error_response

        texts = ["Test text"]

        with pytest.raises(requests.exceptions.HTTPError):
            client._make_request(texts)

    @patch('vectorization.embedding_client.requests.Session.post')
    @patch('vectorization.embedding_client.time.sleep')
    def test_make_request_connection_error_retry(self, mock_sleep, mock_post, client):
        """Test retry logic for connection errors."""
        import requests

        # Simulate connection error then success
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "data": [{"embedding": [0.1] * 1024}]
        }

        mock_post.side_effect = [
            requests.exceptions.ConnectionError("Connection failed"),
            success_response
        ]

        texts = ["Test text"]
        embeddings = client._make_request(texts)

        # Should have retried and succeeded
        assert len(embeddings) == 1
        assert mock_post.call_count == 2

    @patch('vectorization.embedding_client.requests.Session.post')
    @patch('vectorization.embedding_client.time.sleep')
    def test_embed_single_text(self, mock_sleep, mock_post, client):
        """Test embedding a single text."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"embedding": [0.123] * 1024}]
        }
        mock_post.return_value = mock_response

        text = "Patient presents with acute symptoms"
        embedding = client.embed(text)

        assert len(embedding) == 1024
        assert embedding == [0.123] * 1024

        # Verify single text was sent
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["input"] == [text]

    @patch('vectorization.embedding_client.requests.Session.post')
    @patch('vectorization.embedding_client.time.sleep')
    def test_embed_batch(self, mock_sleep, mock_post, client):
        """Test batch embedding."""
        # Mock response for batch
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"embedding": [0.1 + i * 0.01] * 1024}
                for i in range(5)
            ]
        }
        mock_post.return_value = mock_response

        texts = [f"Text {i}" for i in range(5)]
        embeddings = client.embed_batch(texts, show_progress=False)

        assert len(embeddings) == 5
        assert all(len(emb) == 1024 for emb in embeddings)

        # Verify batch was sent in single request
        mock_post.assert_called_once()

    @patch('vectorization.embedding_client.requests.Session.post')
    @patch('vectorization.embedding_client.time.sleep')
    def test_embed_batch_multiple_batches(self, mock_sleep, mock_post, client):
        """Test batch embedding splits into multiple requests."""
        client.batch_size = 3  # Small batch size

        # Mock responses for multiple batches
        def mock_response_factory(request_data):
            response = Mock()
            response.status_code = 200
            num_texts = len(request_data["json"]["input"])
            response.json.return_value = {
                "data": [{"embedding": [0.1] * 1024} for _ in range(num_texts)]
            }
            return response

        mock_post.side_effect = lambda *args, **kwargs: mock_response_factory(kwargs)

        # 7 texts with batch size 3 = 3 batches (3, 3, 1)
        texts = [f"Text {i}" for i in range(7)]
        embeddings = client.embed_batch(texts, show_progress=False)

        assert len(embeddings) == 7
        assert mock_post.call_count == 3  # 3 batches

        # Verify batch sizes
        batch_sizes = [
            len(call[1]["json"]["input"])
            for call in mock_post.call_args_list
        ]
        assert batch_sizes == [3, 3, 1]

    @patch('vectorization.embedding_client.requests.Session.post')
    @patch('vectorization.embedding_client.time.sleep')
    def test_embed_batch_failure_propagates(self, mock_sleep, mock_post, client):
        """Test batch embedding propagates failures."""
        import requests

        # First batch succeeds, second fails
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "data": [{"embedding": [0.1] * 1024} for _ in range(3)]
        }

        error_response = Mock()
        error_response.status_code = 500
        error_response.raise_for_status.side_effect = requests.exceptions.HTTPError()

        mock_post.side_effect = [success_response, error_response]

        client.batch_size = 3
        texts = [f"Text {i}" for i in range(6)]  # 2 batches

        with pytest.raises(requests.exceptions.HTTPError):
            client.embed_batch(texts, show_progress=False)

    def test_get_embedding_dimension(self, client):
        """Test getting embedding dimension."""
        assert client.get_embedding_dimension() == 1024

    def test_context_manager(self, api_key):
        """Test using client as context manager."""
        with patch('vectorization.embedding_client.requests.Session') as mock_session:
            mock_session_instance = MagicMock()
            mock_session.return_value = mock_session_instance

            with NVIDIAEmbeddingsClient(api_key=api_key) as client:
                assert client is not None

            # Verify session was closed
            mock_session_instance.close.assert_called_once()

    @patch('vectorization.embedding_client.requests.Session.post')
    @patch('vectorization.embedding_client.time.sleep')
    def test_session_reuse(self, mock_sleep, mock_post, client):
        """Test that session is reused across requests."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"embedding": [0.1] * 1024}]
        }
        mock_post.return_value = mock_response

        # Make multiple requests
        client.embed("Text 1")
        client.embed("Text 2")

        # Both should use same session
        assert mock_post.call_count == 2
        # Session should have consistent headers
        assert client.session.headers["Authorization"] == f"Bearer {client.api_key}"


class TestNVIDIAEmbeddingsClientIntegration:
    """
    Integration-style tests for end-to-end workflows.
    """

    @pytest.fixture
    def api_key(self):
        return "nvapi-test-key"

    @patch('vectorization.embedding_client.requests.Session.post')
    @patch('vectorization.embedding_client.time.sleep')
    def test_full_batch_workflow(self, mock_sleep, mock_post, api_key):
        """Test complete workflow: init, batch embed, close."""
        # Mock successful responses
        def create_response(num_texts):
            response = Mock()
            response.status_code = 200
            response.json.return_value = {
                "data": [{"embedding": [0.1] * 1024} for _ in range(num_texts)]
            }
            return response

        mock_post.side_effect = [
            create_response(3),
            create_response(2)
        ]

        with NVIDIAEmbeddingsClient(api_key=api_key, batch_size=3) as client:
            texts = [f"Clinical note {i}" for i in range(5)]
            embeddings = client.embed_batch(texts, show_progress=False)

            assert len(embeddings) == 5
            assert all(len(emb) == 1024 for emb in embeddings)

        # Session should be closed
        assert mock_post.call_count == 2

    @patch('vectorization.embedding_client.requests.Session.post')
    @patch('vectorization.embedding_client.time.sleep')
    def test_rate_limiting_in_batch(self, mock_sleep, mock_post, api_key):
        """Test that rate limiting is applied across batch requests."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"embedding": [0.1] * 1024}]
        }
        mock_post.return_value = mock_response

        client = NVIDIAEmbeddingsClient(
            api_key=api_key,
            batch_size=1,
            requests_per_minute=60  # 1 second interval
        )

        # Embed 3 texts (3 requests with batch_size=1)
        texts = ["Text 1", "Text 2", "Text 3"]
        embeddings = client.embed_batch(texts, show_progress=False)

        assert len(embeddings) == 3

        # Should have made 3 requests with rate limiting
        assert mock_post.call_count == 3

        # Check that sleep was called for rate limiting
        # (may be called for retries too, so just verify it was called)
        assert mock_sleep.called


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
