from unittest.mock import MagicMock, patch

import pytest
from app.orchestrator.streaming_response import StreamingResponseGenerator
from app.schemas.llm import LLMStreamResponse, ModelType


@pytest.mark.asyncio
async def test_iter_raises():
    gen = StreamingResponseGenerator(MagicMock(), "m", [], 0.7, 10)
    with pytest.raises(NotImplementedError):
        iter(gen)


@pytest.mark.asyncio
async def test_aiter_and_anext():
    client = MagicMock()
    chunk = MagicMock()
    chunk.choices = [MagicMock()]
    chunk.choices[0].delta.content = "abc"

    async def fake_stream(*args, **kwargs):
        yield chunk

    client.make_streaming_completion_request = fake_stream
    gen = StreamingResponseGenerator(client, "m", [], 0.7, 10)
    # __aiter__ returns self
    assert gen.__aiter__() is gen
    # __anext__ yields a chunk
    result = await gen.__anext__()
    assert isinstance(result, LLMStreamResponse)
    assert result.response == "abc"


@pytest.mark.asyncio
def test_get_model_type_branches():
    gen = StreamingResponseGenerator(
        MagicMock(), "m", [], 0.7, 10, metadata={"model_type": "QUERY"}
    )
    assert gen._get_model_type() == ModelType.QUERY
    gen.intent_type = "QUERY"
    assert gen._get_model_type() == ModelType.QUERY
    gen.intent_type = "notamodel"
    assert gen._get_model_type() == ModelType.QUERY
    gen = StreamingResponseGenerator(MagicMock(), "m", [], 0.7, 10, metadata={})
    assert gen._get_model_type() == ModelType.QUERY


@pytest.mark.asyncio
async def test_create_iterator_normal_and_empty():
    client = MagicMock()
    chunk = MagicMock()
    chunk.choices = [MagicMock()]
    chunk.choices[0].delta.content = ""

    async def fake_stream(*args, **kwargs):
        yield chunk

    client.make_streaming_completion_request = fake_stream
    gen = StreamingResponseGenerator(client, "m", [], 0.7, 10)
    # Should yield a final response with default message if empty
    results = []
    async for r in gen._create_iterator():
        results.append(r)
    assert any("The model did not generate any response." in r.response for r in results)


@pytest.mark.asyncio
async def test_create_iterator_exception():
    client = MagicMock()

    async def fake_stream(*args, **kwargs):
        raise Exception("fail")
        yield

    client.make_streaming_completion_request = fake_stream
    gen = StreamingResponseGenerator(client, "m", [], 0.7, 10)
    with patch("app.orchestrator.streaming_response.logger") as mock_logger:
        results = []
        with pytest.raises(Exception):
            async for r in gen._create_iterator():
                results.append(r)
        assert any("error" in r.response.lower() for r in results)
        assert mock_logger.error.called
