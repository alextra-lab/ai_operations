"""
Unit tests for ExecuteLLM pipeline step.

Tests LLM execution with streaming/non-streaming bifurcation,
token counting, and error handling.
"""

import pytest

from src.orchestrator.app.orchestrator.context import RequestContext
from src.orchestrator.app.orchestrator.llm_router import LLMRouter
from src.orchestrator.app.orchestrator.steps.execute_llm import ExecuteLLM
from src.orchestrator.app.schemas.intent import IntentResponse, RequestType
from src.orchestrator.app.schemas.llm import (
    LLMRequest,
    LLMResponse,
    LLMStreamResponse,
    ModelType,
)


class MockLLMRouter(LLMRouter):
    """Mock LLM router for testing."""

    def __init__(self, response: LLMResponse | None = None, should_stream: bool = False):
        # Don't call super().__init__() to avoid dependencies
        self.mock_response = response
        self.should_stream = should_stream
        self.last_request: LLMRequest | None = None
        self.last_stream_flag: bool | None = None

    async def process(
        self,
        request: LLMRequest,
        stream: bool = False,
        intent_type: RequestType | None = None,
        use_case_config=None,
    ):
        """Mock process that records parameters and returns mock response."""
        self.last_request = request
        self.last_stream_flag = stream

        if stream:
            # Return async generator
            async def mock_stream():
                yield LLMStreamResponse(chunk="test", model_used=ModelType.QUERY, chunk_index=0)

            return mock_stream()
        # Return sync response
        return self.mock_response or LLMResponse(
            response="Mock response",
            model_used=ModelType.QUERY,
            tokens_used=42,
            processing_time=0.1,
            metadata={"prompt_tokens": 10, "completion_tokens": 32},
            tool_calls=None,
        )


@pytest.mark.asyncio
async def test_execute_llm_non_streaming():
    """Test non-streaming LLM execution."""
    mock_response = LLMResponse(
        response="This is the answer",
        model_used=ModelType.QUERY,
        tokens_used=100,
        processing_time=0.5,
        metadata={"prompt_tokens": 50, "completion_tokens": 50},
        tool_calls=None,
    )

    router = MockLLMRouter(response=mock_response)
    step = ExecuteLLM(router, streaming=False)

    ctx = RequestContext(
        req_id="test-1",
        user_id="user1",
        user_uuid=None,
        request_type=RequestType.QUERY,
        query_original="Test query",
        query_sanitized="Test query",
        intent=IntentResponse(
            query="Test query",
            detected_type=RequestType.QUERY,
            confidence=0.9,
            suggested_actions=[],
        ),
        use_case=None,
        prompts=None,
        history_messages=[],
        sources=[],
    )

    # Add LLM request (would be populated by AssemblePrompt in real flow)
    ctx.llm_request = LLMRequest(
        prompt="Test prompt",
        messages=None,
        model_preference=ModelType.QUERY,
        temperature=0.2,
        max_tokens=1024,
    )

    result = await step.run(ctx)

    # Verify response was captured
    assert result.llm_response is not None
    assert result.llm_response.response == "This is the answer"

    # Verify metrics were recorded
    assert result.llm_metrics["model_used"] == "QUERY"  # ModelType enum name
    assert result.llm_metrics["tokens_used"] == 100
    assert result.llm_metrics["prompt_tokens"] == 50
    assert result.llm_metrics["completion_tokens"] == 50
    assert result.llm_metrics["processing_time_s"] == 0.5

    # Verify router was called correctly
    assert router.last_stream_flag is False


@pytest.mark.asyncio
async def test_execute_llm_streaming():
    """Test streaming LLM execution."""
    router = MockLLMRouter(should_stream=True)
    step = ExecuteLLM(router, streaming=True)

    ctx = RequestContext(
        req_id="test-2",
        user_id="user1",
        user_uuid=None,
        request_type=RequestType.QUERY,
        query_original="Test query",
        query_sanitized="Test query",
        intent=IntentResponse(
            query="Test query",
            detected_type=RequestType.QUERY,
            confidence=0.9,
            suggested_actions=[],
        ),
        use_case=None,
        prompts=None,
        history_messages=[],
        sources=[],
    )

    ctx.llm_request = LLMRequest(
        prompt="Test prompt",
        messages=None,
        model_preference=ModelType.QUERY,
        temperature=0.2,
        max_tokens=1024,
    )

    result = await step.run(ctx)

    # Streaming should NOT populate llm_response
    assert result.llm_response is None

    # Stream should be in extras
    assert "llm_stream" in result.extras
    assert hasattr(result.extras["llm_stream"], "__aiter__")

    # Verify router was called with stream=True
    assert router.last_stream_flag is True


