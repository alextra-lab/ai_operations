# MCP Tool Registration API Reference

**Version:** 1.0
**Base URL:** `/api/v1/admin/tools/register`
**Authentication:** Required (Admin role)
**Date:** November 24, 2025
**Status:** ✅ Production Ready (T5-F1/T5-F2 Complete)

---

## Overview

The MCP Tool Registration API provides a **multi-phase workflow** for
registering MCP tools. It is designed for:

- The Angular admin wizard (T5-F2).
- Automation scripts that orchestrate registration directly.
- Operational tooling that inspects or cancels in-progress registrations.

The workflow is modeled as a **stateful session** with seven phases:

1. `basic_info` – Tool identification and metadata
2. `mcp_config` – MCP transport and connection details
3. `security_config` – Authentication and secrets configuration
4. `connection_test` – Connectivity and capability discovery (uses credentials from step 3)
5. `permissions` – RBAC permissions and rate limits
6. `review` – Final review state
7. `commit` – Atomic registration commit

The primary endpoint is a single multi-phase `POST /` call, with helper
endpoints for retrieving and canceling sessions.

---

## Authentication

All endpoints require **admin-only** authentication.

- Include a valid JWT access token in the `Authorization` header:

```bash
Authorization: Bearer <access_token>
```

Example of obtaining an admin token (matches other admin APIs):

```bash
TOKEN=$(curl -s -X POST "http://localhost:8006/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin" \
  -d "password=adminpassword" | jq -r '.access_token')
```

If the token is missing, invalid, or does not belong to an admin user, the API
returns:

- `401 Unauthorized` – Missing/invalid token.
- `403 Forbidden` – Authenticated but not an admin.

---

## Data Models

### ToolRegistrationPhase

```typescript
type ToolRegistrationPhase =
  | "basic_info"
  | "mcp_config"
  | "connection_test"
  | "security_config"
  | "permissions"
  | "review"
  | "commit";
```

### ToolRegistrationRequest

```typescript
interface ToolRegistrationRequest {
  session_id: string | null;    // null for first phase
  phase: ToolRegistrationPhase; // current phase to process
  data: Record<string, any>;    // phase-specific payload
}
```

### ToolRegistrationResponse

```typescript
interface ToolRegistrationResponse {
  session_id: string;                      // registration session ID
  current_phase: ToolRegistrationPhase;    // server-side current phase
  next_phase: ToolRegistrationPhase | null;// next phase if can_proceed
  validation_errors: Record<string, string[]>;
  can_proceed: boolean;                    // whether UI may advance
  discovered_capabilities?: Record<string, any> | null;
  tool_id?: string | null;                 // UUID (set after commit)
  message: string;                         // human-readable summary
}
```

### RegistrationSessionResponse

```typescript
interface RegistrationSessionResponse {
  session_id: string;
  current_phase: ToolRegistrationPhase;
  created_at: string;         // ISO 8601
  updated_at: string;         // ISO 8601
  expires_at: string;         // ISO 8601
  collected_data: Record<string, any>;      // per-phase data
  validation_status: Record<string, boolean>; // phase -> valid?
}
```

### Phase-Specific Data Shapes

These are the typical contents of `request.data` for each phase.

#### Phase 1 – `basic_info`

```json
{
  "tool_id": "qdrant_vector_search",
  "name": "Qdrant Vector Search",
  "description": "Semantic search over Qdrant collections",
  "category": "vector_db",
  "tool_purpose": "retrieval",
  "service_location": "orchestrator",
  "provider": "internal",
  "version": "1.0.0",
  "documentation_url": "https://docs.example.com/tools/qdrant",
  "tags": ["qdrant", "vector", "search"],
  "data_source_type": "internal",
  "data_flow_direction": "ingress",
  "network_access_level": "internal",
  "max_data_sensitivity": "internal"
}
```

**Security Classification Fields (ADR-057):**

| Field | Values | Description |
|-------|--------|-------------|
| `data_source_type` | `internal`, `external`, `none`, `mixed` | Trust level of data sources |
| `data_flow_direction` | `ingress`, `egress`, `bidirectional`, `none` | Direction of data flow |
| `network_access_level` | `isolated`, `internal`, `external` | Network access requirements |
| `max_data_sensitivity` | `public`, `internal`, `confidential`, `restricted` | Max data classification |

