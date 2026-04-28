# Admin Audit Logs API

**Version:** 1.0
**Last Updated:** October 27, 2025
**Implemented:** P4-ADMIN-04
**Base Path:** `/admin/audit-logs`
**Authorization:** Admin role required

---

## Overview

The Audit Logs API provides read-only access to system audit trail for compliance, security monitoring, and operational analysis. All administrative and user actions are automatically logged through the audit middleware.

**Key Features:**
- List audit logs with advanced filtering and pagination
- Aggregate statistics for dashboard displays
- Detailed log inspection
- Date range queries for compliance reporting
- Actor and resource type filtering

---

## Endpoints

### 1. List Audit Logs

**Endpoint:** `GET /admin/audit-logs`
**Authorization:** Admin role required
**Purpose:** Retrieve paginated list of audit logs with optional filtering

#### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `page` | integer | No | 1 | Page number (1-indexed) |
| `page_size` | integer | No | 50 | Items per page (max 100) |
| `start_date` | datetime | No | 30 days ago | Filter logs after this date (ISO 8601 format) |
| `end_date` | datetime | No | now | Filter logs before this date (ISO 8601 format) |
| `actor_user_id` | UUID | No | - | Filter by specific user ID |
| `action` | string | No | - | Filter by action (e.g., "POST /auth/token") |
| `resource_type` | string | No | - | Filter by resource type |
| `success` | boolean | No | - | Filter by success status (true/false) |

#### Response

**Status:** 200 OK

```json
{
  "logs": [
    {
      "id": "uuid",
      "event_time": "2025-10-27T10:57:09.772290Z",
      "actor_user_id": "uuid",
      "actor_username": "admin",
      "actor_roles": ["admin"],
      "action": "POST /auth/token",
      "resource_type": "auth_token",
      "resource_id": "optional-id",
      "use_case_id": null,
      "use_case_name": null,
      "request_id": "req_123",
      "client_ip": "192.0.2.1",
      "user_agent": "Mozilla/5.0...",
      "success": true,
      "details": {},
      "created_at": "2025-10-27T10:57:09.772290Z"
    }
  ],
  "total": 6912,
  "page": 1,
  "page_size": 50,
  "total_pages": 139
}
```

#### Example Request

```bash
curl -X GET "http://localhost:8006/admin/audit-logs?page=1&page_size=20&start_date=2025-10-01T00:00:00Z&success=false" \
  -H "Authorization: Bearer <admin_token>"
```

---

### 2. Get Audit Log Statistics

**Endpoint:** `GET /admin/audit-logs/stats`
**Authorization:** Admin role required
**Purpose:** Retrieve aggregated statistics for dashboard display

#### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `start_date` | datetime | No | 30 days ago | Statistics start date |
| `end_date` | datetime | No | now | Statistics end date |

#### Response

**Status:** 200 OK

```json
{
  "total_events": 6912,
  "success_count": 6607,
  "failure_count": 305,
  "unique_users": 5,
  "unique_resource_types": 12,
  "top_actions": [
    {
      "action": "POST /api/security/events",
      "count": 3849
    },
    {
      "action": "GET /health",
      "count": 2023
    }
  ],
  "top_resource_types": [
    {
      "resource_type": "security_event",
      "count": 3849
    },
    {
      "resource_type": "health_check",
      "count": 2023
    }
  ],
  "start_date": "2025-09-27T00:00:00Z",
  "end_date": "2025-10-27T23:59:59Z"
}
```

#### Example Request

```bash
curl -X GET "http://localhost:8006/admin/audit-logs/stats?start_date=2025-10-01T00:00:00Z" \
  -H "Authorization: Bearer <admin_token>"
```

---

### 3. Get Single Audit Log

**Endpoint:** `GET /admin/audit-logs/{log_id}`
**Authorization:** Admin role required
**Purpose:** Retrieve detailed information for a specific audit log entry

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `log_id` | UUID | Yes | Unique identifier of the audit log |

#### Response

**Status:** 200 OK

