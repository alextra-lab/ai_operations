# Role-Based Use Case Management API

**Version:** 2.0.0
**Last Updated:** 2025-12-08
**Authorization:** Admin or role_admin (collection endpoints)
**Base Path:** `/admin/roles`

---

## Overview

Admin API for managing role-based use case permissions. Allows administrators to assign use cases to roles, enabling scalable RBAC where users inherit access through role memberships.

**Architecture:** Implements ADR-041 (Role-Based Use Case Permissions)

**Key Concepts:**

- **Roles:** User roles (admin, analyst, developer, user, custom roles)
- **Use Cases:** Executable AI assistants with specific configurations
- **Assignments:** Map roles to use cases (users inherit access via role membership)

---

## Custom Roles Support ✅

**Dynamic Role System:**

- System includes predefined roles: `admin`, `analyst`, `developer`, `corpus_admin`, `user`, `service`
- **Custom roles fully supported:** Create any role name matching: `^[a-z][a-z0-9_-]{1,49}$`

**Examples of Custom Roles:**

- `legal_counsel` - For legal department
- `hr_manager` - For HR department
- `threat_hunter` - For advanced SOC analysts
- `soc_tier1`, `soc_tier2`, `soc_tier3` - Tiered access
- `compliance_officer`, `incident_responder`, `audit_reviewer`, etc.

**Workflow:**

1. Create role membership: `INSERT INTO user_roles (user_id, role) VALUES (...)`
2. Assign use cases to role: `POST /admin/roles/{role_name}/use-cases`
3. Users with that role automatically inherit access

---

## Endpoints

### 1. Assign Use Case to Role

**POST** `/admin/roles/{role_name}/use-cases`

Grants access to the specified use case for all users with the given role.

**Authorization:** Admin only

**Path Parameters:**

- `role_name` (string, required) - Role name (any custom role allowed)

**Request Body:**

```json
{
  "use_case_id": "289cba6d-a0c5-401e-856b-c7b19e89ac32",
  "expires_at": null,
  "metadata": {
    "reason": "Threat hunters need IOC enrichment",
    "approved_by": "security_lead",
    "ticket": "SEC-2024-042"
  }
}
```

**Response:** 201 Created

```json
{
  "id": "01d51dc8-89ca-4b95-a996-c0e4c0004b67",
  "role_name": "threat_hunter",
  "use_case_id": "289cba6d-a0c5-401e-856b-c7b19e89ac32",
  "use_case_name": "IOC Lookup",
  "granted_by": "8e518f31-9e9b-4116-835c-efb3ad3bfa9a",
  "granted_at": "2025-10-24T18:17:17.352309Z",
  "expires_at": null,
  "is_active": true,
  "metadata": {
    "reason": "Threat hunters need IOC enrichment"
  }
}
```

**Example:**

```bash
curl -X POST "http://localhost:8006/admin/roles/threat_hunter/use-cases" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "use_case_id": "289cba6d-a0c5-401e-856b-c7b19e89ac32",
    "metadata": {"reason": "Threat hunters need IOC enrichment"}
  }'
```

---

### 2. Revoke Use Case from Role

**DELETE** `/admin/roles/{role_name}/use-cases/{use_case_id}`

Removes access to the specified use case for all users with the given role.

**Authorization:** Admin only

**Path Parameters:**

- `role_name` (string, required) - Role name
- `use_case_id` (UUID, required) - Use case UUID

**Query Parameters:**

- `permanent` (boolean, default: false) - If true, permanently delete. If false, deactivate.

**Response:** 204 No Content

**Example:**

