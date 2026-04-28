# Tools T5: MCP Tool Registration UX – Specification

**Status:** ✅ IMPLEMENTED
**Date:** 2025-11-24
**Completed:** 2025-11-24
**Related ADRs:** `ADR-001-hybrid-tools-architecture.md`,
`ADR-056-MCP-Tool-Registration-Workflow.md`
**Related Tasks:** `T5-F1-MCP-TOOL-REGISTRATION-BACKEND.md` ✅,
`T5-F2-MCP-TOOL-REGISTRATION-FRONTEND.md` ✅

---

## 1. Purpose

Provide a **guided, secure, and auditable workflow** for registering MCP
tools into the existing Tools platform (T1–T4), so that:

- Admins can add/update tools **without direct DB access or raw API calls**.
- Each registration is **validated and tested** before becoming active.
- All registrations are **integrated with secrets, permissions, health,
  and analytics** from day one.

This spec refines the high-level flow from ADR-056 into concrete
requirements for backend and Angular UI implementation.

---

## 2. Scope

### In Scope

- Single-tool, interactive registration via an **admin-only wizard**.
- Support for all MCP transports already implemented:
  - `stdio` (command array)
  - `http` / `sse` (URL endpoint)
- Connection testing and **capability discovery** using existing MCP
  client infrastructure.
- Secure collection of secrets (API keys, passwords, tokens) using
  `SecretsManager`.
- Role-based permission seeding via `ToolPermissionService`.
- Full audit logging of registration attempts and outcomes.

### Out of Scope (Future)

- Bulk registration (CSV/JSON upload or marketplace model).
- Full “Tool marketplace” UX (versioning, ratings, etc.).
- Automatic per-environment promotion (dev → test → prod).

---

## 3. Actors & User Stories

### Actors

- **Admin** – allowed to create, update, and delete tools.
- **Developer** – can see/use tools once configured, but does *not*
  perform registration.
- **System** – MCP clients, health monitor, analytics, orchestrator.

### Key Stories

1. **Admin registers a new MCP tool**
   - Starts wizard from Tools dashboard.
   - Provides basic metadata and MCP connection details.
   - Runs connection test and sees discovered tools/capabilities.
   - Configures authentication and secrets.
   - Assigns initial permissions and rate limits.
   - Reviews summary and confirms.
   - Tool appears in Tools dashboard as **disabled but healthy**.

2. **Admin resumes an interrupted registration**
   - Returns to wizard and is offered to resume an in-progress session.
   - Views collected data and validation status per phase.
   - Can edit any previous phase before committing.

3. **Admin abandons/cancels registration**
   - Cancels an in-progress registration.
   - Registration session is cleaned up server-side.
   - No partial tool records remain in the database.

---

## 4. Functional Requirements

### FR1 – Multi-Phase Workflow

- Phases match ADR-056:
  - `basic_info`, `mcp_config`, `connection_test`, `security_config`,
    `permissions`, `review`, `commit`.
- Each phase:
  - Receives **phase-specific input**.
  - Performs **validation**.
  - Returns:
    - `session_id`
    - `current_phase`
    - `next_phase | null`
    - `validation_errors`
    - `can_proceed` flag.
- Session expiry:
  - Default **1 hour** inactive timeout.
  - Expired sessions are cleaned automatically and cannot be resumed.

### FR2 – Connection Testing & Discovery

- Uses existing MCP client infrastructure (`ToolDiscoveryService`).
- For `action = "test"`:
  - Attempt client connect → initialize → list tools.
  - Capture:
    - `response_time_ms`
    - `server_capabilities`
    - `discovered_tools` (list of tools and schemas).
  - Store test result in session and expose to UI.
- For `action = "skip"`:
  - Mark session with a warning:
    - “Connection not tested – tool may not work correctly.”
- Timeouts are configurable (default 30s) and surfaced to the user.

### FR3 – Security & Secrets

- If `requires_authentication = true`:
  - `secret_name` and `secret_value` are **required**.
  - `secret_value` is:
    - Never logged.
    - Stored via `SecretsManager.store_secret()` during commit.
- Secret types:
  - At least `api_key`, `password`, `oauth_token`, `custom`.
- Admin can:
  - Provide an optional `secret_expires_at`.
  - Change secrets later via existing admin tools endpoints.

### FR4 – Permissions & Limits

- Wizard configures:
  - `rate_limit_per_minute` (optional).
  - `max_concurrent_calls` (default 5).
  - `health_check_interval_seconds` (default 300).
  - Per-role permissions (`role_permissions` list):
    - `role`, `can_view`, `can_use`, `can_configure`,
      `max_calls_per_hour`, `max_calls_per_day`.
