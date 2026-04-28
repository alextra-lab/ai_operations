"""
Capabilities Router for Stateless Core v1

This module implements the capabilities API endpoints for feature flag
management and edition-based capability control (ADR-032).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.database import get_async_db
from ..schemas.capabilities import (
    Capability,
    CapabilityCategory,
    CapabilityStatus,
    EditionCapabilities,
    FeatureFlags,
)
from ..services.capabilities_service import CapabilitiesService

router = APIRouter(prefix="/api/v1/capabilities", tags=["capabilities"])

# Global capabilities service instance
_capabilities_service = CapabilitiesService()


@router.get("/", response_model=list[Capability])
async def get_capabilities(
    edition: str | None = Query(None, description="Filter by edition (core, plus)"),
    category: CapabilityCategory | None = Query(None, description="Filter by category"),
    status: CapabilityStatus | None = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_async_db),
) -> list[Capability]:
    """
    Get system capabilities with optional filtering.

    Args:
        edition: Filter by edition
        category: Filter by category
        status: Filter by status
        db: Database session

    Returns:
        List of matching capabilities
    """
    return _capabilities_service.get_capabilities(
        edition=edition,
        category=category,
        status=status,
    )


@router.get("/feature-flags", response_model=FeatureFlags)
async def get_feature_flags(
    db: AsyncSession = Depends(get_async_db),
) -> FeatureFlags:
    """
    Get current feature flags.

    Args:
        db: Database session

    Returns:
        Current feature flags
    """
    return _capabilities_service.get_feature_flags()


@router.put("/feature-flags", response_model=FeatureFlags)
async def update_feature_flags(
    flags: FeatureFlags,
    db: AsyncSession = Depends(get_async_db),
) -> FeatureFlags:
    """
    Update feature flags.

    Args:
        flags: New feature flags
        db: Database session

    Returns:
        Updated feature flags
    """
    _capabilities_service.update_feature_flags(flags)
    return _capabilities_service.get_feature_flags()


@router.get("/editions/{edition}", response_model=EditionCapabilities)
async def get_edition_capabilities(
    edition: str,
    db: AsyncSession = Depends(get_async_db),
) -> EditionCapabilities:
    """
    Get capabilities for a specific edition.

    Args:
        edition: Edition name (core, plus)
        db: Database session

    Returns:
        Edition capabilities

    Raises:
        HTTPException: If edition not found
    """
    if edition not in ["core", "plus"]:
        raise HTTPException(status_code=400, detail="Invalid edition. Must be 'core' or 'plus'")

    return _capabilities_service.get_edition_capabilities(edition)


@router.get("/categories", response_model=list[str])
async def get_capability_categories(
    db: AsyncSession = Depends(get_async_db),
) -> list[str]:
    """
    Get all capability categories.

    Args:
        db: Database session

    Returns:
        List of capability categories
    """
    categories = _capabilities_service.get_capability_categories()
    return [cat.value for cat in categories]


@router.get("/statuses", response_model=list[str])
async def get_capability_statuses(
    db: AsyncSession = Depends(get_async_db),
) -> list[str]:
    """
    Get all capability statuses.

    Args:
        db: Database session

    Returns:
        List of capability statuses
    """
    statuses = _capabilities_service.get_capability_statuses()
    return [status.value for status in statuses]


@router.get("/system/info")
async def get_system_info(
    db: AsyncSession = Depends(get_async_db),
) -> dict:
    """
    Get system capability information.

    Args:
        db: Database session

    Returns:
        System information
    """
    return _capabilities_service.get_system_info()


@router.get("/system/simple")
async def get_simple_capabilities() -> dict:
    """
    Get simplified capabilities for frontend UI adaptation.

    This is a lightweight endpoint for the frontend to quickly check
    system capabilities without fetching the full capability list.

    Follows ADR-032: Capabilities & Edition Flags

    Returns:
        Simplified capability flags:
        - stateless: bool (client-owned sessions)
        - stateful: bool (server-side history)
        - history: str (provider type: 'none', 'governed')
        - evidence: str (sink type: 'none', 'worm')
        - exports: list[str] (available export formats)
        - edition: str ('core', 'plus')
        - features: dict (feature flags)
    """
    feature_flags = _capabilities_service.get_feature_flags()

    return {
        "stateless": True,  # v1 is stateless by default
        "stateful": False,  # Stateful features disabled in v1
        "history": "none",
        "evidence": "none",
        "crypto": "none",
        "exports": ["md", "json"],  # PDF coming in v1.1
        "edition": "core",
        "features": {
            "run_manifests": feature_flags.run_manifests,
            "preflight_analysis": feature_flags.preflight_analysis,
            "test_suites": True,
            "exemplar_selection": True,
            "ephemeral_collections": False,  # Coming in Layer 4
            "expert_chunking": feature_flags.expert_chunking,
            "advanced_analytics": feature_flags.advanced_analytics,
            "quality_metrics": feature_flags.quality_metrics,
        },
    }


@router.get("/{capability_name}", response_model=Capability)
async def get_capability(
    capability_name: str,
    db: AsyncSession = Depends(get_async_db),
) -> Capability:
    """
    Get a specific capability by name.

    Args:
        capability_name: Name of the capability
        db: Database session

    Returns:
        Capability details

    Raises:
        HTTPException: If capability not found
    """
    capability = _capabilities_service.get_capability(capability_name)
    if not capability:
        raise HTTPException(status_code=404, detail="Capability not found")

    return capability


@router.get("/{capability_name}/available")
async def check_capability_available(
    capability_name: str,
    db: AsyncSession = Depends(get_async_db),
) -> dict:
    """
    Check if a capability is available.

    Args:
        capability_name: Name of the capability
        db: Database session

    Returns:
        Availability status
    """
    is_available = _capabilities_service.is_capability_available(capability_name)
    return {
        "capability": capability_name,
        "available": is_available,
    }