```json
{
  "id": "aca43cda-c50c-40f3-988b-05a8864085d5",
  "event_time": "2025-10-27T10:57:18.211580Z",
  "actor_user_id": "f2938a78-b70a-4749-860f-c9c580b91373",
  "actor_username": "admin",
  "actor_roles": ["admin"],
  "action": "GET /admin/audit-logs/stats",
  "resource_type": "audit_log",
  "resource_id": null,
  "use_case_id": null,
  "use_case_name": null,
  "request_id": "req_123",
  "client_ip": "192.0.2.1",
  "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...",
  "success": true,
  "details": {
    "filters": {
      "start_date": "2025-09-27T10:29:42.144Z",
      "end_date": "2025-10-27T10:29:42.144Z"
    }
  },
  "created_at": "2025-10-27T10:57:18.211580Z"
}
```

#### Example Request

```bash
curl -X GET "http://localhost:8006/admin/audit-logs/aca43cda-c50c-40f3-988b-05a8864085d5" \
  -H "Authorization: Bearer <admin_token>"
```

---

## Error Responses

### 401 Unauthorized

```json
{
  "detail": "Not authenticated"
}
```

### 403 Forbidden

```json
{
  "detail": "Insufficient permissions"
}
```

### 404 Not Found

```json
{
  "detail": "Audit log not found"
}
```

### 500 Internal Server Error

```json
{
  "detail": "Failed to retrieve audit logs"
}
```

---

## Data Model

### AuditLogResponse

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique identifier |
| `event_time` | datetime | When the event occurred (UTC) |
| `actor_user_id` | UUID \| null | User who performed the action |
| `actor_username` | string \| null | Username (or "System") |
| `actor_roles` | string[] | User's roles at time of action |
| `action` | string | HTTP method + path or system action |
| `resource_type` | string | Type of resource affected |
| `resource_id` | string \| null | Specific resource identifier |
| `use_case_id` | UUID \| null | Related use case (if applicable) |
| `use_case_name` | string \| null | Use case name (if applicable) |
| `request_id` | string \| null | Request correlation ID |
| `client_ip` | string \| null | Client IP address |
| `user_agent` | string \| null | Client user agent |
| `success` | boolean | Whether action succeeded |
| `details` | object | Additional context (JSON) |
| `created_at` | datetime | Alias for event_time (for frontend consistency) |

### AuditLogStatsResponse

| Field | Type | Description |
|-------|------|-------------|
| `total_events` | integer | Total log entries in date range |
| `success_count` | integer | Number of successful events |
| `failure_count` | integer | Number of failed events |
| `unique_users` | integer | Number of distinct users |
| `unique_resource_types` | integer | Number of distinct resource types |
| `top_actions` | ActionCount[] | Most frequent actions (top 10) |
| `top_resource_types` | ResourceTypeCount[] | Most accessed resource types (top 10) |
| `start_date` | datetime | Query start date |
| `end_date` | datetime | Query end date |

---

## Implementation Notes

### Database Schema

Audit logs are stored in the `audit_logs` table with the following structure:

- Immutable audit trail (no updates or deletes allowed)
- Indexed on `(use_case_id, event_time)` for UC-specific queries
- Indexed on `(actor_user_id, event_time)` for user activity tracking
- `client_ip` stored as PostgreSQL `INET` type (converted to string in API responses)
- `details` stored as `JSONB` for flexible context storage
- `event_time` with timezone support (UTC)

### Authorization

All endpoints require:
1. Valid JWT access token
2. User role must be `admin`
3. Active user account

Enforced via `require_admin` dependency in FastAPI router.

### Performance Considerations

- Pagination is mandatory (max 100 items per page)
- Queries are optimized with database indexes
- Default date range is last 30 days to limit result sets
- Username and use_case lookups cached per batch (optional optimization pending)

### Audit Trail Integrity

- Logs are immutable (no DELETE or UPDATE operations)
- All administrative actions automatically logged via middleware
- Includes both successful and failed operations
- Captures full request context (IP, user agent, request ID)

---

## Related Documentation

- **Backend Router:** `src/orchestrator/app/routers/admin_audit.py`
- **Database Model:** `src/orchestrator/app/db/models.py` (AuditLog class)
- **Frontend Component:** `src/frontend-angular/src/app/pages/admin/audit-logs/`
- **Task Spec:** P4-ADMIN-04
- **Session Log:** `docs/development/sessions/2025-10-27-admin-panels-adr-compliance-audit.md`

---

**Document Version:** 1.0
**API Version:** v1
**Stability:** Stable
