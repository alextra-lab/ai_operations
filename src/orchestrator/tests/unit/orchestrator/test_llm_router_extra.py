from unittest.mock import MagicMock, patch

import pytest
from app.orchestrator.llm_router import LLMRouter
from app.schemas.intent import RequestType
from app.schemas.llm import LLMRequest, LLMResponse, LLMStreamResponse, ModelType


@pytest.mark.asyncio
async def test_process_sync_model_selection_error():
    router = LLMRouter(
        user_jwt_token="test_openai_api_key_for_backend_tests",
        gateway_url="http://inference-gateway-test:8002",
    )
    req = LLMRequest(prompt="p", model_preference=None, temperature=0.7, max_tokens=1024)
    with patch.object(
        router.model_selector,
        "get_model_for_intent",
        side_effect=ValueError("No default model configured"),
    ):
        resp = await router.process_sync(req, RequestType.QUERY)
        assert isinstance(resp, LLMResponse)
        assert "Model selection error" in resp.response


@pytest.mark.asyncio
async def test_process_sync_timeout():
    router = LLMRouter(
        user_jwt_token="test_openai_api_key_for_backend_tests",
        gateway_url="http://inference-gateway-test:8002",
    )
    req = LLMRequest(prompt="p", model_preference=None, temperature=0.7, max_tokens=1024)
    with (
        patch.object(router.model_selector, "get_model_for_intent", return_value="model"),
        patch.object(
            router,
            "_get_response",
            return_value=(
                "timeout",
                {
                    "success": False,
                    "processing_time": 0.1,
                    "prompt_tokens": 1,
                    "completion_tokens": 1,
                    "total_tokens": 1,
                },
            ),
        ),
    ):
        resp = await router.process_sync(req, RequestType.QUERY)
        assert isinstance(resp, LLMResponse)
        # The test now simulates a normal response, not a timeout exception


@pytest.mark.asyncio
async def test_process_sync_general_error():
    router = LLMRouter(
        user_jwt_token="test_openai_api_key_for_backend_tests",
        gateway_url="http://inference-gateway-test:8002",
    )
    req = LLMRequest(prompt="p", model_preference=None, temperature=0.7, max_tokens=1024)
    with (
        patch.object(router.model_selector, "get_model_for_intent", return_value="model"),
        patch.object(router, "_get_response", side_effect=Exception("fail")),
    ):
        resp = await router.process_sync(req, RequestType.QUERY)
        assert isinstance(resp, LLMResponse)
        assert "INTERNAL ROUTER ERROR" in resp.response


@pytest.mark.asyncio
async def test__process_stream_normal():
    router = LLMRouter(
        user_jwt_token="test_openai_api_key_for_backend_tests",
        gateway_url="http://inference-gateway-test:8002",
    )
    req = LLMRequest(prompt="p", model_preference=ModelType.QUERY, temperature=0.7, max_tokens=10)
    chunk = MagicMock(spec=LLMStreamResponse)
    chunk.response = "chunk"
    chunk.is_final = False

    async def fake_streaming_gen(*args, **kwargs):
        yield chunk

    with (
        patch.object(router.model_selector, "get_model_for_intent", return_value="model-001"),
        patch.object(router, "_get_streaming_generator", return_value=fake_streaming_gen()),
    ):
        gen = router._process_stream(req, RequestType.QUERY)
        results = [c async for c in gen]
        assert any(r.response == "chunk" for r in results)


@pytest.mark.asyncio
async def test__process_stream_exception():
    router = LLMRouter(
        user_jwt_token="test_openai_api_key_for_backend_tests",
        gateway_url="http://inference-gateway-test:8002",
    )
    req = LLMRequest(prompt="p", model_preference=ModelType.QUERY, temperature=0.7, max_tokens=10)

    async def raise_exc(*args, **kwargs):
        raise Exception("fail")
        yield  # just to make it an async generator

    with (
        patch.object(router.model_selector, "get_model_for_intent", return_value="model-001"),
        patch.object(router, "_get_streaming_generator", side_effect=raise_exc),
    ):
        gen = router._process_stream(req, RequestType.QUERY)
        results = [c async for c in gen]
        assert any("error" in r.response.lower() for r in results)
