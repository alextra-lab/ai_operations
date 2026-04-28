"""
Format Response Step (production-ready).

Extracted from controller.process() lines 1187-1264 and 1302-1334 (non-streaming format path).
- Converts LLMResponse → formatted output
- Calls ResponseFormatter.process(...)
- Attaches consolidated metrics and citations

Part of P4-F11 Layer 4 orchestrator refactoring (Pipeline+Steps pattern).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from shared.logging_utils.fastapi import configure_logging

from ...schemas.response import FormattedResponse
from ...services.tool_result_processor import ToolResultProcessor

if TYPE_CHECKING:
    from ...schemas.response import ConsolidatedMetrics
    from ...services.token_tracker import TokenTracker
    from ..context import RequestContext
    from ..response_formatter import ResponseFormatter

logger = configure_logging(service_name="format_response_step", log_level="INFO", log_format="json")


class FormatResponse:
    """
    Response formatting step.

    Formats the LLM response into the final structured output.
    Adds citations, confidence scores, and metadata.
    Also records token usage for analytics.
    """

    def __init__(self, formatter: ResponseFormatter, token_tracker: TokenTracker | None = None):
        """
        Initialize response formatting step.

        Args:
            formatter: Response formatter service
            token_tracker: Optional token tracker for recording usage
        """
        self.formatter = formatter
        self.token_tracker = token_tracker

    async def run(self, ctx: RequestContext) -> RequestContext:
        """
        Execute response formatting step.

        Args:
            ctx: Request context with llm_response populated

        Returns:
            Updated context with formatted response
        """
        # Skip for streaming (API layer will stream chunks via router)
        if ctx.llm_response is None:
            logger.info("FormatResponse skipped: no LLMResponse on context (likely streaming path)")
            return ctx

        try:
            # Collect metrics references
            retrieval_attempted = bool(ctx.sources) or bool(ctx.retrieval_metrics)

            # Build context sources from retrieval sources
            context_sources = []
            logger.info(f"FormatResponse: ctx.sources has {len(ctx.sources)} sources")
            for s in ctx.sources:
                meta = s.metadata if s.metadata else {}

                # Extract all fields needed by response_formatter._convert_context_sources
                # The corpus service returns enriched metadata in the metadata dict
                source_dict = {
                    "document_id": s.document_id,
                    "title": s.title,
                    "chunk_id": getattr(s, "chunk_id", None),
                    "score": s.score,
                    "relevance_score": s.score,
                    "url": getattr(s, "url", None),
                    "content": meta.get("content", ""),
                    "snippet": meta.get("content", ""),
                    "text_snippet": meta.get("content", ""),
                    # Extract metadata fields to top level for response_formatter
                    "chunk_index": meta.get("chunk_index", 0),
                    "source_type": meta.get("source", "Document Library"),
                    "metadata": meta,  # Pass through all metadata from corpus service
                }
                context_sources.append(source_dict)

            # Extract tool citations if tools were used
            if ctx.extras.get("tool_results"):
                tool_citations = ToolResultProcessor.extract_citations_from_tools(
                    ctx.extras["tool_results"]
                )
                # Convert tool citations to context source format
                for citation in tool_citations:
                    context_sources.append(
                        {
                            "document_id": citation.get("url", ""),
                            "title": citation.get(
                                "title", citation.get("tool_name", "Tool Result")
                            ),
                            "source_type": citation.get("source_type", "tool"),
                            "relevance_score": 1.0,  # Tool results are always relevant
                            "content": citation.get("snippet", ""),
                            "metadata": {
                                "tool_name": citation.get("tool_name"),
                                "url": citation.get("url"),
                            },
                        }
                    )
                logger.info(f"Added {len(tool_citations)} tool citations to sources")

            # Call ResponseFormatter.process (matches controller usage)
            formatted: FormattedResponse = await self.formatter.process(
                llm_response=ctx.llm_response,
                request_id=ctx.req_id,
                retrieval_metrics=ctx.retrieval_metrics or None,
                guard_metrics=ctx.guard_metrics or None,
                output_contract=(ctx.use_case.output_contract if ctx.use_case else None),
                context_sources=context_sources,
                retrieval_attempted=retrieval_attempted,
                guard_attempted=bool(ctx.guard_metrics),
            )

            # Attach to context
            ctx.formatted = formatted

            # Enrich llm_metrics with confidence and source count
            ctx.llm_metrics.update(
                {
                    "confidence": formatted.confidence,
                    "sources_count": len(formatted.sources or []),
                }
            )

            # Record token usage for analytics (if token_tracker is available)
            if self.token_tracker and ctx.llm_response and ctx.user_uuid:
                try:
                    metadata = ctx.llm_response.metadata or {}
                    prompt_tokens = metadata.get("prompt_tokens", 0)
                    completion_tokens = metadata.get("completion_tokens", 0)
                    model_used = getattr(ctx.llm_response, "model_used", None)

                    # Extract model_id safely
                    if model_used is None:
                        model_id = "unknown"
                    elif hasattr(model_used, "value"):
                        model_id = str(model_used.value)
                    else:
                        model_id = str(model_used)

                    processing_time_ms = int(
                        (ctx.llm_response.processing_time * 1000)
                        if hasattr(ctx.llm_response, "processing_time")
                        else 0
                    )

                    # Extract model provider from metadata if available
                    model_provider = metadata.get("model_provider")
                    model_version = metadata.get("model_version")

                    # Extract cost information from metadata if available
                    cost_per_1k_in = metadata.get("cost_per_1k_in")
                    cost_per_1k_out = metadata.get("cost_per_1k_out")

                    # Get use case name from context extras (set in use_cases.py router)
                    use_case_name = ctx.extras.get("use_case_name")

                    await self.token_tracker.record_usage(
                        run_id=ctx.req_id,
                        user_id=ctx.user_uuid,
                        model_id=model_id,
                        tokens_in=prompt_tokens,
                        tokens_out=completion_tokens,
                        request_id=ctx.req_id,
                        use_case_id=ctx.use_case_id,
                        use_case_name=use_case_name,
                        intent_type=(
                            ctx.intent.detected_type.value
                            if ctx.intent and hasattr(ctx.intent, "detected_type")
                            else None
                        ),
                        model_provider=model_provider,
                        model_version=model_version,
                        request_type=(ctx.request_type.value if ctx.request_type else None),
                        streaming_used=False,  # FormatResponse only handles non-streaming
                        call_duration_ms=processing_time_ms,
                        cost_per_1k_in=cost_per_1k_in,
                        cost_per_1k_out=cost_per_1k_out,
                        metadata={
                            "confidence": formatted.confidence,
                            "sources_count": len(formatted.sources or []),
                        },
                    )
                    logger.info(
                        "Recorded token usage: run_id=%s, model=%s, tokens=%d",
                        ctx.req_id,
                        model_id,
                        prompt_tokens + completion_tokens,
                    )
                except Exception as e:
                    # Don't fail the request if token tracking fails
                    logger.warning(
                        "Failed to record token usage: %s",
                        str(e),
                        exc_info=True,
                    )

            logger.info(
                "Response formatted successfully (confidence=%.3f)",
                formatted.confidence,
            )
            return ctx

        except Exception as e:
            logger.exception("Response formatting failed: %s", e)
            # Fail-soft: try alternative formatter method, preserving
            # LLM metrics so model_id / tokens are not lost.
            fallback_text = getattr(ctx.llm_response, "response", "") if ctx.llm_response else ""
            fallback_metrics = self._build_fallback_metrics(ctx)
            try:
                ctx.formatted = self.formatter.format_response(
                    text=fallback_text or "I'm sorry, I couldn't format the response.",
                    sources=[],
                    confidence=0.0,
                    suggested_actions={},
                    request_id=ctx.req_id,
                    metrics=fallback_metrics,
                )
            except Exception:
                # Absolute fallback: construct minimal FormattedResponse
                fallback_kwargs: dict = {
                    "response": fallback_text or "I'm sorry, I couldn't format the response.",
                    "sources": [],
                    "confidence": 0.0,
                    "suggested_actions": {},
                    "request_id": ctx.req_id,
                    "cache_stats": None,
                    "structured_data": None,
                }
                if fallback_metrics is not None:
                    fallback_kwargs["metrics"] = fallback_metrics
                ctx.formatted = FormattedResponse(**fallback_kwargs)
            ctx.llm_metrics.setdefault("fallbacks", []).append("format_response_error")
            return ctx

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_fallback_metrics(
        ctx: RequestContext,
    ) -> ConsolidatedMetrics | None:
        """Build ConsolidatedMetrics from ctx.llm_response when the
        main formatter.process() path fails (e.g. output-contract
        validation error).  Returns None when no LLM response exists.
        """
        from ...schemas.response import (
            ConsolidatedMetrics,
            GuardMetrics,
            ModelMetrics,
            RetrievalMetrics,
            ServiceStatus,
        )

        resp = ctx.llm_response
        if not resp:
            return None

        meta = resp.metadata or {}
        model_id = meta.get("model_id", str(resp.model_used))
        tokens_in = meta.get("prompt_tokens", 0)
        tokens_out = meta.get("completion_tokens", resp.tokens_used)

        return ConsolidatedMetrics(
            retrieval=RetrievalMetrics(
                top_k=0,
                hits=0,
                avg_similarity=0.0,
                min_similarity=0.0,
                max_similarity=0.0,
                source_count=0,
            ),
            guard=GuardMetrics(risk_score=0.0, modified=False, details={}),
            model=ModelMetrics(
                model_id=model_id,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                total_tokens=resp.tokens_used,
                processing_time=resp.processing_time,
                metadata=meta,
            ),
            confidence_score=0.0,
            service_status=ServiceStatus(
                retrieval_active=False,
                guard_active=False,
                model_active=True,
                embedding_active=False,
                retrieval_healthy=True,
                guard_healthy=True,
                model_healthy=True,
            ),
        )
