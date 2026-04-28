"""
Output Template Management Router for AI Operations Platform.

Provides CRUD operations for custom output visualization templates.
Built-in templates are read-only; custom templates support full CRUD.

Admin role required for all write operations.

@see ADR-066: Domain-Neutral Visualization Template Architecture
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import admin_required, get_current_user
from shared.auth.models import TokenPayload
from shared.logging_utils.fastapi import configure_logging

from ..db.database import get_async_db
from ..db.models import OutputTemplate as DBOutputTemplate
from ..schemas.output_template import (
    OutputTemplateCreate,
    OutputTemplateListResponse,
    OutputTemplateResponse,
    OutputTemplateUpdate,
)

logger = configure_logging(service_name="output_templates_router")

router = APIRouter(
    prefix="/api/v1/admin/output-templates",
    tags=["output-templates"],
)


@router.get(
    "",
    response_model=OutputTemplateListResponse,
    dependencies=[Depends(get_current_user)],
)
async def list_output_templates(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> OutputTemplateListResponse:
    """List all output templates (built-in + custom)."""
    logger.info(
        "Listing output templates",
        extra={
            "user_id": str(current_user.user_id),
            "page": page,
            "page_size": page_size,
        },
    )

    # Count total
    count_stmt = select(func.count()).select_from(DBOutputTemplate)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # Fetch page
    offset = (page - 1) * page_size
    stmt = (
        select(DBOutputTemplate)
        .order_by(desc(DBOutputTemplate.created_at))
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    templates = result.scalars().all()

    return OutputTemplateListResponse(
        templates=[OutputTemplateResponse.model_validate(t) for t in templates],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{template_id}",
    response_model=OutputTemplateResponse,
    dependencies=[Depends(get_current_user)],
)
async def get_output_template(
    template_id: str,
    db: AsyncSession = Depends(get_async_db),
) -> OutputTemplateResponse:
    """Get a single output template by template_id slug."""
    stmt = select(DBOutputTemplate).where(DBOutputTemplate.template_id == template_id)
    result = await db.execute(stmt)
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Output template '{template_id}' not found",
        )

    return OutputTemplateResponse.model_validate(template)


@router.post(
    "",
    response_model=OutputTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(admin_required)],
)
async def create_output_template(
    payload: OutputTemplateCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> OutputTemplateResponse:
    """Create a new custom output template."""
    # Check for duplicate template_id
    existing_stmt = select(DBOutputTemplate).where(
        DBOutputTemplate.template_id == payload.template_id
    )
    existing_result = await db.execute(existing_stmt)
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Template '{payload.template_id}' already exists",
        )

    db_template = DBOutputTemplate()
    db_template.template_id = payload.template_id
    db_template.name = payload.name
    db_template.description = payload.description
    db_template.is_builtin = False
    db_template.data_schema = payload.data_schema
    db_template.layout = payload.layout
    db_template.export_formats = payload.export_formats
    db_template.created_by = UUID(str(current_user.user_id))

    db.add(db_template)
    await db.commit()
    await db.refresh(db_template)

    logger.info(
        "Created custom output template",
        extra={
            "template_id": payload.template_id,
            "user_id": str(current_user.user_id),
        },
    )

    return OutputTemplateResponse.model_validate(db_template)


@router.put(
    "/{template_id}",
    response_model=OutputTemplateResponse,
    dependencies=[Depends(admin_required)],
)
async def update_output_template(
    template_id: str,
    payload: OutputTemplateUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> OutputTemplateResponse:
    """Update a custom output template. Built-in templates cannot be updated."""
    stmt = select(DBOutputTemplate).where(DBOutputTemplate.template_id == template_id)
    result = await db.execute(stmt)
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Output template '{template_id}' not found",
        )

    if template.is_builtin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Built-in templates cannot be modified",
        )

    # Apply partial update
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)

    await db.commit()
    await db.refresh(template)

    logger.info(
        "Updated custom output template",
        extra={
            "template_id": template_id,
            "user_id": str(current_user.user_id),
            "updated_fields": list(update_data.keys()),
        },
    )

    return OutputTemplateResponse.model_validate(template)


@router.delete(
    "/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(admin_required)],
)
async def delete_output_template(
    template_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> None:
    """Delete a custom output template. Built-in templates cannot be deleted."""
    stmt = select(DBOutputTemplate).where(DBOutputTemplate.template_id == template_id)
    result = await db.execute(stmt)
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Output template '{template_id}' not found",
        )

    if template.is_builtin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Built-in templates cannot be deleted",
        )

    await db.delete(template)
    await db.commit()

    logger.info(
        "Deleted custom output template",
        extra={
            "template_id": template_id,
            "user_id": str(current_user.user_id),
        },
    )
