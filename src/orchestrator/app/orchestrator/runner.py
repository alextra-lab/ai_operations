"""
Use Case Runner - Manifest-Driven Pipeline Executor.

Executes orchestration pipeline using Step pattern.
Replaces monolithic controller.process() with composable steps.

Part of P4-F11 Layer 4 orchestrator refactoring (Pipeline+Steps pattern).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from shared.logging_utils.fastapi import configure_logging

from ..schemas.run_manifest import ResultKind

if TYPE_CHECKING:
    from ..services.telemetry_integration_service import TelemetryIntegration
    from .context import RequestContext

logger = configure_logging(service_name="usecase_runner", log_level="INFO", log_format="json")


class Step(Protocol):
    """
    Protocol for pipeline steps.

    Each step receives RequestContext, performs its operation,
    and returns updated context for the next step.
    """

    async def run(self, ctx: RequestContext) -> RequestContext:
        """
        Execute step logic.

        Args:
            ctx: Request context (input)

        Returns:
            Updated request context (output)
        """
        ...


class UseCaseRunner:
    """
    Manifest-driven pipeline executor.

    Coordinates execution of Steps in sequence, with telemetry integration.
    Follows functional pipeline pattern where each step transforms the context.

    Benefits:
    - Small, testable steps
    - Typed contracts (RequestContext)
    - Easy to add/remove/reorder steps
    - Consistent telemetry
    - Feature-flagged (safe rollback)
    """

    def __init__(self, steps: list[Step], telemetry: TelemetryIntegration):
        """
        Initialize runner with steps and telemetry.

        Args:
            steps: Ordered list of pipeline steps
            telemetry: Telemetry integration service
        """
        self.steps = steps
        self.telemetry = telemetry
        logger.info("UseCaseRunner initialized with %d steps", len(steps))

    async def run(self, ctx: RequestContext) -> Any:
        """
        Execute pipeline with telemetry.

        Args:
            ctx: Initial request context

        Returns:
            Formatted response (ctx.formatted)

        Raises:
            Exception: If any step fails
        """
        logger.info("Starting pipeline execution: req_id=%s", ctx.req_id)

        # Start telemetry capture (with initial params, will update after execution)
        try:
            # Extract what we know at pipeline start
            # Note: use_case_id is in ctx metadata, not ctx.use_case (which is UseCaseConfig)
            use_case_id = str(ctx.use_case_id) if ctx.use_case_id else "default"
            template_ver = "1.0"  # Template version tracked separately

            # Model info won't be known until after AssemblePrompt, use defaults
            model_name = ctx.request_type.value if ctx.request_type else "QUERY"
            model_version = "1.0"

            # Params from use_case if available, else defaults
            if ctx.use_case and hasattr(ctx.use_case, "generation_params"):
                gen_params = ctx.use_case.generation_params
                params = {
                    "temperature": gen_params.temperature if gen_params else 0.2,
                    "max_tokens": gen_params.max_tokens if gen_params else 1024,
                }
            else:
                params = {"temperature": 0.2, "max_tokens": 1024}

            self.telemetry.start_execution_capture(
                request_id=ctx.req_id,
                use_case_id=use_case_id,
                template_ver=template_ver,
                model_name=model_name,
                model_version=model_version,
                params=params,
            )
        except Exception as e:
            logger.warning("Failed to start telemetry: %s", str(e))

        try:
            # Execute steps in sequence
            for i, step in enumerate(self.steps):
                step_name = step.__class__.__name__
                logger.debug("Executing step %d/%d: %s", i + 1, len(self.steps), step_name)

                ctx = await step.run(ctx)

                logger.debug("Step %s complete", step_name)

            # Finish telemetry with success
            try:
                await self.telemetry.finish_execution_capture(
                    request_id=ctx.req_id, _result_kind=ResultKind.SUCCESS
                )
            except Exception as e:
                logger.warning("Failed to finish telemetry: %s", str(e))

            logger.info("Pipeline execution complete: req_id=%s", ctx.req_id)

            return ctx.formatted

        except Exception as e:
            logger.error(
                "Pipeline execution failed at step: %s",
                step.__class__.__name__ if "step" in locals() else "unknown",
            )

            # Record error in telemetry
            try:
                self.telemetry.record_error(ctx.req_id, str(e))
                await self.telemetry.finish_execution_capture(
                    request_id=ctx.req_id, _result_kind=ResultKind.ERROR
                )
            except Exception as telemetry_error:
                logger.warning("Failed to record error in telemetry: %s", str(telemetry_error))

            raise
