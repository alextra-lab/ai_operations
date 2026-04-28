# RBAC Architecture Analysis - Complete System Review

**Date:** 2025-12-10
**Analyst:** Claude
**Purpose:** Validate ADR-060 RBAC architecture for precision and avoid complexity mess
**Status:** 🔴 CRITICAL ISSUES FOUND

---

## Executive Summary

**Finding:** The RBAC architecture has **fundamental inconsistencies** between:

1. ADR-060 (design specification)
2. Backend implementation (rbac_v2.py, use_case_management.py)
3. TokenPayload model (still uses single-role system)

**Critical Issues:**

- ❌ TokenPayload.has_role() expects single role, but ADR-060 requires multi-role
- ❌ No clear permission matrix for use case lifecycle transitions
- ❌ Missing `use_case_publisher` role implementation in transition logic
- ❌ Conflation of `use_case_admin` and `use_case_publisher` responsibilities

---

## Part 1: System Roles Inventory

### All Defined System Roles (Tier 1)

| # | Role | Defined In | Purpose |
|---|------|------------|---------|
| 1 | `admin` | models.py, ADR-060, frontend | Full system access (superuser) |
| 2 | `corpus_admin` | models.py, ADR-060, frontend | Document/collection management |
| 3 | `developer` | models.py, ADR-060, frontend | Use case development (team-scoped) |
| 4 | `use_case_admin` | models.py, ADR-060, frontend | **Technical super-user** for use cases |
| 5 | `use_case_publisher` | models.py, ADR-020, frontend | **Governance** - approve/publish use cases |
| 6 | `tools_admin` | models.py, ADR-060, frontend | Tool/MCP management |
| 7 | `role_admin` | models.py, ADR-060, frontend | Role management |
| 8 | `conversations_privileged` | models.py, ADR-060, frontend | Privileged conversation access |
| 9 | `user` | models.py, ADR-060, frontend | Base authenticated user |
| 10 | `service` | models.py, ADR-060, frontend | Service-to-service authentication |

**Total:** 10 system roles

---

## Part 2: Use Case Lifecycle Permission Matrix

### Lifecycle States

```
draft → review → published → archived
         ↓
       draft (rejection)
```

### Complete Permission Matrix

| Action | admin | use_case_admin | use_case_publisher | developer | corpus_admin | Other |
|--------|-------|----------------|-------------------|-----------|--------------|-------|
| **Create Use Case** (draft) | ✅ Yes | ✅ Yes | ❌ No | ✅ Yes | ❌ No | ❌ No |
| **View Own Drafts** | ✅ Yes | ✅ Yes | ❌ No | ✅ Yes | ❌ No | ❌ No |
| **View Team Drafts** | ✅ Yes (all) | ✅ Yes (all) | ❌ No | ✅ Yes (own team) | ❌ No | ❌ No |
| **Edit Own Drafts** | ✅ Yes | ✅ Yes | ❌ No | ✅ Yes | ❌ No | ❌ No |
| **Edit Team Member Drafts** | ✅ Yes | ✅ Yes | ❌ No | ❌ No | ❌ No | ❌ No |
| **Submit for Review** (draft→review) | ✅ Yes | ✅ Yes | ❌ No | ✅ Yes | ❌ No | ❌ No |
| **View In Review** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes (own team) | ❌ No | ❌ No |
| **Publish** (review→published) | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No | ❌ No | ❌ No |
| **Reject** (review→draft) | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No | ❌ No | ❌ No |
| **View Published** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | Via grouping roles |
| **Edit Published** | ❌ No (immutable) | ❌ No (immutable) | ❌ No (immutable) | ❌ No (immutable) | ❌ No (immutable) | ❌ No (immutable) |
| **Clone Published** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No | ❌ No |
| **Archive** (published→archived) | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No | ❌ No | ❌ No |
| **Execute Use Case** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | Via grouping roles |

### Permission Rationale

#### Who Can Publish Use Cases?

**Answer:** `admin`, `use_case_admin`, `use_case_publisher`

**Rationale:**

- **admin**: Full system access (override capability)
- **use_case_admin**: Technical super-user - can bypass governance for emergency fixes
- **use_case_publisher**: PRIMARY governance role - this is their main responsibility

**NOT:** `developer`, `corpus_admin`, or others

#### Who Can Submit for Review?

**Answer:** `admin`, `use_case_admin`, `developer`

**Rationale:**

- **developer**: Creates use cases, submits when ready
- **use_case_admin**: Can submit any use case (super-user)
- **admin**: Can do anything

**NOT:** `use_case_publisher` (they review, not create)

---

## Part 3: Role Hierarchy Analysis

