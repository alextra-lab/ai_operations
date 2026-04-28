"""
Unit tests for FormatResponse pipeline step.

Tests response formatting, token usage recording, and error handling.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from src.orchestrator.app.orchestrator.context import RequestContext
from src.orchestrator.app.orchestrator.response_formatter import ResponseFormatter
from src.orchestrator.app.orchestrator.steps.format_response import FormatResponse
from src.orchestrator.app.schemas.intent import IntentResponse, RequestType
from src.orchestrator.app.schemas.llm import LLMResponse, ModelType
from src.orchestrator.app.schemas.response import FormattedResponse
from src.orchestrator.app.services.token_tracker import TokenTracker


@pytest.fixture
def mock_formatter():
    """Mock ResponseFormatter."""
    formatter = MagicMock(spec=ResponseFormatter)
    formatter.process.return_value = FormattedResponse(
        response="Test response",
        sources=[],
        confidence=0.85,
        suggested_actions={},
        request_id="test-req",
    )
    return formatter


@pytest.fixture
def mock_token_tracker():
    """Mock TokenTracker."""
    tracker = AsyncMock(spec=TokenTracker)
    tracker.record_usage = AsyncMock()
    return tracker


@pytest.fixture
def context_with_llm_response():
    """RequestContext with LLM response populated."""
    return RequestContext(
        req_id="test-req-1",
        user_id="user1",
        user_uuid=UUID("12345678-1234-5678-1234-567812345678"),
        query_original="test query",
        query_sanitized="test query",
        llm_response=LLMResponse(
            response="Test answer",
            model_used=ModelType.QUERY,
            tokens_used=100,
            processing_time=0.5,
            metadata={
                "prompt_tokens": 50,
                "completion_tokens": 50,
                "model_provider": "openai",
                "model_version": "gpt-4",
            },
        ),
        intent=IntentResponse(
            query="test query",
            detected_type=RequestType.QUERY,
            confidence=0.9,
            suggested_actions=[],
        ),
        request_type=RequestType.QUERY,
        sources=[],
        extras={},
    )


@pytest.fixture
def context_without_llm_response():
    """RequestContext without LLM response (streaming path)."""
    return RequestContext(
        req_id="test-req-2",
        user_id="user1",
        query_original="test query",
        query_sanitized="test query",
        llm_response=None,
        sources=[],
        extras={},
    )


@pytest.mark.asyncio
async def test_format_response_basic(mock_formatter, context_with_llm_response):
    """Test basic response formatting without token tracker."""
    step = FormatResponse(formatter=mock_formatter, token_tracker=None)

    result = await step.run(context_with_llm_response)

    # Verify formatter was called
    mock_formatter.process.assert_called_once()
    assert result.formatted is not None
    assert result.formatted.confidence == 0.85
    assert result.llm_metrics["confidence"] == 0.85
    assert result.llm_metrics["sources_count"] == 0


@pytest.mark.asyncio
async def test_format_response_with_token_tracking(
    mock_formatter, mock_token_tracker, context_with_llm_response
):
    """Test response formatting with token usage recording."""
    step = FormatResponse(formatter=mock_formatter, token_tracker=mock_token_tracker)

    result = await step.run(context_with_llm_response)

    # Verify formatter was called
    mock_formatter.process.assert_called_once()
    assert result.formatted is not None

    # Verify token tracker was called with correct parameters
    mock_token_tracker.record_usage.assert_called_once()
    call_args = mock_token_tracker.record_usage.call_args

    assert call_args.kwargs["run_id"] == "test-req-1"
    assert call_args.kwargs["user_id"] == context_with_llm_response.user_uuid
    assert call_args.kwargs["model_id"] == "QUERY"
    assert call_args.kwargs["tokens_in"] == 50
    assert call_args.kwargs["tokens_out"] == 50
    assert call_args.kwargs["request_id"] == "test-req-1"
    assert call_args.kwargs["model_provider"] == "openai"
    assert call_args.kwargs["model_version"] == "gpt-4"
    assert call_args.kwargs["intent_type"] == "QUERY"
    assert call_args.kwargs["request_type"] == "QUERY"
    assert call_args.kwargs["streaming_used"] is False
    assert call_args.kwargs["call_duration_ms"] == 500
    assert "confidence" in call_args.kwargs["metadata"]
    assert "sources_count" in call_args.kwargs["metadata"]


@pytest.mark.asyncio
async def test_format_response_without_user_uuid(
    mock_formatter, mock_token_tracker, context_with_llm_response
):
    """Test that token tracking is skipped when user_uuid is missing."""
    context_with_llm_response.user_uuid = None
    step = FormatResponse(formatter=mock_formatter, token_tracker=mock_token_tracker)

    result = await step.run(context_with_llm_response)

    # Verify formatter was called
    mock_formatter.process.assert_called_once()
    assert result.formatted is not None

    # Verify token tracker was NOT called
    mock_token_tracker.record_usage.assert_not_called()


@pytest.mark.asyncio
async def test_format_response_skips_streaming_path(
    mock_formatter, mock_token_tracker, context_without_llm_response
):
    """Test that step is skipped when llm_response is None (streaming path)."""
    step = FormatResponse(formatter=mock_formatter, token_tracker=mock_token_tracker)

    result = await step.run(context_without_llm_response)

    # Verify formatter was NOT called
    mock_formatter.process.assert_not_called()
    assert result.formatted is None
    assert result.llm_response is None


@pytest.mark.asyncio
async def test_format_response_token_tracking_failure_does_not_fail_request(
    mock_formatter, mock_token_tracker, context_with_llm_response
):
    """Test that token tracking failure doesn't fail the request."""
    # Make token tracker raise an exception
    mock_token_tracker.record_usage.side_effect = Exception("Database error")

    step = FormatResponse(formatter=mock_formatter, token_tracker=mock_token_tracker)

    result = await step.run(context_with_llm_response)

    # Verify formatter was still called and request succeeded
    mock_formatter.process.assert_called_once()
    assert result.formatted is not None
    assert result.formatted.confidence == 0.85


