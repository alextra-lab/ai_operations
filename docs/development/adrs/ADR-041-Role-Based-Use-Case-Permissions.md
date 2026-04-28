# ADR-041: Role-Based Use Case Permissions (Not Intent-Based)

**Status:** ACCEPTED
**Date:** 2025-10-24
**Accepted:** 2025-10-24
**Authors:** Architecture Team
**Related:** ADR-016 (Dynamic Intent System), ADR-020 (Use Case Publisher Role)

---

## Context

Current database schema includes a `role_intent_permissions` table that incorrectly implements permissions at the **Intent Type** level. This contradicts the intended architecture where:

1. **Intent Types** = Configuration presets only (sampling parameters, model recommendations)
2. **Use Cases** = The actual permission boundary
3. **Roles** = Collections of use case access grants

### Current Incorrect Implementation

```
User → Role → [role_intent_permissions] → Intent Type ❌
```

The `role_intent_permissions` table suggests that roles control which intent types users can access. This is **architecturally incorrect** because:

- Intent Types are templates/presets, not executable functionality
- Different use cases with the same intent type may have different access requirements
- Access control should be at the use case level (what users can execute), not the template level

### Current Workaround

The system currently uses `user_use_case_assignments` for **direct user-to-use-case** assignments:

```sql
CREATE TABLE user_use_case_assignments (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    use_case_id UUID NOT NULL REFERENCES use_cases(id),
    assigned_role VARCHAR(20) NOT NULL,  -- Role *within* this use case
    status VARCHAR(20) DEFAULT 'active',
    ...
);
```

This allows individual users to be granted access to specific use cases, but it **does not support role-based access**.

---

## Decision

We will implement **role-based use case permissions** with the following architecture:

### Correct Architecture

```
┌──────┐    assigned to    ┌──────┐    has access to    ┌──────────┐
│ User │─────────────────> │ Role │────────────────────>│Use Cases │
└──────┘                    └──────┘                     └──────────┘
                                                               ↓ references
                                                         ┌────────────┐
                                                         │Intent Types│
                                                         └────────────┘
                                                         (presets only,
                                                          NOT permissioned)
```

### Implementation

#### 1. New Table: `role_use_case_assignments`

```sql
-- Links roles to use cases (users inherit access through role membership)
CREATE TABLE role_use_case_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_name VARCHAR(50) NOT NULL,  -- 'analyst', 'legal_counsel', 'hr_manager', etc.
    use_case_id UUID NOT NULL REFERENCES use_cases(id) ON DELETE CASCADE,

    -- Audit fields
    granted_by UUID REFERENCES users(id),
    granted_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,

    -- Additional metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    -- Constraints
    UNIQUE(role_name, use_case_id),
    CONSTRAINT ck_role_use_case_assignment_role CHECK (
        role_name IN ('admin', 'analyst', 'developer', 'corpus_admin', 'user', 'service')
    )
);

CREATE INDEX idx_role_use_case_assignments_role ON role_use_case_assignments(role_name, is_active);
CREATE INDEX idx_role_use_case_assignments_use_case ON role_use_case_assignments(use_case_id, is_active);

COMMENT ON TABLE role_use_case_assignments IS
    'Assigns use cases to roles. Users inherit use case access through role memberships.';
COMMENT ON COLUMN role_use_case_assignments.role_name IS
    'System role from user_roles table. Users with this role can execute this use case.';
COMMENT ON COLUMN role_use_case_assignments.is_active IS
    'Can be used to temporarily revoke access without deletion.';
```

#### 2. Access Control Logic

**Modified Use Case Access Check:**

```python
def user_can_access_use_case(user_id: UUID, use_case_id: UUID, db: Session) -> bool:
    """
    Check if user has access to use case through:
    1. Direct user assignment (user_use_case_assignments)
    2. Role-based assignment (role_use_case_assignments)
    3. Admin override (admin role always has access)
    """
    # Admin override
    user = db.query(User).filter(User.id == user_id).first()
    if user.role == "admin":
        return True

    # Direct user assignment
    direct_assignment = db.query(UserUseCaseAssignment).filter(
        UserUseCaseAssignment.user_id == user_id,
        UserUseCaseAssignment.use_case_id == use_case_id,
        UserUseCaseAssignment.status == 'active'
    ).first()
    if direct_assignment:
        return True

    # Role-based assignment (NEW)
    user_roles = db.query(UserRole.role).filter(
        UserRole.user_id == user_id
    ).all()

    for role_row in user_roles:
        role_assignment = db.query(RoleUseCaseAssignment).filter(
            RoleUseCaseAssignment.role_name == role_row.role,
            RoleUseCaseAssignment.use_case_id == use_case_id,
            RoleUseCaseAssignment.is_active == True
        ).first()
        if role_assignment:
            return True

    return False
```

#### 3. Remove `role_intent_permissions`

The `role_intent_permissions` table should be **removed entirely**:

- **DROP TABLE** in migration 026 (same migration that adds `role_use_case_assignments`)
- **Remove from SQLAlchemy models** (if present)
- **Clean up any references** in application code