### Question: Is There a Role Hierarchy?

**Answer:** ❌ **NO - There is NO inheritance hierarchy**

### Current Model: **Flat Permissions with Composition**

```
System Architecture:
┌─────────────────────────────────────────────────────────┐
│ User Account                                            │
│                                                         │
│  Roles: ['developer', 'team:csirt', 'threat_hunting']  │
│         └─ Multiple flat roles, no inheritance          │
│                                                         │
│  Permission Check:                                      │
│    IF 'admin' in roles → ALLOW ALL                      │
│    ELSE IF 'use_case_admin' in roles → ALLOW (context) │
│    ELSE IF 'developer' in roles → ALLOW (limited)      │
│    ELSE → CHECK grouping roles                          │
└─────────────────────────────────────────────────────────┘
```

### Why NO Hierarchy?

**Reason 1: Roles Grant Different Things**

| Role Type | Grants |
|-----------|--------|
| System Roles | **Capabilities** (what you can DO) |
| Grouping Roles | **Resources** (what you can ACCESS) |
| Team Roles | **Visibility Scope** (what you can SEE) |

**These are orthogonal concerns - NOT hierarchical!**

**Reason 2: Privilege Levels Don't Nest**

```
❌ WRONG (Hierarchical thinking):
   admin > use_case_admin > developer > user

✅ CORRECT (Capability-based):
   admin → Grants: system configuration + all capabilities
   use_case_admin → Grants: use case super-user (all teams)
   developer → Grants: use case creation (team-scoped)

   These are DIFFERENT capabilities, not escalating privileges
```

**Example:**

- `developer` with `team:csirt` can create use cases for CSIRT team
- `use_case_publisher` CANNOT create use cases (different capability)
- `use_case_publisher` CAN publish use cases (developer cannot)

**Conclusion:** Roles are **capability grants**, not privilege levels.

---

## Part 4: Implementation Gaps Analysis

### Gap 1: TokenPayload Still Uses Single Role

**Location:** `src/shared/auth/models.py:178-188`

```python
class TokenPayload(BaseModel):
    user_id: str
    username: str
    role: str  # ❌ SINGLE ROLE - should be roles: list[str]

    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN  # ❌ Won't work with multi-role

    def has_role(self, required_roles: list[str]) -> bool:
        return self.role in required_roles  # ❌ Checks single role
```

**Problem:** ADR-060 requires multi-role support, but TokenPayload doesn't support it.

**Impact:**

- Frontend sends multiple roles in JWT
- Backend can't parse them correctly
- Role checks will fail

**Fix Required:**

```python
class TokenPayload(BaseModel):
    user_id: str
    username: str
    roles: list[str]  # ✅ MULTIPLE ROLES

    def is_admin(self) -> bool:
        return UserRole.ADMIN in self.roles

    def has_any_role(self, required_roles: list[str]) -> bool:
        return any(role in self.roles for role in required_roles)

    def has_all_roles(self, required_roles: list[str]) -> bool:
        return all(role in self.roles for role in required_roles)
```

### Gap 2: Missing use_case_publisher in Transition Logic

**Location:** `src/orchestrator/app/routers/use_case_management.py:690-792`

**Current Implementation:**

```python
@router.post("/{use_case_id}/transition")
async def transition_use_case_state(...):
    """
    Requires admin for review→published.  # ❌ INCOMPLETE
    """

    # Only checks for admin
    if target_state == "published" and not await has_role(user_id, "admin", db):
        raise HTTPException(...)  # ❌ Should also allow use_case_publisher
```

**Missing Logic:**

```python
# Should be:
if target_state == "published":
    allowed_roles = ["admin", "use_case_admin", "use_case_publisher"]
    if not await has_any_role(user_id, allowed_roles, db):
        raise HTTPException(
            status_code=403,
            detail=f"Requires one of: {allowed_roles}"
        )

if target_state == "review":
    allowed_roles = ["admin", "use_case_admin", "developer"]
    # Check if user owns the use case OR has admin role
    if use_case.created_by_user_id != user_id:
        if not await has_any_role(user_id, ["admin", "use_case_admin"], db):
            raise HTTPException(
                status_code=403,
                detail="Can only submit own use cases for review"
            )
```

### Gap 3: No can_publish_use_case() Function

**Location:** `src/orchestrator/app/services/rbac_v2.py` (missing)

**What's There:**

- ✅ `get_accessible_use_cases()` - visibility check
- ✅ `can_edit_use_case()` - edit permission check
- ❌ `can_publish_use_case()` - **MISSING**
- ❌ `can_transition_state()` - **MISSING**

**Needed:**

