"""
RecordHistory Pipeline Step.

NO-OP STUB for Core Edition (Stateless v1).
This step is ready for Plus Edition v2+ where conversation history
will be stored server-side with proper encryption and retention policies.

Part of P4-F11 Layer 4 orchestrator refactoring (Pipeline+Steps pattern).
References ADR-033 (Provider Interfaces - disabled for v1).

CRITICAL DISTINCTION - Two Separate Recording Mechanisms:
──────────────────────────────────────────────────────────

1. **Run Manifests (PII-free telemetry)**: ✅ ALREADY WORKING (NOT this step)
   - Purpose: Analytics, debugging, cost tracking WITHOUT storing user data
   - Handled by: TelemetryIntegration.finish_execution_capture()
   - Called by: UseCaseRunner.run() automatically after pipeline completes
   - Records to: run_manifests table (ADR-030 compliant)
   - Contains: Request metadata, performance metrics, model usage
   - Does NOT contain: User queries, responses, conversation content
   - Status: IMPLEMENTED and active in Core Edition v1

2. **Conversation History (stateful storage)**: 📋 THIS STEP (Plus Edition v2+ only)
   - Purpose: Store actual conversation content for multi-turn sessions
   - Would store: User queries, assistant responses, thread context
   - Records to: query_history + thread_messages tables
   - Contains: Full conversation content (PII-containing)
   - Status: DEFERRED to Plus Edition (blocked by ADR-030 stateless requirement)
   - Implementation pattern: Preserved from controller.py lines 1326-1379 below

Implementation blueprint preserved from controller (for Plus Edition):
- history_service.save_history() for query history with metrics/citations
- history_service.add_thread_message() for thread conversations
- Thread-safe error handling (don't fail request)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from shared.logging_utils.fastapi import configure_logging

if TYPE_CHECKING:
    from ..context import RequestContext

logger = configure_logging(service_name="record_history_step", log_level="INFO", log_format="json")


class RecordHistory:
    """
    RecordHistory pipeline step (NO-OP in Core Edition).

    Plus Edition v2+ Implementation Pattern (from existing controller):
    ───────────────────────────────────────────────────────────────────
    1. Save query history (HistoryService.save_history):
       history_service.save_history(
           run_id=ctx.req_id,
           user_id=ctx.user_uuid,
           query_text=ctx.query_sanitized,
           response_text=ctx.formatted.response,
           response_status="success",
           use_case_id=ctx.use_case.use_case_id if ctx.use_case else None,
           use_case_name=ctx.use_case.name if ctx.use_case else None,
           intent_type=ctx.intent.detected_type.value if ctx.intent else None,
           metrics={
               "guard_metrics": ctx.guard_metrics,
               "retrieval_metrics": ctx.retrieval_metrics,
               "llm_metrics": ctx.llm_metrics,
           },
           processing_time_ms=int(ctx.llm_metrics.get("processing_time_s", 0) * 1000),
           sources={"sources": [s.model_dump() for s in ctx.sources]} if ctx.sources else None,
           citations={"citations": ctx.formatted.sources} if ctx.formatted.sources else None,
       )

    2. Save thread messages if thread_id provided (HistoryService.add_thread_message):
       # User query
       history_service.add_thread_message(
           thread_id=ctx.thread_id,
           query_id=None,
           role="user",
           content=ctx.query_sanitized,
           token_count=compaction_service.count_tokens(ctx.query_sanitized),
       )
       # Assistant response
       history_service.add_thread_message(
           thread_id=ctx.thread_id,
           query_id=None,
           role="assistant",
           content=ctx.formatted.response,
           token_count=compaction_service.count_tokens(ctx.formatted.response),
           model_used=ctx.llm_response.model_used if ctx.llm_response else None,
       )

    See controller.py lines 1326-1379 for current implementation.

    Core Edition Behavior (ADR-030 Stateless):
    ───────────────────────────────────────────
    - No-op (returns context unchanged)
    - No conversation storage
    - No token tracking beyond run manifests
    - Client owns all session data

    See ADR-033 for HistoryProvider and provider interface design.
    """

    def __init__(
        self,
        history_service: Any | None = None,
        token_tracker: Any | None = None,
        enabled: bool = False,
    ):
        """
        Initialize RecordHistory step.

        Args:
            history_service: HistoryService instance (None in Core Edition)
            token_tracker: TokenTracker instance (None in Core Edition)
            enabled: Whether to record history (always False in Core Edition)
                     Will be controlled by EDITION env var in Plus Edition
        """
        self.history = history_service
        self.tokens = token_tracker
        self.enabled = enabled

        if enabled:
            logger.warning(
                "RecordHistory enabled but not implemented in Core Edition. "
                "This feature requires Plus Edition v2+ with HistoryProvider (ADR-033)."
            )
        else:
            logger.debug("RecordHistory step initialized (no-op in Core Edition)")

    async def run(self, ctx: RequestContext) -> RequestContext:
        """
        Execute RecordHistory step (no-op in Core Edition).

        Plus Edition v2+ would execute (controller pattern, lines 1326-1379):
        ──────────────────────────────────────────────────────────────────────
        try:
            # 1. Save query history
            self.history.save_history(
                run_id=ctx.req_id,
                user_id=ctx.user_uuid,
                query_text=ctx.query_sanitized,
                response_text=ctx.formatted.response,
                response_status="success",
                use_case_id=ctx.use_case.use_case_id if ctx.use_case else None,
                use_case_name=ctx.use_case.name if ctx.use_case else None,
                intent_type=ctx.intent.detected_type.value if ctx.intent else None,
                metrics={
                    "guard_metrics": ctx.guard_metrics,
                    "retrieval_metrics": ctx.retrieval_metrics,
                    "llm_metrics": ctx.llm_metrics,
                },
                processing_time_ms=int(ctx.llm_metrics.get("processing_time_s", 0) * 1000),
                sources={"sources": [s.model_dump() for s in ctx.sources]} if ctx.sources else None,
                citations={"citations": ctx.formatted.sources} if ctx.formatted.sources else None,
            )

            # 2. Save thread messages if thread_id provided
            if ctx.thread_id:
                from ...services.context_compaction_service import ContextCompactionService
                compaction_service = ContextCompactionService()

                # User query
                self.history.add_thread_message(
                    thread_id=ctx.thread_id,
                    query_id=None,
                    role="user",
                    content=ctx.query_sanitized,
                    token_count=compaction_service.count_tokens(ctx.query_sanitized),
                )

                # Assistant response
                self.history.add_thread_message(
                    thread_id=ctx.thread_id,
                    query_id=None,
                    role="assistant",
                    content=ctx.formatted.response,
                    token_count=compaction_service.count_tokens(ctx.formatted.response),
                    model_used=ctx.llm_response.model_used if ctx.llm_response else None,
                )

        except Exception as hist_err:
            logger.error("Failed to record history: %s", str(hist_err), exc_info=True)
            # Don't fail the request if history recording fails

        Args:
            ctx: Current request context

        Returns:
            Unchanged request context (no-op in Core Edition)
        """
        if self.enabled and (self.history or self.tokens):
            # In Plus Edition v2+, execute the pattern shown above
            logger.warning(
                "RecordHistory.run() called but not implemented (Plus Edition v2+ feature)",
                extra={
                    "request_id": ctx.req_id,
                    "has_history_service": self.history is not None,
                    "has_token_tracker": self.tokens is not None,
                },
            )
        else:
            logger.debug(
                "RecordHistory step skipped (Core Edition - ADR-030 stateless)",
                extra={"request_id": ctx.req_id},
            )

        # Return context unchanged (no-op)
        return ctx
