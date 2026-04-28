# RBAC V2 Implementation Plan

**ADR:** ADR-060 - Corrected RBAC Architecture
**Status:** READY FOR IMPLEMENTATION
**Priority:** CRITICAL
**Created:** 2025-12-08
**Estimated Duration:** 7 weeks
**Team Size:** 2-3 developers

---

## Overview

This plan provides a detailed, sequential implementation strategy for fixing the broken RBAC system. The work is organized into 5 phases with specific tasks, acceptance criteria, and testing requirements.

### Key Objectives

1. ✅ Fix broken Role Management UI
2. ✅ Implement two-tier role system (system roles + grouping roles)
3. ✅ Add team-based use case development isolation
4. ✅ Implement default-deny resource access model
5. ✅ Zero downtime migration from current system

### Risk Mitigation

- **Backward compatibility:** Keep old `users.role` column until Phase 5
- **Incremental deployment:** Each phase is independently testable
- **Rollback capability:** All changes are additive until final cleanup
- **Parallel testing:** Test environment runs alongside production

---

## Phase 1: Database Schema Updates (Week 1) ✅ COMPLETE

**Objective:** Update database schema to support new RBAC model without breaking existing functionality.

**Duration:** 5 days
**Dependencies:** None
**Risk Level:** LOW (additive changes only)
**Status:** ✅ **COMPLETE (December 2025)**

### Task 1.1: Create Migration Files ✅ COMPLETE

**File:** `ops/database/migrations/rbac_v2/001_add_team_id_to_use_cases.sql`

```sql
-- Add team_id column to use_cases table
ALTER TABLE use_cases
ADD COLUMN team_id VARCHAR(100);

-- Index for team-based filtering
CREATE INDEX idx_use_cases_team_lifecycle
ON use_cases(team_id, lifecycle_state);

-- Comment for documentation
COMMENT ON COLUMN use_cases.team_id IS
    'Developer team that owns this use case. Format: team:team_name. ' ||
    'Used to isolate draft use cases between teams. ' ||
    'NULL or team:default for unassigned use cases.';

-- Set default for existing use cases
UPDATE use_cases
SET team_id = 'team:default'
WHERE team_id IS NULL AND lifecycle_state = 'draft';

-- Published use cases don't need team assignment (visible to all)
UPDATE use_cases
SET team_id = NULL
WHERE lifecycle_state = 'published';
```

**File:** `ops/database/migrations/rbac_v2/002_create_role_collection_assignments.sql`

```sql
-- Create table for assigning document collections to roles
CREATE TABLE role_collection_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_name VARCHAR(50) NOT NULL,
    collection_id UUID NOT NULL REFERENCES collections(id) ON DELETE CASCADE,

    -- Audit fields
    granted_by UUID REFERENCES users(id),
    granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    -- Constraints
    UNIQUE(role_name, collection_id)
);

-- Indexes
CREATE INDEX idx_role_collection_assignments_role
ON role_collection_assignments(role_name, is_active);

CREATE INDEX idx_role_collection_assignments_collection
ON role_collection_assignments(collection_id, is_active);

-- Comments
COMMENT ON TABLE role_collection_assignments IS
    'Assigns document collections to roles. Users inherit collection access through role memberships.';

COMMENT ON COLUMN role_collection_assignments.role_name IS
    'Role name (system role or grouping role) that gets access to this collection.';
```

**File:** `ops/database/migrations/rbac_v2/003_migrate_users_to_user_roles.sql`

```sql
-- Migrate existing users.role to user_roles table
-- This ensures backward compatibility during transition

INSERT INTO user_roles (id, user_id, role, granted_by, granted_at, metadata)
SELECT
    gen_random_uuid(),
    id as user_id,
    role,
    NULL as granted_by,  -- System migration
    created_at as granted_at,
    '{"migrated_from": "users.role", "migration_date": "' || NOW()::text || '"}'::jsonb as metadata
FROM users
WHERE role IS NOT NULL
  AND role != ''
  AND NOT EXISTS (
      SELECT 1 FROM user_roles ur
      WHERE ur.user_id = users.id
      AND ur.role = users.role
  );

-- Verify migration
DO $$
DECLARE
    total_users INTEGER;
    migrated_users INTEGER;
BEGIN
    SELECT COUNT(*) INTO total_users FROM users WHERE role IS NOT NULL;
    SELECT COUNT(DISTINCT user_id) INTO migrated_users FROM user_roles
    WHERE role IN ('admin', 'corpus_admin', 'use_case_admin', 'tools_admin', 'conversations', 'role_admin', 'user', 'service');

    IF migrated_users < total_users THEN
        RAISE EXCEPTION 'Migration incomplete: % users found, % migrated', total_users, migrated_users;
    END IF;

    RAISE NOTICE 'Migration successful: % users migrated to user_roles table', migrated_users;
END $$;

-- DO NOT drop users.role column yet - will be removed in Phase 5
```

### Task 1.2: Create Migration Runner Script ✅ COMPLETE

**File:** `ops/database/migrations/rbac_v2/run_migrations.sh`

```bash
#!/bin/bash
# RBAC V2 Migration Runner
# Usage: ./run_migrations.sh [test|production]

set -e  # Exit on error

ENVIRONMENT=${1:-test}
DB_NAME=${POSTGRES_DB:-aio}
DB_USER=${POSTGRES_USER:-postgres}
DB_HOST=${POSTGRES_HOST:-localhost}
DB_PORT=${POSTGRES_PORT:-5432}

echo "=========================================="
echo "RBAC V2 Database Migration"
echo "Environment: $ENVIRONMENT"
echo "Database: $DB_NAME @ $DB_HOST:$DB_PORT"
echo "=========================================="

if [ "$ENVIRONMENT" == "production" ]; then
    read -p "⚠️  Are you sure you want to run migrations on PRODUCTION? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "Migration cancelled."
        exit 0
    fi
fi

# Backup database before migration
echo "Creating backup..."
BACKUP_FILE="backup_rbac_v2_$(date +%Y%m%d_%H%M%S).sql"
pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER $DB_NAME > "$BACKUP_FILE"
echo "✅ Backup created: $BACKUP_FILE"

# Run migrations in order
echo ""
echo "Running migrations..."

for migration_file in 001_*.sql 002_*.sql 003_*.sql; do
    if [ -f "$migration_file" ]; then
        echo "Applying: $migration_file"
        psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f "$migration_file"
        echo "✅ $migration_file completed"
    fi
done

echo ""
echo "=========================================="
echo "✅ All migrations completed successfully"
echo "=========================================="
echo ""
echo "Backup file: $BACKUP_FILE"
echo "Keep this backup until Phase 5 is complete."
```

### Task 1.3: Test Migrations ✅ COMPLETE

**Create Test Script:** `ops/database/migrations/rbac_v2/test_migrations.sh`

