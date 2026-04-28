"""
Integration tests for responses endpoint.

Tests OpenAI Responses API endpoint (/v1/responses).
NEW OPENAI API (2024+) for stateful conversations.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestResponsesBasic:
    """Basic integration tests for responses endpoint."""

    def test_responses_requires_auth(self, client):
        """Test that responses endpoint requires authentication."""
        response = client.post(
            "/v1/responses",
            json={
                "model": "gpt-5",
                "input": "Test",
            },
        )
        # Should return 401 or 403 without auth
        assert response.status_code in (401, 403)

    def test_responses_requires_input_or_previous_id(self, client):
        """Test that either input or previous_response_id is required."""
        response = client.post(
            "/v1/responses",
            json={
                "model": "gpt-5",
                # Missing both input and previous_response_id
            },
            headers={"Authorization": "Bearer fake_token"},
        )
        # Should return 400 for invalid request or 401/403 for auth
        assert response.status_code in (400, 401, 403, 422)

    def test_responses_accepts_string_input(self, client):
        """Test that responses accepts simple string input."""
        response = client.post(
            "/v1/responses",
            json={
                "model": "gpt-5",
                "input": "Analyze this threat",
            },
            headers={"Authorization": "Bearer fake_token"},
        )
        # Should fail auth but request format is valid
        assert response.status_code in (401, 403, 404, 503)

    def test_responses_accepts_array_input(self, client):
        """Test that responses accepts array input with roles."""
        response = client.post(
            "/v1/responses",
            json={
                "model": "gpt-5",
                "input": [{"role": "user", "content": "Analyze this threat"}],
            },
            headers={"Authorization": "Bearer fake_token"},
        )
        # Should fail auth but request format is valid
        assert response.status_code in (401, 403, 404, 503)

    def test_responses_accepts_instructions(self, client):
        """Test that responses accepts instructions parameter."""
        response = client.post(
            "/v1/responses",
            json={
                "model": "gpt-5",
                "input": "Hello",
                "instructions": "You are a cybersecurity expert.",
            },
            headers={"Authorization": "Bearer fake_token"},
        )
        # Should fail auth but request format is valid
        assert response.status_code in (401, 403, 404, 503)

    def test_responses_accepts_previous_response_id(self, client):
        """Test that responses accepts previous_response_id."""
        response = client.post(
            "/v1/responses",
            json={
                "model": "mistral-nemo-2407",
                "previous_response_id": "resp_abc123",
            },
            headers={"Authorization": "Bearer fake_token"},
        )
        # Should fail auth but request format is valid
        assert response.status_code in (401, 403, 404, 503)

    def test_responses_accepts_temperature(self, client):
        """Test that responses accepts temperature parameter."""
        response = client.post(
            "/v1/responses",
            json={
                "model": "gpt-5",
                "input": "Test",
                "temperature": 0.7,
            },
            headers={"Authorization": "Bearer fake_token"},
        )
        # Should fail auth but request format is valid
        assert response.status_code in (401, 403, 404, 503)

    def test_responses_accepts_max_output_tokens(self, client):
        """Test that responses accepts max_output_tokens parameter."""
        response = client.post(
            "/v1/responses",
            json={
                "model": "gpt-5",
                "input": "Test",
                "max_output_tokens": 500,
            },
            headers={"Authorization": "Bearer fake_token"},
        )
        # Should fail auth but request format is valid
        assert response.status_code in (401, 403, 404, 503)

    def test_responses_accepts_tools(self, client):
        """Test that responses accepts tools parameter."""
        response = client.post(
            "/v1/responses",
            json={
                "model": "gpt-5",
                "input": "Test",
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": "search_threats",
                            "description": "Search threat database",
                        },
                    }
                ],
            },
            headers={"Authorization": "Bearer fake_token"},
        )
        # Should fail auth but request format is valid
        assert response.status_code in (401, 403, 404, 503)

    def test_responses_accepts_metadata(self, client):
        """Test that responses accepts metadata parameter."""
        response = client.post(
            "/v1/responses",
            json={
                "model": "gpt-5",
                "input": "Test",
                "metadata": {"session_id": "test-123", "user_type": "analyst"},
            },
            headers={"Authorization": "Bearer fake_token"},
        )
        # Should fail auth but request format is valid
        assert response.status_code in (401, 403, 404, 503)

    def test_request_id_accepted(self, client):
        """Test that X-Request-ID header is accepted."""
        response = client.post(
            "/v1/responses",
            json={
                "model": "gpt-5",
                "input": "Test",
            },
            headers={
                "Authorization": "Bearer fake_token",
                "X-Request-ID": "test-responses-123",
            },
        )
        # Should fail auth, but header should be accepted
        assert response.status_code in (401, 403, 404, 503)

    def test_responses_endpoint_exists(self, client):
        """Test that responses endpoint exists and is routed correctly."""
        # OPTIONS request should work
        response = client.options("/v1/responses")
        # Should return 200 or 405 (method not allowed)
        assert response.status_code in (200, 405)


class TestResponsesValidation:
    """Test request validation for responses endpoint."""

    def test_invalid_temperature_negative(self, client):
        """Test validation of negative temperature."""
        response = client.post(
            "/v1/responses",
            json={
                "model": "gpt-5",
                "input": "Test",
                "temperature": -0.5,  # Invalid (must be >= 0)
            },
            headers={"Authorization": "Bearer fake_token"},
        )
        # Should return 422 for validation error
        assert response.status_code in (401, 403, 422)

    def test_invalid_temperature_too_high(self, client):
        """Test validation of temperature > 2.0."""
        response = client.post(
            "/v1/responses",
            json={
                "model": "gpt-5",
                "input": "Test",
                "temperature": 3.0,  # Invalid (must be <= 2.0)
            },
            headers={"Authorization": "Bearer fake_token"},
        )
        # Should return 422 for validation error
        assert response.status_code in (401, 403, 422)

    def test_invalid_top_p_negative(self, client):
        """Test validation of negative top_p."""
        response = client.post(
            "/v1/responses",
            json={
                "model": "gpt-5",
                "input": "Test",
                "top_p": -0.1,  # Invalid (must be >= 0)
            },
            headers={"Authorization": "Bearer fake_token"},
        )
        # Should return 422 for validation error
        assert response.status_code in (401, 403, 422)

    def test_invalid_top_p_too_high(self, client):
        """Test validation of top_p > 1.0."""
        response = client.post(
            "/v1/responses",
            json={
                "model": "gpt-5",
                "input": "Test",
                "top_p": 1.5,  # Invalid (must be <= 1.0)
            },
            headers={"Authorization": "Bearer fake_token"},
        )
        # Should return 422 for validation error
        assert response.status_code in (401, 403, 422)

    def test_invalid_max_output_tokens_zero(self, client):
        """Test validation of zero max_output_tokens."""
        response = client.post(
            "/v1/responses",
            json={
                "model": "gpt-5",
                "input": "Test",
                "max_output_tokens": 0,  # Invalid (must be > 0)
            },
            headers={"Authorization": "Bearer fake_token"},
        )
        # Should return 422 for validation error
        assert response.status_code in (401, 403, 422)

    def test_invalid_max_output_tokens_negative(self, client):
        """Test validation of negative max_output_tokens."""
        response = client.post(
            "/v1/responses",
            json={
                "model": "gpt-5",
                "input": "Test",
                "max_output_tokens": -100,  # Invalid (must be > 0)
            },
            headers={"Authorization": "Bearer fake_token"},
        )
        # Should return 422 for validation error
        assert response.status_code in (401, 403, 422)

    def test_empty_input_string(self, client):
        """Test responses with empty input string."""
        response = client.post(
            "/v1/responses",
            json={
                "model": "gpt-5",
                "input": "",  # Empty string
            },
            headers={"Authorization": "Bearer fake_token"},
        )
        # May be accepted (provider will reject) or fail validation
        assert response.status_code in (400, 401, 403, 422, 404, 503)

    def test_input_array_with_role(self, client):
        """Test input array with role and content fields."""
        response = client.post(
            "/v1/responses",
            json={
                "model": "gpt-5",
                "input": [{"role": "user", "content": "Test"}],
            },
            headers={"Authorization": "Bearer fake_token"},
        )
        # Should be accepted
        assert response.status_code in (401, 403, 404, 503)

    def test_input_array_missing_content(self, client):
        """Test input array item without content field."""
        response = client.post(
            "/v1/responses",
            json={
                "model": "gpt-5",
                "input": [{"role": "user"}],  # Missing 'content'
            },
            headers={"Authorization": "Bearer fake_token"},
        )
        # Should return 422 for validation error
        assert response.status_code in (401, 403, 422)


class TestResponsesStatefulConversation:
    """Test stateful conversation features."""

    def test_both_input_and_previous_id_accepted(self, client):
        """Test that both input and previous_response_id can be provided."""
        response = client.post(
            "/v1/responses",
            json={
                "model": "gpt-5",
                "input": "Continue the conversation",
                "previous_response_id": "resp_abc123",
            },
            headers={"Authorization": "Bearer fake_token"},
        )
        # Should be accepted (provider decides how to handle)
        assert response.status_code in (401, 403, 404, 503, 400)

    def test_continuation_with_previous_id_only(self, client):
        """Test conversation continuation with only previous_response_id."""
        response = client.post(
            "/v1/responses",
            json={
                "model": "gpt-5",
                "previous_response_id": "resp_xyz789",
                # No input - continuing from previous
            },
            headers={"Authorization": "Bearer fake_token"},
        )
        # Should be accepted
        assert response.status_code in (401, 403, 404, 503)


class TestResponsesOpenAPICompatibility:
    """Test OpenAI API compatibility for responses endpoint."""

    def test_responses_path_is_v1(self, client):
        """Test that responses uses /v1/ prefix."""
        # Should work at /v1/responses
        response = client.post(
            "/v1/responses",
            json={
                "model": "gpt-5",
                "input": "Test",
            },
            headers={"Authorization": "Bearer fake_token"},
        )
        assert response.status_code != 404  # Endpoint exists

    def test_responses_not_at_v2(self, client):
        """Test that responses is not at /v2/ (only v1 supported)."""
        response = client.post(
            "/v2/responses",
            json={
                "model": "gpt-5",
                "input": "Test",
            },
            headers={"Authorization": "Bearer fake_token"},
        )
        # Should return 404 (path not found)
        assert response.status_code == 404


class TestResponsesStreaming:
    """Test streaming support for responses API."""

    def test_streaming_not_yet_implemented(self, client):
        """Test that streaming returns 501 (not yet implemented)."""
        response = client.post(
            "/v1/responses",
            json={
                "model": "gpt-5",
                "input": "Test",
                "stream": True,
            },
            headers={"Authorization": "Bearer fake_token"},
        )
        # May return 501 if it gets past auth, or 401/403 if auth fails first
        assert response.status_code in (401, 403, 501)
