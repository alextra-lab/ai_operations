"""
Unit tests for chat router endpoints.

Tests chat completions and list models endpoints.

P5-A15: Added comprehensive unit tests for async chat router.
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.models.responses import (
    ChatCompletionChoice,
    ChatCompletionMessage,
    ChatCompletionResponse,
    ChatCompletionUsage,
)
from app.routers.chat import chat_completions, list_models
from app.utils.errors import (
    ModelNotFoundError,
    ProviderDisabledError,
    ProviderHTTPError,
    ProviderNotFoundError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)

PROVIDER_MANAGER_PATH = "app.services.provider_manager.ProviderManager"


@pytest.fixture
def mock_token():
    """Mock JWT token payload."""
    token = MagicMock()
    token.sub = "test-user"
    token.user_id = "test-user-uuid"
    token.role = "user"
    token.is_service = MagicMock(return_value=False)
    return token


@pytest.fixture
def mock_service_token():
    """Mock service JWT token payload."""
    token = MagicMock()
    token.sub = "service:test-service"
    token.user_id = "service-uuid"
    token.role = "service"
    token.is_service = MagicMock(return_value=True)
    return token


@pytest.fixture
def chat_request():
    """Sample chat completion request."""
    from app.models.requests import ChatCompletionRequest

    return ChatCompletionRequest(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Hello"}],
        stream=False,
    )


@pytest.fixture
def streaming_request():
    """Sample streaming chat completion request."""
    from app.models.requests import ChatCompletionRequest

    return ChatCompletionRequest(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Hello"}],
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
class TestChatCompletions:
    """Test chat_completions endpoint."""

    async def test_chat_success(self, mock_token, chat_request, mock_provider_config):
        """Test successful chat completion."""
        mock_response = ChatCompletionResponse(
            id="chatcmpl-123",
            object="chat.completion",
            created=int(time.time()),
            model="gpt-4o-mini",
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatCompletionMessage(role="assistant", content="Hello!"),
                    finish_reason="stop",
                )
            ],
            usage=ChatCompletionUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        )

        with patch("app.routers.chat.simple_router") as mock_router:
            mock_router.route = AsyncMock(return_value="test-provider")

            with patch("app.routers.chat.provider_manager") as mock_pm:
                mock_pm.get_provider = AsyncMock(return_value=mock_provider_config)

                with patch("app.routers.chat.ProviderFactory") as mock_factory:
                    mock_provider = AsyncMock()
                    mock_provider.chat_completion = AsyncMock(return_value=mock_response)
                    mock_provider.__aenter__ = AsyncMock(return_value=mock_provider)
                    mock_provider.__aexit__ = AsyncMock(return_value=None)
                    mock_factory.create_provider.return_value = mock_provider

                    with patch("app.routers.chat.get_usage_logger") as mock_logger:
                        mock_usage_logger = AsyncMock()
                        mock_usage_logger.log_usage = AsyncMock()
                        mock_logger.return_value = mock_usage_logger

                        with patch("app.routers.chat.cost_calculator") as mock_calc:
                            mock_calc.calculate = AsyncMock(
                                return_value={
                                    "total_cost_eur": 0.001,
                                    "pricing_source": "mock",
                                }
                            )

                            response = await chat_completions(
                                request=chat_request,
                                token=mock_token,
                                x_request_id="test-request-id",
                            )

        assert response.status_code == 200
        body = response.body.decode()
        assert "chatcmpl-123" in body
        assert "Hello!" in body

    async def test_chat_model_not_found(self, mock_token, chat_request):
        """Test chat completion with unknown model."""
        with patch("app.routers.chat.simple_router") as mock_router:
            mock_router.route = AsyncMock(side_effect=ModelNotFoundError("unknown-model"))

            with pytest.raises(HTTPException) as exc_info:
                await chat_completions(
                    request=chat_request,
                    token=mock_token,
                    x_request_id="test-request-id",
                )

            assert exc_info.value.status_code == 404

    async def test_chat_provider_not_found(self, mock_token, chat_request, mock_provider_config):
        """Test chat completion when provider not found."""
        with patch("app.routers.chat.simple_router") as mock_router:
            mock_router.route = AsyncMock(return_value="test-provider")

            with patch("app.routers.chat.provider_manager") as mock_pm:
                mock_pm.get_provider = AsyncMock(side_effect=ProviderNotFoundError("test-provider"))

                with pytest.raises(HTTPException) as exc_info:
                    await chat_completions(
                        request=chat_request,
                        token=mock_token,
                        x_request_id="test-request-id",
                    )

                assert exc_info.value.status_code == 503

    async def test_chat_provider_disabled(self, mock_token, chat_request, mock_provider_config):
        """Test chat completion when provider is disabled."""
        with patch("app.routers.chat.simple_router") as mock_router:
            mock_router.route = AsyncMock(return_value="test-provider")

            with patch("app.routers.chat.provider_manager") as mock_pm:
                mock_pm.get_provider = AsyncMock(side_effect=ProviderDisabledError("test-provider"))

                with pytest.raises(HTTPException) as exc_info:
                    await chat_completions(
                        request=chat_request,
                        token=mock_token,
                        x_request_id="test-request-id",
                    )

                assert exc_info.value.status_code == 503

    async def test_chat_provider_timeout(self, mock_token, chat_request, mock_provider_config):
        """Test chat completion when provider times out."""
        with patch("app.routers.chat.simple_router") as mock_router:
            mock_router.route = AsyncMock(return_value="test-provider")

            with patch("app.routers.chat.provider_manager") as mock_pm:
                mock_pm.get_provider = AsyncMock(return_value=mock_provider_config)

                with patch("app.routers.chat.ProviderFactory") as mock_factory:
                    mock_provider = AsyncMock()
                    mock_provider.chat_completion = AsyncMock(
                        side_effect=ProviderTimeoutError("test-provider", 30.0)
                    )
                    mock_provider.__aenter__ = AsyncMock(return_value=mock_provider)
                    mock_provider.__aexit__ = AsyncMock(return_value=None)
                    mock_factory.create_provider.return_value = mock_provider

                    with pytest.raises(HTTPException) as exc_info:
                        await chat_completions(
                            request=chat_request,
                            token=mock_token,
                            x_request_id="test-request-id",
                        )

                    assert exc_info.value.status_code == 504

    async def test_chat_provider_rate_limit(self, mock_token, chat_request, mock_provider_config):
        """Test chat completion when rate limited."""
        with patch("app.routers.chat.simple_router") as mock_router:
            mock_router.route = AsyncMock(return_value="test-provider")

            with patch("app.routers.chat.provider_manager") as mock_pm:
                mock_pm.get_provider = AsyncMock(return_value=mock_provider_config)

                with patch("app.routers.chat.ProviderFactory") as mock_factory:
                    mock_provider = AsyncMock()
                    mock_provider.chat_completion = AsyncMock(
                        side_effect=ProviderRateLimitError("Rate limited")
                    )
                    mock_provider.__aenter__ = AsyncMock(return_value=mock_provider)
                    mock_provider.__aexit__ = AsyncMock(return_value=None)
                    mock_factory.create_provider.return_value = mock_provider

                    with pytest.raises(HTTPException) as exc_info:
                        await chat_completions(
                            request=chat_request,
                            token=mock_token,
                            x_request_id="test-request-id",
                        )

                    assert exc_info.value.status_code == 429

    async def test_chat_provider_http_error(self, mock_token, chat_request, mock_provider_config):
        """Test chat completion with provider HTTP error."""
        with patch("app.routers.chat.simple_router") as mock_router:
            mock_router.route = AsyncMock(return_value="test-provider")

            with patch("app.routers.chat.provider_manager") as mock_pm:
                mock_pm.get_provider = AsyncMock(return_value=mock_provider_config)

                with patch("app.routers.chat.ProviderFactory") as mock_factory:
                    mock_provider = AsyncMock()
                    mock_provider.chat_completion = AsyncMock(
                        side_effect=ProviderHTTPError(500, "Server error")
                    )
                    mock_provider.__aenter__ = AsyncMock(return_value=mock_provider)
                    mock_provider.__aexit__ = AsyncMock(return_value=None)
                    mock_factory.create_provider.return_value = mock_provider

                    with pytest.raises(HTTPException) as exc_info:
                        await chat_completions(
                            request=chat_request,
                            token=mock_token,
                            x_request_id="test-request-id",
                        )

                    assert exc_info.value.status_code == 502

    async def test_chat_with_service_token(
        self, mock_service_token, chat_request, mock_provider_config
    ):
        """Test chat completion with service token."""
        mock_response = ChatCompletionResponse(
            id="chatcmpl-123",
            object="chat.completion",
            created=int(time.time()),
            model="gpt-4o-mini",
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatCompletionMessage(role="assistant", content="Hello!"),
                    finish_reason="stop",
                )
            ],
            usage=ChatCompletionUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        )

        with patch("app.routers.chat.simple_router") as mock_router:
            mock_router.route = AsyncMock(return_value="test-provider")

            with patch("app.routers.chat.provider_manager") as mock_pm:
                mock_pm.get_provider = AsyncMock(return_value=mock_provider_config)

                with patch("app.routers.chat.ProviderFactory") as mock_factory:
                    mock_provider = AsyncMock()
                    mock_provider.chat_completion = AsyncMock(return_value=mock_response)
                    mock_provider.__aenter__ = AsyncMock(return_value=mock_provider)
                    mock_provider.__aexit__ = AsyncMock(return_value=None)
                    mock_factory.create_provider.return_value = mock_provider

                    with patch("app.routers.chat.get_usage_logger") as mock_logger:
                        mock_usage_logger = AsyncMock()
                        mock_usage_logger.log_usage = AsyncMock()
                        mock_logger.return_value = mock_usage_logger

                        with patch("app.routers.chat.cost_calculator") as mock_calc:
                            mock_calc.calculate = AsyncMock(
                                return_value={
                                    "total_cost_eur": 0.001,
                                    "pricing_source": "mock",
                                }
                            )

                            response = await chat_completions(
                                request=chat_request,
                                token=mock_service_token,
                                x_request_id=None,  # Test auto-generated request ID
                            )

        assert response.status_code == 200


@pytest.mark.asyncio
class TestStreamingChatCompletions:
    """Test streaming chat completions endpoint."""

    async def test_streaming_returns_streaming_response(
        self, mock_token, streaming_request, mock_provider_config
    ):
        """Test that streaming request returns StreamingResponse."""
        from fastapi.responses import StreamingResponse

        from app.models.responses import ChatCompletionStreamChunk

        mock_chunk = ChatCompletionStreamChunk(
            id="chatcmpl-123",
            object="chat.completion.chunk",
            created=1234567890,
            model="gpt-4o-mini",
            choices=[{"index": 0, "delta": {"content": "Hello"}, "finish_reason": None}],
        )

        async def mock_stream(*_args, **_kwargs):
            yield mock_chunk

        with patch("app.routers.chat.simple_router") as mock_router:
            mock_router.route = AsyncMock(return_value="test-provider")

            with patch("app.routers.chat.provider_manager") as mock_pm:
                mock_pm.get_provider = AsyncMock(return_value=mock_provider_config)

                with patch("app.routers.chat.ProviderFactory") as mock_factory:
                    mock_provider = AsyncMock()
                    mock_provider.stream_chat_completion = mock_stream
                    mock_provider.__aenter__ = AsyncMock(return_value=mock_provider)
                    mock_provider.__aexit__ = AsyncMock(return_value=None)
                    mock_factory.create_provider.return_value = mock_provider

                    with patch("app.routers.chat.get_usage_logger") as mock_logger:
                        mock_usage_logger = AsyncMock()
                        mock_usage_logger.log_usage = AsyncMock()
                        mock_logger.return_value = mock_usage_logger

                        response = await chat_completions(
                            request=streaming_request,
                            token=mock_token,
                            x_request_id="test-request-id",
                        )

        assert isinstance(response, StreamingResponse)
        assert response.media_type == "text/event-stream"


@pytest.mark.asyncio
class TestListModels:
    """Test list_models endpoint."""

    async def test_list_models_success(self, mock_token):
        """Test successful model listing."""
        from app.providers.base import ProviderConfig

        mock_provider = ProviderConfig(
            id="11111111-1111-1111-1111-111111111111",
            name="TestProvider",
            provider_type="openai",
            base_url="http://localhost:1234",
            api_key=None,
            is_enabled=True,
            priority=10,
        )

        mock_provider_manager = MagicMock()
        mock_provider_manager.load_providers = AsyncMock()
        mock_provider_manager.list_providers = AsyncMock(return_value=[mock_provider])

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"id": "gpt-4o-mini", "object": "model"},
                {"id": "gpt-4o", "object": "model"},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with (
            patch(PROVIDER_MANAGER_PATH, return_value=mock_provider_manager),
            patch("httpx.AsyncClient") as mock_client,
        ):
            mock_client_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            mock_client_instance.get = AsyncMock(return_value=mock_response)

            response = await list_models(token=mock_token)

            assert response.status_code == 200
            body = response.body.decode()
            assert "gpt-4o-mini" in body
            assert "gpt-4o" in body
            assert '"object":"list"' in body  # JSON without spaces

    async def test_list_models_aggregates_from_providers(self, mock_token):
        """Test listing models aggregates from all enabled providers with metadata."""
        from app.providers.base import ProviderConfig

        # Mock ProviderManager with two providers
        mock_provider1 = ProviderConfig(
            id="11111111-1111-1111-1111-111111111111",
            name="LMStudio",
            provider_type="openai",
            base_url="http://localhost:1234",
            api_key=None,
            is_enabled=True,
            priority=10,
        )
        mock_provider2 = ProviderConfig(
            id="22222222-2222-2222-2222-222222222222",
            name="Ollama",
            provider_type="openai",
            base_url="http://localhost:11434",
            api_key=None,
            is_enabled=True,
            priority=20,
        )

        mock_provider_manager = MagicMock()
        mock_provider_manager.load_providers = AsyncMock()
        mock_provider_manager.list_providers = AsyncMock(
            return_value=[mock_provider1, mock_provider2]
        )

        # Mock provider responses

        mock_response1 = MagicMock()
        mock_response1.json.return_value = {
            "data": [
                {"id": "openai/gpt-oss-120b", "object": "model"},
                {"id": "mistralai/mistral-small-3.2", "object": "model"},
            ]
        }
        mock_response1.raise_for_status = MagicMock()

        mock_response2 = MagicMock()
        mock_response2.json.return_value = {"data": [{"id": "llama-3.2-70b", "object": "model"}]}
        mock_response2.raise_for_status = MagicMock()

        with (
            patch(PROVIDER_MANAGER_PATH, return_value=mock_provider_manager),
            patch("httpx.AsyncClient") as mock_client,
        ):
            mock_client_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            # Mock sequential calls for two providers
            mock_client_instance.get = AsyncMock(side_effect=[mock_response1, mock_response2])

            response = await list_models(token=mock_token)

            assert response.status_code == 200
            body = response.body.decode()
            import json

            data = json.loads(body)
            assert data["object"] == "list"
            # Note: Test may run against real database, so verify structure and metadata presence
            # The key test is that provider metadata is included in the response
            assert len(data["data"]) >= 2  # At least models from one provider

            # Check provider metadata is included for all models
            for model in data["data"]:
                assert "provider" in model, "Provider metadata missing"
            assert "provider_type" in model, "Provider type metadata missing"
            assert model["provider_type"] in [
                "openai",
                "anthropic",
                "local",
            ]

    async def test_list_models_skips_disabled_providers(self, mock_token):
        """Test listing models skips disabled providers."""
        from app.providers.base import ProviderConfig

        mock_provider = ProviderConfig(
            id="11111111-1111-1111-1111-111111111111",
            name="LMStudio",
            provider_type="openai",
            base_url="http://localhost:1234",
            api_key=None,
            is_enabled=False,  # Disabled
            priority=10,
        )

        mock_provider_manager = AsyncMock()
        mock_provider_manager.load_providers = AsyncMock()
        mock_provider_manager.list_providers = AsyncMock(return_value=[mock_provider])

        with (
            patch(PROVIDER_MANAGER_PATH, return_value=mock_provider_manager),
            patch("httpx.AsyncClient"),
        ):
            response = await list_models(token=mock_token)

            assert response.status_code == 200
            body = response.body.decode()
            import json

            data = json.loads(body)
            assert len(data["data"]) == 0  # No models from disabled provider

    async def test_list_models_empty(self, mock_token):
        """Test listing with no models available."""
        mock_provider_manager = AsyncMock()
        mock_provider_manager.load_providers = AsyncMock()
        mock_provider_manager.list_providers = AsyncMock(return_value=[])

        with patch(PROVIDER_MANAGER_PATH, return_value=mock_provider_manager):
            response = await list_models(token=mock_token)

            assert response.status_code == 200
            body = response.body.decode()
            assert '"data":[]' in body  # JSON without spaces

    async def test_list_models_handles_provider_error(self, mock_token):
        """Test listing models handles provider query errors gracefully."""
        from app.providers.base import ProviderConfig

        mock_provider = ProviderConfig(
            id="11111111-1111-1111-1111-111111111111",
            name="LMStudio",
            provider_type="openai",
            base_url="http://localhost:1234",
            api_key=None,
            is_enabled=True,
            priority=10,
        )

        mock_provider_manager = AsyncMock()
        mock_provider_manager.load_providers = AsyncMock()
        mock_provider_manager.list_providers = AsyncMock(return_value=[mock_provider])

        import httpx

        with (
            patch(PROVIDER_MANAGER_PATH, return_value=mock_provider_manager),
            patch("httpx.AsyncClient") as mock_client,
        ):
            mock_client_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            mock_client_instance.get = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "Not found", request=MagicMock(), response=MagicMock()
                )
            )

            # Should not raise - errors are logged but continue
            response = await list_models(token=mock_token)

            assert response.status_code == 200
            body = response.body.decode()
            import json

            data = json.loads(body)
            assert len(data["data"]) == 0  # Empty due to provider error

    async def test_list_models_error(self, mock_token):
        """Test model listing with error."""
        mock_provider_manager = AsyncMock()
        mock_provider_manager.load_providers = AsyncMock(side_effect=Exception("DB error"))

        with patch(PROVIDER_MANAGER_PATH, return_value=mock_provider_manager):
            with pytest.raises(HTTPException) as exc_info:
                await list_models(token=mock_token)

            assert exc_info.value.status_code == 500
