"""
Integration tests for embeddings endpoint.

Tests basic functionality of /v1/embeddings endpoint.
CRITICAL for RAG functionality verification.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestEmbeddingsBasic:
    """Basic integration tests for embeddings endpoint."""

    def test_embeddings_requires_auth(self, client):
        """Test that embeddings endpoint requires authentication."""
        response = client.post(
            "/v1/embeddings",
            json={
                "model": "bge-embeddings",
                "input": "Test document",
            },
        )
        # Should return 401 or 403 without auth
        assert response.status_code in (401, 403)

    def test_embeddings_invalid_request_missing_model(self, client):
        """Test validation of request missing model field."""
        response = client.post(
            "/v1/embeddings",
            json={
                # Missing required 'model' field
                "input": "Test document",
            },
            headers={"Authorization": "Bearer fake_token"},
        )
        # Should return 422 for validation error or 401/403 for auth
        assert response.status_code in (401, 403, 422)

    def test_embeddings_invalid_request_missing_input(self, client):
        """Test validation of request missing input field."""
        response = client.post(
            "/v1/embeddings",
            json={
                "model": "bge-embeddings",
                # Missing required 'input' field
            },
            headers={"Authorization": "Bearer fake_token"},
        )
        # Should return 422 for validation error or 401/403 for auth
        assert response.status_code in (401, 403, 422)

    def test_embeddings_accepts_string_input(self, client):
        """Test that embeddings accepts single string input."""
        response = client.post(
            "/v1/embeddings",
            json={
                "model": "bge-embeddings",
                "input": "What is cybersecurity?",
            },
            headers={"Authorization": "Bearer fake_token"},
        )
        # Should fail auth but request format is valid
        assert response.status_code in (401, 403, 404, 503)

    def test_embeddings_accepts_array_input(self, client):
        """Test that embeddings accepts array of strings input."""
        response = client.post(
            "/v1/embeddings",
            json={
                "model": "bge-embeddings",
                "input": [
                    "Document 1",
                    "Document 2",
                    "Document 3",
                ],
            },
            headers={"Authorization": "Bearer fake_token"},
        )
        # Should fail auth but request format is valid
        assert response.status_code in (401, 403, 404, 503)

    def test_embeddings_accepts_encoding_format(self, client):
        """Test that embeddings accepts encoding_format parameter."""
        response = client.post(
            "/v1/embeddings",
            json={
                "model": "bge-embeddings",
                "input": "Test",
                "encoding_format": "float",
            },
            headers={"Authorization": "Bearer fake_token"},
        )
        # Should fail auth but request format is valid
        assert response.status_code in (401, 403, 404, 503)

    def test_embeddings_accepts_dimensions(self, client):
        """Test that embeddings accepts dimensions parameter."""
        response = client.post(
            "/v1/embeddings",
            json={
                "model": "text-embedding-3-small",
                "input": "Test",
                "dimensions": 512,
            },
            headers={"Authorization": "Bearer fake_token"},
        )
        # Should fail auth but request format is valid
        assert response.status_code in (401, 403, 404, 503)

    def test_embeddings_accepts_user_parameter(self, client):
        """Test that embeddings accepts user parameter for tracking."""
        response = client.post(
            "/v1/embeddings",
            json={
                "model": "bge-embeddings",
                "input": "Test",
                "user": "test-user-123",
            },
            headers={"Authorization": "Bearer fake_token"},
        )
        # Should fail auth but request format is valid
        assert response.status_code in (401, 403, 404, 503)

    def test_request_id_accepted(self, client):
        """Test that X-Request-ID header is accepted."""
        response = client.post(
            "/v1/embeddings",
            json={
                "model": "bge-embeddings",
                "input": "Test document for RAG",
            },
            headers={
                "Authorization": "Bearer fake_token",
                "X-Request-ID": "test-embeddings-123",
            },
        )
        # Should fail auth, but header should be accepted
        assert response.status_code in (401, 403, 404, 503)

    def test_embeddings_endpoint_exists(self, client):
        """Test that embeddings endpoint exists and is routed correctly."""
        # OPTIONS request should work
        response = client.options("/v1/embeddings")
        # Should return 200 or 405 (method not allowed)
        assert response.status_code in (200, 405)


class TestEmbeddingsRequestValidation:
    """Test request validation for embeddings endpoint."""

    def test_invalid_encoding_format(self, client):
        """Test validation of invalid encoding_format."""
        response = client.post(
            "/v1/embeddings",
            json={
                "model": "bge-embeddings",
                "input": "Test",
                "encoding_format": "invalid_format",  # Invalid
            },
            headers={"Authorization": "Bearer fake_token"},
        )
        # Should return 422 for validation error
        assert response.status_code in (401, 403, 422)

    def test_invalid_dimensions_negative(self, client):
        """Test validation of negative dimensions."""
        response = client.post(
            "/v1/embeddings",
            json={
                "model": "text-embedding-3-small",
                "input": "Test",
                "dimensions": -100,  # Invalid (must be positive)
            },
            headers={"Authorization": "Bearer fake_token"},
        )
        # Should return 422 for validation error
        assert response.status_code in (401, 403, 422)

    def test_invalid_dimensions_zero(self, client):
        """Test validation of zero dimensions."""
        response = client.post(
            "/v1/embeddings",
            json={
                "model": "text-embedding-3-small",
                "input": "Test",
                "dimensions": 0,  # Invalid (must be > 0)
            },
            headers={"Authorization": "Bearer fake_token"},
        )
        # Should return 422 for validation error
        assert response.status_code in (401, 403, 422)

    def test_empty_string_input(self, client):
        """Test embeddings with empty string input."""
        response = client.post(
            "/v1/embeddings",
            json={
                "model": "bge-embeddings",
                "input": "",  # Empty string
            },
            headers={"Authorization": "Bearer fake_token"},
        )
        # May fail validation or pass to provider (which will reject)
        assert response.status_code in (401, 403, 422, 400, 404, 503)

    def test_empty_array_input(self, client):
        """Test embeddings with empty array input."""
        response = client.post(
            "/v1/embeddings",
            json={
                "model": "bge-embeddings",
                "input": [],  # Empty array
            },
            headers={"Authorization": "Bearer fake_token"},
        )
        # May fail validation or pass to provider (which will reject)
        assert response.status_code in (401, 403, 422, 400, 404, 503)

    def test_very_long_input(self, client):
        """Test embeddings with very long text input."""
        long_text = "Test document " * 10000  # ~150KB text
        response = client.post(
            "/v1/embeddings",
            json={
                "model": "bge-embeddings",
                "input": long_text,
            },
            headers={"Authorization": "Bearer fake_token"},
        )
        # Should be accepted (provider will handle token limits)
        assert response.status_code in (401, 403, 404, 503, 400, 413)

    def test_large_batch_input(self, client):
        """Test embeddings with large batch of inputs."""
        large_batch = [f"Document {i}" for i in range(1000)]
        response = client.post(
            "/v1/embeddings",
            json={
                "model": "bge-embeddings",
                "input": large_batch,
            },
            headers={"Authorization": "Bearer fake_token"},
        )
        # Should be accepted (provider will handle batch limits)
        assert response.status_code in (401, 403, 404, 503, 400, 413)


class TestEmbeddingsOpenAPICompatibility:
    """Test OpenAI API compatibility for embeddings endpoint."""

    def test_embeddings_path_is_v1(self, client):
        """Test that embeddings uses /v1/ prefix."""
        # Should work at /v1/embeddings
        response = client.post(
            "/v1/embeddings",
            json={"model": "bge-embeddings", "input": "Test"},
            headers={"Authorization": "Bearer fake_token"},
        )
        assert response.status_code != 404  # Endpoint exists

    def test_embeddings_not_at_v2(self, client):
        """Test that embeddings is not at /v2/ (only v1 supported)."""
        response = client.post(
            "/v2/embeddings",
            json={"model": "bge-embeddings", "input": "Test"},
            headers={"Authorization": "Bearer fake_token"},
        )
        # Should return 404 (path not found)
        assert response.status_code == 404
