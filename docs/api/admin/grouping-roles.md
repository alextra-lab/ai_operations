# Grouping Roles Management API (RBAC V2)

**Version:** 2.0.0
**Last Updated:** 2025-12-08
**Authorization:** Admin or role_admin
**Base Path:** `/api/v1/admin/grouping-roles`
**Status:** ✅ Production Ready

---

## Overview

Admin API for managing use case grouping roles (RBAC V2). Grouping roles control access to published use cases and document collections. This implements the two-tier RBAC model from ADR-060, where grouping roles (Tier 2) provide resource-level access control.

**Architecture:** Implements [ADR-060: Corrected RBAC Architecture](../../development/adrs/ADR-060-Corrected-RBAC-Architecture.md)

**Key Concepts:**

- **Grouping Roles:** Dynamic roles that grant access to specific use cases and collections (e.g., `threat_hunting`, `incident_response`)
- **System Roles:** Predefined capability roles (admin, corpus_admin, use_case_admin, tools_admin, conversations, role_admin) - cannot be created via this API
- **Teams:** Developer teams with prefix `team:` - cannot be created via this API (use Developer Teams API)

**Role Types:**

- **System Roles (Tier 1):** `admin`, `corpus_admin`, `use_case_admin`, `tools_admin`, `conversations`, `role_admin`
- **Grouping Roles (Tier 2):** `threat_hunting`, `incident_response`, `compliance_review`, etc. (user-defined)
- **Teams (Tier 3):** `team:csirt_security`, `team:soc_governance`, etc. (use Developer Teams API)

---

## Authentication

All endpoints require **admin or role_admin** privileges.

```bash
Authorization: Bearer <access_token>
```

**Get Admin Token:**

```bash
TOKEN=$(curl -s -X POST "http://localhost:8006/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin" \
  -d "password=adminpassword" | jq -r '.access_token')
```

---

## Endpoints

### 1. List Grouping Roles

**GET** `/api/v1/admin/grouping-roles`

List all grouping roles with user, use case, and collection counts.

**Authorization:** Admin or role_admin

**Response:** 200 OK

```json
[
  {
    "role_name": "threat_hunting",
    "user_count": 5,
    "use_case_count": 12,
    "collection_count": 3
  },
  {
    "role_name": "incident_response",
    "user_count": 3,
    "use_case_count": 8,
    "collection_count": 2
  }
]
```

**Example:**

```bash
curl -X GET "http://localhost:8006/api/v1/admin/grouping-roles" \
  -H "Authorization: Bearer $TOKEN"
```

**Notes:**

- Returns only grouping roles (excludes system roles and teams)
- Counts reflect active assignments only
- Empty list if no grouping roles exist

---

### 2. Create Grouping Role

**POST** `/api/v1/admin/grouping-roles`

Register a new grouping role. This operation is idempotent - if the role already exists, returns existing role information.

**Authorization:** Admin or role_admin

**Request Body:**

```json
{
  "role_name": "threat_hunting"
}
```

**Path Validation:**

- Must start with lowercase letter
- Can contain: lowercase letters, digits, underscore, hyphen
- Length: 2-50 characters
- Pattern: `^[a-z][a-z0-9_-]{1,49}$`
- Cannot be a system role name
- Cannot start with `team:` prefix

**Response:** 201 Created

```json
{
  "role_name": "threat_hunting",
  "created_by": "8e518f31-9e9b-4116-835c-efb3ad3bfa9a",
  "created_at": "2025-12-08T14:30:00.000000Z"
}
```

**Example:**

```bash
curl -X POST "http://localhost:8006/api/v1/admin/grouping-roles" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "role_name": "threat_hunting"
  }'
```

**Behavior:**

- Creates an anchor membership for the creator (ensures role exists in system)
- If role already exists, returns existing role information
- Role becomes available for use case and collection assignments

**Error Responses:**

- `400 Bad Request`: Invalid role name format, system role name, or team prefix
- `403 Forbidden`: Not admin or role_admin

---

### 3. Delete Grouping Role

**DELETE** `/api/v1/admin/grouping-roles/{role_name}`

Delete a grouping role and all its assignments. This operation:

- Removes all user memberships to this role
- Removes all use case assignments to this role
- Removes all collection assignments to this role

**Authorization:** Admin or role_admin

**Path Parameters:**

- `role_name` (string, required) - Grouping role name to delete

