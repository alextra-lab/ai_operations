"""
Chat completions router - OpenAI-compatible endpoint.

Implements POST /v1/chat/completions with model routing to providers.

VERIFICATION CRITICAL:
- Uses shared.auth.requires_scope("inference:chat") for auth
- Uses shared.logging_utils for logging
- Returns OpenAI-compatible response
- Propagates X-Request-ID header
- SSE streaming support (P1-T6 COMPLETE)

P5-A15 VERIFIED (Nov 28, 2025):
- All endpoints are async (`chat_completions`, `list_models`)
- No direct DB access (uses async SimpleRouter, ProviderManager)
- Streaming uses async generators correctly
"""

import json
import time
import uuid
from collections.abc import AsyncGenerator
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse
from shared.auth import TokenPayload  # type: ignore[import-untyped]
from shared.auth.scopes import requires_scope  # type: ignore[import-untyped]
from shared.logging_utils.fastapi import configure_logging  # type: ignore[import-untyped]

from ..models.requests import ChatCompletionRequest
from ..providers.factory import ProviderFactory
from ..services.cost_calculator import CostCalculator
from ..services.provider_manager import ProviderManager
from ..services.router import SimpleRouter
from ..services.usage_logger import get_usage_logger
from ..utils.errors import (
    GatewayError,
    ModelNotFoundError,
    ProviderDisabledError,
    ProviderHTTPError,
    ProviderNotFoundError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)

logger = configure_logging(service_name="gateway_chat")

# Initialize services (singleton pattern)
simple_router = SimpleRouter()
provider_manager = ProviderManager()
cost_calculator = CostCalculator()

# Create router
router = APIRouter(prefix="/v1", tags=["chat"])


async def _log_usage_error(
    request_id: str,
    token: TokenPayload,
    model: str,
    latency_ms: int,
    http_status: int,
    error_type: str,
    error_message: str,
    stream_enabled: bool = False,
    provider_name: str | None = None,
) -> None:
    """
    Helper to log failed request usage.

    Args:
        request_id: Request correlation ID
        token: User token
        model: Model requested
        latency_ms: Total request latency
        http_status: HTTP status code
        error_type: Error classification
        error_message: Error details
        stream_enabled: Whether streaming was enabled
        provider_name: Provider name if known
    """
    try:
        usage_logger = get_usage_logger()
        await usage_logger.log_usage(
            {
                "request_id": request_id,
                "user_id": token.user_id if not token.is_service() else None,
                "integration_id": token.sub if token.is_service() else None,
                "endpoint": "/v1/chat/completions",
                "provider_name": provider_name,
                "model_requested": model,
                "model_used": None,
                "tokens_in": 0,
                "tokens_out": 0,
                "latency_total_ms": latency_ms,
                "http_status": http_status,
                "success": False,
                "error_type": error_type,
                "error_message": error_message,
                "stream_enabled": stream_enabled,
            }
        )
    except Exception as log_err:
        logger.error(
            "Failed to log error usage",
            extra={"request_id": request_id, "error": str(log_err)},
        )


