"""
Unit tests for responses router endpoints.

Tests OpenAI Responses API endpoint with various scenarios.

P5-A15: Added comprehensive unit tests for async responses router.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.routers.responses import create_response
from app.utils.errors import (
    GatewayError,
    ModelNotFoundError,
    ProviderDisabledError,
    ProviderHTTPError,
    ProviderNotFoundError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)


@pytest.fixture
def mock_token():
    """Mock JWT token payload."""
    token = MagicMock()
    token.sub = "test-user"
    token.user_id = "test-user-uuid"
    token.role = "user"
    return token


@pytest.fixture
def response_request():
    """Sample response request with input."""
    from app.models.response_request import ResponseRequest

    return ResponseRequest(
        model="gpt-4o",
        input="Tell me a joke",
        stream=False,
    )


@pytest.fixture
def response_request_with_previous():
    """Sample response request with previous response ID."""
    from app.models.response_request import ResponseRequest

    return ResponseRequest(
        model="gpt-4o",
        previous_response_id="resp_12345",
        stream=False,
    )


@pytest.fixture
def streaming_response_request():
    """Sample streaming response request."""
    from app.models.response_request import ResponseRequest

    return ResponseRequest(
        model="gpt-4o",
        input="Tell me a joke",
        stream=True,
    )


@pytest.fixture
def mock_provider_config():
    """Mock provider configuration."""
    from app.providers.base import ProviderConfig

    return ProviderConfig(
        id="12345678-1234-1234-1234-123456789abc",
        name="test-provider",
        provider_type="openai_compatible",
        base_url="https://api.test.com/v1",
        api_key="test-key",
        is_enabled=True,
        priority=10,
    )


@pytest.mark.asyncio
class TestCreateResponse:
    """Test create_response endpoint."""

    async def test_response_success(self, mock_token, response_request, mock_provider_config):
        """Test successful response creation."""
        mock_response = {
            "id": "resp_12345",
            "object": "response",
            "created_at": 1234567890,
            "model": "gpt-4o",
            "output": [
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "text", "text": "Why did the chicken..."}],
                }
            ],
            "usage": {
                "input_tokens": 10,
                "output_tokens": 20,
                "total_tokens": 30,
            },
        }

        with patch("app.routers.responses.simple_router") as mock_router:
            mock_router.route = AsyncMock(return_value="test-provider")

            with patch("app.routers.responses.provider_manager") as mock_pm:
                mock_pm.get_provider = AsyncMock(return_value=mock_provider_config)

                with patch("app.routers.responses.ProviderFactory") as mock_factory:
                    mock_provider = AsyncMock()
                    mock_provider.create_response = AsyncMock(return_value=mock_response)
                    mock_provider.__aenter__ = AsyncMock(return_value=mock_provider)
                    mock_provider.__aexit__ = AsyncMock(return_value=None)
                    mock_factory.create_provider.return_value = mock_provider

                    response = await create_response(
                        request=response_request,
                        token=mock_token,
                        x_request_id="test-request-id",
                    )

        assert response.status_code == 200
        body = response.body.decode()
        assert "resp_12345" in body

    async def test_response_with_previous_id(
        self, mock_token, response_request_with_previous, mock_provider_config
    ):
        """Test response with previous response ID (continuation)."""
        mock_response = {
            "id": "resp_67890",
            "object": "response",
            "created_at": 1234567890,
            "model": "gpt-4o",
            "previous_response_id": "resp_12345",
            "output": [
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "text", "text": "Continued response"}],
                }
            ],
        }

        with patch("app.routers.responses.simple_router") as mock_router:
            mock_router.route = AsyncMock(return_value="test-provider")

            with patch("app.routers.responses.provider_manager") as mock_pm:
                mock_pm.get_provider = AsyncMock(return_value=mock_provider_config)

                with patch("app.routers.responses.ProviderFactory") as mock_factory:
                    mock_provider = AsyncMock()
                    mock_provider.create_response = AsyncMock(return_value=mock_response)
                    mock_provider.__aenter__ = AsyncMock(return_value=mock_provider)
                    mock_provider.__aexit__ = AsyncMock(return_value=None)
                    mock_factory.create_provider.return_value = mock_provider

                    response = await create_response(
                        request=response_request_with_previous,
                        token=mock_token,
                        x_request_id="test-request-id",
                    )

        assert response.status_code == 200

    async def test_response_missing_input_and_previous(self, mock_token):
        """Test response fails when both input and previous_response_id missing."""
        from app.models.response_request import ResponseRequest

        invalid_request = ResponseRequest(
            model="gpt-4o",
            input=None,
            previous_response_id=None,
            stream=False,
        )

        with pytest.raises(HTTPException) as exc_info:
            await create_response(
                request=invalid_request,
                token=mock_token,
                x_request_id="test-request-id",
            )

        assert exc_info.value.status_code == 400

    async def test_response_streaming_not_implemented(
        self, mock_token, streaming_response_request, mock_provider_config
    ):
        """Test streaming returns 501 Not Implemented."""
        with patch("app.routers.responses.simple_router") as mock_router:
            mock_router.route = AsyncMock(return_value="test-provider")

            with patch("app.routers.responses.provider_manager") as mock_pm:
                mock_pm.get_provider = AsyncMock(return_value=mock_provider_config)

                with patch("app.routers.responses.ProviderFactory") as mock_factory:
                    mock_provider = AsyncMock()
                    mock_provider.__aenter__ = AsyncMock(return_value=mock_provider)
                    mock_provider.__aexit__ = AsyncMock(return_value=None)
                    mock_factory.create_provider.return_value = mock_provider

                    with pytest.raises(HTTPException) as exc_info:
                        await create_response(
                            request=streaming_response_request,
                            token=mock_token,
                            x_request_id="test-request-id",
                        )

                    assert exc_info.value.status_code == 501

    async def test_response_model_not_found(self, mock_token, response_request):
        """Test response with unknown model."""
        with patch("app.routers.responses.simple_router") as mock_router:
            mock_router.route = AsyncMock(side_effect=ModelNotFoundError("unknown-model"))

            with pytest.raises(HTTPException) as exc_info:
                await create_response(
                    request=response_request,
                    token=mock_token,
                    x_request_id="test-request-id",
                )

            assert exc_info.value.status_code == 404

    async def test_response_provider_not_found(
        self, mock_token, response_request, mock_provider_config
    ):
        """Test response when provider not found."""
        with patch("app.routers.responses.simple_router") as mock_router:
            mock_router.route = AsyncMock(return_value="test-provider")

            with patch("app.routers.responses.provider_manager") as mock_pm:
                mock_pm.get_provider = AsyncMock(side_effect=ProviderNotFoundError("test-provider"))

                with pytest.raises(HTTPException) as exc_info:
                    await create_response(
                        request=response_request,
                        token=mock_token,
                        x_request_id="test-request-id",
                    )

                assert exc_info.value.status_code == 503

    async def test_response_provider_disabled(
        self, mock_token, response_request, mock_provider_config
    ):
        """Test response when provider is disabled."""
        with patch("app.routers.responses.simple_router") as mock_router:
            mock_router.route = AsyncMock(return_value="test-provider")

            with patch("app.routers.responses.provider_manager") as mock_pm:
                mock_pm.get_provider = AsyncMock(side_effect=ProviderDisabledError("test-provider"))

                with pytest.raises(HTTPException) as exc_info:
                    await create_response(
                        request=response_request,
                        token=mock_token,
                        x_request_id="test-request-id",
                    )

                assert exc_info.value.status_code == 503

    async def test_response_provider_timeout(
        self, mock_token, response_request, mock_provider_config
    ):
        """Test response when provider times out."""
        with patch("app.routers.responses.simple_router") as mock_router:
            mock_router.route = AsyncMock(return_value="test-provider")

            with patch("app.routers.responses.provider_manager") as mock_pm:
                mock_pm.get_provider = AsyncMock(return_value=mock_provider_config)

                with patch("app.routers.responses.ProviderFactory") as mock_factory:
                    mock_provider = AsyncMock()
                    mock_provider.create_response = AsyncMock(
                        side_effect=ProviderTimeoutError("test-provider", 30.0)
                    )
                    mock_provider.__aenter__ = AsyncMock(return_value=mock_provider)
                    mock_provider.__aexit__ = AsyncMock(return_value=None)
                    mock_factory.create_provider.return_value = mock_provider

                    with pytest.raises(HTTPException) as exc_info:
                        await create_response(
                            request=response_request,
                            token=mock_token,
                            x_request_id="test-request-id",
                        )

                    assert exc_info.value.status_code == 504

    async def test_response_provider_rate_limit(
        self, mock_token, response_request, mock_provider_config
    ):
        """Test response when rate limited."""
        with patch("app.routers.responses.simple_router") as mock_router:
            mock_router.route = AsyncMock(return_value="test-provider")

            with patch("app.routers.responses.provider_manager") as mock_pm:
                mock_pm.get_provider = AsyncMock(return_value=mock_provider_config)

                with patch("app.routers.responses.ProviderFactory") as mock_factory:
                    mock_provider = AsyncMock()
                    mock_provider.create_response = AsyncMock(
                        side_effect=ProviderRateLimitError("Rate limited")
                    )
                    mock_provider.__aenter__ = AsyncMock(return_value=mock_provider)
                    mock_provider.__aexit__ = AsyncMock(return_value=None)
                    mock_factory.create_provider.return_value = mock_provider

                    with pytest.raises(HTTPException) as exc_info:
                        await create_response(
                            request=response_request,
                            token=mock_token,
                            x_request_id="test-request-id",
                        )

                    assert exc_info.value.status_code == 429

    async def test_response_provider_http_error(
        self, mock_token, response_request, mock_provider_config
    ):
        """Test response with provider HTTP error."""
        with patch("app.routers.responses.simple_router") as mock_router:
            mock_router.route = AsyncMock(return_value="test-provider")

            with patch("app.routers.responses.provider_manager") as mock_pm:
                mock_pm.get_provider = AsyncMock(return_value=mock_provider_config)

                with patch("app.routers.responses.ProviderFactory") as mock_factory:
                    mock_provider = AsyncMock()
                    mock_provider.create_response = AsyncMock(
                        side_effect=ProviderHTTPError(500, "Server error")
                    )
                    mock_provider.__aenter__ = AsyncMock(return_value=mock_provider)
                    mock_provider.__aexit__ = AsyncMock(return_value=None)
                    mock_factory.create_provider.return_value = mock_provider

                    with pytest.raises(HTTPException) as exc_info:
                        await create_response(
                            request=response_request,
                            token=mock_token,
                            x_request_id="test-request-id",
                        )

                    assert exc_info.value.status_code == 502

    async def test_response_gateway_error(self, mock_token, response_request, mock_provider_config):
        """Test response with gateway error."""
        with patch("app.routers.responses.simple_router") as mock_router:
            mock_router.route = AsyncMock(return_value="test-provider")

            with patch("app.routers.responses.provider_manager") as mock_pm:
                mock_pm.get_provider = AsyncMock(return_value=mock_provider_config)

                with patch("app.routers.responses.ProviderFactory") as mock_factory:
                    mock_provider = AsyncMock()
                    mock_provider.create_response = AsyncMock(
                        side_effect=GatewayError("Gateway error")
                    )
                    mock_provider.__aenter__ = AsyncMock(return_value=mock_provider)
                    mock_provider.__aexit__ = AsyncMock(return_value=None)
                    mock_factory.create_provider.return_value = mock_provider

                    with pytest.raises(HTTPException) as exc_info:
                        await create_response(
                            request=response_request,
                            token=mock_token,
                            x_request_id="test-request-id",
                        )

                    assert exc_info.value.status_code == 500

    async def test_response_unexpected_error(
        self, mock_token, response_request, mock_provider_config
    ):
        """Test response with unexpected error."""
        with patch("app.routers.responses.simple_router") as mock_router:
            mock_router.route = AsyncMock(return_value="test-provider")

            with patch("app.routers.responses.provider_manager") as mock_pm:
                mock_pm.get_provider = AsyncMock(return_value=mock_provider_config)

                with patch("app.routers.responses.ProviderFactory") as mock_factory:
                    mock_provider = AsyncMock()
                    mock_provider.create_response = AsyncMock(
                        side_effect=RuntimeError("Unexpected")
                    )
                    mock_provider.__aenter__ = AsyncMock(return_value=mock_provider)
                    mock_provider.__aexit__ = AsyncMock(return_value=None)
                    mock_factory.create_provider.return_value = mock_provider

                    with pytest.raises(HTTPException) as exc_info:
                        await create_response(
                            request=response_request,
                            token=mock_token,
                            x_request_id="test-request-id",
                        )

                    assert exc_info.value.status_code == 500

    async def test_response_auto_request_id(
        self, mock_token, response_request, mock_provider_config
    ):
        """Test response with auto-generated request ID."""
        mock_response = {
            "id": "resp_12345",
            "object": "response",
            "created_at": 1234567890,
            "model": "gpt-4o",
            "output": [],
        }

        with patch("app.routers.responses.simple_router") as mock_router:
            mock_router.route = AsyncMock(return_value="test-provider")

            with patch("app.routers.responses.provider_manager") as mock_pm:
                mock_pm.get_provider = AsyncMock(return_value=mock_provider_config)

                with patch("app.routers.responses.ProviderFactory") as mock_factory:
                    mock_provider = AsyncMock()
                    mock_provider.create_response = AsyncMock(return_value=mock_response)
                    mock_provider.__aenter__ = AsyncMock(return_value=mock_provider)
                    mock_provider.__aexit__ = AsyncMock(return_value=None)
                    mock_factory.create_provider.return_value = mock_provider

                    response = await create_response(
                        request=response_request,
                        token=mock_token,
                        x_request_id=None,  # Auto-generate
                    )

        assert response.status_code == 200
        # Check that X-Request-ID header is set
        assert "X-Request-ID" in response.headers