- Enforcement:
  - Tool starts with `is_enabled = false`.
  - Permissions are created using `ToolPermissionService.grant_permission`.
  - Admin can later change permissions via existing admin UI/API.

### FR5 – Atomic Commit

- Commit phase:
  - Builds `ToolCreate` from merged session data.
  - Starts a DB transaction.
  - Creates:
    - Tool record.
    - Secret record (if any).
    - Permission records.
  - Optionally stores discovered capabilities into `tool.capabilities`.
  - Commits or rolls back as one unit.
- On failure:
  - Roll back transaction and return a clear error.
  - Session remains available for correction and retry.

### FR6 – Audit & Observability

- All registration attempts (per phase) logged with:
  - `session_id`, `user_id`, `phase`, `success/failure`, summary error.
- Final commit log includes:
  - `tool_id` (UUID and slug)
  - `categories`, `service_location`, `tool_purpose`.
- No secret values appear in logs; ensure redaction is applied.

---

## 5. UI Requirements (Angular)

The frontend is specified in more detail in `T5-F2-MCP-TOOL-REGISTRATION-FRONTEND.md`.
This spec captures the **contract** with the backend and the essential UX.

### UR1 – Wizard Shell

- `ToolRegistrationWizardComponent`:
  - Uses Angular Material Stepper.
  - Shows high-level progress and current step.
  - Supports **Cancel**, which:
    - Saves a draft to `localStorage`.
    - Optionally calls backend cancel when user explicitly abandons.
- On load:
  - If a draft exists, offers to **resume**.

### UR2 – Phase Forms

- Each phase has a dedicated child component:
  - Emits `complete` event with phase-specific data.
  - Shows inline field errors and top-level validation messages from
    the backend (`validation_errors`).
- Client-side validation mirrors Pydantic constraints:
  - Required fields.
  - URL format.
  - Enum values.
  - Min/max ranges for numeric fields.

### UR3 – Connection Test UX

- Shows:
  - Test button, loading indicator, status pill.
  - Response time on success.
  - Summary of discovered tools and capabilities.
- On failure:
  - Clear error message and remediation hints.
  - “Retry” and “Skip (expert mode)” options.

### UR4 – Review & Confirm

- Review step shows:
  - Basic info, MCP config, connection result (or skip warning),
    security config (masked secret), and permissions table.
- Requires explicit confirmation (checkbox) before enabling the
  **Register** button.
- On successful commit:
  - Clears local draft.
  - Navigates to the **Tools dashboard** or tool detail page.

---

## 6. Non-Functional Requirements

### NFR1 – Security

- Admin-only access enforced via existing auth (`admin_required` /
  equivalent).
- CSRF protection and standard FastAPI/Angular security measures.
- No secrets logged or returned to the UI.
- Sessions cannot be accessed across users.

### NFR2 – Performance

- Phase requests should complete in:
  - < 200ms for non-connection-test phases.
  - < 30s for connection tests (timeout path).
- Session lookup and validation should remain O(1) for practical
  cardinalities (in-memory store is acceptable for first iteration).

### NFR3 – Reliability

- Connection test failures must **not** create partial tool records.
- Session store must handle concurrent registration attempts by the
  same or different admins without cross-contamination.

---

## 7. Dependencies

- Tools infrastructure T1–T4 (already implemented):
  - `ToolService`, `ToolPermissionService`, `SecretsManager`,
    `ToolDiscoveryService`, MCP clients, health monitor, analytics.
- Auth framework with admin roles and JWTs.
- Existing Tools Track APIs (admin/developer/health/analytics).

---

## 8. Acceptance Criteria

1. **End-to-end registration:**
   - Admin can register a new tool via wizard.
   - New tool appears in Tools dashboard with correct status.
2. **Validation & testing:**
   - All phases enforce required fields and constraints.
   - Connection tests surface clear success/failure information.
3. **Security:**
   - Secrets are encrypted and never logged.
   - Non-admin users cannot access registration endpoints.
4. **Consistency:**
   - Registered tools behave identically to those created via existing
     admin APIs.
5. **Docs & Roadmap:**
   - `MASTER_ROADMAP.md` Tools Track T5 section references this spec,
     ADR-056, and the T5 tasks.

---

## 9. References

- `development/plans/MASTER_ROADMAP.md` – Tools Track (T1–T5)
- `development/plans/TOOLS_IMPLEMENTATION_PLAN.md` (+ Part 2 + Part 3)
- `development/adrs/ADR-001-hybrid-tools-architecture.md`
- `development/adrs/ADR-056-MCP-Tool-Registration-Workflow.md`
- `development/completed/tasks/T5-F1-MCP-TOOL-REGISTRATION-BACKEND.md` ✅
- `development/completed/tasks/T5-F2-MCP-TOOL-REGISTRATION-FRONTEND.md` ✅
