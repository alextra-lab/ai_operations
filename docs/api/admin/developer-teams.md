# Developer Teams Management API (RBAC V2)

**Version:** 2.0.0
**Last Updated:** 2025-12-08
**Authorization:** Admin or role_admin
**Base Path:** `/api/v1/admin/developer-teams`
**Status:** ✅ Production Ready

---

## Overview

Admin API for managing developer teams (RBAC V2). Teams provide isolation boundaries for use case development, allowing different teams to work on draft use cases without seeing each other's work. Published use cases are visible to all teams.

**Architecture:** Implements [ADR-060: Corrected RBAC Architecture](../../development/adrs/ADR-060-Corrected-RBAC-Architecture.md)

**Key Concepts:**

- **Teams:** Represented as roles with prefix `team:` in `user_roles` table
- **Team Isolation:** Draft use cases are isolated by `team_id` - teams can only see their own drafts
- **Published Use Cases:** Published use cases have `team_id = NULL` and are visible to all
- **Team Membership:** Users can belong to multiple teams
- **Use Case Ownership:** Use cases carry team ownership via `use_cases.team_id` column

**Team ID Format:**

- Must start with `team:` prefix
- Format: `team:[a-z0-9_-]{1,64}`
- Examples: `team:csirt_security`, `team:soc_governance`, `team:default`

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

### 1. List Developer Teams

**GET** `/api/v1/admin/developer-teams`

List all developer teams with member and use case counts.

**Authorization:** Admin or role_admin

**Response:** 200 OK

```json
[
  {
    "team_id": "team:csirt_security",
    "member_count": 5,
    "draft_count": 12,
    "published_count": 3
  },
  {
    "team_id": "team:soc_governance",
    "member_count": 3,
    "draft_count": 8,
    "published_count": 2
  }
]
```

**Example:**

```bash
curl -X GET "http://localhost:8006/api/v1/admin/developer-teams" \
  -H "Authorization: Bearer $TOKEN"
```

**Notes:**

- Returns teams sorted alphabetically
- `draft_count` includes draft and review state use cases
- `published_count` shows use cases that were published by this team (historical)
- Empty list if no teams exist

---

### 2. Create Team

**POST** `/api/v1/admin/developer-teams`

Create a new developer team and optionally add an initial member. This operation is idempotent - if the team already exists and the member is already added, returns existing membership information.

**Authorization:** Admin or role_admin

**Request Body:**

```json
{
  "team_id": "team:csirt_security",
  "member_user_id": "8e518f31-9e9b-4116-835c-efb3ad3bfa9a"
}
```

**Fields:**

- `team_id` (string, required) - Team ID, must start with `team:` prefix
- `member_user_id` (UUID, optional) - Initial member UUID (defaults to caller if omitted)

**Team ID Validation:**

- Must start with `team:` prefix
- Can contain: lowercase letters, digits, underscore, hyphen
- Length: 6-70 characters (including `team:` prefix)
- Pattern: `^team:[a-z0-9_-]{1,64}$`

**Response:** 201 Created

```json
{
  "team_id": "team:csirt_security",
  "user_id": "8e518f31-9e9b-4116-835c-efb3ad3bfa9a",
  "added_at": "2025-12-08T14:30:00.000000Z"
}
```

**Example:**

```bash
# Create team with caller as initial member
curl -X POST "http://localhost:8006/api/v1/admin/developer-teams" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "team_id": "team:csirt_security"
  }'

# Create team with specific initial member
curl -X POST "http://localhost:8006/api/v1/admin/developer-teams" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "team_id": "team:soc_governance",
    "member_user_id": "8e518f31-9e9b-4116-835c-efb3ad3bfa9a"
  }'
```

**Behavior:**

- Creates team membership for initial member (or caller if not specified)
- If team and membership already exist, returns existing membership
- Team becomes available for use case assignment

**Error Responses:**

- `400 Bad Request`: Invalid team ID format
- `403 Forbidden`: Not admin or role_admin
- `404 Not Found`: Specified `member_user_id` does not exist

---

### 3. Add Team Member

**POST** `/api/v1/admin/developer-teams/{team_id}/members/{user_id}`

