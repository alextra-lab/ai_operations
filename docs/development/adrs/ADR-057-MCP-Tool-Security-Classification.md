# ADR-057: MCP Tool Security Classification

**Status:** Accepted
**Date:** 2025-11-27
**Implementation Date:** 2025-11-27
**Deciders:** Architecture Team, Security Team
**Tags:** tools, mcp, security, risk-management, classification

---

## Context

**What is the issue we're addressing?**

The current MCP tool registration uses `tool_purpose` (retrieval/orchestrator) and `service_location` fields that conflate technical execution location with security concerns. This creates confusion:

1. **Wrong abstraction**: Users asked "where does code run?" instead of "what are the risks?"
2. **Docker MCP Gateway problem**: A gateway containing PostgreSQL + Web Search + Reasoning tools doesn't fit binary classification
3. **No security controls**: Current model doesn't enable risk-based access control
4. **Missing audit requirements**: No way to identify which tools need enhanced logging

**Real-world example:**

An Elasticsearch MCP querying the company datalake is fundamentally different from a web scraping MCP fetching public data, but both were classified the same way.

**What needs to be decided?**

How should we classify MCP tools to enable:

- Risk-based access control in Use Cases
- Appropriate audit and logging levels
- Security approval workflows
- Runtime security controls (sanitization, network policies)

---

## Decision

**Replace `tool_purpose`/`service_location` with security-focused classification attributes.**

### Security Classification Attributes

#### 1. `data_source_type` - Trust Level of Data Source

| Value | Description | Examples | Trust Level |
|-------|-------------|----------|-------------|
| `internal` | Company-controlled data sources | Elasticsearch datalake, internal APIs, company databases | High |
| `external` | Third-party or public sources | Web scraping, public APIs, external services | Low |
| `none` | No data retrieval | Reasoning tools (ClearThought, Sequential Thinking) | N/A |
| `mixed` | Aggregates multiple source types | Docker MCP Gateway with heterogeneous tools | Varies |

#### 2. `data_flow_direction` - How Data Moves

| Value | Description | Risk Concern | Controls |
|-------|-------------|--------------|----------|
| `ingress` | Brings data INTO the system | Untrusted data injection, malicious content | Input validation, sanitization |
| `egress` | Sends data OUT of the system | Data exfiltration, privacy leaks | Output filtering, DLP |
| `bidirectional` | Both directions | Both concerns | Full monitoring |
| `none` | No external data flow | Lowest risk | Minimal controls |

#### 3. `network_access_level` - Network Reach

| Value | Description | Network Policy |
|-------|-------------|----------------|
| `isolated` | No network access (pure computation) | Block all |
| `internal` | Company network only | Allow internal CIDR, block internet |
| `external` | Can reach public internet | Egress proxy, URL allowlisting |

#### 4. `max_data_sensitivity` - Highest Data Classification Allowed

| Value | Description | Compliance Requirement |
|-------|-------------|----------------------|
| `public` | Public data only | None |
| `internal` | Internal/business confidential | Standard audit |
| `confidential` | Sensitive business data | Enhanced audit |
| `restricted` | PII, PHI, regulated data | Full compliance logging |

### Schema Definition

```python
from enum import Enum

class DataSourceType(str, Enum):
    """Trust level of data sources the tool accesses."""
    INTERNAL = "internal"       # Company-controlled sources
    EXTERNAL = "external"       # Third-party/public sources
    NONE = "none"               # No data retrieval (reasoning)
    MIXED = "mixed"             # Aggregated/gateway tools

class DataFlowDirection(str, Enum):
    """Direction of data flow relative to the platform."""
    INGRESS = "ingress"         # Data comes INTO system
    EGRESS = "egress"           # Data goes OUT of system
    BIDIRECTIONAL = "bidirectional"  # Both directions
    NONE = "none"               # No external data flow

class NetworkAccessLevel(str, Enum):
    """Network access requirements for the tool."""
    ISOLATED = "isolated"       # No network access
    INTERNAL = "internal"       # Internal network only
    EXTERNAL = "external"       # Public internet access

class MaxDataSensitivity(str, Enum):
    """Maximum data classification the tool can process."""
    PUBLIC = "public"           # Public data only
    INTERNAL = "internal"       # Internal business data
    CONFIDENTIAL = "confidential"  # Sensitive business data
    RESTRICTED = "restricted"   # PII, PHI, regulated data
```

