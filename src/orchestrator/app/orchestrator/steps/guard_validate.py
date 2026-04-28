"""
Guard Validate Step.

Validates input with LLM-Guard service and applies policy rules.
Extracted from Orchestrator.validate_with_llm_guard()

Part of P4-F11 Layer 4 orchestrator refactoring (Pipeline+Steps pattern).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from shared.logging_utils.fastapi import configure_logging

if TYPE_CHECKING:
    from ..clients.llm_guard_client import LLMGuardClient
    from ..context import RequestContext
    from ..policy_engine import PolicyEngine

logger = configure_logging(service_name="guard_validate_step", log_level="INFO", log_format="json")


class GuardValidate:
    """
    LLM-Guard validation step.

    Validates user input for security threats using LLM-Guard service.
    Implements graceful degradation if service is unavailable.
    """

    def __init__(
        self,
        guard: LLMGuardClient,
        policy_engine: PolicyEngine | None = None,
        token: str | None = None,
        enabled: bool = True,
        strict_mode: bool = False,
    ):
        """
        Initialize Guard validation step.

        Args:
            guard: LLM-Guard client adapter
            policy_engine: Optional policy engine for additional checks
            token: Optional JWT token for Guard service auth
            enabled: Whether Guard validation is enabled
            strict_mode: Whether to use strict validation mode
        """
        self.guard = guard
        self.policy_engine = policy_engine
        self.token = token
        self.enabled = enabled
        self.strict_mode = strict_mode

    async def run(self, ctx: RequestContext) -> RequestContext:
        """
        Execute Guard validation step.

        Args:
            ctx: Request context

        Returns:
            Updated context with sanitized query and guard metrics
        """
        if not self.enabled:
            logger.info("LLM-Guard validation disabled, skipping")
            ctx.guard_metrics = {
                "status": "disabled",
                "message": "LLM-Guard validation is disabled",
            }
            return ctx

        logger.info("Validating input with LLM-Guard: length=%d", len(ctx.query_original))

        try:
            # Prepare context for Guard service
            guard_context = {
                "source": "orchestrator",
                "timestamp": str(datetime.now(UTC)),
                "user_id": ctx.user_id or "anonymous",
                **(ctx.extras.get("guard_context", {})),
            }

            # Call Guard service
            result = await self.guard.validate(
                query=ctx.query_original,
                context=guard_context,
                request_id=ctx.req_id,
                token=self.token,
            )

            # Extract results
            sanitized_text = result.get("sanitized_text", ctx.query_original)
            risk_score = result.get("risk_score", 0.0)
            modified = result.get("modified", False)
            details = result.get("details", {})

            # Update context
            if modified:
                ctx.query_sanitized = sanitized_text
                logger.info("Input modified by LLM-Guard")

            ctx.guard_metrics = {
                "risk_score": risk_score,
                "modified": modified,
                "details": details,
                "status": "success",
            }

            logger.info(
                "LLM-Guard validation complete: risk=%s, modified=%s",
                risk_score,
                modified,
            )

            return ctx

        except Exception as e:
            # Graceful degradation - don't fail the request
            logger.warning("LLM-Guard validation failed: %s, proceeding without validation", str(e))

            ctx.guard_metrics = {
                "status": "error",
                "error_type": type(e).__name__,
                "message": str(e),
                "graceful_degradation": True,
            }

            # Query remains unchanged
            return ctx
