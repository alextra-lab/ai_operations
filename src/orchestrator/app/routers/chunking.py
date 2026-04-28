"""
Chunking and Preflight Analysis Proxy Router for Backend API.

This router exposes chunking and preflight analysis endpoints and proxies them
to the corpus service. All PDF extraction and chunking is handled by corpus service.

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
    Request,
    UploadFile,
)

from shared.config.loader import load_orchestrator_config

from ..utils.auth import get_current_user

CORPUS_SVC_URL = load_orchestrator_config().retrieval_service_url

router = APIRouter(prefix="/api/v1/chunking", tags=["chunking"])


def get_forward_headers(request: Request) -> dict[str, str]:
    """Forward authentication headers to retrieval service."""
    headers = {}
    if "authorization" in request.headers:
        headers["authorization"] = request.headers["authorization"]
    return headers


@router.post("/preflight/analyze")
async def preflight_analysis_file(
    request: Request,
    file: UploadFile = File(...),
    collection_name: str = Form("default"),
    test_suite_id: str | None = Form(None),
    strategies: str | None = Form(None),
    current_user: Any = Depends(get_current_user),
) -> Any:
    """
    Proxy preflight analysis with file upload to corpus service.

    The corpus service handles PDF extraction and chunking analysis.
    """
    headers = get_forward_headers(request)

    # Forward the file to corpus service
    files = {"file": (file.filename, await file.read(), file.content_type)}
    data = {
        "collection_name": collection_name,
    }
    if test_suite_id:
        data["test_suite_id"] = test_suite_id
    if strategies:
        data["strategies"] = strategies

    url = f"{CORPUS_SVC_URL}/chunking/preflight/analyze"

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, files=files, data=data, headers=headers)

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return resp.json()


@router.post("/preflight")
async def preflight_analysis(
    request: Request,
    payload: dict[str, Any] = Body(...),
    current_user: Any = Depends(get_current_user),
) -> Any:
    """
    Proxy preflight analysis requests to retrieval service (JSON payload with text).

    Analyzes document structure and recommends optimal chunking strategy.
    """
    headers = get_forward_headers(request)

    url = f"{CORPUS_SVC_URL}/chunking/preflight"

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, json=payload, headers=headers)

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return resp.json()


@router.post("/compare")
async def compare_strategies(
    request: Request,
    payload: dict[str, Any] = Body(...),
    current_user: Any = Depends(get_current_user),
) -> Any:
    """
    Proxy strategy comparison requests to retrieval service.

    Compares multiple chunking strategies with detailed metrics.
    """
    headers = get_forward_headers(request)

    url = f"{CORPUS_SVC_URL}/chunking/compare"

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(url, json=payload, headers=headers)

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return resp.json()


@router.post("/apply")
async def apply_chunking_config(
    request: Request,
    payload: dict[str, Any] = Body(...),
    current_user: Any = Depends(get_current_user),
) -> Any:
    """
    Proxy chunking configuration apply requests to retrieval service.

    Applies specified chunking configuration to a document.
    """
    headers = get_forward_headers(request)

    url = f"{CORPUS_SVC_URL}/chunking/apply"

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, json=payload, headers=headers)

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return resp.json()


@router.get("/strategies")
async def get_available_strategies(
    request: Request,
    current_user: Any = Depends(get_current_user),
) -> Any:
    """
    Proxy get available strategies request to retrieval service.
    """
    headers = get_forward_headers(request)

    url = f"{CORPUS_SVC_URL}/chunking/strategies"

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, headers=headers)

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return resp.json()


@router.get("/strategies/{strategy}/config")
async def get_strategy_config(
    request: Request,
    strategy: str,
    current_user: Any = Depends(get_current_user),
) -> Any:
    """
    Proxy get strategy configuration request to retrieval service.
    """
    headers = get_forward_headers(request)

    url = f"{CORPUS_SVC_URL}/chunking/strategies/{strategy}/config"

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, headers=headers)

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return resp.json()


@router.post("/presets")
async def save_preset(
    request: Request,
    payload: dict[str, Any] = Body(...),
    current_user: Any = Depends(get_current_user),
) -> Any:
    """
    Proxy save preset request to retrieval service.
    """
    headers = get_forward_headers(request)

    url = f"{CORPUS_SVC_URL}/chunking/presets"

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload, headers=headers)

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return resp.json()


@router.get("/presets")
async def get_presets(
    request: Request,
    current_user: Any = Depends(get_current_user),
) -> Any:
    """
    Proxy get presets request to retrieval service.
    """
    headers = get_forward_headers(request)

    url = f"{CORPUS_SVC_URL}/chunking/presets"

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, headers=headers)

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return resp.json()


@router.delete("/presets/{preset_id}")
async def delete_preset(
    request: Request,
    preset_id: str,
    current_user: Any = Depends(get_current_user),
) -> Any:
    """
    Proxy delete preset request to retrieval service.
    """
    headers = get_forward_headers(request)

    url = f"{CORPUS_SVC_URL}/chunking/presets/{preset_id}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.delete(url, headers=headers)

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return resp.json()
