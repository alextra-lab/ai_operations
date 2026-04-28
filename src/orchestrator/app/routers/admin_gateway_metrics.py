"""
Admin Gateway Metrics Router

Proxies metrics requests to the inference gateway service.
All gateway metrics operations go through the orchestrator API.

**Authorization:** Admin-only endpoints
"""

from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel

from shared.auth import get_current_user
from shared.auth.models import TokenPayload
from shared.config.loader import load_orchestrator_config
from shared.logging_utils.fastapi import configure_logging

logger = configure_logging(service_name="admin_gateway_metrics")

# Router setup
router = APIRouter(prefix="/admin/gateway/metrics", tags=["Admin", "Gateway Metrics"])

# Inference Gateway URL (admin routes are at /admin, not /v1/admin)
_ORCHESTRATOR_CONFIG = load_orchestrator_config()
_GATEWAY_URL_RAW = _ORCHESTRATOR_CONFIG.inference_gateway_url.rstrip("/")
# Strip /v1 so we hit gateway root: .../admin/metrics/* not .../v1/admin/metrics/*
GATEWAY_URL = (
    _GATEWAY_URL_RAW.removesuffix("/v1") if _GATEWAY_URL_RAW.endswith("/v1") else _GATEWAY_URL_RAW
)


# ============================================================================
# Pydantic Models
# ============================================================================


class GatewayMetrics(BaseModel):
    """Aggregate gateway metrics model."""

    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    total_input_tokens: int
    total_output_tokens: int
    total_cost_eur: float
    avg_latency_ms: float
    p50_latency_ms: float | None
    p95_latency_ms: float | None
    p99_latency_ms: float | None
    unique_models: int
    unique_users: int
    streaming_requests: int


class TimeSeriesPoint(BaseModel):
    """Single time series data point."""

    timestamp: str
    value: float


class TimeSeriesData(BaseModel):
    """Time series data for metrics."""

    latency: list[TimeSeriesPoint]
    tokens: list[TimeSeriesPoint]
    cost: list[TimeSeriesPoint]
    requests: list[TimeSeriesPoint]


class ProviderMetrics(BaseModel):
    """Metrics grouped by provider."""

    provider_name: str
    request_count: int  # Matches Gateway response
    success_rate: float  # Added from Gateway
    avg_latency_ms: float
    total_cost_eur: float
    total_tokens: int  # Matches Gateway response (combined tokens)


class ModelMetrics(BaseModel):
    """Metrics grouped by model."""

    model_name: str
    request_count: int  # Matches Gateway response
    total_tokens: int  # Matches Gateway response (combined tokens)
    total_cost_eur: float
    avg_latency_ms: float


# ============================================================================
# Helper Functions
# ============================================================================


def require_admin(current_user: TokenPayload) -> None:
    """Ensure current user has admin role."""
    if not current_user.has_any_role(["admin"]):
        logger.warning(
            "Unauthorized gateway metrics access attempt",
            extra={"user": current_user.sub, "roles": current_user.roles},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )


def get_forward_headers(request: Request) -> dict[str, str]:
    """Extract and forward authorization headers from the request."""
    headers = {}
    # Check both lowercase and capitalized versions
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth_header:
        headers["Authorization"] = auth_header
    return headers


JSONType = dict[str, Any] | list[Any]


async def proxy_to_gateway(
    method: str,
    endpoint: str,
    request: Request,
    params: dict[str, Any] | None,
    current_user: TokenPayload,
) -> JSONType:
    """
    Proxy request to inference gateway service with authentication.

    Args:
        method: HTTP method (GET)
        endpoint: API endpoint path
        request: FastAPI request object
        params: Query parameters
        current_user: Authenticated user

    Returns:
        Response from gateway service

    Raises:
        HTTPException: If gateway request fails
    """
    require_admin(current_user)

    url = f"{GATEWAY_URL}{endpoint}"
    headers = get_forward_headers(request)

    logger.info(
        "Proxying %s request to gateway",
        method,
        extra={
            "url": url,
            "user": current_user.sub,
            "endpoint": endpoint,
        },
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=method,
                url=url,
                params=params,
                headers=headers,
            )

            response.raise_for_status()
            out: dict[str, Any] | list[Any] = response.json()
            return out

    except httpx.HTTPStatusError as e:
        logger.error("Gateway returned error: %s", e.response.status_code)
        detail: str
        try:
            data: Any = e.response.json()
        except ValueError:
            data = None
        if isinstance(data, dict) and "detail" in data:
            detail = str(data["detail"])
        else:
            detail = "Gateway request failed"
        raise HTTPException(status_code=e.response.status_code, detail=detail) from e
    except httpx.TimeoutException as e:
        logger.error("Gateway request timeout")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Gateway service timeout",
        ) from e
    except httpx.RequestError as e:
        logger.error("Gateway request failed: %s", type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gateway service unavailable",
        ) from e


