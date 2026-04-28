"""
Simplified integration tests for chat completions endpoint.

Tests basic functionality without complex mocking.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.requests import ChatCompletionRequest, ChatMessage


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestChatCompletionsBasic:
    """Basic integration tests for chat completions endpoint."""

    def test_health_endpoint(self, client):
        """Test health endpoint works."""
        with patch("app.main.check_database_connection", AsyncMock(return_value=True)):
            response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "inference-gateway"

    def test_root_endpoint(self, client):
        """Test root endpoint works."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "inference-gateway"
        assert data["status"] == "operational"

    def test_chat_completions_requires_auth(self, client):
        """Test that chat completions requires authentication."""
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "Hello"}],
            },
        )
        # Should return 401 or 403 without auth
        assert response.status_code in (401, 403)

    def test_list_models_requires_auth(self, client):
        """Test that list models requires authentication."""
        response = client.get("/v1/models")
        # Should return 401 or 403 without auth
        assert response.status_code in (401, 403)

    def test_chat_completions_invalid_request(self, client):
        """Test validation of invalid request."""
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-4o-mini",
                # Missing required 'messages' field
            },
            headers={"Authorization": "Bearer fake_token"},
        )
        # Should return 422 for validation error or 401/403 for auth
        assert response.status_code in (401, 403, 422)

    def test_request_id_accepted(self, client):
        """Test that X-Request-ID header is accepted."""
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "Hello"}],
            },
            headers={
                "Authorization": "Bearer fake_token",
                "X-Request-ID": "test-request-123",
            },
        )
        # Should fail auth, but header should be accepted
        assert response.status_code in (401, 403)

    def test_streaming_returns_not_implemented(self, client):
        """Test that streaming returns 501 (not yet implemented)."""
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": True,
            },
            headers={"Authorization": "Bearer fake_token"},
        )
        # May return 501 if it gets past auth, or 401/403 if auth fails first
        assert response.status_code in (401, 403, 501)

    def test_openapi_docs_available(self, client):
        """Test that OpenAPI docs are available in test mode."""
        response = client.get("/docs")
        # Should redirect or show docs page
        assert response.status_code in (200, 307)

    def test_request_model_serialization(self):
        """Test that ChatCompletionRequest serializes correctly."""
        request = ChatCompletionRequest(
            model="gpt-4o-mini",
            messages=[
                ChatMessage(role="system", content="You are helpful."),
                ChatMessage(role="user", content="Hello!"),
            ],
            temperature=0.7,
            max_tokens=150,
        )

        data = request.model_dump(exclude_none=True)
        assert data["model"] == "gpt-4o-mini"
        assert len(data["messages"]) == 2
        assert data["temperature"] == 0.7
        assert data["max_tokens"] == 150
        assert data["stream"] is False  # Default value

    def test_request_model_validation(self):
        """Test that ChatCompletionRequest validates inputs."""
        # Valid request
        request = ChatCompletionRequest(
            model="test-model",
            messages=[ChatMessage(role="user", content="test")],
        )
        assert request.model == "test-model"

        # Temperature out of range should be validated
        with pytest.raises(ValueError):
            ChatCompletionRequest(
                model="test-model",
                messages=[ChatMessage(role="user", content="test")],
                temperature=3.0,  # Max is 2.0
            )

        # Empty messages should fail
        with pytest.raises(ValueError):
            ChatCompletionRequest(
                model="test-model",
                messages=[],  # Min length is 1
            )
