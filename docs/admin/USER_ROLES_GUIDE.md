# User Roles Guide

**Version:** 2.0
**Date:** November 1, 2025
**Purpose:** Comprehensive guide to AI Operations Platform user roles and permissions

---

## Overview

AI Operations Platform uses a **dual-layer role-based access control (RBAC)** system:

- **Layer 1:** System roles control UI/feature access
- **Layer 2:** Custom roles control use case group execution

---

## Role Architecture

### Dual-Layer Role System

AI Operations Platform (AIOP) implements **two distinct role layers**:

```
┌─────────────────────────────────────────────────────────────────┐
│ User Account                                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  LAYER 1: SYSTEM ROLES (users.role - Single Primary Role)       │
│  ════════════════════════════════════════════════════════       │
│  Controls: UI panels, admin features, system capabilities       │
│  Storage: users.role column (single value)                      │
│  Usage: JWT token 'role' claim, frontend rendering              │
│                                                                  │
│  Roles: admin, corpus_admin, use_case_publisher,                │
│         conversations_privileged, user, service                  │
│                                                                  │
│  ----------------------------------------------------------------│
│                                                                  │
│  LAYER 2: CUSTOM USE CASE GROUPING ROLES (user_roles table)     │
│  ════════════════════════════════════════════════════════       │
│  Controls: Which use case groups user can execute               │
│  Storage: user_roles table (multiple rows per user)             │
│  Usage: Use case access control, RLS policies                   │
│                                                                  │
│  Examples: threat_hunting, incident_response,                   │
│            compliance_monitoring, threat_intelligence            │
│  (Dynamically created by admins to group use cases)             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Database Tables:**

```sql
-- Layer 1: System roles (single primary role)
CREATE TABLE users (
    id UUID PRIMARY KEY,
    username VARCHAR UNIQUE NOT NULL,
    role VARCHAR NOT NULL,  -- System role: admin, corpus_admin, use_case_publisher, conversations_privileged, user, service
    ...
);

-- Layer 2: Custom use case grouping roles (multiple per user)
CREATE TABLE user_roles (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    role TEXT NOT NULL,  -- Custom role: threat_hunting, incident_response, etc.
    granted_at TIMESTAMPTZ NOT NULL,
    granted_by UUID REFERENCES users(id),
    metadata JSONB,
    ...
    UNIQUE(user_id, role)
);
```

---

## Layer 1: System Roles

### Standard System Roles (Predefined)

| Role | Code | Description | Access Level |
|------|------|-------------|--------------|
| **Admin** | `admin` | System administrator with full access to all features and configuration | Full Access |
| **Corpus Admin** | `corpus_admin` | Document and corpus management, use case development | High |
| **Use Case Publisher** | `use_case_publisher` | Use case review, approval, and publishing | Medium |
| **Conversations Privileged** | `conversations_privileged` | Privileged access to Conversations UI/API | Medium |
| **User** | `user` | Standard end-user (can execute published use cases) | Basic |
| **Service** | `service` | API service accounts for automation | Special |

### System Role Hierarchy

```
┌────────────────────────────────────────────────────────┐
│                    ADMIN                                │
│  (Full system access - all features + configuration)   │
└────────────────────────────────────────────────────────┘
                          │
         ┌────────────────┼────────────────┐
         │                │                │
┌─────────▼─────────┐ ┌───▼──────┐ ┌──────▼──────────┐
│  CORPUS_ADMIN     │ │ USE_CASE │ │ CONVERSATIONS   │
│  Documents,       │ │ PUBLISHER│ │ PRIVILEGED      │
│  Collections,     │ │ Reviews, │ │ Multi-turn      │
│  Use Case Dev     │ │ Approvals│ │ conversations   │
└───────────────────┘ └──────────┘ └─────────────────┘
         │                │                │
         └────────────────┼────────────────┘
                          │
                 ┌────────▼─────────┐
                 │      USER        │
                 │  Execute use     │
                 │  cases only      │
                 └──────────────────┘