**Response:** 204 No Content

**Example:**

```bash
curl -X DELETE "http://localhost:8006/api/v1/admin/grouping-roles/threat_hunting" \
  -H "Authorization: Bearer $TOKEN"
```

**Error Responses:**

- `400 Bad Request`: Attempting to delete system role or team
- `403 Forbidden`: Not admin or role_admin
- `404 Not Found`: Role does not exist (no-op, returns 204)

**Warning:** This operation is irreversible. All users will lose access to use cases and collections assigned to this role.

---

## Role Name Validation

**Format Rules:**

- Must start with lowercase letter
- Can contain: lowercase letters, digits, underscore, hyphen
- Length: 2-50 characters
- Pattern: `^[a-z][a-z0-9_-]{1,49}$`

**Valid Examples:**
✅ `threat_hunting`, `incident_response`, `compliance_review`, `soc_tier1`, `hr-manager`

**Invalid Examples:**
❌ `ThreatHunting` (uppercase)
❌ `1threat` (starts with digit)
❌ `threat hunting` (space)
❌ `a` (too short)
❌ `admin` (system role - cannot create)
❌ `team:csirt` (team prefix - use Developer Teams API)

---

## Workflow Examples

### Example 1: Create Threat Hunting Role

```bash
# 1. Create grouping role
curl -X POST "http://localhost:8006/api/v1/admin/grouping-roles" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role_name": "threat_hunting"}'

# 2. Assign users to role (via User Management API)
# 3. Assign use cases to role (via Role Use Case Management API)
# 4. Assign collections to role (via Role Collection Management API)
```

### Example 2: List All Grouping Roles

```bash
curl -X GET "http://localhost:8006/api/v1/admin/grouping-roles" \
  -H "Authorization: Bearer $TOKEN" | jq '.[] | select(.user_count > 0)'
```

### Example 3: Clean Up Unused Role

```bash
# List roles with no users
curl -X GET "http://localhost:8006/api/v1/admin/grouping-roles" \
  -H "Authorization: Bearer $TOKEN" | jq '.[] | select(.user_count == 0)'

# Delete unused role
curl -X DELETE "http://localhost:8006/api/v1/admin/grouping-roles/unused_role" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Integration with Other APIs

### Assign Use Cases to Role

Use the [Role Use Case Management API](./role-use-case-management.md):

```bash
POST /admin/roles/{role_name}/use-cases
```

### Assign Collections to Role

Use the [Role Collection Management API](./role-use-case-management.md#collection-assignments):

```bash
POST /admin/roles/{role_name}/collections
```

### Assign Users to Role

Use the User Management API or directly via database:

```sql
INSERT INTO user_roles (user_id, role, granted_by)
VALUES ('user-uuid', 'threat_hunting', 'admin-uuid');
```

---

## Error Handling

### 400 Bad Request

- Invalid role name format
- Attempting to create system role
- Attempting to create team (use Developer Teams API)
- Attempting to delete system role or team

### 403 Forbidden

- Non-admin/role_admin user attempting operation

### 500 Internal Server Error

- Database connection error
- Unexpected error (check logs)

---

## Best Practices

### 1. Use Descriptive Role Names

✅ Good: `threat_hunting`, `incident_response`, `compliance_review`
❌ Bad: `role1`, `temp`, `test`, `group1`

### 2. Plan Role Hierarchy

Create logical groupings:

- `soc_tier1`, `soc_tier2`, `soc_tier3` for tiered access
- `threat_hunting`, `incident_response` for functional teams
- `compliance_review`, `audit_access` for compliance teams

### 3. Document Role Purpose

Use metadata in assignments to document why roles were created and what they're used for.

### 4. Regular Cleanup

Periodically review and remove unused roles to maintain clean RBAC structure.

---

## See Also

- **[ADR-060: Corrected RBAC Architecture](../../development/adrs/ADR-060-Corrected-RBAC-Architecture.md)** - Architecture decision
- **[RBAC V2 Implementation Plan](../../development/plans/RBAC_V2_IMPLEMENTATION_PLAN.md)** - Implementation details
- **[Role Use Case Management API](./role-use-case-management.md)** - Assign use cases to roles
- **[Developer Teams API](./developer-teams.md)** - Manage developer teams
- **[User Management API](../authentication.md)** - Assign users to roles

---

**Last Updated:** 2025-12-08
**Maintainer:** AI Operations Platform Team