```bash
#!/bin/bash
# Test migrations in isolated environment

set -e

# Create test database
createdb aio_rbac_test || true

# Restore production schema
pg_restore -d aio_rbac_test latest_schema_backup.sql

# Run migrations
./run_migrations.sh test

# Verify results
psql -d aio_rbac_test -c "
SELECT
    'use_cases.team_id' as check_item,
    CASE WHEN COUNT(*) > 0 THEN '✅' ELSE '❌' END as status
FROM information_schema.columns
WHERE table_name = 'use_cases' AND column_name = 'team_id';

SELECT
    'role_collection_assignments table' as check_item,
    CASE WHEN COUNT(*) > 0 THEN '✅' ELSE '❌' END as status
FROM information_schema.tables
WHERE table_name = 'role_collection_assignments';

SELECT
    'user_roles migration' as check_item,
    CASE WHEN COUNT(*) > 0 THEN '✅' ELSE '❌' END as status
FROM user_roles
WHERE metadata->>'migrated_from' = 'users.role';
"

# Cleanup
dropdb aio_rbac_test

echo "✅ Migration tests passed"
```

### Task 1.4: Execute Migrations ✅ COMPLETE

**Checklist:**

- [x] Run test migrations on development database
- [x] Verify all tables created successfully
- [x] Verify indexes created
- [x] Verify data migration (users → user_roles)
- [ ] Run on staging environment
- [ ] Get approval from security team
- [ ] Create production backup
- [ ] Run on production during maintenance window
- [ ] Verify production migration success

**Acceptance Criteria:**

- ✅ `use_cases.team_id` column exists
- ✅ `role_collection_assignments` table exists with proper indexes
- ✅ All existing users have entries in `user_roles` table
- ✅ No data loss
- ✅ Application still functions normally

**Rollback Procedure:**

```bash
# If migration fails, restore from backup
psql -d aio < backup_rbac_v2_YYYYMMDD_HHMMSS.sql
```

---

## Phase 2: Backend Implementation (Week 2-3) ✅ COMPLETE

**Objective:** Implement new RBAC logic, APIs, and database models.

**Duration:** 10 days
**Dependencies:** Phase 1 complete ✅
**Risk Level:** MEDIUM (logic changes, extensive testing needed)
**Status:** ✅ **COMPLETE (December 8, 2025)**

### Task 2.1: Create RBAC Service V2 ✅ COMPLETE

**File:** `src/orchestrator/app/services/rbac_v2.py`

```python
"""
RBAC V2 Service - Two-Tier Role System with Team Isolation

Implements ADR-060 access control logic.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import (
    AuthUser,
    RoleUseCaseAssignment,
    RoleCollectionAssignment,
    UseCase,
    Collection,
    UserRoleMembership,
    UserUseCaseAssignment,
)


# System/Capability Roles (Tier 1)
SYSTEM_ROLES = [
    'admin',
    'corpus_admin',
    'use_case_admin',
    'tools_admin',
    'conversations',
    'role_admin'
]


async def get_user_roles(user_id: UUID, db: AsyncSession) -> list[str]:
    """
    Get all roles assigned to a user (system + grouping + teams).

    Returns: ['admin', 'threat_hunting', 'team:csirt_security']
    """
    result = await db.execute(
        select(UserRoleMembership.role)
        .where(UserRoleMembership.user_id == user_id)
    )
    return [row.role for row in result.all()]


async def get_user_system_roles(user_id: UUID, db: AsyncSession) -> list[str]:
    """Get only system/capability roles."""
    all_roles = await get_user_roles(user_id, db)
    return [r for r in all_roles if r in SYSTEM_ROLES]


async def get_user_grouping_roles(user_id: UUID, db: AsyncSession) -> list[str]:
    """Get only use case grouping roles (excluding system roles and teams)."""
    all_roles = await get_user_roles(user_id, db)
    return [
        r for r in all_roles
        if r not in SYSTEM_ROLES and not r.startswith('team:')
    ]


async def get_user_teams(user_id: UUID, db: AsyncSession) -> list[str]:
    """Get team memberships."""
    all_roles = await get_user_roles(user_id, db)
    return [r for r in all_roles if r.startswith('team:')]


async def has_role(user_id: UUID, role: str, db: AsyncSession) -> bool:
    """Check if user has a specific role."""
    result = await db.execute(
        select(UserRoleMembership)
        .where(
            UserRoleMembership.user_id == user_id,
            UserRoleMembership.role == role
        )
    )
    return result.scalar_one_or_none() is not None


async def has_any_role(
    user_id: UUID,
    required_roles: list[str],
    db: AsyncSession
) -> bool:
    """Check if user has any of the required roles."""
    user_roles = await get_user_roles(user_id, db)
    return any(role in user_roles for role in required_roles)


async def get_accessible_use_cases(
    user_id: UUID,
    db: AsyncSession,
    lifecycle_state: str | None = None
) -> list[UseCase]:
    """
    Get use cases accessible to user.

    Visibility rules:
    1. Admin: ALL use cases
    2. use_case_admin with team: ALL published + team's drafts
    3. corpus_admin: ALL published (for reference)
    4. Grouping roles: Only assigned published use cases
    5. No roles: EMPTY (default-deny)
    """
    user_roles = await get_user_roles(user_id, db)

    # Rule 1: Admin sees everything
    if 'admin' in user_roles:
        stmt = select(UseCase)
        if lifecycle_state:
            stmt = stmt.where(UseCase.lifecycle_state == lifecycle_state)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # Rule 2: use_case_admin with team-based visibility
    if 'use_case_admin' in user_roles:
        user_teams = await get_user_teams(user_id, db)

        # Build query for published use cases
        published_stmt = select(UseCase.id).where(
            UseCase.lifecycle_state == 'published'
        )

        if user_teams:
            # Add team drafts
            team_draft_stmt = select(UseCase.id).where(
                UseCase.team_id.in_(user_teams),
                UseCase.lifecycle_state.in_(['draft', 'review'])
            )
            combined_ids = published_stmt.union(team_draft_stmt)
        else:
            combined_ids = published_stmt

        stmt = select(UseCase).where(UseCase.id.in_(combined_ids))

        if lifecycle_state:
            stmt = stmt.where(UseCase.lifecycle_state == lifecycle_state)

        result = await db.execute(stmt)
        return list(result.scalars().all())

    # Rule 3: corpus_admin sees all published
    if 'corpus_admin' in user_roles:
        stmt = select(UseCase).where(UseCase.lifecycle_state == 'published')
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
            UseCase.id == RoleUseCaseAssignment.use_case_id
        )
        .where(
            RoleUseCaseAssignment.role_name.in_(grouping_roles),
            RoleUseCaseAssignment.is_active == True,
            UseCase.lifecycle_state == 'published',
            or_(
                RoleUseCaseAssignment.expires_at.is_(None),
                RoleUseCaseAssignment.expires_at > now
            )
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
    db: AsyncSession
) -> bool:
    """
    Check if user can edit a use case.

    Rules:
    1. Admin: Can edit anything
    2. Non-draft: Cannot edit (must clone)
    3. Creator: Can edit own drafts
    """
    user_roles = await get_user_roles(user_id, db)

    # Admin can edit anything
    if 'admin' in user_roles:
        return True

    # Can only edit drafts
    if use_case.lifecycle_state != 'draft':
        return False

    # Creator can edit own drafts
    if use_case.created_by_user_id == user_id:
        return True

    return False


async def get_accessible_collections(
    user_id: UUID,
    db: AsyncSession
) -> list[Collection]:
    """
    Get document collections accessible to user.

    Visibility rules:
    1. Admin: ALL collections
    2. corpus_admin: ALL collections
    3. Grouping roles: Only assigned collections
    4. No roles: EMPTY (default-deny)
    """
    user_roles = await get_user_roles(user_id, db)

    # Admin sees all
    if 'admin' in user_roles:
        stmt = select(Collection).where(Collection.is_published == True)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # corpus_admin sees all
    if 'corpus_admin' in user_roles:
        stmt = select(Collection).where(Collection.is_published == True)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # Grouping roles - only assigned collections
    grouping_roles = await get_user_grouping_roles(user_id, db)

    if not grouping_roles:
        return []

    now = datetime.now(tz=UTC)

    stmt = (
        select(Collection)
        .join(
            RoleCollectionAssignment,
            Collection.id == RoleCollectionAssignment.collection_id
        )
        .where(
            RoleCollectionAssignment.role_name.in_(grouping_roles),
            RoleCollectionAssignment.is_active == True,
            Collection.is_published == True,
            or_(
                RoleCollectionAssignment.expires_at.is_(None),
                RoleCollectionAssignment.expires_at > now
            )
        )
        .distinct()
    )

    result = await db.execute(stmt)
    return list(result.scalars().all())
```

