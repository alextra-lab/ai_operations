# Adding MCP Tools to AI Operations Platform (AIOP)

**Purpose:** Technical guide for registering and integrating MCP tools.
**Target Audience:** Backend developers, platform engineers, advanced admins
**Last Updated:** November 24, 2025

---

## Overview

AI Operations Platform exposes two primary ways to add MCP tools:

1. **Admin Wizard (UI, T5-F2)** – Guided multi-step registration, ideal for
   one-off or low-volume tools.
2. **Registration API (T5-F1)** – Scriptable multi-phase API for automation,
   CI/CD pipelines, and bulk registration.

Both paths use the same backend workflow:

- Stateful registration session.
- Seven validation phases.
- Connection testing and capability discovery.
- Atomic database commit with encrypted secrets and RBAC seeding.

For UX details, see `docs/user-guides/admin-tool-registration.md`. This guide
focuses on **technical behavior, automation, and integration** with the
existing T1–T4 tools infrastructure.

---

## Prerequisites

Before adding an MCP tool, ensure:

- **MCP Server Requirements**
  - Implements the MCP spec targeted by the platform.
  - Supports one of the transports:
    - STDIO (local process)
    - HTTP
    - SSE (streaming)
  - Exposes `initialize` and `list_tools` operations.

- **Protocol Compatibility**
  - Default protocol version used is:
    - `2024-11-05`
  - If the server requires a different version, confirm compatibility or
    expose a shim.

- **Network & Runtime Access**
  - For STDIO:
    - Binary or script is available in the container or host PATH.
    - All required environment variables are configured.
  - For HTTP/SSE:
    - Hostname and port are reachable from the backend.
    - TLS configuration is correct (CA bundle, self-signed handling, etc.).

- **Security & Compliance**
  - Required API keys or tokens are approved.
  - Secrets can be safely stored in the platform's `SecretsManager`.
  - Tool usage is aligned with security/risk posture (especially for
    internet-facing tools).
  - **Security classification** (ADR-057) is determined:
    - Data source type (internal/external/none/mixed)
    - Data flow direction (ingress/egress/bidirectional/none)
    - Network access level (isolated/internal/external)
    - Maximum data sensitivity (public/internal/confidential/restricted)

---

## MCP Server Types

AI Operations Platform (AIOP) wraps MCP servers via a common client, backed by dedicated
transports.

### STDIO Servers

- Server started as a **local process** with stdin/stdout.
- Configured via `mcp_command`:

```json
{
  "mcp_server_type": "stdio",
  "mcp_command": ["python", "-m", "my_mcp_server"],
  "mcp_endpoint": null
}
```

**Considerations:**

- Process lifecycle is managed by the MCP client.
- Ensure the binary is present in the container image.
- Long-lived processes should handle multiple requests efficiently.

### HTTP Servers

- Server exposes MCP over HTTP or HTTP-like JSON API.
- Configured via `mcp_endpoint`:

```json
{
  "mcp_server_type": "http",
  "mcp_command": null,
  "mcp_endpoint": "http://my-mcp-server:8080"
}
```

**Considerations:**

- Use internal hostnames (Kubernetes service names, Docker networks) for
  production.
- Handle TLS correctly where applicable (certs, CA bundle).

### SSE Servers

- Similar to HTTP, but uses **Server-Sent Events** for streaming.
- Configured via `mcp_endpoint` with `mcp_server_type = "sse"`.

**Considerations:**

- Ensure server supports streaming semantics and timeouts.
- Test behavior under slow or intermittent networks.

---

## Registration Workflow Deep Dive

The registration workflow is implemented by
`ToolRegistrationService` and exposed via
`src/orchestrator/app/routers/tools_registration.py`.

### Phase 1 – basic_info

- Validates:
  - Tool ID uniqueness and slug pattern.
  - Required metadata (name, category, purpose, service location).
- Stores:
  - `session.basic_info` as the canonical tool metadata.

### Phase 2 – mcp_config

- Validates:
  - `mcp_server_type` in allowed set.
  - For `stdio`: `mcp_command` is non-empty.
  - For `http`/`sse`: `mcp_endpoint` is non-empty and begins with
    `http://` or `https://`.
  - `timeout_seconds` range (1–300).
- Stores:
  - `session.mcp_config` for later connection tests and commit.

### Phase 3 – security_config

- Validates:
  - If `requires_authentication` is `true`, both `secret_name` and
    `secret_value` must be provided.
  - Optional `secret_expires_at` is well-formed.
- Stores:
  - `session.security_config` with the raw secret value (encrypted later).

### Phase 4 – connection_test

- If `action == "skip"`:
  - Marks session as untested with a warning.
  - Allows proceeding to the next phase.
