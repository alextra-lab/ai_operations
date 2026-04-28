"""
Unit tests for error response models and utilities.

Tests error response building, exception mapping, and OpenAI compatibility.
"""

from fastapi import status

from app.models.errors import ErrorDetail, ErrorResponse, build_error_response
from app.utils.error_handler import (
    create_error_json_response,
    create_error_stream_chunk,
    map_exception_to_error_response,
)
from app.utils.errors import (
    GatewayError,
    ModelNotFoundError,
    ProviderDisabledError,
    ProviderHTTPError,
    ProviderNotFoundError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)


class TestErrorDetail:
    """Test ErrorDetail Pydantic model."""

    def test_error_detail_creation(self):
        """Test creating ErrorDetail with all fields."""
        detail = ErrorDetail(
            message="Model not found",
            type="invalid_request_error",
            code="model_not_found",
            param="model",
        )

        assert detail.message == "Model not found"
        assert detail.type == "invalid_request_error"
        assert detail.code == "model_not_found"
        assert detail.param == "model"

    def test_error_detail_without_param(self):
        """Test creating ErrorDetail without optional param."""
        detail = ErrorDetail(
            message="Internal error",
            type="gateway_error",
            code="internal_error",
        )

        assert detail.message == "Internal error"
        assert detail.param is None


class TestErrorResponse:
    """Test ErrorResponse Pydantic model."""

    def test_error_response_structure(self):
        """Test error response has correct OpenAI structure."""
        error_resp = ErrorResponse(
            error=ErrorDetail(
                message="Test error",
                type="test_error",
                code="test_code",
            )
        )

        data = error_resp.to_dict()
        assert "error" in data
        assert data["error"]["message"] == "Test error"
        assert data["error"]["type"] == "test_error"
        assert data["error"]["code"] == "test_code"

    def test_from_exception_with_gateway_error(self):
        """Test building ErrorResponse from GatewayError."""
        exc = ModelNotFoundError("gpt-4")
        error_resp = ErrorResponse.from_exception(exc)

        assert error_resp.error.message == "Model 'gpt-4' not found in registry"
        assert error_resp.error.type == "model_not_found"

    def test_from_exception_with_override(self):
        """Test overriding error type and code."""
        exc = Exception("Generic error")
        error_resp = ErrorResponse.from_exception(
            exc,
            error_type="custom_error",
            error_code="custom_code",
        )

        assert error_resp.error.message == "Generic error"
        assert error_resp.error.type == "custom_error"
        assert error_resp.error.code == "custom_code"


class TestBuildErrorResponse:
    """Test build_error_response utility."""

    def test_build_basic_error(self):
        """Test building basic error response."""
        error_resp = build_error_response(
            message="Something went wrong",
            error_type="gateway_error",
            error_code="internal_error",
        )

        assert isinstance(error_resp, ErrorResponse)
        assert error_resp.error.message == "Something went wrong"
        assert error_resp.error.type == "gateway_error"
        assert error_resp.error.code == "internal_error"

    def test_build_error_with_param(self):
        """Test building error with parameter."""
        error_resp = build_error_response(
            message="Invalid model",
            error_type="invalid_request_error",
            error_code="model_not_found",
            param="model",
        )

        assert error_resp.error.param == "model"