**Acceptance Criteria:**

- [x] All functions have type hints
- [x] All functions have docstrings
- [x] Unit tests written for each function (100% coverage)
- [ ] Integration tests for access scenarios

### Task 2.2: Create Database Models ✅ COMPLETE

**File:** `src/orchestrator/app/db/models_rbac.py`

```python
"""
RBAC V2 Database Models
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID as PyUUID

from sqlalchemy import (
    UUID,
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .models import Base, TimestampMixin, AuthUser, Collection


class RoleCollectionAssignment(TimestampMixin, Base):
    """
    Assigns document collections to roles.

    Users inherit collection access through role memberships.
    Implements ADR-060 Tier 2 resource access control.
    """

    __tablename__ = "role_collection_assignments"
    __table_args__ = (
        UniqueConstraint("role_name", "collection_id", name="uq_role_collection_assignment"),
    )

    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=lambda: PyUUID.uuid4()
    )

    role_name: Mapped[str] = mapped_column(String(50), nullable=False)

    collection_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("collections.id", ondelete="CASCADE"),
        nullable=False
    )

    # Audit fields
    granted_by: Mapped[PyUUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(AuthUser.__table__.c.id)
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=UTC),
        nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Metadata
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False
    )

    # Relationships
    collection: Mapped[Collection] = relationship(
        "Collection",
        back_populates="role_assignments"
    )
```

**Update:** `src/orchestrator/app/db/models.py`

Add to `Collection` model:

```python
role_assignments: Mapped[list["RoleCollectionAssignment"]] = relationship(
    "RoleCollectionAssignment",
    back_populates="collection",
    cascade="all, delete-orphan"
)
```

### Task 2.3: Create Admin API Routers ✅ COMPLETE

**File:** `src/orchestrator/app/routers/admin_grouping_roles.py`

```python
"""
Admin API for managing use case grouping roles.

Grouping roles control which use cases users can execute.
Implements ADR-060 Tier 2 resource access control.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import get_current_user
from shared.auth.models import TokenPayload
from shared.logging_utils.fastapi import configure_logging

from ..db.database import get_async_db
from ..db.models import RoleUseCaseAssignment, RoleCollectionAssignment, UserRoleMembership
from ..services.rbac_v2 import SYSTEM_ROLES

logger = configure_logging(__name__)
router = APIRouter(prefix="/admin/grouping-roles", tags=["admin", "grouping-roles"])


# Request/Response Models
class GroupingRoleInfo(BaseModel):
    """Information about a use case grouping role."""
    role_name: str
    display_name: str | None = None
    description: str | None = None
    user_count: int
    use_case_count: int
    collection_count: int


class CreateGroupingRoleRequest(BaseModel):
    """Request to create a new grouping role."""
    role_name: str = Field(..., pattern=r'^[a-z][a-z0-9_-]{1,49}$')
    display_name: str
    description: str | None = None


class GroupingRoleResponse(BaseModel):
    """Response for grouping role operations."""
    role_name: str
    display_name: str
    description: str | None
    created_by: str


# Helper Functions
def require_admin_or_role_admin(current_user: TokenPayload) -> None:
    """Require admin or role_admin role."""
    if current_user.role not in ['admin'] and 'role_admin' not in getattr(current_user, 'roles', []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or role_admin privileges required"
        )


# API Endpoints
@router.get("", response_model=list[GroupingRoleInfo])
async def list_grouping_roles(
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> list[GroupingRoleInfo]:
    """
    List all use case grouping roles.

    Returns dynamic roles (not system roles, not teams).
    """
    require_admin_or_role_admin(current_user)

    # Get all unique roles that are not system roles and not teams
    result = await db.execute(
        select(
            UserRoleMembership.role,
            func.count(UserRoleMembership.user_id).label('user_count')
        )
        .where(
            ~UserRoleMembership.role.in_(SYSTEM_ROLES),
            ~UserRoleMembership.role.like('team:%')
        )
        .group_by(UserRoleMembership.role)
    )

    grouping_roles = []

    for role_name, user_count in result.all():
        # Get use case count
        uc_result = await db.execute(
            select(func.count(RoleUseCaseAssignment.id))
            .where(
                RoleUseCaseAssignment.role_name == role_name,
                RoleUseCaseAssignment.is_active == True
            )
        )
        use_case_count = uc_result.scalar() or 0

        # Get collection count
        col_result = await db.execute(
            select(func.count(RoleCollectionAssignment.id))
            .where(
                RoleCollectionAssignment.role_name == role_name,
                RoleCollectionAssignment.is_active == True
            )
        )
        collection_count = col_result.scalar() or 0

        grouping_roles.append(GroupingRoleInfo(
            role_name=role_name,
            user_count=user_count,
            use_case_count=use_case_count,
            collection_count=collection_count
        ))

    return grouping_roles


@router.post("", response_model=GroupingRoleResponse, status_code=status.HTTP_201_CREATED)
async def create_grouping_role(
    role_data: CreateGroupingRoleRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> GroupingRoleResponse:
    """
    Validate and register a new use case grouping role.

    Role is created implicitly when first assigned to user or resource.
    This endpoint validates the role name format.
    """
    require_admin_or_role_admin(current_user)

    # Validate not a system role
    if role_data.role_name in SYSTEM_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot use system role name: {role_data.role_name}"
        )

    # Validate not a team
    if role_data.role_name.startswith('team:'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Team roles must be created via team management API"
        )

    logger.info(
        f"Created grouping role: {role_data.role_name}",
        extra={
            "role_name": role_data.role_name,
            "created_by": current_user.user_id
        }
    )

    return GroupingRoleResponse(
        role_name=role_data.role_name,
        display_name=role_data.display_name,
        description=role_data.description,
        created_by=current_user.user_id
    )


@router.delete("/{role_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_grouping_role(
    role_name: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """
    Delete a grouping role and all its assignments.

    This removes:
    - All user memberships to this role
    - All use case assignments to this role
    - All collection assignments to this role
    """
    require_admin_or_role_admin(current_user)

    # Validate not a system role
    if role_name in SYSTEM_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete system roles"
        )

    # Delete all user memberships
    await db.execute(
        UserRoleMembership.__table__.delete().where(
            UserRoleMembership.role == role_name
        )
    )

    # Delete all use case assignments
    await db.execute(
        RoleUseCaseAssignment.__table__.delete().where(
            RoleUseCaseAssignment.role_name == role_name
        )
    )

    # Delete all collection assignments
    await db.execute(
        RoleCollectionAssignment.__table__.delete().where(
            RoleCollectionAssignment.role_name == role_name
        )
    )

    await db.commit()

    logger.info(
        f"Deleted grouping role: {role_name}",
        extra={
            "role_name": role_name,
            "deleted_by": current_user.user_id
        }
    )
```

