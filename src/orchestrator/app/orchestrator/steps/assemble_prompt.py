"""
Assemble Prompt Step (production-ready).

Controller parity: process() lines 967-1050
- PromptAssembler.assemble_prompt(template, variables)  (SYNC)
- Build PromptTemplate + variables from ctx
- Merge history + sources + prompts (system/developer/fewshots)
- Create LLMRequest with correct schema fields
- Record extra sampling params (top_p, frequency_penalty, presence_penalty) in metrics

Part of P4-F11 Layer 4 orchestrator refactoring (Pipeline+Steps pattern).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from shared.logging_utils.fastapi import configure_logging

from ...schemas.intent import RequestType
from ...schemas.llm import LLMRequest, ModelType
from ...schemas.prompt import PromptTemplate

if TYPE_CHECKING:
    from ..context import RequestContext
    from ..prompt_assembler import PromptAssembler

logger = configure_logging(service_name="assemble_prompt_step", log_level="INFO", log_format="json")


class AssemblePrompt:
    """
    Prompt assembly step.

    Assembles the final LLM request by combining:
    - Use case prompts (system, developer, fewshots)
    - Retrieved context sources
    - Conversation history
    - User query

    Delegates to PromptAssembler for template filling.
    """

    def __init__(self, assembler: PromptAssembler, default_params: dict[str, Any] | None = None):
        """
        Initialize prompt assembly step.

        Args:
            assembler: Prompt assembler service
            default_params: Default generation parameters if use case config absent
        """
        self.assembler = assembler
        # Default generation params when none provided by UseCaseConfig
        self.default_params = default_params or {"temperature": 0.2, "max_tokens": 1024}

    def _build_template_and_vars(
        self, ctx: RequestContext
    ) -> tuple[PromptTemplate, dict[str, Any]]:
        """
        Build a PromptTemplate and variables dict from the context.
        Includes: system_prompt, developer_prompt, context (sources), history, and the current user query.
        """
        # Build context string from retrieved sources (title + optional snippet)
        context_lines: list[str] = []
        for s in ctx.sources or []:
            title = s.title or "Untitled"
            snippet = ""
            meta = getattr(s, "metadata", {}) or {}
            if isinstance(meta, dict):
                snippet = meta.get("content") or meta.get("snippet") or ""
            if snippet:
                context_lines.append(f"- {title}: {snippet}")
            else:
                context_lines.append(f"- {title}")
        context_text = "\n".join(context_lines)

        # Render history as "Role: content" lines (deterministic, controller parity)
        history_msgs = ctx.history_messages or []
        if history_msgs:
            history_lines = [
                f"{(m.get('role') or 'user').capitalize()}: {m.get('content') or ''}"
                for m in history_msgs
            ]
            history_text = "\n".join(history_lines)
            logger.info(
                f"🔍 HISTORY INCLUDED IN PROMPT: {len(history_msgs)} messages, {len(history_text)} chars",
                extra={
                    "history_message_count": len(history_msgs),
                    "history_char_count": len(history_text),
                    "history_preview": (
                        history_text[:200] if len(history_text) > 200 else history_text
                    ),
                },
            )
        else:
            history_text = ""
            logger.info("⚠️ NO HISTORY: ctx.history_messages is empty")

        # Use-case prompts (validated shape)
        prompts = ctx.prompts or {}
        system_prompt = prompts.get("system_prompt", "")
        developer_prompt = prompts.get("developer_prompt", "")

        # Minimal dynamic template (controller pattern)
        template = PromptTemplate(
            template_id="dynamic/use_case",
            template=(
                "{system_prompt}\n"
                "{developer_prompt}\n"
                "Context:\n{context}\n\n"
                "{history}\n"
                "User: {query}\n"
            ),
            variables=[
                "system_prompt",
                "developer_prompt",
                "context",
                "history",
                "query",
            ],
        )

        variables = {
            "system_prompt": system_prompt,
            "developer_prompt": developer_prompt,
            "context": context_text,
            "history": history_text,
            "query": ctx.query_sanitized or ctx.query_original,
        }
        return template, variables

    def _determine_model_preference(self, ctx: RequestContext) -> ModelType | None:
        """Map Intent RequestType → ModelType (string enum parity)."""
        try:
            if ctx.intent and getattr(ctx.intent, "detected_type", None):
                # RequestType values are strings matching ModelType names in your schema
                return ModelType(
                    getattr(ctx.intent.detected_type, "value", ctx.intent.detected_type)
                )
        except Exception as e:
            logger.warning("Model preference mapping failed: %s", e)
        return None

    @staticmethod
    def _build_response_format(
        ctx: RequestContext,
    ) -> dict[str, Any] | None:
        """Build OpenAI ``response_format`` from output contract.

        Returns ``None`` when the contract does not require structured
        output, so the LLM generates free-form text as usual.
        """
        oc = getattr(ctx.use_case, "output_contract", None) if ctx.use_case else None
        if not oc:
            return None

        from ...schemas.use_case_config import OutputFormat

        if oc.format not in (
            OutputFormat.JSON,
            OutputFormat.STRUCTURED,
        ):
            return None

        # If an explicit JSON Schema is provided, use json_schema mode
        if oc.output_schema:
            rf: dict[str, Any] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "structured_response",
                    "schema": oc.output_schema,
                    "strict": True,
                },
            }
            logger.info(
                "response_format: json_schema mode (schema keys: %s)",
                list(oc.output_schema.get("properties", {}).keys()),
            )
            return rf

        # No schema — basic json_object mode
        logger.info("response_format: json_object mode (no schema)")
        return {"type": "json_object"}

    async def run(self, ctx: RequestContext) -> RequestContext:
        """
        Execute prompt assembly step.

        Args:
            ctx: Request context with use_case, prompts, sources, history

        Returns:
            Updated context with llm_request populated
        """
        try:
            prompts = ctx.prompts or {}

            # Strategy: If we have multi-role prompts, use them. Otherwise, use template-based prompt.
            # This matches legacy controller behavior (lines 914-920, 932-977, 999-1005)

            assembled_text: str = ""
            messages: list[dict[str, str]] | None = None
            template_id_used: str = "unknown"

            if prompts:
                # PATH A: Multi-role prompts available - build messages array
                # 1) Build template + variables for context/history assembly
                template, variables = self._build_template_and_vars(ctx)
                assembled_text = self.assembler.assemble_prompt(template, variables)
                template_id_used = template.template_id
                logger.info(
                    "Prompt assembled with multi-role prompts (template_id=%s)",
                    template_id_used,
                )
            else:
                # PATH B: No multi-role prompts - use template-based prompt (legacy parity)
                # This is what legacy controller does at line 918: prompt_assembler.get_prompt()
                from ...schemas.intent import IntentResponse
                from ...schemas.prompt import PromptRequest

                # Build minimal IntentResponse for template selection
                effective_request_type = ctx.request_type or RequestType.QUERY
                intent_resp = IntentResponse(
                    detected_type=effective_request_type,
                    explicit_type=effective_request_type,
                    inferred_type=effective_request_type,
                    query=ctx.query_sanitized or ctx.query_original,
                    confidence=0.8,  # Default confidence when no intent parsing
                    metadata={},
                )

                # Build context dict from sources
                context_dict = {}
                if ctx.sources:
                    context_dict["sources"] = [
                        {
                            "title": s.title,
                            "content": getattr(s, "metadata", {}).get("content", ""),
                            "score": getattr(s, "score", 0.0),
                        }
                        for s in ctx.sources
                    ]

                prompt_request = PromptRequest(intent=intent_resp, context=context_dict)
                prompt_response = await self.assembler.get_prompt(prompt_request)
                assembled_text = prompt_response.prompt
                template_id_used = prompt_response.template_id
                logger.info(
                    "Prompt assembled using template: %s (no multi-role prompts)",
                    template_id_used,
                )

            # 2) Messages construction (controller parity)
            if prompts:
                # PATH A: Use case with custom prompts
                # Start with existing history in OpenAI message shape if present
                # Note: Strip metadata/timestamp from cached messages (OpenAI format only needs role+content)
                messages = [
                    {"role": m.get("role", "user"), "content": m.get("content", "")}
                    for m in (ctx.history_messages or [])
                ]

                # Combine system + developer into a single system message
                sys_parts: list[str] = []
                if prompts.get("system_prompt"):
                    sys_parts.append(prompts["system_prompt"])
                if prompts.get("developer_prompt"):
                    sys_parts.append("\n\n[Developer Instructions]\n" + prompts["developer_prompt"])
                if sys_parts:
                    messages.append({"role": "system", "content": "\n\n".join(sys_parts)})

                # Few-shot examples (list of {user, assistant})
                for fs in prompts.get("fewshots") or []:
                    if isinstance(fs, dict) and "user" in fs and "assistant" in fs:
                        messages.append({"role": "user", "content": fs["user"]})
                        messages.append({"role": "assistant", "content": fs["assistant"]})

                # Current user turn
                messages.append(
                    {
                        "role": "user",
                        "content": ctx.query_sanitized or ctx.query_original,
                    }
                )

                logger.info(
                    "Messages built (total=%d, history=%d, fewshots=%d)",
                    len(messages),
                    len(ctx.history_messages or []),
                    len(prompts.get("fewshots") or []),
                )
            else:
                # PATH B: Generic conversation (no custom prompts)
                # Build messages array directly from history + new query
                # Note: Strip metadata/timestamp from cached messages (OpenAI format only needs role+content)
                messages = [
                    {"role": m.get("role", "user"), "content": m.get("content", "")}
                    for m in (ctx.history_messages or [])
                ]

                # Add new user query
                messages.append(
                    {
                        "role": "user",
                        "content": ctx.query_sanitized or ctx.query_original,
                    }
                )

                logger.info(
                    "Generic conversation messages built (total=%d, history=%d)",
                    len(messages),
                    len(ctx.history_messages or []),
                )

            # 3) Effective generation params (UseCaseConfig preset/overrides)
            effective = {
                "temperature": self.default_params.get("temperature", 0.2),
                "top_p": 0.95,
                "max_tokens": self.default_params.get("max_tokens", 1024),
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0,
                "max_tool_steps": None,
                "tool_step_timeout": 60,
            }
            try:
                if ctx.use_case and getattr(ctx.use_case, "generation_params", None):
                    gp = ctx.use_case.generation_params.get_effective_params()
                    effective.update(gp or {})
            except Exception as e:
                logger.warning("generation_params.get_effective_params() failed: %s", e)

            temperature = float(effective.get("temperature", 0.2))
            max_tokens = int(effective.get("max_tokens", 1024))

            # 4) Model preference from intent
            model_pref = self._determine_model_preference(ctx)

            # 4b) Use case model override (so execution always uses saved model)
            model_override = None
            if ctx.use_case and getattr(ctx.use_case, "models", None) and ctx.use_case.models.llm:
                model_override = ctx.use_case.models.llm
                logger.info(
                    "AssemblePrompt: using model from use case config: %s",
                    model_override,
                )

            # 4c) Build response_format from output_contract (D5 / ADR-063)
            # Tells the LLM to produce JSON when the use case requires it.
            response_format = self._build_response_format(ctx)

            # 5) Create LLMRequest
            ctx.llm_request = LLMRequest(
                prompt=assembled_text if not messages else "",
                messages=messages,
                model_preference=model_pref,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=None,
                tool_choice=None,
                model_name_override=model_override,
                response_format=response_format,
            )

            # Record additional sampling params in metrics (for telemetry/observability)
            ctx.llm_metrics.update(
                {
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "top_p": float(effective.get("top_p", 0.95)),
                    "frequency_penalty": float(effective.get("frequency_penalty", 0.0)),
                    "presence_penalty": float(effective.get("presence_penalty", 0.0)),
                    "max_tool_steps": effective.get("max_tool_steps"),
                    "tool_step_timeout": effective.get("tool_step_timeout"),
                    "model_preference": (
                        getattr(model_pref, "value", None) if model_pref else None
                    ),
                    "template_id": template_id_used,
                }
            )

            return ctx

        except Exception as e:
            logger.exception("AssemblePrompt failed: %s", e)
            # Fail-soft: provide a minimal prompt so downstream can still run
            fallback = (ctx.query_sanitized or ctx.query_original or "").strip()
            fallback_override = None
            if ctx.use_case and getattr(ctx.use_case, "models", None) and ctx.use_case.models.llm:
                fallback_override = ctx.use_case.models.llm
            ctx.llm_request = LLMRequest(
                prompt=fallback,
                messages=None,
                model_preference=None,
                temperature=0.2,
                max_tokens=1024,
                tools=None,
                tool_choice=None,
                model_name_override=fallback_override,
                response_format=self._build_response_format(ctx),
            )
            ctx.llm_metrics.setdefault("fallbacks", []).append("assemble_prompt_error")
            return ctx
