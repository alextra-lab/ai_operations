# ADR-056: MCP Tool Registration Workflow

**Status:** Accepted
**Date:** 2025-11-24
**Deciders:** Architecture Team
**Tags:** tools, mcp, security, ux, administration

---

## Context

**What is the issue we're addressing?**

The AI Operations Platform platform supports the Model Context Protocol (MCP) for integrating external tools. Currently, tools can only be registered through direct database manipulation or low-level API calls, which:

1. **Lacks User Guidance**: No guided workflow for administrators to register tools properly
2. **Missing Validation**: No pre-registration validation of tool connectivity or capabilities
3. **Error-Prone**: Manual configuration without immediate feedback leads to misconfigured tools
4. **Security Gap**: No clear workflow integration with existing security/permission systems
5. **Poor UX**: Requires technical expertise and database knowledge to add new tools

**Background Context:**

- Existing tool infrastructure is in place (database models, services, MCP clients)
- Security framework exists with RLS policies, secrets management, and RBAC
- Tool discovery service can connect to MCP servers and enumerate capabilities
- Admin APIs support CRUD operations but lack a cohesive registration workflow
- Current implementation requires multi-step manual process across different endpoints

**What needs to be decided?**

How should we design a guided, secure, and user-friendly MCP tool registration workflow that:

- Validates tool configuration before registration
- Tests connectivity to MCP servers
- Automatically discovers tool capabilities
- Integrates seamlessly with existing security/permission systems
- Provides clear feedback and error handling
- Maintains audit trail for compliance

**Forces at play:**

**Technical:**

- Need to support stdio, HTTP, and SSE MCP server types
- Must validate tool connectivity before database persistence
- Should discover capabilities automatically where possible
- Need atomic registration (all-or-nothing)

**Security:**

- Admin-only operation (high privilege)
- Secrets must be encrypted immediately
- Default permissions should be restrictive (opt-in, not opt-out)
- Audit logging required for compliance

**UX:**

- Multi-step process needs clear progress indication
- Errors should be actionable and specific
- Should support both guided wizard and quick registration
- Preview capabilities before final confirmation

**Operational:**

- Tools should start disabled by default (manual enablement)
- Registration failure should not leave partial records
- Should support registration rollback/cleanup

---

## Decision

**We will implement a multi-phase MCP Tool Registration Workflow**

### Core Principles

1. **Guided Multi-Step Process**: Registration follows a clear workflow with validation at each step
2. **Test-Before-Commit**: Validate connectivity and discover capabilities before database persistence
3. **Security-First**: Integrate with existing authentication, authorization, and secrets management
4. **Atomic Operations**: Registration either fully succeeds or fully fails (no partial state)
5. **Defaults to Secure**: Tools start disabled with no permissions until explicitly configured

### Registration Workflow Phases

#### Phase 1: Basic Information

**User provides:**

- Tool name (human-readable) - **REQUIRED**
- Tool description - **REQUIRED** (clear explanation of what the tool does)
- Execution location (External Tool vs Internal Data Access) - **REQUIRED**
- Tool category (optional, defaults to "custom")
- Provider information (optional)

**System auto-generates:**

- Tool ID (derived from name, e.g., "Docker MCP Gateway" → `docker_mcp_gateway`)

**Backend validates:**

- Tool ID uniqueness (auto-generated)
- Valid execution location (maps to `tool_purpose` and `service_location`)
- Required fields present (name, description)

**UX Improvements (2025-11-27):**

- Tool ID is auto-generated from name to prevent formatting errors
- Description is required and prominent (helps users understand tool purpose)
- Category is optional (defaults to "custom" for flexibility)
- **tool_purpose/service_location hidden from UI** - defaults to "orchestrator" for all tools

**Why hide tool_purpose?**

The `tool_purpose` field is an internal architectural routing decision, not a meaningful user choice:

1. **Docker MCP Gateway example**: A gateway can contain PostgreSQL, reasoning, and web scraping MCPs - it doesn't fit any single category
2. **The question "where does code run?" is wrong**: Users care about *what* a tool does, not *where* it executes
3. **99% of MCP tools are "orchestrator"**: External processes, Docker containers, HTTP endpoints
4. **"retrieval" is platform-internal only**: Reserved for tools needing direct internal database access

