# ADR-060: Corrected RBAC Architecture - Two-Tier System with Team-Based Development

**Status:** ACCEPTED
**Date:** 2025-12-08
**Authors:** Architecture Team
**Priority:** CRITICAL - Show Stopping Issue
**Related ADRs:** ADR-041 (Role-Based Use Case Permissions), ADR-020 (Use Case Publisher Role)

---

## Context

The current RBAC implementation has significant architectural inconsistencies that make the Role Management UI confusing and non-functional. Through detailed analysis, we've identified fundamental misalignment between the intended architecture and the implementation.

### Current Problems

#### 1. Architectural Confusion: Two Role Systems Conflated

The system currently has **two distinct role concepts** that are conflated:

**Layer 1: System Roles (Control UI/Feature Access)**

- **Purpose:** Controls which UI panels and admin features users can access
- **Storage:** `users.role` column (single value per user)
- **Examples:** `admin`, `corpus_admin`, `use_case_publisher`, `conversations_privileged`
- **Source:** `src/shared/auth/models.py`

**Layer 2: Use Case Grouping Roles (Control Resource Access)**

- **Purpose:** Controls which use case groups users can execute
- **Storage:** `user_roles` table (multiple per user)
- **Examples:** `threat_hunting`, `incident_response`, `compliance_monitoring`
- **Source:** `docs/admin/USER_ROLES_GUIDE.md`

#### 2. Frontend Shows Wrong Roles

The Role Management UI (`role-management.component.ts`) incorrectly hardcodes these as "System Roles":

```typescript
export const SYSTEM_ROLES: RoleInfo[] = [
  { role_name: 'admin', ... },        // ✅ Correct
  { role_name: 'analyst', ... },      // ❌ NOT a system role
  { role_name: 'developer', ... },    // ❌ NOT a system role
  { role_name: 'corpus_admin', ... }, // ✅ Correct
  { role_name: 'user', ... },         // ✅ Correct
  { role_name: 'service', ... },      // ✅ Correct
];
```

Problems:

- `analyst` and `developer` are **not** Layer 1 system roles
- Missing actual system roles: `use_case_publisher`, `conversations_privileged`
- UI purpose is confused (manages use case assignments but displays as "system roles")

#### 3. Missing Actual System Roles

According to `src/shared/auth/models.py`, the **actual** system roles are:

```python
class UserRole(str, Enum):
    ADMIN = "admin"
    CORPUS_ADMIN = "corpus_admin"
    SERVICE = "service"
    USER = "user"
    USE_CASE_PUBLISHER = "use_case_publisher"          # ❌ Missing from UI
    CONVERSATIONS_PRIVILEGED = "conversations_privileged"  # ❌ Missing from UI
    DEVELOPER = "developer"                             # ❌ Missing from UI and ADR
```

#### 4. Access Control Model Unclear

Current documentation doesn't clearly specify:

- Base users with no roles: Can they see anything?
- Resource visibility: Default-allow or default-deny?
- Use case grouping roles: Who creates them? How are they managed?
- Team boundaries: Can different dev teams see each other's work?

#### 5. Real-World Requirements Not Met

**Business Requirement:** Multi-team deployment

Example: Organization has:

- **CSIRT Security Team:** Develops incident response use cases
- **SOC Governance Team:** Develops compliance and reporting use cases
- **Requirement:** Teams should NOT see each other's draft use cases
- **Current State:** No team isolation mechanism exists

---

## Decision

We will implement a **corrected two-tier RBAC architecture** with **team-based use case development** and **default-deny resource access**.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│ User Account                                                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  TIER 1: SYSTEM ROLES (Capability Grants)                           │
│  ═══════════════════════════════════════════                        │
│  Storage: user_roles table (multiple per user)                      │
│  Purpose: Grant capabilities (what users CAN DO in system)          │
│                                                                      │
│  Roles: admin, corpus_admin, use_case_admin, developer,            │
│         tools_admin, conversations, role_admin                       │
│                                                                      │
│  admin           → Full system access (superuser)                   │
│  corpus_admin    → Manage documents/collections (see ALL docs)      │
│  use_case_admin  → Develop use cases (SUPER USER - see ALL)        │
│  developer       → Create/edit use cases (TEAM-SCOPED visibility)   │
│  tools_admin     → Manage tools/MCPs                                │
│  conversations   → Access conversation interface                     │
│  role_admin      → Create roles, assign users to roles              │
│                                                                      │
│  ──────────────────────────────────────────────────────────────────│
│                                                                      │
│  TIER 2: USE CASE GROUPING ROLES (Resource Access Grants)           │
│  ══════════════════════════════════════════════════                 │
│  Storage: user_roles table (multiple per user)                      │
│  Purpose: Grant access to specific use case groups                  │
│                                                                      │
│  Examples: threat_hunting, incident_response,                       │
│            compliance_monitoring, threat_intelligence               │
│  (Dynamically created by admins to group use cases)                 │
│                                                                      │
│  Mechanism:                                                          │
│    Role → [role_use_case_assignments] → Use Cases                   │
│    Role → [role_collection_assignments] → Document Collections      │
│                                                                      │
│  ──────────────────────────────────────────────────────────────────│
│                                                                      │
│  TIER 3: DEVELOPER TEAMS (Isolation Boundaries)                     │
│  ═══════════════════════════════════════════                        │
│  Storage: user_roles table with 'team:' prefix                      │
│  Purpose: Isolate draft use cases between development teams         │
│                                                                      │
│  Examples: team:csirt_security, team:soc_governance                 │
│                                                                      │
│  Visibility Rules:                                                   │
│    - Team members see only their team's draft use cases             │
│    - Everyone sees all published use cases                          │
│    - Admin sees all teams' drafts                                   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Key Principles

#### 1. Default-Deny Access Model

```
Base User (Authenticated, No Roles):
├─ Can log in ✅
├─ Can see dashboard (empty/minimal) ✅
├─ Cannot see ANY use cases ❌ (until role grants access)
├─ Cannot see ANY documents ❌ (until role grants access)
└─ Sees empty application with "Request Access" messaging
```

**Access is granted through roles:**

- System roles grant **capabilities** (manage documents, develop use cases)
- Grouping roles grant **resource access** (specific use cases and collections)
- Users see ONLY resources their roles grant access to

#### 2. Two-Tier Role System

**Tier 1: System/Capability Roles (Predefined, Immutable)**

These grant **capabilities** - what you can DO:

| Role | Code | Grants | Visibility | Can Publish |
|------|------|--------|------------|-------------|
| Admin | `admin` | Full system access, configuration | ALL resources | Yes |
| Corpus Admin | `corpus_admin` | Manage documents/collections | ALL documents | No |
| Use Case Admin | `use_case_admin` | **Technical super-user** - develop use cases, bypass teams | ALL use cases (all teams) | Yes (emergency) |
| Use Case Publisher | `use_case_publisher` | **Governance** - approve and publish use cases | Submitted use cases (review state) | Yes (primary) |
| Developer | `developer` | Create/edit use cases (TEAM-SCOPED) | Own team's drafts only | No (submit only) |
| Tools Admin | `tools_admin` | Manage tools/MCPs | ALL tools | No |
| Conversations | `conversations` | Access conversation interface | Assigned use cases | No |
| Role Admin | `role_admin` | Create roles, assign users | ALL roles | No |

**Key Points:**

- **Admin and management roles** (`admin`, `corpus_admin`, `use_case_admin`, `tools_admin`, `role_admin`) grant full visibility for oversight purposes
- **Use Case Admin** is a **technical** role - can edit configs, bypass team boundaries (for platform maintenance)
- **Use Case Publisher** is a **governance** role - reviews and approves for organizational standards (read-only)
- **Developer role** is team-scoped - sees only their team's drafts (requires team membership)
- **Conversations role** uses Tier 2 grouping role assignments for resource access

**Tier 2: Use Case Grouping Roles (Dynamic, Admin-Created)**

These grant **resource access** - WHAT you can see/execute:

```typescript
// Examples - created by admins as needed
const useCaseGroupingRoles = [
  'threat_hunting',           // Can execute threat hunting use cases
  'incident_response',        // Can execute IR use cases
  'compliance_review',        // Can execute compliance use cases
  'malware_analysis',         // Can execute malware analysis use cases
  'threat_intelligence',      // Can execute threat intel use cases
  'phishing_investigation',   // Can execute phishing investigation use cases
  'vulnerability_mgmt',       // Can execute vuln management use cases
  'soc_tier1',               // Can execute tier 1 triage use cases
  'soc_tier2',               // Can execute tier 2 investigation use cases
  'soc_tier3',               // Can execute tier 3 advanced use cases
  'legal_review',            // Can execute legal compliance use cases
  // ... unlimited custom roles
];
```

