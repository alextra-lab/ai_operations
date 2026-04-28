"""
Retrieval Client Adapter.

Thin HTTP adapter for Corpus/Retrieval service.
Moves network I/O out of controller for better testability.

Part of P4-F11 Layer 4 orchestrator refactoring (Pipeline+Steps pattern).
"""

from __future__ import annotations

from typing import Any

import httpx

from shared.logging_utils.fastapi import configure_logging

logger = configure_logging(service_name="retrieval_client", log_level="INFO", log_format="json")


class RetrievalClient:
    """
    Thin adapter around the Retrieval (Corpus) service.

    Responsibilities:
    - HTTP calls to retrieval service
    - Semantic search
    - Usage tracking
    - Request/response serialization

    Follows ADR-035: Service Boundary Clarification
    - Orchestrator calls corpus-service via HTTP (not direct imports)
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        http: httpx.AsyncClient | None = None,
    ):
        """
        Initialize Retrieval client.

        Args:
            base_url: Base URL of retrieval service
            timeout: Request timeout in seconds
            http: Optional pre-configured HTTP client
        """
        self.base_url = base_url.rstrip("/")
        self.http = http or httpx.AsyncClient(timeout=timeout)
        logger.info("RetrievalClient initialized")

    async def search(
        self,
        query: str,
        top_k: int,
        collection_names: list[str] | None = None,
        use_case_id: str | None = None,
        headers: dict[str, str] | None = None,
        min_relevancy_score: float | None = None,
    ) -> dict[str, Any]:
        """
        Execute semantic search.

        Args:
            query: Search query
            top_k: Number of results to return
            collection_names: Optional collection names to search
            use_case_id: Optional use case ID for context
            headers: Optional HTTP headers (e.g., auth)
            min_relevancy_score: Optional minimum relevancy score threshold

        Returns:
            Search results with keys:
            - results: list[dict] (retrieved chunks)
            - rag_confidence: float
            - search_metadata: dict

        Raises:
            httpx.HTTPError: If search request fails
        """
        request_headers = headers or {}
        request_headers["Content-Type"] = "application/json"

        payload = {"query_text": query, "top_k": top_k}

        if collection_names:
            payload["collection_names"] = collection_names

        if use_case_id:
            payload["use_case_id"] = use_case_id

        if min_relevancy_score is not None:
            payload["min_relevancy_score"] = min_relevancy_score

        try:
            response = await self.http.post(
                f"{self.base_url}/query/semantic-search",
                json=payload,
                headers=request_headers,
            )
            response.raise_for_status()
            result = response.json()

            results_count = len(result.get("results", []))
            logger.info(
                "Semantic search complete: results=%d, total_results=%s, confidence=%s",
                results_count,
                result.get("total_results"),
                result.get("rag_confidence", 0.0),
            )

            data: dict[str, Any] = result
            return data

        except httpx.HTTPError as e:
            logger.error("Semantic search failed: %s", type(e).__name__)
            raise

    async def record_usage(
        self,
        run_id: str,
        user_id: str | None,
        query_text: str,
        sources: list[dict[str, Any]],
        rag_confidence: float,
        headers: dict[str, str] | None = None,
    ) -> None:
        """
        Record retrieval usage for analytics.

        Args:
            run_id: Execution run ID
            user_id: User ID (if authenticated)
            query_text: Query that was executed
            sources: Retrieved sources
            rag_confidence: RAG confidence score
            headers: Optional HTTP headers

        Raises:
            httpx.HTTPError: If recording fails (logged but not raised)
        """
        request_headers = headers or {}
        request_headers["Content-Type"] = "application/json"

        payload = {
            "run_id": run_id,
            "user_id": user_id,
            "query_text": query_text,
            "sources": sources,
            "rag_confidence": rag_confidence,
        }

        try:
            response = await self.http.post(
                f"{self.base_url}/api/v1/analytics/usage",
                json=payload,
                headers=request_headers,
            )
            response.raise_for_status()

            logger.debug("Usage recorded: run_id=%s", run_id)

        except httpx.HTTPError as e:
            # Don't fail the request if usage recording fails
            logger.warning("Failed to record usage: %s", type(e).__name__)

    async def close(self) -> None:
        """Close HTTP client."""
        await self.http.aclose()