These fields enable Use Cases to restrict which tools are available based on
security policies (see `tool_restrictions` in Use Case configuration).

#### Phase 2 – `mcp_config`

```json
{
  "mcp_server_type": "http",              // "stdio" | "http" | "sse"
  "mcp_command": null,                    // required for "stdio"
  "mcp_endpoint": "http://qdrant-mcp:8080", // required for "http" / "sse"
  "mcp_protocol_version": "2024-11-05",
  "timeout_seconds": 30,
  "config_options": {
    "verify_tls": false
  }
}
```

For `stdio` servers:

```json
{
  "mcp_server_type": "stdio",
  "mcp_command": ["python", "-m", "my_mcp_server"],
  "mcp_endpoint": null,
  "mcp_protocol_version": "2024-11-05",
  "timeout_seconds": 30,
  "config_options": {}
}
```

#### Phase 3 – `security_config`

```json
{
  "requires_authentication": true,
  "authentication_type": "api_key",
  "secret_name": "QDRANT_API_KEY",
  "secret_value": "REDACTED-KEY-VALUE",
  "secret_expires_at": null,
  "config_options": {
    "header_name": "Authorization",
    "prefix": "Bearer "
  }
}
```

#### Phase 4 – `connection_test`

```json
{
  "action": "test"   // "test" | "skip"
}
```

- `"test"`: perform connectivity test and discovery using credentials from phase 3.
- `"skip"`: mark connection as untested (allowed for automation; the wizard
  normally uses `"test"`).

#### Phase 5 – `permissions`

```json
{
  "rate_limit_per_minute": 60,
  "max_concurrent_calls": 5,
  "health_check_interval_seconds": 300,
  "role_permissions": [
    {
      "role": "analyst",
      "can_view": true,
      "can_use": true,
      "can_configure": false,
      "max_calls_per_hour": 100,
      "max_calls_per_day": 500
    },
    {
      "role": "admin",
      "can_view": true,
      "can_use": true,
      "can_configure": true,
      "max_calls_per_hour": null,
      "max_calls_per_day": null
    }
  ]
}
```

#### Phase 6 – `review`

```json
{
  "action": "confirm"   // "confirm" | "edit"
}
```

- `"confirm"`: mark session as ready to commit.
- `"edit"`: indicates the user wants to go back and modify previous phases.

#### Phase 7 – `commit`

```json
{
  "confirmed": true
}
```

If `confirmed` is not `true`, commit is rejected.

---

## Endpoints

### 1. Process Registration Phase

**POST** `/api/v1/admin/tools/register`

Process one step of the registration workflow.

#### Request

- **Body:** `ToolRegistrationRequest`

```bash
curl -X POST "http://localhost:8006/api/v1/admin/tools/register" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": null,
    "phase": "basic_info",
    "data": {
      "tool_id": "qdrant_vector_search",
      "name": "Qdrant Vector Search",
      "description": "Semantic search over Qdrant collections",
      "category": "vector_db",
      "tool_purpose": "retrieval",
      "service_location": "orchestrator",
      "provider": "internal",
      "version": "1.0.0",
      "documentation_url": null,
      "tags": ["qdrant", "vector", "search"]
    }
  }'
```

#### Response (Example – basic_info)

```json
{
  "session_id": "a1b2c3d4...",
  "current_phase": "mcp_config",
  "next_phase": "connection_test",
  "validation_errors": {},
  "can_proceed": true,
  "discovered_capabilities": null,
  "tool_id": null,
  "message": "Phase processed successfully"
}
```

On later phases, `current_phase` and `next_phase` reflect the server-side
state, and `discovered_capabilities` is populated for `connection_test`.

#### Phase: connection_test (Example)

```bash
curl -X POST "http://localhost:8006/api/v1/admin/tools/register" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"${SESSION}\",
    \"phase\": \"connection_test\",
    \"data\": {\"action\": \"test\"}
  }"
```

Example response:

```json
{
  "session_id": "a1b2c3d4...",
  "current_phase": "security_config",
  "next_phase": "permissions",
  "validation_errors": {},
  "can_proceed": true,
  "discovered_capabilities": {
    "tested": true,
    "success": true,
    "response_time_ms": 120.5,
    "server_capabilities": {
      "mcpVersion": "2024-11-05"
    },
    "discovered_tools": [
      {
        "name": "semantic_search",
        "description": "Search Qdrant collections",
        "inputSchema": {
          "type": "object",
          "properties": {
            "query": {"type": "string"}
          },
          "required": ["query"]
        }
      }
    ],
    "tool_count": 1
  },
  "tool_id": null,
  "message": "Phase processed successfully"
}
```

