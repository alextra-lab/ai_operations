"""
Run Manifests Router for Stateless Core v1

This module implements the run manifests API endpoints for telemetry
capture and storage in the stateless architecture (ADR-030).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.database import get_async_db
from ..schemas.run_manifest import (
    ResultKind,
    RunManifest,
    RunManifestCreate,
    RunManifestQuery,
    RunManifestStats,
    RunManifestSummary,
    RunManifestUpdate,
)
from ..services.run_manifest_service import RunManifestService

router = APIRouter(prefix="/api/v1/run-manifests", tags=["run-manifests"])


@router.post("/", response_model=RunManifest)
async def create_run_manifest(
    manifest_data: RunManifestCreate,
    db: AsyncSession = Depends(get_async_db),
) -> RunManifest:
    """
    Create a new run manifest.

    Args:
        manifest_data: Run manifest data to create
        db: Database session

    Returns:
        Created run manifest
    """
    service = RunManifestService(db)
    return await service.create_manifest(manifest_data)


@router.get("/{run_id}", response_model=RunManifest)
async def get_run_manifest(
    run_id: UUID,
    db: AsyncSession = Depends(get_async_db),
) -> RunManifest:
    """
    Get a run manifest by ID.

    Args:
        run_id: Run manifest ID
        db: Database session

    Returns:
        Run manifest details

    Raises:
        HTTPException: If manifest not found
    """
    service = RunManifestService(db)
    manifest = await service.get_manifest(run_id)

    if not manifest:
        raise HTTPException(status_code=404, detail="Run manifest not found")

    return manifest


@router.put("/{run_id}", response_model=RunManifest)
async def update_run_manifest(
    run_id: UUID,
    update_data: RunManifestUpdate,
    db: AsyncSession = Depends(get_async_db),
) -> RunManifest:
    """
    Update a run manifest.

    Args:
        run_id: Run manifest ID
        update_data: Update data
        db: Database session

    Returns:
        Updated run manifest

    Raises:
        HTTPException: If manifest not found
    """
    service = RunManifestService(db)
    manifest = await service.update_manifest(run_id, update_data)

    if not manifest:
        raise HTTPException(status_code=404, detail="Run manifest not found")

    return manifest


@router.get("/", response_model=list[RunManifest])
async def query_run_manifests(
    use_case_id: str | None = Query(None, description="Filter by use case ID"),
    result_kind: str | None = Query(None, description="Filter by result kind"),
    start_date: str | None = Query(None, description="Filter by start date (ISO format)"),
    end_date: str | None = Query(None, description="Filter by end date (ISO format)"),
    min_conformance: float | None = Query(
        None, ge=0.0, le=1.0, description="Minimum conformance score"
    ),
    max_latency_ms: int | None = Query(None, ge=0, description="Maximum latency in milliseconds"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: AsyncSession = Depends(get_async_db),
) -> list[RunManifest]:
    """
    Query run manifests with filters.

    Args:
        use_case_id: Filter by use case ID
        result_kind: Filter by result kind
        start_date: Filter by start date
        end_date: Filter by end date
        min_conformance: Minimum conformance score
        max_latency_ms: Maximum latency
        limit: Maximum number of results
        offset: Number of results to skip
        db: Database session

    Returns:
        List of matching run manifests
    """
    from datetime import datetime

    # Parse dates if provided
    parsed_start_date = None
    parsed_end_date = None

    if start_date:
        try:
            parsed_start_date = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid start_date format. Use ISO format."
            )

    if end_date:
        try:
            parsed_end_date = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use ISO format.")

    # Convert result_kind string to enum if provided
    parsed_result_kind = None
    if result_kind:
        try:
            parsed_result_kind = ResultKind(result_kind)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid result_kind. Must be one of: {[e.value for e in ResultKind]}",
            )

    query = RunManifestQuery(
        use_case_id=use_case_id,
        result_kind=parsed_result_kind,
        start_date=parsed_start_date,
        end_date=parsed_end_date,
        min_conformance=min_conformance,
        max_latency_ms=max_latency_ms,
        limit=limit,
        offset=offset,
    )

    service = RunManifestService(db)
    return await service.query_manifests(query)


@router.get("/stats/overview", response_model=RunManifestStats)
async def get_run_manifest_stats(
    use_case_id: str | None = Query(None, description="Filter by use case ID"),
    db: AsyncSession = Depends(get_async_db),
) -> RunManifestStats:
    """
    Get run manifest statistics.

    Args:
        use_case_id: Optional use case ID to filter by
        db: Database session

    Returns:
        Run manifest statistics
    """
    service = RunManifestService(db)
    return await service.get_manifest_stats(use_case_id=use_case_id)


@router.get("/stats/summaries", response_model=list[RunManifestSummary])
async def get_run_manifest_summaries(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of summaries"),
    db: AsyncSession = Depends(get_async_db),
) -> list[RunManifestSummary]:
    """
    Get run manifest summaries grouped by use case.

    Args:
        limit: Maximum number of summaries to return
        db: Database session

    Returns:
        List of run manifest summaries
    """
    service = RunManifestService(db)
    return await service.get_manifest_summaries(limit=limit)