For advanced use cases (platform-internal tools), administrators can use the direct API to set `tool_purpose = "retrieval"`.

#### Phase 2: MCP Configuration

**User provides:**

- MCP server type (stdio, HTTP, SSE)
- Connection details:
  - **stdio**: Command array (e.g., `["python", "mcp_server.py"]`)
  - **HTTP/SSE**: Endpoint URL
- MCP protocol version (default: 2024-11-05)
- Timeout configuration

**Backend validates:**

- Valid server type
- Required connection details present
- URL format validation for HTTP/SSE
- Command array format for stdio

#### Phase 3: Security Configuration

**User configures:**

- Authentication requirements (yes/no)
- If yes:
  - Authentication type (api_key, oauth, basic, custom)
  - Secret name (unique identifier)
  - Secret value (encrypted immediately)

#### Phase 4: Connection Testing & Discovery

**System performs:**

1. Create temporary MCP client with provided configuration and credentials from phase 3
2. Attempt connection to MCP server with authentication (if required)
3. Initialize MCP session
4. Discover available tools and capabilities
5. Retrieve parameters schema
6. Disconnect cleanly

**User sees:**

- Connection status (success/failure with details)
- Discovered tools list
- Server capabilities
- Parameters schema preview
- Connection response time

**Decision point:**

- If connection fails: User can edit configuration and retry
- If connection succeeds: User reviews discovered capabilities
  - Secret expiration (optional)
- Additional configuration options (tool-specific JSON)

**Backend performs:**

- Encrypt secret value using existing SecretsManager
- Store encrypted secret separately from tool record
- Validate secret name uniqueness

#### Phase 5: Permissions & Limits

**User configures:**

- Execution limits:
  - Timeout seconds (default: 30s, max: 300s)
  - Rate limit per minute (optional)
  - Max concurrent calls (default: 5)
  - Health check interval (default: 300s)
- Initial permissions (per role):
  - can_view (default: false)
  - can_use (default: false)
  - can_configure (default: false)
  - Per-role rate limits (optional)

**Default behavior:**

- Tool starts disabled (`is_enabled = false`)
- No roles have permission by default (explicit grant required)
- Admin role bypasses permission checks

#### Phase 6: Review & Confirmation

**User reviews:**

- Complete tool configuration summary
- Discovered capabilities
- Security settings (secrets masked)
- Permission matrix
- Estimated resource requirements

**User confirms or edits:**

- Go back to any step to modify
- Cancel registration (no persistence)
- Confirm registration (atomic commit)

#### Phase 7: Registration Commit

**Backend performs atomically:**

1. Begin database transaction
2. Create tool record
3. Create secret record (if applicable)
4. Create permission records
5. Create initial health check record
6. Log audit event
7. Commit transaction

**On success:**

- Return complete tool record
- Schedule first health check
- Return tool UUID and configuration

**On failure:**

- Rollback transaction completely
- Return detailed error message
- No partial records remain

### API Design

#### New Endpoint: POST /api/v1/admin/tools/register

**Multi-phase registration workflow endpoint**

```python
class ToolRegistrationPhase(str, Enum):
    BASIC_INFO = "basic_info"
    MCP_CONFIG = "mcp_config"
    CONNECTION_TEST = "connection_test"
    SECURITY_CONFIG = "security_config"
    PERMISSIONS = "permissions"
    REVIEW = "review"
    COMMIT = "commit"

class ToolRegistrationRequest(BaseModel):
    phase: ToolRegistrationPhase
    session_id: str  # Track multi-step workflow
    data: dict[str, Any]  # Phase-specific data

class ToolRegistrationResponse(BaseModel):
    session_id: str
    current_phase: ToolRegistrationPhase
    next_phase: ToolRegistrationPhase | None
    validation_errors: list[str]
    discovered_capabilities: dict[str, Any] | None
    tool_id: UUID | None  # Only set after commit
```

**Alternative: Simplified Endpoint**

For experienced users or automation, maintain existing:

- POST /api/v1/admin/tools (direct creation with all fields)

### UI Design (Angular Frontend)

**Component Structure:**

