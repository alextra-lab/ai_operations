# Database Refresh/Merge Plan for Demo Setup

**Status:** IN PROGRESS (db-refresh-002 ✅, db-refresh-011 ✅ partial)
**Date:** 2025-12-10
**Last Updated:** 2025-12-11
**Author:** Architecture Team
**Priority:** HIGH - Required for Demo
**Related ADRs:** ADR-060 (RBAC V2), ADR-041 (Role-Based Use Case Permissions)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Objectives](#objectives)
3. [Architecture Context](#architecture-context)
4. [Key Decision: Merge RBAC V2 into Init Script](#key-decision-merge-rbac-v2-into-init-script)
5. [Implementation Plan](#implementation-plan)
6. [Demo Data Specifications](#demo-data-specifications)
7. [Verification Strategy](#verification-strategy)
8. [Risk Assessment](#risk-assessment)
9. [Success Criteria](#success-criteria)
10. [Supporting Documents](#supporting-documents)
11. [Appendix](#appendix)

---

## Executive Summary

This plan details the process to prepare a **clean, fresh demo database** with:

- **Consolidated database initialization** (RBAC V2 schema merged into init script)
- **Updated seed data** (12 users across 6 system roles, 3 teams)
- **Role-based access control demonstration** (Team isolation, multi-role assignments)
- **Verification scripts** to ensure data integrity and RBAC functionality

### Key Changes from Current State

| Component | Current State | Target State | Impact |
|-----------|--------------|--------------|--------|
| **Init Script** | Missing RBAC V2 schema | Includes `team_id`, `role_collection_assignments` | ✅ Fresh installs don't need migrations |
| **Users** | 6 system users | 12 users (6 original + 6 demo users) | ✅ Demonstrates all roles |
| **Teams** | None seeded | 3 teams with memberships | ✅ Team isolation demo |
| **Use Cases** | 5 published only | 5 published + 5 draft (team-specific) | ✅ Lifecycle & visibility demo |
| **Setup Process** | Init + 9 migrations + seed | Init + seed (2 steps) | ✅ Simpler, faster |

---

## Objectives

### Primary Goals

1. **Merge RBAC V2 migrations into init script** for fresh installations
2. **Create comprehensive demo dataset** showcasing RBAC V2 features
3. **Verify RBAC functionality** (team isolation, role-based access)
4. **Document credentials and test scenarios** for demo walkthroughs
5. **Automate the reset process** with scripts and verification

### Non-Goals

- ❌ **Production migration** (existing databases use migrations)
- ❌ **Backward compatibility** with old single-role system
- ❌ **Frontend changes** (UI already supports RBAC V2)

---

## Architecture Context

### RBAC V2 Overview

Per **ADR-060**, the system uses a **two-tier RBAC architecture** with **team-based development**:

#### Tier 1: System Roles (Capabilities)

Stored in `user_roles` table, grant **capabilities**:

| Role | Code | Grants | Status |
|------|------|--------|--------|
| Admin | `admin` | Full system access (all resources) | ✅ Implemented |
| Corpus Admin | `corpus_admin` | Manage documents/collections | ✅ Implemented |
| Developer | `developer` | Create/edit use cases (TEAM-SCOPED) | ✅ Implemented |
| Use Case Admin | `use_case_admin` | Use case super admin (ALL teams) | ✅ Implemented |
| Tools Admin | `tools_admin` | Manage tools/MCPs | ✅ Implemented |
| Role Admin | `role_admin` | Role management | ✅ Implemented |
| Use Case Publisher | `use_case_publisher` | Review, approve, publish use cases | ✅ Implemented |
| Conversations Privileged | `conversations_privileged` | Conversation interface access | ✅ Implemented |
| User | `user` | Standard end-user (requires grouping roles for access) | ✅ Implemented |
| Service | `service` | API automation | ✅ Implemented |

**Total System Roles:** 10 (all implemented in both backend and frontend)

#### Tier 2: Grouping Roles (Resource Access)

Stored in `user_roles` table, grant **resource access**:

- Examples: `threat_hunting`, `incident_response`, `compliance_monitoring`
- Dynamically created by admins
- Assigned to use cases and collections
- Users inherit access through role membership

#### Tier 3: Developer Teams (Isolation Boundaries)

Stored in `user_roles` table with `team:` prefix, provide **draft isolation**:

- Format: `team:team_name` (e.g., `team:csirt_security`)
- Team members see only their team's draft use cases
- Everyone sees all published use cases (global visibility)
- Use cases have `team_id` column for ownership

### Database Schema Changes

#### Tables Modified in RBAC V2

**1. `use_cases` table:**

```sql
ALTER TABLE use_cases ADD COLUMN team_id VARCHAR(100);
```

**2. New table: `role_collection_assignments`**

```sql
CREATE TABLE role_collection_assignments (
    id UUID PRIMARY KEY,
    role_name VARCHAR(50) NOT NULL,
    collection_id UUID REFERENCES collections(id),
    granted_by UUID REFERENCES users(id),
    granted_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    UNIQUE(role_name, collection_id)
);
```

**3. `user_roles` table** (already exists, now used for ALL roles):

```sql
-- System roles: 'admin', 'corpus_admin', etc.
-- Grouping roles: 'threat_hunting', 'incident_response', etc.
-- Team memberships: 'team:csirt_security', 'team:soc_governance', etc.
```

---

## Key Decision: Merge RBAC V2 into Init Script

### Problem

Current fresh installation requires:

1. Run `000_complete_init.sql`
2. Run 9 sequential migrations
3. Run RBAC V2 migrations (001, 002, 003)
4. Run seed scripts

**Total: 13 database operations** (complex, error-prone)

### Solution

**Merge RBAC V2 schema changes into `000_complete_init.sql`** for fresh installs:

```
Fresh Install (NEW):        Existing Database (Upgrade):
1. Run init script          1. Run migrations 027-035
2. Run seed scripts         2. Run RBAC V2 migrations (001-003)
                            3. Run seed scripts
```

### Benefits

| Benefit | Impact |
|---------|--------|
| **Simpler setup** | 2 steps vs 13 steps |
| **Faster installation** | ~30 seconds vs ~2 minutes |
| **Less error-prone** | Single atomic transaction |
| **Clearer documentation** | "Init then seed" vs complex migration order |
| **Demo-ready** | Fresh database in seconds |

### Trade-offs

| Trade-off | Mitigation |
|-----------|-----------|
| Init script diverges from migration history | ✅ **Acceptable:** Migrations exist for upgrading prod databases |
| Two paths to current schema | ✅ **Documented:** Fresh (init) vs upgrade (migrations) |
| Must maintain both | ✅ **Low cost:** RBAC V2 schema is stable |

---

## Implementation Plan

### Task Breakdown

All tasks tracked in TODO list. See [Supporting Documents](#supporting-documents) for full details.

#### Phase 1: Update Init Script (db-refresh-001)

**Task:** Update `ops/database/init/000_complete_init.sql` to include RBAC V2 schema

**Changes:**

1. **Add `team_id` column to `use_cases` table:**

   ```sql
   CREATE TABLE IF NOT EXISTS use_cases (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       use_case_id VARCHAR(255) NOT NULL,
       name VARCHAR(255) NOT NULL,
       -- ... existing columns ...
       team_id VARCHAR(100),  -- ← ADD THIS
       -- ... rest of table ...
   );

   CREATE INDEX IF NOT EXISTS idx_use_cases_team_lifecycle
   ON use_cases(team_id, lifecycle_state);

   COMMENT ON COLUMN use_cases.team_id IS
       'Developer team that owns this use case. Format: team:team_name. ' ||

       'Used to isolate draft use cases between teams. ' ||
       'NULL for published use cases (visible to all).';
   ```

2. **Add `role_collection_assignments` table:**

   ```sql
   CREATE TABLE IF NOT EXISTS role_collection_assignments (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       role_name VARCHAR(50) NOT NULL,
       collection_id UUID NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
       granted_by UUID REFERENCES users(id),
       granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
       expires_at TIMESTAMPTZ,
       is_active BOOLEAN DEFAULT TRUE NOT NULL,
       metadata JSONB DEFAULT '{}'::jsonb,
       created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
       updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
       UNIQUE(role_name, collection_id)
   );

   CREATE INDEX IF NOT EXISTS idx_role_collection_assignments_role
   ON role_collection_assignments(role_name, is_active);

   CREATE INDEX IF NOT EXISTS idx_role_collection_assignments_collection
   ON role_collection_assignments(collection_id, is_active);


   COMMENT ON TABLE role_collection_assignments IS
       'Assigns document collections to roles. Users inherit collection access through role memberships. See ADR-060.';
   ```

3. **Add documentation comment at top of file:**

   ```sql
   -- ==============================================================================
   -- NOTE: This init script includes RBAC V2 schema (ADR-060)
   --
   -- For fresh installations: Use this script directly

   -- For upgrading existing databases: Use migrations in ops/database/migrations/rbac_v2/
   --
   -- Last updated: 2025-12-10 (RBAC V2 consolidation)
   -- ==============================================================================
   ```

**Verification:**

```bash
# Check that table and columns exist
psql -c "\\d use_cases" | grep team_id
psql -c "\\d role_collection_assignments"
```

---

#### Phase 2: Update Seed Scripts (db-refresh-002 to db-refresh-005)

##### Task db-refresh-002: Update `001_seed_users.sql` ✅ COMPLETED (2025-12-11)

**Add 11 new demo users (to cover all 11 system roles):**

| Username | Full Name | System Role | Center ID | Purpose |
|----------|-----------|-------------|-----------|---------|
| `admin2` | Admin 2 | `admin` | headquarters | Additional admin for demo |
| `corpus_dev` | Corpus Developer | `corpus_admin` | development_team | Additional corpus admin |
| `developer1` | Developer 1 | **`developer`** | development_team | **Team-scoped use case developer** |
| `developer2` | Developer 2 | **`developer`** | soc_team | **Team-scoped use case developer** |
| `uc_admin` | Use Case Admin | **`use_case_admin`** | headquarters | **Use case super admin (all teams)** |
| `tools_manager` | Tools Manager | **`tools_admin`** | headquarters | **MCP/tools management** |
| `role_manager` | Role Manager | **`role_admin`** | headquarters | **Role management** |
| `publisher2` | Publisher 2 | `use_case_publisher` | governance_team | Additional publisher |
| `analyst_conv` | Analyst Conversations | `conversations_privileged` | soc_team | Additional conversations user |
| `analyst1` | SOC Analyst 1 | `user` | soc_team | Standard user for RBAC demo |
| `analyst2` | SOC Analyst 2 | `user` | soc_team | Standard user for RBAC demo |

**Critical Additions:**
- `developer` role users (developer1, developer2) - team-scoped development
- `use_case_admin` role user (uc_admin) - super admin seeing all teams
- `tools_admin` role user (tools_manager) - MCP/tools management
- `role_admin` role user (role_manager) - role management

These roles exist in code but have no seeded users.

**All users:** Default password `adminpassword` (⚠️ **Change in production!**)

**Implementation:** Add INSERT statement after existing users in `001_seed_users.sql`.

##### Task db-refresh-003: Update `003_seed_use_cases.sql`

**Purpose:** Ensure published use cases have `team_id = NULL` for global visibility (RBAC V2 requirement).

**Add at end of script:**

```sql
-- Ensure published use cases are globally visible (team_id = NULL)
UPDATE use_cases
SET team_id = NULL
WHERE lifecycle_state = 'published'
  AND team_id IS NOT NULL
  AND metadata->>'seed_script' = '003_seed_use_cases';
```

##### Task db-refresh-004: Create `008_seed_rbac_v2_assignments.sql`

**Purpose:** Assign users to teams (Tier 3 developer teams).

**Team Assignments:**

| Team | Team ID | Members |
|------|---------|---------|
| CSIRT Security | `team:csirt_security` | analyst1, analyst2, conv_analyst |
| SOC Governance | `team:soc_governance` | uc_publisher, publisher2 |
| Development | `team:development` | corpus_manager, corpus_dev |

**Implementation:**

```sql
-- Create team memberships
INSERT INTO user_roles (user_id, role, granted_by, granted_at, metadata)
VALUES
  -- team:csirt_security
  ((SELECT id FROM users WHERE username = 'analyst1'), 'team:csirt_security', NULL, NOW(),
   '{"seed_script":"008","team_display_name":"CSIRT Security Team"}'),
  ((SELECT id FROM users WHERE username = 'analyst2'), 'team:csirt_security', NULL, NOW(),
   '{"seed_script":"008","team_display_name":"CSIRT Security Team"}'),
  ((SELECT id FROM users WHERE username = 'conv_analyst'), 'team:csirt_security', NULL, NOW(),
   '{"seed_script":"008","team_display_name":"CSIRT Security Team"}'),

  -- team:soc_governance
  ((SELECT id FROM users WHERE username = 'uc_publisher'), 'team:soc_governance', NULL, NOW(),
   '{"seed_script":"008","team_display_name":"SOC Governance Team"}'),
  ((SELECT id FROM users WHERE username = 'publisher2'), 'team:soc_governance', NULL, NOW(),
   '{"seed_script":"008","team_display_name":"SOC Governance Team"}'),


  -- team:development
  ((SELECT id FROM users WHERE username = 'corpus_manager'), 'team:development', NULL, NOW(),
   '{"seed_script":"008","team_display_name":"Development Team"}'),
  ((SELECT id FROM users WHERE username = 'corpus_dev'), 'team:development', NULL, NOW(),
   '{"seed_script":"008","team_display_name":"Development Team"}')
ON CONFLICT (user_id, role) DO NOTHING;
```

**Verification:**

```sql
-- Verify team memberships
SELECT ur.role AS team, u.username
FROM user_roles ur
JOIN users u ON ur.user_id = u.id
WHERE ur.role LIKE 'team:%'
ORDER BY ur.role, u.username;
```

##### Task db-refresh-005: Create `009_seed_draft_use_cases.sql`

**Purpose:** Create 5 draft use cases (one per team) to demonstrate team isolation.

**Draft Use Cases:**

| Use Case ID | Name | Team | Purpose |
|-------------|------|------|---------|
| `team_uc_csirt_001` | CSIRT Threat Analysis | team:csirt_security | Demonstrates CSIRT team draft |
| `team_uc_csirt_002` | Incident Response Playbook | team:csirt_security | Second CSIRT draft |
| `team_uc_gov_001` | Compliance Reporting | team:soc_governance | Governance team draft |
| `team_uc_dev_001` | RAG Test Case | team:development | Development team draft |
| `team_uc_dev_002` | Model Evaluation | team:development | Second dev draft |

**Key attributes:**

- `lifecycle_state = 'draft'`
- `team_id` set to owning team

- `is_active = false` (drafts are inactive)
- Minimal but valid `config_json` (all required fields)

---

#### Phase 3: Create Automation Scripts (db-refresh-006 to db-refresh-007)

##### Task db-refresh-006: Create `ops/operations/reset_demo_database.sh`

**Purpose:** Automated script to reset database and vector store for demo.

**Features:**

- Drop and recreate database
- Reset Qdrant vector database
- Run init script
- Run all seed scripts in order
- Verify success
- Color-coded output
- Error handling

**Script structure:**

```bash
#!/bin/bash
set -euo pipefail

echo "🔄 Starting Demo Database Reset..."

# 1. Reset Qdrant vector database
python ops/operations/reset_datastores.py

# 2. Drop and recreate PostgreSQL database
psql -c "DROP DATABASE IF EXISTS aio;"
psql -c "CREATE DATABASE aio;"

# 3. Run init script
psql -f ops/database/init/000_complete_init.sql


# 4. Run seed scripts in order
for seed_script in ops/database/seed/*.sql; do
    echo "Running: $seed_script"
    psql -f "$seed_script"
done

echo "✅ Demo database reset complete!"
```

##### Task db-refresh-007: Create `ops/operations/verify_demo_setup.sh`

**Purpose:** Comprehensive verification of demo setup.

**Verification checks:**

1. **User count:** Verify 12 users exist
2. **System role migration:** All users have entries in `user_roles` table
3. **Team memberships:** 7 team role assignments exist
4. **Use cases:** 5 published + 5 draft use cases
5. **Team isolation:** Verify draft use cases have correct `team_id`
6. **Published visibility:** Verify published use cases have `team_id = NULL`
7. **RBAC tables:** Verify `role_collection_assignments` table exists

**Output format:**

```
✅ PASS: User count (expected: 12, actual: 12)
✅ PASS: System role migration (12/12 users migrated)
✅ PASS: Team memberships (expected: 7, actual: 7)
✅ PASS: Published use cases (expected: 5, actual: 5)

✅ PASS: Draft use cases (expected: 5, actual: 5)
✅ PASS: Draft team isolation (all drafts have team_id)
✅ PASS: Published visibility (all published have team_id = NULL)

🎉 All verification checks passed!
```

---

#### Phase 4: Documentation (db-refresh-008 to db-refresh-010)

##### Task db-refresh-008: Create `docs/demo/DEMO_CREDENTIALS.md`

**Purpose:** Reference document for all demo users, credentials, and roles.

**Content:**

- Complete user list with credentials
- System role breakdown
- Team membership matrix
- Access capabilities per user
- Test scenarios cross-reference

See [Appendix A: Demo Credentials](#appendix-a-demo-credentials) for draft content.

##### Task db-refresh-009: Create `docs/demo/DEMO_TEST_SCENARIOS.md`

**Purpose:** Manual test walkthrough scenarios for demo presentation.

**Scenarios:**

1. **Team Isolation:** Developer sees only their team's drafts
2. **Publisher Workflow:** Review, approve, publish use case
3. **Admin Visibility:** Admin sees all teams' drafts
4. **User Access Control:** Base user with no roles sees nothing
5. **Multi-Role User:** User with multiple grouping roles sees combined access

See [Appendix B: Test Scenarios](#appendix-b-test-scenarios) for draft content.

##### Task db-refresh-010: Create `docs/demo/DATABASE_REFRESH_PLAN.md` ✅ (THIS DOCUMENT)

---

#### Phase 5: Testing & Validation (db-refresh-011 to db-refresh-012)

##### Task db-refresh-011: Test Complete Refresh Process End-to-End 🔄 IN PROGRESS (2025-12-11)

**Status:** Seed scripts verified ✅, full end-to-end test pending

**Steps:**

1. Run `reset_demo_database.sh`
2. Run `verify_demo_setup.sh`
3. Log in as each demo user
4. Verify UI shows correct resources
5. Test team isolation manually
6. Document any issues

**Expected duration:** 30-45 minutes

##### Task db-refresh-012: Update `docs/development/guidelines/DATABASE_INITIALIZATION.md`

**Changes:**

- Add note about RBAC V2 schema in init script
- Update fresh install instructions (no migrations needed)
- Clarify upgrade vs fresh install paths
- Add reference to demo setup scripts

---

## Demo Data Specifications

### User Matrix

| # | Username | Full Name | System Role | Center ID | Team(s) | Purpose |
|---|----------|-----------|-------------|-----------|---------|---------|
| 1 | admin | System Administrator | admin | headquarters | - | Full access |
| 2 | corpus_manager | Corpus Manager | corpus_admin | headquarters | team:development | Document management |
| 3 | uc_publisher | Use Case Publisher | use_case_publisher | headquarters | team:soc_governance | Approval workflow |
| 4 | conv_analyst | Conversations Analyst | conversations_privileged | soc_team | team:csirt_security | Conversation access |
| 5 | service_account | Service Account | service | api_automation | - | API automation |
| 6 | testuser | Test User | user | test_center | - | Base user (no access) |
| 7 | admin2 | Admin 2 | admin | headquarters | - | Additional admin |
| 8 | corpus_dev | Corpus Developer | corpus_admin | development_team | team:development | Additional corpus admin |
| 9 | **developer1** | **Developer 1** | **developer** | development_team | team:development | **Team-scoped developer** |
| 10 | **developer2** | **Developer 2** | **developer** | soc_team | team:csirt_security | **Team-scoped developer** |
| 11 | **uc_admin** | **Use Case Admin** | **use_case_admin** | headquarters | - | **Use case super admin (all teams)** |
| 12 | **tools_manager** | **Tools Manager** | **tools_admin** | headquarters | - | **MCP/tools management** |
| 13 | **role_manager** | **Role Manager** | **role_admin** | headquarters | - | **Role management** |
| 14 | publisher2 | Publisher 2 | use_case_publisher | governance_team | team:soc_governance | Additional publisher |
| 15 | analyst_conv | Analyst Conversations | conversations_privileged | soc_team | - | Conversation user |
| 16 | analyst1 | SOC Analyst 1 | user | soc_team | team:csirt_security | RBAC demo |
| 17 | analyst2 | SOC Analyst 2 | user | soc_team | team:csirt_security | RBAC demo |

**Total Users:** 17 (was 6 originally, +11 new users covering all 10 system roles)

### Team Structure

| Team ID | Display Name | Members | Drafts | Purpose |
|---------|--------------|---------|--------|---------|
| team:csirt_security | CSIRT Security Team | **developer2**, analyst1, analyst2, conv_analyst | 2 | Incident response use cases |
| team:soc_governance | SOC Governance Team | uc_publisher, publisher2 | 1 | Compliance/governance use cases |
| team:development | Development Team | **developer1**, corpus_manager, corpus_dev | 2 | Development/testing use cases |

**Key Change:** Added `developer1` and `developer2` to teams - these are users with the `developer` system role (team-scoped use case development capability).

### Use Case Inventory

**Published Use Cases (5):**

| Use Case ID | Name | Team ID | Visible To |
|-------------|------|---------|------------|
| soc_triage_001 | SOC Alert Triage | NULL | Everyone |
| threat_hunting_001 | Threat Hunting Analysis | NULL | Everyone |
| incident_response_001 | Incident Response Workflow | NULL | Everyone |
| compliance_review_001 | Compliance Reporting | NULL | Everyone |
| malware_analysis_001 | Malware Analysis | NULL | Everyone |

**Draft Use Cases (5):**

| Use Case ID | Name | Team ID | Visible To |
|-------------|------|---------|------------|

| team_uc_csirt_001 | CSIRT Threat Analysis | team:csirt_security | CSIRT team only |
| team_uc_csirt_002 | Incident Response Playbook | team:csirt_security | CSIRT team only |
| team_uc_gov_001 | Compliance Reporting | team:soc_governance | Governance team only |
| team_uc_dev_001 | RAG Test Case | team:development | Development team only |
| team_uc_dev_002 | Model Evaluation | team:development | Development team only |

---

## Verification Strategy

### Automated Verification (verify_demo_setup.sh)

**SQL Queries:**

1. **User Count:**

   ```sql
   SELECT COUNT(*) FROM users; -- Expected: 12
   ```

2. **System Role Migration:**

   ```sql
   SELECT COUNT(DISTINCT user_id) FROM user_roles
   WHERE role IN ('admin', 'corpus_admin', 'use_case_publisher',
                  'conversations_privileged', 'user', 'service');
   -- Expected: 12
   ```

3. **Team Memberships:**

   ```sql
   SELECT COUNT(*) FROM user_roles WHERE role LIKE 'team:%';
   -- Expected: 7
   ```

4. **Use Case Inventory:**

   ```sql
   SELECT lifecycle_state, COUNT(*)
   FROM use_cases
   GROUP BY lifecycle_state;
   -- Expected: published=5, draft=5
   ```

5. **Draft Team Isolation:**

   ```sql
   SELECT COUNT(*) FROM use_cases
   WHERE lifecycle_state = 'draft' AND team_id IS NULL;
   -- Expected: 0 (all drafts should have team_id)
   ```

6. **Published Visibility:**

   ```sql
   SELECT COUNT(*) FROM use_cases
   WHERE lifecycle_state = 'published' AND team_id IS NOT NULL;
   -- Expected: 0 (published should have team_id = NULL)
   ```

### Manual Verification (Test Scenarios)

See `docs/demo/DEMO_TEST_SCENARIOS.md` for detailed walkthroughs.

**Quick Checks:**

1. **Base User (testuser):**
   - Login → Should see empty dashboard
   - Should see "No use cases available" message

2. **Team Member (analyst1):**
   - Login → Should see:
     - 5 published use cases
     - 2 CSIRT team drafts
     - 0 other team drafts

3. **Admin:**
   - Login → Should see:
     - 5 published use cases
     - 5 draft use cases (all teams)

4. **Publisher Workflow:**
   - Login as uc_publisher
   - Navigate to Use Case Management
   - Should see drafts from team:soc_governance
   - Can review and approve

---

## Risk Assessment

### High Risk Items

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Init script merge breaks fresh installs | Low | High | ✅ Test on clean database before committing |
| Seed data references non-existent users | Low | High | ✅ Use subqueries `(SELECT id FROM users WHERE username = ...)` |
| Team assignments fail silently | Medium | Medium | ✅ Add verification queries to seed scripts |
| Password hash doesn't match bcrypt format | Low | High | ✅ Use known-good hash from existing users |

### Medium Risk Items

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Draft use cases have invalid config_json | Medium | Low | ✅ Copy config structure from existing use cases |
| Verification script false negatives | Medium | Low | ✅ Test verification on known-good database |
| Documentation out of sync with code | High | Low | ✅ Update docs as part of each task |

### Low Risk Items

- Typos in demo credentials document (easy to fix)
- Test scenarios incomplete (can expand later)
- Verification script output formatting (cosmetic)

---

## Success Criteria

### Technical Criteria

- ✅ Init script includes RBAC V2 schema (team_id, role_collection_assignments)
- ✅ Fresh database created in < 2 minutes (init + seed)
- ✅ All 12 users created successfully
- ✅ All 7 team memberships assigned correctly
- ✅ All 10 use cases created (5 published, 5 draft)
- ✅ Verification script passes all checks
- ✅ No SQL errors during reset process

### Functional Criteria

- ✅ Base user (testuser) sees empty dashboard
- ✅ Team members see only their team's drafts
- ✅ Admin sees all use cases (all teams, all states)
- ✅ Published use cases visible to all users (team_id = NULL)
- ✅ Draft use cases isolated by team (team_id set correctly)

### Documentation Criteria

- ✅ Demo credentials document created and accurate
- ✅ Test scenarios document created with walkthroughs
- ✅ Database initialization guide updated
- ✅ All scripts have usage instructions

---

## Supporting Documents

### Created Documents

1. **`docs/demo/DATABASE_REFRESH_PLAN.md`** (this document)
2. **`docs/demo/DEMO_CREDENTIALS.md`** - User credentials and roles
3. **`docs/demo/DEMO_TEST_SCENARIOS.md`** - Manual test walkthroughs
4. **`ops/operations/reset_demo_database.sh`** - Automated reset script
5. **`ops/operations/verify_demo_setup.sh`** - Verification script

### Updated Documents

1. **`ops/database/init/000_complete_init.sql`** - Added RBAC V2 schema
2. **`ops/database/seed/001_seed_users.sql`** - Added 6 demo users
3. **`ops/database/seed/003_seed_use_cases.sql`** - Added team_id update
4. **`ops/database/seed/008_seed_rbac_v2_assignments.sql`** (NEW) - Team assignments
5. **`ops/database/seed/009_seed_draft_use_cases.sql`** (NEW) - Draft use cases
6. **`docs/development/guidelines/DATABASE_INITIALIZATION.md`** - Updated process

### Referenced Documents

1. **ADR-060:** Corrected RBAC Architecture - Two-Tier System with Team-Based Development
2. **ADR-041:** Role-Based Use Case Permissions (superseded by ADR-060)
3. **`ops/database/migrations/rbac_v2/README.md`** - RBAC V2 migration details
4. **`docs/development/guidelines/DATABASE_INITIALIZATION.md`** - Database setup guide

---

## Appendix

### Appendix A: Demo Credentials

See **`docs/demo/DEMO_CREDENTIALS.md`** for complete credentials document.

**Quick Reference:**

- **Default Password (ALL USERS):** `adminpassword`
- **Admin Users:** admin, admin2
- **Corpus Admins:** corpus_manager, corpus_dev
- **Publishers:** uc_publisher, publisher2
- **Conversation Users:** conv_analyst, analyst_conv
- **Standard Users:** testuser, analyst1, analyst2
- **Service Account:** service_account

### Appendix B: Test Scenarios

See **`docs/demo/DEMO_TEST_SCENARIOS.md`** for complete test scenarios.

**Quick Test Matrix:**

| User | Expected Visible Use Cases | Expected Visible Drafts |
|------|---------------------------|-------------------------|
| testuser | 0 (no roles) | 0 |
| analyst1 | 5 published | 2 (CSIRT team) |
| analyst2 | 5 published | 2 (CSIRT team) |
| uc_publisher | 5 published | 1 (Governance team) |
| corpus_manager | 5 published | 2 (Development team) |
| admin | 5 published | 5 (all teams) |

### Appendix C: Database Schema Diagram

```
┌────────────────────────────────────────────────────────────────┐
│                      RBAC V2 Schema                             │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  users                         user_roles                       │
│  ├─ id (PK)                    ├─ id (PK)                      │
│  ├─ username                   ├─ user_id (FK → users.id)      │
│  ├─ email                      ├─ role (TEXT)                  │
│  ├─ hashed_password            │   • System: admin, corpus_admin│
│  ├─ is_active                  │   • Grouping: threat_hunting  │
│  └─ ...                        │   • Teams: team:csirt_security│
│                                └─ ...                           │
│                                                                 │
│  use_cases                     role_use_case_assignments       │
│  ├─ id (PK)                    ├─ id (PK)                      │
│  ├─ use_case_id                ├─ role_name                    │
│  ├─ name                       ├─ use_case_id (FK → use_cases) │
│  ├─ lifecycle_state            ├─ is_active                    │
│  ├─ team_id (NEW)              └─ ...                          │
│  │   (NULL = published)                                        │
│  │   (team:xxx = draft)        role_collection_assignments (NEW)│
│  └─ ...                        ├─ id (PK)                      │
│                                ├─ role_name                    │
│  collections                   ├─ collection_id (FK)           │
│  ├─ id (PK)                    ├─ is_active                    │
│  ├─ name                       └─ ...                          │
│  ├─ is_published                                               │
│  └─ ...                                                        │

│                                                                 │
└────────────────────────────────────────────────────────────────┘

Visibility Rules:
• Published use cases (team_id = NULL): Visible to ALL users
• Draft use cases (team_id = team:xxx): Visible to team members ONLY

• Admins: See ALL use cases (all teams, all states)
```

### Appendix D: Execution Timeline

**Estimated timeline for complete implementation:**

| Phase | Tasks | Estimated Time | Dependencies |
|-------|-------|----------------|--------------|
| Phase 1: Init Script | db-refresh-001 | 1 hour | None |
| Phase 2: Seed Scripts | db-refresh-002 to 005 | 3 hours | Phase 1 complete |
| Phase 3: Automation | db-refresh-006 to 007 | 2 hours | Phase 2 complete |
| Phase 4: Documentation | db-refresh-008 to 010 | 2 hours | Can run parallel |
| Phase 5: Testing | db-refresh-011 to 012 | 2 hours | All phases complete |

**Total estimated time:** 10 hours (1.5 days)

### Appendix E: Quick Reference Commands

**Reset database for demo:**

```bash
cd $PROJECT_ROOT
bash ops/operations/reset_demo_database.sh
```

**Verify demo setup:**

```bash
bash ops/operations/verify_demo_setup.sh
```

**Manual verification queries:**

```sql
-- User count
SELECT COUNT(*) FROM users; -- Should be 12

-- Team memberships
SELECT u.username, ur.role
FROM user_roles ur
JOIN users u ON ur.user_id = u.id
WHERE ur.role LIKE 'team:%'
ORDER BY ur.role, u.username;

-- Use case inventory
SELECT
    lifecycle_state,
    team_id,
    COUNT(*) as count
FROM use_cases
GROUP BY lifecycle_state, team_id
ORDER BY lifecycle_state, team_id;

-- Draft use cases by team
SELECT
    team_id,
    use_case_id,
    name
FROM use_cases
WHERE lifecycle_state = 'draft'
ORDER BY team_id, use_case_id;
```

---

## Approval

**Plan Status:** ✅ READY FOR REVIEW

**Reviewers:**

- [ ] Product Owner
- [ ] Development Team
- [ ] Demo Presentation Team

**Approval Date:** _______________

**Implementation Start Date:** _______________

---

**END OF DATABASE_REFRESH_PLAN.md**