class TestMapExceptionToErrorResponse:
    """Test exception mapping to error responses."""

    def test_map_model_not_found(self):
        """Test mapping ModelNotFoundError."""
        exc = ModelNotFoundError("gpt-4")
        error_resp, status_code = map_exception_to_error_response(exc)

        assert status_code == status.HTTP_404_NOT_FOUND
        assert error_resp.error.type == "invalid_request_error"
        assert error_resp.error.code == "model_not_found"
        assert "gpt-4" in error_resp.error.message

    def test_map_provider_not_found(self):
        """Test mapping ProviderNotFoundError."""
        exc = ProviderNotFoundError("openai")
        error_resp, status_code = map_exception_to_error_response(exc)

        assert status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert error_resp.error.type == "provider_error"
        assert error_resp.error.code == "provider_unavailable"

    def test_map_provider_disabled(self):
        """Test mapping ProviderDisabledError."""
        exc = ProviderDisabledError("mistral")
        error_resp, status_code = map_exception_to_error_response(exc)

        assert status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert error_resp.error.type == "provider_error"
        assert error_resp.error.code == "provider_unavailable"

    def test_map_provider_timeout(self):
        """Test mapping ProviderTimeoutError."""
        exc = ProviderTimeoutError("openai", 30.0)
        error_resp, status_code = map_exception_to_error_response(exc)

        assert status_code == status.HTTP_504_GATEWAY_TIMEOUT
        assert error_resp.error.type == "timeout_error"
        assert error_resp.error.code == "provider_timeout"

    def test_map_provider_rate_limit(self):
        """Test mapping ProviderRateLimitError."""
        exc = ProviderRateLimitError("openai", retry_after=60)
        error_resp, status_code = map_exception_to_error_response(exc)

        assert status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert error_resp.error.type == "rate_limit_error"
        assert error_resp.error.code == "rate_limit_exceeded"

    def test_map_provider_http_error(self):
        """Test mapping ProviderHTTPError."""
        exc = ProviderHTTPError("openai", 502, "Bad Gateway")
        error_resp, status_code = map_exception_to_error_response(exc)

        assert status_code == status.HTTP_502_BAD_GATEWAY
        assert error_resp.error.type == "provider_http_error"
        assert error_resp.error.code == "http_502"

    def test_map_generic_gateway_error(self):
        """Test mapping generic GatewayError."""
        exc = GatewayError("Something failed", "gateway_error")
        error_resp, status_code = map_exception_to_error_response(exc)

        assert status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert error_resp.error.type == "gateway_error"
        assert error_resp.error.code == "internal_error"
        # Should not leak internal details
        assert error_resp.error.message == "Internal server error"

    def test_map_unknown_exception(self):
        """Test mapping unknown exception."""
        exc = ValueError("Unexpected error")
        error_resp, status_code = map_exception_to_error_response(exc)

        assert status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert error_resp.error.type == "unexpected_error"
        assert error_resp.error.code == "internal_error"
        # Should not leak internal details
        assert error_resp.error.message == "Internal server error"


class TestCreateErrorJSONResponse:
    """Test JSON response creation."""

    def test_create_json_response_basic(self):
        """Test creating JSON response from exception."""
        exc = ModelNotFoundError("gpt-4")
        response = create_error_json_response(exc)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "error" in response.body.decode()

    def test_create_json_response_with_request_id(self):
        """Test creating JSON response with request ID."""
        exc = ModelNotFoundError("gpt-4")
        response = create_error_json_response(exc, request_id="req_123")

        assert response.headers["X-Request-ID"] == "req_123"


class TestCreateErrorStreamChunk:
    """Test SSE error chunk creation."""

    def test_create_stream_chunk_basic(self):
        """Test creating SSE error chunk."""
        exc = ModelNotFoundError("gpt-4")
        chunk = create_error_stream_chunk(exc)

        assert chunk.startswith("data: ")
        assert chunk.endswith("\n\n")
        assert "error" in chunk
        assert "model_not_found" in chunk

    def test_create_stream_chunk_structure(self):
        """Test SSE chunk has proper structure."""
        exc = ProviderTimeoutError("openai", 30.0)
        chunk = create_error_stream_chunk(exc)

        # Should be valid SSE format
        assert chunk.startswith("data: ")
        assert chunk.endswith("\n\n")

        # Should contain error details
        assert "timeout_error" in chunk
        assert "provider_timeout" in chunk


class TestOpenAICompatibility:
    """Test OpenAI API compatibility."""

    def test_error_structure_matches_openai(self):
        """Test error structure matches OpenAI format."""
        error_resp = build_error_response(
            message="Model not found",
            error_type="invalid_request_error",
            error_code="model_not_found",
        )

        data = error_resp.to_dict()

        # OpenAI structure: {"error": {"message": ..., "type": ..., "code": ...}}
        assert "error" in data
        assert "message" in data["error"]
        assert "type" in data["error"]
        assert "code" in data["error"]

    def test_optional_param_excluded_when_none(self):
        """Test that None param is excluded from output."""
        error_resp = build_error_response(
            message="Error",
            error_type="test",
            error_code="test",
            param=None,
        )

        data = error_resp.to_dict()
        # param should not be in output when None
        assert "param" not in data["error"]
