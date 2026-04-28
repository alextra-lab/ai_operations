"""
Admin API for managing use case grouping roles (RBAC V2).

Grouping roles control access to published use cases and collections.
Implements ADR-060 two-tier role model (Tier 2: grouping roles).
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from shared.auth import get_current_user
from shared.logging_utils.fastapi import configure_logging

from ..db.database import get_async_db
from ..db.models import RoleUseCaseAssignment, UserRoleMembership
from ..db.models_rbac import RoleCollectionAssignment
from ..services.rbac_v2 import SYSTEM_ROLES

logger = configure_logging(__name__)
router = APIRouter(
    prefix="/api/v1/admin/grouping-roles",
    tags=["Admin - Grouping Roles"],
)

ROLE_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{1,49}$")

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from shared.auth.models import TokenPayload


class GroupingRoleInfo(BaseModel):
    """Information about a grouping role."""

    role_name: str
    user_count: int
    use_case_count: int
    collection_count: int


class CreateGroupingRoleRequest(BaseModel):
    """Request to register a grouping role."""

    role_name: str = Field(
        ...,
        description="Lowercase role id",
        pattern=ROLE_PATTERN.pattern,
    )


class GroupingRoleResponse(BaseModel):
    """Response when creating a grouping role."""

    role_name: str
    created_by: UUID
    created_at: datetime


def require_admin_or_role_admin(current_user: TokenPayload) -> None:
    """Require admin or role_admin privileges."""
    if current_user.has_any_role(["admin", "role_admin"]):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin or role_admin privileges required",
    )


async def _active_role_names(db: AsyncSession) -> list[str]:
    """Collect grouping role names from memberships and assignments."""
    membership_stmt = select(UserRoleMembership.role).where(
        ~UserRoleMembership.role.in_(SYSTEM_ROLES),
        ~UserRoleMembership.role.like("team:%"),
    )
    membership_rows = await db.execute(membership_stmt)
    membership_roles = {row[0] for row in membership_rows.all()}

    use_case_stmt = select(RoleUseCaseAssignment.role_name)
    use_case_rows = await db.execute(use_case_stmt)
    use_case_roles = {row[0] for row in use_case_rows.all()}

    collection_stmt = select(RoleCollectionAssignment.role_name)
    collection_rows = await db.execute(collection_stmt)
    collection_roles = {row[0] for row in collection_rows.all()}

    return sorted(membership_roles | use_case_roles | collection_roles)


@router.get("", response_model=list[GroupingRoleInfo])
async def list_grouping_roles(
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> list[GroupingRoleInfo]:
    """List all grouping roles with basic counts."""
    require_admin_or_role_admin(current_user)

    role_names = await _active_role_names(db)
    if not role_names:
        return []

    user_counts_stmt = (
        select(
            UserRoleMembership.role,
            func.count(UserRoleMembership.user_id),
        )
        .where(UserRoleMembership.role.in_(role_names))
        .group_by(UserRoleMembership.role)
    )
    user_counts = {row[0]: row[1] for row in (await db.execute(user_counts_stmt)).all()}

    use_case_counts_stmt = (
        select(
            RoleUseCaseAssignment.role_name,
            func.count(RoleUseCaseAssignment.id),
        )
        .where(
            RoleUseCaseAssignment.role_name.in_(role_names),
            RoleUseCaseAssignment.is_active == True,  # noqa: E712
        )
        .group_by(RoleUseCaseAssignment.role_name)
    )
    use_case_counts = {row[0]: row[1] for row in (await db.execute(use_case_counts_stmt)).all()}

    collection_counts_stmt = (
        select(
            RoleCollectionAssignment.role_name,
            func.count(RoleCollectionAssignment.id),
        )
        .where(
            RoleCollectionAssignment.role_name.in_(role_names),
            RoleCollectionAssignment.is_active == True,  # noqa: E712
        )
        .group_by(RoleCollectionAssignment.role_name)
    )
    collection_counts = {row[0]: row[1] for row in (await db.execute(collection_counts_stmt)).all()}

    return [
        GroupingRoleInfo(
            role_name=role,
            user_count=user_counts.get(role, 0),
            use_case_count=use_case_counts.get(role, 0),
            collection_count=collection_counts.get(role, 0),
        )
        for role in role_names
    ]


@router.post("", response_model=GroupingRoleResponse, status_code=status.HTTP_201_CREATED)
async def create_grouping_role(
    request: CreateGroupingRoleRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> GroupingRoleResponse:
    """Register a grouping role (idempotent)."""
    require_admin_or_role_admin(current_user)

    role_name = request.role_name
    if role_name in SYSTEM_ROLES or role_name.startswith("team:"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid grouping role name",
        )

    # Ensure at least one anchor membership (creator) exists
    creator_id = UUID(str(current_user.user_id))
    existing_stmt = select(UserRoleMembership).where(
        UserRoleMembership.user_id == creator_id,
        UserRoleMembership.role == role_name,
    )
    existing = (await db.execute(existing_stmt)).scalar_one_or_none()
    if not existing:
        membership = UserRoleMembership()  # type: ignore[call-arg]
        membership.user_id = creator_id
        membership.role = role_name
        membership.granted_by = creator_id
        membership.metadata_json = {"created_via": "grouping_role_api"}
        db.add(membership)
        await db.commit()
        await db.refresh(membership)
        created_at = membership.created_at
    else:
        created_at = existing.created_at

    logger.info(
        "Registered grouping role",
        extra={"role_name": role_name, "created_by": str(creator_id)},
    )
    return GroupingRoleResponse(
        role_name=role_name,
        created_by=creator_id,
        created_at=created_at,
    )


@router.delete("/{role_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_grouping_role(
    role_name: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> None:
    """Delete a grouping role and all its assignments."""
    require_admin_or_role_admin(current_user)

    if role_name in SYSTEM_ROLES or role_name.startswith("team:"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete system roles or teams via this endpoint",
        )

    await db.execute(
        UserRoleMembership.__table__.delete().where(UserRoleMembership.role == role_name)
    )
    await db.execute(
        RoleUseCaseAssignment.__table__.delete().where(RoleUseCaseAssignment.role_name == role_name)
    )
    await db.execute(
        RoleCollectionAssignment.__table__.delete().where(
            RoleCollectionAssignment.role_name == role_name
        )
    )
    await db.commit()

    logger.info(
        "Deleted grouping role",
        extra={"role_name": role_name, "deleted_by": str(current_user.user_id)},
    )
