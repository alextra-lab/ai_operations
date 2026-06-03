"""
Orchestrator router module.

This module defines the API endpoints for the orchestration functionality.
It provides a unified interface for processing requests through the orchestrator
pipeline, including intent parsing, LLM routing, and response formatting.
"""

import json
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import cast

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth.models import TokenPayload
from shared.config.schemas import OrchestratorConfig
from shared.logging_utils.fastapi import GENERIC_CLIENT_ERROR, configure_logging

from ..config.runtime import build_runtime_config
from ..db.database import get_async_db
from ..dependencies.config import get_orchestrator_settings

# --- Pipeline + Steps Architecture (ADR-036) ---
from ..orchestrator.clients.llm_guard_client import LLMGuardClient
from ..orchestrator.clients.retrieval_client import RetrievalClient
from ..orchestrator.context import RequestContext
from ..orchestrator.controller import Orchestrator
from ..orchestrator.runner import Step, UseCaseRunner
from ..orchestrator.steps.assemble_prompt import AssemblePrompt
from ..orchestrator.steps.execute_llm import ExecuteLLM
from ..orchestrator.steps.format_response import FormatResponse
from ..orchestrator.steps.guard_validate import GuardValidate
from ..orchestrator.steps.retrieve_context import RetrieveContext
from ..schemas.intent import RequestType
from ..schemas.response import FormattedResponse
from ..services.conversation_cache import get_conversation_cache
from ..services.model_metadata_inferencer import ModelMetadataInferencer
from ..services.model_registry_service import ModelRegistryService
from ..utils.auth import (
    get_current_user,
    jwt_validator,
)

# Configure logger for this router
logger = configure_logging(service_name="orchestrator_router", log_level="INFO", log_format="json")

# Create router with 'orchestrator' tag for OpenAPI grouping and API versioning
router = APIRouter(prefix="/api/v1", tags=["orchestrator"])


async def _calculate_cache_capacity(
    db: AsyncSession,
    model_id: str | None,
    max_output_tokens: int | None,
    system_overhead: int = 500,
) -> int:
    """
    Calculate cache capacity based on model's context window.

    Formula: Cache = Model Context Window - Max Output Tokens - System Overhead

    Args:
        db: Async database session for model lookup
        model_id: Model identifier (e.g., "gpt-4-turbo")
        max_output_tokens: User-configured max output tokens
        system_overhead: Tokens reserved for system prompts

    Returns:
        Cache capacity in tokens
    """
    default_context_window = 8000
    default_max_output = 2000

    # Default fallback
    if not model_id:
        return default_context_window - default_max_output - system_overhead

    try:
        # Try 1: Look up model from database registry
        model_service = ModelRegistryService(session=db)
        model_info = await model_service.get_model(model_id)

        if model_info and model_info.context_window:
            context_window = model_info.context_window
            max_output = max_output_tokens or model_info.max_output_tokens or default_max_output

            cache_capacity = context_window - max_output - system_overhead

            logger.debug(
                "Calculated cache capacity from database registry",
                extra={
                    "model_id": model_id,
                    "source": "database",
                    "context_window": context_window,
                    "max_output_tokens": max_output,
                    "cache_capacity": cache_capacity,
                },
            )

            return max(cache_capacity, 1000)

        # Try 2: Fallback to YAML metadata
        inferencer = ModelMetadataInferencer()
        yaml_metadata = inferencer.infer_metadata(model_id, None)

        if yaml_metadata and yaml_metadata.get("context_window"):
            ctx_win = yaml_metadata["context_window"]
            context_window = int(ctx_win) if ctx_win is not None else 0  # type: ignore[arg-type]
            max_out = max_output_tokens or yaml_metadata.get(
                "max_output_tokens", default_max_output
            )
            max_output = int(max_out) if max_out is not None else 0  # type: ignore[arg-type]

            cache_capacity = context_window - max_output - system_overhead

            logger.info(
                "Calculated cache capacity from YAML config",
                extra={
                    "model_id": model_id,
                    "source": "yaml",
                    "context_window": context_window,
                    "max_output_tokens": max_output,
                    "cache_capacity": cache_capacity,
                },
            )

            return max(cache_capacity, 1000)

        # Fallback to defaults
        logger.warning(
            "Model not found in registry or YAML, using defaults",
            extra={"model_id": model_id},
        )
        return default_context_window - default_max_output - system_overhead

    except Exception as e:
        logger.error(
            "Failed to lookup model for cache sizing",
            extra={"model_id": model_id, "error": str(e)},
        )
        return default_context_window - default_max_output - system_overhead