```python
async def can_transition_state(
    user_id: UUID,
    use_case: UseCase,
    target_state: str,
    db: AsyncSession
) -> bool:
    """Check if user can transition use case to target state."""
    user_roles = await get_user_roles(user_id, db)
    current_state = use_case.lifecycle_state

    # draft → review: creator OR admin/use_case_admin
    if current_state == "draft" and target_state == "review":
        if use_case.created_by_user_id == user_id:
            return True
        return any(r in user_roles for r in ["admin", "use_case_admin"])

    # review → published: admin, use_case_admin, or use_case_publisher
    if current_state == "review" and target_state == "published":
        return any(r in user_roles for r in ["admin", "use_case_admin", "use_case_publisher"])

    # review → draft (rejection): admin, use_case_admin, or use_case_publisher
    if current_state == "review" and target_state == "draft":
        return any(r in user_roles for r in ["admin", "use_case_admin", "use_case_publisher"])

    # published → archived: admin, use_case_admin, or use_case_publisher
    if current_state == "published" and target_state == "archived":
        return any(r in user_roles for r in ["admin", "use_case_admin", "use_case_publisher"])

    return False
```

### Gap 4: ADR-060 Doesn't Define use_case_publisher

**Location:** `docs/development/adrs/ADR-060-Corrected-RBAC-Architecture.md:177-186`

**Current Table:**

```markdown
| Role | Code | Grants |
|------|------|--------|
| Admin | `admin` | Full system access |
| Use Case Admin | `use_case_admin` | Develop use cases (SUPER USER) |
| Developer | `developer` | Create/edit use cases |
```

**Missing:** `use_case_publisher` row!

**Should Be:**

```markdown
| Role | Code | Grants | Can Publish |
|------|------|--------|-------------|
| Admin | `admin` | Full system access | Yes |
| Use Case Admin | `use_case_admin` | Technical super-user | Yes (emergency) |
| Use Case Publisher | `use_case_publisher` | Governance - approve/publish | Yes (primary) |
| Developer | `developer` | Create/edit use cases | No |
```

---

## Part 5: Role Distinction Clarity

### The Confusion: use_case_admin vs use_case_publisher

**Problem:** These roles sound similar but serve DIFFERENT purposes.

### Clear Distinction

| Aspect | use_case_admin | use_case_publisher |
|--------|----------------|-------------------|
| **Purpose** | Technical super-user | Governance officer |
| **Primary User** | Senior developers, platform engineers | SOC managers, security leads, compliance |
| **Can Create Use Cases** | ✅ Yes | ❌ No |
| **Can Edit Drafts** | ✅ Yes (any team) | ❌ No |
| **Can View All Team Drafts** | ✅ Yes | ❌ No (only submitted for review) |
| **Can Publish Use Cases** | ✅ Yes (emergency override) | ✅ Yes (primary responsibility) |
| **Can Bypass Team Boundaries** | ✅ Yes | ❌ No |
| **Typical Scenario** | "Debug production issue with use case config" | "Approve use case meets security standards before deployment" |
| **Access to System Admin** | ❌ No | ❌ No |
| **Technical vs Governance** | **Technical** | **Governance** |

### Real-World Example

**Scenario:** Use case needs emergency fix in production

```
use_case_admin (Grace):
1. Sees ALL use cases (including all team drafts)
2. Can edit ANY use case config (bypass team boundaries)
3. Can publish immediately (technical override)
4. Used for: Emergency fixes, debugging, platform maintenance

use_case_publisher (Emma):
1. Sees ONLY use cases submitted for review
2. CANNOT edit use case configs (read-only reviewer)
3. Can approve/reject based on governance criteria
4. Used for: Quality gates, compliance review, organizational standards
```

**Key Insight:** These are **complementary roles**, not competing roles.

---

## Part 6: Overlapping Permissions Check

### Analysis Method

For each action, check which roles can perform it:

| Action | Roles That Can Do It | Overlap Type |
|--------|---------------------|--------------|
| Create use case | `admin`, `use_case_admin`, `developer` | ✅ Intentional (admin=superuser) |
| Edit own draft | `admin`, `use_case_admin`, `developer` | ✅ Intentional |
| Edit any draft | `admin`, `use_case_admin` | ✅ Intentional (super-user capability) |
| Submit for review | `admin`, `use_case_admin`, `developer` | ✅ Intentional |
| Publish use case | `admin`, `use_case_admin`, `use_case_publisher` | ✅ Intentional (different contexts) |
| View all team drafts | `admin`, `use_case_admin` | ✅ Intentional (admin=all, use_case_admin=technical) |
| Manage roles | `admin`, `role_admin` | ✅ Intentional (delegation) |
| Manage documents | `admin`, `corpus_admin` | ✅ Intentional (delegation) |