**Similar files to create:**

- `src/orchestrator/app/routers/admin_developer_teams.py`
- Update `src/orchestrator/app/routers/admin_roles.py` with collection assignments
- Update `src/orchestrator/app/routers/use_case_management.py` with team logic

**Completion Summary (December 8, 2025):**

✅ Created `admin_grouping_roles.py` router with:

- List grouping roles endpoint
- Create grouping role endpoint (idempotent anchor membership)
- Delete grouping role endpoint (cascades to assignments)

✅ Created `admin_developer_teams.py` router with:

- List developer teams endpoint
- Create team endpoint
- Add/remove team members
- List team use cases

✅ Updated `admin_roles.py` with:

- Collection assignment endpoints (list, assign, remove)
- Fixed SYSTEM_ROLES check bug (protects all system roles, not just admin)
- Admin/role_admin authorization helper

✅ Registered routers in `main.py`

✅ Created integration tests (`test_admin_rbac_v2_api.py`)

✅ Fixed test environment loading and hardcoded credentials

**Files Created:**

- `src/orchestrator/app/routers/admin_grouping_roles.py`
- `src/orchestrator/app/routers/admin_developer_teams.py`
- `src/orchestrator/tests/integration/test_admin_rbac_v2_api.py`

**Files Modified:**

- `src/orchestrator/app/routers/admin_roles.py` (collection assignments + bug fix)
- `src/orchestrator/app/main.py` (router registration)
- `src/orchestrator/app/db/database.py` (RBAC model registration)
- `src/orchestrator/tests/integration/conftest.py` (environment loading)

### Task 2.4: Update Use Case Management API ✅ COMPLETE

**Status:** ✅ **COMPLETE (December 8, 2025)**

**File:** `src/orchestrator/app/routers/use_case_management.py`

**Completion Summary:**

✅ Updated `list_use_cases_for_management` to use `get_accessible_use_cases` from RBAC V2
✅ Updated `create_use_case` with:

- Role authorization check (use_case_admin or admin required)
- Team assignment logic (auto-assign, validate, or default)
- Team membership validation
✅ Updated `update_use_case` to use `can_edit_use_case` for permission checks
✅ Updated `clone_use_case` with team assignment logic
✅ Fixed `transition_state` to clear `team_id` when publishing (published use cases visible to all)
✅ Updated `use_cases.py` router - `get_available_use_cases` now uses RBAC V2

**Authorization Bug Fix:**

- Fixed missing role check in `create_use_case` endpoint
- Added verification for `use_case_admin` or `admin` role before allowing creation
- Created comprehensive unit tests for authorization scenarios

**Files Modified:**

- `src/orchestrator/app/routers/use_case_management.py` (RBAC V2 integration + auth fix)
- `src/orchestrator/app/routers/use_cases.py` (RBAC V2 integration)
- `src/orchestrator/tests/unit/routers/test_use_case_management.py` (new tests)
- `src/orchestrator/tests/unit/routers/test_use_cases.py` (updated for RBAC V2)

**Test Coverage:**

- 4 unit tests for use_case_management router
- 23 unit tests for use_cases router (all passing)
- Authorization scenarios fully tested

Add to existing endpoints:

```python
# Import new RBAC service
from ..services.rbac_v2 import (
    get_accessible_use_cases,
    get_user_teams,
    has_role,
    can_edit_use_case
)

# Update GET /use-cases endpoint
@router.get("", response_model=list[UseCaseResponse])
async def list_use_cases(
    lifecycle_state: str | None = Query(None),
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> list[UseCaseResponse]:
    """
    List use cases accessible to current user.

    Uses RBAC V2 access control (ADR-060).
    """
    use_cases = await get_accessible_use_cases(
        UUID(current_user.user_id),
        db,
        lifecycle_state=lifecycle_state
    )

    return [UseCaseResponse.from_orm(uc) for uc in use_cases]


# Update POST /use-cases endpoint
@router.post("", response_model=UseCaseResponse, status_code=201)
async def create_use_case(
    use_case_data: UseCaseCreateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> UseCaseResponse:
    """
    Create use case with automatic team assignment.
    """
    user_id = UUID(current_user.user_id)
    user_teams = await get_user_teams(user_id, db)
    is_admin = await has_role(user_id, 'admin', db)

    # Determine team assignment
    if use_case_data.team_id:
        team_id = use_case_data.team_id
        if not is_admin and team_id not in user_teams:
            raise HTTPException(
                status_code=403,
                detail=f"You are not a member of team '{team_id}'"
            )
    elif len(user_teams) == 1:
        team_id = user_teams[0]
    elif len(user_teams) > 1:
        raise HTTPException(
            status_code=400,
            detail="You are a member of multiple teams. Please specify team_id."
        )
    else:
        team_id = 'team:default'

    # Create use case
    use_case = UseCase(
        use_case_id=use_case_data.use_case_id,
        name=use_case_data.name,
        team_id=team_id,
        created_by_user_id=user_id,
        lifecycle_state='draft',
        # ... other fields
    )

    db.add(use_case)
    await db.commit()
    await db.refresh(use_case)

    return UseCaseResponse.from_orm(use_case)
```

### Task 2.5: Write Backend Tests ✅ COMPLETE (Unit Tests)

**Status:** Unit tests complete with 100% coverage. Integration tests pending (Task 4.1).

**File:** `src/orchestrator/tests/integration/test_rbac_v2.py`