**Key Point:** These roles get **assigned use cases and collections**. Users inherit access through role membership.

#### 2.1. Creating New Grouping Roles

Grouping roles are created dynamically by administrators. The workflow is:

**Step 1: Create the Grouping Role**

Use the API endpoint or UI to register a new grouping role:

```bash
# API: POST /api/v1/admin/grouping-roles
curl -X POST "http://localhost:8006/api/v1/admin/grouping-roles" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role_name": "threat_hunting"}'
```

**Role Name Requirements:**

- Must start with lowercase letter
- Can contain: lowercase letters, digits, underscore, hyphen
- Length: 2-50 characters
- Pattern: `^[a-z][a-z0-9_-]{1,49}$`
- Cannot be a system role name (admin, developer, user, etc.)
- Cannot start with `team:` prefix

**Authorization:** Admin or `role_admin` role required

**Step 2: Assign Use Cases to the Role**

Once the role exists, assign use cases to grant execution access:

```bash
# API: POST /admin/roles/{role_name}/use-cases
curl -X POST "http://localhost:8006/admin/roles/threat_hunting/use-cases" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "use_case_id": "289cba6d-a0c5-401e-856b-c7b19e89ac32"
  }'
```

**Step 3: Assign Users to the Role**

Assign users to the grouping role so they inherit access to assigned use cases:

```bash
# API: POST /admin/users/{user_id}/roles
curl -X POST "http://localhost:8006/admin/users/{user_id}/roles" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role_name": "threat_hunting"}'
```

**Complete Workflow Example:**

1. Admin creates grouping role: `threat_hunting`
2. Admin assigns 5 use cases to `threat_hunting` role
3. Admin assigns 3 users to `threat_hunting` role
4. Result: All 3 users can now execute all 5 assigned use cases

**Note:** System roles (Tier 1) should **NOT** have use cases assigned. Only grouping roles (Tier 2) should have use cases assigned for execution access.

#### 2.2. Use Case Lifecycle Permissions Matrix

The following matrix defines who can perform each action in the use case lifecycle:

| Action | admin | use_case_admin | use_case_publisher | developer | corpus_admin | grouping roles |
|--------|-------|----------------|-------------------|-----------|--------------|----------------|
| **Create Use Case** (draft) | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| **View Own Drafts** | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| **View Team Drafts** | ✅ (all) | ✅ (all) | ❌ | ✅ (own team) | ❌ | ❌ |
| **Edit Own Drafts** | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| **Edit Any Draft** | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Submit for Review** (draft→review) | ✅ | ✅ | ❌ | ✅ (own) | ❌ | ❌ |
| **View In Review** | ✅ | ✅ | ✅ | ✅ (own team) | ❌ | ❌ |
| **Publish** (review→published) | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Reject** (review→draft) | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| **View Published** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (assigned) |
| **Edit Published** | ❌ (immutable) | ❌ (immutable) | ❌ (immutable) | ❌ (immutable) | ❌ (immutable) | ❌ (immutable) |
| **Clone Published** | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| **Archive** (published→archived) | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Execute Use Case** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (assigned) |

**Key Insights:**

1. **Three Roles Can Publish:**
   - `admin` - Superuser override
   - `use_case_admin` - Technical emergency fixes
   - `use_case_publisher` - Primary governance approval

2. **Developers Submit, Don't Publish:**
   - Developers create and submit use cases
   - Cannot publish directly (governance gate)

3. **Published Use Cases Are Immutable:**
   - No one can edit published use cases
   - Must clone to create new draft version

4. **Team Isolation:**
   - Developers see only own team's drafts
   - `use_case_admin` sees all teams (super-user)

#### 2.3. State Transition Authority

Valid use case lifecycle state transitions:

```
draft → review → published → archived
         ↓
       draft (rejection)
```

**Who Can Perform Each Transition:**

| Transition | Required Role(s) | Notes |
|------------|-----------------|-------|
| **draft → review** | Creator, `use_case_admin`, `admin` | Developer submits own use case for review |
| **review → published** | `use_case_publisher`, `use_case_admin`, `admin` | Governance approval required |
| **review → draft** | `use_case_publisher`, `use_case_admin`, `admin` | Rejection - send back for fixes |
| **published → archived** | `use_case_publisher`, `use_case_admin`, `admin` | Retire use case |

**Implementation:**

```python
# src/orchestrator/app/services/rbac_v2.py
async def can_transition_state(
    user_id: UUID,
    use_case: UseCase,
    target_state: str,
    db: AsyncSession
) -> bool:
    """Check if user can transition use case to target state."""
    user_roles = await get_user_roles(user_id, db)
    current_state = use_case.lifecycle_state

    # Admin can do anything
    if "admin" in user_roles:
        return True

    # draft → review: creator OR use_case_admin
    if current_state == "draft" and target_state == "review":
        if "use_case_admin" in user_roles:
            return True
        if use_case.created_by_user_id == user_id:
            return True
        return False

    # review → published: use_case_admin or use_case_publisher
    if current_state == "review" and target_state == "published":
        return any(
            role in user_roles
            for role in ["use_case_admin", "use_case_publisher"]
        )

    # review → draft (rejection): use_case_admin or use_case_publisher
    if current_state == "review" and target_state == "draft":
        return any(
            role in user_roles
            for role in ["use_case_admin", "use_case_publisher"]
        )

    # published → archived: use_case_admin or use_case_publisher
    if current_state == "published" and target_state == "archived":
        return any(
            role in user_roles
            for role in ["use_case_admin", "use_case_publisher"]
        )

    return False
```

#### 2.4. Use Case Admin vs Use Case Publisher: Critical Distinction

These two roles sound similar but serve **fundamentally different purposes**. Conflating them creates confusion.

**use_case_admin: Technical Super-User Role**

| Aspect | Details |
|--------|---------|
| **Purpose** | Technical super-user for platform maintenance and debugging |
| **Primary Users** | Senior developers, platform engineers, DevOps |
| **Can Create Use Cases** | ✅ Yes - can create use cases for any team |
| **Can Edit Drafts** | ✅ Yes - can edit ANY draft from ANY team |
| **Can View All Team Drafts** | ✅ Yes - sees ALL teams' drafts for debugging |
| **Can Publish Use Cases** | ✅ Yes - emergency override capability |
| **Can Bypass Team Boundaries** | ✅ Yes - no team restrictions |
| **Technical vs Governance** | **Technical** - focuses on system functionality |
| **Typical Scenario** | "Production use case is broken - need to fix config immediately" |

**use_case_publisher: Governance Role**

| Aspect | Details |
|--------|---------|
| **Purpose** | Governance officer for organizational standards and compliance |
| **Primary Users** | SOC managers, security leads, compliance officers |
| **Can Create Use Cases** | ❌ No - read-only reviewer |
| **Can Edit Drafts** | ❌ No - cannot modify configurations |
| **Can View All Team Drafts** | ❌ No - only sees use cases submitted for review |
| **Can Publish Use Cases** | ✅ Yes - primary governance approval responsibility |
| **Can Bypass Team Boundaries** | ❌ No - reviews submitted use cases only |
| **Technical vs Governance** | **Governance** - focuses on standards compliance |
| **Typical Scenario** | "Review use case to ensure it meets security policy before deployment" |

**Key Differences:**

1. **Access Scope:**
   - `use_case_admin`: Sees ALL use cases in ALL states from ALL teams
   - `use_case_publisher`: Sees ONLY use cases in "review" state (submitted)

2. **Edit Capability:**
   - `use_case_admin`: Can edit ANY use case config (technical changes)
   - `use_case_publisher`: Read-only (approval/rejection only)

3. **Primary Function:**
   - `use_case_admin`: Fix broken use cases, debug issues, maintain platform
   - `use_case_publisher`: Enforce organizational standards, compliance gates

4. **When They Publish:**
   - `use_case_admin`: Emergency situations, technical overrides
   - `use_case_publisher`: Normal workflow, governance approval

**Real-World Example:**

```
Scenario: New threat hunting use case needs deployment

Developer (Alice):
1. Creates draft use case for threat hunting
2. Tests configuration
3. Submits for review (draft → review)

Use Case Publisher (Security Manager Bob):
1. Reviews submitted use case
2. Checks: Does it meet security standards?
3. Checks: Does it access authorized data sources?
4. Checks: Is detection logic appropriate?
5. Approves: Publishes use case (review → published)

Use Case Admin (Platform Engineer Grace):
- NOT involved in normal workflow
- ONLY involved if: Use case breaks in production
- Can: Directly edit configs, bypass review process if needed
```

