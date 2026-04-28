"""
Admin API for managing user role memberships (RBAC V2).

Allows administrators to assign/remove system roles, grouping roles, and teams
for users. Implements ADR-060 two-tier RBAC architecture.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from shared.auth import get_current_user
from shared.auth.models import TokenPayload
from shared.logging_utils.fastapi import configure_logging

from ..db.database import get_async_db
from ..db.models import AuthUser, UserRoleMembership
from ..services.rbac_v2 import SYSTEM_ROLES

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = configure_logging(__name__)
router = APIRouter(
    prefix="/api/v1/admin/users",
    tags=["Admin - User Roles"],
)


class UserRoleInfo(BaseModel):
    """Information about a user's role membership."""

    role: str
    granted_by: UUID | None = None
    granted_at: datetime | None = None
    metadata: dict = Field(default_factory=dict)


class UserRolesResponse(BaseModel):
    """Response containing all roles for a user."""

    user_id: UUID
    system_roles: list[str] = Field(default_factory=list)
    grouping_roles: list[str] = Field(default_factory=list)
    teams: list[str] = Field(default_factory=list)
    all_roles: list[UserRoleInfo] = Field(default_factory=list)


class UpdateUserRolesRequest(BaseModel):
    """Request to update user roles."""

    system_roles: list[str] = Field(default_factory=list, description="System roles to assign")
    grouping_roles: list[str] = Field(default_factory=list, description="Grouping roles to assign")
    teams: list[str] = Field(
        default_factory=list, description="Teams to assign (must start with 'team:')"
    )


def _extract_user_context(
    current_user: TokenPayload | dict,
) -> tuple[str | None, list[str], str | None]:
    """
    Safely extract role, scopes, and user_id from token payload.

    For multi-role support (ADR-060), returns first role from roles array
    for backward compatibility with logging code.
    """
    role = None
    scopes: list[str] = []
    user_id: str | None = None

    if isinstance(current_user, dict):
        # Handle dict (backward compatibility)
        roles = current_user.get("roles", [])
        if roles:
            role = roles[0]  # Use first role for logging
        elif "role" in current_user:
            role = current_user.get("role")  # Legacy single role
        scopes = current_user.get("scopes") or []
        user_id = current_user.get("user_id")
    else:
        # Handle TokenPayload object (multi-role support per ADR-060)
        if hasattr(current_user, "roles") and current_user.roles:
            role = current_user.roles[0]  # Use first role for logging
        elif hasattr(current_user, "role"):
            role = getattr(current_user, "role", None)  # Legacy single role
        scopes = getattr(current_user, "scopes", None) or []
        user_id = getattr(current_user, "user_id", None)

    # Normalize scopes to list[str]
    if not isinstance(scopes, list):
        try:
            scopes = list(scopes)
        except Exception:
            scopes = []

    return role, scopes, user_id


def require_admin_or_role_admin(current_user: TokenPayload | dict) -> None:
    """Require admin or role_admin privileges."""
    # Handle TokenPayload object (multi-role support per ADR-060)
    if isinstance(current_user, TokenPayload):
        if current_user.has_any_role(["admin", "role_admin"]):
            return
    # Handle dict (backward compatibility)
    elif isinstance(current_user, dict):
        roles = current_user.get("roles", [])
        if "admin" in roles or "role_admin" in roles:
            return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin or role_admin privileges required",
    )


async def _assert_user_exists(user_id: UUID, db: AsyncSession) -> AuthUser:
    """Verify user exists and return the user object."""
    stmt = select(AuthUser).where(AuthUser.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )
    return user