```
ToolRegistrationWizardComponent
├── BasicInfoStepComponent
├── McpConfigStepComponent
├── ConnectionTestStepComponent
├── SecurityConfigStepComponent
├── PermissionsStepComponent
└── ReviewConfirmStepComponent
```

**Features:**

- Angular Material Stepper for workflow
- Real-time validation feedback
- Connection test with loading indicator
- Capability preview component
- Permission matrix editor
- Breadcrumb navigation
- Save draft functionality (browser storage)

### Integration with Existing Systems

**Security Integration:**

- Uses existing `admin_required` decorator
- Leverages `SecretsManager` for encryption
- Creates `ToolPermission` records via `ToolPermissionService`
- Respects existing RLS policies

**Tool Infrastructure:**

- Uses `ToolService.create_tool()` for persistence
- Uses `ToolDiscoveryService` for capability discovery
- Uses `create_mcp_client()` for connection testing
- Integrates with `ToolHealthMonitor` for initial health check

**Audit & Observability:**

- Logs all registration attempts (success/failure)
- Records tool creation in `tools.created_by`
- First health check scheduled immediately
- Audit event created for compliance

---

## Alternatives Considered

### Option 1: Single-Step Registration (Current State)

**Description:** Continue with direct API endpoint requiring all fields upfront

**Pros:**

- Simpler implementation
- Faster for experienced users
- Less state management

**Cons:**

- Poor user experience
- No validation until submission
- Configuration errors discovered late
- No capability preview
- Error-prone for new users

**Why Rejected:** Doesn't solve the core UX and validation problems

### Option 2: Automatic Registration via URL

**Description:** User provides only MCP server URL, system auto-discovers everything

**Pros:**

- Minimal user input
- Fast registration
- Less room for error

**Cons:**

- Not all MCP servers support auto-discovery
- Stdio tools require command specification
- Security configuration still needs manual input
- Permission setup still required
- Less flexibility for custom configurations

**Why Rejected:** Too magical, doesn't work for all MCP server types

### Option 3: Configuration File Upload

**Description:** User uploads YAML/JSON configuration file for tool registration

**Pros:**

- Good for bulk operations
- Version control friendly
- Easy to replicate tools

**Cons:**

- Requires external file preparation
- No guided workflow
- No connection validation before upload
- Poor error feedback
- Not user-friendly for ad-hoc registration

**Why Rejected:** Better suited as a complementary feature, not primary workflow

### Option 4: Two-Phase Registration (Basic + Advanced)

**Description:** Simplified two-step process: basic info then everything else

**Pros:**

- Simpler than full wizard
- Faster for experienced users
- Less state management

**Cons:**

- Still requires all details upfront in phase 2
- No incremental validation
- Connection testing happens after configuration entry
- Less guidance for users
- Harder to provide specific error feedback

**Why Rejected:** Doesn't provide enough structure and guidance

---

## Consequences

### Positive Consequences

**User Experience:**

- Clear, guided workflow reduces registration errors
- Immediate validation feedback at each step
- Connection testing prevents misconfigured tools
- Capability preview shows what tools can do
- Error messages are actionable and specific

**Security:**

- Secrets encrypted immediately upon entry
- Default-deny permission model
- Tools start disabled (manual enablement)
- Complete audit trail for compliance
- Integration with existing security framework

**Reliability:**

- Pre-registration validation catches issues early
- Atomic operations prevent partial states
- Connection testing verifies tool availability
- Automatic capability discovery reduces manual errors

**Maintainability:**

- Clear separation of concerns (phases)
- Reusable validation logic
- Testable workflow steps
- Backend and frontend decoupled via clear API contract

### Negative Consequences

**Complexity:**

- Multi-step workflow adds UI/UX complexity
- Session state management required for wizard
- More frontend components to maintain
- More comprehensive testing required

**Performance:**

- Connection testing adds latency to registration
- Discovery phase may take several seconds
- Multiple API calls vs single registration endpoint
- Network timeouts possible during testing

**Development Effort:**

- Requires both backend and frontend development
- More extensive testing required (unit + integration + E2E)
- UI/UX design and refinement needed
- Documentation and user guides required

**User Friction:**

- More steps to complete registration
- May be perceived as "too much process" by power users
- Requires maintaining state across multiple steps
- More clicks to complete registration

### Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Wizard state loss** | Medium | Store draft in browser localStorage; backend session with expiry |
| **Connection test timeout** | High | Configurable timeout; clear error messages; retry mechanism |
| **Partial registration on failure** | High | Database transactions; rollback on error; cleanup handlers |
| **MCP server unavailable during test** | Medium | Allow skip of connection test (expert mode); warning about untested tools |
| **Session hijacking** | Low | Session tokens tied to user; short expiry; CSRF protection |
| **Discovery returns invalid schema** | Medium | Schema validation; fallback to manual entry; error recovery |
| **User abandons mid-workflow** | Low | Save draft functionality; resume later; session timeout cleanup |
| **Secrets exposure in logs** | High | Use existing logging redaction; never log secret values; audit secret access |
| **Concurrent registration conflicts** | Low | Tool ID uniqueness constraint; optimistic locking; clear error message |

---

## Implementation Notes

### Phase 1: Backend API (T5-F1)

**Files to create/modify:**

- `src/orchestrator/app/routers/tools_registration.py` (NEW)
- `src/orchestrator/app/services/tool_registration_service.py` (NEW)
- `src/orchestrator/app/schemas/tool_registration.py` (NEW)

**Key features:**

- Multi-phase registration endpoint
- Session management for workflow
- Connection testing logic
- Atomic registration commit
- Validation at each phase

**Testing:**

- Unit tests for each phase
- Integration test for full workflow
- Error handling tests
- Connection test mocking

### Phase 2: Angular UI (T5-F2)

**Files to create:**

- `src/frontend-angular/src/app/pages/tools/tool-registration-wizard/` (NEW directory)
  - `tool-registration-wizard.component.ts`
  - `tool-registration-wizard.component.html`
  - `tool-registration-wizard.component.scss`
- `src/frontend-angular/src/app/pages/tools/tool-registration-wizard/steps/` (NEW)
  - `basic-info-step.component.ts`
  - `mcp-config-step.component.ts`
  - `connection-test-step.component.ts`
  - `security-config-step.component.ts`
  - `permissions-step.component.ts`
  - `review-confirm-step.component.ts`
- `src/frontend-angular/src/app/api/services/tool-registration.service.ts` (NEW)

**Key features:**

- Angular Material Stepper
- Form validation per step
- Connection test progress indicator
- Capability preview display
- Permission matrix editor
- Draft save/restore

**Testing:**

- Component unit tests
- Form validation tests
- Integration tests with mock API
- E2E tests for full workflow

### Phase 3: Documentation

**Files to update:**

- `docs/user-guides/admin-tool-registration.md` (NEW)
- `docs/api/tools-registration-api.md` (NEW)
- `docs/development/guides/adding-mcp-tools.md` (UPDATE)
- `docs/architecture/TOOLS_ARCHITECTURE_DIAGRAMS.md` (UPDATE)

### Migration Strategy

1. Implement backend API first (no breaking changes)
2. Maintain existing POST /api/v1/admin/tools endpoint
3. Add new registration wizard UI
4. Support both workflows in parallel
5. Eventually deprecate direct tool creation in UI (keep API for automation)

### Dependencies

- Existing tool infrastructure (models, services, MCP clients)
- Existing security framework (auth, permissions, secrets)
- Angular Material (Stepper, Forms, Progress)
- Existing ToolService, ToolDiscoveryService, SecretsManager

### Testing Strategy

**Unit Tests (90%+ coverage):**

- Each registration phase validation
- Connection testing logic
- Session management
- Error handling
- Permission creation

**Integration Tests (80%+ coverage):**

- Full registration workflow (mocked MCP server)
- Security integration
- Database transactions
- API endpoint responses

**E2E Tests:**

- Complete registration wizard flow
- Error scenarios (connection failures, validation errors)
- Draft save/restore
- Permission configuration

**Security Testing:**

- Secret encryption verification
- Permission enforcement
- Audit logging verification
- Input sanitization

---

## References