**Rationale:**

- Intent Types are configuration presets, not permission boundaries
- Pre-v1 release - no backward compatibility needed
- Clean architecture - remove incorrect implementation completely

#### 4. Keep `user_use_case_assignments` for Overrides

The existing `user_use_case_assignments` table remains for:

- **Individual exceptions** - Grant/revoke access to specific users
- **Temporary assignments** - Time-limited access with `expires_at`

- **Use case-specific roles** - Users may have different roles within different use cases

**Access Resolution Priority:**

1. Admin role → Full access (bypass checks)
2. Direct user assignment (`user_use_case_assignments`) → Explicit grant/deny
3. Role-based assignment (`role_use_case_assignments`) → Inherited from role
4. Default → No access

---

## Consequences

### Positive

✅ **Correct architectural layering**

- Intent Types are presets only (no permissions)
- Use Cases are the permission boundary
- Roles grant use case access

✅ **Scalable role management**

- Assign 10 use cases to "analyst" role → All analysts get access
- No need to individually assign each user to each use case

✅ **Flexible access control**

- Role-based (standard)
- Individual user overrides (exceptions)
- Time-limited assignments (expires_at)

✅ **Clear semantics**

- "analyst role can use Threat Intel Query use case"
- NOT "analyst role can use QUERY intent type" (meaningless)

### Negative

❌ **Migration required**

- Remove `role_intent_permissions` table
- Add new table `role_use_case_assignments`
- Update access control logic in backend
- Update admin UI for role management

Note: Since this is pre-v1, removal is clean (no production deployments to migrate)

❌ **Additional complexity**

- Access checks now evaluate both direct and role-based assignments
- Need clear UI to show "why does this user have access?" (direct vs inherited)

### Neutral

🔄 **v1 cleanup benefit**

- `user_use_case_assignments` unchanged (direct assignments still work)
- `role_intent_permissions` removed completely (clean architecture)
- Admin role behavior unchanged (always full access)
- No backward compatibility concerns (pre-v1 release)

---

## Implementation Plan

### Phase 1: Database Schema (1-2 hours)

1. Create migration `026_role_use_case_assignments.sql`

2. **DROP TABLE `role_intent_permissions`** (incorrect architecture)
3. Add `role_use_case_assignments` table, indexes, comments
4. Seed initial assignments for existing use cases

### Phase 2: Backend Logic (3-4 hours)

1. Create SQLAlchemy model `RoleUseCaseAssignment`
2. Update `user_can_access_use_case()` logic

3. Add RLS policies for new table
4. Update `/api/use-cases/available` endpoint
5. Add tests (unit + integration)

### Phase 3: Admin API (2-3 hours)

1. CRUD endpoints for role-use-case assignments

   - `POST /api/admin/roles/{role_name}/use-cases` - Assign use case to role
   - `DELETE /api/admin/roles/{role_name}/use-cases/{use_case_id}` - Revoke
   - `GET /api/admin/roles/{role_name}/use-cases` - List role's use cases
   - `GET /api/admin/use-cases/{use_case_id}/roles` - List roles with access
2. Add permission checks (admin-only)

### Phase 4: Documentation (1-2 hours)

1. Update ERD.md with correct relationships
2. Update RLS_POLICIES.md
3. Update SCHEMA.md
4. Add migration notes
5. Update ADR-016 with clarification

### Phase 5: Frontend (Future - Phase 5)

1. Role management UI (assign use cases to roles)
2. Use case permissions UI (show roles with access)
3. User detail view (show inherited vs direct access)

**Total Effort:** 7-11 hours (backend + DB), Frontend deferred to Phase 5

---

## Alternative Considered

### Option B: Deprecate Instead of Remove `role_intent_permissions`

**Not chosen** because:

- Pre-v1 release - no production deployments to maintain
- Cleaner to remove incorrect architecture completely
- No reason to carry deprecated tables in v1 release

### Option C: Keep Current System

**Not chosen** because:

- Architecturally incorrect (permissions at wrong layer)
- Does not scale (must assign each user individually)
- Confusing semantics (what does "analyst can use QUERY intent" mean?)

### Option D: Remove `user_use_case_assignments` Entirely

**Not chosen** because:

- Loses ability for individual exceptions
- Cannot handle temporary access grants
- Less flexible for edge cases

---

## References

- **ADR-020:** Use Case Publisher Role (role hierarchy)
- **ADR-037:** UUID Primary Keys (applies to new table)
- **ERD.md:** Entity relationships (needs update)
- **SCHEMA.md:** Database schema documentation (needs update)

---

## Decision Record

**Proposed By:** Architecture Team
**Date:** 2025-10-24
**Accepted By:** Product Owner
**Status:** ACCEPTED

**Implementation:**

- Task Spec: P4-TASK-14 (Role-Based Use Case Permissions)
- Target Phase: Phase 4 or Phase 5 (TBD)
- Estimated Effort: 7-11 hours (backend + database)
