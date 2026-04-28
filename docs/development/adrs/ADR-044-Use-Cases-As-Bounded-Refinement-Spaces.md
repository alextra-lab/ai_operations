# ADR-044: Use Cases as Bounded Iterative Refinement Spaces

**Status:** ✅ ACCEPTED
**Date:** 2025-10-26
**Deciders:** Architecture Team
**Related:** ADR-018 (Use Case Owned Architecture), ADR-043 (Conversations as QUERY Pattern), ADR-016 (Dynamic Intent System), ADR-030 (Stateless Conversations)

---

## Context

AI Operations Platform provides multiple use cases (Threat Analysis, IOC Lookup, Rule Generation, etc.), each with specific configurations. We need to clarify:

1. **What is a use case conceptually?**
2. **How do use cases differ from general chatbots?**
3. **Why do some use cases require structured inputs while others don't?**
4. **How does multi-turn conversation work within use case boundaries?**

### Current Architecture

- Use cases own their configuration (ADR-018)
- Use cases reference intent types for defaults (ADR-016)
- Conversations support multi-turn refinement (ADR-043, ADR-030)
- Use cases can have optional `input_fields` for structured forms

**Missing:** Clear articulation of use cases as **purpose-built, domain-constrained AI assistants** that support iterative refinement.

---

## Decision

**Use cases are bounded iterative refinement spaces that create purpose-built AI assistants.**

### Core Principle

Each use case defines:
1. **Domain boundaries** (what topics/tasks it handles)
2. **Execution constraints** (what resources it can access)
3. **Interaction mode** (structured form vs conversational)
4. **Refinement capability** (iterative improvement through conversation)

**Result:** A portfolio of specialized assistants, NOT a general-purpose chatbot.

---

## Architecture

### 1. Use Case = Bounded Domain

```
┌────────────────────────────────────────────────────┐
│ Use Case: "Sigma Rule Generator"                  │
│                                                    │
│ Domain Boundaries:                                 │
│ ✓ Detection rule creation                         │
│ ✓ Rule syntax and logic                           │
│ ✓ MITRE ATT&CK mapping                            │
│ ✗ General security questions (out of scope)       │
│ ✗ Unrelated topics (rejected)                     │
│                                                    │
│ Enforcement Mechanisms:                            │
│ • RAG Collections: [sigma_examples, mitre_ttps]   │
│ • Tools: [sigma_validator, rule_tester]           │
│ • Prompts: "You are a detection engineer..."      │
│ • Model: mistral-large (code-focused)             │
└────────────────────────────────────────────────────┘
```

### 2. Intent Type Proposes, Use Case Constrains

```
Intent Type (Minimal Defaults)
    ├─ RULE_GENERATION: code model, temp=0.2
    ├─ SUMMARIZATION: balanced model, temp=0.5
    └─ QUERY: general model, temp=0.7
            ↓
Use Case (Full Constraints)
    ├─ Specific RAG collections
    ├─ Specific tools allowlist
    ├─ Specific prompts
    ├─ Specific model (can override intent default)
    └─ Specific input mode
            ↓
Execution (Bounded Refinement)
    ├─ Initial response (from structured input OR freeform query)
    └─ Multi-turn refinement (stays within domain boundaries)
```

### 3. Two Interaction Patterns

#### Pattern A: Structured → Refinement

**Use Case with `input_fields` (structured form):**

```json
{
  "name": "IOC Enrichment",
  "intent_type": "ENRICHMENT",
  "input_fields": [
    {"name": "ioc_value", "type": "text", "required": true},
    {"name": "ioc_type", "type": "select", "options": ["ip", "domain", "hash"]}
  ],
  "rag": {"vector_collections": ["threat_intel", "ioc_feeds"]},
  "tools_allowlist": ["virustotal_lookup", "misp_query"],
  "prompts": {
    "system_prompt": "You are a threat intelligence analyst specializing in IOC enrichment..."
  }
}
```

**User Flow:**

```
Step 1: Fill Form (Structured Input)
┌──────────────────────────────┐
│ IOC Value: 185.220.101.42    │
│ IOC Type:  [IP Address ▼]    │
│           [Submit]            │
└──────────────────────────────┘

Step 2: Initial Response
"This IP is a Tor exit node associated with APT28
infrastructure. Observed in campaigns..."

Step 3: Conversational Refinement
User: "What malware families used it?"
→ [searches threat_intel, stays in IOC domain]

User: "Show timeline of activity"
→ [reformats data, still within IOC context]

User: "What's the capital of France?"
→ "I'm an IOC enrichment assistant. I can only
   analyze threat indicators. Ask me about IPs,
   domains, or file hashes."
```

