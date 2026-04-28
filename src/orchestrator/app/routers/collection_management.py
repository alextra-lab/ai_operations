"""
Collection Management Router

Proxies collection management requests to the retrieval service.
All collection operations go through the orchestrator API.
"""

from typing import Any
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from shared.auth import get_current_user
from shared.auth.models import TokenPayload
from shared.config.loader import load_orchestrator_config
from shared.logging_utils.fastapi import configure_logging

logger = configure_logging(service_name="collection_management")

# Router setup
router = APIRouter(prefix="/v1/admin/collections", tags=["Collection Management"])

_ORCHESTRATOR_CONFIG = load_orchestrator_config()


# Pydantic models for collection management
class CollectionCreate(BaseModel):
    name: str = Field(
        ..., min_length=3, max_length=255, description="Unique name for the collection"
    )
    description: str | None = Field(
        None, max_length=1000, description="Description of the collection"
    )
    embedding_model: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Identifier of the embedding model",
    )
    embedding_provider: str = Field(
        ..., min_length=1, max_length=100, description="Provider of the embedding model"
    )
    embedding_dimensions: int = Field(
        ..., gt=0, description="Vector dimensions for this embedding model"
    )


class CollectionUpdate(BaseModel):
    description: str | None = Field(
        None, max_length=1000, description="Description of the collection"
    )
    is_active: bool | None = Field(None, description="Whether the collection is active")


class CollectionResponse(BaseModel):
    id: str
    name: str
    description: str | None
    embedding_model: str
    embedding_provider: str
    embedding_dimensions: int
    qdrant_collection_name: str
    is_default: bool
    is_active: bool
    is_system_managed: bool
    created_by: str
    created_at: str
    updated_at: str
    document_count: int


class CollectionListResponse(BaseModel):
    collections: list[CollectionResponse]
    total: int


class CollectionStats(BaseModel):
    id: str
    name: str
    document_count: int
    total_chunks: int
    total_size_bytes: int
    last_updated: str


CORPUS_SVC_URL = _ORCHESTRATOR_CONFIG.retrieval_service_url


# Helper to forward headers (esp. Authorization)
def get_forward_headers(request: Request) -> dict[str, str]:
    """Extract and forward authorization headers from the request."""
    headers = {}
    # Check both lowercase and capitalized versions
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth_header:
        headers["Authorization"] = auth_header
        logger.debug("Authorization header present for proxy")
    else:
        logger.warning("No authorization header found in request")
    return headers


