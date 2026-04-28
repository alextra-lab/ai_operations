from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from app.orchestrator.controller import Orchestrator
from app.schemas.intent import RequestType


def make_orchestrator(config: dict | None = None) -> Orchestrator:
    from app.orchestrator.llm_router import LLMRouter

    base_config: dict = {
        "inference_gateway_url": "http://inference-gateway-test:8002",
    }
    if config:
        base_config.update(config)

    llm_router = LLMRouter(
        user_jwt_token="test_openai_api_key_for_backend_tests",
        gateway_url=base_config["inference_gateway_url"],
    )
    # Create mock async session for PromptAssembler
    async_db = AsyncMock()
    return Orchestrator(async_db=async_db, config=base_config, llm_router=llm_router)


def test_get_top_k_for_intent():
    orch = make_orchestrator()
    assert orch._get_top_k_for_intent(RequestType.QUERY) == 5
    assert orch._get_top_k_for_intent(RequestType.SUMMARIZATION) == 8
    assert orch._get_top_k_for_intent(RequestType.ENRICHMENT) == 3
    assert orch._get_top_k_for_intent(RequestType.RULE_GENERATION) == 4

    class Dummy:
        value = "other"

    assert orch._get_top_k_for_intent(Dummy()) == 5


def test_get_fallback_context():
    orch = make_orchestrator()
    ctx = orch._get_fallback_context("q", RequestType.QUERY, "err")
    assert ctx["sources"] == []
    assert ctx["metadata"]["error"] == "err"
    assert ctx["metadata"]["intent_type"] == RequestType.QUERY.value


def test_create_error_response():
    orch = make_orchestrator()
    resp = orch._create_error_response("fail", "reqid")
    assert resp.response.startswith("An error occurred: fail")
    assert resp.request_id == "reqid"
    assert resp.confidence == 0.0
    assert "retry" in resp.suggested_actions


@pytest.mark.asyncio
async def test_validate_with_llm_guard_success():
    orch = make_orchestrator({"llm_guard_url": "http://fake"})
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "sanitized_text": "cleaned",
        "risk_score": 0.1,
        "modified": True,
        "details": {"foo": "bar"},
    }
    mock_response.raise_for_status.return_value = None
    mock_client = MagicMock()
    mock_client.__aenter__.return_value.post.return_value = mock_response
    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await orch.validate_with_llm_guard(
            "dirty", user_id="u", request_id="r", context={"x": 1}
        )
        assert result[0] == "cleaned"
        assert result[1] == 0.1
        assert result[2] is True
        assert result[3]["foo"] == "bar"


@pytest.mark.asyncio
async def test_validate_with_llm_guard_http_error():
    """Test that LLM-Guard HTTP errors are handled gracefully with safe defaults."""
    orch = make_orchestrator({"llm_guard_url": "http://fake"})
    mock_client = MagicMock()
    mock_client.__aenter__.return_value.post.side_effect = httpx.HTTPStatusError(
        "fail", request=MagicMock(), response=MagicMock()
    )
    with patch("httpx.AsyncClient", return_value=mock_client):
        # Should NOT raise exception - graceful degradation
        sanitized, risk_score, modified, details = await orch.validate_with_llm_guard("dirty")

        # Verify safe defaults returned
        assert sanitized == "dirty"  # Original text unchanged
        assert risk_score == 0.0  # Safe default
        assert modified is False  # Not modified
        assert details["status"] == "error"
        assert details["error_type"] == "http_error"
        assert details["graceful_degradation"] is True


@pytest.mark.asyncio
async def test_validate_with_llm_guard_request_error():
    """Test that LLM-Guard connection errors are handled gracefully with safe defaults."""
    orch = make_orchestrator({"llm_guard_url": "http://fake"})
    mock_client = MagicMock()
    mock_client.__aenter__.return_value.post.side_effect = httpx.RequestError(
        "fail", request=MagicMock()
    )
    with patch("httpx.AsyncClient", return_value=mock_client):
        # Should NOT raise exception - graceful degradation
        sanitized, risk_score, modified, details = await orch.validate_with_llm_guard("dirty")

        # Verify safe defaults returned
        assert sanitized == "dirty"  # Original text unchanged
        assert risk_score == 0.0  # Safe default
        assert modified is False  # Not modified
        assert details["status"] == "error"
        assert details["error_type"] == "connection_error"
        assert details["graceful_degradation"] is True


