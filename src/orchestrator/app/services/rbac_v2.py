"""
RBAC V2 Service - Two-Tier Role System with Team Isolation

Implements ADR-060 access control logic.

This service provides functions for:
- Role management (system roles, grouping roles, teams)
- Use case access control with team isolation
- Collection access control
- Edit permissions
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, false, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import (
    AuthUser,
    RoleUseCaseAssignment,
    UseCase,
    UserRoleMembership,
)
from ..db.models_rbac import RoleCollectionAssignment

# System/Capability Roles (Tier 1) - All 10 system roles per ADR-060
SYSTEM_ROLES = [
    "admin",
    "corpus_admin",
    "developer",
    "use_case_admin",
    "tools_admin",
    "role_admin",
    "use_case_publisher",
    "conversations_privileged",
    "user",
    "service",
]


async def get_user_roles(user_id: UUID, db: AsyncSession) -> list[str]:
    """
    Get all roles assigned to a user (system + grouping + teams).

    Per ADR-060, roles are stored in the user_roles table. This function also
    checks the users.role column as a fallback for users that may not have
    been migrated to the user_roles table yet.

    Args:
        user_id: User UUID
        db: Async database session

    Returns:
        List of role names: ['admin', 'threat_hunting', 'team:csirt_security']
    """
    roles: list[str] = []

    # Get roles from user_roles table (RBAC V2 - primary source)
    result = await db.execute(
        select(UserRoleMembership.role).where(UserRoleMembership.user_id == user_id)
    )
    roles.extend([row.role for row in result.all()])

    # Fallback: Check users.role column if no roles found in user_roles table
    # This ensures users created before seed scripts were updated still work
    if not roles:
        user_result = await db.execute(select(AuthUser.role).where(AuthUser.id == user_id))
        fallback_role = user_result.scalar_one_or_none()
        if fallback_role:
            roles.append(fallback_role)

    return roles


async def get_user_system_roles(user_id: UUID, db: AsyncSession) -> list[str]:
    """
    Get only system/capability roles.

    Args:
        user_id: User UUID
        db: Async database session

    Returns:
        List of system role names
    """
    all_roles = await get_user_roles(user_id, db)
    return [r for r in all_roles if r in SYSTEM_ROLES]


async def get_user_grouping_roles(user_id: UUID, db: AsyncSession) -> list[str]:
    """
    Get only use case grouping roles (excluding system roles and teams).

    Args:
        user_id: User UUID
        db: Async database session

    Returns:
        List of grouping role names (e.g., 'threat_hunting', 'incident_response')
    """
    all_roles = await get_user_roles(user_id, db)
    return [r for r in all_roles if r not in SYSTEM_ROLES and not r.startswith("team:")]


async def get_user_teams(user_id: UUID, db: AsyncSession) -> list[str]:
    """
    Get team memberships.

    Args:
        user_id: User UUID
        db: Async database session

    Returns:
        List of team role names (e.g., 'team:csirt_security', 'team:soc_governance')
    """
    all_roles = await get_user_roles(user_id, db)
    return [r for r in all_roles if r.startswith("team:")]


async def has_role(user_id: UUID, role: str, db: AsyncSession) -> bool:
    """
    Check if user has a specific role.

    Args:
        user_id: User UUID
        role: Role name to check
        db: Async database session

    Returns:
        True if user has the role, False otherwise
    """
    result = await db.execute(
        select(UserRoleMembership).where(
            UserRoleMembership.user_id == user_id,
            UserRoleMembership.role == role,
        )
    )
    return result.scalar_one_or_none() is not None


async def has_any_role(
    user_id: UUID,
    required_roles: list[str],
    db: AsyncSession,
) -> bool:
    """
    Check if user has any of the required roles.

    Args:
        user_id: User UUID
        required_roles: List of role names to check
        db: Async database session

    Returns:
        True if user has any of the required roles, False otherwise
    """
    user_roles = await get_user_roles(user_id, db)
    return any(role in user_roles for role in required_roles)


async def get_accessible_use_cases(
    user_id: UUID,
    db: AsyncSession,
    lifecycle_state: str | None = None,
) -> list[UseCase]:
    """
    Get use cases accessible to user.

    Visibility rules:
    1. Admin: ALL use cases
    2. use_case_admin with team: ALL published + team's drafts
    3. corpus_admin: ALL published (for reference)
    4. Grouping roles: Only assigned published use cases
    5. No roles: EMPTY (default-deny)

    Args:
        user_id: User UUID
        db: Async database session
        lifecycle_state: Optional filter by lifecycle state

    Returns:
        List of accessible UseCase objects
    """
    user_roles = await get_user_roles(user_id, db)

    # Rule 1: Admin sees everything
    if "admin" in user_roles:
        stmt = select(UseCase)
        if lifecycle_state:
            stmt = stmt.where(UseCase.lifecycle_state == lifecycle_state)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # Rule 2: use_case_admin with team-based visibility
    if "use_case_admin" in user_roles:
        user_teams = await get_user_teams(user_id, db)

        # Build query based on lifecycle_state filter
        if lifecycle_state == "published":
            # Only published use cases (all teams)
            stmt = select(UseCase).where(UseCase.lifecycle_state == "published")
        elif lifecycle_state in ("draft", "review"):
            # Only team drafts/review (if user has teams)
            if user_teams:
                stmt = select(UseCase).where(
                    UseCase.team_id.in_(user_teams),
                    UseCase.lifecycle_state == lifecycle_state,
                )
            else:
                # No teams = no drafts/review
                stmt = select(UseCase).where(false())  # Empty result (no teams, no drafts)
        else:
            # No filter or other state: ALL published + team's drafts
            # Build OR condition: published OR (team drafts/review)
            if user_teams:
                stmt = select(UseCase).where(
                    or_(
                        UseCase.lifecycle_state == "published",
                        and_(
                            UseCase.team_id.in_(user_teams),
                            UseCase.lifecycle_state.in_(["draft", "review"]),
                        ),
                    )
                )
            else:
                # No teams = only published
                stmt = select(UseCase).where(UseCase.lifecycle_state == "published")

        result = await db.execute(stmt)
        return list(result.scalars().all())

    # Rule 3: corpus_admin sees all published
    if "corpus_admin" in user_roles:
        stmt = select(UseCase).where(UseCase.lifecycle_state == "published")
        if lifecycle_state:
            stmt = stmt.where(UseCase.lifecycle_state == lifecycle_state)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # Rule 4: Grouping roles - only assigned published use cases
    grouping_roles = await get_user_grouping_roles(user_id, db)

    if not grouping_roles:
        return []  # No roles = no access

    now = datetime.now(tz=UTC)

    stmt = (
        select(UseCase)
        .join(
            RoleUseCaseAssignment,
            UseCase.id == RoleUseCaseAssignment.use_case_id,
        )
        .where(
            RoleUseCaseAssignment.role_name.in_(grouping_roles),
            RoleUseCaseAssignment.is_active == True,  # noqa: E712
            UseCase.lifecycle_state == "published",
            or_(
                RoleUseCaseAssignment.expires_at.is_(None),
                RoleUseCaseAssignment.expires_at > now,
            ),
        )
        .distinct()
    )

    if lifecycle_state:
        stmt = stmt.where(UseCase.lifecycle_state == lifecycle_state)

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def can_edit_use_case(
    user_id: UUID,
    use_case: UseCase,
    db: AsyncSession,
) -> bool:
    """
    Check if user can edit a use case.

    Rules:
    1. Admin: Can edit anything
    2. Non-draft: Cannot edit (must clone)
    3. Creator: Can edit own drafts

    Args:
        user_id: User UUID
        use_case: UseCase object to check
        db: Async database session

    Returns:
        True if user can edit, False otherwise
    """
    user_roles = await get_user_roles(user_id, db)

    # Admin can edit anything
    if "admin" in user_roles:
        return True

    # Can only edit drafts
    if use_case.lifecycle_state != "draft":
        return False

    # Creator can edit own drafts
    return use_case.created_by_user_id == user_id


async def can_transition_state(
    user_id: UUID,
    use_case: UseCase,
    target_state: str,
    db: AsyncSession,
) -> bool:
    """
    Check if user can transition use case to target state.

    Implements lifecycle state transition permissions per ADR-060:
    - draft → review: creator OR admin/use_case_admin
    - review → published: admin, use_case_admin, or use_case_publisher
    - review → draft (rejection): admin, use_case_admin, or use_case_publisher
    - published → archived: admin, use_case_admin, or use_case_publisher

    Args:
        user_id: User UUID
        use_case: UseCase object to transition
        target_state: Target lifecycle state
        db: Async database session

    Returns:
        True if user can transition, False otherwise
    """
    user_roles = await get_user_roles(user_id, db)
    current_state = use_case.lifecycle_state

    # Admin can do anything
    if "admin" in user_roles:
        return True

    # draft → review: creator OR use_case_admin
    if current_state == "draft" and target_state == "review":
        # use_case_admin can submit any draft
        if "use_case_admin" in user_roles:
            return True
        # Creator can submit own draft
        if use_case.created_by_user_id == user_id:
            return True
        # Developer can submit own draft
        return "developer" in user_roles and use_case.created_by_user_id == user_id

    # review → published: use_case_admin or use_case_publisher
    if current_state == "review" and target_state == "published":
        return any(role in user_roles for role in ["use_case_admin", "use_case_publisher"])

    # review → draft (rejection): use_case_admin or use_case_publisher
    if current_state == "review" and target_state == "draft":
        return any(role in user_roles for role in ["use_case_admin", "use_case_publisher"])

    # published → archived: use_case_admin or use_case_publisher
    if current_state == "published" and target_state == "archived":
        return any(role in user_roles for role in ["use_case_admin", "use_case_publisher"])

    # No other transitions allowed
    return False


async def get_accessible_collections(
    user_id: UUID,
    db: AsyncSession,
) -> list[dict[str, Any]]:
    """
    Get document collections accessible to user.

    Visibility rules:
    1. Admin: ALL collections
    2. corpus_admin: ALL collections
    3. Grouping roles: Only assigned collections
    4. No roles: EMPTY (default-deny)

    Note: Collections table is in corpus_svc, so we query it directly
    using table() reference.

    Args:
        user_id: User UUID
        db: Async database session

    Returns:
        List of collection dictionaries with id, name, is_active, etc.
    """

    # Reference collections table directly using text() for cross-service table access
    # Collections are in corpus_svc but we need to query them for RBAC
    user_roles = await get_user_roles(user_id, db)

    # Admin sees all active collections
    if "admin" in user_roles:
        result = await db.execute(
            text(
                "SELECT id, name, description, is_active, is_default FROM collections WHERE is_active = true"
            )
        )
        rows = result.all()
        return [dict(row._mapping) for row in rows]

    # corpus_admin sees all active collections
    if "corpus_admin" in user_roles:
        result = await db.execute(
            text(
                "SELECT id, name, description, is_active, is_default FROM collections WHERE is_active = true"
            )
        )
        rows = result.all()
        return [dict(row._mapping) for row in rows]

    # Grouping roles - only assigned collections
    grouping_roles = await get_user_grouping_roles(user_id, db)

    if not grouping_roles:
        return []

    now = datetime.now(tz=UTC)

    # Query with join to role_collection_assignments
    stmt = (
        select(RoleCollectionAssignment.collection_id)
        .where(
            RoleCollectionAssignment.role_name.in_(grouping_roles),
            RoleCollectionAssignment.is_active == True,  # noqa: E712
            or_(
                RoleCollectionAssignment.expires_at.is_(None),
                RoleCollectionAssignment.expires_at > now,
            ),
        )
        .distinct()
    )
    result = await db.execute(stmt)
    collection_ids = [row[0] for row in result.all()]

    if not collection_ids:
        return []

    # Get collection details
    result = await db.execute(
        text(
            "SELECT id, name, description, is_active, is_default FROM collections WHERE id = ANY(:ids) AND is_active = true"
        ).bindparams(ids=collection_ids)
    )
    rows = result.all()
    return [dict(row._mapping) for row in rows]
