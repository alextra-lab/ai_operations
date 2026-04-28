from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.orchestrator.app.db.models import Tool
from src.orchestrator.app.orchestrator.context import RequestContext
from src.orchestrator.app.orchestrator.llm_router import LLMRouter
from src.orchestrator.app.orchestrator.steps.execute_llm import ExecuteLLM
from src.orchestrator.app.schemas.llm import LLMRequest, LLMResponse, ModelType
from src.orchestrator.app.schemas.use_case_config import UseCaseConfig
from src.orchestrator.app.services.tool_executor import ToolExecutor


@pytest.fixture
def mock_router():
    return AsyncMock(spec=LLMRouter)


@pytest.fixture
def mock_tool_executor():
    executor = AsyncMock(spec=ToolExecutor)
    # Mock db attribute for _get_tool_definitions
    executor.db = MagicMock()
    return executor


@pytest.fixture
def context():
    return RequestContext(
        req_id="test-req",
        query_original="test query",
        query_sanitized="test query",
        llm_request=LLMRequest(prompt="test"),
        use_case=UseCaseConfig(
            id=uuid4(),
            name="Test Use Case",
            intent_type="QUERY",
            tools_allowlist=["tool-1"],
        ),
    )


@pytest.mark.asyncio
async def test_run_no_tools(mock_router, context):
    """Test execution without tools."""
    # Setup
    step = ExecuteLLM(router=mock_router)

    # Mock response
    mock_response = LLMResponse(
        response="Test response",
        model_used=ModelType.QUERY,
        tokens_used=10,
        processing_time=0.1,
    )
    mock_router.process.return_value = mock_response

    # Execute
    result_ctx = await step.run(context)

    # Verify
    assert result_ctx.llm_response == mock_response
    mock_router.process.assert_called_once()
    assert not result_ctx.llm_request.tools


@pytest.mark.asyncio
async def test_run_with_tools_no_calls(mock_router, mock_tool_executor, context):
    """Test execution with tools enabled but no tool calls."""
    # Setup
    step = ExecuteLLM(router=mock_router, tool_executor=mock_tool_executor)

    # Mock tool definition retrieval
    with patch.object(step, "_get_tool_definitions", new_callable=AsyncMock) as mock_get_tools:
        mock_get_tools.return_value = [{"type": "function", "function": {"name": "tool-1"}}]

        # Mock response
        mock_response = LLMResponse(
            response="Test response",
            model_used=ModelType.QUERY,
            tokens_used=10,
            processing_time=0.1,
        )
        mock_router.process.return_value = mock_response

        # Execute
        result_ctx = await step.run(context)

        # Verify
        assert result_ctx.llm_response == mock_response
        mock_get_tools.assert_called_once()
        call_args = mock_get_tools.call_args
        assert call_args[0][0] == ["tool-1"]  # First positional arg is tool_ids
        assert result_ctx.llm_request.tools is not None
        assert len(result_ctx.llm_request.tools) == 1


@pytest.mark.asyncio
async def test_run_tool_loop(mock_router, mock_tool_executor, context):
    """Test tool execution loop."""
    # Setup
    step = ExecuteLLM(router=mock_router, tool_executor=mock_tool_executor)

    # Create mock tool for database query
    mock_tool = MagicMock(spec=Tool)
    mock_tool.id = uuid4()
    mock_tool.tool_id = "tool-1"

    # Mock database query result
    mock_db_result = MagicMock()
    mock_db_result.scalars.return_value.first.return_value = mock_tool
    mock_tool_executor.db.execute.return_value = mock_db_result

    # Mock tool definitions
    with patch.object(step, "_get_tool_definitions", new_callable=AsyncMock) as mock_get_tools:
        mock_get_tools.return_value = [{"type": "function", "function": {"name": "tool-1"}}]

        # Mock responses for loop
        # Turn 1: Tool call
        tool_call_response = LLMResponse(
            response="",
            model_used=ModelType.QUERY,
            tokens_used=10,
            processing_time=0.1,
            tool_calls=[
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "tool-1", "arguments": '{"arg": "value"}'},
                }
            ],
        )

        # Turn 2: Final response
        final_response = LLMResponse(
            response="Final answer",
            model_used=ModelType.QUERY,
            tokens_used=20,
            processing_time=0.2,
        )

        mock_router.process.side_effect = [tool_call_response, final_response]

        # Mock tool execution
        mock_tool_executor.execute_tool.return_value = {"status": "ok"}

        # Execute
        result_ctx = await step.run(context)

        # Verify
        assert result_ctx.llm_response == final_response
        assert mock_router.process.call_count == 2
        mock_tool_executor.execute_tool.assert_called_once()

        # Verify messages updated with formatted content
        messages = result_ctx.llm_request.messages
        assert len(messages) >= 3  # User + Assistant(Call) + Tool(Result)
        assert messages[-2]["role"] == "assistant"
        assert messages[-2]["tool_calls"] is not None
        assert messages[-1]["role"] == "tool"
        # Content should be formatted by ToolResultProcessor
        assert "Tool: tool-1" in messages[-1]["content"]
        assert "Result:" in messages[-1]["content"]
        assert "status" in messages[-1]["content"]

        # Verify tool results tracked
        assert "tool_results" in result_ctx.extras
        assert len(result_ctx.extras["tool_results"]) == 1
        assert result_ctx.extras["tool_results"][0]["tool"] == "tool-1"
        assert result_ctx.extras["tool_results"][0]["status"] == "success"

        # Verify tool metadata in metrics
        assert "tool_metadata" in result_ctx.llm_metrics
        assert result_ctx.llm_metrics["tool_metadata"]["tool_call_count"] == 1
        assert result_ctx.llm_metrics["tool_metadata"]["tool_successes"] == 1


@pytest.mark.asyncio
async def test_max_turns_reached(mock_router, mock_tool_executor, context):
    """Test max turns limit."""
    step = ExecuteLLM(router=mock_router, tool_executor=mock_tool_executor)

    # Create mock tool for database query
    mock_tool = MagicMock(spec=Tool)
    mock_tool.id = uuid4()
    mock_tool.tool_id = "tool-1"

    # Mock database query result
    mock_db_result = MagicMock()
    mock_db_result.scalars.return_value.first.return_value = mock_tool
    mock_tool_executor.db.execute.return_value = mock_db_result

    with patch.object(step, "_get_tool_definitions", return_value=[{}]):
        # Always return tool call
        tool_call_response = LLMResponse(
            response="",
            model_used=ModelType.QUERY,
            tokens_used=10,
            processing_time=0.1,
            tool_calls=[{"id": "call_1", "function": {"name": "tool-1", "arguments": "{}"}}],
        )
        mock_router.process.return_value = tool_call_response
        mock_tool_executor.execute_tool.return_value = "result"

        result_ctx = await step.run(context)

        assert result_ctx.llm_response is None
        assert "max_tool_turns_reached" in result_ctx.llm_metrics.get("warnings", [])
        assert mock_router.process.call_count == 5


@pytest.mark.asyncio
async def test_streaming_bypass(mock_router, mock_tool_executor, context):
    """Test streaming bypasses tool loop."""
    step = ExecuteLLM(router=mock_router, streaming=True, tool_executor=mock_tool_executor)

    mock_stream = AsyncMock()
    mock_stream.__aiter__.return_value = iter([])
    mock_router.process.return_value = mock_stream

    result_ctx = await step.run(context)

    assert result_ctx.extras.get("llm_stream") == mock_stream
    assert result_ctx.llm_response is None