**Why Both Roles Exist:**

- **Separation of Concerns:** Technical maintenance ≠ Governance approval
- **Security:** Governance officers don't need technical super-user access
- **Scalability:** Allows delegation without over-privileging
- **Compliance:** Segregation of duties for audit requirements

#### 3. Team-Based Use Case Development

**Problem:** Different development teams (CSIRT vs SOC Governance) should not see each other's draft use cases.

**Solution:** Developer teams with draft use case isolation.

```
Organization
├─ Team: "team:csirt_security"
│   ├─ Members: Alice (developer), Bob (developer)
│   ├─ Draft Use Cases: [UC-1, UC-2, UC-5] (only team members see)
│   └─ Published Use Cases: [UC-10, UC-11] (everyone sees)
│
├─ Team: "team:soc_governance"
│   ├─ Members: Dave (developer), Emma (developer)
│   ├─ Draft Use Cases: [UC-3, UC-4] (only team members see)
│   └─ Published Use Cases: [UC-12, UC-13] (everyone sees)
│
├─ Use Case Admin: Grace (use_case_admin)
│   └─ Can see: ALL teams' drafts + ALL published use cases
│
└─ Admin: Frank (admin)
    └─ Can see: ALL teams' drafts + ALL published use cases
```

**Visibility Rules:**

| User | Role | Can See Drafts From | Can See Published | Can Edit |
|------|------|-------------------|-------------------|----------|
| Alice (CSIRT) | developer + team:csirt_security | Only CSIRT team drafts | All published UCs | Own drafts only |
| Dave (SOC Gov) | developer + team:soc_governance | Only SOC Gov team drafts | All published UCs | Own drafts only |
| Grace | use_case_admin | ALL drafts (all teams) | All published UCs | ALL drafts |
| Frank | admin | ALL drafts (all teams) | All published UCs | ALL drafts |

---

## Database Schema Changes

### 1. Remove Single Role Column from Users Table

**Current (INCORRECT):**

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    username VARCHAR UNIQUE NOT NULL,
    role VARCHAR NOT NULL,  -- ❌ Single role per user
    ...
);
```

**Corrected:**

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    username VARCHAR UNIQUE NOT NULL,
    -- role column REMOVED
    hashed_password VARCHAR NOT NULL,
    email VARCHAR,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 2. Use user_roles Table for ALL Roles (Already Exists)

```sql
-- This table ALREADY EXISTS - we just use it correctly now
CREATE TABLE user_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role TEXT NOT NULL,  -- System role OR grouping role OR team
    granted_by UUID REFERENCES users(id),
    granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,  -- Optional expiration
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, role)
);

CREATE INDEX idx_user_roles_user_id ON user_roles(user_id);
CREATE INDEX idx_user_roles_role ON user_roles(role);

-- Examples of role values:
-- System roles: 'admin', 'corpus_admin', 'use_case_admin', 'tools_admin', 'conversations', 'role_admin'
-- Grouping roles: 'threat_hunting', 'incident_response', 'compliance_review', etc.
-- Team memberships: 'team:csirt_security', 'team:soc_governance', etc.
```

### 3. Add Team ID to Use Cases Table

```sql
ALTER TABLE use_cases
ADD COLUMN team_id VARCHAR(100);

-- Index for team-based filtering
CREATE INDEX idx_use_cases_team_lifecycle
ON use_cases(team_id, lifecycle_state);

-- Comment
COMMENT ON COLUMN use_cases.team_id IS
    'Developer team that owns this use case. Format: team:team_name. ' ||
    'Used to isolate draft use cases between teams. ' ||
    'NULL or team:default for unassigned use cases.';
```

### 4. Add Collection Assignments to Roles (NEW)

```sql
-- Grant document collection access to roles
CREATE TABLE role_collection_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_name VARCHAR(50) NOT NULL,  -- Any role (system or grouping)
    collection_id UUID NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    granted_by UUID REFERENCES users(id),
    granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(role_name, collection_id)
);

CREATE INDEX idx_role_collection_assignments_role
ON role_collection_assignments(role_name, is_active);

CREATE INDEX idx_role_collection_assignments_collection
ON role_collection_assignments(collection_id, is_active);

COMMENT ON TABLE role_collection_assignments IS
    'Assigns document collections to roles. Users inherit collection access through role memberships.';
```

### 5. Keep Existing Tables (No Changes)

These tables **already exist and are correct**:

```sql
-- ✅ Already correct - no changes needed
CREATE TABLE role_use_case_assignments (
    id UUID PRIMARY KEY,
    role_name VARCHAR(50) NOT NULL,
    use_case_id UUID NOT NULL REFERENCES use_cases(id) ON DELETE CASCADE,
    granted_by UUID REFERENCES users(id),
    granted_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    UNIQUE(role_name, use_case_id)
);

-- ✅ Already correct - no changes needed
CREATE TABLE user_use_case_assignments (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    use_case_id UUID NOT NULL REFERENCES use_cases(id) ON DELETE CASCADE,
    assigned_role VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    assigned_by_user_id UUID REFERENCES users(id),
    assigned_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    UNIQUE(user_id, use_case_id, assigned_role)
);
```

---

## Access Control Logic

### 1. Get User's Roles (All Types)

```python
async def get_user_roles(user_id: UUID, db: AsyncSession) -> list[str]:
    """
    Get all roles assigned to a user (system roles + grouping roles + teams).

    Returns: ['admin', 'threat_hunting', 'team:csirt_security']
    """
    result = await db.execute(
        select(UserRoleMembership.role)
        .where(UserRoleMembership.user_id == user_id)
    )
    return [row.role for row in result.all()]


async def get_user_system_roles(user_id: UUID, db: AsyncSession) -> list[str]:
    """
    Get only system/capability roles for a user.

    Returns: ['admin', 'developer', 'use_case_admin']
    """
    all_roles = await get_user_roles(user_id, db)
    system_roles = [
        'admin', 'corpus_admin', 'use_case_admin', 'developer',
        'tools_admin', 'conversations', 'role_admin'
    ]
    return [r for r in all_roles if r in system_roles]


async def get_user_grouping_roles(user_id: UUID, db: AsyncSession) -> list[str]:
    """
    Get only use case grouping roles for a user.

    Returns: ['threat_hunting', 'incident_response']
    """
    all_roles = await get_user_roles(user_id, db)
    system_roles = [
        'admin', 'corpus_admin', 'use_case_admin', 'developer',
        'tools_admin', 'conversations', 'role_admin'
    ]
    # Exclude system roles and team memberships
    return [
        r for r in all_roles
        if r not in system_roles and not r.startswith('team:')
    ]


async def get_user_teams(user_id: UUID, db: AsyncSession) -> list[str]:
    """
    Get team memberships for a user.

    Returns: ['team:csirt_security', 'team:soc_governance']
    """
    all_roles = await get_user_roles(user_id, db)
    return [r for r in all_roles if r.startswith('team:')]


async def has_any_role(
    user_id: UUID,
    required_roles: list[str],
    db: AsyncSession
) -> bool:
    """Check if user has any of the required roles."""
    user_roles = await get_user_roles(user_id, db)
    return any(role in user_roles for role in required_roles)
