"""
Execute LLM Step (production-ready).

Extracted from controller.process() lines ~1035-1100 and ~1052-1300:
- Calls LLMRouter.process(llm_request, stream=bool, intent_type, use_case_config)
- Handles streaming vs non-streaming
- Captures token usage & model info into ctx.llm_metrics
- Handles Tool Execution loop (T3-F2)
- Enforces security-based tool restrictions (ADR-057)

Part of P4-F11 Layer 4 orchestrator refactoring (Pipeline+Steps pattern).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import and_
from sqlalchemy.future import select

from shared.logging_utils.fastapi import configure_logging

from ...db.models import Tool
from ...schemas.llm import LLMResponse
from ...schemas.tool import (
    DataFlowDirection,
    DataSourceType,
    MaxDataSensitivity,
    NetworkAccessLevel,
    ToolCategory,
    ToolListItem,
)
from ...services.tool_result_processor import ToolResultProcessor
from ..tool_validator import ToolValidator

if TYPE_CHECKING:
    from ...services.tool_executor import ToolExecutor
    from ..context import RequestContext
    from ..llm_router import LLMRouter

logger = configure_logging(service_name="execute_llm_step", log_level="INFO", log_format="json")


class ExecuteLLM:
    """
    LLM execution step.

    Executes the assembled LLM request using LLMRouter.
    Handles both streaming and non-streaming execution.
    Supports Tool Execution loop (LLM -> Tool -> Result -> LLM).
    """

    def __init__(
        self,
        router: LLMRouter,
        streaming: bool = False,
        tool_executor: ToolExecutor | None = None,
    ):
        """
        Initialize LLM execution step.

        Args:
            router: LLM router service
            streaming: Whether to use streaming execution
            tool_executor: Service for executing tools (optional)
        """
        self.router = router
        self.streaming = streaming
        self.tool_executor = tool_executor

    async def run(self, ctx: RequestContext) -> RequestContext:
        """
        Execute LLM request.

        Args:
            ctx: Request context with llm_request populated

        Returns:
            Updated context with llm_response (or stream in extras)
        """
        if not ctx.llm_request:
            logger.error("ExecuteLLM: ctx.llm_request is missing")
            ctx.llm_metrics.setdefault("errors", []).append("missing_llm_request")
            return ctx

        # Determine intent type from context
        intent_type = None
        if ctx.intent and hasattr(ctx.intent, "detected_type"):
            intent_type = ctx.intent.detected_type

        # Inject tools if enabled and allowlisted
        # ADR-057: Security restrictions are applied within _get_tool_definitions
        if self.tool_executor and ctx.use_case and ctx.use_case.tools_allowlist:
            tools = await self._get_tool_definitions(ctx.use_case.tools_allowlist, ctx)
            if tools:
                ctx.llm_request.tools = tools
                # Default to auto unless specified otherwise
                ctx.llm_request.tool_choice = "auto"
                logger.info(f"Injected {len(tools)} tools into LLM request")

        try:
            logger.info(
                "Executing LLM (stream=%s, intent=%s)",
                self.streaming,
                getattr(intent_type, "value", None),
            )

            # Initialize tool results tracking
            if "tool_results" not in ctx.extras:
                ctx.extras["tool_results"] = []

            # Tool execution loop (max 5 turns)
            max_turns = 5
            current_turn = 0

            while current_turn < max_turns:
                result = await self.router.process(
                    request=ctx.llm_request,
                    stream=self.streaming,
                    intent_type=intent_type,
                    use_case_config=ctx.use_case,
                )

                if self.streaming:
                    # Handle streaming response
                    # Note: Tool execution in streaming mode requires complex client-side handling
                    # or accumulating the stream here. For T3-F2, we assume tools are primarily
                    # used in non-streaming mode or the client handles the tool call chunks.
                    if not hasattr(result, "__aiter__"):
                        logger.error(
                            "LLMRouter.process returned non-stream for stream=True; ignoring"
                        )
                        ctx.llm_metrics.setdefault("errors", []).append("expected_stream_got_sync")
                        return ctx

                    ctx.extras["llm_stream"] = result
                    ctx.llm_response = None
                    logger.info("Streaming generator attached to context")
                    return ctx

                # Non-streaming path
                if not isinstance(result, LLMResponse):
                    logger.error(
                        "LLMRouter.process did not return LLMResponse for non-streaming path"
                    )
                    ctx.llm_metrics.setdefault("errors", []).append("expected_sync_got_stream")
                    return ctx

                # Check for tool calls
                if result.tool_calls:
                    logger.info(
                        f"Received {len(result.tool_calls)} tool calls (turn {current_turn + 1})"
                    )

                    # Execute tools and update messages
                    await self._handle_tool_calls(ctx, result)

                    current_turn += 1
                    continue  # Loop back to call LLM with results

                # Final response (no tool calls)
                ctx.llm_response = result
                self._record_metrics(ctx, result)

                # Add tool metadata to metrics if tools were used
                if ctx.extras.get("tool_results"):
                    tool_metadata = ToolResultProcessor.format_for_response(
                        ctx.extras["tool_results"]
                    )
                    ctx.llm_metrics["tool_metadata"] = tool_metadata

                return ctx

            logger.warning("Max tool execution turns reached")
            ctx.llm_metrics.setdefault("warnings", []).append("max_tool_turns_reached")
            return ctx

        except Exception as e:
            logger.exception("LLM execution failed: %s", e)
            ctx.llm_metrics.setdefault("errors", []).append("llm_execution_error")
            return ctx

    async def _get_tool_definitions(
        self,
        tool_ids: list[str],
        ctx: RequestContext | None = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve tool definitions for allowlisted tools.

        Applies both allowlist filtering and security restrictions (ADR-057).

        Args:
            tool_ids: List of allowed tool IDs
            ctx: Request context (optional, used for security restrictions)

        Returns:
            List of OpenAI-compatible tool definitions
        """
        if not self.tool_executor:
            return []

        try:
            # Query database for enabled tools in allowlist
            # Note: We need to handle UUID conversion if tool_ids are strings
            tools = []
            for tid in tool_ids:
                try:
                    # Try exact match (UUID or string ID)
                    # Assuming tool_id in allowlist matches Tool.tool_id (string) or Tool.id (UUID)
                    # Usually allowlist uses string IDs (e.g. "web-scraper")

                    # We need to query the DB. Since self.tool_executor has the session...
                    # But we should use the session carefully.
                    stmt = select(Tool).where(and_(Tool.tool_id == tid, Tool.is_enabled))
                    result = await self.tool_executor.db.execute(stmt)
                    tool = result.scalars().first()

                    if tool:
                        tools.append(tool)
                    else:
                        # Try UUID lookup just in case
                        try:
                            uuid_id = UUID(tid)
                            stmt = select(Tool).where(and_(Tool.id == uuid_id, Tool.is_enabled))
                            result = await self.tool_executor.db.execute(stmt)
                            tool = result.scalars().first()
                            if tool:
                                tools.append(tool)
                        except ValueError:
                            pass

                except Exception as e:
                    logger.warning(f"Error fetching tool {tid}: {e}")

            # ADR-057: Apply security restrictions if configured
            filtered_tools = tools
            if ctx and ctx.use_case and ctx.use_case.tool_restrictions:
                validator = ToolValidator()
                tool_list_items = [self._tool_to_list_item(t) for t in tools]
                allowed_items, rejected = validator.filter_tools_by_restrictions(
                    tool_list_items,
                    ctx.use_case.tool_restrictions,
                )

                if rejected:
                    logger.info(
                        "Security restrictions rejected %d tools: %s",
                        len(rejected),
                        [r[0] for r in rejected],
                    )

                # Map back to Tool objects
                allowed_ids = {item.tool_id for item in allowed_items}
                filtered_tools = [t for t in tools if t.tool_id in allowed_ids]

            # Convert to OpenAI format
            tool_definitions = []
            for tool in filtered_tools:
                definition = {
                    "type": "function",
                    "function": {
                        "name": tool.tool_id,
                        "description": tool.description or "",
                        "parameters": tool.parameters_schema or {},
                    },
                }
                tool_definitions.append(definition)

            return tool_definitions

        except Exception as e:
            logger.error(f"Failed to get tool definitions: {e}")
            return []

    def _tool_to_list_item(self, tool: Tool) -> ToolListItem:
        """Convert a Tool database model to ToolListItem for validation."""
        return ToolListItem(
            id=tool.id,
            tool_id=tool.tool_id,
            name=tool.name,
            description=tool.description,
            category=ToolCategory(tool.category),
            is_enabled=tool.is_enabled,
            is_healthy=tool.is_healthy,
            requires_authentication=tool.requires_authentication,
            data_source_type=DataSourceType(tool.data_source_type),
            data_flow_direction=DataFlowDirection(tool.data_flow_direction),
            network_access_level=NetworkAccessLevel(tool.network_access_level),
            max_data_sensitivity=MaxDataSensitivity(tool.max_data_sensitivity),
        )

    async def _handle_tool_calls(self, ctx: RequestContext, result: LLMResponse) -> None:
        """
        Execute tool calls and update context messages.

        Uses ToolResultProcessor to format results for LLM context.

        Args:
            ctx: Request context
            result: LLM response containing tool calls
        """
        if not result.tool_calls or not ctx.llm_request:
            return

        # 1. Add assistant message with tool calls to history
        assistant_msg = {
            "role": "assistant",
            "content": result.response,
            "tool_calls": result.tool_calls,
        }

        # Ensure messages list exists
        if not ctx.llm_request.messages:
            ctx.llm_request.messages = [{"role": "user", "content": ctx.llm_request.prompt}]

        ctx.llm_request.messages.append(assistant_msg)

        # 2. Execute each tool and collect normalized results
        normalized_results = []

        for tool_call in result.tool_calls:
            tool_name = tool_call["function"]["name"]
            tool_call_id = tool_call["id"]
            arguments_str = tool_call["function"]["arguments"]

            try:
                arguments = json.loads(arguments_str)
            except json.JSONDecodeError:
                arguments = {}
                logger.warning(f"Failed to parse arguments for tool {tool_name}")

            logger.info(f"Executing tool {tool_name} (call_id={tool_call_id})")

            start_time = datetime.now(UTC)
            exec_result: dict[str, Any] | None = None
            error: str | None = None

            if self.tool_executor:
                try:
                    # Find tool ID (UUID) from name
                    stmt = select(Tool).where(Tool.tool_id == tool_name)
                    db_result = await self.tool_executor.db.execute(stmt)
                    tool = db_result.scalars().first()

                    if tool:
                        # Execute tool
                        # Use user_roles for multi-role support (ADR-060), fallback to user_role for backward compatibility
                        user_roles_for_tool = (
                            ctx.user_roles
                            if ctx.user_roles
                            else ([ctx.user_role] if ctx.user_role else ["user"])
                        )
                        exec_result = await self.tool_executor.execute_tool(
                            tool_id=tool.id,
                            tool_name=tool_name,
                            parameters=arguments,
                            user_id=(
                                ctx.user_uuid if ctx.user_uuid else UUID(int=0)
                            ),  # Fallback if None
                            user_roles=user_roles_for_tool,  # Multi-role support per ADR-060
                            run_id=ctx.req_id,
                            use_case_id=ctx.use_case_id,
                        )
                    else:
                        error = f"Tool {tool_name} not found"

                except Exception as e:
                    error = str(e)
                    logger.error(f"Tool execution error: {e}")
            else:
                error = "Tool executor not available"

            # Calculate duration
            duration_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

            # Normalize result
            normalized_result = ToolResultProcessor.normalize_execution_result(
                tool_name=tool_name,
                exec_result=exec_result,
                error=error,
                duration_ms=duration_ms,
            )
            normalized_results.append(normalized_result)

            # Format result content for LLM message
            tool_result_content = ToolResultProcessor.format_for_llm([normalized_result])

            # 3. Add tool result message to history
            tool_msg = {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "name": tool_name,
                "content": tool_result_content,
            }
            ctx.llm_request.messages.append(tool_msg)

        # Store normalized results in context for response metadata
        if "tool_results" not in ctx.extras:
            ctx.extras["tool_results"] = []
        ctx.extras["tool_results"].extend(normalized_results)

    def _record_metrics(self, ctx: RequestContext, result: LLMResponse) -> None:
        """Record LLM execution metrics."""
        metadata = result.metadata or {}
        prompt_tokens = metadata.get("prompt_tokens", 0)
        completion_tokens = metadata.get("completion_tokens", 0)

        ctx.llm_metrics.update(
            {
                "model_used": getattr(result.model_used, "value", result.model_used),
                "tokens_used": result.tokens_used,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "processing_time_s": result.processing_time,
            }
        )
        logger.info(
            "LLM completed (model=%s, tokens=%s, time=%.3fs)",
            ctx.llm_metrics.get("model_used"),
            ctx.llm_metrics.get("tokens_used"),
            ctx.llm_metrics.get("processing_time_s", 0.0),
        )