#### Pattern B: Conversational from Start

**Use Case with `input_fields: []` (freeform conversation):**

```json
{
  "name": "Threat Intel Q&A",
  "intent_type": "QUERY",
  "input_fields": [],  // No structured form - direct conversation
  "rag": {"vector_collections": ["threat_reports", "apt_analysis"]},
  "tools_allowlist": ["search_reports"],
  "prompts": {
    "system_prompt": "You are a threat intelligence expert. Answer questions about APTs, malware, and campaigns..."
  }
}
```

**User Flow:**

```
Step 1: Start Conversation (No Form)
User: "What do we know about APT29?"

Step 2: Response
"APT29 (Cozy Bear) is a Russian state-sponsored
group known for..."

Step 3: Continue Refinement
User: "What tools do they use?"
→ [continues in threat intel domain]

User: "Any recent campaigns?"
→ [searches threat_reports collection]

User: "How do I cook pasta?"
→ "I specialize in threat intelligence. Ask me
   about threat actors, malware, or campaigns."
```

---

## Execution Architecture

### Flow Diagram

```
┌─────────────────────────────────────────────────────┐
│ 1. User Initiates                                   │
│    • Via Structured Form (if input_fields present) │
│    • Via Conversation (if input_fields empty)      │
└────────────────┬────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────┐
│ 2. System Loads Use Case Constraints                │
│    • RAG collections (knowledge boundary)           │
│    • Tools allowlist (capability boundary)          │
│    • Prompts (behavior boundary)                    │
│    • Model + params (execution boundary)            │
└────────────────┬────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────┐
│ 3. Pipeline Execution (ADR-036)                     │
│    GuardValidate → RetrieveContext → AssemblePrompt │
│    → ExecuteLLM → FormatResponse                    │
│    [All constrained by use case config]             │
└────────────────┬────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────┐
│ 4. Initial Response Delivered                       │
└────────────────┬────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────┐
│ 5. Multi-turn Refinement (Optional)                 │
│    • User asks follow-up questions                  │
│    • System uses ephemeral cache (ADR-030)         │
│    • Same constraints apply to all turns            │
│    • Out-of-domain requests rejected by prompts    │
└─────────────────────────────────────────────────────┘
```

### Constraint Enforcement

| Mechanism | Purpose | Example |
|-----------|---------|---------|
| **RAG Collections** | Limit searchable knowledge | Only search `malware_reports`, not `hr_policies` |
| **Tools Allowlist** | Limit external capabilities | Can use `virustotal`, cannot use `send_email` |
| **System Prompt** | Define persona & boundaries | "You are a malware analyst..." + "Refuse off-topic requests" |
| **Developer Prompt** | Hidden instructions | "Always cite sources. Use technical terminology." |
| **Model Selection** | Execution characteristics | Code-focused for rules, general for questions |
| **Generation Params** | Output consistency | Low temp for rules (precise), high for creative tasks |
| **Input-Driven Scoping** | Runtime data isolation | User provides `incident_id` → RAG filtered to that incident only |

### Input Fields as Security Boundaries

**Critical Insight:** Input fields serve dual purposes:

1. **UI Form Generation** (user experience)
2. **Runtime Data Scoping** (security/access control)

When a user provides structured inputs, those values act as **security constraints** throughout execution:

```
Use Case: "Incident Deep Dive"
Input Fields:
  - incident_id: text (required)

User Input: incident_id = "INC-12345"

Runtime Enforcement:
┌─────────────────────────────────────────────────┐
│ RAG Searches                                    │
│ • Collections: [incidents, alerts, evidence]    │
│ • Metadata filter: {"incident_id": "INC-12345"} │
│ • Result: Only returns docs for INC-12345      │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ Tool Calls                                      │
│ • Tools: [query_siem, fetch_alert_details]     │
│ • Scoped params: {"incident_id": "INC-12345"}  │
│ • Result: Tools cannot access other incidents  │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ Multi-turn Conversation                         │
│ • Session context includes incident scope       │
│ • All follow-up queries maintain scope         │
│ • User CANNOT pivot to other incidents         │
└─────────────────────────────────────────────────┘
```