@router.post("/process", response_model=FormattedResponse)
async def process_request(
    request: Request,
    query: str = Body(..., description="User query or request text"),
    request_type: RequestType
    | None = Body(None, description="Request type (QUERY, RULE_GENERATION, etc.)"),
    stream: bool = Body(False, description="Whether to use streaming response"),
    session_id: str
    | None = Body(None, description="Client-owned session ID for ephemeral conversation context"),
    thread_id: uuid.UUID
    | None = Body(
        None,
        description="Thread UUID for multi-turn conversations (deprecated in stateless v1)",
    ),
    discussion_id: str
    | None = Body(None, description="External incident/ticket ID for correlation"),
    use_case_id: uuid.UUID | None = Body(None, description="Use case UUID"),
    current_user: TokenPayload = Depends(get_current_user),  # Provides user details like role, id
    raw_token_creds: HTTPAuthorizationCredentials
    | None = Depends(jwt_validator.security),  # Provides HTTPAuthorizationCredentials
    db: AsyncSession = Depends(get_async_db),
    settings: OrchestratorConfig = Depends(get_orchestrator_settings),
) -> FormattedResponse | StreamingResponse:
    """
    Process a request through the orchestration workflow.

    This endpoint handles the complete orchestration process:
    1. Authentication (via JWT dependency)
    2. Intent parsing
    3. LLM-Guard validation
    4. Context retrieval
    5. Prompt assembly
    6. LLM request processing
    7. Response formatting
    8. Thread context management (if thread_id provided)

    Args:
        request: The FastAPI request object
        query: User query or request text
        request_type: Optional explicit request type (if provided by UI)
        context: Optional pre-provided context (overrides retrieval)
        stream: Whether to use streaming response
        thread_id: Optional thread UUID for multi-turn conversations
        discussion_id: Optional external incident/ticket ID for correlation
        use_case_id: Optional use case UUID
        current_user: The authenticated user information (from JWT payload)
        raw_token: The raw JWT token string from the Authorization header
        db: Database session

    Returns:
        For non-streaming: JSON response with formatted content
        For streaming: Streaming response with SSE format
    """
    # Extract the raw token string from HTTPAuthorizationCredentials
    raw_token = raw_token_creds.credentials if raw_token_creds else None
    # Use the raw_token for authentication checks within the orchestrator
    # current_user can be used for other user-specific logic if needed, like logging user_id

    # Generate request ID for tracing
    request_id = str(uuid.uuid4())

    logger.info(
        "Received orchestration request",
        extra={
            "user_id": current_user.user_id,
            "stream": stream,
            "request_type": str(request_type) if request_type else None,
        },
    )

    # Initialize orchestrator with centralized configuration settings
    runtime_config = build_runtime_config(settings)

    # Create LLMRouter with JWT token for Inference Gateway
    from ..orchestrator.llm_router import LLMRouter
    from ..orchestrator.model_selection import ModelSelector, load_intent_defaults_from_async_db

    if raw_token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing JWT token")

    # Load intent→model defaults from DB so ModelSelector has a populated cache (ADR-069)
    intent_defaults, intent_temperatures = await load_intent_defaults_from_async_db(db)
    model_selector = ModelSelector(
        preloaded_defaults=intent_defaults,
        preloaded_temperatures=intent_temperatures,
    )

    llm_router = LLMRouter(
        user_jwt_token=raw_token,
        gateway_url=settings.inference_gateway_url,
        request_timeout_seconds=settings.request_timeout_seconds,
        model_selector=model_selector,
    )
    # Create sync session for Orchestrator services that still require sync
    # All services now use async_db
    try:
        orchestrator = Orchestrator(
            async_db=db,
            config=runtime_config,
            llm_router=llm_router,
        )

        logger.info(
            "Orchestrator created with Inference Gateway",
            extra={"user_id": current_user.user_id},
        )
        # Process the request differently based on streaming flag
        if stream:
            logger.info(
                "Processing streaming orchestration request",
                extra={
                    "user_id": current_user.user_id,
                },
            )

            # Build same context as non-streaming (use case selection)
            effective_request_type = request_type or RequestType.QUERY

            # Load use case config and prompts (by ID or intent type)
            use_case_cfg = None
            use_case_prompts = None

            if use_case_id:
                # USE CASE DRIVEN: Explicit use case execution
                use_case_cfg = await orchestrator.config_loader.load_config(str(use_case_id))
                use_case_prompts = await orchestrator.load_use_case_prompts(str(use_case_id))
            else:
                # GENERIC CONVERSATION: No use case specified
                use_case_cfg = orchestrator.config_loader.get_default_config()
                use_case_prompts = None

            # Load conversation history from ephemeral cache if session_id provided
            cache = get_conversation_cache()
            history_messages = []

            logger.debug(
                "Session context",
                extra={"has_session": bool(session_id)},
            )

            if session_id:
                # Calculate cache capacity: Model Context Window - Max Output - Overhead
                model_id = use_case_cfg.models.llm if use_case_cfg else None
                max_output_tokens = (
                    use_case_cfg.generation_params.max_tokens if use_case_cfg else None
                )
                cache_capacity = await _calculate_cache_capacity(
                    db=db, model_id=model_id, max_output_tokens=max_output_tokens
                )

                cache.set_session_limits(
                    session_id,
                    max_tokens=cache_capacity,
                    reserved_response_tokens=0,  # Already calculated in cache_capacity
                )

                cached_history = cache.get(session_id)
                if cached_history:
                    history_messages = cached_history
                    logger.info(
                        "✅ CACHE HIT: Loaded conversation history from cache",
                        extra={
                            "session_id": session_id,
                            "message_count": len(history_messages),
                            "history_preview": [
                                {"role": m["role"], "content_length": len(m["content"])}
                                for m in history_messages[:3]
                            ],
                        },
                    )
                else:
                    logger.info(
                        "CACHE MISS: No cached history found for session",
                        extra={"session_id": session_id},
                    )

            # Build RequestContext (identical to non-streaming path)
            ctx = RequestContext(
                req_id=request_id,
                user_id=getattr(current_user, "user_id", None),
                user_uuid=getattr(current_user, "user_uuid", None),
                user_role=(
                    current_user.roles[0] if current_user.roles else "user"
                ),  # Deprecated, kept for backward compatibility
                user_roles=(
                    current_user.roles if current_user.roles else ["user"]
                ),  # Multi-role support per ADR-060
                request_type=effective_request_type,
                query_original=query,
                query_sanitized=query,
                intent=None,
                use_case_id=use_case_id,
                use_case=use_case_cfg,
                prompts=use_case_prompts,
                thread_id=thread_id,
                discussion_id=discussion_id,
                history_messages=history_messages,
                sources=[],
                rag_enabled=False,
                llm_request=None,
                llm_response=None,
                formatted=None,
            )

            # Compose HTTP client adapters
            guard_client = LLMGuardClient(base_url=orchestrator.llm_guard_url)
            retrieval_client = RetrievalClient(
                base_url=orchestrator.config.get(
                    "retrieval_svc_url", "http://corpus-service:8001/api/v1"
                )
            )

            # Compose pipeline steps WITH STREAMING enabled
            # Note: FormatResponse omitted - it skips when llm_response is None (streaming)
            streaming_steps: list[Step] = [
                GuardValidate(
                    guard=guard_client,
                    policy_engine=None,
                    token=raw_token,
                    enabled=orchestrator.config.get("llm_guard_enabled", False),
                    strict_mode=orchestrator.config.get("llm_guard_strict_mode", False),
                ),
                RetrieveContext(
                    retrieval=retrieval_client,
                    headers=({"Authorization": f"Bearer {raw_token}"} if raw_token else None),
                    use_case_id=str(use_case_id) if use_case_id else None,
                ),
                AssemblePrompt(assembler=orchestrator.prompt_assembler),
                ExecuteLLM(router=orchestrator.llm_router, streaming=True),
            ]

            # Create streaming response generator
            async def event_generator() -> AsyncGenerator[str, None]:
                accumulated_response = ""
                try:
                    # Add user message to cache before LLM processing
                    logger.info(
                        f"DEBUG STREAMING: About to try cache append, session_id={session_id}",
                        extra={"session_id": session_id},
                    )

                    if session_id and not cache.append(session_id, "user", query):
                        # Session doesn't exist yet, create it
                        logger.info(
                            "DEBUG: Creating new cache session",
                            extra={"session_id": session_id},
                        )
                        cache.set(
                            session_id,
                            [
                                {
                                    "role": "user",
                                    "content": query,
                                    "timestamp": datetime.utcnow().isoformat(),
                                }
                            ],
                        )
                        logger.info(
                            "Created new cache session with user message",
                            extra={"session_id": session_id},
                        )
                    else:
                        logger.info(
                            "DEBUG: Appended to existing session",
                            extra={"session_id": session_id},
                        )

                    # Run pipeline through UseCaseRunner for proper telemetry
                    runner = UseCaseRunner(
                        steps=streaming_steps,
                        telemetry=orchestrator.telemetry_integration,
                    )

                    # Execute all steps (returns None since FormatResponse omitted)
                    await runner.run(ctx)

                    # Extract streaming generator from context (placed by ExecuteLLM)
                    if "llm_stream" not in ctx.extras:
                        logger.error(
                            "No LLM stream in context after pipeline execution",
                            extra={"request_id": request_id},
                        )
                        error_data = {
                            "error": "No LLM stream generated",
                            "message": "Streaming pipeline failed",
                            "request_id": request_id,
                        }
                        yield f"data: {json.dumps(error_data)}\n\n"
                        return

                    # Get the streaming generator
                    llm_stream = ctx.extras["llm_stream"]

                    # Stream chunks - they're already formatted as LLMStreamResponse
                    async for chunk in llm_stream:
                        # Accumulate response for cache update
                        accumulated_response += chunk.response

                        chunk_data = {
                            "response": chunk.response,
                            "model_used": (
                                chunk.model_used.value
                                if hasattr(chunk.model_used, "value")
                                else str(chunk.model_used)
                            ),
                            "tokens_used": chunk.tokens_used,
                            "processing_time": chunk.processing_time,
                            "chunk_number": chunk.chunk_number,
                            "is_final": chunk.is_final,
                            "metadata": chunk.metadata,
                            "request_id": request_id,
                        }
                        yield f"data: {json.dumps(chunk_data)}\n\n"

                    # After streaming completes, add assistant response to cache
                    if session_id and accumulated_response:
                        cache.append(
                            session_id,
                            "assistant",
                            accumulated_response,
                            {"request_id": request_id},
                        )

                        # Get cache stats for UI
                        cache_stats = cache.get_session_stats(session_id)

                        # Send final event with cache stats
                        final_event = {
                            "response": "",
                            "chunk_number": 0,
                            "is_final": True,
                            "cache_stats": cache_stats,
                            "request_id": request_id,
                        }
                        yield f"data: {json.dumps(final_event)}\n\n"

                        logger.debug(
                            "Updated cache with assistant response",
                            extra={
                                "session_id": session_id,
                                "response_length": len(accumulated_response),
                                "cache_stats": cache_stats,
                            },
                        )

                except Exception as e:
                    logger.error(
                        "Streaming pipeline error",
                        extra={"error": str(e), "request_id": request_id},
                        exc_info=True,
                    )
                    error_data = {
                        "error": "Streaming failed",
                        "message": GENERIC_CLIENT_ERROR,
                        "request_id": request_id,
                    }
                    yield f"data: {json.dumps(error_data)}\n\n"

            return StreamingResponse(event_generator(), media_type="text/event-stream")
        logger.info(
            "Processing non-streaming orchestration request",
            extra={
                "user_id": current_user.user_id,
            },
        )

        # Execute through Pipeline+Steps architecture (ADR-036)
        # Determine effective request type (default to QUERY if not provided)
        effective_request_type = request_type or RequestType.QUERY

        # Load use case config and prompts (by ID or intent type)
        use_case_cfg = None
        use_case_prompts = None

        if use_case_id:
            # USE CASE DRIVEN: Explicit use case execution with specific config/prompts
            # use_case_id here is the UUID (id column), not the string use_case_id column
            use_case_cfg = await orchestrator.config_loader.load_config(str(use_case_id))
            use_case_prompts = await orchestrator.load_use_case_prompts(str(use_case_id))
        else:
            # GENERIC CONVERSATION: No use case specified - use default config + template prompts
            # This supports UI Conversations feature without requiring a specific use case
            #
            # FUTURE WORK: Make generic conversation config customizable
            # Currently uses orchestrator.config_loader.get_default_config() which returns
            # hardcoded defaults. Future enhancement could allow:
            # - User-specific conversation preferences (model, temperature, etc.)
            # - Organization-wide defaults
            # - Per-conversation settings stored in thread metadata
            # See UI_DEVELOPMENT_PLAN.md for conversation feature specification
            use_case_cfg = orchestrator.config_loader.get_default_config()
            use_case_prompts = None  # Will trigger template fallback in AssemblePrompt

        # Load conversation history from ephemeral cache if session_id provided
        cache = get_conversation_cache()
        history_messages = []
        if session_id:
            # Calculate cache capacity: Model Context Window - Max Output - Overhead
            model_id = use_case_cfg.models.llm if use_case_cfg else None
            max_output_tokens = use_case_cfg.generation_params.max_tokens if use_case_cfg else None
            cache_capacity = await _calculate_cache_capacity(
                db=db, model_id=model_id, max_output_tokens=max_output_tokens
            )

            cache.set_session_limits(
                session_id,
                max_tokens=cache_capacity,
                reserved_response_tokens=0,  # Already calculated in cache_capacity
            )

            cached_history = cache.get(session_id)
            if cached_history:
                history_messages = cached_history
                logger.info(
                    "✅ CACHE HIT (non-streaming): Loaded conversation history from cache",
                    extra={
                        "session_id": session_id,
                        "message_count": len(history_messages),
                        "history_preview": [
                            {"role": m["role"], "content_length": len(m["content"])}
                            for m in history_messages[:3]
                        ],
                    },
                )
            else:
                logger.info(
                    "CACHE MISS (non-streaming): No cached history found for session",
                    extra={"session_id": session_id},
                )

        # Build RequestContext from incoming request
        ctx = RequestContext(
            req_id=request_id,
            user_id=getattr(current_user, "user_id", None),
            user_uuid=getattr(current_user, "user_uuid", None),
            user_role=(
                current_user.roles[0] if current_user.roles else "user"
            ),  # Deprecated, kept for backward compatibility
            user_roles=(
                current_user.roles if current_user.roles else ["user"]
            ),  # Multi-role support per ADR-060
            request_type=effective_request_type,
            query_original=query,
            query_sanitized=query,  # Will be updated by GuardValidate
            intent=None,  # Will be populated by intent parser if needed
            use_case_id=use_case_id,
            use_case=use_case_cfg,
            prompts=use_case_prompts,
            thread_id=thread_id,
            discussion_id=discussion_id,
            history_messages=history_messages,  # Loaded from ephemeral cache
            sources=[],  # Will be populated by RetrieveContext
            rag_enabled=False,  # Will be set by RetrieveContext
            llm_request=None,  # Will be built by AssemblePrompt
            llm_response=None,  # Will be populated by ExecuteLLM
            formatted=None,  # Will be populated by FormatResponse
        )

        # Compose HTTP client adapters
        guard_client = LLMGuardClient(base_url=orchestrator.llm_guard_url)
        retrieval_client = RetrievalClient(
            base_url=orchestrator.config.get(
                "retrieval_svc_url", "http://corpus-service:8001/api/v1"
            )
        )

        # Compose pipeline steps using existing orchestrator services
        steps: list[Step] = [
            GuardValidate(
                guard=guard_client,
                policy_engine=None,  # Not yet extracted
                token=raw_token,
                enabled=orchestrator.config.get("llm_guard_enabled", False),
                strict_mode=orchestrator.config.get("llm_guard_strict_mode", False),
            ),
            RetrieveContext(
                retrieval=retrieval_client,
                headers={"Authorization": f"Bearer {raw_token}"} if raw_token else None,
                use_case_id=str(use_case_id) if use_case_id else None,
            ),
            AssemblePrompt(assembler=orchestrator.prompt_assembler),
            ExecuteLLM(router=orchestrator.llm_router, streaming=False),
            FormatResponse(
                formatter=orchestrator.response_formatter,
                token_tracker=orchestrator.token_tracker,
            ),
        ]

        # Create runner with telemetry integration
        runner = UseCaseRunner(steps=steps, telemetry=orchestrator.telemetry_integration)

        # Execute pipeline (returns FormattedResponse from ctx.formatted)
        formatted_response = await runner.run(ctx)

        # Update cache with user query and assistant response
        if session_id and formatted_response:
            # Add user message if session doesn't exist yet
            if not cache.append(session_id, "user", query):
                # Create new session
                cache.set(
                    session_id,
                    [
                        {
                            "role": "user",
                            "content": query,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    ],
                )
                logger.debug(
                    "Created new cache session with user message",
                    extra={"session_id": session_id},
                )

            # Add assistant response
            cache.append(
                session_id,
                "assistant",
                formatted_response.response,
                {
                    "request_id": formatted_response.request_id,
                    "confidence": formatted_response.confidence,
                },
            )

            # Get cache stats for UI visibility
            cache_stats = cache.get_session_stats(session_id)
            formatted_response.cache_stats = cache_stats

            logger.debug(
                "Updated cache with user query and assistant response",
                extra={"session_id": session_id, "cache_stats": cache_stats},
            )

        # Return formatted response (now includes cache_stats)
        if formatted_response:
            logger.info(
                "Pipeline execution completed",
                extra={
                    "user_id": current_user.user_id,
                },
            )
            return cast("FormattedResponse | StreamingResponse", formatted_response)
        # Fallback if no formatted response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Pipeline completed but no formatted response generated",
        )
    except HTTPException as e:
        logger.warning(
            "HTTPException during orchestration request",
            extra={
                "user_id": current_user.user_id,
                "error": str(e.detail),
                "status_code": e.status_code,
            },
        )
        raise
    except Exception as e:
        logger.error(
            "Unhandled exception during orchestration request",
            extra={
                "user_id": current_user.user_id,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing request: {e!s}",
        ) from e
