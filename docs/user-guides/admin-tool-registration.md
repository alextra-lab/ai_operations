# MCP Tool Registration – Admin User Guide

**Purpose:** Learn how to register MCP tools using the admin wizard.
**Target Audience:** SOC Administrators, System Admins
**Last Updated:** November 24, 2025

---

## Overview

The MCP Tool Registration wizard provides a guided, multi-phase workflow for
adding new MCP tools to AI Operations Platform. It validates configuration at
each step, tests connectivity, and performs an atomic commit so that tools are
either fully registered or not created at all.

### Registration Workflow Summary

The workflow follows seven backend phases, surfaced in six UI steps:

1. **Basic Information** – Tool identity, category, and purpose
2. **MCP Configuration** – Transport type and connection details
3. **Connection Test** – Test MCP server and discover capabilities
4. **Security Configuration** – Authentication and secrets handling
5. **Permissions & Limits** – RBAC, rate limits, and timeouts
6. **Review & Confirm** – Summary and final confirmation
7. **Commit (backend)** – Atomic registration in the database

The final commit happens when you click **Register Tool** on the
**Review & Confirm** step; if anything fails, the system rolls back and
no partial records remain.

---

## Prerequisites

- **Role:** You must be logged in as an **Admin** (admin-only endpoints).
- **MCP Server:** You have the MCP server ready:
  - **STDIO:** Command to start the server
  - **HTTP/SSE:** Base URL where the server is listening
- **Network Access:** The backend must be able to reach the MCP server host.
- **Secrets:** Any required API keys, tokens, or passwords are available and
  approved for use.

---

## Starting the Registration Wizard

1. Navigate to the **Admin Tools** area in the Angular UI.
2. Open the **Tools** dashboard (registered tools list).
3. Click **Register New MCP Tool** to open the wizard.
4. You will see a horizontal stepper labeled from **Basic Information** through
   **Review & Confirm**.

If you previously saved a draft, the wizard will automatically load your
in-progress configuration (see **Drafts & Resuming** below).

---

## Phase 1 – Basic Information

Use this step to define how the tool will appear in the platform.

### Fields

- **Tool ID** (required)
  - Slug-style identifier (e.g., `qdrant_vector_search`)
  - Allowed characters: `a–z`, `0–9`, `_`, `-`
  - Must be unique across all tools
- **Tool Name** (required)
  - Human-readable name (e.g., `Qdrant Vector Search`)
- **Category** (required)
  - Example values: `database`, `vector_db`, `web_scraping`, `reasoning`,
    `documentation`, `custom`
- **Purpose** (required)
  - Typical values:
    - `retrieval` – Tools that fetch or search data
    - `orchestrator` – Tools that coordinate or transform work
- Additional optional fields may include:
  - **Description**
  - **Provider**
  - **Version**
  - **Documentation URL**
  - **Tags**

### Security Classification (ADR-057)

Starting November 2025, tools include **security classification** attributes that
determine which Use Cases can access them:

| Field | Values | Description |
|-------|--------|-------------|
| **Data Source** | Internal, External, None, Mixed | Trust level of data sources |
| **Data Flow** | Ingress, Egress, Bidirectional, None | Direction of data movement |
| **Network Access** | Isolated, Internal, External | Network reach required |
| **Max Sensitivity** | Public, Internal, Confidential, Restricted | Data classification level |

**Why This Matters:**

- Use Cases can define **Tool Restrictions** (security policies).
- Tools that don't meet the Use Case's restrictions are automatically blocked.
- Example: A "High Security (PII)" Use Case may only allow tools with
  `data_source_type = internal` and `data_flow_direction = ingress`.

**Default Values:**

New tools default to conservative settings (`internal`, `ingress`, `internal`,
`internal`). Adjust based on the tool's actual behavior.

### What the System Validates

- Tool ID format and uniqueness
- Required fields present
- Category and purpose values are valid
- Security classification values are valid

### Admin Actions

1. Fill in the required fields.
2. **Set security classification** based on what data the tool accesses and how.
3. Click **Next**.

If validation fails, inline errors are shown next to the affected fields and
the wizard stays on the same step.

---

