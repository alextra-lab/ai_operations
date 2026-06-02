"""
Integration tests for GuardValidate → LLMGuardClient path.

Exercises the full path: GuardValidate.run() → LLMGuardClient.validate() → HTTP service.

Regression guard for AIO-74: the bug caused LLMGuardClient to send
{"query": ...} but LLM-Guard service requires {"input_text": ...}.
These tests prove the fix is in place — a valid request reaches the
service, gets a real response, and guard_metrics["status"] == "success".

Uses httpx.MockTransport so no live service is required.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch

import httpx
import pytest

from app.orchestrator.clients.llm_guard_client import LLMGuardClient
from app.orchestrator.context import RequestContext
from app.orchestrator.steps.guard_validate import GuardValidate

# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------

VALID_RESPONSE: dict[str, Any] = {
    "sanitized_text": "show me open P1 alerts",
    "risk_score": 0.0,
    "modified": False,
    "details": {},
}


def _make_client(handler) -> LLMGuardClient:
    """Wire an LLMGuardClient through a mock httpx transport."""
    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport)
    return LLMGuardClient(base_url="http://test", http=http_client)


def _minimal_ctx() -> RequestContext:
    """Build the smallest valid RequestContext."""
    return RequestContext(
        req_id="test-req-001",
        query_original="show me open P1 alerts",
        query_sanitized="show me open P1 alerts",
    )


# ---------------------------------------------------------------------------
# Test 1: Happy path — guard validates successfully
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_happy_path_guard_validates_successfully():
    """
    Full path: GuardValidate.run() → LLMGuardClient → mock HTTP service.

    The mock handler accepts any request that carries input_text and returns
    a 200 with a clean result.  guard_metrics["status"] must be "success".
    """

    def happy_handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert "input_text" in body, "payload must contain input_text (AIO-74 regression check)"
        return httpx.Response(200, json=VALID_RESPONSE)

    guard_client = _make_client(happy_handler)
    step = GuardValidate(guard=guard_client, enabled=True)
    ctx = _minimal_ctx()

    ctx = await step.run(ctx)

    assert ctx.guard_metrics["status"] == "success", (
        "expected status='success' but got status=%r — "
        "this would be 'error' if AIO-74 regression were present"
        % ctx.guard_metrics.get("status")
    )
    assert ctx.guard_metrics["risk_score"] == 0.0
    assert ctx.guard_metrics["modified"] is False


# ---------------------------------------------------------------------------
# Test 2: Known-bad input is flagged (high risk score, text redacted)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_known_bad_input_is_flagged():
    """
    When the guard service returns a high risk score and modified=True,
    GuardValidate must store those values in guard_metrics and update
    ctx.query_sanitized with the sanitized text.
    """
    pii_response: dict[str, Any] = {
        "sanitized_text": "REDACTED",
        "risk_score": 0.95,
        "modified": True,
        "details": {"reason": "pii_detected"},
    }

    def pii_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=pii_response)

    guard_client = _make_client(pii_handler)
    step = GuardValidate(guard=guard_client, enabled=True)
    ctx = _minimal_ctx()

    ctx = await step.run(ctx)

    assert ctx.guard_metrics["modified"] is True
    assert ctx.guard_metrics["risk_score"] == 0.95
    assert ctx.query_sanitized == "REDACTED", (
        "query_sanitized must be updated to the sanitized_text returned by the guard service"
    )
    assert ctx.guard_metrics["status"] == "success"


# ---------------------------------------------------------------------------
# Test 3: Regression assertion — old broken payload triggers 422 → "error"
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_old_broken_payload_yields_error_status():
    """
    Demonstrates the AIO-74 regression: if the client sends the OLD payload
    {"query": ..., "context": ...} instead of {"input_text": ...}, the
    service returns 422 and GuardValidate gracefully degrades to status="error".

    We simulate the pre-fix behaviour by patching LLMGuardClient.validate to
    send the broken payload, then confirm GuardValidate catches the resulting
    HTTP error and records status="error".
    """

    def strict_handler(request: httpx.Request) -> httpx.Response:
        """Reject requests that lack input_text — mirrors FastAPI validation."""
        body = json.loads(request.content)
        if "input_text" not in body:
            return httpx.Response(422, json={"detail": "input_text is required"})
        return httpx.Response(200, json=VALID_RESPONSE)

    guard_client = _make_client(strict_handler)
    step = GuardValidate(guard=guard_client, enabled=True)
    ctx = _minimal_ctx()

    # Patch LLMGuardClient.validate to send the old broken payload.
    # This simulates what the client did BEFORE the AIO-74 fix.
    async def _broken_validate(
        self_inner,
        query: str,
        context: dict,
        request_id: str,
        token: str | None = None,
        strict_mode: bool = False,
    ) -> dict:
        headers = {
            "X-Request-ID": request_id,
            "Content-Type": "application/json",
        }
        broken_payload = {
            "query": query,        # old, wrong key
            "context": context,    # missing input_text
        }
        response = await self_inner.http.post(
            f"{self_inner.base_url}/api/validate",
            json=broken_payload,
            headers=headers,
        )
        response.raise_for_status()  # will raise on 422
        result: dict = response.json()
        return result

    with patch.object(LLMGuardClient, "validate", _broken_validate):
        ctx = await step.run(ctx)

    assert ctx.guard_metrics["status"] == "error", (
        "expected status='error' for the old broken payload (AIO-74 regression), "
        "but got status=%r" % ctx.guard_metrics.get("status")
    )
    # Graceful degradation: the pipeline must not raise; the context is returned
    assert ctx.guard_metrics.get("graceful_degradation") is True