@pytest.mark.asyncio
async def test_validate_with_llm_guard_unexpected_error():
    """Test that LLM-Guard unexpected errors are handled gracefully with safe defaults."""
    orch = make_orchestrator({"llm_guard_url": "http://fake"})
    mock_client = MagicMock()
    mock_client.__aenter__.return_value.post.side_effect = Exception("fail")
    with patch("httpx.AsyncClient", return_value=mock_client):
        # Should NOT raise exception - graceful degradation
        sanitized, risk_score, modified, details = await orch.validate_with_llm_guard("dirty")

        # Verify safe defaults returned
        assert sanitized == "dirty"  # Original text unchanged
        assert risk_score == 0.0  # Safe default
        assert modified is False  # Not modified
        assert details["status"] == "error"
        assert "graceful_degradation" in details
        assert details["graceful_degradation"] is True


@pytest.mark.asyncio
async def test_retrieve_context_success():
    orch = make_orchestrator({"retrieval_svc_url": "http://fake"})
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {
                "document_id": "doc1",
                "document_title": "t",
                "text_snippet": "s",
                "score": 0.9,
                "metadata": {},
            }
        ]
    }
    mock_response.raise_for_status.return_value = None
    mock_client = MagicMock()
    mock_client.__aenter__.return_value.post.return_value = mock_response
    with patch("httpx.AsyncClient", return_value=mock_client):
        ctx = await orch.retrieve_context("q", RequestType.QUERY, request_id="r")
        assert ctx["sources"][0]["document_id"] == "doc1"
        assert ctx["metadata"]["retrieval_method"] == "semantic_search"


@pytest.mark.asyncio
async def test_retrieve_context_http_error():
    orch = make_orchestrator({"retrieval_svc_url": "http://fake"})
    mock_client = MagicMock()
    mock_client.__aenter__.return_value.post.side_effect = httpx.HTTPStatusError(
        "fail", request=MagicMock(), response=MagicMock()
    )
    with patch("httpx.AsyncClient", return_value=mock_client):
        ctx = await orch.retrieve_context("q", RequestType.QUERY, request_id="r")
        assert ctx["metadata"]["retrieval_method"] == "fallback"
        assert "HTTP error" in ctx["metadata"]["error"]


@pytest.mark.asyncio
async def test_retrieve_context_request_error():
    orch = make_orchestrator({"retrieval_svc_url": "http://fake"})
    mock_client = MagicMock()
    mock_client.__aenter__.return_value.post.side_effect = httpx.RequestError(
        "fail", request=MagicMock()
    )
    with patch("httpx.AsyncClient", return_value=mock_client):
        ctx = await orch.retrieve_context("q", RequestType.QUERY, request_id="r")
        assert ctx["metadata"]["retrieval_method"] == "fallback"
        assert "Request error" in ctx["metadata"]["error"]


@pytest.mark.asyncio
async def test_retrieve_context_unexpected_error():
    orch = make_orchestrator({"retrieval_svc_url": "http://fake"})
    mock_client = MagicMock()
    mock_client.__aenter__.return_value.post.side_effect = Exception("fail")
    with patch("httpx.AsyncClient", return_value=mock_client):
        ctx = await orch.retrieve_context("q", RequestType.QUERY, request_id="r")
        assert ctx["metadata"]["retrieval_method"] == "fallback"
        assert "Unexpected error" in ctx["metadata"]["error"]


@pytest.mark.asyncio
async def test_record_retrieval_success():
    orch = make_orchestrator({"retrieval_svc_url": "http://fake"})
    mock_response = MagicMock()
    mock_response.json.return_value = {"ok": True}
    mock_response.raise_for_status.return_value = None
    mock_client = MagicMock()
    mock_client.__aenter__.return_value.post.return_value = mock_response
    with patch("httpx.AsyncClient", return_value=mock_client):
        # Should not raise
        await orch.record_retrieval("doc", [], "u", "q", [], {}, "runid")


@pytest.mark.asyncio
async def test_record_retrieval_http_error():
    orch = make_orchestrator({"retrieval_svc_url": "http://fake"})
    mock_client = MagicMock()
    mock_client.__aenter__.return_value.post.side_effect = httpx.HTTPStatusError(
        "fail", request=MagicMock(), response=MagicMock()
    )
    with patch("httpx.AsyncClient", return_value=mock_client):
        # Should not raise
        await orch.record_retrieval("doc", [], "u", "q", [], {}, "runid")


@pytest.mark.asyncio
async def test_record_retrieval_unexpected_error():
    orch = make_orchestrator({"retrieval_svc_url": "http://fake"})
    mock_client = MagicMock()
    mock_client.__aenter__.return_value.post.side_effect = Exception("fail")
    with patch("httpx.AsyncClient", return_value=mock_client):
        # Should not raise
        await orch.record_retrieval("doc", [], "u", "q", [], {}, "runid")
