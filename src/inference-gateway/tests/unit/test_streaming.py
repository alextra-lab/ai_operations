"""
Unit tests for SSE streaming functionality.

Tests P1-T6: SSE Streaming Support
"""

import json
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.requests import ChatCompletionRequest, ChatMessage
from app.providers.base import ProviderConfig
from app.providers.openai_provider import OpenAIProvider


@pytest.mark.asyncio
async def test_stream_chat_completion_parses_sse_format():
    """Test that stream_chat_completion properly parses SSE format."""
    # Create provider
    config = ProviderConfig(
        id="12345678-1234-1234-1234-123456789abc",
        name="test-provider",
        provider_type="openai_compatible",
        base_url="https://test.api.com",
        api_key="test-key",
        timeout_seconds=30,
        is_enabled=True,
    )
    provider = OpenAIProvider(config)

    # Mock the httpx client stream method
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    # Simulate SSE lines
    sse_lines = [
        "data: "
        + json.dumps(
            {
                "id": "test-123",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "gpt-4o-mini",
                "choices": [{"index": 0, "delta": {"content": "Hello"}, "finish_reason": None}],
            }
        ),
        "",
        "data: "
        + json.dumps(
            {
                "id": "test-123",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "gpt-4o-mini",
                "choices": [{"index": 0, "delta": {"content": " world"}, "finish_reason": None}],
            }
        ),
        "",
        "data: [DONE]",
    ]

    async def mock_aiter_lines():
        for line in sse_lines:
            yield line

    mock_response.aiter_lines = mock_aiter_lines

    # Mock the stream context manager
    mock_stream = AsyncMock()
    mock_stream.__aenter__.return_value = mock_response
    mock_stream.__aexit__.return_value = None

    provider.client.stream = MagicMock(return_value=mock_stream)

    # Create request
    request = ChatCompletionRequest(
        model="gpt-4o-mini",
        messages=[ChatMessage(role="user", content="Hi")],
    )

    # Execute streaming
    chunks = []
    async for chunk in provider.stream_chat_completion(request, "test-req-123"):
        chunks.append(chunk)

    # Verify chunks
    assert len(chunks) == 2, "Should receive 2 chunks before [DONE]"

    # Verify first chunk
    assert chunks[0].id == "test-123"
    assert chunks[0].object == "chat.completion.chunk"
    assert chunks[0].model == "gpt-4o-mini"
    assert chunks[0].choices[0]["delta"]["content"] == "Hello"

    # Verify second chunk
    assert chunks[1].choices[0]["delta"]["content"] == " world"

    # Cleanup
    await provider.close()


@pytest.mark.asyncio
async def test_stream_chat_completion_handles_done_signal():
    """Test that streaming stops at [DONE] signal."""
    config = ProviderConfig(
        id="12345678-1234-1234-1234-123456789abc",
        name="test-provider",
        provider_type="openai_compatible",
        base_url="https://test.api.com",
        api_key="test-key",
        timeout_seconds=30,
        is_enabled=True,
    )
    provider = OpenAIProvider(config)

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    # SSE with [DONE] signal
    sse_lines = [
        "data: "
        + json.dumps(
            {
                "id": "test-123",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "gpt-4o-mini",
                "choices": [{"index": 0, "delta": {"content": "Hi"}, "finish_reason": None}],
            }
        ),
        "",
        "data: [DONE]",
        "",
        # This should not be processed
        "data: "
        + json.dumps(
            {
                "id": "test-123",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "gpt-4o-mini",
                "choices": [{"index": 0, "delta": {"content": "Extra"}, "finish_reason": None}],
            }
        ),
    ]

    async def mock_aiter_lines():
        for line in sse_lines:
            yield line

    mock_response.aiter_lines = mock_aiter_lines

    mock_stream = AsyncMock()
    mock_stream.__aenter__.return_value = mock_response
    mock_stream.__aexit__.return_value = None

    provider.client.stream = MagicMock(return_value=mock_stream)

    request = ChatCompletionRequest(
        model="gpt-4o-mini",
        messages=[ChatMessage(role="user", content="Hi")],
    )

    chunks = []
    async for chunk in provider.stream_chat_completion(request):
        chunks.append(chunk)

    # Should only get 1 chunk (before [DONE])
    assert len(chunks) == 1
    assert chunks[0].choices[0]["delta"]["content"] == "Hi"

    await provider.close()