## Phase 2 – MCP Configuration

Configure how AI Operations Platform (AIOP) will connect to the MCP server.

### Fields

- **Server Type** (required)
  - `STDIO` – Local process with stdin/stdout transport
  - `HTTP` – HTTP-based MCP server
  - `SSE` – Server-Sent Events (streaming) MCP server

- **For STDIO servers:**
  - **Command** (required)
    - JSON-style command array, for example:
      - `["python", "-m", "my_mcp_server"]`
      - `["node", "dist/server.js"]`

- **For HTTP/SSE servers:**
  - **Endpoint URL** (required)
    - Example: `http://localhost:8080`

- **Protocol & Timeout:**
  - **MCP Protocol Version:** default `2024-11-05`
  - **Timeout (seconds):** default `30`, min `1`, max `300`

### What the System Validates

- Server type is one of `stdio`, `http`, `sse`
- For `stdio`:
  - Command is provided
- For `http`/`sse`:
  - Endpoint URL is provided
  - URL starts with `http://` or `https://`
- Timeout is within allowed range

### Admin Actions

1. Select **Server Type**.
2. Provide either the **Command** (STDIO) or **Endpoint URL** (HTTP/SSE).
3. Adjust **Timeout** if needed.
4. Click **Next**.

---

## Phase 3 – Security Configuration

Configure how the tool authenticates to the MCP server and how secrets are
stored. **Important:** This step must be completed before connection testing
so that credentials can be used for the connection test.

---

## Phase 4 – Connection Testing

This step verifies that AI Operations Platform (AIOP) can talk to the MCP server and discover
its capabilities using the credentials you provided in the previous step.

### What Happens During Test

When you click **Test Connection** the system:

1. Creates a temporary MCP client using your MCP config and security credentials.
2. Connects to the MCP server with authentication (if required).
3. Performs MCP initialization.
4. Calls `list_tools` (or equivalent) to discover tools.
5. Measures response time.
6. Disconnects cleanly.

### UI Elements

- **Test Connection** button with network icon.
- Loading indicator: "Testing connection…" with spinner.
- **Result panel:**
  - On success:
    - Green success message
    - Number of tools discovered
  - On failure:
    - Red error message with the error text from the backend

### Success Path

- You see a success message and a tool count.
- The wizard allows you to click **Next** to proceed to Permissions.

### Failure Path

- You see an error message (e.g., connection refused, timeout, invalid
  credentials, invalid configuration).
- The wizard stays on the same step until a successful test.

Common root causes are listed under **Troubleshooting**.

> **Expert Mode (skip test)**
> The backend supports a `connection_test` phase with `action = "skip"` for
> automation and advanced API usage. The UI wizard is intentionally strict and
> requires a successful connection test before proceeding, to avoid deploying
> untested tools.

### Fields

- **Requires Authentication**
  - If disabled:
    - No secret fields are required.
  - If enabled:
    - **Secret Name** (required)
    - **Secret Value** (required, masked)
    - Optional expiration date (when exposed in UI)

### How Secrets Are Handled

- Secrets are **never** logged in plaintext.
- On commit:
  - Secret values are passed to the backend once.
  - Stored using `SecretsManager` with encryption in the database.
  - Only a reference (secret name) is kept on the tool record.
- When you later test or execute the tool:
  - The execution pipeline retrieves and decrypts the secret server-side.

### Admin Actions

1. Toggle **Requires Authentication**:
   - Disabled for unauthenticated local tools.
   - Enabled for tools that require API keys, tokens, or passwords.
2. If enabled, enter **Secret Name** and **Secret Value**.
3. Click **Next**.

If required fields are missing when authentication is enabled, the wizard shows
validation errors and prevents navigation.

---

## Phase 5 – Permissions & Limits

Configure how the tool can be used, and by whom.

### Fields

- **Rate Limit (per minute)** (optional)
  - Maximum allowed invocations per minute.
- **Max Concurrent Calls**
  - Default `5`, must be ≥ 1 and ≤ 100.
- **Health Check Interval (seconds)** (when exposed)
  - Default `300`, minimum `60`.