**Security Model:**

```
Layer 1: Use Case Boundaries (Domain)
  ├─ Which collections can be searched?
  ├─ Which tools can be invoked?
  └─ What topics are in scope?

Layer 2: Input-Driven Scoping (Record-Level)
  ├─ Which specific records within collections?
  ├─ Which entity instances can be accessed?
  └─ Enforced via metadata_filters + tool params

Layer 3: RBAC (User Permissions)
  ├─ Can user execute this use case?
  └─ Can user access this specific entity? (row-level)
```

**Example Implementation:**

```python
# Backend execution handler
async def execute_use_case(
    use_case: UseCase,
    user_inputs: dict[str, Any],
    user: User
) -> Response:
    # Load use case config (defines domain boundaries)
    config = UseCaseConfig.from_dict(use_case.config_json)

    # Apply input-driven scoping (record-level security)
    scoped_rag_config = apply_input_scoping(
        config.rag,
        user_inputs=user_inputs,
        input_fields=config.input_fields
    )

    # Example: incident_id input → RAG metadata filter
    # scoped_rag_config.metadata_filters = {
    #     "incident_id": user_inputs.get("incident_id")
    # }

    # All subsequent RAG searches are now scoped
    # All tool calls receive scoped parameters
    # Multi-turn refinement maintains scope
```

**Benefits:**

✅ **Data Isolation**: Users cannot escape the scope of their input
✅ **Multi-tenancy Support**: Each execution sandboxed by input
✅ **Compliance**: Ensures access only to authorized data
✅ **Audit Trail**: Input values logged for security review
✅ **Zero Trust**: Don't trust user to stay in scope - enforce it

---

## Examples

### Example 1: Rule Generation with Refinement

```
Use Case: "YARA Rule Builder"
Intent: RULE_GENERATION
Input Fields:
  - malware_description: textarea (required)
  - target_format: select (yara/sigma/snort)

# Turn 1: Structured Input
User submits form:
  malware_description: "PowerShell-based backdoor using Base64 encoding"
  target_format: "yara"

Response:
rule PowerShell_Backdoor_Base64 {
  meta:
    description = "Detects PowerShell backdoor..."
  strings:
    $ps1 = "powershell" nocase
    $b64 = /[A-Za-z0-9+/]{20,}={0,2}/
  condition:
    all of them
}

# Turn 2: Refinement
User: "Add detection for command execution"

Response: [updated rule with execution patterns]

# Turn 3: Refinement
User: "Make it less prone to false positives"

Response: [adds more specific conditions]

# Turn 4: Out-of-Domain (Rejected)
User: "What's the weather?"

Response: "I'm a YARA rule generation assistant.
I can only help with malware detection rules."
```

### Example 2: Conversational Q&A

```
Use Case: "Incident Response Q&A"
Intent: QUERY
Input Fields: [] (conversational mode)

# Turn 1: Start Conversation
User: "What should I do first in a ransomware incident?"

Response: "In a ransomware incident, follow these steps:
1. Isolate affected systems...
2. Preserve forensic evidence...
[cites incident_playbooks collection]"

# Turn 2: Refinement
User: "What if Active Directory is compromised?"

Response: "If AD is compromised, escalate immediately:
1. Reset KRBTGT account twice...
[continues in IR domain]"

# Turn 3: Refinement
User: "Show me the containment checklist"

Response: [retrieves checklist from playbooks]

# Turn 4: Domain Boundary
User: "How do I report this to executives?"

Response: "I specialize in technical incident response.
For executive reporting, use the Communication
Playbook use case."
```

### Example 3: Input-Driven Security Scoping