Note: 'service' role is for API automation (not shown in hierarchy)
```

---

## Role Capabilities

### Admin

**Full System Access**

**Can Access:**
- ✅ All menu items and features
- ✅ System Administration
  - User Management (create, edit, deactivate users)
  - Role Management (assign roles to users)
  - System Configuration (LLM settings, security)
  - Audit Logs (view all system events)
  - Model Management (LLM/embedding model config)
  - Collection Management
- ✅ Analytics (all dashboards including Token Usage)
- ✅ Developer Tools (use case development, query tools)
- ✅ Use Case Governance (approve/publish use cases)
- ✅ Document Management
- ✅ Conversations
- ✅ All Use Cases

**Permissions:**
- All CRUD operations
- All API endpoints
- Database RLS: bypass most restrictions

---

### Corpus Admin

**Document & Use Case Development**

**Can Access:**
- ✅ Dashboard
- ✅ SOC Dashboard
- ✅ Use Cases (execute published)
- ✅ Document Management
  - Upload Documents
  - Document Library
  - Processing Status
- ✅ Analytics (Usage, Performance)
- ✅ Developer Tools
  - Query Developer Tools
  - My Drafts (use cases)
  - Create Use Case
  - Pattern Library
- ✅ Collection Management (admin panel)
- ❌ System Administration
- ❌ Conversations
- ❌ Use Case Governance (approval)
- ❌ Token Usage (admin analytics)

**Use Cases:**
- Document librarians
- Corpus managers
- Use case developers
- RAG system administrators

---

### Use Case Publisher

**Use Case Review & Approval**

**Can Access:**
- ✅ Dashboard
- ✅ Use Cases (execute published)
- ✅ Use Case Governance
  - Pending Reviews
  - Published Use Cases
  - Archived Use Cases
- ❌ Use Case Development
- ❌ System Administration
- ❌ Document Management
- ❌ Analytics
- ❌ Conversations

**Purpose:**
- Review submitted use cases
- Approve or reject use cases
- Publish use cases (make available to users)
- Archive outdated use cases
- **Does NOT have platform admin access** (separation of duties)

**Use Cases:**
- Content governance teams
- Compliance reviewers
- Domain subject matter experts

---

### Conversations Privileged

**Privileged Conversations Access**

**Can Access:**
- ✅ Dashboard
- ✅ Use Cases (execute published)
- ✅ Conversations
  - Thread List
  - Multi-turn conversations
  - Context preservation
- ❌ All other features (default deny)

**Purpose:**
- **NEW ROLE** (added Nov 1, 2025)
- Conversations feature requires explicit privilege
- Not visible to regular users by default
- Supports classified/sensitive conversation workflows

**Use Cases:**
- Specialized analysts requiring conversation interface
- Investigations requiring multi-turn context
- Sensitive operations requiring audit trail

---

### User

**Standard End-User**

**Can Access:**
- ✅ Dashboard
- ✅ Use Cases (execute published only)
- ❌ Everything else

**Purpose:**
- General workforce
- Execute pre-approved use cases
- No administrative access
- No development access

---

### Service

**API Automation Accounts**

**Special Role:**
- Programmatic API access
- Used by SOAR platforms (Cortex, Splunk)
- Used by ITSM integrations (ServiceNow, Jira)
- No UI access (API only)
- Configurable scope via API keys

---

## Layer 2: Custom Use Case Grouping Roles

### Purpose

**Layer 2 roles control which use case groups a user can execute**, independent of their system role (Layer 1).

### Examples

| Custom Role | Description | Use Case Groups |
|-------------|-------------|-----------------|
| `threat_hunting` | Threat hunting workflows | Threat Hunt, Adversary Tracking, IOC Analysis |
| `incident_response` | Incident response workflows | Triage, Containment, Root Cause Analysis |
| `compliance_monitoring` | Compliance and audit | Policy Validation, Audit Reports, Risk Scoring |
| `threat_intelligence` | Threat intel analysis | Intel Enrichment, Campaign Tracking, Attribution |

### User Example

**Jane (SOC Analyst)**
- **System Role (Layer 1):** `user`
  - Can access: Dashboard, Use Cases (execute only)
  - Cannot access: Admin, Developer Tools, Conversations
- **Custom Roles (Layer 2):** `threat_hunting`, `incident_response`
  - Can execute: Use cases tagged with these groups
  - Cannot execute: Compliance or TI use cases

### Assignment

**Via SQL:**
```sql
-- Assign custom roles to user
INSERT INTO user_roles (user_id, role, granted_by, metadata)
SELECT
    u.id,
    'threat_hunting',
    (SELECT id FROM users WHERE username = 'admin'),
    '{"reason": "Threat hunt team member", "ticket": "HR-1234"}'::jsonb
FROM users u
WHERE u.username = 'jane';