- [ADR-001: Hybrid Tools Architecture](ADR-001-hybrid-tools-architecture.md)
- [ADR-049: Unified Authentication and Security Implementation](ADR-049-Unified-Authentication-Security-Implementation.md)
- [Tools Implementation Plan](../plans/TOOLS_IMPLEMENTATION_PLAN.md)
- [Tools Implementation Plan Part 2](../plans/TOOLS_IMPLEMENTATION_PLAN_PART2.md)
- [Tools Architecture Diagrams](../../architecture/TOOLS_ARCHITECTURE_DIAGRAMS.md)
- [MCP Protocol Specification](https://modelcontextprotocol.io/specification/)
- **External Research:**
  - [MCP Security Considerations (Writer.com)](https://writer.com/engineering/mcp-security-considerations/)
  - [Policy-Based Access Control for MCP (arXiv)](https://arxiv.org/abs/2506.01333)

---

## Status Updates

### 2025-11-24 - Accepted

**Changed By:** Architecture Team
**Reason:** Approved after review. Addresses UX gap in tool registration, integrates with existing security framework, provides clear implementation path.

**Next Steps:**

1. Create feature implementation task (T5-F1, T5-F2)
2. Update MASTER_ROADMAP.md
3. Begin backend API implementation
4. Design UI mockups for registration wizard

### 2025-11-27 - UX Refinements

**Changed By:** Development Team
**Reason:** User feedback and usability testing revealed several UX issues in the initial implementation.

**Changes Made:**

1. **Tool ID Auto-Generation**: Tool ID is now automatically generated from the tool name (e.g., "Docker MCP Gateway" → `docker_mcp_gateway`). Users no longer need to manually enter a slug-formatted ID.

2. **Description Required**: Description field is now required and prominently placed. Clear descriptions help users understand what tools do.

3. **Simplified "Purpose" → "Execution Location"**: The confusing `tool_purpose` field has been relabeled as "Execution Location" with clear explanations:
   - **External Tool (Orchestrator)**: External APIs, reasoning tools, Docker MCP tools
   - **Internal Data Access (Retrieval Service)**: Direct access to internal databases (PostgreSQL, Qdrant)

4. **Category Now Optional**: Category field defaults to "custom" and is no longer required. Most MCP tools (especially aggregators like Docker MCP Toolkit) don't fit neatly into predefined categories.

5. **Fixed 405 API Error**: Corrected trailing slash mismatch between frontend POST and backend route definition.

**Rationale:**

The original design assumed users would understand the internal architecture concepts (`tool_purpose`, `service_location`). In practice:

- **Docker MCP Toolkit** exposes multiple heterogeneous tools through a gateway - categories don't apply
- Users want to describe *what* a tool does, not *where* it runs
- Auto-generating IDs eliminates a common source of validation errors
- The hybrid architecture (Retrieval vs Orchestrator) is an implementation detail users shouldn't need to understand deeply

**Tool Purpose (Hidden Default):**

All tools registered through the UI default to `tool_purpose = "orchestrator"` and `service_location = "orchestrator"`.

| Scenario | tool_purpose | service_location | How to Set |
|----------|--------------|------------------|------------|
| **Standard MCP tools** (99% of cases) | `orchestrator` | `orchestrator` | Default (UI) |
| Docker MCP Gateway, Context7, Reasoning | `orchestrator` | `orchestrator` | Default (UI) |
| Platform-internal DB tools | `retrieval` | `retrieval_service` | Direct API only |

The "retrieval" option is intentionally NOT exposed in the UI because:

- It's an internal architectural detail users shouldn't need to understand
- Docker MCP Gateway containing a PostgreSQL MCP still runs in orchestrator (the internal PostgreSQL MCP connects to *its own* database, not ours)
- Only platform engineers configuring direct internal database access tools would use this

**Files Modified:**

- `src/orchestrator/app/routers/tools_registration.py` - Fixed trailing slash route
- `src/frontend-angular/src/app/pages/admin/tool-registration-wizard/tool-registration-wizard.component.ts` - Auto-generate tool_id, sync service_location
- `src/frontend-angular/src/app/pages/admin/tool-registration-wizard/tool-registration-wizard.component.html` - Simplified form, better labels
- `src/frontend-angular/src/app/pages/admin/tool-registration-wizard/tool-registration-wizard.component.scss` - Tool ID preview styling

---

**Template Version:** 1.0
**Based On:** [Michael Nygard's ADR pattern](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
