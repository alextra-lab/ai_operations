"""Minimal stdlib HTTP client for ``POST /api/validate``.

Kept dependency-free (``urllib``) so the harness runs anywhere the service runs
without the model stack. Used by both the golden-capture CLI and the candidate
comparison path in the tests.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .corpus import Case


@dataclass
class Probe:
    """Result of a single ``/api/validate`` call."""

    status: int
    payload: dict
    latency_ms: float


def validate(
    base_url: str,
    case: Case,
    *,
    timeout: float = 60.0,
) -> Probe:
    """POST one case to ``{base_url}/api/validate`` and time the round trip."""
    body: dict[str, object] = {"input_text": case.text, "strict_mode": case.strict_mode}
    if case.context is not None:
        body["context"] = case.context

    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url=f"{base_url.rstrip('/')}/api/validate",
        data=data,
        headers={
            "Content-Type": "application/json",
            "X-Request-Id": f"parity-{case.id}",
        },
        method="POST",
    )

    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # trusted local URL
            raw = resp.read()
            status = resp.status
    except urllib.error.HTTPError as exc:  # surface the body for debugging
        raw = exc.read()
        status = exc.code
    latency_ms = (time.perf_counter() - start) * 1000.0

    try:
        payload = json.loads(raw.decode("utf-8")) if raw else {}
    except json.JSONDecodeError:
        payload = {"_raw": raw.decode("utf-8", "replace")}

    return Probe(status=status, payload=payload, latency_ms=latency_ms)


def health(base_url: str, *, timeout: float = 5.0) -> bool:
    """True if ``GET {base_url}/health`` returns 200."""
    req = urllib.request.Request(url=f"{base_url.rstrip('/')}/health", method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # trusted local URL
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError):
        return False