```bash
# Soft delete (deactivate)
curl -X DELETE "http://localhost:8006/admin/roles/threat_hunter/use-cases/289cba6d-a0c5-401e-856b-c7b19e89ac32" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Permanent deletion
curl -X DELETE "http://localhost:8006/admin/roles/threat_hunter/use-cases/289cba6d-a0c5-401e-856b-c7b19e89ac32?permanent=true" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

### 3. List Role's Use Cases

**GET** `/admin/roles/{role_name}/use-cases`

Get all use cases assigned to a role.

**Authorization:** Admin only

**Path Parameters:**

- `role_name` (string, required) - Role name

**Query Parameters:**

- `include_inactive` (boolean, default: false) - Include inactive assignments

**Response:** 200 OK

```json
{
  "role_name": "threat_hunter",
  "total": 1,
  "active": 1,
  "assignments": [
    {
      "id": "01d51dc8-89ca-4b95-a996-c0e4c0004b67",
      "role_name": "threat_hunter",
      "use_case_id": "289cba6d-a0c5-401e-856b-c7b19e89ac32",
      "use_case_name": "IOC Lookup",
      "granted_by": "8e518f31-9e9b-4116-835c-efb3ad3bfa9a",
      "granted_at": "2025-10-24T18:17:17.352309Z",
      "expires_at": null,
      "is_active": true,
      "metadata": {
        "reason": "Threat hunters need IOC enrichment"
      }
    }
  ]
}
```

**Example:**

```bash
curl -X GET "http://localhost:8006/admin/roles/threat_hunter/use-cases" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

### 4. List Use Case's Roles

**GET** `/admin/roles/use-cases/{use_case_id}/roles`

Get all roles that have access to a use case.

**Authorization:** Admin only

**Path Parameters:**

- `use_case_id` (UUID, required) - Use case UUID

**Response:** 200 OK

```json
[
  "admin",
  "analyst",
  "developer",
  "threat_hunter"
]
```

**Note:** Admin role always included (implicit access via admin override)

**Example:**

```bash
curl -X GET "http://localhost:8006/admin/roles/use-cases/289cba6d-a0c5-401e-856b-c7b19e89ac32/roles" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

## Collection Assignments (RBAC V2)

**Version:** 2.0.0 (Added December 8, 2025)
**Architecture:** Implements [ADR-060: Corrected RBAC Architecture](../../development/adrs/ADR-060-Corrected-RBAC-Architecture.md)

Collection assignments allow administrators to grant document collection access to roles. Users inherit collection access through role memberships, enabling fine-grained control over which roles can access which document collections.

**Key Concepts:**

- **Collection Access:** Users with grouping roles can only access collections assigned to those roles
- **System Roles:** System roles (`admin`, `corpus_admin`) have implicit access to all collections
- **Grouping Roles:** Grouping roles require explicit collection assignments
- **Default-Deny:** Users without roles or with roles that have no collection assignments see no collections

### 5. Assign Collection to Role

**POST** `/admin/roles/{role_name}/collections`

Grants access to the specified collection for all users with the given role.

**Authorization:** Admin or role_admin

**Path Parameters:**

- `role_name` (string, required) - Role name (grouping role, not system role)

**Request Body:**

```json
{
  "collection_id": "289cba6d-a0c5-401e-856b-c7b19e89ac32",
  "expires_at": null,
  "metadata": {
    "reason": "Threat hunters need access to IOC collection",
    "approved_by": "security_lead",
    "ticket": "SEC-2024-042"
  }
}
```

**Response:** 201 Created

```json
{
  "id": "01d51dc8-89ca-4b95-a996-c0e4c0004b67",
  "role_name": "threat_hunting",
  "collection_id": "289cba6d-a0c5-401e-856b-c7b19e89ac32",
  "granted_by": "8e518f31-9e9b-4116-835c-efb3ad3bfa9a",
  "granted_at": "2025-12-08T18:17:17.352309Z",
  "expires_at": null,
  "is_active": true,
  "metadata": {
    "reason": "Threat hunters need access to IOC collection"
  }
}
```

**Example:**

```bash
curl -X POST "http://localhost:8006/admin/roles/threat_hunting/collections" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_id": "289cba6d-a0c5-401e-856b-c7b19e89ac32",
    "metadata": {"reason": "Threat hunters need access to IOC collection"}
  }'
```

**Notes:**

- System roles (`admin`, `corpus_admin`, `use_case_admin`, `tools_admin`, `conversations`, `role_admin`) already have implicit access to all collections
- Attempting to assign collections to system roles returns `400 Bad Request`
- Operation is idempotent - if assignment exists, updates it

**Error Responses:**

- `400 Bad Request`: System role specified (system roles have implicit access)
- `403 Forbidden`: Not admin or role_admin
- `404 Not Found`: Collection does not exist

---

### 6. Revoke Collection from Role

**DELETE** `/admin/roles/{role_name}/collections/{collection_id}`

Removes access to the specified collection for all users with the given role.

**Authorization:** Admin or role_admin

**Path Parameters:**

- `role_name` (string, required) - Role name
- `collection_id` (UUID, required) - Collection UUID

**Query Parameters:**

- `permanent` (boolean, default: false) - If true, permanently delete. If false, deactivate.

**Response:** 204 No Content

**Example:**

```bash
# Soft delete (deactivate)
curl -X DELETE "http://localhost:8006/admin/roles/threat_hunting/collections/289cba6d-a0c5-401e-856b-c7b19e89ac32" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Permanent deletion
curl -X DELETE "http://localhost:8006/admin/roles/threat_hunting/collections/289cba6d-a0c5-401e-856b-c7b19e89ac32?permanent=true" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Error Responses:**

