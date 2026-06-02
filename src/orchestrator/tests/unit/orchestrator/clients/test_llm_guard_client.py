"""
Unit tests for LLMGuardClient HTTP payload contract.

Regression guard for AIO-74: client was sending {"query": ...} but the
LLM-Guard service requires {"input_text": ...}.

Uses httpx.MockTransport to capture outgoing requests without any live HTTP.
"""

from __future__ import annotations

import json

import httpx
import pytest

from app.orchestrator.clients.llm_guard_client import LLMGuardClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_RESPONSE = {
    "sanitized_text": "hello world",
    "risk_score": 0.0,
    "modified": False,
    "details": {},
}


def make_mock_transport(
    captured: list[httpx.Request],
    response_body: dict,
    status_code: int = 200,
) -> httpx.MockTransport:
    """Return an httpx.MockTransport that captures the request and returns a fixed response."""

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(status_code, json=response_body)

    return httpx.MockTransport(handler)


def make_client(
    captured: list[httpx.Request],
    response_body: dict | None = None,
) -> LLMGuardClient:
    """Construct an LLMGuardClient backed by a mock transport."""
    transport = make_mock_transport(captured, response_body or VALID_RESPONSE)
    http_client = httpx.AsyncClient(transport=transport)
    return LLMGuardClient(base_url="http://test", http=http_client)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_payload_uses_input_text_key():
    """Correct payload key: JSON body must have 'input_text', not 'query'."""
    captured: list[httpx.Request] = []
    client = make_client(captured)

    await client.validate(
        query="what is the incident count?",
        context={},
        request_id="req-001",
    )

    assert len(captured) == 1
    body = json.loads(captured[0].content)
    assert "input_text" in body
    assert body["input_text"] == "what is the incident count?"


@pytest.mark.asyncio
async def test_payload_does_not_contain_query_key():
    """No 'query' key: the outgoing payload must NOT contain a 'query' field."""
    captured: list[httpx.Request] = []
    client = make_client(captured)

    await client.validate(
        query="show me open alerts",
        context={},
        request_id="req-002",
    )

    body = json.loads(captured[0].content)
    assert "query" not in body


@pytest.mark.asyncio
async def test_strict_mode_forwarded():
    """strict_mode is forwarded: payload must carry the value passed in."""
    captured: list[httpx.Request] = []
    client = make_client(captured)

    await client.validate(
        query="test query",
        context={},
        request_id="req-003",
        strict_mode=True,
    )

    body = json.loads(captured[0].content)
    assert "strict_mode" in body
    assert body["strict_mode"] is True


@pytest.mark.asyncio
async def test_strict_mode_defaults_false():
    """strict_mode defaults to False when not passed."""
    captured: list[httpx.Request] = []
    client = make_client(captured)

    await client.validate(
        query="test query",
        context={},
        request_id="req-004",
    )

    body = json.loads(captured[0].content)
    assert body["strict_mode"] is False


@pytest.mark.asyncio
async def test_context_values_stringified():
    """Non-string context values are serialized as strings in the outgoing payload."""
    captured: list[httpx.Request] = []
    client = make_client(captured)

    await client.validate(
        query="test query",
        context={"user_id": 42, "flag": True},
        request_id="req-005",
    )

    body = json.loads(captured[0].content)
    assert body["context"] == {"user_id": "42", "flag": "True"}


@pytest.mark.asyncio
async def test_empty_context_becomes_none():
    """When context={} is passed, the payload's 'context' field must be None."""
    captured: list[httpx.Request] = []
    client = make_client(captured)

    await client.validate(
        query="test query",
        context={},
        request_id="req-006",
    )

    body = json.loads(captured[0].content)
    assert body["context"] is None


@pytest.mark.asyncio
async def test_happy_path_round_trip():
    """Full request-response contract: correct outgoing payload and expected return keys."""
    service_response = {
        "sanitized_text": "cleaned query",
        "risk_score": 0.15,
        "modified": True,
        "details": {"scanner": "regex", "matched": ["pattern_1"]},
    }
    captured: list[httpx.Request] = []
    client = make_client(captured, response_body=service_response)

    result = await client.validate(
        query="original query",
        context={"role": "analyst"},
        request_id="req-007",
    )

    # Verify outgoing payload was well-formed
    body = json.loads(captured[0].content)
    assert body["input_text"] == "original query"
    assert body["context"] == {"role": "analyst"}
    assert "query" not in body

    # Verify response keys are returned as-is
    assert result["sanitized_text"] == "cleaned query"
    assert result["risk_score"] == 0.15
    assert result["modified"] is True
    assert "details" in result