### Database Schema Update

```sql
-- New columns for tools table
ALTER TABLE tools ADD COLUMN data_source_type VARCHAR(20)
    NOT NULL DEFAULT 'internal'
    CHECK (data_source_type IN ('internal', 'external', 'none', 'mixed'));

ALTER TABLE tools ADD COLUMN data_flow_direction VARCHAR(20)
    NOT NULL DEFAULT 'ingress'
    CHECK (data_flow_direction IN ('ingress', 'egress', 'bidirectional', 'none'));

ALTER TABLE tools ADD COLUMN network_access_level VARCHAR(20)
    NOT NULL DEFAULT 'internal'
    CHECK (network_access_level IN ('isolated', 'internal', 'external'));

ALTER TABLE tools ADD COLUMN max_data_sensitivity VARCHAR(20)
    NOT NULL DEFAULT 'internal'
    CHECK (max_data_sensitivity IN ('public', 'internal', 'confidential', 'restricted'));

-- Deprecate old columns (keep for migration, remove in future)
-- tool_purpose: DEPRECATED - use data_source_type + data_flow_direction
-- service_location: DEPRECATED - all MCPs run in orchestrator

-- Add index for security queries
CREATE INDEX idx_tools_security ON tools(data_source_type, max_data_sensitivity);
```

---

## Use Case Tool Restrictions

### Restriction Model

Use Cases can restrict which tools are allowed based on security attributes:

```python
class UseCaseToolRestrictions(BaseModel):
    """Security-based tool restrictions for a Use Case."""

    # Data source restrictions
    allowed_data_sources: list[DataSourceType] = [
        DataSourceType.INTERNAL,
        DataSourceType.NONE
    ]

    # Data flow restrictions
    allowed_data_flows: list[DataFlowDirection] = [
        DataFlowDirection.INGRESS,
        DataFlowDirection.NONE
    ]

    # Network access restrictions
    allowed_network_access: list[NetworkAccessLevel] = [
        NetworkAccessLevel.ISOLATED,
        NetworkAccessLevel.INTERNAL
    ]

    # Minimum required sensitivity level
    # Tool must support AT LEAST this sensitivity
    required_data_sensitivity: MaxDataSensitivity = MaxDataSensitivity.INTERNAL
```

### Example Use Case Configurations

#### High-Security Use Case (PII Processing)

```json
{
  "use_case_id": "customer_support_pii",
  "name": "Customer Support (PII)",
  "tool_restrictions": {
    "allowed_data_sources": ["internal", "none"],
    "allowed_data_flows": ["ingress", "none"],
    "allowed_network_access": ["isolated", "internal"],
    "required_data_sensitivity": "restricted"
  }
}
```

**Effect:** Only internal data sources, no internet access, tools must be approved for PII.

#### Research Use Case (Open Data)

```json
{
  "use_case_id": "research_analysis",
  "name": "Research & Analysis",
  "tool_restrictions": {
    "allowed_data_sources": ["internal", "external", "none"],
    "allowed_data_flows": ["ingress", "bidirectional", "none"],
    "allowed_network_access": ["isolated", "internal", "external"],
    "required_data_sensitivity": "public"
  }
}
```

**Effect:** Can use any tools, but only for public data analysis.

#### Internal Analytics Use Case

```json
{
  "use_case_id": "internal_analytics",
  "name": "Internal Data Analytics",
  "tool_restrictions": {
    "allowed_data_sources": ["internal", "none"],
    "allowed_data_flows": ["ingress", "none"],
    "allowed_network_access": ["internal"],
    "required_data_sensitivity": "confidential"
  }
}
```

**Effect:** Internal tools only, can handle confidential data, no internet.

---

## Security Controls by Classification

### Audit & Logging

| Attribute | Value | Audit Level |
|-----------|-------|-------------|
| `data_source_type` | `external` | Full request/response logging |
| `data_flow_direction` | `egress` | Alert on sensitive patterns |
| `network_access_level` | `external` | Network traffic logging |
| `max_data_sensitivity` | `restricted` | Compliance audit trail |

### Runtime Controls

| Attribute | Value | Control |
|-----------|-------|---------|
| `data_source_type` | `external` | LLM-Guard output sanitization |
| `data_flow_direction` | `ingress` | Input validation, size limits |
| `data_flow_direction` | `egress` | DLP scanning, output filtering |
| `network_access_level` | `external` | Egress proxy, URL allowlist |

