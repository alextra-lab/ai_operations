"""
Template Management Router for AI Operations Platform.

Provides CRUD operations, version control, and approval workflows for prompt templates.
Admin and corpus_admin roles only.
"""

import difflib
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import admin_required, get_current_user
from shared.auth.models import TokenPayload
from shared.logging_utils.fastapi import configure_logging

from ..db.database import get_async_db
from ..db.models import PromptTemplate as DBPromptTemplate
from ..schemas.template_management import (
    TemplateActivationRequest,
    TemplateApprovalRequest,
    TemplateCreate,
    TemplateDiffRequest,
    TemplateDiffResponse,
    TemplateListResponse,
    TemplateRejectionRequest,
    TemplateResponse,
    TemplateUpdate,
    TemplateVersionCreate,
    TemplateVersionListResponse,
    TemplateVersionResponse,
)

logger = configure_logging(service_name="templates_router")

router = APIRouter(prefix="/api/v1/templates", tags=["templates"])


# ============================================================================
# Template CRUD Endpoints
# ============================================================================


@router.get("", response_model=TemplateListResponse, dependencies=[Depends(admin_required)])
async def list_templates(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    template_id_filter: str | None = Query(None, description="Filter by template ID"),
    deployment_status: str | None = Query(None, description="Filter by deployment status"),
    active_only: bool = Query(False, description="Return only active versions"),
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> TemplateListResponse:
    """
    List all prompt templates with filtering and pagination.

    Requires corpus_admin or admin role.
    """
    try:
        logger.info(
            "Listing templates",
            extra={
                "user_id": str(current_user.user_id),
                "page": page,
                "page_size": page_size,
                "filters": {
                    "template_id": template_id_filter,
                    "deployment_status": deployment_status,
                    "active_only": active_only,
                },
            },
        )

        # Build query
        stmt = select(DBPromptTemplate)

        # Apply filters
        if template_id_filter:
            stmt = stmt.where(DBPromptTemplate.template_id == template_id_filter)
        if deployment_status:
            stmt = stmt.where(DBPromptTemplate.deployment_status == deployment_status)
        if active_only:
            stmt = stmt.where(DBPromptTemplate.is_active_version)

        # Get total count
        count_stmt = select(func.count(DBPromptTemplate.id))
        if template_id_filter:
            count_stmt = count_stmt.where(DBPromptTemplate.template_id == template_id_filter)
        if deployment_status:
            count_stmt = count_stmt.where(DBPromptTemplate.deployment_status == deployment_status)
        if active_only:
            count_stmt = count_stmt.where(DBPromptTemplate.is_active_version)
        count_result = await db.execute(count_stmt)
        total_count = count_result.scalar() or 0

        # Apply pagination
        offset = (page - 1) * page_size
        stmt = stmt.order_by(desc(DBPromptTemplate.created_at)).offset(offset).limit(page_size)
        result = await db.execute(stmt)
        templates = result.scalars().all()

        # Convert to response models
        template_responses = [TemplateResponse.model_validate(t) for t in templates]

        logger.info(
            f"Returned {len(template_responses)} templates",
            extra={"total_count": total_count, "user_id": str(current_user.user_id)},
        )

        return TemplateListResponse(
            templates=template_responses,
            total_count=total_count,
            page=page,
            page_size=page_size,
        )

    except Exception as e:
        logger.error(
            f"Error listing templates: {e}",
            extra={"user_id": str(current_user.user_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list templates",
        ) from e


@router.get(
    "/{template_id}",
    response_model=TemplateResponse,
    dependencies=[Depends(admin_required)],
)
async def get_template(
    template_id: str,
    version: int | None = Query(
        None, description="Specific version number (default: active version)"
    ),
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> TemplateResponse:
    """
    Get a specific template by ID.

    Returns the active version by default, or a specific version if requested.
    Requires corpus_admin or admin role.
    """
    try:
        logger.info(
            f"Fetching template: {template_id}",
            extra={
                "user_id": str(current_user.user_id),
                "template_id": template_id,
                "version": version,
            },
        )

        # Build query
        stmt = select(DBPromptTemplate).where(DBPromptTemplate.template_id == template_id)

        if version:
            stmt = stmt.where(DBPromptTemplate.version_number == version)
        else:
            stmt = stmt.where(DBPromptTemplate.is_active_version)

        result = await db.execute(stmt)
        template = result.scalar_one_or_none()

        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template '{template_id}' not found",
            )

        return TemplateResponse.model_validate(template)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error fetching template: {e}",
            extra={"user_id": str(current_user.user_id), "template_id": template_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch template",
        ) from e


@router.post("", response_model=TemplateResponse, dependencies=[Depends(admin_required)])
async def create_template(
    template_data: TemplateCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> TemplateResponse:
    """
    Create a new prompt template.

    Requires corpus_admin or admin role.
    """
    try:
        logger.info(
            f"Creating template: {template_data.template_id}",
            extra={
                "user_id": str(current_user.user_id),
                "template_id": template_data.template_id,
            },
        )

        # Check if template_id already exists
        stmt = select(DBPromptTemplate).where(
            DBPromptTemplate.template_id == template_data.template_id
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Template with ID '{template_data.template_id}' already exists",
            )

        # Create new template
        template_kwargs = {
            "template_id": template_data.template_id,
            "use_case_id": template_data.use_case_id,
            "prompt_type": template_data.prompt_type,
            "version_number": 1,
            "template_content": template_data.template_content,
            "variables": template_data.variables,
            "metadata_json": template_data.metadata_json,
            "is_active_version": True,  # First version is always active
            "deployment_status": template_data.deployment_status,
            "created_by_user_id": UUID(current_user.user_id),
        }
        new_template = DBPromptTemplate(**template_kwargs)  # type: ignore

        db.add(new_template)
        await db.commit()
        await db.refresh(new_template)

        logger.info(
            f"Template created: {template_data.template_id}",
            extra={
                "template_id": template_data.template_id,
                "id": str(new_template.id),
            },
        )

        return TemplateResponse.model_validate(new_template)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(
            f"Error creating template: {e}",
            extra={
                "user_id": str(current_user.user_id),
                "template_id": template_data.template_id,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create template",
        ) from e


@router.put(
    "/{template_id}",
    response_model=TemplateResponse,
    dependencies=[Depends(admin_required)],
)
async def update_template(
    template_id: str,
    template_data: TemplateUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> TemplateResponse:
    """
    Update the active version of a template.

    Only updates the currently active version. To create a new version, use the versions endpoint.
    Requires corpus_admin or admin role.
    """
    try:
        logger.info(
            f"Updating template: {template_id}",
            extra={"user_id": str(current_user.user_id), "template_id": template_id},
        )

        # Get active version
        stmt = select(DBPromptTemplate).where(
            and_(
                DBPromptTemplate.template_id == template_id,
                DBPromptTemplate.is_active_version == True,  # noqa: E712
            )
        )
        result = await db.execute(stmt)
        template = result.scalar_one_or_none()

        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Active version of template '{template_id}' not found",
            )

        # Update fields
        if template_data.template_content is not None:
            template.template_content = template_data.template_content
        if template_data.variables is not None:
            template.variables = template_data.variables
        if template_data.metadata_json is not None:
            template.metadata_json = template_data.metadata_json
        if template_data.deployment_status is not None:
            template.deployment_status = template_data.deployment_status

        await db.commit()
        await db.refresh(template)

        logger.info(
            f"Template updated: {template_id}",
            extra={"template_id": template_id, "id": str(template.id)},
        )

        return TemplateResponse.model_validate(template)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(
            f"Error updating template: {e}",
            extra={"user_id": str(current_user.user_id), "template_id": template_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update template",
        ) from e


@router.delete("/{template_id}", dependencies=[Depends(admin_required)])
async def delete_template(
    template_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> dict:
    """
    Delete all versions of a template.

    This is a destructive operation that removes all versions of the template.
    Requires corpus_admin or admin role.
    """
    try:
        logger.info(
            f"Deleting template: {template_id}",
            extra={"user_id": str(current_user.user_id), "template_id": template_id},
        )

        # Get all versions
        stmt = select(DBPromptTemplate).where(DBPromptTemplate.template_id == template_id)
        result = await db.execute(stmt)
        templates = result.scalars().all()

        if not templates:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template '{template_id}' not found",
            )

        # Delete all versions
        from sqlalchemy import delete

        delete_stmt = delete(DBPromptTemplate).where(DBPromptTemplate.template_id == template_id)
        await db.execute(delete_stmt)
        await db.commit()

        logger.info(
            f"Template deleted: {template_id}",
            extra={"template_id": template_id, "versions_deleted": len(templates)},
        )

        return {
            "message": f"Template '{template_id}' deleted successfully",
            "versions_deleted": len(templates),
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(
            f"Error deleting template: {e}",
            extra={"user_id": str(current_user.user_id), "template_id": template_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete template",
        ) from e


# ============================================================================
# Version Control Endpoints
# ============================================================================


@router.get(
    "/{template_id}/versions",
    response_model=TemplateVersionListResponse,
    dependencies=[Depends(admin_required)],
)
async def get_template_versions(
    template_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> TemplateVersionListResponse:
    """
    Get all versions of a template.

    Returns version history ordered by version number descending.
    Requires corpus_admin or admin role.
    """
    try:
        logger.info(
            f"Fetching template versions: {template_id}",
            extra={"user_id": str(current_user.user_id), "template_id": template_id},
        )

        # Get all versions
        stmt = (
            select(DBPromptTemplate)
            .where(DBPromptTemplate.template_id == template_id)
            .order_by(desc(DBPromptTemplate.version_number))
        )
        result = await db.execute(stmt)
        versions = result.scalars().all()

        if not versions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template '{template_id}' not found",
            )

        version_responses = [TemplateVersionResponse.model_validate(v) for v in versions]

        return TemplateVersionListResponse(
            template_id=template_id,
            versions=version_responses,
            total_versions=len(version_responses),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error fetching template versions: {e}",
            extra={"user_id": str(current_user.user_id), "template_id": template_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch template versions",
        ) from e


@router.post(
    "/{template_id}/versions",
    response_model=TemplateResponse,
    dependencies=[Depends(admin_required)],
)
async def create_template_version(
    template_id: str,
    version_data: TemplateVersionCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> TemplateResponse:
    """
    Create a new version of an existing template.

    The new version becomes the active version automatically.
    Requires corpus_admin or admin role.
    """
    try:
        logger.info(
            f"Creating new version for template: {template_id}",
            extra={"user_id": str(current_user.user_id), "template_id": template_id},
        )

        # Get the latest version to copy metadata
        stmt = (
            select(DBPromptTemplate)
            .where(DBPromptTemplate.template_id == template_id)
            .order_by(desc(DBPromptTemplate.version_number))
        )
        result = await db.execute(stmt)
        latest = result.scalar_one_or_none()

        if not latest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template '{template_id}' not found",
            )

        # Deactivate all existing versions
        update_stmt = (
            update(DBPromptTemplate)
            .where(DBPromptTemplate.template_id == template_id)
            .values(is_active_version=False)
        )
        await db.execute(update_stmt)

        # Create new version
        new_version_number = latest.version_number + 1

        # Merge change notes into metadata if provided
        new_metadata = version_data.metadata_json.copy()
        if version_data.change_notes:
            new_metadata["change_notes"] = version_data.change_notes

        version_kwargs = {
            "template_id": template_id,
            "use_case_id": latest.use_case_id,
            "prompt_type": latest.prompt_type,
            "version_number": new_version_number,
            "template_content": version_data.template_content,
            "variables": version_data.variables,
            "metadata_json": new_metadata,
            "is_active_version": True,
            "deployment_status": "draft",  # New versions start as draft
            "created_by_user_id": UUID(current_user.user_id),
        }
        new_version = DBPromptTemplate(**version_kwargs)  # type: ignore

        db.add(new_version)
        await db.commit()
        await db.refresh(new_version)

        logger.info(
            f"New template version created: {template_id} v{new_version_number}",
            extra={"template_id": template_id, "version_number": new_version_number},
        )

        return TemplateResponse.model_validate(new_version)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(
            f"Error creating template version: {e}",
            extra={"user_id": str(current_user.user_id), "template_id": template_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create template version",
        ) from e


@router.post(
    "/{template_id}/activate",
    response_model=TemplateResponse,
    dependencies=[Depends(admin_required)],
)
async def activate_template_version(
    template_id: str,
    activation_data: TemplateActivationRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> TemplateResponse:
    """
    Activate a specific version of a template.

    Deactivates all other versions and sets the specified version as active.
    Requires corpus_admin or admin role.
    """
    try:
        logger.info(
            f"Activating template version: {template_id} v{activation_data.version_number}",
            extra={
                "user_id": str(current_user.user_id),
                "template_id": template_id,
                "version_number": activation_data.version_number,
            },
        )

        # Get the target version
        stmt = select(DBPromptTemplate).where(
            and_(
                DBPromptTemplate.template_id == template_id,
                DBPromptTemplate.version_number == activation_data.version_number,
            )
        )
        result = await db.execute(stmt)
        target_version = result.scalar_one_or_none()

        if not target_version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Version {activation_data.version_number} of template '{template_id}' not found",
            )

        # Deactivate all versions
        update_stmt = (
            update(DBPromptTemplate)
            .where(DBPromptTemplate.template_id == template_id)
            .values(is_active_version=False)
        )
        await db.execute(update_stmt)

        # Activate target version
        target_version.is_active_version = True
        await db.commit()
        await db.refresh(target_version)

        logger.info(
            f"Template version activated: {template_id} v{activation_data.version_number}",
            extra={
                "template_id": template_id,
                "version_number": activation_data.version_number,
            },
        )

        return TemplateResponse.model_validate(target_version)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(
            f"Error activating template version: {e}",
            extra={
                "user_id": str(current_user.user_id),
                "template_id": template_id,
                "version_number": activation_data.version_number,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate template version",
        ) from e


@router.post(
    "/{template_id}/diff",
    response_model=TemplateDiffResponse,
    dependencies=[Depends(admin_required)],
)
async def compare_template_versions(
    template_id: str,
    diff_request: TemplateDiffRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> TemplateDiffResponse:
    """
    Compare two versions of a template.

    Returns a unified diff of the template content and metadata changes.
    Requires corpus_admin or admin role.
    """
    try:
        logger.info(
            f"Comparing template versions: {template_id} v{diff_request.version_1} vs v{diff_request.version_2}",
            extra={
                "user_id": str(current_user.user_id),
                "template_id": template_id,
                "version_1": diff_request.version_1,
                "version_2": diff_request.version_2,
            },
        )

        # Get both versions
        stmt_1 = select(DBPromptTemplate).where(
            and_(
                DBPromptTemplate.template_id == template_id,
                DBPromptTemplate.version_number == diff_request.version_1,
            )
        )
        result_1 = await db.execute(stmt_1)
        version_1 = result_1.scalar_one_or_none()

        stmt_2 = select(DBPromptTemplate).where(
            and_(
                DBPromptTemplate.template_id == template_id,
                DBPromptTemplate.version_number == diff_request.version_2,
            )
        )
        result_2 = await db.execute(stmt_2)
        version_2 = result_2.scalar_one_or_none()

        if not version_1:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Version {diff_request.version_1} not found",
            )

        if not version_2:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Version {diff_request.version_2} not found",
            )

        # Generate diff
        content_1 = version_1.template_content.splitlines(keepends=True)
        content_2 = version_2.template_content.splitlines(keepends=True)
        diff = "".join(
            difflib.unified_diff(
                content_1,
                content_2,
                fromfile=f"v{diff_request.version_1}",
                tofile=f"v{diff_request.version_2}",
            )
        )

        # Compare variables
        vars_1 = set(version_1.variables)
        vars_2 = set(version_2.variables)
        variables_added = list(vars_2 - vars_1)
        variables_removed = list(vars_1 - vars_2)

        # Simple metadata comparison
        metadata_changes = {
            "version_1_keys": list(version_1.metadata_json.keys()),
            "version_2_keys": list(version_2.metadata_json.keys()),
        }

        return TemplateDiffResponse(
            template_id=template_id,
            version_1=diff_request.version_1,
            version_2=diff_request.version_2,
            content_diff=diff,
            variables_added=variables_added,
            variables_removed=variables_removed,
            metadata_changes=metadata_changes,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error comparing template versions: {e}",
            extra={"user_id": str(current_user.user_id), "template_id": template_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compare template versions",
        ) from e


# ============================================================================
# Approval Workflow Endpoints
# ============================================================================


@router.post(
    "/{template_id}/approve",
    response_model=TemplateResponse,
    dependencies=[Depends(admin_required)],
)
async def approve_template(
    template_id: str,
    approval_data: TemplateApprovalRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> TemplateResponse:
    """
    Approve the active version of a template for deployment.

    Sets deployment_status to 'approved' and records the approver and approval time.
    Requires corpus_admin or admin role.
    """
    try:
        logger.info(
            f"Approving template: {template_id}",
            extra={"user_id": str(current_user.user_id), "template_id": template_id},
        )

        # Get active version
        stmt = select(DBPromptTemplate).where(
            and_(
                DBPromptTemplate.template_id == template_id,
                DBPromptTemplate.is_active_version == True,  # noqa: E712
            )
        )
        result = await db.execute(stmt)
        template = result.scalar_one_or_none()

        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Active version of template '{template_id}' not found",
            )

        # Update approval fields
        template.deployment_status = "approved"
        template.approved_by_user_id = UUID(current_user.user_id)
        template.approved_at = datetime.now(UTC)

        # Add approval notes to metadata if provided
        if approval_data.approval_notes:
            metadata = template.metadata_json.copy()
            metadata["approval_notes"] = approval_data.approval_notes
            template.metadata_json = metadata

        await db.commit()
        await db.refresh(template)

        logger.info(
            f"Template approved: {template_id}",
            extra={
                "template_id": template_id,
                "approved_by": str(current_user.user_id),
            },
        )

        return TemplateResponse.model_validate(template)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(
            f"Error approving template: {e}",
            extra={"user_id": str(current_user.user_id), "template_id": template_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to approve template",
        ) from e


@router.post(
    "/{template_id}/reject",
    response_model=TemplateResponse,
    dependencies=[Depends(admin_required)],
)
async def reject_template(
    template_id: str,
    rejection_data: TemplateRejectionRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> TemplateResponse:
    """
    Reject the active version of a template.

    Sets deployment_status back to 'draft' and records rejection reason.
    Requires corpus_admin or admin role.
    """
    try:
        logger.info(
            f"Rejecting template: {template_id}",
            extra={"user_id": str(current_user.user_id), "template_id": template_id},
        )

        # Get active version
        stmt = select(DBPromptTemplate).where(
            and_(
                DBPromptTemplate.template_id == template_id,
                DBPromptTemplate.is_active_version == True,  # noqa: E712
            )
        )
        result = await db.execute(stmt)
        template = result.scalar_one_or_none()

        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Active version of template '{template_id}' not found",
            )

        # Update status and add rejection reason to metadata
        template.deployment_status = "draft"
        metadata = template.metadata_json.copy()
        metadata["rejection_reason"] = rejection_data.rejection_reason
        metadata["rejected_by"] = str(current_user.user_id)
        metadata["rejected_at"] = datetime.now(UTC).isoformat()
        template.metadata_json = metadata

        await db.commit()
        await db.refresh(template)

        logger.info(
            f"Template rejected: {template_id}",
            extra={
                "template_id": template_id,
                "rejected_by": str(current_user.user_id),
            },
        )

        return TemplateResponse.model_validate(template)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(
            f"Error rejecting template: {e}",
            extra={"user_id": str(current_user.user_id), "template_id": template_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reject template",
        ) from e