- **Role-based Permissions** (backend model)
  - For each role:
    - `can_view`
    - `can_use`
    - `can_configure`
    - Optional per-role rate limits

The current UI exposes the core limit fields and a `role_permissions` payload
that is sent to the backend; defaults are secure (no permissions granted unless
you explicitly configure them).

### Default Behaviors

- New tools are created with `is_enabled = false`.
- Permissions are “default deny”:
  - No role can view/use/configure the tool until configured.
- Admin role can always manage tools via admin APIs.

### Admin Actions

1. Set global rate limit and concurrency as required.
2. Configure per-role permissions if available in your deployment.
3. Click **Next**.

---

## Phase 6 & 7 – Review, Confirm, and Commit

The **Review & Confirm** step corresponds to the backend **review** and
**commit** phases.

### Review Summary

You will see a read-only summary including:

- **Basic Information:**
  - Tool ID, Name, Category, Purpose
- **MCP Configuration:**
  - Server type (STDIO/HTTP/SSE)
  - Endpoint or command summary
- **Connection Test:**
  - Whether the test succeeded
  - Tool count discovered (if available)
- **Security:**
  - Whether authentication is required
  - Secret names only (values are **never** shown)
- **Permissions & Limits:**
  - Rate limits and core limits

### Committing the Registration

When you click **Register Tool**:

1. The frontend sends a **review** phase with `action = "confirm"`.
2. Then sends a **commit** phase with `confirmed = true`.
3. The backend:
   - Starts a database transaction.
   - Creates the tool record.
   - Stores secrets via `SecretsManager`.
   - Creates permission entries.
   - Optionally attaches discovered capabilities and parameter schemas.
   - Commits or rolls back as a single atomic unit.
4. The registration session is cleaned up.

On success you will see a snackbar message confirming registration and be
redirected back to the **Admin Tools** list.

On failure you will see an error message; the session remains so you can
correct configuration and retry.

---

## Drafts, Autosave & Resuming

The wizard includes draft management so you can pause and resume safely.

### How Drafts Work

- Drafts are stored in the browser using `localStorage`.
- Each draft includes:
  - Current step index
  - Phase data collected so far
  - Associated backend registration session ID (if created)
- Drafts expire after **1 hour** of inactivity.

### When Drafts Are Saved

- The wizard debounces changes and periodically saves the latest data.
- When you click **Next** on a step, data for that step is persisted into the
  draft.

### Resuming a Draft

1. Open **Register New MCP Tool** again.
2. If a valid draft exists, it is loaded automatically:
   - Forms are pre-populated.
   - The stepper jumps to your last step.
3. Continue from where you left off and complete the workflow.

### Canceling a Registration

- Clicking **Cancel**:
  - Optionally informs the backend to delete the registration session.
  - Returns you to the **Admin Tools** list.
  - The local draft remains for up to 1 hour unless you explicitly clear it.

---

## Troubleshooting

### Connection Test Failures

**Symptoms:**

- “Connection failed: …” message on the Connection Test step.
- No tools discovered.

**Common Causes & Fixes:**

- **Server not running**
  - Ensure the MCP server process/container is up and reachable.
  - For STDIO, verify the command path and environment.
  - For HTTP/SSE, confirm the host and port.
- **Network issues**
  - Local firewall blocking the port.
  - Wrong hostname or protocol (HTTP vs HTTPS).
- **Timeouts**
  - Server is slow to respond; increase timeout seconds in MCP config.
  - Check MCP server logs for long-running operations.
- **MCP protocol errors**
  - Server does not implement the expected MCP spec.
  - Check the tool’s documentation and ensure you are using a compatible
    version.

If tests continue to fail, capture the error message and consult the tool
owner or platform team.

### Validation Errors

**Symptoms:**

- Cannot proceed to the next step; error messages shown under fields.
- API responses include validation errors.

**Common Fields to Check:**

- Tool ID pattern (lowercase slug, no spaces).
- Missing required fields (marked with `*`).
- Invalid URL format (must start with `http://` or `https://`).
- Timeout or numeric fields outside permitted ranges.

### Session Expiry

**Symptoms:**

- Request fails with a message that the registration session has expired.
- You are returned to an earlier step or asked to start again.

