"""
Responses router - OpenAI-compatible Responses API endpoint.

Implements POST /v1/responses for stateful conversations.

NEW OPENAI API (2024+):
- Stateful conversation management
- Automatic state tracking
- Multimodal support (text, images, audio)
- Tool calling support

VERIFICATION:
- Uses shared.auth.requires_scope("inference:responses") for auth
- Uses shared.logging_utils for logging
- Returns OpenAI-compatible response
- Propagates X-Request-ID header

P5-A15 VERIFIED (Nov 28, 2025):
- Endpoint is async (`create_response`)
- No direct DB access (uses async SimpleRouter, ProviderManager)
"""

import time
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import JSONResponse
from shared.auth import TokenPayload  # type: ignore[import-untyped]
from shared.auth.scopes import requires_scope  # type: ignore[import-untyped]
from shared.logging_utils.fastapi import configure_logging  # type: ignore[import-untyped]

from ..models.response_request import ResponseRequest
from ..models.response_response import Response
from ..providers.factory import ProviderFactory
from ..services.provider_manager import ProviderManager
from ..services.router import SimpleRouter
from ..utils.errors import (
    GatewayError,
    ModelNotFoundError,
    ProviderDisabledError,
    ProviderHTTPError,
    ProviderNotFoundError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)

logger = configure_logging(service_name="gateway_responses")

# Initialize services (singleton pattern)
simple_router = SimpleRouter()
provider_manager = ProviderManager()

# Create router
router = APIRouter(prefix="/v1", tags=["responses"])


@router.post("/responses", response_model=Response)
async def create_response(
    request: ResponseRequest,
    token: TokenPayload = Depends(requires_scope("inference:responses")),
    x_request_id: Annotated[str | None, Header()] = None,
) -> JSONResponse:
    """
    Create a stateful response (OpenAI Responses API).

    OpenAI-compatible responses endpoint for stateful conversations.
    Automatically manages conversation state - no manual history required.

    Supports:
    - Stateful conversations (previous_response_id)
    - Multimodal input (text, images, audio)
    - Tool calling
    - Streaming responses

    Follows ADR-050 (dumb pipe pattern):
    1. Route model → provider
    2. Get provider config
    3. Call provider.create_response()
    4. Return response with ID for continuation

    Args:
        request: Response request (model, messages or previous_response_id)
        token: Authenticated user token with inference:responses scope
        x_request_id: Optional request ID for tracing

    Returns:
        JSONResponse: Response with ID for conversation continuation

    Raises:
        HTTPException: Various errors mapped from provider exceptions
            - 400: Invalid request (missing messages and previous_response_id)
            - 404: Model not found
            - 429: Rate limit exceeded
            - 503: Provider unavailable
            - 504: Provider timeout
            - 500: Internal error
    """
    start_time = time.time()
    request_id = x_request_id or str(uuid.uuid4())

    # Validate: Must have input OR previous_response_id
    if not request.input and not request.previous_response_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "message": "Either 'input' or 'previous_response_id' is required",
                    "type": "invalid_request",
                }
            },
        )

    logger.info(
        "Responses request received",
        extra={
            "request_id": request_id,
            "model": request.model,
            "user_id": token.user_id,
            "has_previous": bool(request.previous_response_id),
            "has_input": bool(request.input),
            "has_instructions": bool(request.instructions),
        },
    )

    try:
        # Step 1: Route model to provider
        provider_name = await simple_router.route(request.model)
        logger.debug(
            "Request routed to provider",
            extra={
                "request_id": request_id,
                "model": request.model,
                "provider": provider_name,
            },
        )

        # Step 2: Get provider configuration
        provider_config = await provider_manager.get_provider(provider_name)

        # Step 3: Create provider instance and call
        provider = ProviderFactory.create_provider(provider_config)
        async with provider:
            # Check if streaming requested
            if request.stream:
                # TODO: Implement streaming for responses API
                raise HTTPException(
                    status_code=status.HTTP_501_NOT_IMPLEMENTED,
                    detail={
                        "error": {
                            "message": "Streaming not yet implemented for /v1/responses",
                            "type": "not_implemented",
                        }
                    },
                )

            response = await provider.create_response(request, request_id)

        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "Responses request completed",
            extra={
                "request_id": request_id,
                "model": request.model,
                "provider": provider_name,
                "latency_ms": latency_ms,
                "response_id": response.get("id"),
            },
        )

        # Return response with headers
        return JSONResponse(
            content=response,
            headers={
                "X-Request-ID": request_id,
                "X-Gateway-Latency-Ms": str(latency_ms),
            },
        )

    except ModelNotFoundError as e:
        logger.warning(
            "Model not found",
            extra={"request_id": request_id, "model": request.model, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "message": str(e),
                    "type": "model_not_found",
                    "param": "model",
                }
            },
        )

    except ProviderNotFoundError as e:
        logger.error(
            "Provider not found",
            extra={"request_id": request_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": {"message": str(e), "type": "provider_not_found"}},
        )

    except ProviderDisabledError as e:
        logger.warning(
            "Provider disabled",
            extra={"request_id": request_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": {"message": str(e), "type": "provider_disabled"}},
        )

    except ProviderRateLimitError as e:
        logger.warning(
            "Provider rate limit exceeded",
            extra={"request_id": request_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": {
                    "message": str(e),
                    "type": "rate_limit_exceeded",
                    "retry_after": getattr(e, "retry_after", None),
                }
            },
        )

    except ProviderTimeoutError as e:
        logger.error(
            "Provider timeout",
            extra={"request_id": request_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={"error": {"message": str(e), "type": "timeout"}},
        )

    except ProviderHTTPError as e:
        logger.error(
            "Provider HTTP error",
            extra={
                "request_id": request_id,
                "status_code": e.status_code,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": {"message": str(e), "type": "provider_error"}},
        )

    except GatewayError as e:
        logger.error(
            "Gateway error",
            extra={"request_id": request_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"message": str(e), "type": "gateway_error"}},
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is (e.g., 501 for streaming)
        raise

    except Exception as e:
        logger.exception(
            "Unexpected error in responses endpoint",
            extra={"request_id": request_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "message": "An unexpected error occurred",
                    "type": "internal_error",
                }
            },
        )
