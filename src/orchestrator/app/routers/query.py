"""
Query proxy endpoints for the Orchestrator API.

This router exposes query and analytics endpoints and proxies them to the retrieval-svc.
"""

from typing import Any

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request

from shared.config.loader import load_orchestrator_config

from ..services.response_transformer import ResponseTransformer
from ..utils.auth import get_current_user

CORPUS_SVC_URL = load_orchestrator_config().retrieval_service_url

router = APIRouter(prefix="/api/v1", tags=["query"])


# Helper to forward headers (esp. Authorization)
def get_forward_headers(request: Request) -> dict[str, str]:
    """Forward Authorization header to downstream services."""
    headers = {}
    # Check both lowercase and capitalized versions
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth_header:
        headers["Authorization"] = auth_header
    return headers


# Helper to extract user_id from current_user
def get_user_id(current_user: Any) -> str | None:
    """
    Extract user_id from TokenPayload or dict.

    TokenPayload (ADR-060) has 'user_id' field (UUID as string).
    Legacy dicts might have 'id' or 'sub'.
    """
    # First try to get the 'user_id' field (TokenPayload per ADR-060)
    if isinstance(current_user, dict):
        if "user_id" in current_user:
            return str(current_user["user_id"])
        if "id" in current_user:
            return str(current_user["id"])
        # If no 'id', try to use 'sub' (username) as the user ID
        if "sub" in current_user:
            return str(current_user["sub"])
    # Try object attribute access (TokenPayload has user_id)
    elif hasattr(current_user, "user_id"):
        return str(current_user.user_id)
    elif hasattr(current_user, "id"):
        return str(current_user.id)
    elif hasattr(current_user, "sub"):
        return str(current_user.sub)
    return None


@router.post("/query/search")
async def search_documents(
    request: Request,
    query_request: dict = Body(...),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Search documents using semantic similarity.

    This endpoint proxies the request to the retrieval service's semantic-search endpoint.
    """
    headers = get_forward_headers(request)

    # Map the request to match the retrieval service schema
    retrieval_request = {
        "query_text": query_request.get("query", ""),
        "top_k": query_request.get("limit", 10),
        "filters": query_request.get("filters"),
        "min_relevancy_score": query_request.get("threshold", 0.0),
        "run_id": query_request.get("run_id"),
        "metadata": query_request.get("metadata"),
    }

    url = f"{CORPUS_SVC_URL}/query/semantic-search"
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=retrieval_request, headers=headers)

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    # Transform the response to match frontend schema
    raw_response = resp.json()
    return ResponseTransformer.transform_retrieval_response(raw_response)


# /query/ask endpoint removed - use /api/v1/process for proper RAG functionality
# This was a broken endpoint that returned fake answers without calling the LLM


@router.get("/analytics/documents/hot")
async def get_hot_documents(
    request: Request,
    limit: int = Query(10),
    hours: int = Query(24),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """Get hot documents analytics."""
    headers = get_forward_headers(request)

    # Map hours to days for the retrieval service
    days_back = max(1, hours // 24)
    params = {"limit": limit, "days_back": days_back}

    url = f"{CORPUS_SVC_URL}/analytics/hot-documents"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params, headers=headers)

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    # Wrap list response in dict for API consistency
    return {
        "documents": resp.json(),
        "total": len(resp.json()),
        "limit": limit,
        "hours": hours,
    }


@router.get("/analytics/usage/stats")
async def get_usage_statistics(
    request: Request,
    hours: int = Query(24),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """Get usage statistics."""
    headers = get_forward_headers(request)

    # Map to the performance metrics endpoint
    days_back = max(1, hours // 24)
    params = {"days_back": days_back}

    url = f"{CORPUS_SVC_URL}/analytics/performance-metrics"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params, headers=headers)

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    data: dict[str, Any] = resp.json()
    return data
