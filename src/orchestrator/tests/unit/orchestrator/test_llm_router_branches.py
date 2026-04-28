from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.orchestrator.llm_router import LLMRouter
from app.schemas.intent import RequestType
from app.schemas.llm import LLMRequest, ModelType
from openai import APITimeoutError


def test_init_invalid_request_timeout():
    """Test that invalid request_timeout_seconds logs a warning."""
    with patch("app.orchestrator.llm_router.logger") as mock_logger:
        LLMRouter(
            user_jwt_token="test_openai_api_key_for_backend_tests",
            gateway_url="http://inference-gateway-test:8002",
            request_timeout_seconds="notanint",  # type: ignore[arg-type]
        )
        assert mock_logger.warning.called


# Test _apply_intent_parameters for both branches
def test_apply_intent_parameters_branches():
    router = LLMRouter(
        user_jwt_token="test_openai_api_key_for_backend_tests",
        gateway_url="http://inference-gateway-test:8002",
    )
    req = LLMRequest(prompt="p", model_preference=ModelType.QUERY, temperature=0.7, max_tokens=1024)
    with (
        patch.object(
            router.parameter_manager, "get_intent_temperature", return_value=0.9
        ) as mock_temp,
        patch.object(
            router.parameter_manager, "get_intent_max_tokens", return_value=2048
        ) as mock_tokens,
        patch("app.orchestrator.llm_router.logger") as mock_logger,
    ):
        router._apply_intent_parameters(req, RequestType.QUERY)
        assert req.temperature == 0.9
        assert req.max_tokens == 2048
        assert mock_temp.called and mock_tokens.called
        assert mock_logger.info.call_count >= 2


@pytest.mark.asyncio
async def test_get_response_success():
    """Test _get_response returns response on successful completion (ADR-069: no fallback)."""
    router = LLMRouter(
        user_jwt_token="test_openai_api_key_for_backend_tests",
        gateway_url="http://inference-gateway-test:8002",
    )
    success_response = MagicMock()
    success_response.choices = [MagicMock(message=MagicMock(content="ok"))]
    success_response.usage = MagicMock(prompt_tokens=1, completion_tokens=1, total_tokens=1)

    router.client.make_async_completion_request = AsyncMock(return_value=success_response)

    resp, meta, tool_calls = await router._get_response(
        openai_model="model-001",
        messages=[{"role": "user", "content": "hi"}],
        temperature=0.7,
        max_tokens=10,
        model_type=ModelType.QUERY,
        intent_type=RequestType.QUERY,
    )
    assert resp == "ok"
    assert meta["success"]
    assert meta["model_id"] == "model-001"


@pytest.mark.asyncio
async def test_get_response_timeout_raises():
    """Test _get_response propagates APITimeoutError (ADR-069: no fallback)."""
    router = LLMRouter(
        user_jwt_token="test_openai_api_key_for_backend_tests",
        gateway_url="http://inference-gateway-test:8002",
    )
    router.client.make_async_completion_request = AsyncMock(side_effect=APITimeoutError("timeout"))

    with pytest.raises(APITimeoutError):
        await router._get_response(
            openai_model="model-001",
            messages=[{"role": "user", "content": "hi"}],
            temperature=0.7,
            max_tokens=10,
            model_type=ModelType.QUERY,
            intent_type=RequestType.QUERY,
        )
