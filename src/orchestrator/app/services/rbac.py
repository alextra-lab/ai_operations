"""
Role-Based Access Control (RBAC) service for use case permissions.

Implements ADR-041 role-based use case access control.

This module provides async functions to check if users have access to use cases
through three mechanisms:
1. Admin role override (admin always has access)
2. Direct user assignment (user_use_case_assignments table)
3. Role-based assignment (role_use_case_assignments table)

Access Resolution Priority:
1. Admin role → Full access (bypass all checks)
2. Direct user assignment → Explicit grant
3. Role-based assignment → Inherited from role membership
4. Default → No access

Fully async per ADR-022 (P5-A23 - sync patterns removed Nov 2025).
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import (
    AuthUser,
    RoleUseCaseAssignment,
    UseCase,
    UserRoleMembership,
    UserUseCaseAssignment,
)


async def user_can_access_use_case(user_id: UUID, use_case_id: UUID, db: AsyncSession) -> bool:
    """
    Check if user has access to use case.

    Checks three levels in order:
    1. Admin override (admin role always has access)
    2. Direct user assignment (user_use_case_assignments)
    3. Role-based assignment (role_use_case_assignments)

    Args:
        user_id: User UUID
        use_case_id: Use case UUID
        db: Async database session

    Returns:
        True if user has access, False otherwise

    Example:
        >>> await user_can_access_use_case(
        ...     UUID("550e8400-e29b-41d4-a716-446655440000"),
        ...     UUID("ba0c6e49-2813-4887-8970-e0c1753234f7"),
        ...     db
        ... )
        True
    """
    # Check 1: Admin override
    result = await db.execute(select(AuthUser).where(AuthUser.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return False

    # Admin role bypasses all checks
    if user.role == "admin":  # type: ignore[attr-defined]
        return True

    # Check 2: Direct user assignment
    result = await db.execute(
        select(UserUseCaseAssignment).where(
            and_(
                UserUseCaseAssignment.user_id == user_id,
                UserUseCaseAssignment.use_case_id == use_case_id,
                UserUseCaseAssignment.status == "active",
            )
        )
    )
    direct_assignment = result.scalar_one_or_none()

    if direct_assignment:
        return True

    # Check 3: Role-based assignment
    now = datetime.now(tz=UTC)

    # Get user's roles
    result = await db.execute(
        select(UserRoleMembership.role).where(UserRoleMembership.user_id == user_id)
    )
    user_roles = result.all()

    if not user_roles:
        return False

    role_names = [role.role for role in user_roles]

    # Check if any of user's roles grant access to this use case
    result = await db.execute(
        select(RoleUseCaseAssignment).where(
            RoleUseCaseAssignment.role_name.in_(role_names),
            RoleUseCaseAssignment.use_case_id == use_case_id,
            RoleUseCaseAssignment.is_active.is_(True),
            or_(
                RoleUseCaseAssignment.expires_at.is_(None),
                RoleUseCaseAssignment.expires_at > now,
            ),
        )
    )
    role_assignment = result.scalar_one_or_none()

    return role_assignment is not None


async def get_accessible_use_cases(
    user_id: UUID,
    db: AsyncSession,
    include_inactive: bool = False,
    lifecycle_state: str | None = "published",
) -> list[UseCase]:
    """
    Get all use cases accessible to user through direct or role-based assignments.

    Args:
        user_id: User UUID
        db: Async database session
        include_inactive: Include inactive use cases (default: False)
        lifecycle_state: Filter by lifecycle state (default: "published")
            Options: "draft", "review", "published", "archived", None (all states)

    Returns:
        List of UseCase objects accessible to the user

    Example:
        >>> use_cases = await get_accessible_use_cases(
        ...     UUID("550e8400-e29b-41d4-a716-446655440000"),
        ...     db,
        ...     lifecycle_state="published"
        ... )
        >>> len(use_cases)
        5
    """
    result = await db.execute(select(AuthUser).where(AuthUser.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return []

    # Admin sees all
    user_role = str(user.role)  # type: ignore[attr-defined]
    if user_role == "admin":
        stmt = select(UseCase)
        if not include_inactive:
            stmt = stmt.where(UseCase.is_active.is_(True))
        if lifecycle_state:
            stmt = stmt.where(UseCase.lifecycle_state == lifecycle_state)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # Get use case IDs from direct assignments
    direct_ids = (
        select(UserUseCaseAssignment.use_case_id)
        .where(
            and_(
                UserUseCaseAssignment.user_id == user_id,
                UserUseCaseAssignment.status == "active",
            )
        )
        .scalar_subquery()
    )

    # Get use case IDs from role-based assignments
    user_roles = (
        select(UserRoleMembership.role)
        .where(UserRoleMembership.user_id == user_id)
        .scalar_subquery()
    )

    now = datetime.now(tz=UTC)

    role_ids = (
        select(RoleUseCaseAssignment.use_case_id)
        .where(
            RoleUseCaseAssignment.role_name.in_(user_roles),
            RoleUseCaseAssignment.is_active.is_(True),
            or_(
                RoleUseCaseAssignment.expires_at.is_(None),
                RoleUseCaseAssignment.expires_at > now,
            ),
        )
        .scalar_subquery()
    )

    # Combine both sources
    stmt = select(UseCase).where(or_(UseCase.id.in_(direct_ids), UseCase.id.in_(role_ids)))

    if not include_inactive:
        stmt = stmt.where(UseCase.is_active.is_(True))

    if lifecycle_state:
        stmt = stmt.where(UseCase.lifecycle_state == lifecycle_state)

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_user_access_source(user_id: UUID, use_case_id: UUID, db: AsyncSession) -> dict | None:
    """
    Determine how a user has access to a use case (for transparency/audit).

    Returns information about whether access is via admin, direct assignment,
    or role inheritance.

    Args:
        user_id: User UUID
        use_case_id: Use case UUID
        db: Async database session

    Returns:
        Dictionary with access source information, or None if no access:
        {
            "has_access": bool,
            "source": "admin" | "direct" | "role" | "none",
            "details": {...}  # Additional context
        }

    Example:
        >>> source = await get_user_access_source(user_id, use_case_id, db)
        >>> source
        {
            "has_access": True,
            "source": "role",
            "details": {
                "role_name": "analyst",
                "granted_at": "2025-10-24T10:00:00Z"
            }
        }
    """
    # Check admin
    result = await db.execute(select(AuthUser).where(AuthUser.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return {
            "has_access": False,
            "source": "none",
            "details": {"reason": "user_not_found"},
        }

    user_role = str(user.role)  # type: ignore[attr-defined]
    if user_role == "admin":
        return {"has_access": True, "source": "admin", "details": {"role": "admin"}}

    # Check direct assignment
    result = await db.execute(
        select(UserUseCaseAssignment).where(
            and_(
                UserUseCaseAssignment.user_id == user_id,
                UserUseCaseAssignment.use_case_id == use_case_id,
                UserUseCaseAssignment.status == "active",
            )
        )
    )
    direct = result.scalar_one_or_none()

    if direct:
        return {
            "has_access": True,
            "source": "direct",
            "details": {
                "assigned_role": direct.assigned_role,
                "assigned_at": direct.assigned_at.isoformat(),
                "expires_at": (direct.expires_at.isoformat() if direct.expires_at else None),
            },
        }

    # Check role-based
    now = datetime.now(tz=UTC)
    result = await db.execute(
        select(UserRoleMembership.role).where(UserRoleMembership.user_id == user_id)
    )
    user_roles = result.all()

    if not user_roles:
        return {
            "has_access": False,
            "source": "none",
            "details": {"reason": "no_roles_assigned"},
        }

    role_names = [role.role for role in user_roles]

    result = await db.execute(
        select(RoleUseCaseAssignment).where(
            RoleUseCaseAssignment.role_name.in_(role_names),
            RoleUseCaseAssignment.use_case_id == use_case_id,
            RoleUseCaseAssignment.is_active.is_(True),
            or_(
                RoleUseCaseAssignment.expires_at.is_(None),
                RoleUseCaseAssignment.expires_at > now,
            ),
        )
    )
    role_assignment = result.scalar_one_or_none()

    if role_assignment:
        return {
            "has_access": True,
            "source": "role",
            "details": {
                "role_name": role_assignment.role_name,
                "granted_at": role_assignment.granted_at.isoformat(),
                "expires_at": (
                    role_assignment.expires_at.isoformat() if role_assignment.expires_at else None
                ),
                "is_active": role_assignment.is_active,
            },
        }

    return {
        "has_access": False,
        "source": "none",
        "details": {"reason": "no_matching_assignments"},
    }
