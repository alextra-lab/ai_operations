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
# Test 3: Service 422 → graceful degradation (AIO-74 regression guard)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_service_422_yields_graceful_degradation():
    """
    When the LLM-Guard service returns 422 — as it did on every call before
    AIO-74 was fixed, because the client sent {"query": ...} instead of
    {"input_text": ...} — GuardValidate must catch the resulting
    httpx.HTTPStatusError and degrade gracefully.

    We simulate the 422 at the transport level so the full real stack runs:
      GuardValidate.run()
        → LLMGuardClient.validate()  (real implementation)
          → httpx raises HTTPStatusError on raise_for_status()
        → GuardValidate catches Exception, sets status="error"

    Assertions:
    - guard_metrics["status"] == "error"  (not "success" — proves degradation)
    - guard_metrics["graceful_degradation"] == True
    - The pipeline does not raise (context is returned unchanged)
    """

    def always_422(request: httpx.Request) -> httpx.Response:
        """Unconditionally reject — mirrors the service behaviour when input_text is absent."""
        return httpx.Response(422, json={"detail": [{"msg": "field required", "loc": ["body", "input_text"]}]})

    guard_client = _make_client(always_422)
    step = GuardValidate(guard=guard_client, enabled=True)
    ctx = _minimal_ctx()

    ctx = await step.run(ctx)

    assert ctx.guard_metrics["status"] == "error", (
        "expected status='error' when service returns 422, "
        "but got status=%r — guard_metrics: %r" % (ctx.guard_metrics.get("status"), ctx.guard_metrics)
    )
    assert ctx.guard_metrics.get("graceful_degradation") is True, (
        "expected graceful_degradation=True in guard_metrics"
    )
