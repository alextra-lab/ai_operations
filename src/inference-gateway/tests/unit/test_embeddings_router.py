"""
Unit tests for embeddings router endpoints.

Tests embeddings endpoint with various scenarios.

P5-A15: Added comprehensive unit tests for async embeddings router.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.routers.embeddings import create_embeddings
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
def embedding_request():
    """Sample embedding request."""
    from app.models.embedding_request import EmbeddingRequest

    return EmbeddingRequest(
        model="text-embedding-3-small",
        input="Hello world",
    )


@pytest.fixture
def batch_embedding_request():
    """Sample batch embedding request."""
    from app.models.embedding_request import EmbeddingRequest

    return EmbeddingRequest(
        model="text-embedding-3-small",
        input=["Hello world", "Goodbye world", "Test input"],
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
class TestCreateEmbeddings:
    """Test create_embeddings endpoint."""

    async def test_embeddings_success(self, mock_token, embedding_request, mock_provider_config):
        """Test successful embedding creation."""
        mock_response = {
            "object": "list",
            "data": [
                {
                    "object": "embedding",
                    "embedding": [0.1, 0.2, 0.3, 0.4, 0.5],
                    "index": 0,
                }
            ],
            "model": "text-embedding-3-small",
            "usage": {"prompt_tokens": 5, "total_tokens": 5},
        }

        with patch("app.routers.embeddings.simple_router") as mock_router:
            mock_router.route = AsyncMock(return_value="test-provider")

            with patch("app.routers.embeddings.provider_manager") as mock_pm:
                mock_pm.get_provider = AsyncMock(return_value=mock_provider_config)

                with patch("app.routers.embeddings.ProviderFactory") as mock_factory:
                    mock_provider = AsyncMock()
                    mock_provider.create_embeddings = AsyncMock(return_value=mock_response)
                    mock_provider.__aenter__ = AsyncMock(return_value=mock_provider)
                    mock_provider.__aexit__ = AsyncMock(return_value=None)
                    mock_factory.create_provider.return_value = mock_provider

                    response = await create_embeddings(
                        request=embedding_request,
                        token=mock_token,
                        x_request_id="test-request-id",
                    )

        assert response.status_code == 200
        body = response.body.decode()
        assert "embedding" in body
        assert "text-embedding-3-small" in body

    async def test_embeddings_batch_success(
        self, mock_token, batch_embedding_request, mock_provider_config
    ):
        """Test successful batch embedding creation."""
        mock_response = {
            "object": "list",
            "data": [
                {"object": "embedding", "embedding": [0.1, 0.2], "index": 0},
                {"object": "embedding", "embedding": [0.3, 0.4], "index": 1},
                {"object": "embedding", "embedding": [0.5, 0.6], "index": 2},
            ],
            "model": "text-embedding-3-small",
            "usage": {"prompt_tokens": 15, "total_tokens": 15},
        }

        with patch("app.routers.embeddings.simple_router") as mock_router:
            mock_router.route = AsyncMock(return_value="test-provider")

            with patch("app.routers.embeddings.provider_manager") as mock_pm:
                mock_pm.get_provider = AsyncMock(return_value=mock_provider_config)

                with patch("app.routers.embeddings.ProviderFactory") as mock_factory:
                    mock_provider = AsyncMock()
                    mock_provider.create_embeddings = AsyncMock(return_value=mock_response)
                    mock_provider.__aenter__ = AsyncMock(return_value=mock_provider)
                    mock_provider.__aexit__ = AsyncMock(return_value=None)
                    mock_factory.create_provider.return_value = mock_provider

                    response = await create_embeddings(
                        request=batch_embedding_request,
                        token=mock_token,
                        x_request_id="test-request-id",
                    )

        assert response.status_code == 200

    async def test_embeddings_model_not_found(self, mock_token, embedding_request):
        """Test embeddings with unknown model."""
        with patch("app.routers.embeddings.simple_router") as mock_router:
            mock_router.route = AsyncMock(side_effect=ModelNotFoundError("unknown-model"))

            with pytest.raises(HTTPException) as exc_info:
                await create_embeddings(
                    request=embedding_request,
                    token=mock_token,
                    x_request_id="test-request-id",
                )

            assert exc_info.value.status_code == 404

    async def test_embeddings_provider_not_found(
        self, mock_token, embedding_request, mock_provider_config
    ):
        """Test embeddings when provider not found."""
        with patch("app.routers.embeddings.simple_router") as mock_router:
            mock_router.route = AsyncMock(return_value="test-provider")

            with patch("app.routers.embeddings.provider_manager") as mock_pm:
                mock_pm.get_provider = AsyncMock(side_effect=ProviderNotFoundError("test-provider"))

                with pytest.raises(HTTPException) as exc_info:
                    await create_embeddings(
                        request=embedding_request,
                        token=mock_token,
                        x_request_id="test-request-id",
                    )

                assert exc_info.value.status_code == 503

    async def test_embeddings_provider_disabled(
        self, mock_token, embedding_request, mock_provider_config
    ):
        """Test embeddings when provider is disabled."""
        with patch("app.routers.embeddings.simple_router") as mock_router:
            mock_router.route = AsyncMock(return_value="test-provider")

            with patch("app.routers.embeddings.provider_manager") as mock_pm:
                mock_pm.get_provider = AsyncMock(side_effect=ProviderDisabledError("test-provider"))

                with pytest.raises(HTTPException) as exc_info:
                    await create_embeddings(
                        request=embedding_request,
                        token=mock_token,
                        x_request_id="test-request-id",
                    )

                assert exc_info.value.status_code == 503

    async def test_embeddings_provider_timeout(
        self, mock_token, embedding_request, mock_provider_config
    ):
        """Test embeddings when provider times out."""
        with patch("app.routers.embeddings.simple_router") as mock_router:
            mock_router.route = AsyncMock(return_value="test-provider")

            with patch("app.routers.embeddings.provider_manager") as mock_pm:
                mock_pm.get_provider = AsyncMock(return_value=mock_provider_config)

                with patch("app.routers.embeddings.ProviderFactory") as mock_factory:
                    mock_provider = AsyncMock()
                    mock_provider.create_embeddings = AsyncMock(
                        side_effect=ProviderTimeoutError("test-provider", 30.0)
                    )
                    mock_provider.__aenter__ = AsyncMock(return_value=mock_provider)
                    mock_provider.__aexit__ = AsyncMock(return_value=None)
                    mock_factory.create_provider.return_value = mock_provider

                    with pytest.raises(HTTPException) as exc_info:
                        await create_embeddings(
                            request=embedding_request,
                            token=mock_token,
                            x_request_id="test-request-id",
                        )

                    assert exc_info.value.status_code == 504

    async def test_embeddings_provider_rate_limit(
        self, mock_token, embedding_request, mock_provider_config
    ):
        """Test embeddings when rate limited."""
        with patch("app.routers.embeddings.simple_router") as mock_router:
            mock_router.route = AsyncMock(return_value="test-provider")

            with patch("app.routers.embeddings.provider_manager") as mock_pm:
                mock_pm.get_provider = AsyncMock(return_value=mock_provider_config)

                with patch("app.routers.embeddings.ProviderFactory") as mock_factory:
                    mock_provider = AsyncMock()
                    mock_provider.create_embeddings = AsyncMock(
                        side_effect=ProviderRateLimitError("Rate limited")
                    )
                    mock_provider.__aenter__ = AsyncMock(return_value=mock_provider)
                    mock_provider.__aexit__ = AsyncMock(return_value=None)
                    mock_factory.create_provider.return_value = mock_provider

                    with pytest.raises(HTTPException) as exc_info:
                        await create_embeddings(
                            request=embedding_request,
                            token=mock_token,
                            x_request_id="test-request-id",
                        )

                    assert exc_info.value.status_code == 429

    async def test_embeddings_provider_http_error(
        self, mock_token, embedding_request, mock_provider_config
    ):
        """Test embeddings with provider HTTP error."""
        with patch("app.routers.embeddings.simple_router") as mock_router:
            mock_router.route = AsyncMock(return_value="test-provider")

            with patch("app.routers.embeddings.provider_manager") as mock_pm:
                mock_pm.get_provider = AsyncMock(return_value=mock_provider_config)

                with patch("app.routers.embeddings.ProviderFactory") as mock_factory:
                    mock_provider = AsyncMock()
                    mock_provider.create_embeddings = AsyncMock(
                        side_effect=ProviderHTTPError(500, "Server error")
                    )
                    mock_provider.__aenter__ = AsyncMock(return_value=mock_provider)
                    mock_provider.__aexit__ = AsyncMock(return_value=None)
                    mock_factory.create_provider.return_value = mock_provider

                    with pytest.raises(HTTPException) as exc_info:
                        await create_embeddings(
                            request=embedding_request,
                            token=mock_token,
                            x_request_id="test-request-id",
                        )

                    assert exc_info.value.status_code == 502

    async def test_embeddings_gateway_error(
        self, mock_token, embedding_request, mock_provider_config
    ):
        """Test embeddings with gateway error."""
        with patch("app.routers.embeddings.simple_router") as mock_router:
            mock_router.route = AsyncMock(return_value="test-provider")

            with patch("app.routers.embeddings.provider_manager") as mock_pm:
                mock_pm.get_provider = AsyncMock(return_value=mock_provider_config)

                with patch("app.routers.embeddings.ProviderFactory") as mock_factory:
                    mock_provider = AsyncMock()
                    mock_provider.create_embeddings = AsyncMock(
                        side_effect=GatewayError("Gateway error")
                    )
                    mock_provider.__aenter__ = AsyncMock(return_value=mock_provider)
                    mock_provider.__aexit__ = AsyncMock(return_value=None)
                    mock_factory.create_provider.return_value = mock_provider

                    with pytest.raises(HTTPException) as exc_info:
                        await create_embeddings(
                            request=embedding_request,
                            token=mock_token,
                            x_request_id="test-request-id",
                        )

                    assert exc_info.value.status_code == 500

    async def test_embeddings_unexpected_error(
        self, mock_token, embedding_request, mock_provider_config
    ):
        """Test embeddings with unexpected error."""
        with patch("app.routers.embeddings.simple_router") as mock_router:
            mock_router.route = AsyncMock(return_value="test-provider")

            with patch("app.routers.embeddings.provider_manager") as mock_pm:
                mock_pm.get_provider = AsyncMock(return_value=mock_provider_config)

                with patch("app.routers.embeddings.ProviderFactory") as mock_factory:
                    mock_provider = AsyncMock()
                    mock_provider.create_embeddings = AsyncMock(
                        side_effect=RuntimeError("Unexpected")
                    )
                    mock_provider.__aenter__ = AsyncMock(return_value=mock_provider)
                    mock_provider.__aexit__ = AsyncMock(return_value=None)
                    mock_factory.create_provider.return_value = mock_provider

                    with pytest.raises(HTTPException) as exc_info:
                        await create_embeddings(
                            request=embedding_request,
                            token=mock_token,
                            x_request_id="test-request-id",
                        )

                    assert exc_info.value.status_code == 500

    async def test_embeddings_auto_request_id(
        self, mock_token, embedding_request, mock_provider_config
    ):
        """Test embeddings with auto-generated request ID."""
        mock_response = {
            "object": "list",
            "data": [{"object": "embedding", "embedding": [0.1, 0.2], "index": 0}],
            "model": "text-embedding-3-small",
            "usage": {"prompt_tokens": 5, "total_tokens": 5},
        }

        with patch("app.routers.embeddings.simple_router") as mock_router:
            mock_router.route = AsyncMock(return_value="test-provider")

            with patch("app.routers.embeddings.provider_manager") as mock_pm:
                mock_pm.get_provider = AsyncMock(return_value=mock_provider_config)

                with patch("app.routers.embeddings.ProviderFactory") as mock_factory:
                    mock_provider = AsyncMock()
                    mock_provider.create_embeddings = AsyncMock(return_value=mock_response)
                    mock_provider.__aenter__ = AsyncMock(return_value=mock_provider)
                    mock_provider.__aexit__ = AsyncMock(return_value=None)
                    mock_factory.create_provider.return_value = mock_provider

                    response = await create_embeddings(
                        request=embedding_request,
                        token=mock_token,
                        x_request_id=None,  # Auto-generate
                    )

        assert response.status_code == 200
        # Check that X-Request-ID header is set
        assert "X-Request-ID" in response.headers