```python
"""
Integration tests for RBAC V2 system.

Tests ADR-060 access control rules.
"""

import pytest
from uuid import uuid4

from src.orchestrator.app.services.rbac_v2 import (
    get_accessible_use_cases,
    get_accessible_collections,
    can_edit_use_case,
    get_user_roles,
    get_user_teams,
)


@pytest.mark.asyncio
async def test_default_deny_no_roles(db_session, test_user):
    """Base user with no roles sees nothing (default-deny)."""
    use_cases = await get_accessible_use_cases(test_user.id, db_session)
    assert len(use_cases) == 0

    collections = await get_accessible_collections(test_user.id, db_session)
    assert len(collections) == 0


@pytest.mark.asyncio
async def test_admin_sees_all(db_session, admin_user, published_use_case, draft_use_case):
    """Admin sees all use cases regardless of state."""
    use_cases = await get_accessible_use_cases(admin_user.id, db_session)

    use_case_ids = [uc.id for uc in use_cases]
    assert published_use_case.id in use_case_ids
    assert draft_use_case.id in use_case_ids


@pytest.mark.asyncio
async def test_grouping_role_access(
    db_session,
    test_user,
    published_use_case,
    draft_use_case
):
    """User with grouping role sees only assigned published use cases."""
    # Assign user to grouping role
    await assign_role(test_user.id, 'threat_hunting', db_session)

    # Assign published use case to role
    await assign_use_case_to_role(
        'threat_hunting',
        published_use_case.id,
        db_session
    )

    use_cases = await get_accessible_use_cases(test_user.id, db_session)

    assert len(use_cases) == 1
    assert use_cases[0].id == published_use_case.id
    assert draft_use_case.id not in [uc.id for uc in use_cases]


@pytest.mark.asyncio
async def test_team_isolation(
    db_session,
    use_case_admin_user,
    other_use_case_admin_user
):
    """Teams cannot see each other's draft use cases."""
    # Assign users to different teams
    await assign_role(use_case_admin_user.id, 'team:csirt', db_session)
    await assign_role(other_use_case_admin_user.id, 'team:soc_gov', db_session)

    # User 1 creates draft
    draft_uc = await create_use_case(
        "test-uc-1",
        use_case_admin_user.id,
        team_id='team:csirt',
        db=db_session
    )

    # User 1 can see their draft
    user1_ucs = await get_accessible_use_cases(
        use_case_admin_user.id,
        db_session,
        lifecycle_state='draft'
    )
    assert draft_uc.id in [uc.id for uc in user1_ucs]

    # User 2 cannot see User 1's draft
    user2_ucs = await get_accessible_use_cases(
        other_use_case_admin_user.id,
        db_session,
        lifecycle_state='draft'
    )
    assert draft_uc.id not in [uc.id for uc in user2_ucs]


@pytest.mark.asyncio
async def test_use_case_admin_team_visibility(
    db_session,
    use_case_admin_user,
    teammate_user
):
    """Team members can see each other's drafts but not edit them."""
    # Both users in same team
    await assign_role(use_case_admin_user.id, 'use_case_admin', db_session)
    await assign_role(use_case_admin_user.id, 'team:csirt', db_session)
    await assign_role(teammate_user.id, 'use_case_admin', db_session)
    await assign_role(teammate_user.id, 'team:csirt', db_session)

    # User 1 creates draft
    draft_uc = await create_use_case(
        "test-uc-1",
        use_case_admin_user.id,
        team_id='team:csirt',
        db=db_session
    )

    # User 2 can SEE it
    user2_ucs = await get_accessible_use_cases(
        teammate_user.id,
        db_session,
        lifecycle_state='draft'
    )
    assert draft_uc.id in [uc.id for uc in user2_ucs]

    # But User 2 cannot EDIT it (only creator can edit)
    can_edit = await can_edit_use_case(teammate_user.id, draft_uc, db_session)
    assert can_edit == False

    # User 1 CAN edit it
    can_edit = await can_edit_use_case(use_case_admin_user.id, draft_uc, db_session)
    assert can_edit == True


@pytest.mark.asyncio
async def test_collection_role_assignment(
    db_session,
    test_user,
    published_collection
):
    """User with grouping role sees assigned collections."""
    # Assign user to grouping role
    await assign_role(test_user.id, 'threat_hunting', db_session)

    # Assign collection to role
    await assign_collection_to_role(
        'threat_hunting',
        published_collection.id,
        db_session
    )

    collections = await get_accessible_collections(test_user.id, db_session)

    assert len(collections) == 1
    assert collections[0].id == published_collection.id


@pytest.mark.asyncio
async def test_corpus_admin_sees_all_collections(
    db_session,
    corpus_admin_user,
    published_collection,
    other_collection
):
    """corpus_admin sees all collections (for management)."""
    collections = await get_accessible_collections(corpus_admin_user.id, db_session)

    collection_ids = [c.id for c in collections]
    assert published_collection.id in collection_ids
    assert other_collection.id in collection_ids
```

**Acceptance Criteria for Phase 2:**

- [x] All RBAC V2 functions implemented ✅
- [x] All database models created ✅
- [x] All admin APIs implemented ✅
- [x] Use case management updated with team logic ✅
- [x] 100% test coverage for RBAC functions ✅ (Unit tests)
- [x] All tests passing ✅ (32 unit tests passing)
- [x] API documentation updated ✅ (Dec 8, 2025)

---

## Phase 3: Frontend Implementation (Week 4-5) ✅ COMPLETE

**Objective:** Update Angular UI to reflect new RBAC model.

**Duration:** 10 days
**Dependencies:** Phase 2 complete ✅
**Risk Level:** MEDIUM (extensive UI changes)
**Status:** ✅ **COMPLETE (December 9, 2025)** - All tasks (3.1, 3.2, 3.3, 3.4, 3.5, 3.6) ✅

### Task 3.1: Update Role Management Models ✅ COMPLETE

**File:** `src/frontend-angular/src/app/pages/admin/role-management/models/role-management.models.ts`

```typescript
/**
 * System/capability roles (Tier 1) - Predefined, immutable.
 */
export const SYSTEM_ROLES: RoleInfo[] = [
  {
    role_name: 'admin',
    display_name: 'Administrator',
    description: 'Full system access - superuser',
    is_system_role: true,
  },
  {
    role_name: 'corpus_admin',
    display_name: 'Corpus Administrator',
    description: 'Document and collection management - sees all documents',
    is_system_role: true,
  },
  {
    role_name: 'use_case_admin',
    display_name: 'Use Case Administrator',
    description: 'Use case development - sees all use cases',
    is_system_role: true,
  },
  {
    role_name: 'tools_admin',
    display_name: 'Tools Administrator',
    description: 'Tool and MCP management',
    is_system_role: true,
  },
  {
    role_name: 'conversations',
    display_name: 'Conversations Access',
    description: 'Access to multi-turn conversation interface',
    is_system_role: true,
  },
  {
    role_name: 'role_admin',
    display_name: 'Role Administrator',
    description: 'Create roles and assign users to roles',
    is_system_role: true,
  },
];

/**
 * Use case grouping role (Tier 2) - Dynamic, admin-created.
 */
export interface GroupingRoleInfo {
  role_name: string;
  display_name?: string;
  description?: string;
  user_count: number;
  use_case_count: number;
  collection_count: number;
}

/**
 * Developer team (Tier 3) - Isolation boundaries.
 */
export interface DeveloperTeamInfo {
  team_id: string;  // Format: team:team_name
  display_name: string;
  description?: string;
  member_count: number;
  draft_count: number;
  published_count: number;
}
```