```
Use Case: "Incident Deep Dive"
Intent: QUERY
Input Fields:
  - incident_id: text (required)

RAG Collections: [incidents, alerts, evidence, investigation_notes]
Tools: [query_siem, fetch_alert_details, get_timeline]

# Turn 1: Structured Input (Security Boundary Established)
User submits form:
  incident_id: "INC-12345"

System applies runtime scoping:
  rag.metadata_filters = {"incident_id": "INC-12345"}
  tool_params_scope = {"incident_id": "INC-12345"}

Response: "Incident INC-12345: Ransomware attack detected.
Initial compromise: 2025-10-25 14:32 UTC
Affected systems: 3 servers, 12 workstations
[retrieves data ONLY for INC-12345]"

# Turn 2: Conversational Refinement (Scope Maintained)
User: "Show me the timeline of the attack"

System maintains scope:
  - RAG search: incidents + alerts filtered to INC-12345
  - Tool call: get_timeline(incident_id="INC-12345")

Response: "Timeline for INC-12345:
14:32 - Initial phishing email opened
14:35 - Malicious payload executed
14:42 - Lateral movement detected
[all data scoped to INC-12345 only]"

# Turn 3: User Attempts Scope Escape (BLOCKED)
User: "Show me all incidents from this week"

System enforces constraint:
  - Session is scoped to INC-12345
  - Cannot expand scope mid-conversation
  - User would need to execute use case again with different input

Response: "I'm currently analyzing incident INC-12345.
To view other incidents, please return to the use case
selection and specify a different incident ID."

# Turn 4: Refinement Within Scope (ALLOWED)
User: "What malware family was involved?"

Response: "Incident INC-12345 involves the Conti ransomware family.
IoCs: [lists IoCs from INC-12345 evidence collection]
[remains within INC-12345 scope]"
```

**Security Enforcement:**
- ✅ User can deeply explore INC-12345 (authorized)
- ❌ User cannot access INC-67890 (not in scope)
- ❌ User cannot list "all incidents" (scope escape attempt)
- ✅ All RAG searches filtered to `{"incident_id": "INC-12345"}`
- ✅ All tool calls receive `incident_id` parameter
- ✅ Scope persists across entire conversation session

---

## Benefits

### 1. Security & Safety

✅ **Bounded knowledge**: Can only access approved RAG collections
✅ **Controlled tools**: Can only invoke allowlisted capabilities
✅ **Consistent behavior**: Prompts enforce boundaries across conversations
✅ **Input-driven isolation**: User inputs create runtime data scopes
✅ **Multi-tenancy safe**: Each execution sandboxed by input constraints
✅ **Zero trust enforcement**: System enforces scope, doesn't rely on user behavior
✅ **Audit trail**: All actions constrained and logged with input context

### 2. User Experience

✅ **Predictable**: Users know what each assistant can/can't do
✅ **Focused**: No irrelevant responses or scope creep
✅ **Iterative**: Can refine outputs through conversation
✅ **Flexible**: Structured forms OR freeform chat based on use case needs

### 3. Developer Experience

✅ **Composable**: Create new assistants by configuring constraints
✅ **Testable**: Bounded domains easier to test than general chatbot
✅ **Maintainable**: Changes to one use case don't affect others
✅ **Extensible**: Add new use cases without modifying core system

---

## Implementation Details

### Backend Schema

The `UseCaseConfig` schema enforces boundaries:

```python
class UseCaseConfig(BaseModel):
    # OPTIONAL - enables structured vs conversational mode
    input_fields: list[InputFieldConfig] = Field(
        default_factory=list,
        description="Form fields for structured input. Empty = conversational mode."
    )

    # REQUIRED - defines domain boundaries
    rag: RAGConfig  # Which collections can be searched
    tools_allowlist: list[str]  # Which tools can be invoked
    models: ModelsConfig  # Which model to use
    generation_params: GenerationParamsConfig  # How to generate

    # Behavior boundaries enforced via prompts in metadata
```

### Frontend Rendering

```typescript
// Dynamic form OR conversation interface
if (useCase.config_json.input_fields?.length > 0) {
  // Render structured form
  renderDynamicForm(useCase.config_json.input_fields);
  afterSubmit(() => switchToConversationMode());
} else {
  // Render conversation interface directly
  renderConversationInterface();
}
```

### Multi-turn Context

- **Ephemeral cache** (ADR-030): Stores conversation history
- **Session-based** (ADR-030): Client manages session_id
- **Bounded**: Same use case constraints apply to all turns
- **Stateless**: No server-side persistence required

---

## Consequences

### Positive

✅ **Clear mental model**: "Use cases = specialized assistants"
✅ **Security by design**: Boundaries enforced at multiple levels
✅ **Flexible UX**: Supports both forms and conversations
✅ **Scalable**: Easy to add new specialized assistants
✅ **Testable**: Bounded domains easier to validate

### Negative

⚠️ **Complexity**: More configuration per use case
⚠️ **Prompt engineering**: Need careful boundary prompts
⚠️ **User education**: Users need to understand scope of each use case

### Mitigations

