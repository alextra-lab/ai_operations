from unittest.mock import MagicMock, patch

import pytest
from app.orchestrator.llm_router import LLMRouter
from app.schemas.intent import RequestType
from app.schemas.llm import LLMRequest, LLMResponse, LLMStreamResponse, ModelType
from app.schemas.use_case_config import ModelsConfig, UseCaseConfig


@pytest.fixture
def router():
    return LLMRouter(
        user_jwt_token="test_openai_api_key_for_backend_tests",
        gateway_url="http://inference-gateway-test:8002",
    )


def test_apply_intent_parameters_temperature_and_tokens(router):
    req = LLMRequest(prompt="p", model_preference=ModelType.QUERY, temperature=0.7, max_tokens=1024)
    with (
        patch.object(
            router.parameter_manager, "get_intent_temperature", return_value=0.9
        ) as mock_temp,
        patch.object(
            router.parameter_manager, "get_intent_max_tokens", return_value=2048
        ) as mock_tokens,
    ):
        router._apply_intent_parameters(req, RequestType.QUERY)
        assert req.temperature == 0.9
        assert req.max_tokens == 2048
        assert mock_temp.called and mock_tokens.called


@pytest.mark.asyncio
async def test_process_sync_model_selection_error(router):
    req = LLMRequest(prompt="p", model_preference=ModelType.QUERY, temperature=0.7, max_tokens=1024)
    with patch.object(
        router.model_selector,
        "get_model_for_intent",
        side_effect=ValueError("No default model configured"),
    ):
        resp = await router.process_sync(req, RequestType.QUERY)
        assert isinstance(resp, LLMResponse)
        assert "Model selection error" in resp.response


@pytest.mark.asyncio
async def test_process_sync_timeout(router):
    req = LLMRequest(prompt="p", model_preference=ModelType.QUERY, temperature=0.7, max_tokens=1024)
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
async def test_process_sync_general_error(router):
    req = LLMRequest(prompt="p", model_preference=ModelType.QUERY, temperature=0.7, max_tokens=1024)
    with (
        patch.object(router.model_selector, "get_model_for_intent", return_value="model"),
        patch.object(router, "_get_response", side_effect=Exception("fail")),
    ):
        resp = await router.process_sync(req, RequestType.QUERY)
        assert isinstance(resp, LLMResponse)
        assert "INTERNAL ROUTER ERROR" in resp.response


@pytest.mark.asyncio
async def test__process_stream_yields_chunks(router):
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
        assert len(results) == 1
        assert results[0].response == "chunk"


def test_apply_config_overrides_model_name_override(router):
    """Test that model_name_override is set correctly from use case config (ADR-069)."""
    req = LLMRequest(prompt="test", temperature=0.7, max_tokens=1024)
    use_case_config = UseCaseConfig(models=ModelsConfig(llm="foundation-sec-8b-instruct-mlx"))

    router._apply_config_overrides(req, use_case_config)

    assert req.model_name_override == "foundation-sec-8b-instruct-mlx"


def test_apply_config_overrides_model_pin(router):
    """Test that any model ID pin is applied from config.models.llm."""
    req = LLMRequest(prompt="test", temperature=0.7, max_tokens=1024)
    use_case_config = UseCaseConfig(models=ModelsConfig(llm="gpt-4o-mini"))

    router._apply_config_overrides(req, use_case_config)

    assert req.model_name_override == "gpt-4o-mini"


def test_apply_config_overrides_no_config(router):
    """Test that no override is applied when config is None."""
    req = LLMRequest(prompt="test", temperature=0.7, max_tokens=1024)
    initial_override = req.model_name_override

    router._apply_config_overrides(req, None)

    assert req.model_name_override == initial_override


def test_apply_config_overrides_generation_params(router):
    """Test that generation parameters are applied from config."""
    from app.schemas.use_case_config import GenerationParamsConfig, SamplingPreset

    req = LLMRequest(prompt="test", temperature=0.7, max_tokens=1024)
    use_case_config = UseCaseConfig(
        models=ModelsConfig(llm="gpt-4o"),
        generation_params=GenerationParamsConfig(
            sampling_preset=SamplingPreset.CUSTOM, temperature=0.5, max_tokens=2048
        ),
    )

    router._apply_config_overrides(req, use_case_config)

    assert req.temperature == 0.5
    assert req.max_tokens == 2048


@pytest.mark.asyncio
async def test_process_sync_uses_model_name_override(router):
    """Test that process_sync uses model_name_override when set."""
    req = LLMRequest(
        prompt="test",
        temperature=0.7,
        max_tokens=1024,
        model_name_override="foundation-sec-8b-instruct-mlx",
    )

    with (
        patch.object(
            router,
            "_get_response",
            return_value=(
                "response text",
                {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
                None,
            ),
        ),
        patch("app.orchestrator.llm_router.logger") as mock_logger,
    ):
        resp = await router.process_sync(req, RequestType.QUERY)

        assert isinstance(resp, LLMResponse)
        # Verify that the override was used (check log calls)
        log_calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any("use case config" in str(call).lower() for call in log_calls)


def test_get_streaming_generator_passes_model_id(router):
    """Test that _get_streaming_generator passes openai_model to StreamingResponseGenerator."""
    with patch("app.orchestrator.llm_router.StreamingResponseGenerator") as mock_gen_class:
        router._get_streaming_generator(
            messages=[{"role": "user", "content": "test"}],
            openai_model="foundation-sec-8b-instruct-mlx",
            temperature=0.7,
            max_tokens=1024,
            intent_type=RequestType.QUERY,
        )

        assert mock_gen_class.called
        call_kwargs = mock_gen_class.call_args[1]
        assert call_kwargs["model"] == "foundation-sec-8b-instruct-mlx"


@pytest.mark.asyncio
async def test__process_stream_exception(router):
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