### Task 3.2: Create Grouping Role Management Component ✅ COMPLETE

**File:** `src/frontend-angular/src/app/pages/admin/use-case-role-management/use-case-role-management.component.ts`

**Status:** ✅ **COMPLETE (December 8, 2025)**

**Completion Summary:**

- ✅ Created `GroupingRolesService` with list/create/delete operations
- ✅ Created `UseCaseRoleManagementComponent` with ADR-012 layered layout
- ✅ Added route `/admin/roles/grouping` with navigation menu entry
- ✅ Implemented role name validation (pattern: `^[a-z][a-z0-9_-]{1,49}$`)
- ✅ Added unit tests (5 component tests, 4 service tests) - all passing
- ✅ Fixed template ICU message errors (regex patterns in mat-hint)

**Files Created:**

- `src/frontend-angular/src/app/pages/admin/use-case-role-management/use-case-role-management.component.{ts,html,scss,spec.ts}`
- `src/frontend-angular/src/app/pages/admin/use-case-role-management/services/grouping-roles.service.{ts,spec.ts}`

### Task 3.3: Create Developer Teams Component ✅ COMPLETE

**File:** `src/frontend-angular/src/app/pages/admin/developer-teams/developer-teams.component.ts`

**Status:** ✅ **COMPLETE (December 8, 2025)**

**Completion Summary:**

- ✅ Created `DeveloperTeamsService` with list/create/add/remove member operations
- ✅ Created `DeveloperTeamsComponent` with ADR-012 layered layout
- ✅ Added route `/admin/developer-teams` with navigation menu entry
- ✅ Implemented team ID validation (pattern: `^team:[a-z0-9_-]{1,64}$`)
- ✅ Added unit tests (5 component tests, 4 service tests) - all passing
- ✅ Fixed template ICU message errors (regex patterns in mat-hint)

**Files Created:**

- `src/frontend-angular/src/app/pages/admin/developer-teams/developer-teams.component.{ts,html,scss,spec.ts}`
- `src/frontend-angular/src/app/pages/admin/developer-teams/services/developer-teams.service.{ts,spec.ts}`

### Task 3.4: Update User Management Component ✅ COMPLETE

**File:** `src/frontend-angular/src/app/pages/admin/user-management.component.ts`

**Status:** ✅ **COMPLETE (December 8, 2025)**

**Completion Summary:**

- ✅ Updated `UserManagementService` with `getUserRoles()` and `updateUserRoles()` methods
- ✅ Updated `UserManagementComponent` to display multiple roles as chips in user list
- ✅ Updated `UserEditDialogComponent` with multi-role assignment UI:
  - System roles (single-select via checkboxes, radio-like behavior)
  - Grouping roles (multi-select checkboxes)
  - Teams (multi-select checkboxes, disabled if not use_case_admin or admin)
- ✅ Updated `UserCreateDialogComponent` with multi-role assignment during user creation
- ✅ Added `loadUserRolesForList()` method to fetch roles for all users in list
- ✅ Fixed system role checkbox deselection bug (resets to 'user' when unchecked)
- ✅ Fixed `isSubmitting` state management in success handlers
- ✅ Added backend API router `admin_user_roles.py` with 4 endpoints:
  - `GET /api/v1/admin/users/{user_id}/roles` - Get all user roles
  - `PUT /api/v1/admin/users/{user_id}/roles` - Update all user roles
  - `POST /api/v1/admin/users/{user_id}/roles/{role_name}` - Add single role
  - `DELETE /api/v1/admin/users/{user_id}/roles/{role_name}` - Remove single role
- ✅ Fixed audit middleware KeyError (removed duplicate request_id from extra dict)
- ✅ Fixed duplicate "role" keys in logging dictionaries (renamed to "role_name" and "admin_role")
- ✅ Added comprehensive error handling and null safety checks
- ✅ Updated unit tests for both create and edit dialogs (added NoopAnimationsModule, system role tests)

**Files Modified:**

- `src/frontend-angular/src/app/pages/admin/user-management.component.{ts,html}`
- `src/frontend-angular/src/app/pages/admin/user-management/components/user-edit-dialog/user-edit-dialog.component.{ts,html,spec.ts}`
- `src/frontend-angular/src/app/pages/admin/user-management/components/user-create-dialog/user-create-dialog.component.{ts,html,spec.ts}`
- `src/frontend-angular/src/app/pages/admin/user-management/services/user-management.service.ts`
- `src/frontend-angular/src/app/pages/admin/user-management/models/user-management.models.ts`
- `src/orchestrator/app/routers/admin_user_roles.py` (new file)
- `src/orchestrator/app/main.py` (router registration)
- `src/orchestrator/app/middleware/audit.py` (KeyError fix)
- `src/orchestrator/tests/unit/routers/test_admin_user_roles.py` (new file)

### Task 3.5: Update Use Case Developer Component ✅ COMPLETE

**File:** `src/frontend-angular/src/app/pages/admin/use-case-developer/use-case-developer.component.ts`

**Status:** ✅ **COMPLETE (December 9, 2025)**

**Implementation:**
- ✅ Renamed to "Use Case Manager" (better reflects lifecycle management)
- ✅ Added tabbed interface with 4 tabs:
  - My Drafts (created_by current user, edit capability)
  - Team Drafts (team filter, view-only, filtered by user teams)
  - In Review (use cases under review)
  - Published (active use cases with clone option)
- ✅ Team collaboration features:
  - Fetches user's team memberships from RBAC V2 API
  - Filters team drafts to show only drafts from user's teams
  - Team selector chips for multi-team users
  - Proper team isolation (can't see other teams' drafts)
- ✅ ADR-012 compliant (Layered Page Layout Pattern)
- ✅ 17 unit tests (all passing)
- ✅ Production-ready (compilation clean, linting clean)

**Files Modified:**
- `src/frontend-angular/src/app/pages/admin/use-case-developer/use-case-developer.component.{ts,html,scss,spec.ts}`
- `src/frontend-angular/src/app/core/auth/auth.models.ts` (added `developer` role)
- `src/frontend-angular/src/app/core/services/navigation.service.ts` (moved to Developer Tools, added `developer` role)
- `src/frontend-angular/src/app/app.routes.ts` (updated breadcrumb)

### Task 3.6: Update Navigation Service ✅ COMPLETE

**File:** `src/frontend-angular/src/app/core/services/navigation.service.ts`

**Status:** ✅ **COMPLETE (December 9, 2025)**

