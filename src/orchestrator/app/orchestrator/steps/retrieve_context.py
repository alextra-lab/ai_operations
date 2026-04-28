"""
Retrieve Context Step (production-ready).

Aligned with controller.retrieve_context() lines 459-602:
- Honors RAG enablement in UseCaseConfig
- Extracts structured query fields
- Calls RetrievalClient.search(query, top_k, collection_ids, use_case_id, headers)
- Transforms results into RequestContext.sources (RetrievalSource)
- Populates ctx.retrieval_metrics and ctx.rag_enabled
- Graceful HTTP and unexpected error handling

Part of P4-F11 Layer 4 orchestrator refactoring (Pipeline+Steps pattern).
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from shared.logging_utils.fastapi import configure_logging

from ..context import RequestContext, RetrievalSource

if TYPE_CHECKING:
    from ..clients.retrieval_client import RetrievalClient

logger = configure_logging(
    service_name="retrieve_context_step", log_level="INFO", log_format="json"
)


class RetrieveContext:
    """
    Context retrieval step using RAG.

    Retrieves relevant document chunks from corpus-service to provide
    context for LLM execution. Implements graceful degradation.
    """

    def __init__(
        self,
        retrieval: RetrievalClient,
        headers: dict[str, str] | None = None,
        use_case_id: str | None = None,
        default_top_k: int = 8,
    ):
        """
        Initialize retrieval step.

        Args:
            retrieval: Retrieval client adapter
            headers: Optional HTTP headers for auth
            use_case_id: Optional use case ID
            default_top_k: Default number of results if not in config
        """
        self.retrieval = retrieval
        self.headers = headers
        self.use_case_id = use_case_id
        self.default_top_k = default_top_k

    def _extract_search_query(self, query: str) -> str:
        """
        Extract an effective search query from a possibly structured input.

        Supports simple "Field: Value" multi-line inputs by concatenating values.

        Args:
            query: The raw query string (may contain field labels)

        Returns:
            Extracted search query text
        """
        if not query:
            return ""

        if ":" in query and "\n" in query:
            values: list[str] = []
            for line in query.splitlines():
                parts = line.split(":", 1)
                if len(parts) == 2:
                    value = parts[1].strip()
                    if value and len(value) > 3:
                        values.append(value)
            if values:
                extracted = " ".join(values)
                logger.debug("Extracted structured search query: %s", extracted)
                return extracted

        return query

    def _resolve_top_k(self, ctx: RequestContext) -> int:
        """Resolve top_k from use case config or use default."""
        try:
            if ctx.use_case and ctx.use_case.rag and ctx.use_case.rag.top_k:
                return int(ctx.use_case.rag.top_k)
        except Exception:
            pass
        return self.default_top_k

    async def run(self, ctx: RequestContext) -> RequestContext:
        """
        Execute context retrieval step.

        Args:
            ctx: Request context

        Returns:
            Updated context with retrieved sources and metrics
        """
        # Respect RAG enablement
        if ctx.use_case and getattr(ctx.use_case, "rag", None) and not ctx.use_case.rag.enabled:
            logger.info("RAG disabled in use case config; skipping retrieval")
            ctx.rag_enabled = False
            ctx.retrieval_metrics = {
                "retrieval_time": 0.0,
                "total_sources": 0,
                "rag_enabled": False,
            }
            ctx.sources = []
            return ctx

        search_query = self._extract_search_query(ctx.query_sanitized or ctx.query_original)
        top_k = self._resolve_top_k(ctx)
        collection_names: list[str] | None = None
        similarity_threshold: float | None = None
        try:
            if ctx.use_case and getattr(ctx.use_case, "rag", None):
                # Read list of collection names from use case RAG config
                collection_names = getattr(ctx.use_case.rag, "vector_collections", None)
                # Read similarity threshold from use case RAG config
                similarity_threshold = getattr(ctx.use_case.rag, "similarity_threshold", None)
        except Exception:
            collection_names = None
            similarity_threshold = None

        start = time.time()
        try:
            result = await self.retrieval.search(
                query=search_query,
                top_k=top_k,
                collection_names=collection_names,
                use_case_id=self.use_case_id,
                headers=self.headers,
                min_relevancy_score=similarity_threshold,
            )

            # Transform results into RetrievalSource list
            sources: list[RetrievalSource] = []
            for item in result.get("results", []):
                # Merge chunk_metadata and document_metadata from corpus service
                merged_metadata = {
                    "content": item.get("text_snippet") or item.get("full_text") or "",
                    "relevance_score": item.get("score"),
                    **(item.get("chunk_metadata") or {}),
                    **(item.get("document_metadata") or {}),
                }

                sources.append(
                    RetrievalSource(
                        document_id=item.get("document_id"),
                        title=item.get("document_title") or item.get("title") or "Unknown Document",
                        chunk_id=item.get("chunk_id"),
                        score=item.get("score"),
                        url=item.get("url"),
                        metadata=merged_metadata,
                    )
                )

            elapsed = time.time() - start
            ctx.sources = sources
            ctx.rag_enabled = True
            ctx.retrieval_metrics = {
                "retrieval_time": elapsed,
                "intent_type": getattr(getattr(ctx.intent, "detected_type", None), "value", None),
                "query": ctx.query_original,
                "sources_found": len(sources),
                "retrieval_method": "semantic_search",
                "top_k": top_k,
            }
            logger.info("Retrieved %d sources in %.3fs", len(sources), elapsed)
            return ctx

        except Exception as e:
            # Preserve graceful degradation as in controller: return empty context with error info
            logger.error("Retrieval failed: %s", e)
            ctx.sources = []
            ctx.rag_enabled = False
            ctx.retrieval_metrics = {
                "retrieval_time": 0.0,
                "intent_type": getattr(getattr(ctx.intent, "detected_type", None), "value", None),
                "query": ctx.query_original,
                "sources_found": 0,
                "retrieval_method": "semantic_search",
                "error": str(e),
            }
            return ctx