#### Phase: commit (Example)

```bash
# REVIEW
curl -X POST "http://localhost:8006/api/v1/admin/tools/register" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"${SESSION}\",
    \"phase\": \"review\",
    \"data\": {\"action\": \"confirm\"}
  }"

# COMMIT
curl -X POST "http://localhost:8006/api/v1/admin/tools/register" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"${SESSION}\",
    \"phase\": \"commit\",
    \"data\": {\"confirmed\": true}
  }"
```

Commit response:

```json
{
  "session_id": "a1b2c3d4...",
  "current_phase": "commit",
  "next_phase": null,
  "validation_errors": {},
  "can_proceed": true,
  "discovered_capabilities": null,
  "tool_id": "c7d3e2a1-9876-4321-b123-456789abcdef",
  "message": "Tool 'Qdrant Vector Search' registered successfully"
}
```

#### Status Codes

- `200 OK` – Phase processed successfully.
- `400 Bad Request` – Invalid phase, missing data, or invalid initial phase
  (e.g., first call not using `basic_info`), or expired/missing session.
- `401/403` – Authentication/authorization failures.
- `500 Internal Server Error` – Unexpected server error.

Error responses follow FastAPI’s standard shape:

```json
{
  "detail": "Registration session 'abc' has expired"
}
```

---

### 2. Get Registration Session

**GET** `/api/v1/admin/tools/register/session/{session_id}`

Retrieve current state and collected data for a registration session. Useful
for resuming interrupted registrations, debugging, or automation tooling.

#### Request

```bash
curl -X GET \
  "http://localhost:8006/api/v1/admin/tools/register/session/${SESSION}" \
  -H "Authorization: Bearer $TOKEN"
```

#### Response

```json
{
  "session_id": "a1b2c3d4...",
  "current_phase": "permissions",
  "created_at": "2025-11-24T10:00:00Z",
  "updated_at": "2025-11-24T10:05:00Z",
  "expires_at": "2025-11-24T11:00:00Z",
  "collected_data": {
    "basic_info": { "...": "..." },
    "mcp_config": { "...": "..." },
    "connection_result": {
      "tested": true,
      "success": true,
      "tool_count": 1
    },
    "security_config": {
      "requires_authentication": true,
      "authentication_type": "api_key",
      "secret_name": "QDRANT_API_KEY",
      "secret_value": "***REDACTED***"
    },
    "permissions_config": {
      "rate_limit_per_minute": 60,
      "max_concurrent_calls": 5,
      "health_check_interval_seconds": 300,
      "role_permissions": [ "...omitted..." ]
    }
  },
  "validation_status": {
    "basic_info": true,
    "mcp_config": true,
    "connection_test": true,
    "security_config": true,
    "permissions": true,
    "review": false,
    "commit": false
  }
}
```

> **Security Note:**
> The API masks any `secret_value` fields with `***REDACTED***` when returning
> session data.

#### Status Codes

- `200 OK` – Session found and returned.
- `404 Not Found` – Session not found or has expired.
- `401/403` – Authentication/authorization failures.

---

### 3. Cancel Registration Session

**DELETE** `/api/v1/admin/tools/register/session/{session_id}`

Cancel an in-progress registration and clean up the session. This does **not**
delete any already-committed tools; it only clears transient workflow state.

#### Request

```bash
curl -X DELETE \
  "http://localhost:8006/api/v1/admin/tools/register/session/${SESSION}" \
  -H "Authorization: Bearer $TOKEN"
```

#### Response

- `204 No Content` – Session removed (or already absent).

Errors are intentionally non-fatal; if the session does not exist, the
operation is treated as a no-op.

#### Status Codes

- `204 No Content` – Cancel succeeded or session already gone.
- `401/403` – Authentication/authorization failures.

---

## Session Management

### Lifecycle

- Sessions are created automatically on the first **basic_info** phase when
  `session_id` is `null`.
- Each subsequent phase must include the same `session_id`.
- Sessions expire after **1 hour** of inactivity:
  - Expired sessions are cleaned up from the in-memory store.
  - Further API calls with that `session_id` return `400` or `404`
    (depending on endpoint).

