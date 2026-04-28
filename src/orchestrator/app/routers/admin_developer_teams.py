"""
Admin API for developer teams (RBAC V2 team isolation).

Teams are represented as roles with prefix 'team:' in user_roles.
Use cases carry team ownership via use_cases.team_id.
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
from shared.auth.models import User as AuthUser
from shared.logging_utils.fastapi import configure_logging

from ..db.database import get_async_db
from ..db.models import UseCase, UserRoleMembership

logger = configure_logging(__name__)
router = APIRouter(
    prefix="/api/v1/admin/developer-teams",
    tags=["Admin - Developer Teams"],
)

TEAM_PATTERN = re.compile(r"^team:[a-z0-9_-]{1,64}$")

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from shared.auth.models import TokenPayload


class TeamInfo(BaseModel):
    """Team with membership and use case counts."""

    team_id: str
    member_count: int
    draft_count: int
    published_count: int


class TeamMembershipResponse(BaseModel):
    """Response when adding a member to a team."""

    team_id: str
    user_id: UUID
    added_at: datetime


class TeamUseCaseInfo(BaseModel):
    """Minimal use case info for a team."""

    id: UUID
    name: str
    lifecycle_state: str


class CreateTeamRequest(BaseModel):
    """Request to create a team."""

    team_id: str = Field(
        ...,
        description="Team id, must start with team:",
        pattern=TEAM_PATTERN.pattern,
    )
    member_user_id: UUID | None = Field(None, description="Initial member (defaults to caller)")


def require_admin_or_role_admin(current_user: TokenPayload) -> None:
    """Require admin or role_admin privileges."""
    if current_user.has_any_role(["admin", "role_admin"]):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin or role_admin privileges required",
    )


async def _team_ids(db: AsyncSession) -> set[str]:
    """Collect team ids from memberships and use cases."""
    membership_rows = await db.execute(
        select(UserRoleMembership.role).where(UserRoleMembership.role.like("team:%"))
    )
    membership_ids = {row[0] for row in membership_rows.all()}

    use_case_rows = await db.execute(select(UseCase.team_id).where(UseCase.team_id.is_not(None)))
    use_case_ids = {row[0] for row in use_case_rows.all() if row[0]}

    return membership_ids | use_case_ids


@router.get("", response_model=list[TeamInfo])
async def list_developer_teams(
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> list[TeamInfo]:
    """List developer teams with member and use case counts."""
    require_admin_or_role_admin(current_user)

    team_ids = await _team_ids(db)
    if not team_ids:
        return []

    member_counts_stmt = (
        select(
            UserRoleMembership.role,
            func.count(UserRoleMembership.user_id),
        )
        .where(UserRoleMembership.role.in_(team_ids))
        .group_by(UserRoleMembership.role)
    )
    member_counts = {row[0]: row[1] for row in (await db.execute(member_counts_stmt)).all()}

    use_case_counts_stmt = (
        select(
            UseCase.team_id,
            UseCase.lifecycle_state,
            func.count(UseCase.id),
        )
        .where(UseCase.team_id.in_(team_ids))
        .group_by(UseCase.team_id, UseCase.lifecycle_state)
    )
    draft_counts: dict[str, int] = {}
    published_counts: dict[str, int] = {}
    for team_id, lifecycle, count in (await db.execute(use_case_counts_stmt)).all():
        if lifecycle == "published":
            published_counts[team_id] = count
        else:
            draft_counts[team_id] = draft_counts.get(team_id, 0) + count

    return [
        TeamInfo(
            team_id=team_id,
            member_count=member_counts.get(team_id, 0),
            draft_count=draft_counts.get(team_id, 0),
            published_count=published_counts.get(team_id, 0),
        )
        for team_id in sorted(team_ids)
    ]


async def _assert_user_exists(user_id: UUID, db: AsyncSession) -> None:
    """Ensure the target user exists."""
    user_stmt = select(AuthUser).where(AuthUser.id == user_id)
    user = (await db.execute(user_stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )


@router.post("", response_model=TeamMembershipResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    request: CreateTeamRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> TeamMembershipResponse:
    """Create a team (idempotent) and add initial member."""
    require_admin_or_role_admin(current_user)

    team_id = request.team_id
    if not TEAM_PATTERN.match(team_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Team id must start with team:",
        )

    member_user_id = request.member_user_id or UUID(str(current_user.user_id))
    await _assert_user_exists(member_user_id, db)

    existing_stmt = select(UserRoleMembership).where(
        UserRoleMembership.user_id == member_user_id,
        UserRoleMembership.role == team_id,
    )
    existing = (await db.execute(existing_stmt)).scalar_one_or_none()
    if existing:
        return TeamMembershipResponse(
            team_id=team_id,
            user_id=member_user_id,
            added_at=existing.created_at,
        )

    membership = UserRoleMembership()  # type: ignore[call-arg]
    membership.user_id = member_user_id
    membership.role = team_id
    membership.granted_by = UUID(str(current_user.user_id))
    membership.metadata_json = {"created_via": "developer_teams_api"}
    db.add(membership)
    await db.commit()
    await db.refresh(membership)

    logger.info(
        "Created team and added member",
        extra={"team_id": team_id, "user_id": str(member_user_id)},
    )
    return TeamMembershipResponse(
        team_id=team_id,
        user_id=member_user_id,
        added_at=membership.created_at,
    )


@router.post(
    "/{team_id}/members/{user_id}",
    response_model=TeamMembershipResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_team_member(
    team_id: str,
    user_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> TeamMembershipResponse:
    """Add a user to a team."""
    require_admin_or_role_admin(current_user)

    if not TEAM_PATTERN.match(team_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Team id must start with team:",
        )

    await _assert_user_exists(user_id, db)

    existing_stmt = select(UserRoleMembership).where(
        UserRoleMembership.user_id == user_id,
        UserRoleMembership.role == team_id,
    )
    existing = (await db.execute(existing_stmt)).scalar_one_or_none()
    if existing:
        return TeamMembershipResponse(
            team_id=team_id,
            user_id=user_id,
            added_at=existing.created_at,
        )

    membership = UserRoleMembership()  # type: ignore[call-arg]
    membership.user_id = user_id
    membership.role = team_id
    membership.granted_by = UUID(str(current_user.user_id))
    membership.metadata_json = {"added_via": "developer_teams_api"}
    db.add(membership)
    await db.commit()
    await db.refresh(membership)

    logger.info(
        "Added user to team",
        extra={"team_id": team_id, "user_id": str(user_id)},
    )
    return TeamMembershipResponse(
        team_id=team_id,
        user_id=user_id,
        added_at=membership.created_at,
    )


@router.delete("/{team_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_team_member(
    team_id: str,
    user_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> None:
    """Remove a user from a team (no-op if absent)."""
    require_admin_or_role_admin(current_user)

    await db.execute(
        UserRoleMembership.__table__.delete().where(
            UserRoleMembership.user_id == user_id,
            UserRoleMembership.role == team_id,
        )
    )
    await db.commit()

    logger.info(
        "Removed user from team",
        extra={"team_id": team_id, "user_id": str(user_id)},
    )


@router.get("/{team_id}/use-cases", response_model=list[TeamUseCaseInfo])
async def list_team_use_cases(
    team_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> list[TeamUseCaseInfo]:
    """List use cases owned by the given team."""
    require_admin_or_role_admin(current_user)

    stmt = select(UseCase).where(UseCase.team_id == team_id)
    rows = await db.execute(stmt)
    use_cases = rows.scalars().all()

    return [
        TeamUseCaseInfo(
            id=uc.id,
            name=uc.name,
            lifecycle_state=uc.lifecycle_state,
        )
        for uc in use_cases
    ]