```

### 2. Use Case Access Control

```python
async def get_accessible_use_cases(
    user_id: UUID,
    db: AsyncSession,
    lifecycle_state: str | None = None
) -> list[UseCase]:
    """
    Get use cases accessible to user based on their roles and team memberships.

    Visibility rules:
    1. Admin: Sees ALL use cases (all states, all teams)
    2. use_case_admin: Sees ALL use cases (all states, all teams) - SUPER USER
    3. developer with team membership:
       - Sees ALL published use cases (any team)
       - Sees ONLY their team's draft/review use cases
    4. corpus_admin: Sees all published use cases (for reference)
    5. Grouping roles: See only published use cases assigned to those roles
    6. No roles: Sees NOTHING (empty list)
    """
    user_roles = await get_user_roles(user_id, db)
    user_teams = await get_user_teams(user_id, db)

    # Rule 1: Admin sees everything
    if 'admin' in user_roles:
        stmt = select(UseCase)
        if lifecycle_state:
            stmt = stmt.where(UseCase.lifecycle_state == lifecycle_state)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # Rule 2: use_case_admin sees everything (SUPER USER)
    if 'use_case_admin' in user_roles:
        stmt = select(UseCase)
        if lifecycle_state:
            stmt = stmt.where(UseCase.lifecycle_state == lifecycle_state)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # Rule 3: developer with team-based draft visibility
    if 'developer' in user_roles:
        # See all published use cases
        published_cte = (
            select(UseCase.id)
            .where(UseCase.lifecycle_state == 'published')
        ).cte('published_ids')

        # See draft/review use cases from own teams only
        if user_teams:
            team_draft_cte = (
                select(UseCase.id)
                .where(
                    UseCase.team_id.in_(user_teams),
                    UseCase.lifecycle_state.in_(['draft', 'review'])
                )
            ).cte('team_draft_ids')

            # Combine: published + team drafts
            combined_ids = select(published_cte.c.id).union(
                select(team_draft_cte.c.id)
            )
        else:
            # No team membership = only see published
            combined_ids = select(published_cte.c.id)

        stmt = select(UseCase).where(UseCase.id.in_(combined_ids))

        if lifecycle_state:
            stmt = stmt.where(UseCase.lifecycle_state == lifecycle_state)

        result = await db.execute(stmt)
        return list(result.scalars().all())

    # Rule 4: corpus_admin sees all published (for reference)
    if 'corpus_admin' in user_roles:
        stmt = select(UseCase)
        # Apply lifecycle_state filter: default to 'published' for corpus_admin
        if lifecycle_state:
            stmt = stmt.where(UseCase.lifecycle_state == lifecycle_state)
        else:
            # Default: corpus_admin sees published use cases for reference
            stmt = stmt.where(UseCase.lifecycle_state == 'published')
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # Rule 5: No system roles = check grouping role assignments
    grouping_roles = await get_user_grouping_roles(user_id, db)

    if not grouping_roles:
        # No roles = no access
        return []

    # Get use cases assigned to user's grouping roles
    # Grouping roles only see published use cases (unless explicitly filtered)
    stmt = (
        select(UseCase)
        .join(RoleUseCaseAssignment, UseCase.id == RoleUseCaseAssignment.use_case_id)
        .where(
            RoleUseCaseAssignment.role_name.in_(grouping_roles),
            RoleUseCaseAssignment.is_active == True,
            or_(
                RoleUseCaseAssignment.expires_at.is_(None),
                RoleUseCaseAssignment.expires_at > datetime.now(UTC)
            )
        )
        .distinct()
    )

    # Apply lifecycle_state filter: default to 'published' for grouping roles
    if lifecycle_state:
        stmt = stmt.where(UseCase.lifecycle_state == lifecycle_state)
    else:
        # Default: grouping roles only see published use cases
        stmt = stmt.where(UseCase.lifecycle_state == 'published')

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
    1. Admin: Can edit anything (any state)
    2. use_case_admin: Can edit anything (any state) - SUPER USER
    3. Non-draft use cases: Cannot edit (immutability - must clone)
    4. Draft creator: Can edit own drafts
    5. Team member: Can VIEW team drafts but cannot edit (only creator can edit)
    """
    user_roles = await get_user_roles(user_id, db)

    # Rule 1: Admin can edit anything
    if 'admin' in user_roles:
        return True

    # Rule 2: use_case_admin can edit anything (SUPER USER)
    if 'use_case_admin' in user_roles:
        return True

    # Rule 3: Can only edit drafts
    if use_case.lifecycle_state != 'draft':
        return False

    # Rule 4: Creator can edit own drafts
    if use_case.created_by_user_id == user_id:
        return True

    # Rule 5: Team members can view but not edit
    # (No collaborative editing - prevents conflicts)
    return False
```

### 3. Document Collection Access Control

```python
async def get_accessible_collections(
    user_id: UUID,
    db: AsyncSession
) -> list[Collection]:
    """
    Get document collections accessible to user.

    Visibility rules:
    1. Admin: Sees ALL collections
    2. corpus_admin: Sees ALL collections (for management)
    3. Grouping roles: See only collections assigned to those roles
    4. No roles: Sees NOTHING (empty list)
    """
    user_roles = await get_user_roles(user_id, db)

    # Rule 1: Admin sees all
    if 'admin' in user_roles:
        stmt = select(Collection).where(Collection.is_published == True)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # Rule 2: corpus_admin sees all
    if 'corpus_admin' in user_roles:
        stmt = select(Collection).where(Collection.is_published == True)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # Rule 3: Check grouping role assignments
    grouping_roles = await get_user_grouping_roles(user_id, db)

    if not grouping_roles:
        # No roles = no collections
        return []

    # Get collections assigned to user's grouping roles
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
                RoleCollectionAssignment.expires_at > datetime.now(UTC)
            )
        )
        .distinct()
    )

    result = await db.execute(stmt)
    return list(result.scalars().all())
```

### 4. Team Management

```python
async def create_use_case_with_team(
    use_case_data: UseCaseCreateRequest,
    user_id: UUID,
    db: AsyncSession
) -> UseCase:
    """
    Create use case and assign to creator's team.

    Team assignment rules:
    1. If user has ONE team: Auto-assign to that team
    2. If user has MULTIPLE teams: Require team_id in request
    3. If user has NO teams: Assign to 'team:default'
    4. Admin and use_case_admin can specify any team
    """
    user_roles = await get_user_roles(user_id, db)
    user_teams = await get_user_teams(user_id, db)

    # Determine team assignment
    if use_case_data.team_id:
        # Explicit team specified
        team_id = use_case_data.team_id

        # Validate: user must be member of specified team (unless admin/use_case_admin)
        if 'admin' not in user_roles and 'use_case_admin' not in user_roles and team_id not in user_teams:
            raise HTTPException(
                status_code=403,
                detail=f"You are not a member of team '{team_id}'"
            )
    elif len(user_teams) == 1:
        # Auto-assign to user's only team
        team_id = user_teams[0]
    elif len(user_teams) > 1:
        # Multiple teams - must specify
        raise HTTPException(
            status_code=400,
            detail="You are a member of multiple teams. Please specify team_id."
        )
    else:
        # No team membership - default team
        team_id = 'team:default'

    # Create use case
    use_case = UseCase(
        use_case_id=use_case_data.use_case_id,
        name=use_case_data.name,
        description=use_case_data.description,
        team_id=team_id,
        created_by_user_id=user_id,
        lifecycle_state='draft',
        config_json=use_case_data.config,
        # ... other fields
    )

    db.add(use_case)
    await db.commit()
    await db.refresh(use_case)

    return use_case
```

---

## Frontend Changes

### 1. Corrected System Roles Definition

**File:** `src/frontend-angular/src/app/pages/admin/role-management/models/role-management.models.ts`

```typescript
/**
 * Predefined system/capability roles (Tier 1).
 * These are immutable and cannot be deleted.
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
    description: 'Use case development SUPER USER - sees all use cases across all teams',
    is_system_role: true,
  },
  {
    role_name: 'developer',
    display_name: 'Developer',
    description: 'Use case development - team-scoped visibility (sees only own team drafts)',
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
```

### 2. New UI: Use Case Grouping Role Management

**New Page:** `/admin/use-case-roles`

```typescript
@Component({
  selector: 'app-use-case-role-management',
  template: `
    <div class="page-container">
      <div class="page-header">
        <h1>
          <mat-icon>folder_shared</mat-icon>
          Use Case Grouping Roles
        </h1>
        <button mat-raised-button color="primary" (click)="createRole()">
          <mat-icon>add</mat-icon> Create New Role
        </button>
      </div>

      <p class="help-text">
        Use case grouping roles control which use cases users can execute.
        Assign use cases to roles, then assign users to roles.
      </p>

      <table mat-table [dataSource]="groupingRoles">
        <ng-container matColumnDef="role_name">
          <th mat-header-cell *matHeaderCellDef>Role Name</th>
          <td mat-cell *matCellDef="let role">
            <code>{{ role.role_name }}</code>
          </td>
        </ng-container>

        <ng-container matColumnDef="display_name">
          <th mat-header-cell *matHeaderCellDef>Display Name</th>
          <td mat-cell *matCellDef="let role">{{ role.display_name }}</td>
        </ng-container>

        <ng-container matColumnDef="description">
          <th mat-header-cell *matHeaderCellDef>Description</th>
          <td mat-cell *matCellDef="let role">{{ role.description }}</td>
        </ng-container>

        <ng-container matColumnDef="use_case_count">
          <th mat-header-cell *matHeaderCellDef>Use Cases</th>
          <td mat-cell *matCellDef="let role">{{ role.use_case_count }}</td>
        </ng-container>

        <ng-container matColumnDef="collection_count">
          <th mat-header-cell *matHeaderCellDef>Collections</th>
          <td mat-cell *matCellDef="let role">{{ role.collection_count }}</td>
        </ng-container>

        <ng-container matColumnDef="user_count">
          <th mat-header-cell *matHeaderCellDef>Users</th>
          <td mat-cell *matCellDef="let role">{{ role.user_count }}</td>
        </ng-container>

        <ng-container matColumnDef="actions">
          <th mat-header-cell *matHeaderCellDef>Actions</th>
          <td mat-cell *matCellDef="let role">
            <button mat-icon-button (click)="manageUseCases(role)">
              <mat-icon>assignment</mat-icon>
            </button>
            <button mat-icon-button (click)="manageCollections(role)">
              <mat-icon>folder</mat-icon>
            </button>
            <button mat-icon-button (click)="manageUsers(role)">
              <mat-icon>people</mat-icon>
            </button>
            <button mat-icon-button (click)="deleteRole(role)">
              <mat-icon>delete</mat-icon>
            </button>
          </td>
        </ng-container>

        <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
        <tr mat-row *matRowDef="let row; columns: displayedColumns"></tr>
      </table>
    </div>
  `
})
export class UseCaseRoleManagementComponent implements OnInit {
  groupingRoles: GroupingRoleInfo[] = [];

  async ngOnInit() {
    // Load dynamic grouping roles from backend
    this.groupingRoles = await this.roleService.getGroupingRoles();
  }

  createRole() {
    const dialogRef = this.dialog.open(CreateGroupingRoleDialog, {
      width: '600px'
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.loadRoles();
      }
    });
  }
}
```

### 3. New UI: Developer Team Management

**New Page:** `/admin/developer-teams`

```typescript
@Component({
  selector: 'app-developer-teams',
  template: `
    <div class="page-container">
      <div class="page-header">
        <h1>
          <mat-icon>groups</mat-icon>
          Developer Teams
        </h1>
        <button mat-raised-button color="primary" (click)="createTeam()">
          <mat-icon>add</mat-icon> Create Team
        </button>
      </div>

      <p class="help-text">
        Developer teams isolate draft use cases between groups.
        Team members can see each other's drafts but not other teams' drafts.
      </p>

      <table mat-table [dataSource]="teams">
        <ng-container matColumnDef="display_name">
          <th mat-header-cell *matHeaderCellDef>Team Name</th>
          <td mat-cell *matCellDef="let team">{{ team.display_name }}</td>
        </ng-container>

        <ng-container matColumnDef="team_id">
          <th mat-header-cell *matHeaderCellDef>Team ID</th>
          <td mat-cell *matCellDef="let team">
            <code>{{ team.team_id }}</code>
          </td>
        </ng-container>

        <ng-container matColumnDef="member_count">
          <th mat-header-cell *matHeaderCellDef>Members</th>
          <td mat-cell *matCellDef="let team">{{ team.member_count }}</td>
        </ng-container>

        <ng-container matColumnDef="draft_count">
          <th mat-header-cell *matHeaderCellDef>Drafts</th>
          <td mat-cell *matCellDef="let team">{{ team.draft_count }}</td>
        </ng-container>

        <ng-container matColumnDef="published_count">
          <th mat-header-cell *matHeaderCellDef>Published</th>
          <td mat-cell *matCellDef="let team">{{ team.published_count }}</td>
        </ng-container>

        <ng-container matColumnDef="actions">
          <th mat-header-cell *matHeaderCellDef>Actions</th>
          <td mat-cell *matCellDef="let team">
            <button mat-icon-button (click)="manageMembers(team)">
              <mat-icon>people</mat-icon>
            </button>
            <button mat-icon-button (click)="viewUseCases(team)">
              <mat-icon>visibility</mat-icon>
            </button>
            <button mat-icon-button (click)="editTeam(team)">
              <mat-icon>edit</mat-icon>
            </button>
          </td>
        </ng-container>

        <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
        <tr mat-row *matRowDef="let row; columns: displayedColumns"></tr>
      </table>
    </div>
  `
})
export class DeveloperTeamsComponent { }
```

### 4. Updated UI: Use Case Developer View

```typescript
@Component({
  selector: 'app-use-case-developer',
  template: `
    <mat-tab-group>
      <!-- My Drafts - only use cases I created -->
      <mat-tab label="My Drafts ({{ myDraftCount }})">
        <app-use-case-list
          [filter]="{
            lifecycle_state: 'draft',
            created_by: currentUserId
          }"
          [showEdit]="true"
        ></app-use-case-list>
      </mat-tab>

      <!-- Team Drafts - use cases from my team(s) -->
      <mat-tab label="Team Drafts ({{ teamDraftCount }})" *ngIf="userTeams.length > 0">
        <div *ngIf="userTeams.length > 1" class="team-selector">
          <mat-chip-list>
            <mat-chip
              *ngFor="let team of userTeams"
              [selected]="selectedTeam === team.team_id"
              (click)="selectTeam(team.team_id)"
            >
              {{ team.display_name }}
            </mat-chip>
          </mat-chip-list>
        </div>

        <app-use-case-list
          [filter]="{
            lifecycle_state: 'draft',
            team_id: selectedTeam
          }"
          [showCreator]="true"
          [showEdit]="false"
        ></app-use-case-list>

        <div class="help-text">
          <mat-icon>info</mat-icon>
          These are draft use cases from your team.
          You can view and clone them but only edit your own.
        </div>
      </mat-tab>

      <!-- In Review -->
      <mat-tab label="In Review ({{ reviewCount }})">
        <app-use-case-list
          [filter]="{ lifecycle_state: 'review' }"
          [showEdit]="false"
        ></app-use-case-list>
      </mat-tab>

      <!-- Published -->
      <mat-tab label="Published ({{ publishedCount }})">
        <app-use-case-list
          [filter]="{ lifecycle_state: 'published' }"
          [showEdit]="false"
          [showClone]="true"
        ></app-use-case-list>
      </mat-tab>
    </mat-tab-group>
  `
})
export class UseCaseDeveloperComponent implements OnInit {
  userTeams: DeveloperTeam[] = [];
  selectedTeam: string | null = null;

  async ngOnInit() {
    this.userTeams = await this.teamService.getMyTeams();
    if (this.userTeams.length > 0) {
      this.selectedTeam = this.userTeams[0].team_id;
    }
  }
}
```

### 5. Updated UI: User Management - Role Assignment

```typescript
// User detail dialog
@Component({
  selector: 'app-user-detail-dialog',
  template: `
    <h2>Edit User: {{ user.username }}</h2>

    <mat-divider></mat-divider>

    <h3>System Roles (Capabilities)</h3>
    <p class="help-text">Grant user capabilities in the system</p>
    <mat-chip-list>
      <mat-chip
        *ngFor="let role of systemRoles"
        [selected]="userHasRole(role.role_name)"
        (click)="toggleRole(role.role_name)"
      >
        {{ role.display_name }}
      </mat-chip>
    </mat-chip-list>

    <mat-divider></mat-divider>

    <h3>Use Case Grouping Roles</h3>
    <p class="help-text">Grant access to specific use case groups</p>
    <mat-chip-list>
      <mat-chip
        *ngFor="let role of groupingRoles"
        [selected]="userHasRole(role.role_name)"
        (click)="toggleRole(role.role_name)"
      >
        {{ role.display_name }}
      </mat-chip>
    </mat-chip-list>

    <mat-divider></mat-divider>

    <h3>Developer Teams</h3>
    <p class="help-text">Assign user to development teams (for developer/use_case_admin users)</p>
    <mat-chip-list>
      <mat-chip
        *ngFor="let team of developerTeams"
        [selected]="userHasRole(team.team_id)"
        (click)="toggleRole(team.team_id)"
        [disabled]="!userHasRole('developer') && !userHasRole('use_case_admin')"
      >
        {{ team.display_name }}
      </mat-chip>
    </mat-chip-list>
    <p class="help-text" *ngIf="!userHasRole('developer') && !userHasRole('use_case_admin')">
      User must have developer or use_case_admin role to join developer teams
    </p>

    <div class="dialog-actions">
      <button mat-button (click)="cancel()">Cancel</button>
      <button mat-raised-button color="primary" (click)="save()">Save</button>
    </div>
  `
})
export class UserDetailDialogComponent { }
```

---

## Backend API Changes

### 1. New Endpoints: Grouping Role Management

```python
# src/orchestrator/app/routers/admin_grouping_roles.py

@router.get("/admin/grouping-roles", response_model=list[GroupingRoleInfo])
async def list_grouping_roles(
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> list[GroupingRoleInfo]:
    """
    List all use case grouping roles.

    Returns dynamic roles (not system roles) with counts.
    """
    require_admin_or_role_admin(current_user)

    # Get all roles that are not system roles and not teams
    system_roles = ['admin', 'corpus_admin', 'use_case_admin', 'tools_admin', 'conversations', 'role_admin']

    result = await db.execute(
        select(UserRoleMembership.role, func.count(UserRoleMembership.user_id))
        .where(
            ~UserRoleMembership.role.in_(system_roles),
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
        use_case_count = uc_result.scalar()

        # Get collection count
        col_result = await db.execute(
            select(func.count(RoleCollectionAssignment.id))
            .where(
                RoleCollectionAssignment.role_name == role_name,
                RoleCollectionAssignment.is_active == True
            )
        )
        collection_count = col_result.scalar()

        grouping_roles.append(GroupingRoleInfo(
            role_name=role_name,
            user_count=user_count,
            use_case_count=use_case_count,
            collection_count=collection_count
        ))

    return grouping_roles


@router.post("/admin/grouping-roles", response_model=GroupingRoleResponse)
async def create_grouping_role(
    role_data: CreateGroupingRoleRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> GroupingRoleResponse:
    """
    Create a new use case grouping role.

    Role is created by first assignment (user or use case).
    This endpoint just validates the role name.
    """
    require_admin_or_role_admin(current_user)

    # Validate role name format
    if not re.match(r'^[a-z][a-z0-9_-]{1,49}$', role_data.role_name):
        raise HTTPException(
            status_code=400,
            detail="Invalid role name. Must be lowercase alphanumeric with underscores/hyphens, 2-50 chars"
        )

    # Check not a system role
    system_roles = ['admin', 'corpus_admin', 'use_case_admin', 'tools_admin', 'conversations', 'role_admin']
    if role_data.role_name in system_roles:
        raise HTTPException(
            status_code=400,
            detail="Cannot use system role name"
        )

    # Check not a team
    if role_data.role_name.startswith('team:'):
        raise HTTPException(
            status_code=400,
            detail="Team roles must be created via team management"
        )

    logger.info(f"Created grouping role: {role_data.role_name}")

    return GroupingRoleResponse(
        role_name=role_data.role_name,
        display_name=role_data.display_name,
        description=role_data.description,
        created_by=current_user.user_id
    )
```

### 2. New Endpoints: Developer Team Management

```python
# src/orchestrator/app/routers/admin_developer_teams.py

@router.get("/admin/developer-teams", response_model=list[DeveloperTeamInfo])
async def list_developer_teams(
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> list[DeveloperTeamInfo]:
    """List all developer teams with statistics."""
    require_admin_or_role_admin(current_user)

    # Get all team roles
    result = await db.execute(
        select(
            UserRoleMembership.role,
            func.count(UserRoleMembership.user_id)
        )
        .where(UserRoleMembership.role.like('team:%'))
        .group_by(UserRoleMembership.role)
    )

    teams = []
    for team_id, member_count in result.all():
        # Get draft count
        draft_result = await db.execute(
            select(func.count(UseCase.id))
            .where(
                UseCase.team_id == team_id,
                UseCase.lifecycle_state == 'draft'
            )
        )
        draft_count = draft_result.scalar()

        # Get published count
        pub_result = await db.execute(
            select(func.count(UseCase.id))
            .where(
                UseCase.team_id == team_id,
                UseCase.lifecycle_state == 'published'
            )
        )
        published_count = pub_result.scalar()

        # Get team metadata
        meta_result = await db.execute(
            select(UserRoleMembership.metadata)
            .where(UserRoleMembership.role == team_id)
            .limit(1)
        )
        metadata = meta_result.scalar()

        teams.append(DeveloperTeamInfo(
            team_id=team_id,
            display_name=metadata.get('team_display_name', team_id.replace('team:', '').replace('_', ' ').title()),
            description=metadata.get('description', ''),
            member_count=member_count,
            draft_count=draft_count,
            published_count=published_count
        ))

    return teams


@router.post("/admin/developer-teams", response_model=DeveloperTeamResponse)
async def create_developer_team(
    team_data: CreateDeveloperTeamRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> DeveloperTeamResponse:
    """Create a new developer team."""
    require_admin_or_role_admin(current_user)

    # Validate team_id format
    team_id = f"team:{team_data.team_name}"

    if not re.match(r'^team:[a-z][a-z0-9_-]{1,49}$', team_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid team name. Must be lowercase alphanumeric with underscores/hyphens"
        )

    # Check if team already exists
    result = await db.execute(
        select(UserRoleMembership)
        .where(UserRoleMembership.role == team_id)
        .limit(1)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Team '{team_id}' already exists"
        )

    logger.info(f"Created developer team: {team_id}")

    return DeveloperTeamResponse(
        team_id=team_id,
        display_name=team_data.display_name,
        description=team_data.description,
        member_count=0,
        draft_count=0,
        published_count=0
    )


@router.post("/admin/developer-teams/{team_id}/members", status_code=201)
async def add_team_member(
    team_id: str,
    member_data: TeamMemberRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Add a user to a developer team."""
    require_admin_or_role_admin(current_user)

    # Validate and normalize team_id
    if not team_id.startswith('team:'):
        team_id = f"team:{team_id}"

    # Validate user exists and has developer or use_case_admin role
    # (This must execute unconditionally, not just when team_id is normalized)
    user = await db.get(AuthUser, UUID(member_data.user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_roles = await get_user_roles(UUID(member_data.user_id), db)
    if 'developer' not in user_roles and 'use_case_admin' not in user_roles:
        raise HTTPException(
            status_code=400,
            detail="User must have developer or use_case_admin role to join developer teams"
        )

    # Add team membership
    membership = UserRoleMembership(
        user_id=UUID(member_data.user_id),
        role=team_id,
        granted_by=UUID(current_user.user_id),
        metadata={'team_display_name': member_data.team_display_name or team_id}
    )

    db.add(membership)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail="User is already a member of this team"
        )

    logger.info(f"Added user {member_data.user_id} to team {team_id}")

    return {"message": "User added to team successfully"}
```

### 3. Updated Endpoint: Use Case Creation with Team

```python
# src/orchestrator/app/routers/use_case_management.py

@router.post("/use-cases", response_model=UseCaseResponse)
async def create_use_case(
    use_case_data: UseCaseCreateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> UseCaseResponse:
    """
    Create new use case with automatic team assignment.

    Requires: developer, use_case_admin, or admin role.
    """
    # Verify user has required role
    user_id = UUID(current_user.user_id)
    is_admin = await has_role(user_id, "admin", db)
    is_use_case_admin = await has_role(user_id, "use_case_admin", db)
    is_developer = await has_role(user_id, "developer", db)

    if not (is_admin or is_use_case_admin or is_developer):
        raise HTTPException(
            status_code=403,
            detail="developer, use_case_admin, or admin role required"
        )

    user_teams = await get_user_teams(UUID(current_user.user_id), db)
    user_roles = await get_user_roles(UUID(current_user.user_id), db)

    # Determine team assignment
    if use_case_data.team_id:
        # Explicit team specified
        team_id = use_case_data.team_id

        # Validate: user must be member (unless admin/use_case_admin)
        if 'admin' not in user_roles and 'use_case_admin' not in user_roles and team_id not in user_teams:
            raise HTTPException(
                status_code=403,
                detail=f"You are not a member of team '{team_id}'"
            )
    elif len(user_teams) == 1:
        # Auto-assign to user's only team
        team_id = user_teams[0]
    elif len(user_teams) > 1:
        # Multiple teams - must specify
        raise HTTPException(
            status_code=400,
            detail="You are a member of multiple teams. Please specify team_id in request."
        )
    else:
        # No team membership - default team
        team_id = 'team:default'

    # Create use case
    use_case = UseCase(
        use_case_id=use_case_data.use_case_id,
        name=use_case_data.name,
        description=use_case_data.description,
        category=use_case_data.category,
        intent_type=use_case_data.intent_type,
        team_id=team_id,
        created_by_user_id=UUID(current_user.user_id),
        lifecycle_state='draft',
        is_active=False,
        config_json=use_case_data.config.model_dump(),
        metadata_json=use_case_data.metadata or {}
    )

    db.add(use_case)
    await db.commit()
    await db.refresh(use_case)

    logger.info(
        f"Created use case {use_case.use_case_id} for team {team_id}",
        extra={
            "use_case_id": use_case.use_case_id,
            "team_id": team_id,
            "user_id": current_user.user_id
        }
    )

    return UseCaseResponse.from_orm(use_case)
```

### 4. New Endpoint: Collection Role Assignments

```python
# src/orchestrator/app/routers/admin_roles.py

@router.post(
    "/{role_name}/collections",
    response_model=RoleCollectionAssignResponse,
    status_code=201
)
async def assign_collection_to_role(
    role_name: str,
    request: RoleCollectionAssignRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> RoleCollectionAssignResponse:
    """Assign a document collection to a role."""
    require_admin(current_user)

    # Verify collection exists
    collection = await db.get(Collection, request.collection_id)
    if not collection:
        raise HTTPException(
            status_code=404,
            detail=f"Collection {request.collection_id} not found"
        )

    # Check if already assigned
    result = await db.execute(
        select(RoleCollectionAssignment).where(
            and_(
                RoleCollectionAssignment.role_name == role_name,
                RoleCollectionAssignment.collection_id == request.collection_id
            )
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Update existing
        existing.is_active = True
        existing.expires_at = request.expires_at
        existing.metadata_json = request.metadata
        existing.granted_by = UUID(current_user.user_id)
        existing.granted_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(existing)

        logger.info(f"Updated collection assignment: {role_name} -> {collection.name}")

        return RoleCollectionAssignResponse.from_orm(existing)

    # Create new assignment
    assignment = RoleCollectionAssignment(
        role_name=role_name,
        collection_id=request.collection_id,
        granted_by=UUID(current_user.user_id),
        expires_at=request.expires_at,
        metadata_json=request.metadata
    )

    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)

    logger.info(f"Assigned collection to role: {role_name} -> {collection.name}")

    return RoleCollectionAssignResponse.from_orm(assignment)
```

---

## Migration Strategy

### Phase 1: Database Schema Updates (Week 1)

**Objective:** Update database schema without breaking existing functionality.

#### Step 1.1: Add Team ID Column to Use Cases

```sql
-- Migration: 001_add_team_id_to_use_cases.sql
ALTER TABLE use_cases
ADD COLUMN team_id VARCHAR(100);

CREATE INDEX idx_use_cases_team_lifecycle
ON use_cases(team_id, lifecycle_state);

COMMENT ON COLUMN use_cases.team_id IS
    'Developer team that owns this use case. Format: team:team_name';

-- Set default for existing use cases
UPDATE use_cases
SET team_id = 'team:default'
WHERE team_id IS NULL;
```

#### Step 1.2: Create Collection Role Assignments Table

```sql
-- Migration: 002_create_role_collection_assignments.sql
CREATE TABLE role_collection_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_name VARCHAR(50) NOT NULL,
    collection_id UUID NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    granted_by UUID REFERENCES users(id),
    granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    UNIQUE(role_name, collection_id)
);

CREATE INDEX idx_role_collection_assignments_role
ON role_collection_assignments(role_name, is_active);

CREATE INDEX idx_role_collection_assignments_collection
ON role_collection_assignments(collection_id, is_active);

COMMENT ON TABLE role_collection_assignments IS
    'Assigns document collections to roles. Users inherit collection access through role memberships.';
```

#### Step 1.3: Migrate Existing Users to user_roles Table

```sql
-- Migration: 003_migrate_users_to_user_roles.sql

-- Migrate existing users.role to user_roles table
INSERT INTO user_roles (user_id, role, granted_by, granted_at, metadata)
SELECT
    id,
    role,
    NULL,  -- System migration
    created_at,
    '{}'::jsonb
FROM users
WHERE role IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM user_roles ur
      WHERE ur.user_id = users.id
      AND ur.role = users.role
  );

-- DO NOT drop users.role column yet - keep for backward compatibility during migration
-- Will be dropped in Phase 4
```

### Phase 2: Backend Implementation (Week 2-3)

**Objective:** Implement new RBAC logic and APIs.

#### Step 2.1: Update Auth Models

**File:** `src/shared/auth/models.py`

```python
# Update UserRole enum to be reference only
class SystemRole(str, Enum):
    """System/capability roles (Tier 1)."""
    ADMIN = "admin"
    CORPUS_ADMIN = "corpus_admin"
    USE_CASE_ADMIN = "use_case_admin"
    TOOLS_ADMIN = "tools_admin"
    CONVERSATIONS = "conversations"
    ROLE_ADMIN = "role_admin"

    @classmethod
    def all_roles(cls) -> list[str]:
        return [role.value for role in cls]
```

#### Step 2.2: Implement RBAC Service

Create new file: `src/orchestrator/app/services/rbac_v2.py`

Implement all functions from "Access Control Logic" section above.

#### Step 2.3: Create New API Routers

- `src/orchestrator/app/routers/admin_grouping_roles.py`
- `src/orchestrator/app/routers/admin_developer_teams.py`
- Update `src/orchestrator/app/routers/admin_roles.py` with collection assignments
- Update `src/orchestrator/app/routers/use_case_management.py` with team logic

#### Step 2.4: Add Models

Create: `src/orchestrator/app/db/models_rbac.py`

```python
class RoleCollectionAssignment(TimestampMixin, Base):
    """Collection assignments to roles."""
    __tablename__ = "role_collection_assignments"
    # ... (as defined in schema section)
```

#### Step 2.5: Update Use Case APIs

Modify:

- `GET /api/use-cases` - Filter by user's accessible use cases
- `POST /api/use-cases` - Add team assignment logic
- `GET /api/use-cases/{id}` - Check team-based visibility

#### Step 2.6: Add Collection Visibility Logic

Create: `src/orchestrator/app/services/collection_rbac.py`

Implement collection access control (from "Access Control Logic" section).

### Phase 3: Frontend Implementation (Week 4-5)

**Objective:** Update Angular UI to reflect new RBAC model.

#### Step 3.1: Update Models

**File:** `src/frontend-angular/src/app/pages/admin/role-management/models/role-management.models.ts`

- Fix `SYSTEM_ROLES` constant (remove analyst, developer)
- Add `GroupingRoleInfo` interface
- Add `DeveloperTeamInfo` interface

#### Step 3.2: Create New Components

- `use-case-role-management.component.ts` (grouping roles)
- `developer-teams.component.ts` (team management)
- `create-grouping-role-dialog.component.ts`
- `create-team-dialog.component.ts`
- `team-member-manager.component.ts`

#### Step 3.3: Update Existing Components

- `user-management.component.ts` - Multi-role assignment
- `use-case-developer.component.ts` - Team-filtered tabs
- `use-case-list.component.ts` - Team visibility
- Navigation service - Update menu visibility logic

#### Step 3.4: Update Services

- `role-management.service.ts` - Add grouping role APIs
- `team-management.service.ts` (new) - Team APIs
- `auth.service.ts` - Multi-role support

### Phase 4: Testing & Rollout (Week 6)

**Objective:** Comprehensive testing and safe production deployment.

#### Step 4.1: Backend Testing

```python
# tests/integration/test_rbac_v2.py

async def test_default_deny_access():
    """Base user with no roles sees nothing."""
    user = await create_test_user("alice")
    use_cases = await get_accessible_use_cases(user.id, db)
    assert len(use_cases) == 0

async def test_grouping_role_access():
    """User with grouping role sees assigned use cases."""
    user = await create_test_user("bob")
    await assign_role(user.id, "threat_hunting", db)
    await assign_use_case_to_role("threat_hunting", use_case_1.id, db)

    use_cases = await get_accessible_use_cases(user.id, db)
    assert len(use_cases) == 1
    assert use_cases[0].id == use_case_1.id

async def test_team_isolation():
    """Teams cannot see each other's drafts."""
    alice = await create_test_user("alice")
    bob = await create_test_user("bob")

    await assign_role(alice.id, "developer", db)
    await assign_role(bob.id, "developer", db)
    await assign_role(alice.id, "team:csirt", db)
    await assign_role(bob.id, "team:soc_gov", db)

    alice_uc = await create_use_case("test-uc-1", alice.id, team_id="team:csirt", db)

    alice_ucs = await get_accessible_use_cases(alice.id, db, lifecycle_state="draft")
    bob_ucs = await get_accessible_use_cases(bob.id, db, lifecycle_state="draft")

    assert alice_uc in alice_ucs
    assert alice_uc not in bob_ucs  # Bob cannot see Alice's team draft

async def test_use_case_admin_sees_all():
    """use_case_admin sees all drafts from all teams."""
    grace = await create_test_user("grace")
    await assign_role(grace.id, "use_case_admin", db)

    all_ucs = await get_accessible_use_cases(grace.id, db, lifecycle_state=None)
    assert len(all_ucs) > 0  # Sees everything including all team drafts

async def test_admin_sees_all():
    """Admin sees all drafts from all teams."""
    admin = await create_test_user("admin")
    await assign_role(admin.id, "admin", db)

    all_ucs = await get_accessible_use_cases(admin.id, db, lifecycle_state=None)
    assert len(all_ucs) > 0  # Sees everything including all team drafts
```

#### Step 4.2: Frontend Testing

- Unit tests for role management components
- E2E tests for role assignment workflows
- Team isolation verification
- Empty state testing (no roles)

#### Step 4.3: Data Migration Verification

```sql
-- Verify migration success
SELECT
    COUNT(*) as total_users,
    COUNT(DISTINCT ur.user_id) as users_with_roles,
    COUNT(*) FILTER (WHERE u.role IS NOT NULL) as users_with_old_role
FROM users u
LEFT JOIN user_roles ur ON u.id = ur.user_id;

-- Should show: total_users = users_with_roles (all migrated)
```

#### Step 4.4: Production Deployment

1. **Backup database**
2. **Deploy schema migrations** (Phase 1)
3. **Deploy backend** (Phase 2)
4. **Deploy frontend** (Phase 3)
5. **Verify functionality**
6. **Monitor logs for errors**

### Phase 5: Cleanup (Week 7)

**Objective:** Remove deprecated code and columns.

#### Step 5.1: Drop users.role Column

```sql
-- Migration: 004_drop_users_role_column.sql
-- ONLY run this after verifying everything works in production

ALTER TABLE users DROP COLUMN role;
```

#### Step 5.2: Remove Old Code

- Delete `src/shared/auth/models.py:UserRole` (old enum)
- Remove any remaining references to single user role
- Update documentation

---

## Example User Scenarios

### Scenario 1: Base User (No Access)

```
User: carol
Roles: [] (none)

Login → See dashboard (empty) → Message: "No use cases available. Contact administrator."
```

### Scenario 2: SOC Analyst (Grouping Roles Only)

```
User: alice
Roles: ['threat_hunting', 'incident_response']

Login → See:
- Use Cases: 8 use cases (5 from threat_hunting + 3 from incident_response)
- Collections: 3 collections (assigned to her roles)
- Cannot: Access admin panels, develop use cases, manage documents
```

### Scenario 3: Developer (Single Team)

```
User: bob
Roles: ['developer', 'team:csirt_security']

Login → See:
- My Drafts: 3 use cases (created by bob)
- Team Drafts: 5 use cases (from team:csirt_security)
- In Review: 2 use cases (any team)
- Published: ALL published use cases
- Can: Create/edit own drafts, clone any use case, submit for review
- Cannot: Edit team members' drafts, see other teams' drafts
```

### Scenario 4: Developer (Multiple Teams)

```
User: dave
Roles: ['developer', 'team:csirt_security', 'team:soc_governance']

Creating use case → Must specify team_id in request
Login → See:
- Team selector (CSIRT / SOC Gov)
- Team Drafts filtered by selected team
```

### Scenario 5: Use Case Admin (Super User)

```
User: grace
Roles: ['use_case_admin']

Login → See:
- ALL use cases (all states, all teams)
- ALL collections (for reference)
- Developer Tools admin panels
- Can: Create/edit ANY use case, manage use case lifecycle
- Cannot: System administration, user management
```

### Scenario 6: Admin (Full Access)

```
User: frank
Roles: ['admin']

Login → See:
- ALL use cases (all states, all teams)
- ALL collections
- ALL admin panels
- Can: Everything
```

### Scenario 7: Role Admin

```
User: emma
Roles: ['role_admin', 'threat_hunting']

Login → See:
- Own use cases (from threat_hunting role)
- Admin panel: Role Management
  - Create grouping roles
  - Assign use cases to roles
  - Assign users to roles
  - Create developer teams
- Cannot: Configure system, manage all users, access other admin functions
```

---

## Rollback Plan

If issues arise during deployment:

### Immediate Rollback (< 1 hour)

1. **Revert frontend deployment** (restore previous Angular build)
2. **Revert backend deployment** (restore previous API version)
3. **Database state:** No rollback needed - new columns/tables are additive and unused

### Partial Rollback (< 4 hours)

If migration partially completed:

```sql
-- Restore users.role column from user_roles table
UPDATE users u
SET role = (
    SELECT role
    FROM user_roles ur
    WHERE ur.user_id = u.id
    AND ur.role IN ('admin', 'corpus_admin', 'use_case_admin', 'tools_admin', 'conversations', 'role_admin')
    LIMIT 1
)
WHERE role IS NULL;
```

### Full Rollback (< 8 hours)

1. Drop new tables: `role_collection_assignments`
2. Drop new column: `use_cases.team_id`
3. Restore application from backup
4. Restore database from backup (if needed)

---

## Success Criteria

### Technical Metrics

- ✅ All users migrated from single role to multi-role system
- ✅ Zero downtime deployment
- ✅ < 100ms latency for role checks
- ✅ < 500ms latency for use case filtering
- ✅ 100% backward compatibility during migration

### Functional Metrics

- ✅ Base users see empty state (default-deny works)
- ✅ Grouping roles grant access to assigned use cases
- ✅ Team isolation works (teams can't see each other's drafts)
- ✅ Admin can manage all roles and teams
- ✅ No user loses access they previously had

### User Acceptance

- ✅ Role Management UI is understandable
- ✅ Admins can create grouping roles
- ✅ Admins can create developer teams
- ✅ Developers can see team drafts
- ✅ Documentation is clear and complete

---

## Documentation Updates Required

### Files to Update

1. `docs/admin/USER_ROLES_GUIDE.md` - Complete rewrite
2. `docs/api/admin/role-management.md` - Add grouping roles, teams
3. `docs/architecture/database/ERD.md` - Update with new relationships
4. `docs/architecture/database/SCHEMA.md` - Add new tables
5. `docs/architecture/database/RLS_POLICIES.md` - Update policies
6. `docs/development/adrs/ADR-041-Role-Based-Use-Case-Permissions.md` - Mark as superseded

### New Documentation

1. `docs/admin/GROUPING_ROLES_GUIDE.md` - How to create and manage grouping roles
2. `docs/admin/DEVELOPER_TEAMS_GUIDE.md` - How to manage developer teams
3. `docs/development/guides/rbac-implementation.md` - Developer guide

---

## Alternatives Considered

### Alternative 1: Keep Single Role System

**Rejected** because:

- ❌ Not flexible enough for real-world deployments
- ❌ Users need multiple capability grants (not mutually exclusive)
- ❌ Doesn't support team isolation

### Alternative 2: Use Dedicated Teams Table

**Rejected in favor of reusing user_roles** because:

- ❌ More complex (additional tables)
- ❌ Inconsistent with existing role system
- ⚠️ Could be revisited if richer team features needed (team leads, team permissions, etc.)

### Alternative 3: Allow Collaborative Editing Within Teams

**Rejected** because:

- ❌ Prevents merge conflicts
- ❌ Unclear ownership
- ❌ Version control issues
- ✅ Clone feature provides collaboration without conflicts

### Alternative 4: Default-Allow Access Model

**Rejected** because:

- ❌ Less secure
- ❌ Violates principle of least privilege
- ❌ Harder to audit who has access to what
- ✅ Default-deny is industry best practice

---

## References

- **ADR-041:** Role-Based Use Case Permissions (superseded by this ADR)
- **ADR-020:** Use Case Publisher Role
- **OWASP RBAC Guide:** <https://owasp.org/www-community/Access_Control>
- **NIST RBAC Standard:** <https://csrc.nist.gov/projects/role-based-access-control>

---

## Decision Record

**Proposed By:** Architecture Team
**Date:** 2025-12-08
**Status:** ACCEPTED
**Priority:** CRITICAL

**Approved By:**

- [ ] Product Owner
- [ ] Security Team
- [ ] Development Team Lead

**Implementation Start Date:** TBD
**Target Completion Date:** 7 weeks from approval

---

## Appendix A: Database Schema Summary

### Tables Modified

| Table | Changes | Migration |
|-------|---------|-----------|
| `users` | Remove `role` column (Phase 5) | 004 |
| `use_cases` | Add `team_id` column | 001 |

### Tables Created

| Table | Purpose | Migration |
|-------|---------|-----------|
| `role_collection_assignments` | Assign collections to roles | 002 |

### Tables Unchanged (Already Correct)

- `user_roles` - Multi-role support
- `role_use_case_assignments` - Use case to role mapping
- `user_use_case_assignments` - Direct user assignments

---

## Appendix B: Quick Reference

### System Roles (Tier 1)

```
admin              → Full access (all resources, all teams)
corpus_admin       → Manage documents (all documents)
use_case_admin     → Develop use cases SUPER USER (all use cases, all teams)
developer          → Create/edit use cases (team-scoped visibility)
tools_admin        → Manage tools
conversations      → Use conversation interface
role_admin         → Manage roles
```

### Grouping Role Examples (Tier 2)

```
threat_hunting
incident_response
compliance_review
malware_analysis
threat_intelligence
phishing_investigation
vulnerability_mgmt
soc_tier1
soc_tier2
legal_review
```

### Team Format (Tier 3)

```
team:csirt_security
team:soc_governance
team:threat_intel
team:compliance
```

---

**END OF ADR-060**