# ============================================================================
# API Endpoints
# ============================================================================


@router.get(
    "/aggregate",
    response_model=GatewayMetrics,
    summary="Get aggregate metrics",
    description="Retrieve aggregate gateway usage metrics for a time window",
)
async def get_aggregate_metrics(
    request: Request,
    hours: int = Query(24, ge=1, le=720, description="Time window in hours"),
    provider: str | None = Query(None, description="Filter by provider name"),
    current_user: TokenPayload = Depends(get_current_user),
) -> GatewayMetrics:
    """Get aggregate gateway metrics."""
    params: dict[str, Any] = {"hours": hours}
    if provider:
        params["provider"] = provider

    result = await proxy_to_gateway(
        method="GET",
        endpoint="/admin/metrics/aggregate",
        request=request,
        params=params,
        current_user=current_user,
    )
    if not isinstance(result, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid response from gateway",
        )
    return GatewayMetrics(**result)


@router.get(
    "/timeseries",
    response_model=TimeSeriesData,
    summary="Get time series metrics",
    description="Retrieve time series gateway metrics",
)
async def get_timeseries_metrics(
    request: Request,
    hours: int = Query(24, ge=1, le=720, description="Time window in hours"),
    interval_minutes: int = Query(60, ge=1, le=1440, description="Data point interval in minutes"),
    provider: str | None = Query(None, description="Filter by provider name"),
    current_user: TokenPayload = Depends(get_current_user),
) -> TimeSeriesData:
    """Get time series gateway metrics."""
    params: dict[str, Any] = {"hours": hours, "interval_minutes": interval_minutes}
    if provider:
        params["provider"] = provider

    result = await proxy_to_gateway(
        method="GET",
        endpoint="/admin/metrics/timeseries",
        request=request,
        params=params,
        current_user=current_user,
    )
    if not isinstance(result, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid response from gateway",
        )
    return TimeSeriesData(**result)


@router.get(
    "/by-provider",
    response_model=list[ProviderMetrics],
    summary="Get metrics by provider",
    description="Retrieve gateway metrics grouped by provider",
)
async def get_metrics_by_provider(
    request: Request,
    hours: int = Query(24, ge=1, le=720, description="Time window in hours"),
    current_user: TokenPayload = Depends(get_current_user),
) -> list[ProviderMetrics]:
    """Get gateway metrics grouped by provider."""
    params: dict[str, Any] = {"hours": hours}
    result = await proxy_to_gateway(
        method="GET",
        endpoint="/admin/metrics/by-provider",
        request=request,
        params=params,
        current_user=current_user,
    )
    if not isinstance(result, list):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid response from gateway",
        )
    typed_items: list[dict[str, Any]] = []
    for item in result:
        if not isinstance(item, dict):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Invalid item in gateway response",
            )
        typed_items.append(item)
    return [ProviderMetrics(**item) for item in typed_items]


@router.get(
    "/by-model",
    response_model=list[ModelMetrics],
    summary="Get metrics by model",
    description="Retrieve gateway metrics grouped by model",
)
async def get_metrics_by_model(
    request: Request,
    hours: int = Query(24, ge=1, le=720, description="Time window in hours"),
    current_user: TokenPayload = Depends(get_current_user),
) -> list[ModelMetrics]:
    """Get gateway metrics grouped by model."""
    params: dict[str, Any] = {"hours": hours}
    result = await proxy_to_gateway(
        method="GET",
        endpoint="/admin/metrics/by-model",
        request=request,
        params=params,
        current_user=current_user,
    )
    if not isinstance(result, list):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid response from gateway",
        )
    typed_items: list[dict[str, Any]] = []
    for item in result:
        if not isinstance(item, dict):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Invalid item in gateway response",
            )
        typed_items.append(item)
    return [ModelMetrics(**item) for item in typed_items]
