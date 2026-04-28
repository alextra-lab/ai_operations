"""
Public Configuration Router

Read-only endpoints for platform configuration used by the
wizard and other UI components. No admin role required —
any authenticated user can read configuration presets.

ADR-067: Dynamic Categories and Intent Capability Profiles.
"""

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import get_current_user
from shared.auth.models import TokenPayload

from ..db.database import get_async_db

router = APIRouter(
    prefix="/api/v1/config",
    tags=["config"],
)


# ============================================================================
# Response Schemas
# ============================================================================


class CategoryResponse(BaseModel):
    """Category definition returned by the API."""

    category_code: str = Field(description="Unique category identifier (e.g. GENERAL)")
    display_name: str = Field(description="Human-readable category name")
    description: str = Field(description="Category description")
    icon: str = Field(description="Material icon name")
    color: str = Field(description="Hex color code")
    sort_order: int = Field(description="Display sort order")


class IntentTypeResponse(BaseModel):
    """Intent type with capability profile returned by the API."""

    intent_code: str = Field(description="Unique intent identifier (e.g. EXTRACTION)")
    display_name: str = Field(description="Human-readable intent name")
    description: str = Field(description="Intent description")
    category_code: str = Field(description="Parent category code")
    icon: str = Field(description="Material icon name")
    color: str = Field(description="Hex color code")
    is_system: bool = Field(description="Whether this is a built-in system intent")
    default_sampling_preset: str = Field(description="Auto-preset: strict | balanced | creative")
    default_output_format: str = Field(description="Auto-preset: text | json | yaml | structured")
    recommended_capabilities: list[str] = Field(description="Informational capability tags")
    sort_order: int = Field(description="Display sort order")


class CategoriesListResponse(BaseModel):
    """List of all active categories."""

    categories: list[CategoryResponse]
    total: int


class IntentTypesListResponse(BaseModel):
    """List of all active intent types with capability profiles."""

    intent_types: list[IntentTypeResponse]
    total: int


# ============================================================================
# Endpoints
# ============================================================================


@router.get(
    "/categories",
    response_model=CategoriesListResponse,
    summary="List all categories",
    description=(
        "Returns all active categories for use case classification. "
        "Categories are loaded dynamically by the wizard."
    ),
)
async def list_categories(
    _user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """List all active intent categories."""
    result = await db.execute(
        text(
            """
            SELECT category_code, display_name, description,
                   icon, color, sort_order
            FROM intent_categories
            WHERE is_active = TRUE
            ORDER BY sort_order
            """
        )
    )
    rows = result.mappings().all()
    categories = [CategoryResponse(**row) for row in rows]
    return {"categories": categories, "total": len(categories)}


@router.get(
    "/intent-types",
    response_model=IntentTypesListResponse,
    summary="List all intent types with capability profiles",
    description=(
        "Returns all active intent types with their capability "
        "profiles and auto-preset defaults. Used by the wizard "
        "to auto-configure sampling and output format. ADR-067."
    ),
)
async def list_intent_types(
    _user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """List all active intent types with capability profiles."""
    result = await db.execute(
        text(
            """
            SELECT
                it.intent_code,
                it.display_name,
                it.description,
                ic.category_code,
                it.icon,
                it.color,
                it.is_system,
                it.default_sampling_preset,
                it.default_output_format,
                it.recommended_capabilities,
                it.sort_order
            FROM intent_types it
            JOIN intent_categories ic ON ic.id = it.category_id
            WHERE it.is_active = TRUE
              AND ic.is_active = TRUE
            ORDER BY it.sort_order
            """
        )
    )
    rows = result.mappings().all()
    intent_types = [IntentTypeResponse(**row) for row in rows]
    return {"intent_types": intent_types, "total": len(intent_types)}
