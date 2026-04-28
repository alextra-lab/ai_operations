"""
Unit tests for EmbeddingServiceClient.

Tests verify:
1. Provider-specific endpoint is used when provider is specified
2. OpenAI-compatible endpoint is used when provider is None
3. Request payloads are correctly formatted
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.corpus_svc.app.clients.embedding_client import (
    EmbeddingObject,
    EmbeddingServiceClient,
)


@pytest.fixture
def mock_session():
    """Create a mock aiohttp session."""
    session = AsyncMock()
    response = AsyncMock()
    response.status = 200
    response.ok = True
    response.json = AsyncMock(
        return_value={
            "data": [
                {"embedding": [0.1, 0.2, 0.3], "index": 0},
                {"embedding": [0.4, 0.5, 0.6], "index": 1},
            ],
            "model": "test-model",
            "usage": {"prompt_tokens": 10, "total_tokens": 10},
        }
    )
    response.raise_for_status = AsyncMock(return_value=None)
    response.text = AsyncMock(return_value="")
    session.post = AsyncMock(return_value=response)
    return session


@pytest.fixture
def embedding_client():
    """Create an EmbeddingServiceClient instance."""
    return EmbeddingServiceClient(
        base_url="http://test-embedding-service:8001",
        token="test-token",
    )


@pytest.mark.asyncio
async def test_embed_texts_with_provider_uses_provider_endpoint(mock_session, embedding_client):
    """Test that provider-specific endpoint is used when provider is specified."""
    # Provider endpoint returns {"vectors": [[...], ...], "usage": {...}}
    provider_response = {
        "vectors": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
        "usage": {"prompt_tokens": 10, "total_tokens": 10},
    }
    mock_session.post.return_value.json = AsyncMock(return_value=provider_response)

    with patch.object(embedding_client, "_get_session", return_value=mock_session):
        results = await embedding_client.embed_texts(
            texts=["test text"],
            model="text-embedding-3-small",
            provider="openai",
        )

        # Verify provider-specific endpoint was called
        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        assert "/embed/provider/openai" in call_args[0][0]

        # Verify payload format
        payload = call_args[1]["json"]
        assert payload["texts"] == ["test text"]
        assert payload["model"] == "text-embedding-3-small"

        # Verify results
        assert len(results) == 2
        assert isinstance(results[0], EmbeddingObject)


@pytest.mark.asyncio
async def test_embed_texts_without_provider_uses_openai_endpoint(mock_session, embedding_client):
    """Test that OpenAI-compatible endpoint is used when provider is None."""
    response_data = {
        "data": [
            {"embedding": [0.1, 0.2, 0.3], "index": 0},
        ],
        "model": "test-model",
        "usage": {"prompt_tokens": 5, "total_tokens": 5},
    }
    mock_session.post.return_value.json = AsyncMock(return_value=response_data)

    with patch.object(embedding_client, "_get_session", return_value=mock_session):
        results = await embedding_client.embed_texts(
            texts=["test text"],
            model="text-embedding-3-small",
            provider=None,
        )

        # Verify OpenAI-compatible endpoint was called
        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        assert "/v1/embeddings" in call_args[0][0]

        # Verify payload format (OpenAI-compatible)
        payload = call_args[1]["json"]
        assert payload["input"] == ["test text"]
        assert payload["model"] == "text-embedding-3-small"

        # Verify results
        assert len(results) == 1
        assert isinstance(results[0], EmbeddingObject)


@pytest.mark.asyncio
async def test_embed_texts_provider_endpoint_response_format(mock_session, embedding_client):
    """Test that provider-specific endpoint response is correctly parsed."""
    # Provider endpoint returns {"vectors": [[...], ...], "usage": {...}}
    provider_response = {
        "vectors": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
        "usage": {"prompt_tokens": 10, "total_tokens": 10},
    }
    mock_session.post.return_value.json = AsyncMock(return_value=provider_response)

    with patch.object(embedding_client, "_get_session", return_value=mock_session):
        results = await embedding_client.embed_texts(
            texts=["text1", "text2"],
            provider="openai",
        )

        # Verify results parsed correctly
        assert len(results) == 2
        assert results[0].embedding == [0.1, 0.2, 0.3]
        assert results[1].embedding == [0.4, 0.5, 0.6]
        assert results[0].index == 0
        assert results[1].index == 1


@pytest.mark.asyncio
async def test_embed_texts_handles_auth_errors(mock_session, embedding_client):
    """Test that authentication errors are properly raised."""
    from src.corpus_svc.app.clients.embedding_client import EmbeddingAuthenticationError

    response_401 = AsyncMock()
    response_401.status = 401
    response_401.text = AsyncMock(return_value="Unauthorized")
    mock_session.post.return_value = response_401

    with (
        patch.object(embedding_client, "_get_session", return_value=mock_session),
        pytest.raises(EmbeddingAuthenticationError),
    ):
        await embedding_client.embed_texts(
            texts=["test"],
            provider="openai",
        )