async def proxy_to_retrieval_service(
    method: str,
    endpoint: str,
    request: Request,
    data: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    current_user: TokenPayload = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Proxy request to retrieval service with authentication.

    Args:
        method: HTTP method (GET, POST, PUT, DELETE)
        endpoint: API endpoint path
        data: Request body data
        params: Query parameters
        current_user: Authenticated user

    Returns:
        Response data from retrieval service

    Raises:
        HTTPException: If retrieval service request fails
    """
    url = f"{CORPUS_SVC_URL}{endpoint}"

    # Forward headers from the original request
    headers = get_forward_headers(request)
    headers.update({"Content-Type": "application/json", "User-Agent": "orchestrator-proxy/1.0"})

    logger.info("Proxying %s request to corpus service", method)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method.upper() == "GET":
                response = await client.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                response = await client.post(url, headers=headers, json=data, params=params)
            elif method.upper() == "PUT":
                response = await client.put(url, headers=headers, json=data, params=params)
            elif method.upper() == "DELETE":
                response = await client.delete(url, headers=headers, params=params)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported HTTP method: {method}",
                )

            # Handle response
            logger.info("Corpus proxy response status: %s", response.status_code)

            if response.status_code >= 400:
                error_detail = "Unknown error"
                try:
                    error_data = response.json()
                    error_detail = error_data.get("detail", str(error_data))
                except Exception:
                    error_detail = response.text or f"HTTP {response.status_code}"

                logger.error(
                    "Corpus service error: status=%s",
                    response.status_code,
                )
                raise HTTPException(status_code=response.status_code, detail=error_detail)

            result: dict[str, Any] = response.json() if response.content else {}
            return result

    except httpx.TimeoutException:
        logger.error("Timeout connecting to retrieval service")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Retrieval service timeout",
        )
    except httpx.ConnectError:
        logger.error("Failed to connect to retrieval service")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Retrieval service unavailable",
        )
    except Exception as e:
        logger.error(
            "Unexpected error proxying to corpus service: %s",
            type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/", response_model=CollectionListResponse)
async def list_collections(
    request: Request,
    active_only: bool = Query(True, description="Only return active collections"),
    embedding_model: str | None = Query(None, description="Filter by embedding model"),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return"),
    current_user: TokenPayload = Depends(get_current_user),
) -> CollectionListResponse:
    """
    List all collections with optional filters.

    **Permissions:** admin, corpus_admin
    """
    # Check permissions (multi-role support per ADR-060)
    if not current_user.has_any_role(["admin", "corpus_admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Required roles: admin, corpus_admin",
        )

    params: dict[str, Any] = {"active_only": active_only, "skip": skip, "limit": limit}
    if embedding_model:
        params["embedding_model"] = embedding_model

    result = await proxy_to_retrieval_service(
        "GET", "/admin/collections/", request, params=params, current_user=current_user
    )

    return CollectionListResponse(**result)


@router.get("/available", response_model=CollectionListResponse)
async def list_available_collections(
    request: Request, current_user: TokenPayload = Depends(get_current_user)
) -> CollectionListResponse:
    """
    List available collections for Use Case configuration.

    Returns only active collections that can be selected for RAG queries.

    **Permissions:** All authenticated users
    """
    result = await proxy_to_retrieval_service(
        "GET", "/collections/available", request, current_user=current_user
    )

    return CollectionListResponse(**result)


@router.get("/{collection_id}", response_model=CollectionResponse)
async def get_collection(
    collection_id: UUID,
    request: Request,
    current_user: TokenPayload = Depends(get_current_user),
) -> CollectionResponse:
    """
    Get collection by ID.

    **Permissions:** admin, corpus_admin
    """
    # Check permissions (multi-role support per ADR-060)
    if not current_user.has_any_role(["admin", "corpus_admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Required roles: admin, corpus_admin",
        )

    result = await proxy_to_retrieval_service(
        "GET", f"/admin/collections/{collection_id}", request, current_user=current_user
    )

    return CollectionResponse(**result)


@router.post("/", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED)
async def create_collection(
    collection: CollectionCreate,
    request: Request,
    current_user: TokenPayload = Depends(get_current_user),
) -> CollectionResponse:
    """
    Create a new collection.

    **Permissions:** admin, corpus_admin
    """
    # Check permissions (multi-role support per ADR-060)
    if not current_user.has_any_role(["admin", "corpus_admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Required roles: admin, corpus_admin",
        )

    result = await proxy_to_retrieval_service(
        "POST",
        "/admin/collections/",
        request,
        data=collection.dict(),
        current_user=current_user,
    )

    return CollectionResponse(**result)


@router.put("/{collection_id}", response_model=CollectionResponse)
async def update_collection(
    collection_id: UUID,
    collection: CollectionUpdate,
    request: Request,
    current_user: TokenPayload = Depends(get_current_user),
) -> CollectionResponse:
    """
    Update collection.

    Only description and is_active can be updated.
    Embedding model is immutable after creation.

    **Permissions:** admin, corpus_admin
    """
    # Check permissions (multi-role support per ADR-060)
    if not current_user.has_any_role(["admin", "corpus_admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Required roles: admin, corpus_admin",
        )

    result = await proxy_to_retrieval_service(
        "PUT",
        f"/admin/collections/{collection_id}",
        request,
        data=collection.dict(exclude_unset=True),
        current_user=current_user,
    )

    return CollectionResponse(**result)


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection(
    collection_id: UUID,
    request: Request,
    current_user: TokenPayload = Depends(get_current_user),
) -> None:
    """
    Delete collection.

    Collection must have no documents to be deleted.
    System-managed collections cannot be deleted.

    **Permissions:** admin, corpus_admin
    """
    # Check permissions (multi-role support per ADR-060)
    if not current_user.has_any_role(["admin", "corpus_admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Required roles: admin, corpus_admin",
        )

    await proxy_to_retrieval_service(
        "DELETE",
        f"/admin/collections/{collection_id}",
        request,
        current_user=current_user,
    )


@router.get("/{collection_id}/stats", response_model=CollectionStats)
async def get_collection_stats(
    collection_id: UUID,
    request: Request,
    current_user: TokenPayload = Depends(get_current_user),
) -> CollectionStats:
    """
    Get collection statistics.

    **Permissions:** admin, corpus_admin
    """
    # Check permissions (multi-role support per ADR-060)
    if not current_user.has_any_role(["admin", "corpus_admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Required roles: admin, corpus_admin",
        )

    result = await proxy_to_retrieval_service(
        "GET",
        f"/admin/collections/{collection_id}/stats",
        request,
        current_user=current_user,
    )

    return CollectionStats(**result)


# Public endpoints for use case configuration


@router.get("/public/{collection_id}", response_model=CollectionResponse)
async def get_collection_public(
    collection_id: UUID,
    request: Request,
    current_user: TokenPayload = Depends(get_current_user),
) -> CollectionResponse:
    """
    Get collection by ID (public read-only endpoint).

    **Permissions:** All authenticated users
    """
    result = await proxy_to_retrieval_service(
        "GET", f"/collections/{collection_id}", request, current_user=current_user
    )

    return CollectionResponse(**result)