-- Assign multiple custom roles
INSERT INTO user_roles (user_id, role, granted_by)
SELECT u.id, 'incident_response', (SELECT id FROM users WHERE username = 'admin')
FROM users u
WHERE u.username = 'jane';
```

**Via Admin UI (Future):**
- Navigate to System Administration → Role Management
- Assign use cases to custom roles
- Users inherit access through custom role membership

### Features

- **Flexible:** No database CHECK constraint
- **Dynamic:** Admins can create custom roles on demand
- **Auditable:** Full audit trail (granted_by, granted_at, metadata)
- **Granular:** Users can have multiple custom roles
- **Use Case Mapping:** Use cases tagged with custom roles via `role_use_case_assignments`

**See:** ADR-041 Role-Based Use Case Permissions

---

## Role Assignment

### Assigning Layer 1 (System Role)

**Via SQL:**
```sql
-- Set user's primary system role
UPDATE users
SET role = 'corpus_admin'
WHERE username = 'alice';
```

**Via Admin UI:**
- Navigate to System Administration → User Management
- Edit user
- Select system role from dropdown (admin, corpus_admin, use_case_publisher, conversations_privileged, user, service)
- Save

**Note:** Each user has exactly ONE system role (Layer 1).

### Assigning Layer 2 (Custom Use Case Grouping Roles)

**Via SQL:**
```sql
-- Add custom role membership(s)
INSERT INTO user_roles (user_id, role, granted_by, metadata)
SELECT
    u.id,
    'threat_hunting',
    (SELECT id FROM users WHERE username = 'admin'),
    '{"reason": "Threat hunt team member", "ticket": "HR-5678"}'::jsonb
FROM users u
WHERE u.username = 'alice';

-- Add another custom role
INSERT INTO user_roles (user_id, role, granted_by)
SELECT u.id, 'incident_response', (SELECT id FROM users WHERE username = 'admin')
FROM users u
WHERE u.username = 'alice';
```

**Via Admin UI (Future):**
- Navigate to System Administration → Role Management
- Assign custom roles to users
- Map use cases to custom roles

**Note:** Users can have MULTIPLE custom roles (Layer 2).

---

## Role-Based Use Case Access

Users can access use cases through:

1. **Direct Assignment** (`user_use_case_assignments`)
2. **Role Membership** (`role_use_case_assignments`)

### Example

```sql
-- Grant all 'analyst' role members access to "Threat Triage" use case
INSERT INTO role_use_case_assignments (role_name, use_case_id, granted_by)
SELECT
    'analyst',
    uc.id,
    (SELECT id FROM users WHERE username = 'admin')
FROM use_cases uc
WHERE uc.use_case_id = 'threat-triage';

-- All users with 'analyst' role can now execute this use case
```

**See:**
- ADR-041: Role-Based Use Case Permissions
- API: `docs/api/admin/role-use-case-management.md`

---

## Navigation by Role

### Regular User

```
└─ Dashboard
└─ Use Cases → Browse Use Cases
```

### Corpus Admin

```
└─ Dashboard
└─ SOC Dashboard
└─ Use Cases → Browse Use Cases
└─ Document Management
   ├─ Upload Documents
   ├─ Document Library
   └─ Processing Status
└─ Analytics
   ├─ Usage Analytics
   └─ Performance Metrics
└─ Developer Tools
   ├─ Query Developer Tools
   ├─ My Drafts
   ├─ Create Use Case
   └─ Pattern Library
```

### Use Case Publisher

```
└─ Dashboard
└─ Use Cases → Browse Use Cases
└─ Governance
   ├─ Pending Reviews
   ├─ Published Use Cases
   └─ Archived Use Cases
```

### Conversations Privileged

```
└─ Dashboard
└─ Use Cases → Browse Use Cases
└─ Conversations → Thread List
```

### Admin (Full Access)

```
└─ Dashboard
└─ SOC Dashboard
└─ Use Cases → Browse Use Cases
└─ Conversations → Thread List
└─ Document Management (...)
└─ Analytics
   ├─ Usage Analytics
   ├─ Performance Metrics
   ├─ Token Usage
   └─ Security Audit
└─ Developer Tools (...)
└─ Governance (...)
└─ System Administration
   ├─ User Management
   ├─ Role Management
   ├─ System Configuration
   ├─ Audit Logs
   ├─ Model Management
   └─ Collection Management