async def _handle_streaming_request(
    request: ChatCompletionRequest,
    token: TokenPayload,
    x_request_id: str,
    start_time: float,
) -> StreamingResponse:
    """
    Handle streaming chat completion request.

    Follows ADR-050 (dumb pipe) and existing streaming pattern from orchestrator.

    Args:
        request: Chat completion request with stream=true
        token: Authenticated user token
        x_request_id: Request ID for tracing
        start_time: Request start time for latency tracking

    Returns:
        StreamingResponse: SSE stream with chat completion chunks

    Raises:
        HTTPException: Various errors mapped from provider exceptions
    """

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events from provider stream."""
        try:
            # Step 1: Route model to provider
            provider_name = await simple_router.route(request.model)
            logger.debug(
                "Streaming request routed to provider",
                extra={
                    "request_id": x_request_id,
                    "model": request.model,
                    "provider": provider_name,
                },
            )

            # Step 2: Get provider configuration
            provider_config = await provider_manager.get_provider(provider_name)

            # Step 3: Create provider instance and stream
            provider = ProviderFactory.create_provider(provider_config)
            async with provider:
                chunk_count = 0
                async for chunk in provider.stream_chat_completion(request, x_request_id):  # type: ignore[union-attr,misc]
                    # Format as SSE: "data: {json}\n\n"
                    chunk_json = chunk.model_dump_json()
                    yield f"data: {chunk_json}\n\n"
                    chunk_count += 1

                # Send [DONE] signal
                yield "data: [DONE]\n\n"

                latency_ms = int((time.time() - start_time) * 1000)
                logger.info(
                    "Streaming completion successful",
                    extra={
                        "request_id": x_request_id,
                        "model": request.model,
                        "provider": provider_name,
                        "chunks": chunk_count,
                        "latency_ms": latency_ms,
                    },
                )

                # Log usage record (async, non-blocking)
                try:
                    usage_logger = get_usage_logger()
                    await usage_logger.log_usage(
                        {
                            "request_id": x_request_id,
                            "user_id": (token.user_id if not token.is_service() else None),
                            "integration_id": token.sub if token.is_service() else None,
                            "endpoint": "/v1/chat/completions",
                            "provider_name": provider_name,
                            "model_requested": request.model,
                            "model_used": request.model,
                            "tokens_in": 0,  # Streaming doesn't return usage
                            "tokens_out": 0,
                            "latency_total_ms": latency_ms,
                            "http_status": 200,
                            "success": True,
                            "stream_enabled": True,
                            "metadata_json": {"chunks": chunk_count},
                        }
                    )
                except Exception as log_err:
                    logger.error(
                        "Failed to log usage",
                        extra={"request_id": x_request_id, "error": str(log_err)},
                    )

        except ModelNotFoundError as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.warning(
                "Streaming model not found",
                extra={
                    "request_id": x_request_id,
                    "model": request.model,
                    "latency_ms": latency_ms,
                },
            )
            error_chunk = {
                "error": {
                    "message": e.message,
                    "type": "model_not_found_error",
                    "code": "model_not_found",
                }
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"

        except (ProviderNotFoundError, ProviderDisabledError) as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(
                "Streaming provider error",
                extra={
                    "request_id": x_request_id,
                    "model": request.model,
                    "error": e.message,
                    "latency_ms": latency_ms,
                },
            )
            error_chunk = {
                "error": {
                    "message": e.message,
                    "type": "provider_error",
                    "code": "provider_unavailable",
                }
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"

        except ProviderTimeoutError as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(
                "Streaming provider timeout",
                extra={
                    "request_id": x_request_id,
                    "model": request.model,
                    "provider": e.provider_name,
                    "timeout_seconds": e.timeout_seconds,
                    "latency_ms": latency_ms,
                },
            )
            error_chunk = {
                "error": {
                    "message": e.message,
                    "type": "timeout_error",
                    "code": "provider_timeout",
                }
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"

        except ProviderRateLimitError as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.warning(
                "Streaming provider rate limit",
                extra={
                    "request_id": x_request_id,
                    "model": request.model,
                    "provider": e.provider_name,
                    "retry_after": e.retry_after,
                    "latency_ms": latency_ms,
                },
            )
            error_chunk = {
                "error": {
                    "message": e.message,
                    "type": "rate_limit_error",
                    "code": "rate_limit_exceeded",
                }
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"

        except ProviderHTTPError as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(
                "Streaming provider HTTP error",
                extra={
                    "request_id": x_request_id,
                    "model": request.model,
                    "provider": e.provider_name,
                    "status_code": e.status_code,
                    "detail": e.detail,
                    "latency_ms": latency_ms,
                },
            )
            error_chunk = {
                "error": {
                    "message": e.message,
                    "type": "provider_http_error",
                    "code": f"http_{e.status_code}",
                }
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"

        except GatewayError as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(
                "Streaming gateway error",
                extra={
                    "request_id": x_request_id,
                    "model": request.model,
                    "error_type": e.error_type,
                    "error": e.message,
                    "latency_ms": latency_ms,
                },
            )
            error_chunk = {
                "error": {
                    "message": "Internal server error",
                    "type": "gateway_error",
                    "code": "internal_error",
                }
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.exception(
                "Streaming unexpected error",
                extra={
                    "request_id": x_request_id,
                    "model": request.model,
                    "error": str(e),
                    "latency_ms": latency_ms,
                },
            )
            error_chunk = {
                "error": {
                    "message": "Internal server error",
                    "type": "unexpected_error",
                    "code": "internal_error",
                }
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Request-ID": x_request_id,
        },
    )


@router.post("/chat/completions", response_model=None)
async def chat_completions(
    request: ChatCompletionRequest,
    token: Annotated[TokenPayload, Depends(requires_scope("inference:chat"))],
    x_request_id: Annotated[str | None, Header()] = None,
) -> JSONResponse | StreamingResponse:
    """
    Create a chat completion (OpenAI-compatible).

    This endpoint routes requests to the appropriate LLM provider based on
    the requested model. Returns OpenAI-compatible responses.

    Supports both synchronous and streaming (SSE) responses.

    Args:
        request: Chat completion request (OpenAI format)
        token: Authenticated user token with inference:chat scope
        x_request_id: Optional request ID for tracing

    Returns:
        ChatCompletionResponse | StreamingResponse: OpenAI-compatible response

    Raises:
        HTTPException: Various errors (401, 403, 404, 429, 500, 503, 504)

    Examples:
        Synchronous:
        ```bash
        curl -X POST http://localhost:8002/v1/chat/completions \\
          -H "Authorization: Bearer $TOKEN" \\
          -H "Content-Type: application/json" \\
          -d '{
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "Hello!"}]
          }'
        ```

        Streaming:
        ```bash
        curl -N -X POST http://localhost:8002/v1/chat/completions \\
          -H "Authorization: Bearer $TOKEN" \\
          -H "Content-Type: application/json" \\
          -d '{
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "Hello!"}],
            "stream": true
          }'
        ```
    """
    # Generate request ID if not provided
    if not x_request_id:
        x_request_id = f"req_{uuid.uuid4().hex[:16]}"

    start_time = time.time()

    logger.info(
        "Chat completion request",
        extra={
            "request_id": x_request_id,
            "model": request.model,
            "user_id": token.user_id,
            "messages": len(request.messages),
            "stream": request.stream,
        },
    )

    # Handle streaming requests
    if request.stream:
        return await _handle_streaming_request(request, token, x_request_id, start_time)

    try:
        # Step 1: Route model to provider
        provider_name = await simple_router.route(request.model)
        logger.debug(
            "Model routed to provider",
            extra={
                "request_id": x_request_id,
                "model": request.model,
                "provider": provider_name,
            },
        )

        # Step 2: Get provider configuration
        provider_config = await provider_manager.get_provider(provider_name)
        logger.debug(
            "Provider configuration loaded",
            extra={
                "request_id": x_request_id,
                "provider": provider_name,
                "base_url": provider_config.base_url,
            },
        )

        # Step 3: Create provider instance and call
        provider = ProviderFactory.create_provider(provider_config)
        async with provider:
            response = await provider.chat_completion(request, x_request_id)

        latency_ms = int((time.time() - start_time) * 1000)

        # Calculate cost using existing pricing infrastructure
        tokens_in = response.usage.prompt_tokens if response.usage else 0
        tokens_out = response.usage.completion_tokens if response.usage else 0
        cost_result = await cost_calculator.calculate(
            model_id=request.model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
        )
        cost_eur = cost_result["total_cost_eur"]

        logger.info(
            "Chat completion successful",
            extra={
                "request_id": x_request_id,
                "model": request.model,
                "provider": provider_name,
                "latency_ms": latency_ms,
                "prompt_tokens": tokens_in,
                "completion_tokens": tokens_out,
                "cost_eur": cost_eur,
                "pricing_source": cost_result["pricing_source"],
            },
        )

        # Log usage record (async, non-blocking)
        try:
            usage_logger = get_usage_logger()
            await usage_logger.log_usage(
                {
                    "request_id": x_request_id,
                    "user_id": token.user_id if not token.is_service() else None,
                    "integration_id": token.sub if token.is_service() else None,
                    "endpoint": "/v1/chat/completions",
                    "provider_name": provider_name,
                    "model_requested": request.model,
                    "model_used": request.model,
                    "tokens_in": tokens_in,
                    "tokens_out": tokens_out,
                    "cost_eur": cost_eur,
                    "latency_total_ms": latency_ms,
                    "http_status": 200,
                    "success": True,
                    "stream_enabled": False,
                    "metadata_json": {
                        "pricing_source": cost_result["pricing_source"],
                    },
                }
            )
        except Exception as log_err:
            logger.error(
                "Failed to log usage",
                extra={"request_id": x_request_id, "error": str(log_err)},
            )

        # Add cost to response headers (OpenAI-compatible extension)
        return JSONResponse(
            content=response.model_dump(mode="json", exclude_none=True),
            headers={
                "X-Request-ID": x_request_id,
                "X-Cost-EUR": f"{cost_eur:.6f}",
            },
        )

    except ModelNotFoundError as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.warning(
            "Model not found",
            extra={
                "request_id": x_request_id,
                "model": request.model,
                "latency_ms": latency_ms,
            },
        )
        await _log_usage_error(
            x_request_id,
            token,
            request.model,
            latency_ms,
            404,
            "model_not_found",
            e.message,
            request.stream,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e

    except (ProviderNotFoundError, ProviderDisabledError) as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(
            "Provider error",
            extra={
                "request_id": x_request_id,
                "model": request.model,
                "error": e.message,
                "latency_ms": latency_ms,
            },
        )
        await _log_usage_error(
            x_request_id,
            token,
            request.model,
            latency_ms,
            503,
            "provider_error",
            e.message,
            request.stream,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=e.message,
        ) from e

    except ProviderTimeoutError as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(
            "Provider timeout",
            extra={
                "request_id": x_request_id,
                "model": request.model,
                "provider": e.provider_name,
                "timeout_seconds": e.timeout_seconds,
                "latency_ms": latency_ms,
            },
        )
        await _log_usage_error(
            x_request_id,
            token,
            request.model,
            latency_ms,
            504,
            "timeout",
            e.message,
            request.stream,
            e.provider_name,
        )
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=e.message,
        ) from e

    except ProviderRateLimitError as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.warning(
            "Provider rate limit",
            extra={
                "request_id": x_request_id,
                "model": request.model,
                "provider": e.provider_name,
                "retry_after": e.retry_after,
                "latency_ms": latency_ms,
            },
        )
        await _log_usage_error(
            x_request_id,
            token,
            request.model,
            latency_ms,
            429,
            "rate_limit",
            e.message,
            request.stream,
            e.provider_name,
        )
        # Return OpenAI-compatible 429 response with Retry-After header
        headers = {}
        if e.retry_after:
            headers["Retry-After"] = str(e.retry_after)

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=e.message,
            headers=headers,
        ) from e

    except ProviderHTTPError as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(
            "Provider HTTP error",
            extra={
                "request_id": x_request_id,
                "model": request.model,
                "provider": e.provider_name,
                "status_code": e.status_code,
                "detail": e.detail,
                "latency_ms": latency_ms,
            },
        )
        # Map provider errors to appropriate status codes
        gateway_status = _map_provider_status(e.status_code)
        raise HTTPException(
            status_code=gateway_status,
            detail=e.message,
        ) from e

    except GatewayError as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(
            "Gateway error",
            extra={
                "request_id": x_request_id,
                "model": request.model,
                "error_type": e.error_type,
                "error": e.message,
                "latency_ms": latency_ms,
            },
        )
        await _log_usage_error(
            x_request_id,
            token,
            request.model,
            latency_ms,
            500,
            e.error_type,
            e.message,
            request.stream,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.message,
        ) from e

    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.exception(
            "Unexpected error",
            extra={
                "request_id": x_request_id,
                "model": request.model,
                "error": str(e),
                "latency_ms": latency_ms,
            },
        )
        await _log_usage_error(
            x_request_id,
            token,
            request.model,
            latency_ms,
            500,
            "unexpected_error",
            "Internal server error",
            request.stream,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


def _map_provider_status(provider_status: int) -> int:
    """
    Map provider HTTP status to Gateway status.

    OpenAI error codes:
    - 400: Bad request (validation errors)
    - 401: Invalid authentication
    - 403: Permission denied
    - 404: Resource not found
    - 429: Rate limit exceeded
    - 500: Server error
    - 503: Service unavailable
    """
    # Most provider errors should be passed through
    if provider_status in (400, 401, 403, 404, 429, 500, 503):
        return provider_status

    # Default to 502 Bad Gateway for unknown provider errors
    return status.HTTP_502_BAD_GATEWAY


@router.get("/models")
async def list_models(
    token: Annotated[
        TokenPayload,
        Depends(requires_scope("inference:chat")),
    ],
) -> JSONResponse:
    """
    List available models (OpenAI-compatible with Gateway extension).

    Aggregates models from all enabled Gateway providers and includes provider metadata.
    This enables automatic provider assignment during Orchestrator sync.

    Args:
        token: Authenticated user token with inference:chat scope

    Returns:
        JSONResponse: OpenAI-compatible models list with provider extension

    Example:
        ```bash
        curl http://localhost:8002/v1/models \\
          -H "Authorization: Bearer $TOKEN"
        ```

    Response includes provider metadata:
        ```json
        {
          "data": [
            {"id": "model-id", "provider": "LMStudio", ...}
          ]
        }
        ```
    """
    logger.debug("List models request", extra={"user_id": token.user_id})

    try:
        # Import provider manager for querying providers
        from ..services.provider_manager import ProviderManager

        provider_manager = ProviderManager()
        await provider_manager.load_providers()

        enabled_providers = await provider_manager.list_providers()
        all_models: list[dict[str, Any]] = []

        # Query each enabled provider for their models
        import httpx

        async with httpx.AsyncClient() as client:
            for provider_config in enabled_providers:
                if not provider_config.is_enabled:
                    continue

                try:
                    # Build provider endpoint
                    provider_endpoint = provider_config.base_url.rstrip("/")
                    if not provider_endpoint.endswith("/v1"):
                        models_url = f"{provider_endpoint}/v1/models"
                    else:
                        models_url = f"{provider_endpoint}/models"

                    # Build headers
                    headers = {}
                    if provider_config.api_key:
                        headers["Authorization"] = f"Bearer {provider_config.api_key}"

                    # Query provider
                    response = await client.get(models_url, headers=headers, timeout=10.0)
                    response.raise_for_status()

                    data = response.json()
                    provider_models = data.get("data", [])

                    # Tag each model with provider metadata
                    for model in provider_models:
                        all_models.append(
                            {
                                "id": model.get("id"),
                                "object": "model",
                                "created": int(time.time()),
                                "owned_by": "gateway",
                                "provider": provider_config.name,
                                "provider_type": provider_config.provider_type,
                            }
                        )

                    logger.debug(
                        f"Discovered {len(provider_models)} models from {provider_config.name}",
                        extra={"provider": provider_config.name, "count": len(provider_models)},
                    )

                except Exception as e:
                    logger.warning(
                        f"Failed to query models from {provider_config.name}: {e}",
                        extra={"provider": provider_config.name, "error": str(e)},
                    )

        logger.info(
            f"Aggregated {len(all_models)} models from {len(enabled_providers)} provider(s)",
            extra={"total_models": len(all_models), "provider_count": len(enabled_providers)},
        )

        return JSONResponse(
            content={
                "object": "list",
                "data": all_models,
            }
        )

    except Exception as e:
        logger.exception("Error listing models", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list models",
        ) from e
