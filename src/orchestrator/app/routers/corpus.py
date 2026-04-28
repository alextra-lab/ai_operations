"""
Corpus management proxy endpoints for the Orchestrator API.

This router exposes document management endpoints and proxies them to the retrieval-svc.

P5-A12: Verified async patterns (Nov 2025).
Already uses httpx.AsyncClient for all proxy operations - no database sessions.
"""

from typing import Any

import httpx
from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
)

from shared.config.loader import load_orchestrator_config

from ..utils.auth import get_current_user

CORPUS_SVC_URL = load_orchestrator_config().retrieval_service_url

router = APIRouter(prefix="/api/v1/documents", tags=["corpus"])


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


@router.post("/", status_code=202)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    collection_name: str | None = Form("default"),
    title: str | None = Form(None),
    source: str | None = Form(None),
    author: str | None = Form(None),
    classification: str | None = Form(None),
    tags: str | None = Form(None),
    metadata: str | None = Form(None),
    process_async: bool = Form(True),
    current_user: Any = Depends(get_current_user),
) -> Any:
    """
    Upload a document to the retrieval service.

    This endpoint proxies the request to the retrieval service, passing the JWT token
    in the Authorization header for authentication.
    """
    # Forward the Authorization header which contains the JWT with user info
    headers = get_forward_headers(request)

    # Read the file content
    file_content = await file.read()

    # Prepare the multipart form data
    files = {"file": (file.filename, file_content, file.content_type)}

    # Prepare other form fields
    data = {
        "collection_name": collection_name,
        "title": title,
        "source": source,
        "author": author,
        "classification": classification,
        "tags": tags,
        "metadata": metadata,
        "process_async": str(process_async),
    }

    # Remove None values
    data = {k: v for k, v in data.items() if v is not None}

    # Make the request to the retrieval service
    url = f"{CORPUS_SVC_URL}/documents/"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, data=data, files=files, headers=headers)
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@router.get("/")
async def list_documents(
    request: Request,
    limit: int = Query(10),
    offset: int = Query(0),
    document_type: str | None = Query(None),
    tag: str | None = Query(None),
    query: str | None = Query(None),
    include_deleted: bool = Query(False),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    url = f"{CORPUS_SVC_URL}/documents/"
    params: dict[str, str | int | bool] = {
        "limit": limit,
        "offset": offset,
        "type": "",
        "include_deleted": include_deleted,
    }
    if document_type:
        params["type"] = document_type
    if tag:
        params["tag"] = tag
    if query:
        params["query"] = query

    # Add user_id to params
    user_id = get_user_id(current_user)
    if user_id:
        params["user_id"] = user_id

    headers = get_forward_headers(request)
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, params=params, headers=headers)  # type: ignore[arg-type]
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    # Transform response to match frontend expectations
    documents_list = resp.json()
    return {
        "documents": documents_list,
        "total": len(documents_list),
        "limit": limit,
        "offset": offset,
    }


@router.get("/stats")
async def get_document_statistics(
    request: Request, current_user: Any = Depends(get_current_user)
) -> Any:
    url = f"{CORPUS_SVC_URL}/documents/stats"
    headers = get_forward_headers(request)

    # Add user_id to params
    params = {}
    user_id = get_user_id(current_user)
    if user_id:
        params["user_id"] = user_id

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, params=params, headers=headers)
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@router.get("/{document_id}")
async def get_document(
    request: Request,
    document_id: str,
    include_preview: bool = Query(False),
    preview_length: int = Query(1000),
    current_user: Any = Depends(get_current_user),
) -> Any:
    url = f"{CORPUS_SVC_URL}/documents/{document_id}"
    params: dict[str, str | int | bool] = {
        "include_preview": include_preview,
        "preview_length": preview_length,
    }

    # Add user_id to params
    user_id = get_user_id(current_user)
    if user_id:
        params["user_id"] = user_id

    headers = get_forward_headers(request)
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, params=params, headers=headers)
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@router.patch("/{document_id}")
async def update_document(
    request: Request,
    document_id: str,
    update_request: dict[str, Any] = Body(...),
    current_user: Any = Depends(get_current_user),
) -> Any:
    url = f"{CORPUS_SVC_URL}/documents/{document_id}"
    headers = get_forward_headers(request)

    # Add user_id to the update request if not already present
    user_id = get_user_id(current_user)
    if user_id and "user_id" not in update_request:
        update_request = {**update_request, "user_id": user_id}

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.patch(url, json=update_request, headers=headers)
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@router.delete("/{document_id}")
async def delete_document(
    request: Request,
    document_id: str,
    force: bool = Query(False),
    current_user: Any = Depends(get_current_user),
) -> Any:
    url = f"{CORPUS_SVC_URL}/documents/{document_id}"
    params: dict[str, Any] = {"force": force}

    # Add user_id to params
    user_id = get_user_id(current_user)
    if user_id:
        params["user_id"] = user_id

    headers = get_forward_headers(request)
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.delete(url, params=params, headers=headers)
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@router.get("/{document_id}/status")
async def get_document_status(
    request: Request,
    document_id: str,
    current_user: Any = Depends(get_current_user),
) -> Any:
    """
    Get the processing status of a document.
    """
    url = f"{CORPUS_SVC_URL}/documents/{document_id}/status"
    headers = get_forward_headers(request)

    # Add user_id to params
    params = {}
    user_id = get_user_id(current_user)
    if user_id:
        params["user_id"] = user_id

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, params=params, headers=headers)

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@router.get("/{document_id}/download")
async def download_document(
    request: Request,
    document_id: str,
    current_user: Any = Depends(get_current_user),
) -> Any:
    """
    Download a document file.
    """
    url = f"{CORPUS_SVC_URL}/documents/{document_id}/download"
    headers = get_forward_headers(request)

    # Add user_id to params
    params = {}
    user_id = get_user_id(current_user)
    if user_id:
        params["user_id"] = user_id

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, params=params, headers=headers)

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    # Return the file content with appropriate headers
    from fastapi.responses import Response

    return Response(
        content=resp.content,
        media_type=resp.headers.get("content-type", "application/octet-stream"),
        headers={
            "Content-Disposition": resp.headers.get(
                "content-disposition", f'attachment; filename="{document_id}"'
            )
        },
    )


@router.post("/{document_id}/reprocess")
async def reprocess_document(
    request: Request,
    document_id: str,
    embedding_model: str | None = Query(None),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Trigger document reprocessing.

    This endpoint proxies to the retrieval service's process endpoint,
    which will re-chunk and re-embed the document.
    """
    url = f"{CORPUS_SVC_URL}/documents/{document_id}/process"
    headers = get_forward_headers(request)

    # Add optional embedding model as query param
    params: dict[str, str] = {}
    if embedding_model:
        params["embedding_model"] = embedding_model

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, params=params, headers=headers)

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    data: dict[str, Any] = resp.json()
    return data