- `403 Forbidden`: Not admin or role_admin
- `404 Not Found`: Assignment not found

---

### 7. List Role's Collections

**GET** `/admin/roles/{role_name}/collections`

Get all collections assigned to a role.

**Authorization:** Admin or role_admin

**Path Parameters:**

- `role_name` (string, required) - Role name

**Query Parameters:**

- `include_inactive` (boolean, default: false) - Include inactive assignments

**Response:** 200 OK

```json
{
  "role_name": "threat_hunting",
  "total": 2,
  "active": 2,
  "assignments": [
    {
      "id": "01d51dc8-89ca-4b95-a996-c0e4c0004b67",
      "role_name": "threat_hunting",
      "collection_id": "289cba6d-a0c5-401e-856b-c7b19e89ac32",
      "granted_by": "8e518f31-9e9b-4116-835c-efb3ad3bfa9a",
      "granted_at": "2025-12-08T18:17:17.352309Z",
      "expires_at": null,
      "is_active": true,
      "metadata": {
        "reason": "Threat hunters need access to IOC collection"
      }
    },
    {
      "id": "02e62e99-9adb-5ca6-baa7-d1f5cf1d1d78",
      "role_name": "threat_hunting",
      "collection_id": "3a1b2c3d-4e5f-6789-0123-456789abcdef",
      "granted_by": "8e518f31-9e9b-4116-835c-efb3ad3bfa9a",
      "granted_at": "2025-12-08T19:20:00.000000Z",
      "expires_at": "2026-01-01T00:00:00.000000Z",
      "is_active": true,
      "metadata": {
        "reason": "Temporary access for Q4 analysis"
      }
    }
  ]
}
```

**Example:**

```bash
curl -X GET "http://localhost:8006/admin/roles/threat_hunting/collections" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Notes:**

- System roles will return empty list (they have implicit access, no explicit assignments)
- Only grouping roles will have explicit collection assignments

---

## Collection Access Resolution (RBAC V2)

Users inherit collection access through a **priority system:**

1. **Admin Override** - Admin role always has access to all collections
2. **Corpus Admin** - `corpus_admin` role has access to all collections
3. **Grouping Role Assignment** - Users with grouping roles inherit access to collections assigned to those roles
4. **Default** - No access (default-deny)

**Example:**

```
User "alice" has roles: ["threat_hunting", "incident_response"]

Role "threat_hunting" assigned to collections: [A, B]
Role "incident_response" assigned to collections: [C, D]

Result: Alice can access collections [A, B, C, D]
```

**System Role Behavior:**

- `admin` - Sees all collections
- `corpus_admin` - Sees all collections
- `use_case_admin` - Sees all collections (for reference)
- Other system roles - No implicit collection access (must use grouping roles)

---

## Custom Role Examples

### Example 1: Create Legal Department Role

```sql
-- Step 1: Create users with legal_counsel role
INSERT INTO user_roles (user_id, role)
SELECT id, 'legal_counsel'
FROM users
WHERE username IN ('jane.lawyer', 'john.attorney');

-- Step 2: Assign contract review use cases to legal_counsel role
INSERT INTO role_use_case_assignments (role_name, use_case_id)
SELECT 'legal_counsel', id
FROM use_cases
WHERE intent_type = 'CONTRACT_REVIEW'
  AND lifecycle_state = 'published';
```

**Result:** All users with `legal_counsel` role can now execute contract review use cases.

### Example 2: Create Tiered SOC Access

```sql
-- SOC Tier 1: Basic query use cases only
INSERT INTO role_use_case_assignments (role_name, use_case_id)
SELECT 'soc_tier1', id
FROM use_cases
WHERE intent_type = 'QUERY' AND category = 'basic_analysis';

