"""
Admin Gateway Provider Management Router

Proxies provider management requests to the inference gateway service.
All gateway provider operations go through the orchestrator API.

**Authorization:** Admin-only endpoints
"""

from typing import Any
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from shared.auth import get_current_user
from shared.auth.models import TokenPayload
from shared.config.loader import load_orchestrator_config
from shared.logging_utils.fastapi import configure_logging

logger = configure_logging(service_name="admin_gateway_providers")

# Router setup
router = APIRouter(prefix="/admin/gateway/providers", tags=["Admin", "Gateway Providers"])

# Inference Gateway URL (admin routes are at /admin, not /v1/admin)
_ORCHESTRATOR_CONFIG = load_orchestrator_config()
_GATEWAY_URL_RAW = _ORCHESTRATOR_CONFIG.inference_gateway_url.rstrip("/")
# Strip /v1 so we hit gateway root: .../admin/... not .../v1/admin/...
GATEWAY_URL = (
    _GATEWAY_URL_RAW.removesuffix("/v1") if _GATEWAY_URL_RAW.endswith("/v1") else _GATEWAY_URL_RAW
)


# ============================================================================
# Pydantic Models
# ============================================================================


# Import shared provider models
from shared.providers import (
    ProviderConfig,
    ProviderConfigUpdate,
    ProviderListResponse,
    ProviderTestResult,
)

# ============================================================================
# Helper Functions
# ============================================================================


def require_admin(current_user: TokenPayload) -> None:
    """Ensure current user has admin role."""
    if not current_user.has_role("admin"):
        logger.warning(
            "Unauthorized gateway provider access attempt",
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


async def proxy_to_gateway(
    method: str,
    endpoint: str,
    request: Request,
    data: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    current_user: TokenPayload = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Proxy request to inference gateway service with authentication.

    Args:
        method: HTTP method (GET, POST, PUT, DELETE)
        endpoint: API endpoint path
        request: FastAPI request object
        data: Request body data
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
        f"Proxying {method} request to gateway",
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
                json=data,
                params=params,
                headers=headers,
            )

            response.raise_for_status()

            # Handle 204 No Content (DELETE responses)
            if response.status_code == 204:
                return {}

            result: dict[str, Any] = response.json()
            return result

    except httpx.HTTPStatusError as e:
        logger.error(
            "Gateway returned error: %s",
            e.response.status_code,
        )
        raise HTTPException(
            status_code=e.response.status_code,
            detail=e.response.json().get("detail", "Gateway request failed"),
        )
    except httpx.TimeoutException:
        logger.error("Gateway request timeout")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Gateway service timeout",
        )
    except httpx.RequestError as e:
        logger.error("Gateway request failed: %s", type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gateway service unavailable",
        )


# ============================================================================
# API Endpoints
# ============================================================================


@router.get(
    "",
    response_model=ProviderListResponse,
    summary="List all providers",
    description="Retrieve paginated list of gateway providers",
)
async def list_providers(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    enabled_only: bool = Query(False),
    current_user: TokenPayload = Depends(get_current_user),
) -> ProviderListResponse:
    """List all gateway providers with optional filters."""
    params = {"limit": limit, "offset": offset, "enabled_only": enabled_only}
    result = await proxy_to_gateway(
        method="GET",
        endpoint="/admin/providers",
        request=request,
        params=params,
        current_user=current_user,
    )
    return ProviderListResponse(**result)


@router.get(
    "/{provider_id}",
    response_model=ProviderConfig,
    summary="Get provider by ID",
    description="Retrieve a single provider configuration",
)
async def get_provider(
    provider_id: UUID,
    request: Request,
    current_user: TokenPayload = Depends(get_current_user),
) -> ProviderConfig:
    """Get a specific provider by ID."""
    result = await proxy_to_gateway(
        method="GET",
        endpoint=f"/admin/providers/{provider_id}",
        request=request,
        current_user=current_user,
    )
    return ProviderConfig(**result)


@router.post(
    "",
    response_model=ProviderConfig,
    status_code=status.HTTP_201_CREATED,
    summary="Create provider",
    description="Create a new gateway provider configuration",
)
async def create_provider(
    provider: ProviderConfig,
    request: Request,
    current_user: TokenPayload = Depends(get_current_user),
) -> ProviderConfig:
    """Create a new gateway provider."""
    result = await proxy_to_gateway(
        method="POST",
        endpoint="/admin/providers",
        request=request,
        data=provider.model_dump(exclude_unset=True),
        current_user=current_user,
    )
    return ProviderConfig(**result)


@router.put(
    "/{provider_id}",
    response_model=ProviderConfig,
    summary="Update provider",
    description="Update an existing provider configuration",
)
async def update_provider(
    provider_id: UUID,
    provider: ProviderConfigUpdate,
    request: Request,
    current_user: TokenPayload = Depends(get_current_user),
) -> ProviderConfig:
    """Update a gateway provider."""
    result = await proxy_to_gateway(
        method="PUT",
        endpoint=f"/admin/providers/{provider_id}",
        request=request,
        data=provider.model_dump(exclude_unset=True),
        current_user=current_user,
    )
    return ProviderConfig(**result)


@router.delete(
    "/{provider_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete provider",
    description="Delete a gateway provider configuration",
)
async def delete_provider(
    provider_id: UUID,
    request: Request,
    current_user: TokenPayload = Depends(get_current_user),
) -> None:
    """Delete a gateway provider."""
    await proxy_to_gateway(
        method="DELETE",
        endpoint=f"/admin/providers/{provider_id}",
        request=request,
        current_user=current_user,
    )


@router.post(
    "/{provider_id}/test",
    response_model=ProviderTestResult,
    summary="Test provider connectivity",
    description="Test if a provider can be reached and is functional",
)
async def test_provider(
    provider_id: UUID,
    request: Request,
    current_user: TokenPayload = Depends(get_current_user),
) -> ProviderTestResult:
    """Test provider connectivity."""
    result = await proxy_to_gateway(
        method="POST",
        endpoint=f"/admin/providers/{provider_id}/test",
        request=request,
        current_user=current_user,
    )
    return ProviderTestResult(**result)
