"""
Admin API for role-based use case assignments.

Allows administrators to manage which roles have access to which use cases.
Implements ADR-041 role-based use case permissions.

P5-A11: Migrated to async database patterns (Nov 2025).

**Authorization:** Admin-only endpoints
"""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import get_current_user
from shared.auth.models import TokenPayload
from shared.logging_utils.fastapi import configure_logging

from ..db.database import get_async_db
from ..db.models import RoleUseCaseAssignment, UseCase
from ..db.models_rbac import RoleCollectionAssignment
from ..services.rbac_v2 import SYSTEM_ROLES

logger = configure_logging(__name__)
router = APIRouter(prefix="/admin/roles", tags=["admin", "roles"])


# ============================================================================
# System Role Metadata
# ============================================================================


class SystemRoleInfo(BaseModel):
    """System role information with metadata."""

    role_name: str = Field(..., description="System role code")
    display_name: str = Field(..., description="Human-readable role name")
    description: str = Field(..., description="Role description and capabilities")
    is_system_role: bool = Field(True, description="Always true for system roles")


# System role metadata (display names and descriptions)
SYSTEM_ROLE_METADATA: dict[str, dict[str, str]] = {
    "admin": {
        "display_name": "Administrator",
        "description": "Full system access - superuser",
    },
    "corpus_admin": {
        "display_name": "Corpus Administrator",
        "description": "Document and collection management - sees all documents",
    },
    "developer": {
        "display_name": "Developer",
        "description": "Team-scoped use case development - can create/edit use cases for assigned teams",
    },
    "use_case_admin": {
        "display_name": "Use Case Administrator",
        "description": "Use case super admin - sees all use cases across all teams",
    },
    "tools_admin": {
        "display_name": "Tools Administrator",
        "description": "Tool and MCP management",
    },
    "role_admin": {
        "display_name": "Role Administrator",
        "description": "Create roles and assign users to roles",
    },
    "use_case_publisher": {
        "display_name": "Use Case Publisher",
        "description": "Review, approve, and publish use cases",
    },
    "conversations_privileged": {
        "display_name": "Conversations Privileged",
        "description": "Privileged access to multi-turn conversation interface",
    },
    "user": {
        "display_name": "User",
        "description": "Standard end-user - requires grouping roles for use case access",
    },
    "service": {
        "display_name": "Service Account",
        "description": "API automation and service-to-service authentication",
    },
}


# ============================================================================
# Request/Response Models
# ============================================================================


class RoleUseCaseAssignRequest(BaseModel):
    """Request to assign a use case to a role."""

    use_case_id: UUID = Field(..., description="Use case UUID to assign")
    expires_at: datetime | None = Field(None, description="Optional expiration timestamp")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")


class RoleUseCaseAssignResponse(BaseModel):
    """Response for role-use case assignment operations."""

    id: UUID
    role_name: str
    use_case_id: UUID
    use_case_name: str
    granted_by: UUID | None
    granted_at: datetime
    expires_at: datetime | None
    is_active: bool
    metadata: dict

    class Config:
        from_attributes = True


class RoleUseCaseListResponse(BaseModel):
    """List of use cases assigned to a role."""

    role_name: str
    total: int
    active: int
    assignments: list[RoleUseCaseAssignResponse]


class RoleCollectionAssignRequest(BaseModel):
    """Request to assign a collection to a role."""

    collection_id: UUID = Field(..., description="Collection UUID to assign")
    expires_at: datetime | None = Field(None, description="Optional expiration timestamp")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")


class RoleCollectionAssignResponse(BaseModel):
    """Response for role-collection assignment operations."""

    id: UUID
    role_name: str
    collection_id: UUID
    granted_by: UUID | None
    granted_at: datetime
    expires_at: datetime | None
    is_active: bool
    metadata: dict

    class Config:
        from_attributes = True


class RoleCollectionListResponse(BaseModel):
    """List of collections assigned to a role."""

    role_name: str
    total: int
    active: int
    assignments: list[RoleCollectionAssignResponse]


# ============================================================================
# Helper Functions
# ============================================================================


def require_admin(current_user: TokenPayload) -> None:
    """
    Verify current user is admin.

    Raises:
        HTTPException: If user is not admin
    """
    if not current_user.has_role("admin"):
        logger.warning("Non-admin user %s attempted admin operation", current_user.user_id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )


def require_admin_or_role_admin(current_user: TokenPayload) -> None:
    """Allow admin or role_admin."""
    if current_user.has_any_role(["admin", "role_admin"]):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin or role_admin privileges required",
    )


# ============================================================================
# API Endpoints
# ============================================================================