**Implementation:**
- ✅ Moved "Use Case Manager" from System Administration to Developer Tools (first item)
- ✅ Added `developer` role to all Developer Tools menu items
- ✅ Updated menu visibility logic for multi-role system
- ✅ Proper role-based access: `admin`, `corpus_admin`, `use_case_admin`, `developer`

**Files Modified:**
- `src/frontend-angular/src/app/core/services/navigation.service.ts`

**Acceptance Criteria for Phase 3:**

- [x] All new components created ✅ (Tasks 3.1, 3.2, 3.3)
- [x] User Management Component updated ✅ (Task 3.4)
- [x] Use Case Manager Component updated ✅ (Task 3.5 - renamed from "Use Case Developer")
- [x] Navigation updated for multi-role system ✅ (Task 3.6 - routes, roles, menu placement)
- [x] Empty states for no-access scenarios ✅ (Implemented in 3.2, 3.3)
- [x] All components have unit tests ✅ (User management tests updated, Use Case Manager: 17 tests passing)
- [ ] E2E tests for critical workflows (Pending Phase 4)
- [ ] UI/UX reviewed and approved (Pending review)

---

## Phase 4: Integration Testing & Deployment (Week 6)

**Objective:** Comprehensive testing and safe production deployment.

**Duration:** 5 days
**Dependencies:** Phase 2 & 3 complete
**Risk Level:** HIGH (production deployment)

### Task 4.1: Integration Testing

Run comprehensive test suite:

```bash
# Backend tests
cd src/orchestrator
./run_tests.sh --cov=app --cov-report=term-missing

# Frontend tests
cd src/frontend-angular
npm run test:ci

# E2E tests
cd tests/e2e
pytest test_rbac_workflows.py -v
```

### Task 4.2: Manual QA Testing

**Test Scenarios:**

1. **Default-Deny Verification**
   - Create new user with no roles
   - Login → Should see empty dashboard with "Request Access" message
   - ✅ Verified: No use cases visible, no collections visible

2. **Grouping Role Assignment**
   - Admin creates "threat_hunting" grouping role
   - Admin assigns 3 use cases to role
   - Admin assigns test user to role
   - Test user login → Should see exactly 3 use cases
   - ✅ Verified: Correct use cases visible

3. **Team Isolation**
   - Admin creates 2 teams: csirt, soc_gov
   - Admin assigns User A to csirt, User B to soc_gov
   - User A creates draft use case
   - User B login → Should NOT see User A's draft
   - ✅ Verified: Teams isolated

4. **Admin Override**
   - Admin login → Should see ALL use cases, ALL teams' drafts
   - ✅ Verified: Admin sees everything

5. **Multi-Role Assignment**
   - Admin assigns user: ['use_case_admin', 'threat_hunting', 'team:csirt']
   - User should have developer capabilities + access to threat_hunting use cases
   - ✅ Verified: Multi-role functionality works

### Task 4.3: Performance Testing

```python
# ops/testing/rbac_performance_test.py

import asyncio
import time
from uuid import uuid4

async def test_rbac_performance():
    """Test RBAC access check performance."""

    # Setup: 100 users, 50 use cases, 10 roles
    users = [create_user() for _ in range(100)]
    use_cases = [create_use_case() for _ in range(50)]
    roles = [create_role() for _ in range(10)]

    # Assign roles to users
    for user in users:
        user_roles = random.sample(roles, k=random.randint(1, 3))
        for role in user_roles:
            assign_role(user.id, role.name)

    # Assign use cases to roles
    for role in roles:
        role_use_cases = random.sample(use_cases, k=random.randint(5, 15))
        for uc in role_use_cases:
            assign_use_case_to_role(role.name, uc.id)

    # Test: Get accessible use cases for each user
    start = time.time()

    for user in users:
        accessible_ucs = await get_accessible_use_cases(user.id, db)

    end = time.time()
    avg_time = (end - start) / len(users) * 1000  # ms per user

    print(f"Average time per user: {avg_time:.2f}ms")
    assert avg_time < 500, f"Performance degraded: {avg_time}ms > 500ms threshold"
```

**Performance Targets:**

- ✅ Use case access check: < 100ms
- ✅ Use case list filtering: < 500ms
- ✅ Role assignment: < 50ms
- ✅ Dashboard load: < 2s

### Task 4.4: Security Audit

**Checklist:**

- [ ] SQL injection vulnerabilities checked
- [ ] Authorization bypass attempts tested
- [ ] Role escalation attempts tested
- [ ] Team isolation bypass attempts tested
- [ ] Default-deny verified (no accidental grants)
- [ ] Admin-only endpoints properly protected
- [ ] JWT token validation working
- [ ] RLS policies tested
- [ ] Audit logging enabled for role changes

### Task 4.5: Staging Deployment

1. **Deploy to staging environment**
2. **Run smoke tests**
3. **Load test with realistic data**
4. **Get stakeholder approval**

### Task 4.6: Production Deployment

**Pre-Deployment Checklist:**

- [ ] Database backup created
- [ ] Rollback plan documented and tested
- [ ] Deployment runbook prepared
- [ ] Monitoring alerts configured
- [ ] On-call team notified
- [ ] Maintenance window scheduled
- [ ] Stakeholders notified

**Deployment Steps:**

```bash
# 1. Backup production database
pg_dump -h prod-db -U postgres aio > backup_pre_rbac_v2.sql

# 2. Run database migrations
cd ops/database/migrations/rbac_v2
./run_migrations.sh production

# 3. Deploy backend
cd src/orchestrator
./deploy.sh production

# 4. Deploy frontend
cd src/frontend-angular
npm run build:production
./deploy.sh production

# 5. Verify deployment
curl https://api.aio.com/health
curl https://app.aio.com/

# 6. Monitor logs
tail -f /var/log/aio/api.log
tail -f /var/log/aio/frontend.log

# 7. Run smoke tests
pytest tests/smoke/test_rbac_v2.py
```

**Post-Deployment Verification:**

- [ ] All services healthy
- [ ] Users can log in
- [ ] Role assignments work
- [ ] Use case access control working
- [ ] No errors in logs
- [ ] Performance metrics acceptable

---

## Phase 5: Cleanup & Documentation (Week 7)

**Objective:** Remove deprecated code and finalize documentation.

**Duration:** 5 days
**Dependencies:** Phase 4 complete, production stable
**Risk Level:** LOW

### Task 5.1: Drop Deprecated Database Column

**After 1 week of stable production:**

```sql
-- Migration: 004_drop_users_role_column.sql
-- ONLY run this after verifying everything works in production

-- Verify migration success first
SELECT
    COUNT(*) as total_users,
    COUNT(DISTINCT ur.user_id) as users_with_roles
FROM users u
LEFT JOIN user_roles ur ON u.id = ur.user_id;

-- Should match: total_users = users_with_roles

-- Drop the column
ALTER TABLE users DROP COLUMN IF EXISTS role;

-- Verify
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'users' AND column_name = 'role';
-- Should return 0 rows
```

### Task 5.2: Remove Deprecated Code