- If `action == "test"`:
  - Builds a temporary `Tool` instance from `basic_info`, `mcp_config`, and `security_config`.
  - Uses credentials from `security_config` (if authentication required) for the connection test.
  - Uses `ToolDiscoveryService` to:
    - Create an MCP client instance (with authentication headers if needed).
    - Connect, initialize, and call `list_tools()`.
    - Measure response time.
  - Stores:
    - `tested` / `success` flags.
    - `response_time_ms`.
    - Raw `server_capabilities`.
    - `discovered_tools` list and `tool_count`.

On successful commit, `server_capabilities` and (optionally) input schemas are
attached to the persisted tool.

### Phase 5 – permissions

- Validates:
  - Rate limits (global and per role) are within allowed ranges.
  - `role_permissions` entries contain non-empty role names.
- Stores:
  - `session.permissions_config`, later passed to `ToolPermissionService`.

### Phases 6 & 7 – review and commit

- **review**:
  - `action = "edit"`: mark as not ready for commit.
  - `action = "confirm"`: mark as ready; `can_proceed = true`.

- **commit**:
  - Validates presence of `basic_info` and `mcp_config`.
  - Constructs a `ToolCreate` schema by merging:
    - `basic_info`
    - `mcp_config`
    - `security_config` (without raw secret value)
    - `permissions_config`
  - Starts a DB transaction and:
    - Calls `ToolService.create_tool`.
    - Stores secrets via `SecretsManager.store_secret`.
    - Grants permissions via `ToolPermissionService.grant_permission`.
    - Stores discovered capabilities/parameter schemas if available.
  - On success:
    - Commits transaction.
    - Deletes the in-memory session.
  - On failure:
    - Rolls back transaction.
    - Keeps session with `validation_errors["commit"]` populated.

---

## Direct API Usage & Automation

For full API details, see `docs/api/tools-registration-api.md`. This section
focuses on **patterns** for automation and bulk registration.

### Single Tool Script Pattern

- Wrap each phase in a helper function that:
  - Accepts `session_id` and `phase data`.
  - Calls `POST /api/v1/admin/tools/register`.
  - Throws on HTTP errors or `can_proceed = false` for required phases.
- Store `session_id` after the first successful response.
- Use `GET /session/{session_id}` for debugging.

### Bulk Registration Pattern

1. Define a configuration file (YAML/JSON) describing tools:

```yaml
tools:
  - id: qdrant_vector_search
    name: Qdrant Vector Search
    category: vector_db
    purpose: retrieval
    service_location: orchestrator
    mcp:
      type: http
      endpoint: http://qdrant-mcp:8080
      timeout_seconds: 30
    auth:
      secret_name: QDRANT_API_KEY
      secret_value_env: QDRANT_API_KEY
    permissions:
      rate_limit_per_minute: 60
      max_concurrent_calls: 5
```

2. For each entry:
   - Map fields into the appropriate phase data payloads.
   - Populate `secret_value` from environment variables.
   - Invoke phases 1–7 sequentially.

3. For non-interactive environments:
   - Optionally use `"action": "skip"` in `connection_test` if you cannot
     reach the MCP server at deployment time, but schedule validation later.

### Error Recovery

- If a phase fails validation:
  - Use `validation_errors` to understand which fields are invalid.
  - Fix the configuration and re-run the same phase.
- If `commit` fails:
  - Inspect `validation_errors["commit"]`.
  - Fix root cause (e.g., conflicting tool ID, DB constraints).
  - Re-run `commit` with the same `session_id`.

---

## Integration with T1–T4 Infrastructure

Once committed, tools are fully integrated into the existing tools stack:

- **ToolService**
  - New tool is persisted with:
    - `tool_id`, category, purpose, provider, MCP config, capabilities.
    - `is_enabled = false` by default (secure-by-default).

- **SecretsManager**
  - Stores encrypted credentials, keyed by tool UUID and secret name.
  - Tool execution fetches and decrypts these secrets at runtime.

- **ToolPermissionService**
  - Seeds per-role permissions based on registration configuration.
  - Enforced during tool execution and developer UI visibility.

- **Tool Executor & Orchestrator (T3)**
  - Orchestrator reads use case configuration and tool allowlists.
  - `ToolExecutor`:
    - Checks tool enabled/healthy status.
    - Enforces RBAC and rate limits.
    - Creates MCP client and invokes the tool.

- **Health Monitoring & Analytics (T4)**
  - `ToolHealthMonitor` periodically checks MCP connectivity using the stored
    config and records health status.
  - Tool invocations are logged for usage analytics and incident analysis.

The net effect: **registration is the entry point** into the full execution
pipeline, not an isolated data entry step.