### Approval Workflows

| Attribute | Value | Approval Required |
|-----------|-------|-------------------|
| `data_source_type` | `external` | Security team review |
| `data_flow_direction` | `egress` | Data governance approval |
| `max_data_sensitivity` | `restricted` | Compliance sign-off |
| `network_access_level` | `external` | Network security review |

---

## Docker MCP Gateway Handling

Aggregated gateways like Docker MCP Gateway present a challenge:

### Option A: Register as `mixed` (Recommended)

```json
{
  "tool_id": "docker_mcp_gateway",
  "name": "Docker MCP Gateway",
  "data_source_type": "mixed",
  "data_flow_direction": "bidirectional",
  "network_access_level": "external",
  "max_data_sensitivity": "internal",
  "description": "Aggregated gateway - individual tool capabilities vary"
}
```

**Security policy:** Treat as highest-risk combination until individual tools are classified.

### Option B: Register Individual Tools

If the gateway supports tool discovery, register each internal MCP separately with appropriate classifications.

### Option C: Gateway Metadata

Store known tool classifications in gateway metadata:

```json
{
  "contained_tools": [
    {"name": "postgres_mcp", "data_source_type": "internal"},
    {"name": "web_search", "data_source_type": "external"},
    {"name": "clearthought", "data_source_type": "none"}
  ]
}
```

---

## Migration Plan

### Phase 1: Add New Columns (Non-Breaking)

1. Add new security columns with defaults
2. Keep deprecated columns (`tool_purpose`, `service_location`)
3. Update registration API to accept new fields
4. Update UI to show new classification form

### Phase 2: Migrate Existing Tools

```sql
-- Migrate existing tools based on old classification
UPDATE tools SET
    data_source_type = CASE
        WHEN tool_purpose = 'retrieval' THEN 'internal'
        WHEN category IN ('reasoning', 'documentation') THEN 'none'
        ELSE 'external'
    END,
    data_flow_direction = CASE
        WHEN tool_purpose = 'retrieval' THEN 'ingress'
        WHEN category = 'reasoning' THEN 'none'
        ELSE 'ingress'
    END,
    network_access_level = CASE
        WHEN tool_purpose = 'retrieval' THEN 'internal'
        WHEN category = 'reasoning' THEN 'isolated'
        ELSE 'external'
    END,
    max_data_sensitivity = 'internal'  -- Conservative default
WHERE data_source_type IS NULL;
```

### Phase 3: Enable Use Case Restrictions

1. Add `tool_restrictions` to Use Case schema
2. Implement restriction validation in Orchestrator
3. Add UI for configuring restrictions

### Phase 4: Deprecate Old Fields

1. Log warnings when `tool_purpose`/`service_location` are used
2. Update documentation
3. Remove in next major version

---

## Consequences

### Positive

- ✅ **Risk-based access control**: Use Cases can restrict tools by security profile
- ✅ **Clear audit requirements**: Logging levels based on actual risk
- ✅ **Approval workflows**: Security reviews triggered by classification
- ✅ **Runtime controls**: Appropriate sanitization and monitoring
- ✅ **Gateway support**: `mixed` type handles aggregated tools

### Negative

- ⚠️ **Migration effort**: Existing tools need reclassification
- ⚠️ **User education**: New concepts to understand
- ⚠️ **Complexity**: More fields than before (but more meaningful)

### Risks

| Risk | Mitigation |
|------|------------|
| Users mis-classify tools | Provide classification guide, validation hints |
| Over-restrictive defaults block legitimate use | Start with permissive defaults, tighten over time |
| Gateway tools bypass restrictions | Flag `mixed` for manual review |

---

## References

- [ADR-001: Hybrid Tools Architecture](ADR-001-hybrid-tools-architecture.md) (superseded by this ADR)
- [ADR-056: MCP Tool Registration Workflow](ADR-056-MCP-Tool-Registration-Workflow.md)
- [ADR-049: Unified Authentication and Security](ADR-049-Unified-Authentication-Security-Implementation.md)
- NIST SP 800-53: Security and Privacy Controls
- OWASP API Security Top 10

---

**Template Version:** 1.0
**Based On:** [Michael Nygard's ADR pattern](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