- **Templates/Patterns**: Reusable starting points for common use cases
- **Cloning**: Copy existing use cases as starting point
- **Clear naming**: Use case names indicate domain clearly
- **Good descriptions**: Explain what each assistant can/can't do
- **Graceful rejection**: Friendly messages when out-of-domain

---

## Related Decisions

- **ADR-018**: Use cases own their configuration
- **ADR-016**: Intent types provide minimal defaults
- **ADR-043**: Conversations as QUERY pattern implementation
- **ADR-030**: Ephemeral conversation cache
- **ADR-036**: Pipeline architecture for execution

---

## Examples in Production

### Structured Use Cases (with input_fields)

1. **IOC Lookup**: Requires ioc_value + ioc_type
2. **Incident Summary**: Requires incident_details + summary_type
3. **Rule Generator**: Requires attack_description + platform

### Conversational Use Cases (without input_fields)

1. **Threat Intel Q&A**: Freeform questions about threats
2. **Log Investigation**: Conversational log analysis
3. **Policy Review**: Freeform compliance questions

All use cases support multi-turn refinement within their bounded domains.

---

## Open Questions & Design Challenges

### Challenge 1: Discovery Mode vs. Strict Isolation

**Problem:** Some use cases need strict data isolation (security/compliance), while others need discovery workflows (threat hunting, incident response).

**Example Scenario:**

```
SOC analyst investigating incident INC-12345:
- Discovers shared IOC with incident INC-67890
- Finds lateral movement indicators in INC-67891
- Realizes they're part of campaign CAMP-2025-10

Should the use case:
A) Stay strictly scoped to INC-12345? (secure but limiting)
B) Allow discovery of related incidents? (useful but risky)
```

**Two Conflicting Use Cases:**

```
Use Case 1: "Customer Data Review" (Compliance)
├─ strict_constraints: true
├─ allow_discovery: false
└─ Reason: MUST NOT access other customer data (PII, compliance)

Use Case 2: "Campaign Analysis" (Threat Hunting)
├─ strict_constraints: false
├─ allow_discovery: true
├─ max_discovery_depth: 2
└─ Reason: MUST follow related entities to understand scope
```

**Proposed Solutions (Needs Further Design):**

#### Option A: Per-Field Scoping Mode

```python
class ScopingMode(str, Enum):
    STRICT = "strict"              # Exact match only, no discovery
    RELATED = "related"            # Allow related entities (1 hop)
    HIERARCHICAL = "hierarchical"  # Allow parent/child relationships
    CAMPAIGN = "campaign"          # Allow campaign-based grouping

class InputFieldConfig(BaseModel):
    name: str
    # ... existing fields

    # NEW: Scoping behavior
    scoping_mode: ScopingMode = Field(
        default=ScopingMode.STRICT,
        description="How this input constrains data access"
    )
    allow_discovery: bool = Field(
        default=False,
        description="Allow AI to discover related entities during investigation"
    )
    max_discovery_depth: int = Field(
        default=0,
        description="Maximum hops in discovery chain (0 = strict, 1-3 = discovery)"
    )
```

**Example Configuration:**

```json
{
  "name": "Campaign Hunter",
  "input_fields": [
    {
      "name": "initial_incident",
      "type": "text",
      "scoping_mode": "campaign",
      "allow_discovery": true,
      "max_discovery_depth": 2
    }
  ],
  "rag": {
    "collections": ["incidents", "iocs", "campaigns"]
  }
}
```

**Runtime Behavior:**

```
User Input: initial_incident = "INC-12345"

Execution Flow:
┌─────────────────────────────────────────┐
│ Depth 0: Start with INC-12345          │
│ • RAG filter: {"incident_id": "INC-12345"} │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ Depth 1: Discover Related (if allowed) │
│ • Find shared IOC: 185.220.101.42       │
│ • Expand filter: {"ioc": "185.220.101.42"} │
│ • Discover: INC-67890, INC-67891        │
│ • Audit: "Discovered via shared IOC"   │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ Depth 2: Campaign Correlation          │
│ • Find campaign: CAMP-2025-10           │
│ • Expand filter: {"campaign": "CAMP-2025-10"} │
│ • Audit: "Discovered via campaign link"│
│ • Stop: max_discovery_depth reached    │
└─────────────────────────────────────────┘
```

#### Option B: Use Case-Level Discovery Policy