@router.get("/{user_id}")
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> dict:
    """
    Get user details by ID (admin only).

    This endpoint provides user information for admin interfaces.
    For role information, use /{user_id}/roles.
    """
    try:
        require_admin_or_role_admin(current_user)
        user = await _assert_user_exists(user_id, db)
        return {
            "id": str(user.id),
            "username": user.username,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role or "user",
            "is_active": user.is_active,
            "user_metadata": user.user_metadata or {},
            "created_at": user.created_at.isoformat() if user.created_at is not None else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at is not None else None,
            "last_login": user.last_login.isoformat() if user.last_login is not None else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error retrieving user",
            exc_info=True,
            extra={"user_id": str(user_id), "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user",
        ) from e


@router.get("/{user_id}/roles", response_model=UserRolesResponse)
async def get_user_roles(
    user_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> UserRolesResponse:
    """
    Get all roles assigned to a user.

    Returns system roles, grouping roles, and teams separately.
    """
    try:
        require_admin_or_role_admin(current_user)
        await _assert_user_exists(user_id, db)

        # Get all role memberships from user_roles table
        stmt = select(UserRoleMembership).where(UserRoleMembership.user_id == user_id)
        result = await db.execute(stmt)
        memberships = result.scalars().all()

        all_roles_list: list[str] = []
        grouping_roles_list: list[str] = []
        teams_list: list[str] = []
        system_roles: list[str] = []

        role_info_list: list[UserRoleInfo] = []

        for membership in memberships:
            role_name = membership.role
            if not role_name:
                continue
            all_roles_list.append(role_name)

            if role_name in SYSTEM_ROLES:
                if role_name not in system_roles:
                    system_roles.append(role_name)
            elif role_name.startswith("team:"):
                teams_list.append(role_name)
            else:
                grouping_roles_list.append(role_name)

            role_info_list.append(
                UserRoleInfo(
                    role=role_name,
                    granted_by=membership.granted_by,
                    granted_at=membership.created_at,
                    metadata=membership.metadata_json or {},
                )
            )

        return UserRolesResponse(
            user_id=user_id,
            system_roles=system_roles,
            grouping_roles=grouping_roles_list,
            teams=teams_list,
            all_roles=role_info_list,
        )
    except HTTPException:
        raise
    except Exception as e:
        role, scopes, admin_user_id = _extract_user_context(current_user)
        logger.error(
            "Error retrieving user roles",
            exc_info=True,
            extra={
                "user_id": str(user_id),
                "admin_user_id": str(admin_user_id or ""),
                "role": role,
                "scopes": scopes,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user roles",
        ) from e


@router.put("/{user_id}/roles", response_model=UserRolesResponse)
async def update_user_roles(
    user_id: UUID,
    request: UpdateUserRolesRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> UserRolesResponse:
    """
    Update all roles for a user (bulk operation).

    Replaces existing role memberships with the provided lists.
    System roles are stored in users.role (single value) and user_roles table.
    Grouping roles and teams are stored in user_roles table.
    """
    try:
        role, scopes, admin_user_id = _extract_user_context(current_user)
        require_admin_or_role_admin(current_user)
        user = await _assert_user_exists(user_id, db)

        # Validate system roles (should be single value, but allow multiple for flexibility)
        if len(request.system_roles) > 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only one system role can be assigned (primary role)",
            )

        # Validate all system roles are valid
        for system_role in request.system_roles:
            if system_role not in SYSTEM_ROLES:
                valid_roles = ", ".join(SYSTEM_ROLES)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid system role: {system_role}. Must be one of: {valid_roles}",
                )

        # Validate teams start with 'team:'
        for team in request.teams:
            if not team.startswith("team:"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid team format: {team}. Teams must start with 'team:'",
                )

        # Update primary system role in users table
        if request.system_roles:
            user.role = request.system_roles[0]  # type: ignore[assignment]
        else:
            # Default to 'user' if no system role specified
            user.role = "user"  # type: ignore[assignment]

        # Get existing memberships
        existing_stmt = select(UserRoleMembership).where(UserRoleMembership.user_id == user_id)
        existing_result = await db.execute(existing_stmt)
        existing_memberships = existing_result.scalars().all()

        # Build sets of roles to keep
        roles_to_keep = set(request.system_roles + request.grouping_roles + request.teams)
        existing_roles = {m.role for m in existing_memberships if m.role}

        # Remove roles that are no longer assigned
        for membership in existing_memberships:
            if membership.role and membership.role not in roles_to_keep:
                await db.delete(membership)

        # Add new roles
        roles_to_add = roles_to_keep - existing_roles
        for role_name in roles_to_add:
            # Skip if it's the primary system role (already in users.role)
            if role_name in SYSTEM_ROLES and role_name == user.role:
                continue

            membership = UserRoleMembership()  # type: ignore[call-arg]
            membership.user_id = user_id
            membership.role = role_name
            if admin_user_id:
                try:
                    membership.granted_by = UUID(str(admin_user_id))
                except Exception:
                    membership.granted_by = None
            membership.metadata_json = {"added_via": "admin_user_roles_api"}
            db.add(membership)

        await db.commit()

        logger.info(
            "Updated user roles",
            extra={
                "user_id": str(user_id),
                "admin_user_id": str(admin_user_id or ""),
                "role": role,
                "scopes": scopes,
                "system_roles": request.system_roles,
                "grouping_roles": request.grouping_roles,
                "teams": request.teams,
            },
        )

        # Return updated roles
        return await get_user_roles(user_id, db, current_user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error updating user roles",
            exc_info=True,
            extra={
                "user_id": str(user_id),
                "admin_user_id": str(admin_user_id or ""),
                "role": role,
                "scopes": scopes,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user roles",
        ) from e


@router.post("/{user_id}/roles/{role_name}", status_code=status.HTTP_201_CREATED)
async def add_user_role(
    user_id: UUID,
    role_name: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> dict:
    """Add a single role to a user."""
    try:
        role, scopes, admin_user_id = _extract_user_context(current_user)
        require_admin_or_role_admin(current_user)
        await _assert_user_exists(user_id, db)

        # Check if already assigned
        existing_stmt = select(UserRoleMembership).where(
            UserRoleMembership.user_id == user_id,
            UserRoleMembership.role == role_name,
        )
        existing = (await db.execute(existing_stmt)).scalar_one_or_none()
        if existing:
            return {
                "message": "Role already assigned",
                "role": role_name,
                "user_id": str(user_id),
            }

        # Create new membership
        membership = UserRoleMembership()  # type: ignore[call-arg]
        membership.user_id = user_id
        membership.role = role_name
        if admin_user_id:
            try:
                membership.granted_by = UUID(str(admin_user_id))
            except Exception:
                membership.granted_by = None
        membership.metadata_json = {"added_via": "admin_user_roles_api"}
        db.add(membership)
        await db.commit()

        logger.info(
            "Added role to user",
            extra={
                "user_id": str(user_id),
                "role_name": role_name,
                "admin_user_id": str(admin_user_id or ""),
                "admin_role": role,
                "scopes": scopes,
            },
        )

        return {"message": "Role assigned", "role": role_name, "user_id": str(user_id)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error adding role to user",
            exc_info=True,
            extra={
                "user_id": str(user_id),
                "role_name": role_name,
                "admin_user_id": str(admin_user_id or ""),
                "admin_role": role,
                "scopes": scopes,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add role to user",
        ) from e


@router.delete("/{user_id}/roles/{role_name}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user_role(
    user_id: UUID,
    role_name: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> None:
    """Remove a role from a user."""
    try:
        role, scopes, admin_user_id = _extract_user_context(current_user)
        require_admin_or_role_admin(current_user)
        user = await _assert_user_exists(user_id, db)

        # Don't allow removing primary system role via this endpoint
        user_role_value: str = user.role or ""  # type: ignore[assignment]
        if user_role_value == role_name and role_name in SYSTEM_ROLES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove primary system role. Update user's primary role instead.",
            )

        await db.execute(
            UserRoleMembership.__table__.delete().where(
                UserRoleMembership.user_id == user_id,
                UserRoleMembership.role == role_name,
            )
        )
        await db.commit()

        logger.info(
            "Removed role from user",
            extra={
                "user_id": str(user_id),
                "role_name": role_name,
                "admin_user_id": str(admin_user_id or ""),
                "admin_role": role,
                "scopes": scopes,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error removing role from user",
            exc_info=True,
            extra={
                "user_id": str(user_id),
                "role_name": role_name,
                "admin_user_id": str(admin_user_id or ""),
                "admin_role": role,
                "scopes": scopes,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove role from user",
        ) from e