-- SOC Tier 2: Query + enrichment
INSERT INTO role_use_case_assignments (role_name, use_case_id)
SELECT 'soc_tier2', id
FROM use_cases
WHERE intent_type IN ('QUERY', 'ENRICHMENT');

-- SOC Tier 3: All security use cases
INSERT INTO role_use_case_assignments (role_name, use_case_id)
SELECT 'soc_tier3', id
FROM use_cases
WHERE category LIKE '%security%';
```

### Example 3: Via Admin API

```bash
# Get admin token
TOKEN=$(curl -s -X POST "http://localhost:8006/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin" -d "password=adminpassword" | jq -r '.access_token')

# Assign use case to custom role "threat_hunter"
curl -X POST "http://localhost:8006/admin/roles/threat_hunter/use-cases" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "use_case_id": "289cba6d-a0c5-401e-856b-c7b19e89ac32",
    "metadata": {
      "reason": "Threat hunters need IOC enrichment",
      "approved_by": "soc_manager"
    }
  }'

# List all use cases for threat_hunter role
curl -X GET "http://localhost:8006/admin/roles/threat_hunter/use-cases" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Access Resolution

Users inherit use case access through a **3-level priority system:**

1. **Admin Override** - Admin role always has full access (bypasses checks)
2. **Direct Assignment** - Explicit user-to-use-case assignment (`user_use_case_assignments`)
3. **Role Assignment** - Inherited through role membership (`role_use_case_assignments`)
4. **Default** - No access

**Example:**

```
User "alice" has roles: ["user", "threat_hunter"]

Role "user" assigned to use_cases: [A, B, C]
Role "threat_hunter" assigned to use_cases: [D, E]

Result: Alice can access use cases [A, B, C, D, E]
```

---

## Role Name Validation

**Format Rules:**

- Must start with lowercase letter
- Can contain: lowercase letters, digits, underscore, hyphen
- Length: 2-50 characters
- Pattern: `^[a-z][a-z0-9_-]{1,49}$`

**Valid:**
✅ `threat_hunter`, `legal_counsel`, `soc_tier1`, `hr-manager`

**Invalid:**
❌ `ThreatHunter` (uppercase)
❌ `1threat` (starts with digit)
❌ `threat hunter` (space)
❌ `a` (too short)

---

## Error Handling

### 400 Bad Request

- Invalid role name format
- Invalid use case UUID format
- Missing required fields

### 403 Forbidden

- Non-admin user attempting admin operation

### 404 Not Found

- Use case not found
- Role-use case assignment not found (on DELETE)

### 500 Internal Server Error

- Database connection error
- Unexpected error (check logs)

---

## Best Practices

### 1. Use Descriptive Role Names

✅ Good: `threat_hunter`, `legal_counsel`, `compliance_officer`
❌ Bad: `role1`, `temp`, `test`

### 2. Document Role Assignments

Always include metadata explaining why the assignment was made:

```json
{
  "use_case_id": "...",
  "metadata": {
    "reason": "Threat hunters need IOC enrichment capability",
    "approved_by": "soc_manager",
    "ticket": "SEC-2024-042",
    "date": "2025-10-24"
  }
}
```

### 3. Use Expiration for Temporary Access

```json
{
  "use_case_id": "...",
  "expires_at": "2025-12-31T23:59:59Z",
  "metadata": {
    "reason": "Temporary access for Q4 audit"
  }
}
```

### 4. Leverage Role Hierarchy

Create tiered roles for scalability:

- `soc_tier1` → Basic use cases
- `soc_tier2` → Intermediate use cases
- `soc_tier3` → All security use cases

---

## See Also

- **ADR-041:** Role-Based Use Case Permissions (architecture decision)
- **ADR-060:** Corrected RBAC Architecture (RBAC V2 with collection assignments)
- **P4-TASK-14:** Implementation task spec
- **[Grouping Roles API](./grouping-roles.md)** - Manage grouping roles
- **[Developer Teams API](./developer-teams.md)** - Manage developer teams
- **SCHEMA.md:** Database schema documentation
- **RLS_POLICIES.md:** Row-level security policies

---

**Last Updated:** 2025-12-08
**Maintainer:** AI Operations Platform Team