**Cause & Fix:**

- Sessions expire after **1 hour** of inactivity to reduce risk.
- Start a new registration or re-open the wizard; the latest draft from the
  browser may still restore your forms if saved recently.

### Permission Configuration Issues

**Symptoms:**

- Tool registers successfully but does not appear for certain users.
- Tool invocations fail with permission errors.

**Checklist:**

- Confirm global tool status:
  - Tool is created and not archived.
- Check RBAC:
  - Roles configured in **Permissions & Limits** match your organization’s
    role names.
- Verify rate limits:
  - Per-user or per-role rate limits are not set too low.

If you suspect a permission misconfiguration, coordinate with the security or
platform team to review the effective RBAC matrix.

---

## Best Practices

### Naming Conventions for Tool IDs

- Use **lowercase slugs**:
  - `vendor_system_action` (e.g., `qdrant_vector_search`)
- Avoid:
  - Spaces, uppercase letters, and ambiguous abbreviations.
- Keep tool IDs stable over time; use separate IDs for major variations.

### Security Recommendations

- Treat all secrets as production-grade:
  - Avoid using personal or test API keys in shared environments.
  - Rotate secrets regularly and update tool configuration as needed.
- Limit access:
  - Grant `can_use` only to roles that truly need the tool.
  - Separate configuration permissions (`can_configure`) from usage.
- Review logs:
  - Use tool invocation logs and health checks to monitor misuse or anomalies.

### Permission Matrix Design

- Start with the most restrictive settings:
  - No roles configured; then add only the necessary ones.
- Common pattern:
  - `analyst` – `can_view`, `can_use`
  - `lead` – `can_view`, `can_use`, `can_configure` for specific tools
  - `admin` – full access via admin APIs
- Consider different rate limits per role when tools are expensive or
  impact external systems.

### When to Skip Connection Tests

- **Strongly recommended:** Always run a connection test in the wizard before
  committing registration.
- Only consider skipping (via API, not UI) when:
  - You are migrating many known-good tools programmatically.
  - Connectivity is temporarily restricted but you must pre-stage tool
    metadata.
- If you skip tests programmatically, clearly mark those tools and schedule
  follow-up validation once connectivity is available.

---

## FAQ

### 1. How does an admin start the registration wizard?

From the **Admin Tools** dashboard, click **Register New MCP Tool** to open the
wizard and follow the six-step flow.

### 2. What happens if the connection test fails?

The wizard shows a failure message, does **not** allow you to proceed, and
keeps your configuration so you can adjust details and re-run the test. No
tool is created until the commit phase succeeds.

### 3. How are secrets handled securely?

Secrets are submitted once during registration, encrypted via
`SecretsManager`, and stored separately from the tool record. They are never
returned to the UI or written to logs in plaintext.

### 4. What permissions are required?

Only users with the **Admin** role can access the registration endpoints and
wizard. Runtime access to the tool is controlled separately through role-based
permissions configured in the **Permissions & Limits** phase.

### 5. How can registration be resumed after interruption?

If you close the browser or navigate away, the wizard saves a draft in the
browser and the backend keeps the session alive for about an hour. When you
re-open **Register New MCP Tool**, your draft is loaded and you can continue.

---

## Related Documentation

- **Security Classification:**
  `docs/development/adrs/ADR-057-MCP-Tool-Security-Classification.md`
- **Architecture Decision:**
  `docs/development/adrs/ADR-056-MCP-Tool-Registration-Workflow.md`
- **Implementation Spec:**
  `docs/development/specs/TOOLS_T5_MCP_TOOL_REGISTRATION_SPEC.md`
- **Backend Implementation:**
  `docs/development/completed/tasks/T5-F1-MCP-TOOL-REGISTRATION-BACKEND.md`
- **Frontend Implementation:**
  `docs/development/completed/tasks/T5-F2-MCP-TOOL-REGISTRATION-FRONTEND.md`
- **Developer Guide (API & Integration):**
  `docs/development/guides/adding-mcp-tools.md`
- **Tools Architecture Diagrams:**
  `docs/architecture/TOOLS_ARCHITECTURE_DIAGRAMS.md`