Add a user to a team. This operation is idempotent - if the user is already a member, returns existing membership.

**Authorization:** Admin or role_admin

**Path Parameters:**

- `team_id` (string, required) - Team ID
- `user_id` (UUID, required) - User UUID to add

**Response:** 201 Created

```json
{
  "team_id": "team:csirt_security",
  "user_id": "8e518f31-9e9b-4116-835c-efb3ad3bfa9a",
  "added_at": "2025-12-08T14:30:00.000000Z"
}
```

**Example:**

```bash
curl -X POST "http://localhost:8006/api/v1/admin/developer-teams/team:csirt_security/members/8e518f31-9e9b-4116-835c-efb3ad3bfa9a" \
  -H "Authorization: Bearer $TOKEN"
```

**Error Responses:**

- `400 Bad Request`: Invalid team ID format
- `403 Forbidden`: Not admin or role_admin
- `404 Not Found`: User does not exist

---

### 4. Remove Team Member

**DELETE** `/api/v1/admin/developer-teams/{team_id}/members/{user_id}`

Remove a user from a team. This is a no-op if the user is not a member.

**Authorization:** Admin or role_admin

**Path Parameters:**

- `team_id` (string, required) - Team ID
- `user_id` (UUID, required) - User UUID to remove

**Response:** 204 No Content

**Example:**

```bash
curl -X DELETE "http://localhost:8006/api/v1/admin/developer-teams/team:csirt_security/members/8e518f31-9e9b-4116-835c-efb3ad3bfa9a" \
  -H "Authorization: Bearer $TOKEN"
```

**Notes:**

- Removing a user from a team does not affect use cases they created
- Use cases remain owned by the team (via `team_id` column)
- User will lose access to team's draft use cases after removal

**Error Responses:**

- `400 Bad Request`: Invalid team ID format
- `403 Forbidden`: Not admin or role_admin

---

### 5. List Team Use Cases

**GET** `/api/v1/admin/developer-teams/{team_id}/use-cases`

List all use cases owned by the specified team.

**Authorization:** Admin or role_admin

**Path Parameters:**

- `team_id` (string, required) - Team ID

**Response:** 200 OK

```json
[
  {
    "id": "289cba6d-a0c5-401e-856b-c7b19e89ac32",
    "name": "IOC Lookup",
    "lifecycle_state": "draft"
  },
  {
    "id": "3a1b2c3d-4e5f-6789-0123-456789abcdef",
    "name": "Threat Intelligence Query",
    "lifecycle_state": "published"
  }
]
```

**Example:**

```bash
curl -X GET "http://localhost:8006/api/v1/admin/developer-teams/team:csirt_security/use-cases" \
  -H "Authorization: Bearer $TOKEN"
```

**Notes:**

- Returns all use cases with `team_id` matching the specified team
- Includes use cases in all lifecycle states (draft, review, published, archived)
- Published use cases may have `team_id = NULL` (visible to all teams)

**Error Responses:**

- `400 Bad Request`: Invalid team ID format
- `403 Forbidden`: Not admin or role_admin

---

## Team ID Validation

**Format Rules:**

- Must start with `team:` prefix
- Can contain: lowercase letters, digits, underscore, hyphen
- Length: 6-70 characters (including `team:` prefix)
- Pattern: `^team:[a-z0-9_-]{1,64}$`

**Valid Examples:**
✅ `team:csirt_security`, `team:soc_governance`, `team:default`, `team:security-team-1`

**Invalid Examples:**
❌ `csirt_security` (missing `team:` prefix)
❌ `Team:Security` (uppercase)
❌ `team: Security` (space)
❌ `team:` (empty after prefix)
❌ `team:very-long-name-that-exceeds-sixty-four-characters-after-prefix` (too long)

---

## Workflow Examples

### Example 1: Create Team and Add Members

```bash
# 1. Create team with initial member
curl -X POST "http://localhost:8006/api/v1/admin/developer-teams" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "team_id": "team:csirt_security",
    "member_user_id": "8e518f31-9e9b-4116-835c-efb3ad3bfa9a"
  }'

# 2. Add additional members
curl -X POST "http://localhost:8006/api/v1/admin/developer-teams/team:csirt_security/members/9f629g42-af0c-5227-946d-fgc4be4cgf0b" \
  -H "Authorization: Bearer $TOKEN"

curl -X POST "http://localhost:8006/api/v1/admin/developer-teams/team:csirt_security/members/0g73ah53-bg1d-6338-a57e-ghd5cf5dhg1c" \
  -H "Authorization: Bearer $TOKEN"
```