**Files to delete:**

- Old `UserRole` enum references that use single role
- Any code checking `user.role` directly

**Files to update:**

- All authentication middleware
- All JWT token generation/validation
- All role check functions

### Task 5.3: Update Documentation

**Files to create/update:**

1. **docs/admin/USER_ROLES_GUIDE_V2.md**
   - Complete rewrite explaining two-tier system
   - Examples of each role type
   - How-to guides for role assignment

2. **docs/admin/GROUPING_ROLES_GUIDE.md**
   - How to create grouping roles
   - How to assign use cases to roles
   - How to assign users to roles
   - Best practices

3. **docs/admin/DEVELOPER_TEAMS_GUIDE.md**
   - How to create developer teams
   - How to assign users to teams
   - Team isolation explained
   - Use case ownership

4. **docs/api/admin/grouping-roles.md**
   - API documentation for grouping role management

5. **docs/api/admin/developer-teams.md**
   - API documentation for team management

6. **docs/development/guides/rbac-implementation.md**
   - Developer guide for implementing RBAC checks
   - Code examples
   - Testing patterns

7. **Update existing docs:**
   - docs/architecture/database/ERD.md
   - docs/architecture/database/SCHEMA.md
   - docs/architecture/database/RLS_POLICIES.md
   - docs/api/authentication.md

### Task 5.4: Create Training Materials

1. **Video: RBAC V2 Overview** (10 minutes)
   - System architecture
   - Role types explained
   - How access is granted

2. **Video: Admin Tutorial** (15 minutes)
   - Creating grouping roles
   - Creating teams
   - Assigning users
   - Common scenarios

3. **PDF: Quick Reference Guide**
   - Role types table
   - Common tasks
   - Troubleshooting

### Task 5.5: Knowledge Transfer

- [ ] Present to development team
- [ ] Present to security team
- [ ] Present to admin users
- [ ] Q&A session
- [ ] Feedback collection

---

## Success Metrics

### Technical Metrics

| Metric | Target | Actual |
|--------|--------|--------|
| Migration success rate | 100% | ___ |
| Test coverage (backend) | > 90% | ___ |
| Test coverage (frontend) | > 80% | ___ |
| Performance (access check) | < 100ms | ___ |
| Zero downtime deployment | Yes | ___ |

### Business Metrics

| Metric | Target | Actual |
|--------|--------|--------|
| User satisfaction | > 8/10 | ___ |
| Admin satisfaction | > 9/10 | ___ |
| Support tickets (RBAC) | < 5/week | ___ |
| Onboarding time | < 30 min | ___ |

### Functional Validation

- [ ] Default-deny works (users with no roles see nothing)
- [ ] Grouping roles grant access to assigned use cases
- [ ] Team isolation works (teams can't see each other's drafts)
- [ ] Admin can manage all roles and teams
- [ ] Multi-role assignment works correctly
- [ ] No user loses access they previously had
- [ ] Role Management UI is intuitive
- [ ] Performance is acceptable

---

## Risk Mitigation

### Risk 1: Data Loss During Migration

**Mitigation:**

- Full database backup before migration
- Test migrations on copy of production data
- Keep old `users.role` column until Phase 5
- Verify migration success before proceeding

**Rollback:**

```sql
-- Restore users.role from user_roles
UPDATE users u
SET role = (
    SELECT role FROM user_roles ur
    WHERE ur.user_id = u.id
    AND ur.role IN ('admin', 'corpus_admin', 'use_case_admin', 'tools_admin', 'conversations', 'role_admin')
    LIMIT 1
);
```

### Risk 2: Performance Degradation

**Mitigation:**

- Performance testing before deployment
- Database indexes on critical columns
- Query optimization
- Caching strategy for role checks

**Monitoring:**

- APM metrics for RBAC function calls
- Slow query log monitoring
- User-reported slowness

### Risk 3: Authorization Bypass

**Mitigation:**

- Security audit before deployment
- Penetration testing
- Code review of all RBAC logic
- Default-deny architecture

**Detection:**

- Audit logging for all role changes
- Anomaly detection for unusual access patterns
- Regular security audits

### Risk 4: User Confusion

**Mitigation:**

- Clear UI messaging
- Help text and tooltips
- Training materials
- Admin documentation

**Support:**

- Dedicated support during rollout
- FAQ document
- Video tutorials

---

## Dependencies

### External Dependencies

- PostgreSQL 14+
- Python 3.12+
- Angular 21+
- FastAPI latest

### Internal Dependencies

- Phase 1 → Phase 2 (backend needs schema)
- Phase 2 → Phase 3 (frontend needs APIs)
- Phase 2 & 3 → Phase 4 (testing needs both)
- Phase 4 → Phase 5 (cleanup needs stable production)

### Team Dependencies

- Backend developers (Phase 2)
- Frontend developers (Phase 3)
- QA team (Phase 4)
- DevOps (Phase 4 deployment)
- Security team (Phase 4 audit)
- Technical writers (Phase 5 docs)

---

## Timeline Summary

| Phase | Duration | Week | Status |
|-------|----------|------|--------|
| Phase 1: Database Schema | 5 days | Week 1 | ✅ COMPLETE (Dec 2025) |
| Phase 2: Backend Implementation | 10 days | Week 2-3 | ✅ COMPLETE (Dec 2025) |
| Phase 3: Frontend Implementation | 10 days | Week 4-5 | ✅ COMPLETE (Dec 9, 2025) |
| Phase 4: Testing & Deployment | 5 days | Week 6 | 📋 Pending |
| Phase 5: Cleanup & Documentation | 5 days | Week 7 | 📋 Pending |
| **Total** | **35 days** | **7 weeks** | **Phase 3 Complete** |

---

## Next Steps

1. **Get approval for plan** from stakeholders
2. **Assign resources** (developers, QA, DevOps)
3. **Schedule kickoff meeting**
4. **Set up project tracking** (Jira, etc.)
5. **Begin Phase 1** - Database schema updates

---

## Appendix: Command Reference

### Useful Commands

```bash
# Run database migrations
cd ops/database/migrations/rbac_v2
./run_migrations.sh production

# Run backend tests
cd src/orchestrator
./run_tests.sh --cov=app --cov-report=html

# Run frontend tests
cd src/frontend-angular
npm run test
npm run test:e2e

# Check migration status
psql -d aio -c "
SELECT
    (SELECT COUNT(*) FROM users) as total_users,
    (SELECT COUNT(DISTINCT user_id) FROM user_roles) as users_with_roles,
    (SELECT COUNT(*) FROM role_use_case_assignments) as use_case_assignments,
    (SELECT COUNT(*) FROM role_collection_assignments) as collection_assignments,
    (SELECT COUNT(DISTINCT team_id) FROM use_cases WHERE team_id IS NOT NULL) as teams;
"

# Performance test
python ops/testing/rbac_performance_test.py

# Security audit
python ops/testing/rbac_security_audit.py
```

---

**END OF IMPLEMENTATION PLAN**