### Conclusion: ✅ No Problematic Overlaps

**All overlaps are intentional:**

- `admin` is superuser - should overlap with everything
- `use_case_admin` and `use_case_publisher` both publish (different contexts)
- Delegation roles (`role_admin`, `corpus_admin`) overlap with `admin` by design

---

## Part 7: Recommendations

### 1. Fix TokenPayload for Multi-Role Support (HIGH PRIORITY)

**File:** `src/shared/auth/models.py`

```python
class TokenPayload(BaseModel):
    user_id: str
    username: str
    roles: list[str]  # Changed from role: str
    scopes: list[str]
    iat: int
    exp: int
    iss: str
    token_type: str

    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return UserRole.ADMIN in self.roles

    def has_any_role(self, required_roles: list[str]) -> bool:
        """Check if user has any of the required roles."""
        return any(role in self.roles for role in required_roles)

    def has_all_roles(self, required_roles: list[str]) -> bool:
        """Check if user has all of the required roles."""
        return all(role in self.roles for role in required_roles)
```

### 2. Add can_transition_state() to RBAC V2 (HIGH PRIORITY)

**File:** `src/orchestrator/app/services/rbac_v2.py`

Add the function from Gap 3 above.

### 3. Update Transition Endpoint (HIGH PRIORITY)

**File:** `src/orchestrator/app/routers/use_case_management.py`

```python
@router.post("/{use_case_id}/transition")
async def transition_use_case_state(...):
    # Use can_transition_state() instead of hardcoded checks
    if not await can_transition_state(user_id, use_case, target_state, db):
        raise HTTPException(
            status_code=403,
            detail=f"Not authorized to transition {current_state} → {target_state}"
        )
```

### 4. Complete ADR-060 Documentation (MEDIUM PRIORITY)

**File:** `docs/development/adrs/ADR-060-Corrected-RBAC-Architecture.md`

Add:

- `use_case_publisher` to system roles table
- Complete use case lifecycle permission matrix
- Clarify use_case_admin vs use_case_publisher distinction
- Add section: "Use Case Lifecycle State Transitions"

### 5. Update Frontend Role Guards (LOW PRIORITY)

**File:** `src/frontend-angular/src/app/core/auth/*`

Ensure guards handle multiple roles correctly.

---

## Part 8: Final Architecture Validation

### ✅ Is the RBAC Architecture Clean?

**YES** - with fixes applied:

1. **✅ Clear Separation of Concerns**
   - System roles = capabilities
   - Grouping roles = resource access
   - Team roles = visibility scope

2. **✅ No Hierarchy (Correct)**
   - Flat permission model
   - Composition over inheritance
   - Role checks are explicit, not inherited

3. **✅ No Problematic Overlaps**
   - All overlaps are intentional
   - `admin` as superuser makes sense
   - Delegation roles work correctly

4. **✅ Default-Deny Model**
   - No roles = no access
   - Explicit grants required
   - Secure by default

### ❌ What Needs Fixing?

1. **TokenPayload multi-role support** (CRITICAL)
2. **Add can_transition_state() function** (HIGH)
3. **Update transition endpoint logic** (HIGH)
4. **Complete ADR-060 documentation** (MEDIUM)

### Summary Assessment

**Architecture Design:** ✅ **SOUND** - Well thought out, clear separation of concerns

**Implementation:** ⚠️ **INCOMPLETE** - Has gaps but fixable

**Documentation:** ⚠️ **INCOMPLETE** - Missing use_case_publisher details

**Recommendation:** **Fix the 4 gaps above, then ADR-060 is SOLID.**

---

## Appendix: Quick Reference Tables

### System Roles Quick Reference

| Role | Create UC | Edit Any | Publish | Manage System |
|------|-----------|----------|---------|---------------|
| admin | ✅ | ✅ | ✅ | ✅ |
| use_case_admin | ✅ | ✅ | ✅ | ❌ |
| use_case_publisher | ❌ | ❌ | ✅ | ❌ |
| developer | ✅ | ❌ (own only) | ❌ | ❌ |
| corpus_admin | ❌ | ❌ | ❌ | ❌ (docs only) |
| role_admin | ❌ | ❌ | ❌ | ❌ (roles only) |

### Lifecycle Transition Authority

| Transition | Who Can Do It |
|------------|---------------|
| draft → review | Creator, use_case_admin, admin |
| review → published | use_case_publisher, use_case_admin, admin |
| review → draft | use_case_publisher, use_case_admin, admin |
| published → archived | use_case_publisher, use_case_admin, admin |

---

**END OF ANALYSIS**