### Example 2: List Teams and Their Use Cases

```bash
# List all teams
curl -X GET "http://localhost:8006/api/v1/admin/developer-teams" \
  -H "Authorization: Bearer $TOKEN" | jq

# List use cases for a specific team
curl -X GET "http://localhost:8006/api/v1/admin/developer-teams/team:csirt_security/use-cases" \
  -H "Authorization: Bearer $TOKEN" | jq
```

### Example 3: Manage Team Membership

```bash
# Add member
curl -X POST "http://localhost:8006/api/v1/admin/developer-teams/team:csirt_security/members/NEW_USER_UUID" \
  -H "Authorization: Bearer $TOKEN"

# Remove member
curl -X DELETE "http://localhost:8006/api/v1/admin/developer-teams/team:csirt_security/members/OLD_USER_UUID" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Team Isolation Rules

### Draft Use Cases

- Draft use cases are isolated by `team_id`
- Users with `use_case_admin` role can see:
  - ALL published use cases (regardless of team)
  - Their team's draft/review use cases (if they have team membership)
- Users without team membership see only published use cases

### Published Use Cases

- Published use cases should have `team_id = NULL` (visible to all)
- When transitioning from draft → published, `team_id` is cleared
- Historical tracking: Published use cases may retain team association for audit purposes

### Multi-Team Users

- Users can belong to multiple teams
- When creating a use case, if user has multiple teams, they must specify `team_id`
- If user has single team, `team_id` is auto-assigned
- If user has no teams, use case is assigned to `team:default`

---

## Integration with Use Case Management

### Create Use Case with Team Assignment

When creating a use case via the Use Case Management API, team assignment works as follows:

1. **If `team_id` provided:** Validates user is member of that team (or admin)
2. **If single team membership:** Auto-assigns to user's team
3. **If multiple teams:** Requires explicit `team_id` (400 error if omitted)
4. **If no teams:** Assigns to `team:default`

**Example:**

```bash
# Create use case (team auto-assigned if user has single team)
curl -X POST "http://localhost:8006/api/v1/admin/use-cases" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "IOC Lookup",
    "team_id": "team:csirt_security"
  }'
```

---

## Error Handling

### 400 Bad Request

- Invalid team ID format
- Missing required fields

### 403 Forbidden

- Non-admin/role_admin user attempting operation

### 404 Not Found

- User does not exist (when adding member)

### 500 Internal Server Error

- Database connection error
- Unexpected error (check logs)

---

## Best Practices

### 1. Use Descriptive Team Names

✅ Good: `team:csirt_security`, `team:soc_governance`, `team:compliance_team`
❌ Bad: `team:team1`, `team:temp`, `team:test`

### 2. Plan Team Structure

Create teams based on organizational structure:

- `team:csirt_security` - CSIRT team
- `team:soc_governance` - SOC governance team
- `team:compliance_team` - Compliance team

### 3. Use Default Team for Unassigned

Assign use cases to `team:default` if user has no team membership.

### 4. Regular Team Review

Periodically review team membership and remove inactive members.

### 5. Clear Team ID on Publish

Ensure published use cases have `team_id = NULL` for visibility to all teams.

---

## See Also

- **[ADR-060: Corrected RBAC Architecture](../../development/adrs/ADR-060-Corrected-RBAC-Architecture.md)** - Architecture decision
- **[RBAC V2 Implementation Plan](../../development/plans/RBAC_V2_IMPLEMENTATION_PLAN.md)** - Implementation details
- **[Use Case Management API](../use-case-management.md)** - Create and manage use cases with team assignment
- **[Grouping Roles API](./grouping-roles.md)** - Manage grouping roles
- **[Role Use Case Management API](./role-use-case-management.md)** - Assign use cases to roles

---

**Last Updated:** 2025-12-08
**Maintainer:** AI Operations Platform Team