```python
class DiscoveryPolicy(BaseModel):
    """Policy for entity discovery during execution."""

    enabled: bool = Field(
        default=False,
        description="Whether discovery of related entities is allowed"
    )
    max_depth: int = Field(
        default=0,
        description="Maximum discovery hops (0 = strict isolation)"
    )
    allowed_relations: list[str] = Field(
        default_factory=list,
        description="Types of relations to follow: ['shared_ioc', 'lateral_movement', 'campaign']"
    )
    require_explicit_approval: bool = Field(
        default=False,
        description="Require user approval before following each relation"
    )

class UseCaseConfig(BaseModel):
    # ... existing fields

    discovery_policy: DiscoveryPolicy = Field(
        default_factory=DiscoveryPolicy,
        description="Policy for discovering related entities during execution"
    )
```

**Security Considerations:**

1. **Audit Trail**: Every discovery hop must be logged
   ```json
   {
     "session_id": "...",
     "initial_scope": {"incident_id": "INC-12345"},
     "discovery_chain": [
       {"depth": 1, "relation": "shared_ioc", "discovered": "INC-67890", "via": "185.220.101.42"},
       {"depth": 2, "relation": "campaign", "discovered": "CAMP-2025-10", "via": "common_ttps"}
     ]
   }
   ```

2. **RBAC Integration**: User must have permissions for discovered entities
   ```python
   if allow_discovery:
       for discovered_entity in discovered_entities:
           if not user.has_permission(discovered_entity):
               # Skip this entity, log access denial
               continue
   ```

3. **Compliance Mode**: Some use cases MUST disable discovery
   ```python
   if use_case.requires_compliance_isolation:
       discovery_policy.enabled = False  # Override, cannot be changed
   ```

### Challenge 2: Tool Scoping

**Problem:** Tools (like ServiceNow MCP) must also respect input scoping, not just RAG.

**Example:**

```python
# User input: incident_id = "INC-12345"

# Tool call MUST be scoped:
servicenow_mcp.query_incident(
    incident_id="INC-12345",  # From user input
    # Cannot query other incidents
)

# Discovery mode:
if allow_discovery:
    related_incidents = servicenow_mcp.find_related_incidents(
        incident_id="INC-12345",
        relation_types=["shared_ioc", "lateral_movement"],
        max_results=10
    )
    # Returns INC-67890, INC-67891
    # Audit log records discovery
```

**Implementation Pattern:**

```python
async def execute_tool_call(
    tool_name: str,
    tool_params: dict,
    input_scopes: dict,  # From user inputs
    discovery_policy: DiscoveryPolicy
) -> ToolResult:
    # Apply input scoping to tool parameters
    scoped_params = apply_input_scoping(tool_params, input_scopes)

    # Execute tool with scoped parameters
    result = await tool_registry.execute(tool_name, scoped_params)

    # If discovery allowed, check for related entities
    if discovery_policy.enabled and result.has_related_entities:
        related = await discover_related_entities(
            result,
            max_depth=discovery_policy.max_depth,
            allowed_relations=discovery_policy.allowed_relations,
            user_permissions=current_user.permissions
        )
        result.add_discovered_entities(related, audit_trail=True)

    return result
```

---

## Future Work

**Immediate (Phase 3):**
1. ✅ Schema supports `input_fields` (completed 2025-10-26)
2. ⏳ **Design scoping modes** (strict vs. discovery) - **NEEDS ADR**
3. ⏳ **Tool scoping implementation** - apply input constraints to all tool calls
4. ⏳ **Discovery audit trail** - log all scope expansions

**Medium Term (Phase 4):**
1. **Discovery policy per use case** - configuration for allowed discovery
2. **User approval workflow** - prompt user before following relations
3. **RBAC integration** - verify permissions for discovered entities
4. **Discovery analytics** - track how often scope expands, typical patterns

**Long Term (v2.0):**
1. **Dynamic boundary adjustment** - users request temporary scope expansion
2. **Use case chaining** - hand off to related use case when boundary reached
3. **Auto-suggestion** - recommend alternative use case when out-of-domain
4. **Compliance certification** - prove strict isolation for regulated use cases

---

**Decision Date:** 2025-10-26
**Implementation Status:** ✅ ACTIVE (use case system supports basic pattern)
**Schema Update Status:** ✅ COMPLETED (`input_fields` now optional)
**Next Steps:** Design discovery mode architecture (separate ADR recommended)