```

---

## Security Considerations

### Role Enforcement

**Frontend:**
- Menu visibility based on `UserRole` type
- Route guards (`RoleGuard`) enforce URL-level access
- Components check `AuthService.hasRole()` before rendering

**Backend:**
- JWT token includes primary `role` claim
- Endpoints use `@Depends(get_current_user)` for authentication
- Optional: `@Depends(require_roles(...))` for authorization
- Database RLS policies check `current_user_roles()`

### Best Practices

1. **Principle of Least Privilege**
   - Assign minimum role needed for job function
   - Use custom roles for specialized access

2. **Separation of Duties**
   - Use Case Publishers ≠ Platform Admins
   - Developers ≠ Approvers
   - Reduces insider threat

3. **Audit Trail**
   - All role assignments logged to `user_roles` table
   - `granted_by` and `granted_at` for accountability
   - `metadata` for business context

4. **Role Review**
   - Periodic access reviews (quarterly recommended)
   - Remove unnecessary role memberships
   - Archive inactive user accounts

---

## Migration & Compatibility

### Deprecated Roles

**`analyst` role** - Removed Nov 1, 2025
- Replaced by combination of:
  - **System Role:** `user` (Layer 1)
  - **Custom Roles:** `threat_hunting`, `incident_response`, etc. (Layer 2)
- Migration: Convert `analyst` → `user` system role + assign relevant custom roles

**`developer` role** - Never existed
- Legacy seed script referenced non-existent role
- Use `corpus_admin` instead

### New Roles (Added Nov 2025)

**`conversations_privileged`** - Added Nov 1, 2025
- Requires explicit assignment
- Not visible by default
- Backward compatible (no breaking changes)

**`use_case_publisher`** - Added Oct 2025
- Separates governance from platform admin
- Replaces ad-hoc corpus_admin approval workflows
- Frontend implemented; backend mappable to corpus_admin temporarily

---

## Troubleshooting

### User Can't See Menu Item

**Check:**
1. User's primary role: `SELECT role FROM users WHERE username = '...'`
2. Multi-role memberships: `SELECT role FROM user_roles WHERE user_id = '...'`
3. Frontend `navigation.service.ts` - verify role in `roles: [...]` array
4. Frontend JWT token - decode and check `role` claim

### User Can't Execute Use Case

**Check:**
1. Use case published: `SELECT lifecycle_state FROM use_cases WHERE use_case_id = '...'`
2. Direct assignment: `SELECT * FROM user_use_case_assignments WHERE user_id = '...'`
3. Role assignment: `SELECT * FROM role_use_case_assignments WHERE role_name = '...'`
4. RLS policies enabled: `SELECT * FROM pg_policies WHERE tablename = 'use_cases'`

### Role Assignment Not Working

**Check:**
1. Primary role vs. multi-role:
   - Primary role: `users.role` (single value)
   - Multi-role: `user_roles` table (multiple rows)
2. Database CHECK constraints (may block custom roles)
3. Frontend `normalizeRoles()` - verify role in `allowedRoles` array
4. JWT refresh needed (logout/login to get new token)

---

## API Reference

### Admin Endpoints

```
GET    /api/v1/admin/users                 # List users
POST   /api/v1/admin/users                 # Create user
PUT    /api/v1/admin/users/{id}            # Update user role
DELETE /api/v1/admin/users/{id}            # Deactivate user

GET    /api/v1/admin/roles                 # List roles
GET    /api/v1/admin/roles/{role}/users    # List users with role
POST   /api/v1/admin/roles/{role}/use-cases/{uc_id}  # Assign use case to role
DELETE /api/v1/admin/roles/{role}/use-cases/{uc_id}  # Revoke use case from role
```

**See:** `docs/api/admin/*.md`

---

## References

- **ADR-020:** Use Case Publisher Role
- **ADR-041:** Role-Based Use Case Permissions
- **API Docs:** `docs/api/admin/role-use-case-management.md`
- **Database Schema:** `ops/database/init/000_complete_init.sql`
- **Backend Model:** `src/shared/auth/models.py`
- **Frontend Type:** `src/frontend-angular/src/app/core/auth/auth.models.ts`

---

**Last Updated:** November 1, 2025
**Version:** 2.0
**Maintained By:** Architecture Team

**Changelog:**
- **v2.0 (Nov 1, 2025):** Clarified dual-layer role architecture; removed `analyst` system role
- **v1.0 (Nov 1, 2025):** Initial comprehensive role guide