@pytest.mark.asyncio
async def test_stream_chat_completion_skips_empty_lines():
    """Test that empty lines are properly skipped."""
    config = ProviderConfig(
        id="12345678-1234-1234-1234-123456789abc",
        name="test-provider",
        provider_type="openai_compatible",
        base_url="https://test.api.com",
        api_key="test-key",
        timeout_seconds=30,
        is_enabled=True,
    )
    provider = OpenAIProvider(config)

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    # SSE with many empty lines
    sse_lines = [
        "",
        "",
        "data: "
        + json.dumps(
            {
                "id": "test-123",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "gpt-4o-mini",
                "choices": [{"index": 0, "delta": {"content": "Test"}, "finish_reason": None}],
            }
        ),
        "",
        "",
        "",
        "data: [DONE]",
    ]

    async def mock_aiter_lines():
        for line in sse_lines:
            yield line

    mock_response.aiter_lines = mock_aiter_lines

    mock_stream = AsyncMock()
    mock_stream.__aenter__.return_value = mock_response
    mock_stream.__aexit__.return_value = None

    provider.client.stream = MagicMock(return_value=mock_stream)

    request = ChatCompletionRequest(
        model="gpt-4o-mini",
        messages=[ChatMessage(role="user", content="Hi")],
    )

    chunks = []
    async for chunk in provider.stream_chat_completion(request):
        chunks.append(chunk)

    assert len(chunks) == 1
    assert chunks[0].choices[0]["delta"]["content"] == "Test"

    await provider.close()


@pytest.mark.asyncio
async def test_stream_chat_completion_handles_malformed_json():
    """Test that malformed JSON chunks are logged and skipped."""
    config = ProviderConfig(
        id="12345678-1234-1234-1234-123456789abc",
        name="test-provider",
        provider_type="openai_compatible",
        base_url="https://test.api.com",
        api_key="test-key",
        timeout_seconds=30,
        is_enabled=True,
    )
    provider = OpenAIProvider(config)

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    # SSE with malformed JSON
    sse_lines = [
        "data: "
        + json.dumps(
            {
                "id": "test-123",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "gpt-4o-mini",
                "choices": [{"index": 0, "delta": {"content": "Good"}, "finish_reason": None}],
            }
        ),
        "",
        "data: {invalid json}",  # Malformed
        "",
        "data: "
        + json.dumps(
            {
                "id": "test-123",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "gpt-4o-mini",
                "choices": [{"index": 0, "delta": {"content": "Also good"}, "finish_reason": None}],
            }
        ),
        "",
        "data: [DONE]",
    ]

    async def mock_aiter_lines():
        for line in sse_lines:
            yield line

    mock_response.aiter_lines = mock_aiter_lines

    mock_stream = AsyncMock()
    mock_stream.__aenter__.return_value = mock_response
    mock_stream.__aexit__.return_value = None

    provider.client.stream = MagicMock(return_value=mock_stream)

    request = ChatCompletionRequest(
        model="gpt-4o-mini",
        messages=[ChatMessage(role="user", content="Hi")],
    )

    chunks = []
    async for chunk in provider.stream_chat_completion(request):
        chunks.append(chunk)

    # Should get 2 valid chunks (malformed one skipped)
    assert len(chunks) == 2
    assert chunks[0].choices[0]["delta"]["content"] == "Good"
    assert chunks[1].choices[0]["delta"]["content"] == "Also good"

    await provider.close()


@pytest.mark.asyncio
async def test_stream_chat_completion_propagates_request_id():
    """Test that request ID is properly propagated in headers."""
    config = ProviderConfig(
        id="12345678-1234-1234-1234-123456789abc",
        name="test-provider",
        provider_type="openai_compatible",
        base_url="https://test.api.com",
        api_key="test-key",
        timeout_seconds=30,
        is_enabled=True,
    )
    provider = OpenAIProvider(config)

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    sse_lines = ["data: [DONE]"]

    async def mock_aiter_lines():
        for line in sse_lines:
            yield line

    mock_response.aiter_lines = mock_aiter_lines

    mock_stream = AsyncMock()
    mock_stream.__aenter__.return_value = mock_response
    mock_stream.__aexit__.return_value = None

    provider.client.stream = MagicMock(return_value=mock_stream)

    request = ChatCompletionRequest(
        model="gpt-4o-mini",
        messages=[ChatMessage(role="user", content="Hi")],
    )

    request_id = "custom-request-id-123"

    # Execute (will iterate over empty generator)
    chunks = []
    async for chunk in provider.stream_chat_completion(request, request_id):
        chunks.append(chunk)

    # Verify stream was called with correct headers
    call_args = provider.client.stream.call_args
    assert call_args[1]["headers"]["X-Request-ID"] == request_id

    await provider.close()