---

## Troubleshooting & Diagnostics

### Debugging Connection Issues

- Use `connection_test` phase details:
  - `response_time_ms`
  - `tool_count` and `discovered_tools`
  - Error strings from MCP client failures
- Check MCP server logs for:
  - Incorrect endpoints or missing routes.
  - TLS handshake errors.
  - JSON parsing or protocol mismatches.

### Common MCP Protocol Errors

- **Invalid or missing `list_tools` implementation**
  - Discovery fails; ensure the MCP server exposes tool metadata correctly.
- **Non-MCP JSON payloads**
  - Ensure server adheres to MCP message formats; adapters may be required.
- **Version mismatches**
  - Verify `mcp_protocol_version` or add backward-compatibility shims.

### Log Analysis

- Backend logs (structured JSON) include:
  - Session creation, updates, and cleanup.
  - Per-phase success/failure with session IDs.
  - Connection test results and errors.
  - Commit success/failure with tool IDs and UUIDs.

Use session IDs from API responses to correlate logs with specific workflows.

---

## Security Classification (ADR-057)

As of November 2025, all tools include **security classification** attributes
that enable Use Cases to enforce security policies.

### Classification Attributes

| Attribute | Values | Purpose |
|-----------|--------|---------|
| `data_source_type` | `internal`, `external`, `none`, `mixed` | Trust level of data |
| `data_flow_direction` | `ingress`, `egress`, `bidirectional`, `none` | Data movement |
| `network_access_level` | `isolated`, `internal`, `external` | Network reach |
| `max_data_sensitivity` | `public`, `internal`, `confidential`, `restricted` | Max data class |

### Classification Examples

| Tool | Data Source | Data Flow | Network | Sensitivity |
|------|-------------|-----------|---------|-------------|
| Qdrant (internal) | `internal` | `ingress` | `internal` | `confidential` |
| Web Scraper | `external` | `ingress` | `external` | `public` |
| Email Sender | `none` | `egress` | `external` | `internal` |
| Calculator | `none` | `none` | `isolated` | `public` |

### Use Case Tool Restrictions

Use Cases can define `tool_restrictions` to limit which tools are available:

```python
tool_restrictions:
  allowed_data_sources: ["internal", "none"]
  allowed_data_flows: ["ingress", "none"]
  allowed_network_levels: ["isolated", "internal"]
  required_data_sensitivity: "restricted"
```

**Presets** are available for common policies:

- `high_security` – PII handling, internal only
- `internal_only` – Internal data, no external access
- `research_open` – All sources, public data only
- `no_egress` – All sources, but no data export

The orchestrator validates tools against restrictions **before** presenting
them to the LLM, ensuring security policies are enforced at execution time.

---

## Advanced Topics

### Custom Authentication Types

- Standard types include:
  - `api_key`, `password`, `oauth_token`, `custom`.
- For `custom` auth:
  - Store required fields in `config_options`.
  - Extend execution layers (or MCP client) to interpret these fields and
    apply the appropriate headers or tokens.

### Tool-Specific Configuration

- Use `config_options` in `mcp_config` or `security_config` for:
  - Custom headers or query parameters.
  - TLS flags (verify, CA paths).
  - Tool-specific JSON configuration understood by your MCP server.

A typical pattern:

```json
{
  "config_options": {
    "headers": {
      "X-Tenant-ID": "customer_a"
    },
    "max_retries": 3
  }
}
```

Execution-time code can read these options from the tool record and modify the
MCP client behavior accordingly.

### Performance Tuning

- **Timeouts**
  - Set `timeout_seconds` high enough for normal workloads (e.g., 30–60s) but
    low enough to protect orchestrator throughput.
- **Rate Limits & Concurrency**
  - Start with conservative values; increase as operational confidence grows.
- **Discovery Cost**
  - For heavy discovery flows, run connection tests in controlled environments
    and reuse capability metadata where possible.

---

## Related Documentation

- **Architecture & Workflow**
  - `docs/development/adrs/ADR-056-MCP-Tool-Registration-Workflow.md`
  - `docs/development/specs/TOOLS_T5_MCP_TOOL_REGISTRATION_SPEC.md`
  - `docs/architecture/TOOLS_ARCHITECTURE_DIAGRAMS.md`

- **Implementation Details**
  - `src/orchestrator/app/routers/tools_registration.py`
  - `src/orchestrator/app/services/tool_registration_service.py`
  - `src/orchestrator/app/schemas/tool_registration.py`

- **User & API Guides**
  - `docs/user-guides/admin-tool-registration.md`
  - `docs/api/tools-registration-api.md`
  - `docs/development/guides/TOOLS_START_HERE.md`