### Storage

- The current implementation uses an **in-memory session store** in
  `ToolRegistrationService`:
  - Suitable for single-process deployments and testing.
  - Future production deployments may migrate this to Redis or another
    distributed store.

### Data Collected per Session

- `basic_info`: tool slug, display name, category, purpose, etc.
- `mcp_config`: transport, endpoint/command, timeout, options.
- `connection_result`: success flag, response time, discovered tools, etc.
- `security_config`: authentication type and secret metadata.
- `permissions_config`: RBAC and rate limit configuration.
- `validation_errors`: per-phase error lists.
- `can_proceed`: whether the last processed phase is valid.

---

## Error Handling

### HTTP Status Codes Summary

- `200 OK` – Phase processed / session retrieved.
- `204 No Content` – Session canceled.
- `400 Bad Request` – Invalid input, invalid phase order, or expired session.
- `401 Unauthorized` / `403 Forbidden` – Authentication/authorization issues.
- `404 Not Found` – Session not found (GET/DELETE).
- `500 Internal Server Error` – Unhandled server error.

### Error Response Format

All errors return a FastAPI-style error object:

```json
{
  "detail": "Human-readable error message"
}
```

The `validation_errors` field on `ToolRegistrationResponse` provides additional
per-phase detail for successful 200 responses where the phase validation
failed (`can_proceed = false`):

```json
{
  "session_id": "a1b2c3d4...",
  "current_phase": "basic_info",
  "next_phase": null,
  "validation_errors": {
    "basic_info": [
      "Tool ID 'qdrant_vector_search' already exists"
    ]
  },
  "can_proceed": false,
  "discovered_capabilities": null,
  "tool_id": null,
  "message": "Phase processed successfully"
}
```

---

## Integration Examples

### Complete Registration Workflow (cURL)

```bash
BASE="http://localhost:8006/api/v1/admin/tools/register"

# 1. BASIC INFO
SESSION=$(curl -s -X POST "$BASE" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": null,
    "phase": "basic_info",
    "data": {
      "tool_id": "qdrant_vector_search",
      "name": "Qdrant Vector Search",
      "description": "Semantic search over Qdrant collections",
      "category": "vector_db",
      "tool_purpose": "retrieval",
      "service_location": "orchestrator",
      "provider": "internal",
      "version": "1.0.0",
      "documentation_url": null,
      "tags": ["qdrant", "vector", "search"]
    }
  }' | jq -r '.session_id')

# 2. MCP CONFIG
curl -s -X POST "$BASE" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"${SESSION}\",
    \"phase\": \"mcp_config\",
    \"data\": {
      \"mcp_server_type\": \"http\",
      \"mcp_command\": null,
      \"mcp_endpoint\": \"http://qdrant-mcp:8080\",
      \"mcp_protocol_version\": \"2024-11-05\",
      \"timeout_seconds\": 30,
      \"config_options\": {}
    }
  }" > /dev/null

# 3. CONNECTION TEST
curl -s -X POST "$BASE" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"${SESSION}\",
    \"phase\": \"connection_test\",
    \"data\": {\"action\": \"test\"}
  }" | jq '.discovered_capabilities'

# 4. SECURITY CONFIG
curl -s -X POST "$BASE" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"${SESSION}\",
    \"phase\": \"security_config\",
    \"data\": {
      \"requires_authentication\": true,
      \"authentication_type\": \"api_key\",
      \"secret_name\": \"QDRANT_API_KEY\",
      \"secret_value\": \"REDACTED-KEY-VALUE\",
      \"secret_expires_at\": null,
      \"config_options\": {}
    }
  }" > /dev/null

# 5. PERMISSIONS
curl -s -X POST "$BASE" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"${SESSION}\",
    \"phase\": \"permissions\",
    \"data\": {
      \"rate_limit_per_minute\": 60,
      \"max_concurrent_calls\": 5,
      \"health_check_interval_seconds\": 300,
      \"role_permissions\": [
        {\"role\": \"analyst\", \"can_view\": true, \"can_use\": true, \"can_configure\": false},
        {\"role\": \"admin\", \"can_view\": true, \"can_use\": true, \"can_configure\": true}
      ]
    }
  }" > /dev/null

# 6. REVIEW
curl -s -X POST "$BASE" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"${SESSION}\",
    \"phase\": \"review\",
    \"data\": {\"action\": \"confirm\"}
  }" > /dev/null

# 7. COMMIT
curl -s -X POST "$BASE" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"${SESSION}\",
    \"phase\": \"commit\",
    \"data\": {\"confirmed\": true}
  }" | jq '.tool_id, .message'
```

