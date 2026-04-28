# Demo User Credentials & Access Guide

**Status:** READY FOR DEMO
**Last Updated:** 2025-12-10
**Related:** `docs/development/plans/DATABASE_REFRESH_PLAN.md`, DEMO_TEST_SCENARIOS.md
**Security Level:** 🔒 DEMO ONLY - NOT FOR PRODUCTION

---

## ⚠️ Security Warning

**ALL users in this demo environment share the default password:**

```
Password: adminpassword
```

**This password MUST be changed in production environments!**

The bcrypt hash used in seed scripts:

```
$2b$12$tfGexjAaqWbPYand3DPqouy9d5adFeksdPVk1aOQInD/XhdCwZY/6
```

---

## Quick Reference

### Login Credentials

**All users:**

- **Password:** `adminpassword`
- **Authentication:** JWT-based
- **Session Duration:** 24 hours (configurable)

### User Categories

| Category | Count | System Roles | Purpose |
|----------|-------|--------------|---------|
| **Administrators** | 2 | admin | Full system access |
| **Corpus Administrators** | 2 | corpus_admin | Document/collection management |
| **Developers** | 2 | **developer** | **Team-scoped use case development** |
| **Use Case Administrators** | 1 | **use_case_admin** | **Use case super admin (all teams)** |
| **Tools Administrators** | 1 | **tools_admin** | **MCP/tools management** |
| **Role Administrators** | 1 | **role_admin** | **Role management** |
| **Publishers** | 2 | use_case_publisher | Use case approval workflow |
| **Conversation Users** | 2 | conversations_privileged | Multi-turn conversation access |
| **Standard Users** | 2 | user | Base users (role-based access only) |
| **Service Accounts** | 1 | service | API automation |

**Total Users:** 17 (was 6 originally, +11 new for complete role coverage)

---

## User Roster

### 1. Administrators (Full Access)

#### User: `admin`

```yaml
Username: admin
Password: adminpassword
Full Name: System Administrator
Email: admin@example.com
System Role: admin
Center ID: headquarters
Team Memberships: None
```

**Capabilities:**

- ✅ Full system access (superuser)
- ✅ All admin panels
- ✅ User management
- ✅ System configuration
- ✅ Sees ALL use cases (all teams, all states)
- ✅ Sees ALL document collections
- ✅ Can edit ANY use case
- ✅ Can manage ALL resources

**Use for:**

- System administration demonstrations
- Full-access scenarios
- Override/recovery operations

---

#### User: `admin2`

```yaml
Username: admin2
Password: adminpassword
Full Name: Admin 2
Email: admin2@example.com
System Role: admin
Center ID: headquarters
Team Memberships: None
```

**Capabilities:**

- ✅ Identical to `admin`
- ✅ Full system access

**Use for:**

- Multi-admin demonstrations
- Admin collaboration scenarios

---

### 2. Corpus Administrators (Document Management)

#### User: `corpus_manager`

```yaml
Username: corpus_manager
Password: adminpassword
Full Name: Corpus Manager
Email: corpus@example.com
System Role: corpus_admin
Center ID: headquarters
Team Memberships: team:development
```

**Capabilities:**

- ✅ Manage documents and collections
- ✅ Upload/delete documents
- ✅ Create/modify collections
- ✅ Sees ALL published documents
- ✅ Access corpus management UI
- ✅ Sees published use cases (for reference)
- ✅ Can view Development team's draft use cases
- ❌ Cannot approve/publish use cases
- ❌ Cannot access system administration

**Use for:**

- Document management demonstrations
- Collection organization
- RAG corpus development
- Team collaboration (development team)

---

#### User: `corpus_dev`

```yaml
Username: corpus_dev
Password: adminpassword
Full Name: Corpus Developer
Email: corpus_dev@example.com
System Role: corpus_admin
Center ID: development_team
Team Memberships: team:development
```

**Capabilities:**

- ✅ Identical to `corpus_manager`
- ✅ Development team member

**Use for:**

- Multi-user corpus management
- Development team scenarios