@pytest.mark.asyncio
async def test_format_response_with_use_case_name(
    mock_formatter, mock_token_tracker, context_with_llm_response
):
    """Test that use case name is extracted from context extras."""
    context_with_llm_response.extras["use_case_name"] = "Test Use Case"
    context_with_llm_response.use_case_id = UUID("87654321-4321-8765-4321-876543218765")

    step = FormatResponse(formatter=mock_formatter, token_tracker=mock_token_tracker)

    await step.run(context_with_llm_response)

    # Verify use case name was passed to token tracker
    call_args = mock_token_tracker.record_usage.call_args
    assert call_args.kwargs["use_case_name"] == "Test Use Case"
    assert call_args.kwargs["use_case_id"] == context_with_llm_response.use_case_id


@pytest.mark.asyncio
async def test_format_response_model_id_extraction(
    mock_formatter, mock_token_tracker, context_with_llm_response
):
    """Test that model_id is extracted correctly from model_used."""
    # Test with ModelType enum
    context_with_llm_response.llm_response.model_used = ModelType.SUMMARIZATION

    step = FormatResponse(formatter=mock_formatter, token_tracker=mock_token_tracker)

    await step.run(context_with_llm_response)

    call_args = mock_token_tracker.record_usage.call_args
    assert call_args.kwargs["model_id"] == "SUMMARIZATION"


@pytest.mark.asyncio
async def test_format_response_with_tool_citations(mock_formatter, context_with_llm_response):
    """Test that tool citations are added to context sources."""
    # Tool results must match the format expected by ToolResultProcessor
    context_with_llm_response.extras["tool_results"] = [
        {
            "tool": "test_tool",
            "status": "success",
            "result": {
                "sources": [
                    {
                        "url": "https://example.com",
                        "title": "Test Result",
                        "snippet": "Test content",
                    }
                ]
            },
        }
    ]

    step = FormatResponse(formatter=mock_formatter, token_tracker=None)

    await step.run(context_with_llm_response)

    # Verify formatter was called with tool citations in context_sources
    call_args = mock_formatter.process.call_args
    context_sources = call_args.kwargs["context_sources"]
    assert len(context_sources) == 1
    assert context_sources[0]["source_type"] == "tool"
    assert context_sources[0]["title"] == "Test Result"


@pytest.mark.asyncio
async def test_format_response_error_handling_fallback(mock_formatter, context_with_llm_response):
    """Test error handling with fallback formatting."""
    # Make formatter.process raise an exception
    mock_formatter.process.side_effect = Exception("Formatter error")
    mock_formatter.format_response.return_value = FormattedResponse(
        response="Fallback response",
        sources=[],
        confidence=0.0,
        suggested_actions={},
        request_id="test-req-1",
    )

    step = FormatResponse(formatter=mock_formatter, token_tracker=None)

    result = await step.run(context_with_llm_response)

    # Verify fallback was used
    assert result.formatted is not None
    assert result.formatted.response == "Fallback response"
    assert "format_response_error" in result.llm_metrics.get("fallbacks", [])


@pytest.mark.asyncio
async def test_format_response_error_handling_absolute_fallback(
    mock_formatter, context_with_llm_response
):
    """Test absolute fallback when both formatter methods fail."""
    # Make both formatter methods raise exceptions
    mock_formatter.process.side_effect = Exception("Formatter error")
    mock_formatter.format_response.side_effect = Exception("Fallback error")

    # Set llm_response.response to empty string to trigger absolute fallback message
    context_with_llm_response.llm_response.response = ""

    step = FormatResponse(formatter=mock_formatter, token_tracker=None)

    result = await step.run(context_with_llm_response)

    # Verify absolute fallback was used
    assert result.formatted is not None
    assert result.formatted.response == "I'm sorry, I couldn't format the response."
    assert result.formatted.confidence == 0.0
    assert "format_response_error" in result.llm_metrics.get("fallbacks", [])