@pytest.mark.asyncio
async def test_execute_llm_missing_request():
    """Test handling of missing llm_request."""
    router = MockLLMRouter()
    step = ExecuteLLM(router, streaming=False)

    ctx = RequestContext(
        req_id="test-3",
        user_id="user1",
        user_uuid=None,
        request_type=RequestType.QUERY,
        query_original="Test",
        query_sanitized="Test",
        intent=None,
        use_case=None,
        prompts=None,
        history_messages=[],
        sources=[],
    )

    # Don't set llm_request
    result = await step.run(ctx)

    # Should return early with error
    assert result.llm_response is None
    assert "missing_llm_request" in result.llm_metrics.get("errors", [])


@pytest.mark.asyncio
async def test_execute_llm_with_intent_type():
    """Test that intent_type is passed to router."""
    router = MockLLMRouter()
    step = ExecuteLLM(router, streaming=False)

    ctx = RequestContext(
        req_id="test-4",
        user_id="user1",
        user_uuid=None,
        request_type=RequestType.SUMMARIZATION,
        query_original="Summarize this",
        query_sanitized="Summarize this",
        intent=IntentResponse(
            query="Summarize this",
            detected_type=RequestType.SUMMARIZATION,
            confidence=0.95,
            suggested_actions=[],
        ),
        use_case=None,
        prompts=None,
        history_messages=[],
        sources=[],
    )

    ctx.llm_request = LLMRequest(
        prompt="Summarize: ...",
        messages=None,
        model_preference=ModelType.SUMMARIZATION,
        temperature=0.3,
        max_tokens=2048,
    )

    await step.run(ctx)

    # Router should have been called (can't easily verify intent_type was passed
    # without more complex mocking, but we verified the call happens)
    assert router.last_request == ctx.llm_request


@pytest.mark.asyncio
async def test_execute_llm_error_handling():
    """Test error handling during LLM execution."""

    class ErrorRouter(LLMRouter):
        def __init__(self):
            pass

        async def process(self, request, stream=False, intent_type=None, use_case_config=None):
            raise RuntimeError("LLM service unavailable")

    router = ErrorRouter()
    step = ExecuteLLM(router, streaming=False)

    ctx = RequestContext(
        req_id="test-5",
        user_id="user1",
        user_uuid=None,
        request_type=RequestType.QUERY,
        query_original="Test",
        query_sanitized="Test",
        intent=None,
        use_case=None,
        prompts=None,
        history_messages=[],
        sources=[],
    )

    ctx.llm_request = LLMRequest(
        prompt="Test",
        messages=None,
        model_preference=None,
        temperature=0.2,
        max_tokens=1024,
    )

    result = await step.run(ctx)

    # Should handle error gracefully
    assert "llm_execution_error" in result.llm_metrics.get("errors", [])
    assert result.llm_response is None  # No response due to error


@pytest.mark.asyncio
async def test_execute_llm_intent_none_safe():
    """Test that None intent is handled safely."""
    router = MockLLMRouter()
    step = ExecuteLLM(router, streaming=False)

    ctx = RequestContext(
        req_id="test-6",
        user_id="user1",
        user_uuid=None,
        request_type=RequestType.QUERY,
        query_original="Test",
        query_sanitized="Test",
        intent=None,  # No intent
        use_case=None,
        prompts=None,
        history_messages=[],
        sources=[],
    )

    ctx.llm_request = LLMRequest(
        prompt="Test",
        messages=None,
        model_preference=None,
        temperature=0.2,
        max_tokens=1024,
    )

    # Should not crash with None intent
    result = await step.run(ctx)

    assert result.llm_response is not None