@router.get("/system-roles", response_model=list[SystemRoleInfo])
async def list_system_roles(
    current_user: TokenPayload = Depends(get_current_user),
) -> list[SystemRoleInfo]:
    """
    Get all system roles with metadata (display names and descriptions).

    Returns the complete list of system roles (Tier 1) defined in the platform.
    This endpoint provides dynamic role information for UI components.

    **Authorization:** All authenticated users (public role information)
    """
    return [
        SystemRoleInfo(
            role_name=role_name,
            display_name=SYSTEM_ROLE_METADATA[role_name]["display_name"],
            description=SYSTEM_ROLE_METADATA[role_name]["description"],
            is_system_role=True,
        )
        for role_name in SYSTEM_ROLES
        if role_name in SYSTEM_ROLE_METADATA
    ]


@router.post(
    "/{role_name}/use-cases",
    response_model=RoleUseCaseAssignResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign_use_case_to_role(
    role_name: str,
    request: RoleUseCaseAssignRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> RoleUseCaseAssignResponse:
    """
    Assign a use case to a grouping role (Tier 2).

    Grants execution access to the specified use case for all users with the given role.

    **Important (ADR-060):**
    - System roles (Tier 1) should NOT have use cases assigned to them.
    - System roles grant CAPABILITIES (what you can do), not resource access.
    - Only grouping roles (Tier 2) should have use cases assigned for execution.
    - Examples of grouping roles: `analyst`, `threat_hunting`, `incident_response`

    **Args:**
    - **role_name**: Grouping role name (NOT a system role like admin, developer, user)
    - **use_case_id**: UUID of the use case to assign
    - **expires_at**: Optional expiration timestamp

    **Returns:**
    - Assignment details

    **Authorization:** Admin only
    """
    require_admin(current_user)

    # Validate role name format (alphanumeric + underscores/hyphens)
    import re

    if not re.match(r"^[a-z][a-z0-9_-]{1,49}$", role_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role name format. Must be lowercase alphanumeric with underscores/hyphens, 2-50 chars",
        )

    # Prevent assigning use cases to system roles (Tier 1)
    # System roles grant capabilities, not execution access (ADR-060)
    if role_name in SYSTEM_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot assign use cases to system role '{role_name}'. "
                "System roles (Tier 1) grant capabilities (what you can do), not resource access. "
                "Use grouping roles (Tier 2) like 'analyst', 'threat_hunting', etc. for use case execution access."
            ),
        )

    # Verify use case exists
    result = await db.execute(select(UseCase).where(UseCase.id == request.use_case_id))
    use_case = result.scalar_one_or_none()
    if not use_case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Use case {request.use_case_id} not found",
        )

    # Check if assignment already exists
    result = await db.execute(
        select(RoleUseCaseAssignment).where(
            and_(
                RoleUseCaseAssignment.role_name == role_name,
                RoleUseCaseAssignment.use_case_id == request.use_case_id,
            )
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Update existing assignment (reactivate if inactive)
        existing.is_active = True
        existing.expires_at = request.expires_at
        existing.metadata_json = request.metadata
        existing.granted_by = UUID(current_user.user_id)  # type: ignore[assignment]
        existing.granted_at = datetime.now(tz=UTC)
        await db.commit()
        await db.refresh(existing)

        logger.info(
            "Updated role-use case assignment: %s -> %s",
            role_name,
            use_case.name,
            extra={
                "role_name": role_name,
                "use_case_id": str(request.use_case_id),
                "admin_user_id": str(current_user.user_id),
                "operation": "update",
            },
        )

        return RoleUseCaseAssignResponse(
            id=existing.id,
            role_name=existing.role_name,
            use_case_id=UUID(str(existing.use_case_id)),
            use_case_name=use_case.name,
            granted_by=existing.granted_by,
            granted_at=existing.granted_at,
            expires_at=existing.expires_at,
            is_active=existing.is_active,
            metadata=existing.metadata_json,
        )

    # Create new assignment
    assignment_kwargs = {
        "role_name": role_name,
        "use_case_id": request.use_case_id,
        "granted_by": UUID(current_user.user_id),
        "expires_at": request.expires_at,
        "metadata_json": request.metadata,
    }
    assignment = RoleUseCaseAssignment(**assignment_kwargs)  # type: ignore

    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)

    logger.info(
        "Created role-use case assignment: %s -> %s",
        role_name,
        use_case.name,
        extra={
            "role_name": role_name,
            "use_case_id": str(request.use_case_id),
            "admin_user_id": str(current_user.user_id),
            "operation": "create",
        },
    )

    return RoleUseCaseAssignResponse(
        id=assignment.id,
        role_name=assignment.role_name,
        use_case_id=assignment.use_case_id,
        use_case_name=use_case.name,
        granted_by=assignment.granted_by,
        granted_at=assignment.granted_at,
        expires_at=assignment.expires_at,
        is_active=assignment.is_active,
        metadata=assignment.metadata_json,
    )


@router.delete("/{role_name}/use-cases/{use_case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_use_case_from_role(
    role_name: str,
    use_case_id: UUID,
    permanent: bool = Query(False, description="Permanently delete (true) or deactivate (false)"),
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> None:
    """
    Revoke a use case from a grouping role.

    Removes execution access to the specified use case for all users with the given role.

    **Note:** This endpoint can be used to clean up incorrect assignments to system roles,
    but new assignments to system roles are prevented (see assign_use_case_to_role).

    **Args:**
    - **role_name**: Grouping role name (or system role for cleanup purposes)
    - **use_case_id**: UUID of the use case to revoke
    - **permanent**: If true, permanently delete assignment. If false, deactivate.

    **Returns:**
    - 204 No Content on success

    **Authorization:** Admin only
    """
    require_admin(current_user)

    result = await db.execute(
        select(RoleUseCaseAssignment).where(
            and_(
                RoleUseCaseAssignment.role_name == role_name,
                RoleUseCaseAssignment.use_case_id == use_case_id,
            )
        )
    )
    assignment = result.scalar_one_or_none()

    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assignment not found for role {role_name} and use case {use_case_id}",
        )

    if permanent:
        # Permanent deletion
        from sqlalchemy import delete

        stmt = delete(RoleUseCaseAssignment).where(RoleUseCaseAssignment.id == assignment.id)
        await db.execute(stmt)
        operation = "deleted"
    else:
        # Soft delete (deactivate)
        assignment.is_active = False
        operation = "deactivated"

    await db.commit()

    logger.info(
        "Role-use case assignment %s: %s -> %s",
        operation,
        role_name,
        use_case_id,
        extra={
            "role_name": role_name,
            "use_case_id": str(use_case_id),
            "admin_user_id": str(current_user.user_id),
            "operation": operation,
        },
    )


@router.get("/{role_name}/use-cases", response_model=RoleUseCaseListResponse)
async def get_role_use_cases(
    role_name: str,
    include_inactive: bool = Query(False, description="Include inactive assignments"),
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> RoleUseCaseListResponse:
    """
    Get all use cases assigned to a grouping role.

    **Note:** System roles (Tier 1) should not have use cases assigned.
    This endpoint is primarily for grouping roles (Tier 2) that grant execution access.

    **Args:**
    - **role_name**: Grouping role name (or system role for inspection)
    - **include_inactive**: Include inactive assignments

    **Returns:**
    - List of use case assignments for the role

    **Authorization:** Admin only
    """
    require_admin(current_user)

    # Build query
    stmt = select(RoleUseCaseAssignment).where(RoleUseCaseAssignment.role_name == role_name)

    if not include_inactive:
        stmt = stmt.where(RoleUseCaseAssignment.is_active == True)  # noqa: E712

    result = await db.execute(stmt)
    assignments = result.scalars().all()

    # Fetch use case names
    use_case_ids = [a.use_case_id for a in assignments]
    if use_case_ids:
        result = await db.execute(select(UseCase).where(UseCase.id.in_(use_case_ids)))
        use_cases = result.scalars().all()
        use_case_map = {uc.id: uc.name for uc in use_cases}
    else:
        use_case_map = {}

    # Build response
    response_assignments = [
        RoleUseCaseAssignResponse(
            id=a.id,
            role_name=a.role_name,
            use_case_id=a.use_case_id,
            use_case_name=use_case_map.get(a.use_case_id, "Unknown"),
            granted_by=a.granted_by,
            granted_at=a.granted_at,
            expires_at=a.expires_at,
            is_active=a.is_active,
            metadata=a.metadata_json,
        )
        for a in assignments
    ]

    return RoleUseCaseListResponse(
        role_name=role_name,
        total=len(assignments),
        active=sum(1 for a in assignments if a.is_active),
        assignments=response_assignments,
    )


@router.get("/use-cases/{use_case_id}/roles", response_model=list[str])
async def get_use_case_roles(
    use_case_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> list[str]:
    """
    Get all roles that have access to a use case.

    **Args:**
    - **use_case_id**: UUID of the use case

    **Returns:**
    - List of role names with access to this use case

    **Authorization:** Admin only
    """
    require_admin(current_user)

    # Verify use case exists
    result = await db.execute(select(UseCase).where(UseCase.id == use_case_id))
    use_case = result.scalar_one_or_none()
    if not use_case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Use case {use_case_id} not found",
        )

    # Get active assignments
    now = datetime.now(tz=UTC)
    result = await db.execute(
        select(RoleUseCaseAssignment).where(
            and_(
                RoleUseCaseAssignment.use_case_id == use_case_id,
                RoleUseCaseAssignment.is_active == True,  # noqa: E712
                or_(
                    RoleUseCaseAssignment.expires_at.is_(None),
                    RoleUseCaseAssignment.expires_at > now,
                ),
            )
        )
    )
    assignments = result.scalars().all()

    role_names = [a.role_name for a in assignments]

    # Admin always has access (implicit)
    if "admin" not in role_names:
        role_names.append("admin")

    return sorted(role_names)


# ============================================================================
# Collection assignment endpoints (RBAC V2)
# ============================================================================


@router.post(
    "/{role_name}/collections",
    response_model=RoleCollectionAssignResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign_collection_to_role(
    role_name: str,
    request: RoleCollectionAssignRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> RoleCollectionAssignResponse:
    """Assign a collection to a role (admin or role_admin)."""
    require_admin_or_role_admin(current_user)

    if role_name in SYSTEM_ROLES:
        # System roles already have implicit access; avoid noisy assignments
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="System roles already have access to all collections",
        )

    existing_stmt = select(RoleCollectionAssignment).where(
        RoleCollectionAssignment.role_name == role_name,
        RoleCollectionAssignment.collection_id == request.collection_id,
    )
    existing = (await db.execute(existing_stmt)).scalar_one_or_none()

    if existing:
        existing.is_active = True
        existing.expires_at = request.expires_at
        existing.metadata_json = request.metadata
        existing.granted_by = UUID(current_user.user_id)  # type: ignore[arg-type]
        existing.granted_at = datetime.now(tz=UTC)
        await db.commit()
        await db.refresh(existing)
        return RoleCollectionAssignResponse(
            id=existing.id,
            role_name=existing.role_name,
            collection_id=existing.collection_id,
            granted_by=existing.granted_by,
            granted_at=existing.granted_at,
            expires_at=existing.expires_at,
            is_active=existing.is_active,
            metadata=existing.metadata_json,
        )

    assignment = RoleCollectionAssignment()  # type: ignore[call-arg]
    assignment.role_name = role_name
    assignment.collection_id = request.collection_id
    assignment.granted_by = UUID(current_user.user_id)
    assignment.expires_at = request.expires_at
    assignment.metadata_json = request.metadata
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)

    logger.info(
        "Created role-collection assignment",
        extra={
            "role_name": role_name,
            "collection_id": str(request.collection_id),
            "admin_user_id": str(current_user.user_id),
        },
    )

    return RoleCollectionAssignResponse(
        id=assignment.id,
        role_name=assignment.role_name,
        collection_id=assignment.collection_id,
        granted_by=assignment.granted_by,
        granted_at=assignment.granted_at,
        expires_at=assignment.expires_at,
        is_active=assignment.is_active,
        metadata=assignment.metadata_json,
    )


@router.delete(
    "/{role_name}/collections/{collection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_collection_from_role(
    role_name: str,
    collection_id: UUID,
    permanent: bool = Query(False, description="Permanently delete (true) or deactivate (false)"),
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> None:
    """Revoke collection access for a role."""
    require_admin_or_role_admin(current_user)

    result = await db.execute(
        select(RoleCollectionAssignment).where(
            RoleCollectionAssignment.role_name == role_name,
            RoleCollectionAssignment.collection_id == collection_id,
        )
    )
    assignment = result.scalar_one_or_none()

    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found for role and collection",
        )

    if permanent:
        await db.execute(
            RoleCollectionAssignment.__table__.delete().where(
                RoleCollectionAssignment.id == assignment.id
            )
        )
        operation = "deleted"
    else:
        assignment.is_active = False
        operation = "deactivated"

    await db.commit()

    logger.info(
        "Role-collection assignment %s",
        operation,
        extra={
            "role_name": role_name,
            "collection_id": str(collection_id),
            "admin_user_id": str(current_user.user_id),
        },
    )


@router.get("/{role_name}/collections", response_model=RoleCollectionListResponse)
async def get_role_collections(
    role_name: str,
    include_inactive: bool = Query(False, description="Include inactive assignments"),
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> RoleCollectionListResponse:
    """Get all collections assigned to a role."""
    require_admin_or_role_admin(current_user)

    stmt = select(RoleCollectionAssignment).where(RoleCollectionAssignment.role_name == role_name)
    if not include_inactive:
        stmt = stmt.where(RoleCollectionAssignment.is_active == True)  # noqa: E712

    result = await db.execute(stmt)
    assignments = result.scalars().all()

    response_assignments = [
        RoleCollectionAssignResponse(
            id=a.id,
            role_name=a.role_name,
            collection_id=a.collection_id,
            granted_by=a.granted_by,
            granted_at=a.granted_at,
            expires_at=a.expires_at,
            is_active=a.is_active,
            metadata=a.metadata_json,
        )
        for a in assignments
    ]

    return RoleCollectionListResponse(
        role_name=role_name,
        total=len(assignments),
        active=sum(1 for a in assignments if a.is_active),
        assignments=response_assignments,
    )
