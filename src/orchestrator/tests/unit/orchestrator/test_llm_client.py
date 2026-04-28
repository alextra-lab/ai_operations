from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai.types.chat import ChatCompletion, ChatCompletionChunk


def make_real_llm_client():
    patch.stopall()
    from app.orchestrator.llm_client import LLMClient

    return LLMClient(api_key="test_openai_api_key_for_backend_tests")


def test_make_completion_request_success():
    llm_client = make_real_llm_client()
    mock_response = MagicMock(spec=ChatCompletion)
    llm_client.client.chat.completions.create = MagicMock(return_value=mock_response)
    result = llm_client.make_completion_request("model", ["msg"], 0.7, 10)
    assert result is mock_response


def test_make_completion_request_error():
    llm_client = make_real_llm_client()
    llm_client.client.chat.completions.create = MagicMock(side_effect=Exception("fail"))
    with patch("app.orchestrator.llm_client.logger") as mock_logger:
        with pytest.raises(Exception):
            llm_client.make_completion_request("model", ["msg"], 0.7, 10)
        assert mock_logger.error.called


@pytest.mark.asyncio
async def test_make_streaming_completion_request_success():
    llm_client = make_real_llm_client()
    chunk1 = MagicMock(spec=ChatCompletionChunk)
    chunk2 = MagicMock(spec=ChatCompletionChunk)

    async def fake_stream(*args, **kwargs):
        yield chunk1
        yield chunk2

    async_client_mock = MagicMock()
    async_client_mock.chat.completions.create = AsyncMock(return_value=fake_stream())
    llm_client.async_client = async_client_mock
    with patch("app.orchestrator.llm_client.logger") as mock_logger:
        results = [
            c async for c in llm_client.make_streaming_completion_request("model", ["msg"], 0.7, 10)
        ]
        assert chunk1 in results and chunk2 in results
        assert mock_logger.info.called


@pytest.mark.asyncio
async def test_make_streaming_completion_request_error():
    llm_client = make_real_llm_client()

    async def fake_stream(*args, **kwargs):
        raise Exception("fail")
        yield  # just to make it an async generator

    async_client_mock = MagicMock()
    async_client_mock.chat.completions.create = AsyncMock(return_value=fake_stream())
    llm_client.async_client = async_client_mock
    with patch("app.orchestrator.llm_client.logger") as mock_logger:
        with pytest.raises(Exception):
            async for _ in llm_client.make_streaming_completion_request("model", ["msg"], 0.7, 10):
                pass
        assert mock_logger.error.called
