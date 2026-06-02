"""
LLM-Guard Client Adapter.

Thin HTTP adapter for LLM-Guard service.
Moves network I/O out of controller for better testability.

Part of P4-F11 Layer 4 orchestrator refactoring (Pipeline+Steps pattern).
"""

from __future__ import annotations

from typing import Any

import httpx

from shared.logging_utils.fastapi import configure_logging

logger = configure_logging(service_name="llm_guard_client", log_level="INFO", log_format="json")


class LLMGuardClient:
    """
    Thin adapter around the LLM-Guard service.

    Responsibilities:
    - HTTP calls to LLM-Guard service
    - Request/response serialization
    - Timeout and retry handling

    Moves network I/O out of controller to follow ports-and-adapters pattern.
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 10.0,
        http: httpx.AsyncClient | None = None,
    ):
        """
        Initialize LLM-Guard client.

        Args:
            base_url: Base URL of LLM-Guard service
            timeout: Request timeout in seconds
            http: Optional pre-configured HTTP client
        """
        self.base_url = base_url.rstrip("/")
        self.http = http or httpx.AsyncClient(timeout=timeout)
        logger.info("LLMGuardClient initialized")

    async def validate(
        self,
        query: str,
        context: dict[str, Any],
        request_id: str,
        token: str | None = None,
        strict_mode: bool = False,
    ) -> dict[str, Any]:
        """
        Validate query with LLM-Guard service.

        Args:
            query: User query to validate
            context: Request context for validation
            request_id: Request ID for tracing
            token: Optional JWT token for authentication
            strict_mode: Whether to use strict validation mode

        Returns:
            Validation result with keys:
            - sanitized_text: str (sanitized query text)
            - modified: bool (whether query was modified)
            - risk_score: float (risk score 0.0-1.0)
            - details: dict (validation details)

        Raises:
            httpx.HTTPError: If validation request fails
        """
        headers = {"X-Request-ID": request_id, "Content-Type": "application/json"}

        if token:
            headers["Authorization"] = f"Bearer {token}"

        payload = {
            "input_text": query,
            "context": {k: str(v) for k, v in context.items()},
            "strict_mode": strict_mode,
        }

        try:
            response = await self.http.post(
                f"{self.base_url}/api/validate", json=payload, headers=headers
            )
            response.raise_for_status()
            result = response.json()

            logger.debug(
                "LLM-Guard validation complete: modified=%s, risk_score=%s",
                result.get("modified", False),
                result.get("risk_score", 0.0),
            )

            data: dict[str, Any] = result
            return data

        except httpx.HTTPError as e:
            logger.error("LLM-Guard validation failed: %s", type(e).__name__)
            raise

    async def close(self) -> None:
        """Close HTTP client."""
        await self.http.aclose()