---

### 3. Developers (Team-Scoped Use Case Development)

#### User: `developer1`

```yaml
Username: developer1
Password: adminpassword
Full Name: Developer 1
Email: developer1@example.com
System Role: developer
Center ID: development_team
Team Memberships: team:development
```

**Capabilities:**

- ✅ Create new use cases (assigned to own team)
- ✅ Edit own draft use cases
- ✅ View Development team's draft use cases
- ✅ View ALL published use cases
- ✅ Submit use cases for review
- ✅ **TEAM-SCOPED visibility** (sees only own team's drafts)
- ❌ Cannot see other teams' drafts (CSIRT, Governance)
- ❌ Cannot approve/publish use cases (review only)
- ❌ Cannot manage documents or collections

**Use for:**

- **Team-scoped development demonstrations** ⭐ PRIMARY USE CASE
- Use case creation workflows
- Team collaboration scenarios
- Team isolation verification (cannot see other teams' drafts)

---

#### User: `developer2`

```yaml
Username: developer2
Password: adminpassword
Full Name: Developer 2
Email: developer2@example.com
System Role: developer
Center ID: soc_team
Team Memberships: team:csirt_security
```

**Capabilities:**

- ✅ Identical to `developer1`
- ✅ CSIRT Security team member (different team)
- ✅ Sees CSIRT team drafts only
- ❌ Cannot see Development or Governance team drafts

**Use for:**

- Cross-team isolation demonstrations
- Multi-developer scenarios
- Team-based access control verification
- Demonstrates that developers in different teams cannot see each other's drafts

---

### 4. Use Case Administrators (Super Admin - All Teams)

#### User: `uc_admin`
```yaml
Username: uc_admin
Password: adminpassword
Full Name: Use Case Admin
Email: uc_admin@example.com
System Role: use_case_admin
Center ID: headquarters
Team Memberships: None (sees all teams)
```

**Capabilities:**
- ✅ **SUPER USER** for use case development
- ✅ Create use cases (any team)
- ✅ Edit ANY use case (regardless of creator or team)
- ✅ View ALL use cases (ALL teams, ALL states)
- ✅ Submit, approve, and publish use cases
- ✅ Global visibility across all teams
- ✅ Override team boundaries
- ❌ Not full system admin (cannot manage users/system config)

**Use for:**
- **Use case governance** ⭐ PRIMARY USE CASE
- Cross-team oversight
- Use case quality assurance
- Emergency use case fixes
- Demonstrates super admin role different from developer

**Key Distinction from Developer:**
- `developer` role: Team-scoped (sees only own team's drafts)
- `use_case_admin` role: Global visibility (sees ALL teams' drafts)

---

### 5. Tools Administrators (MCP/Tools Management)

#### User: `tools_manager`
```yaml
Username: tools_manager
Password: adminpassword
Full Name: Tools Manager
Email: tools_manager@example.com
System Role: tools_admin
Center ID: headquarters
Team Memberships: None
```

**Capabilities:**
- ✅ Manage MCP (Model Context Protocol) servers
- ✅ Register/configure tools
- ✅ Update tool schemas
- ✅ Enable/disable tools
- ✅ View all tool registrations
- ✅ Access tools admin UI panels
- ❌ Cannot create use cases
- ❌ Cannot manage users

**Use for:**
- **MCP/tools administration** ⭐ PRIMARY USE CASE
- Tool registration workflows
- Tool schema management
- Demonstrates tools-specific admin role

---

### 6. Role Administrators (Role Management)

#### User: `role_manager`
```yaml
Username: role_manager
Password: adminpassword
Full Name: Role Manager
Email: role_manager@example.com
System Role: role_admin
Center ID: headquarters
Team Memberships: None
```

**Capabilities:**
- ✅ Create grouping roles (Tier 2)
- ✅ Assign use cases to roles
- ✅ Assign collections to roles
- ✅ Assign users to roles
- ✅ Manage developer teams
- ✅ View all role assignments
- ✅ Access role management UI
- ❌ Cannot create system roles (those are hardcoded)
- ❌ Cannot create use cases
- ❌ Cannot manage documents

**Use for:**
- **Role-based access control management** ⭐ PRIMARY USE CASE
- Grouping role creation
- User-to-role assignments
- Demonstrates delegated role administration

---

### 7. Use Case Publishers (Approval Workflow)

#### User: `uc_publisher`

```yaml
Username: uc_publisher
Password: adminpassword
Full Name: Use Case Publisher
Email: publisher@example.com
System Role: use_case_publisher
Center ID: headquarters
Team Memberships: team:soc_governance
```

**Capabilities:**

- ✅ Review draft use cases
- ✅ Approve use cases for publishing
- ✅ Publish approved use cases
- ✅ Archive use cases
- ✅ Sees SOC Governance team's drafts
- ✅ Sees ALL published use cases
- ✅ Access use case governance UI
- ❌ Cannot create new use cases (review only)
- ❌ Cannot manage documents
- ❌ Cannot edit published use cases

**Use for:**

- Use case approval workflow demonstrations
- Governance scenarios
- Review process walkthroughs
- Team-based draft visibility

---

#### User: `publisher2`

```yaml
Username: publisher2
Password: adminpassword
Full Name: Publisher 2
Email: publisher2@example.com
System Role: use_case_publisher
Center ID: governance_team
Team Memberships: team:soc_governance
```

**Capabilities:**

- ✅ Identical to `uc_publisher`
- ✅ SOC Governance team member

**Use for:**

- Multi-reviewer scenarios
- Collaborative governance
- Approval escalation demonstrations

---

### 5. Conversation-Privileged Users

#### User: `conv_analyst`

```yaml
Username: conv_analyst
Password: adminpassword
Full Name: Conversations Analyst
Email: conv_analyst@example.com
System Role: conversations_privileged
Center ID: soc_team
Team Memberships: team:csirt_security
```

**Capabilities:**

- ✅ Access multi-turn conversation interface
- ✅ Execute use cases via conversation mode
- ✅ Sees CSIRT Security team's drafts
- ✅ Sees ALL published use cases
- ✅ Can test/use drafts in conversation mode
- ❌ Cannot create/edit use cases
- ❌ Cannot manage documents
- ❌ Limited admin access

**Use for:**

- Conversation interface demonstrations
- Multi-turn interaction scenarios
- Team draft testing
- CSIRT team workflows

---

#### User: `analyst_conv`

```yaml
Username: analyst_conv
Password: adminpassword
Full Name: Analyst Conversations
Email: analyst_conv@example.com
System Role: conversations_privileged
Center ID: soc_team
Team Memberships: None
```

**Capabilities:**

- ✅ Access multi-turn conversation interface
- ✅ Execute published use cases only
- ❌ No team membership (sees no drafts)

**Use for:**

- Conversation-only user demonstrations
- Limited access scenarios

---

### 6. Standard Users (Role-Based Access)

#### User: `analyst1`

```yaml
Username: analyst1
Password: adminpassword
Full Name: SOC Analyst 1
Email: analyst1@example.com
System Role: user
Center ID: soc_team
Team Memberships: team:csirt_security
```

**Capabilities:**

- ✅ Sees published use cases (requires grouping role assignment)
- ✅ Sees CSIRT Security team's drafts
- ✅ Can view team members' work
- ❌ Base user role (no inherent access)
- ❌ Cannot create/edit use cases
- ❌ Cannot manage documents
- ❌ No admin access

**Use for:**

- **Team isolation demonstrations** ⭐ PRIMARY USE CASE
- Standard end-user scenarios
- RBAC access control demonstrations
- Team collaboration visibility

---

#### User: `analyst2`

```yaml
Username: analyst2
Password: adminpassword
Full Name: SOC Analyst 2
Email: analyst2@example.com
System Role: user
Center ID: soc_team
Team Memberships: team:csirt_security
```

**Capabilities:**

- ✅ Identical to `analyst1`
- ✅ CSIRT Security team member

**Use for:**

- Multi-user team scenarios
- Collaboration demonstrations
- Team isolation verification

---

#### User: `testuser`

```yaml
Username: testuser
Password: adminpassword
Full Name: Test User
Email: testuser@example.com
System Role: user
Center ID: test_center
Team Memberships: None
```

**Capabilities:**

- ✅ Can log in successfully
- ✅ Can access dashboard
- ❌ **Sees NO use cases** (no grouping roles assigned)
- ❌ **Sees NO collections** (no access grants)
- ❌ Cannot create/edit anything
- ❌ No admin access

**Use for:**

- **Default-deny access control demonstration** ⭐ PRIMARY USE CASE
- Empty state UI testing
- "No access" scenarios
- Security baseline verification

---

### 7. Service Accounts (API Automation)

#### User: `service_account`

```yaml
Username: service_account
Password: adminpassword
Full Name: Service Account
Email: service@example.com
System Role: service
Center ID: api_automation
Team Memberships: None
```

**Capabilities:**

- ✅ API authentication (JWT tokens)
- ✅ Execute use cases programmatically
- ✅ Access granted via grouping roles
- ❌ No UI access (API only)
- ❌ Cannot manage resources

**Use for:**

- API automation demonstrations
- Machine-to-machine scenarios
- Integration testing

---

## Team Membership Matrix

| Team ID | Display Name | Members | Draft Use Cases | Purpose |
|---------|--------------|---------|-----------------|---------|
| **team:csirt_security** | CSIRT Security Team | **developer2**, analyst1, analyst2, conv_analyst | 2 | Incident response use cases |
| **team:soc_governance** | SOC Governance Team | uc_publisher, publisher2 | 1 | Compliance/governance use cases |
| **team:development** | Development Team | **developer1**, corpus_manager, corpus_dev | 2 | Development/testing use cases |

---

## Access Control Matrix

### Use Case Visibility

| User | Published Use Cases | Draft Use Cases | Edit Permissions |
|------|---------------------|-----------------|------------------|
| **admin** | ALL (5) | ALL teams (5) | ALL |
| **admin2** | ALL (5) | ALL teams (5) | ALL |
| **corpus_manager** | ALL (5) | Development team (2) | Own drafts only |
| **corpus_dev** | ALL (5) | Development team (2) | Own drafts only |
| **developer1** | ALL (5) | Development team (2) | Own drafts only |
| **developer2** | ALL (5) | CSIRT team (2) | Own drafts only |
| **uc_publisher** | ALL (5) | Governance team (1) | Own drafts only |
| **publisher2** | ALL (5) | Governance team (1) | Own drafts only |
| **conv_analyst** | ALL (5) | CSIRT team (2) | Own drafts only |
| **analyst_conv** | ALL (5) | None (0) | None |
| **analyst1** | ALL (5) | CSIRT team (2) | None |
| **analyst2** | ALL (5) | CSIRT team (2) | None |
| **testuser** | None (0) ⚠️ | None (0) | None |
| **service_account** | Via grouping roles | None | None |

**Key Points:**

- ⚠️ `testuser` requires grouping role assignments to see ANY use cases
- Published use cases visible to all authenticated users with appropriate roles
- Draft use cases isolated by team membership
- Edit permissions restricted to creators (developers) or admins

---

## Role Assignment Guide

### How to Grant Access

#### Option 1: System Role Assignment (Tier 1)

**Via SQL:**

```sql
-- Assign system role to user
INSERT INTO user_roles (user_id, role, granted_by, granted_at, metadata)
VALUES (
    (SELECT id FROM users WHERE username = 'username'),
    'admin',  -- or corpus_admin, use_case_publisher, etc.
    NULL,
    NOW(),
    '{"granted_reason": "Demo purposes"}'::jsonb
);
```

**Via UI:**

- Navigate to Admin → User Management
- Select user
- Toggle system role checkboxes

#### Option 2: Grouping Role Assignment (Tier 2)

**Via SQL:**

```sql
-- Assign grouping role to user (grants use case access)
INSERT INTO user_roles (user_id, role, granted_by, granted_at, metadata)
VALUES (
    (SELECT id FROM users WHERE username = 'testuser'),
    'threat_hunting',  -- or incident_response, compliance_review, etc.
    (SELECT id FROM users WHERE username = 'admin'),
    NOW(),
    '{"granted_reason": "Threat hunting team member"}'::jsonb
);
```

**Via UI:**

- Navigate to Admin → Role Management → Grouping Roles
- Select role
- Add user to role

#### Option 3: Team Membership (Tier 3)

**Via SQL:**

```sql
-- Assign team membership to user (grants draft visibility)
INSERT INTO user_roles (user_id, role, granted_by, granted_at, metadata)
VALUES (
    (SELECT id FROM users WHERE username = 'analyst1'),
    'team:csirt_security',
    NULL,
    NOW(),
    '{"seed_script": "008", "team_display_name": "CSIRT Security Team"}'::jsonb
);
```

**Via UI:**

- Navigate to Admin → Developer Teams
- Select team
- Add user to team

---

## Demo Scenarios by User

### Scenario 1: Full Access (Admin)

**User:** `admin` or `admin2`

**Walkthrough:**

1. Login → See full dashboard
2. Navigate to Use Case Management
3. **Verify:** See 10 use cases (5 published + 5 draft from all teams)
4. Navigate to Document Management
5. **Verify:** See all collections
6. Navigate to Admin panels
7. **Verify:** Access to all admin features

**Expected Result:** ✅ Full visibility and control

---

### Scenario 2: Team Isolation (Developer)

**User:** `analyst1` (CSIRT team member)

**Walkthrough:**

1. Login → See dashboard
2. Navigate to Use Cases
3. **Verify:** See 7 use cases:
   - 5 published (all users)
   - 2 CSIRT team drafts
4. **Verify:** Do NOT see:
   - Governance team draft (1)
   - Development team drafts (2)
5. Attempt to view other team's draft
6. **Expected Result:** ❌ 403 Forbidden or not listed

**Expected Result:** ✅ Team isolation working correctly

---

### Scenario 3: Default-Deny Access (Base User)

**User:** `testuser` (no roles)

**Walkthrough:**

1. Login → See dashboard
2. Navigate to Use Cases
3. **Verify:** Empty list (no use cases visible)
4. **Verify:** Message: "No use cases available. Contact administrator."
5. Navigate to Documents
6. **Verify:** Empty list (no collections visible)
7. Navigate to Admin (should not appear in menu)
8. **Expected Result:** ❌ Cannot access admin features

**Expected Result:** ✅ Default-deny access model working

---

### Scenario 4: Approval Workflow (Publisher)

**User:** `uc_publisher` (SOC Governance team)

**Walkthrough:**

1. Login → See dashboard
2. Navigate to Use Case Management
3. **Verify:** See governance team draft: `team_uc_gov_001`
4. Open draft use case
5. Click "Submit for Review"
6. **Verify:** Lifecycle state changes to `review`
7. As publisher, click "Approve"
8. **Verify:** Use case can now be published
9. Click "Publish"
10. **Verify:**
    - `team_id` set to NULL
    - `lifecycle_state` = published
    - Now visible to all users

**Expected Result:** ✅ Approval workflow complete

---

### Scenario 5: Corpus Management

**User:** `corpus_manager` (Development team)

**Walkthrough:**

1. Login → See dashboard
2. Navigate to Document Management
3. Upload test document
4. Create new collection
5. Assign document to collection
6. **Verify:** Collection created successfully
7. Navigate to Use Cases
8. **Verify:** See development team drafts (2)
9. **Verify:** Can reference collections in use case config

**Expected Result:** ✅ Document management working

---

## Troubleshooting

### User Cannot Log In

**Symptoms:**

- Invalid credentials error
- Authentication failure

**Checks:**

```sql
-- Verify user exists
SELECT username, email, is_active FROM users WHERE username = 'username';

-- Verify password hash
SELECT username, hashed_password FROM users WHERE username = 'username';
-- Should be: $2b$12$tfGexjAaqWbPYand3DPqouy9d5adFeksdPVk1aOQInD/XhdCwZY/6

-- Verify user is active
SELECT username, is_active FROM users WHERE username = 'username';
-- Should be: TRUE
```

**Solutions:**

- Ensure password is exactly `adminpassword`
- Verify `is_active = TRUE`
- Check JWT secret configuration

---

### User Sees Empty Dashboard

**Symptoms:**

- No use cases visible
- No collections visible
- UI shows "No access" messages

**Expected Behavior:**

- **If user = `testuser`:** This is CORRECT (default-deny)
- **If user has roles:** This is a problem

**Checks:**

```sql
-- Verify user roles
SELECT u.username, ur.role
FROM users u
LEFT JOIN user_roles ur ON u.id = ur.user_id
WHERE u.username = 'username';

-- Verify use case assignments
SELECT
    u.username,
    uc.name,
    uc.lifecycle_state,
    uc.team_id
FROM users u
JOIN user_roles ur ON u.id = ur.user_id
LEFT JOIN role_use_case_assignments ruca ON ur.role = ruca.role_name
LEFT JOIN use_cases uc ON ruca.use_case_id = uc.id
WHERE u.username = 'username';
```

**Solutions:**

- Assign grouping roles to user (for use case access)
- Verify published use cases have `team_id = NULL`
- Verify user is in correct team (for draft visibility)

---

### User Sees Wrong Team's Drafts

**Symptoms:**

- Team member sees other team's draft use cases
- Team isolation not working

**This is a critical RBAC bug!**

**Checks:**

```sql
-- Verify user's teams
SELECT u.username, ur.role AS team
FROM users u
JOIN user_roles ur ON u.id = ur.user_id
WHERE u.username = 'username'
  AND ur.role LIKE 'team:%';

-- Verify draft use case team assignments
SELECT
    use_case_id,
    name,
    lifecycle_state,
    team_id
FROM use_cases
WHERE lifecycle_state = 'draft';

-- Check if user can query other team's draft
SELECT
    uc.use_case_id,
    uc.name,
    uc.team_id,
    ur.role AS user_team
FROM use_cases uc
CROSS JOIN user_roles ur
WHERE ur.user_id = (SELECT id FROM users WHERE username = 'analyst1')
  AND ur.role LIKE 'team:%'
  AND uc.lifecycle_state = 'draft'
  AND uc.team_id != ur.role;
-- Should return ZERO rows
```

**Solutions:**

- Verify backend RBAC logic (check `get_accessible_use_cases` function)
- Ensure drafts have correct `team_id` set
- Test team isolation logic

---

## Security Notes

### Password Management

**Demo Environment:**

- ✅ Single shared password acceptable for demo
- ✅ Bcrypt hashing in database
- ✅ Password never transmitted/stored in plaintext

**Production Environment:**

- ⚠️ **Unique passwords per user REQUIRED**
- ⚠️ **Change all default passwords immediately**
- ⚠️ **Implement password complexity requirements**
- ⚠️ **Enable password expiration policies**
- ⚠️ **Use external identity provider (LDAP/SAML/OAuth) if available**

### JWT Token Management

**Configuration:**

- Token expiration: 24 hours (configurable)
- Refresh token support: Yes
- Token includes: user_id, username, roles

**Security:**

- JWT secret MUST be changed from default in production
- Use strong random secret (256+ bits entropy)
- Rotate secrets periodically
- Implement token revocation for compromised accounts

---

## Related Documentation

- **`docs/development/plans/DATABASE_REFRESH_PLAN.md`** - Complete setup process
- **DEMO_TEST_SCENARIOS.md** - Manual test walkthroughs
- **ADR-060** - RBAC V2 architecture
- **`docs/admin/USER_ROLES_GUIDE.md`** - Role management guide
- **`docs/api/authentication.md`** - Authentication API reference

---

**END OF DEMO_CREDENTIALS.MD**