### Python Example (httpx)

```python
import httpx

BASE_URL = "http://localhost:8006/api/v1/admin/tools/register"
TOKEN = "YOUR_ADMIN_TOKEN"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}

with httpx.Client(base_url=BASE_URL, headers=headers, timeout=30.0) as client:
    # Phase 1: basic_info
    resp = client.post(
        "",
        json={
            "session_id": None,
            "phase": "basic_info",
            "data": {
                "tool_id": "qdrant_vector_search",
                "name": "Qdrant Vector Search",
                "description": "Semantic search over Qdrant collections",
                "category": "vector_db",
                "tool_purpose": "retrieval",
                "service_location": "orchestrator",
                "provider": "internal",
                "version": "1.0.0",
                "documentation_url": None,
                "tags": ["qdrant", "vector", "search"],
            },
        },
    )
    resp.raise_for_status()
    session_id = resp.json()["session_id"]

    def phase(phase_name: str, data: dict) -> dict:
        r = client.post("", json={
            "session_id": session_id,
            "phase": phase_name,
            "data": data,
        })
        r.raise_for_status()
        return r.json()

    phase("mcp_config", {
        "mcp_server_type": "http",
        "mcp_command": None,
        "mcp_endpoint": "http://qdrant-mcp:8080",
        "mcp_protocol_version": "2024-11-05",
        "timeout_seconds": 30,
        "config_options": {},
    })

    conn = phase("connection_test", {"action": "test"})
    print("Connection test:", conn["discovered_capabilities"])

    phase("security_config", {
        "requires_authentication": True,
        "authentication_type": "api_key",
        "secret_name": "QDRANT_API_KEY",
        "secret_value": "REDACTED-KEY-VALUE",
        "secret_expires_at": None,
        "config_options": {},
    })

    phase("permissions", {
        "rate_limit_per_minute": 60,
        "max_concurrent_calls": 5,
        "health_check_interval_seconds": 300,
        "role_permissions": [],
    })

    phase("review", {"action": "confirm"})
    commit_resp = phase("commit", {"confirmed": True})

    print("Registered tool UUID:", commit_resp["tool_id"])
```

### JavaScript / TypeScript Example (fetch)

```typescript
const BASE_URL = "/api/v1/admin/tools/register";

async function postPhase(
  token: string,
  sessionId: string | null,
  phase: string,
  data: Record<string, any>
) {
  const res = await fetch(BASE_URL, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ session_id: sessionId, phase, data }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }

  return res.json();
}
```

---

## Resuming and Error Recovery

### Resuming an Interrupted Registration

Automation tools can resume by:

1. Storing the `session_id` after the first successful call.
2. Calling `GET /session/{session_id}` to inspect progress.
3. Sending the next phase request with the same `session_id`.

If the session has expired (`404`), start a new registration from `basic_info`.

### Handling Commit Failures

If the `commit` phase fails:

- The database transaction is **rolled back**, so no partial tool records
  remain.
- The session is kept with a validation error on the `commit` phase.
- You can:
  - Inspect `validation_errors["commit"]`.
  - Fix the underlying issue (for example, conflicting tool ID or database
    constraint).
  - Re-run commit with the same `session_id`.

---

## Relationship to Other Tool APIs

- **Admin Tool CRUD:**
  Existing admin endpoints (e.g. `tools_admin`) can still create tools in a
  single step for advanced use cases.

- **Execution & Monitoring:**
  Once committed, registered tools are visible to:
  - Tool execution pipeline (`ToolExecutor`).
  - Health monitoring (`ToolHealthMonitor`).
  - Analytics and RBAC services (`ToolPermissionService`, etc.).

- **Developer UI:**
  Registered tools appear in the developer tool selection UI and can be
  assigned to use cases according to the T1–T4 architecture.

For a conceptual overview of how registration feeds into execution and health
monitoring, see:

- `docs/architecture/TOOLS_ARCHITECTURE_DIAGRAMS.md`
- `docs/development/guides/adding-mcp-tools.md`
