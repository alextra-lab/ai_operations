# Google Prompt Engineering PDF Integration Assessment

**Date:** October 20, 2025
**Source:** Google "Prompt Engineering" Guide (22365_3_Prompt Engineering_v7.pdf)
**Reviewer:** ChatGPT Research + Cursor AI
**Status:** Architectural Review - No Implementation

---

## Executive Summary

Comprehensive review of prompt engineering best practices from Google's guide against AI Operations Platform's current architecture. Identifies high-value integrations to strengthen determinism, reduce costs, and improve enterprise auditability.

**Key Recommendation:** Implement sampling presets (ADR-023) as Phase 4 Priority 1 feature.

---

## Responses to Targeted Questions

### 1. Tools Status: T3/T4 Implementation Reality

**Answer:** Part 2 (PENDING) is correct, Part 3 (complete) is aspirational.

**Current State:**
- ✅ **T1 (Tool Registration):** 25% complete (schema exists, CRUD/secrets/permissions pending)
- ⏸️ **T2 (MCP Integration):** 0% (not started)
- ⏸️ **T3 (Execution):** 0% (no `tool_executor.py`, no circuit breakers, no health monitoring)
- ⏸️ **T4 (Enterprise):** 0% (no health dashboard, no analytics APIs)

**Evidence:**
```bash
# Missing files:
src/orchestrator/app/services/tool_executor.py  # Does not exist
src/orchestrator/app/services/tool_health.py    # Does not exist
tests/integration/test_tool_executor.py    # Does not exist
```

**Action Items:**
1. Update `TOOLS_IMPLEMENTATION_PLAN_PART3.md` status markers from ✅ to ⏸️
2. Keep P3-F4 (Tool Selection UI) as "scaffolding only" with clear "blocked by T1-T2" messaging
3. Plan T3/T4 implementation for Q1 2026 per Master Roadmap

---

### 2. Sampling Policies: Global Defaults vs Per-Use-Case

**Recommendation:** **Hybrid approach** - Global presets with per-Use-Case override capability.

**Architecture:** (See ADR-023 for full details)

```python
# Three canonical presets (global)
SamplingPreset.STRICT  # temp=0.15, top_p=0.90
SamplingPreset.BALANCED       # temp=0.65, top_p=0.95
SamplingPreset.CREATIVE       # temp=0.85, top_p=0.97

# Per-Use-Case configuration
class GenerationParamsConfig:
    sampling_preset: SamplingPreset = Field(default=BALANCED)
    # Overrides require CUSTOM preset + RBAC permission
    temperature: float | None = None
    max_tokens: int | None = None
    top_p: float | None = None
```

**RBAC Matrix:**

| Role | Can Use Presets | Can Use CUSTOM | Can Override max_tokens |
|------|----------------|----------------|------------------------|
| analyst | ✅ | ❌ | ❌ |
| use_case_publisher | ✅ | ✅ (with warning) | ✅ (within bounds) |
| corpus_admin | ✅ | ✅ | ✅ |
| admin | ✅ | ✅ | ✅ |

**Rationale:**
- ✅ Analysts get consistent, validated behavior by default (no tuning required)
- ✅ AIO Developers can experiment with CUSTOM preset (innovation)
- ✅ Published UCs locked to tested configuration (stability)
- ✅ Audit trail shows "preset=strict" (clear intent)

---

### 3. Output Contracts: Strict vs Best-Effort

**Recommendation:** **Use Case category-based policy:**

| Use Case Category | Validation Mode | Rationale |
|-------------------|----------------|-----------|
| **Extraction** (IOCs, entities) | `STRICT` | Downstream automation requires valid JSON |
| **Classification** (triage, severity) | `STRICT` | Alerting systems parse structured output |
| **Tool-use** (ReAct, function calling) | `STRICT` | Function parameters must match schema |
| **Summarization** | `BEST_EFFORT` | Human-readable text, schema less critical |
| **Q&A / Explanation** | `BEST_EFFORT` | Natural language, flexible format |
| **Playbook Generation** | `BEST_EFFORT` | Creative content, structure secondary |

**Implementation:**

```python
# Already exists in use_case_config.py (lines 114-126)
class OutputContractConfig:
    format: OutputFormat = Field(default=OutputFormat.TEXT)
    output_schema: dict | None = Field(default=None)
    validation_mode: ValidationMode = Field(
        default=ValidationMode.BEST_EFFORT
    )
```

**Enhancement Needed:** JSON repair pass (from PDF)

```python
# Add to ResponseFormatter
async def validate_and_repair_json(
    self,
    raw_output: str,
    schema: dict | None,
    mode: ValidationMode
) -> dict | str:
    """
    Validate output against schema with optional repair.

    BEST_EFFORT: Try to extract/fix JSON, fall back to raw text
    STRICT: Reject invalid output, raise validation error
    """
    try:
        parsed = json.loads(raw_output)
        if schema:
            jsonschema.validate(parsed, schema)
        return parsed
    except (json.JSONDecodeError, jsonschema.ValidationError) as e:
        if mode == ValidationMode.STRICT:
            raise ValidationError(f"Output validation failed: {e}")

        # BEST_EFFORT: Attempt repair
        repaired = self._attempt_json_repair(raw_output)
        if repaired:
            return repaired

        # Fall back to raw text
        logger.warning(f"JSON repair failed, returning raw output: {e}")
        return {"raw_output": raw_output, "error": str(e)}
```

**Action Items:**
1. Add JSON repair logic to `ResponseFormatter` (P4 feature)
2. Update Pattern Library to mark extraction/classification patterns as `STRICT`
3. Document validation mode selection criteria in Use Case management guide

---

### 4. Pattern Seeding: Core + SOC-Specific

**Recommendation:** YES - Seed both general techniques and SOC workflows.

**Current State:**
- ✅ 29 patterns from promptingguide.ai already seeded
- ❌ Missing: Sampling preset recommendations per pattern
- ❌ Missing: SOC-specific blueprints

**Proposed Additions:**

#### A. Update Existing Patterns with Presets

```sql
-- Deterministic patterns (predictable outputs)
UPDATE prompt_patterns
SET recommended_preset = 'strict',
    max_tokens_override = 1024
WHERE pattern_id IN (
    'zero-shot',
    'few-shot',
    'role-prompting'
);

-- Balanced patterns (general Q&A)
UPDATE prompt_patterns
SET recommended_preset = 'balanced',
    max_tokens_override = 2048
WHERE pattern_id IN (
    'chain-of-thought',
    'self-consistency',
    'rag-citations'
);

-- Creative patterns (generative tasks)
UPDATE prompt_patterns
SET recommended_preset = 'creative',
    max_tokens_override = 4096
WHERE pattern_id IN (
    'tree-of-thoughts',
    'directional-stimulus'
);

-- Tool-use patterns (constrained for cost)
UPDATE prompt_patterns
SET recommended_preset = 'balanced',
    max_tokens_override = 2048,
    special_params = '{"max_tool_steps": 5, "tool_step_timeout": 30}'::jsonb
WHERE pattern_id IN ('react', 'react-rag');
```

#### B. Add SOC-Specific Patterns

**New patterns to seed:**

1. **Threat Intelligence Triage + RAG**
   ```sql
   INSERT INTO prompt_patterns (
       pattern_id, name, category,
       recommended_preset, max_tokens_override,
       system_prompt_template, developer_prompt_template,
       description, tags
   ) VALUES (
       'ti-triage-rag',
       'Threat Intelligence Triage with RAG',
       'soc',
       'strict',
       1024,
       'You are a SOC analyst specializing in threat intelligence triage...',
       'Use retrieved context to classify threat level. Output format: JSON with fields: threat_level, confidence, justification, recommended_actions. Always include citations from source documents using [doc_id] format.',
       'Classify threat intelligence reports using RAG context with structured output',
       '["soc", "triage", "threat-intel", "rag", "classification"]'::jsonb
   );
   ```

2. **IOC Extraction (Structured)**
   ```sql
   INSERT INTO prompt_patterns (
       pattern_id, name, category,
       recommended_preset, max_tokens_override,
       system_prompt_template, developer_prompt_template,
       description, tags
   ) VALUES (
       'ioc-extraction-structured',
       'IOC Extraction (Structured Output)',
       'soc',
       'strict',
       512,
       'You are an IOC extraction specialist...',
       'Extract all IOCs from text. Output valid JSON array of objects: [{"type": "ip"|"domain"|"hash"|"url", "value": "...", "context": "..."}]. No markdown, no explanations, only valid JSON.',
       'Extract indicators of compromise with strict JSON schema',
       '["soc", "ioc", "extraction", "json", "strict"]'::jsonb
   );
   ```

3. **Incident Summary Generation**
   ```sql
   INSERT INTO prompt_patterns (
       pattern_id, name, category,
       recommended_preset, max_tokens_override,
       system_prompt_template, developer_prompt_template,
       description, tags
   ) VALUES (
       'incident-summary',
       'Incident Summary Generation',
       'soc',
       'balanced',
       2048,
       'You are a SOC analyst writing executive incident summaries...',
       'Summarize security incident details for executive audience. Structure: 1) What happened, 2) Impact, 3) Current status, 4) Next steps. Use clear, non-technical language.',
       'Generate executive-level incident summaries',
       '["soc", "incident", "summarization", "executive"]'::jsonb
   );
   ```

4. **Playbook Drafting (SOC Procedures)**
   ```sql
   INSERT INTO prompt_patterns (
       pattern_id, name, category,
       recommended_preset, max_tokens_override,
       system_prompt_template, developer_prompt_template,
       description, tags
   ) VALUES (
       'soc-playbook-draft',
       'SOC Playbook Drafting',
       'soc',
       'creative',
       4096,
       'You are an experienced SOC manager creating runbooks and playbooks...',
       'Generate detailed step-by-step procedures. Structure each step with: Objective, Prerequisites, Steps (numbered), Verification, Escalation criteria. Reference NIST/MITRE frameworks where applicable.',
       'Draft SOC playbooks and runbooks for incident response',
       '["soc", "playbook", "runbook", "procedures", "creative"]'::jsonb
   );
   ```

5. **Alert Correlation Analysis**
   ```sql
   INSERT INTO prompt_patterns (
       pattern_id, name, category,
       recommended_preset, max_tokens_override,
       system_prompt_template, developer_prompt_template,
       description, tags
   ) VALUES (
       'alert-correlation',
       'Alert Correlation Analysis',
       'soc',
       'balanced',
       2048,
       'You are a SOC analyst correlating security alerts...',
       'Analyze multiple alerts to identify patterns, common indicators, or potential campaigns. Output: correlation_score (0-1), related_alerts (array), hypothesis (string), recommended_investigation_steps (array).',
       'Correlate multiple security alerts to identify patterns',
       '["soc", "correlation", "alerts", "analysis"]'::jsonb
   );
   ```

**Migration Script:**

```bash
# ops/migrations/sql/seed_soc_patterns.sql
# Adds 5 SOC-specific patterns + updates existing 29 with presets
```

**Action Items:**
1. Create `seed_soc_patterns.sql` migration (P4 or parallel to P4)
2. Test all 5 new patterns in staging with real SOC data
3. Document pattern selection criteria in Use Case management guide
4. Add pattern filtering by tags: "Show me SOC patterns"

---

### 5. Guardrails for ReAct/Tools: Max Caps

**Recommendation:** Per-Use-Case caps with policy enforcement.

**Proposed Limits:**

| Use Case Type | max_tokens | max_tool_steps | tool_step_timeout | Cost Cap (est.) |
|---------------|------------|----------------|-------------------|----------------|
| **Simple Q&A** | 1024 | 0 (no tools) | N/A | $0.001/query |
| **RAG Query** | 2048 | 0 (retrieval only) | N/A | $0.003/query |
| **Single Tool Use** | 2048 | 3 | 30s | $0.01/query |
| **ReAct Workflow** | 3072 | 5 | 30s | $0.03/query |
| **Complex Automation** | 4096 | 8 | 60s | $0.08/query |

**Implementation:** (Already in ADR-023 schema)

```python
class GenerationParamsConfig(BaseModel):
    max_tokens: int | None = Field(default=2048, le=16384)
    max_tool_steps: int | None = Field(
        default=None,
        description="Maximum tool invocation steps (for ReAct patterns)",
        ge=1, le=10
    )
    tool_step_timeout: int = Field(
        default=30,
        description="Timeout per tool step (seconds)",
        ge=5, le=120
    )
```

**Runtime Enforcement:**

```python
# In ToolExecutor (when T3 implemented)
class ToolExecutor:
    async def execute_tool_chain(
        self,
        initial_query: str,
        allowed_tools: list[str],
        max_steps: int = 5
    ):
        """Execute ReAct-style tool chain with step limit."""
        step_count = 0

        while step_count < max_steps:
            # Check if LLM wants to call tool
            decision = await self.llm_router.get_tool_decision(...)

            if decision.action == "final_answer":
                return decision.answer

            if decision.action == "call_tool":
                step_count += 1

                if step_count >= max_steps:
                    logger.warning(
                        f"Max tool steps ({max_steps}) reached. "
                        f"Forcing final answer."
                    )
                    # Force LLM to provide answer with current context
                    return await self.llm_router.force_final_answer(...)

                # Execute tool
                result = await self.execute_single_tool(decision.tool, ...)
                # Continue loop with result
```

**Cost Tracking:**

```python
# In TokenTracker service
async def track_tool_execution(
    self,
    use_case_id: str,
    step_count: int,
    tokens_used: int,
    estimated_cost_usd: float
):
    """Track tool execution costs for budget monitoring."""
    if estimated_cost_usd > USE_CASE_COST_CAP:
        logger.error(
            f"Use Case {use_case_id} exceeded cost cap: "
            f"${estimated_cost_usd:.4f} > ${USE_CASE_COST_CAP:.4f}"
        )
        # Alert admin, optionally disable UC
```

**Action Items:**
1. Add max_tool_steps and tool_step_timeout to GenerationParamsConfig (Done in ADR-023)
2. Implement step counter in ToolExecutor when T3 is built (Q1 2026)
3. Add cost tracking per tool execution in TokenTracker
4. Create admin dashboard for tool cost monitoring (T4 feature)

---

### 6. Version Discipline: Immutable Published Versions

**Recommendation:** YES - Enforce immutability at "published" lifecycle state.

**Current State:**
- ✅ Lifecycle states exist: draft, review, published, archived
- ✅ State transitions implemented with validation
- ❌ Published versions NOT immutable (can still be edited)
- ❌ No forced clone-for-edit workflow

**Proposed Architecture:**

```python
# Update Use Case validation in backend
class UseCaseUpdate(BaseModel):
    # ... existing fields ...

    @validator("*", pre=True, always=True)
    def validate_published_immutability(cls, v, values, field):
        """Prevent editing published Use Cases."""
        # Check if this UC is published
        use_case = get_current_use_case(values.get("use_case_id"))

        if use_case and use_case.lifecycle_state == "published":
            raise ValueError(
                "Cannot edit published Use Case. "
                "Please clone and create a new version."
            )

        return v
```

**Clone-for-Edit Workflow:**

```python
# Add to UseCaseRouter
@router.post("/{use_case_id}/clone", response_model=UseCaseResponse)
async def clone_use_case(
    use_case_id: str,
    new_name: str | None = None,
    current_user: TokenPayload = Depends(auth_required)
):
    """
    Clone Use Case (required for editing published versions).

    - Creates new Use Case with incremented version
    - Copies all configuration from source
    - Sets lifecycle_state = 'draft'
    - Preserves lineage in metadata
    """
    source_uc = await use_case_service.get_by_id(use_case_id)

    if not source_uc:
        raise HTTPException(404, "Use Case not found")

    # Create clone
    cloned_uc = await use_case_service.clone(
        source_id=use_case_id,
        new_name=new_name or f"{source_uc.name} (v{source_uc.version + 1})",
        created_by=current_user.username
    )

    logger.info(
        f"Cloned Use Case {use_case_id} → {cloned_uc.use_case_id} "
        f"by {current_user.username}"
    )

    return cloned_uc
```

**Frontend Workflow:**

```typescript
// In use-case-list.component.ts
async editUseCase(useCase: UseCase) {
  if (useCase.lifecycle_state === 'published') {
    // Show dialog: "Published Use Cases are immutable"
    const result = await this.dialog.open(CloneConfirmDialog, {
      data: { useCase }
    }).afterClosed().toPromise();

    if (result === 'clone') {
      // Clone and navigate to editor
      const cloned = await this.useCaseService.cloneUseCase(useCase.id);
      this.router.navigate(['/use-cases/wizard', cloned.use_case_id]);
    }
  } else {
    // Direct edit for draft/review
    this.router.navigate(['/use-cases/wizard', useCase.use_case_id]);
  }
}
```

**Audit Trail:**

```sql
-- Add to metadata_json
{
  "lineage": {
    "cloned_from": "original-uc-id",
    "clone_reason": "Performance optimization",
    "clone_date": "2025-11-15T10:30:00Z",
    "cloned_by": "john.analyst"
  }
}
```

**Action Items:**
1. Add immutability validation to UseCaseUpdate schema (P4)
2. Implement clone endpoint in backend (P4)
3. Update Use Case List UI with clone workflow (P4)
4. Add lineage tracking to metadata_json (P4)
5. Document version discipline in Use Case management guide (P4)

---

### 7. Value Metrics: KPI Dashboard

**Recommendation:** Per-Use-Case metrics dashboard with business value KPIs.

**Proposed Metrics:**

#### A. Quality Metrics
- **Precision@k:** Retrieval relevance (% of top-k results useful)
- **Avg Confidence:** LLM confidence scores across queries
- **Output Validity:** % of responses passing schema validation
- **Citation Coverage:** % of responses with proper source citations
- **Analyst Acceptance Rate:** % of responses marked "helpful" by users

#### B. Performance Metrics
- **Time-to-First-Token (TTFT):** Streaming latency
- **Total Response Time:** End-to-end latency
- **Token Efficiency:** Tokens used vs retrieved context size
- **Cache Hit Rate:** % of queries served from cache

#### C. Cost Metrics
- **Cost per Query:** Average cost (input + output tokens)
- **Cost per Use Case:** Total spend per UC over time period
- **ROI Estimate:** Time saved × analyst hourly rate - cost

#### D. Operational Metrics
- **Query Volume:** Queries per day/week/month
- **Error Rate:** % of queries with errors
- **Guard Risk Events:** % of queries flagged by LLM-Guard
- **Tool Execution Success:** % of tool calls succeeding (when T3 live)

**Schema Design:**

```sql
-- New table for UC metrics
CREATE TABLE use_case_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    use_case_id VARCHAR(255) REFERENCES use_cases(use_case_id),
    metric_date DATE NOT NULL,

    -- Quality
    avg_confidence DECIMAL(3,2),
    output_validity_rate DECIMAL(3,2),
    citation_coverage_rate DECIMAL(3,2),
    analyst_acceptance_rate DECIMAL(3,2),

    -- Performance
    avg_ttft_ms INTEGER,
    avg_total_time_ms INTEGER,
    avg_tokens_used INTEGER,
    cache_hit_rate DECIMAL(3,2),

    -- Cost
    total_cost_usd DECIMAL(10,4),
    avg_cost_per_query DECIMAL(6,4),

    -- Operational
    query_count INTEGER,
    error_count INTEGER,
    guard_risk_count INTEGER,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_uc_metric_date UNIQUE(use_case_id, metric_date)
);

CREATE INDEX idx_uc_metrics_date ON use_case_metrics(metric_date DESC);
CREATE INDEX idx_uc_metrics_use_case ON use_case_metrics(use_case_id);
```

**Analytics Service:**

```python
# src/orchestrator/app/services/use_case_analytics.py

class UseCaseAnalyticsService:
    """Calculate and store Use Case value metrics."""

    async def calculate_daily_metrics(
        self,
        use_case_id: str,
        target_date: date
    ) -> UseCaseMetrics:
        """Calculate metrics for a Use Case on a specific date."""

        # Get all executions for this UC on target date
        executions = await self.history_service.get_executions(
            use_case_id=use_case_id,
            start_date=target_date,
            end_date=target_date + timedelta(days=1)
        )

        if not executions:
            return None

        # Calculate quality metrics
        avg_confidence = mean([e.confidence for e in executions if e.confidence])
        output_validity_rate = sum(
            1 for e in executions if e.output_valid
        ) / len(executions)

        # Calculate performance metrics
        avg_ttft_ms = mean([e.ttft_ms for e in executions if e.ttft_ms])
        avg_total_time_ms = mean([e.total_time_ms for e in executions])

        # Calculate cost metrics
        total_cost = sum([e.cost_usd for e in executions])
        avg_cost_per_query = total_cost / len(executions)

        # Calculate operational metrics
        error_count = sum(1 for e in executions if e.had_error)
        guard_risk_count = sum(1 for e in executions if e.guard_flagged)

        # Store metrics
        metrics = UseCaseMetrics(
            use_case_id=use_case_id,
            metric_date=target_date,
            avg_confidence=avg_confidence,
            output_validity_rate=output_validity_rate,
            avg_ttft_ms=avg_ttft_ms,
            avg_total_time_ms=avg_total_time_ms,
            total_cost_usd=total_cost,
            avg_cost_per_query=avg_cost_per_query,
            query_count=len(executions),
            error_count=error_count,
            guard_risk_count=guard_risk_count
        )

        await self.db.save(metrics)
        return metrics
```

**Frontend Dashboard:**

```typescript
// src/app/pages/analytics/use-case-value-dashboard.component.ts

interface UseCaseValueCard {
  use_case_id: string;
  name: string;

  // Quality score (0-100)
  quality_score: number;  // Weighted avg of confidence, validity, acceptance

  // Efficiency score (0-100)
  efficiency_score: number;  // Based on latency, cache hits, token usage

  // ROI estimate
  queries_per_week: number;
  time_saved_minutes: number;  // Assumed 5 min per query
  cost_per_week_usd: number;
  roi_estimate_usd: number;  // (time_saved * $50/hr) - cost

  // Trend indicators
  quality_trend: 'up' | 'down' | 'stable';
  cost_trend: 'up' | 'down' | 'stable';
}
```

**Dashboard UI:**

```html
<!-- Use Case Value Dashboard -->
<div class="dashboard-grid">
  <mat-card *ngFor="let uc of useCaseCards" class="value-card">
    <mat-card-header>
      <mat-card-title>{{ uc.name }}</mat-card-title>
      <mat-icon [class.trend-up]="uc.quality_trend === 'up'"
                [class.trend-down]="uc.quality_trend === 'down'">
        trending_{{ uc.quality_trend }}
      </mat-icon>
    </mat-card-header>

    <mat-card-content>
      <!-- Quality Score -->
      <div class="metric-row">
        <span class="metric-label">Quality</span>
        <span class="metric-value">{{ uc.quality_score }}/100</span>
        <mat-progress-bar mode="determinate"
                          [value]="uc.quality_score">
        </mat-progress-bar>
      </div>

      <!-- Efficiency Score -->
      <div class="metric-row">
        <span class="metric-label">Efficiency</span>
        <span class="metric-value">{{ uc.efficiency_score }}/100</span>
        <mat-progress-bar mode="determinate"
                          [value]="uc.efficiency_score">
        </mat-progress-bar>
      </div>

      <!-- ROI Estimate -->
      <div class="metric-row highlight">
        <span class="metric-label">Weekly ROI</span>
        <span class="metric-value">
          ${{ uc.roi_estimate_usd | number:'1.2-2' }}
        </span>
        <small>{{ uc.queries_per_week }} queries,
               {{ uc.time_saved_minutes }}min saved</small>
      </div>

      <!-- Quick Stats -->
      <div class="quick-stats">
        <span>Avg Confidence: {{ uc.avg_confidence | percent }}</span>
        <span>Avg Latency: {{ uc.avg_latency_ms }}ms</span>
        <span>Cost/Query: ${{ uc.avg_cost_per_query }}</span>
      </div>
    </mat-card-content>

    <mat-card-actions>
      <button mat-button [routerLink]="['/analytics/use-cases', uc.use_case_id]">
        View Details
      </button>
    </mat-card-actions>
  </mat-card>
</div>
```

**Action Items:**
1. Create `use_case_metrics` table schema (P4 or P5)
2. Implement `UseCaseAnalyticsService` (P5-F3 Enterprise Analytics)
3. Create daily metrics calculation job (cron or Celery)
4. Build Use Case Value Dashboard component (P5-F3)
5. Add analyst feedback mechanism ("Was this helpful?" thumbs up/down)
6. Document metric definitions and calculation methods

---

### 8. Air-Gapped Stance: Internet-Capable Tools

**Recommendation:** YES - Permanent disable for production, optional for dev/staging.

**Implementation:**

```python
# In tool registry schema
class Tool(Base):
    id = Column(UUID, primary_key=True)
    tool_id = Column(String, unique=True, nullable=False)

    # New fields for air-gapped control
    requires_internet = Column(Boolean, default=False)
    allowed_in_airgapped = Column(Boolean, default=True)

    # Deployment environment flags
    enabled_in_dev = Column(Boolean, default=True)
    enabled_in_staging = Column(Boolean, default=True)
    enabled_in_prod = Column(Boolean, default=True)
```

**Deployment Configuration:**

```bash
# Environment variables
DEPLOYMENT_ENVIRONMENT=production  # development, staging, production
AIR_GAPPED_MODE=true               # true, false

# In docker-compose.prod.yml
environment:
  - DEPLOYMENT_ENVIRONMENT=production
  - AIR_GAPPED_MODE=true
```

**Runtime Enforcement:**

```python
# In ToolValidator (when T3 implemented)
class ToolValidator:
    def validate_tool_allowed(
        self,
        tool: Tool,
        use_case_config: UseCaseConfig
    ) -> bool:
        """Validate tool is allowed in current environment."""

        # Check air-gapped mode
        if os.getenv("AIR_GAPPED_MODE") == "true":
            if tool.requires_internet:
                logger.error(
                    f"Tool {tool.tool_id} requires internet but "
                    f"system is in air-gapped mode"
                )
                return False

            if not tool.allowed_in_airgapped:
                logger.error(
                    f"Tool {tool.tool_id} not allowed in air-gapped mode"
                )
                return False

        # Check deployment environment
        env = os.getenv("DEPLOYMENT_ENVIRONMENT", "development")
        if env == "production" and not tool.enabled_in_prod:
            logger.error(
                f"Tool {tool.tool_id} not enabled in production"
            )
            return False

        return True
```

**Tool Registry Seeding:**

```sql
-- Mark internet-requiring tools
UPDATE tools
SET requires_internet = TRUE,
    allowed_in_airgapped = FALSE,
    enabled_in_prod = FALSE
WHERE tool_id IN (
    'web_search',
    'http_fetch',
    'external_api_call',
    'dns_lookup',
    'whois_query'
);

-- Mark air-gapped safe tools
UPDATE tools
SET requires_internet = FALSE,
    allowed_in_airgapped = TRUE,
    enabled_in_prod = TRUE
WHERE tool_id IN (
    'local_file_read',
    'database_query',
    'regex_match',
    'json_parse',
    'qdrant_search'
);
```

**Action Items:**
1. Add `requires_internet` and `allowed_in_airgapped` to tool schema (T1)
2. Implement runtime validation in ToolValidator (T3)
3. Add environment flags to docker-compose.prod.yml (P4-F6)
4. Document air-gapped tool policy in operations guide (P4-F6)
5. Create tool audit report: "Show me all internet-requiring tools"

---

## Implementation Priority Matrix

| Integration | Phase | Priority | Effort | Impact | Dependencies |
|-------------|-------|----------|--------|--------|--------------|
| **Sampling Presets (ADR-023)** | P4 | 🔴 HIGH | 5-7 days | Enterprise determinism | None |
| **SOC Pattern Seeding** | P4 | 🟡 MEDIUM | 1-2 days | Developer productivity | Presets complete |
| **Output Contract Validation** | P4 | 🟡 MEDIUM | 2-3 days | Automation reliability | None |
| **Version Immutability** | P4 | 🟡 MEDIUM | 2-3 days | Change control | None |
| **Value Metrics Dashboard** | P5 | 🟢 LOW | 5-7 days | Business justification | Analytics infra |
| **ReAct Guardrails** | T3 | 🟡 MEDIUM | 1-2 days | Cost control | Tools Track T3 |
| **Air-Gapped Tool Control** | P4/T1 | 🟡 MEDIUM | 1-2 days | Enterprise security | Tool registry |
| **Prompt Linter (Basic)** | P4 | 🟡 MEDIUM | 3-4 days | Quality assurance | Presets, patterns |

---

## Recommended Implementation Sequence

### Phase 4 (November 2025)

**Week 1:**
1. ✅ ADR-023 Sampling Presets (schema, backend, validation) - 3 days
2. ✅ P3-F5 Output Formatting Engine - 3 days
3. ✅ Version Immutability + Clone workflow - 2 days

**Week 2:**
4. ✅ P3-F6 Use Case Validation & Testing (basic linter) - 3 days
5. ✅ SOC Pattern Seeding + Preset Migration - 2 days
6. ✅ Output Contract JSON Repair - 2 days

**Week 3-4:**
7. Security & Enterprise features (P4-F1 through P4-F5) per original plan

**Total P4 Duration:** 4-5 weeks (includes deferred P3 features)

### Phase 5 (Q1 2026)

- Value Metrics Dashboard (P5-F3 Enterprise Analytics)
- Embedding Model Migration (P5-F8)
- Advanced user management features

### Tools Track T3 (Q1 2026)

- Tool Executor with circuit breakers
- ReAct guardrails (max_tool_steps enforcement)
- Tool cost tracking integration

---

## Document Cross-References

**New Documents Created:**
- ✅ `docs/development/adrs/ADR-023-Sampling-Presets-and-Guardrails.md`
- ✅ `docs/development/analysis/2025-10-20-google-pdf-integration-assessment.md` (this document)

**Documents to Update:**
- `docs/development/plans/future/PHASE_04_SECURITY_ENTERPRISE.md` - Add P3-F5, P3-F6, Presets
- `docs/development/plans/TOOLS_IMPLEMENTATION_PLAN_PART3.md` - Correct T3/T4 status markers
- `ops/migrations/sql/seed_soc_patterns.sql` - New migration (create)

**Documents to Create (Next):**
- `docs/development/plans/features/active/P3-F5_OUTPUT_FORMATTING_ENGINE_SPEC.md`
- `docs/development/plans/features/active/P3-F6_USE_CASE_VALIDATION_TESTING_SPEC.md`

---

## Summary & Next Actions

### Key Takeaways

1. ✅ **Sampling Presets are the highest-value integration** - ADR-023 provides complete architecture
2. ✅ **Tools Status clarified** - T3/T4 are PENDING, not complete
3. ✅ **SOC patterns needed** - 5 new patterns specified, ready to seed
4. ✅ **Version immutability recommended** - Clone-for-edit workflow essential
5. ✅ **Value metrics** - Dashboard design ready for P5 implementation

### Immediate Actions (This Week)

1. **Review ADR-023** - Approve sampling preset architecture
2. **Update Phase 4 plan** - Add P3-F5, P3-F6, sampling presets to feature index
3. **Create P3-F5 spec** - Output Formatting Engine detailed specification
4. **Create P3-F6 spec** - Use Case Validation & Testing specification
5. **Correct T3/T4 status** - Update Part 3 document markers

### Next Sprint Actions

1. **Implement ADR-023** - Sampling presets (P4 priority 1)
2. **Seed SOC patterns** - Add 5 new patterns + preset migration
3. **Implement version immutability** - Clone-for-edit workflow
4. **Basic prompt linter** - High-entropy detection, preset validation

---

**Document Owner:** Project team
**Last Updated:** October 20, 2025
**Status:** Architecture Review Complete - Ready for Implementation Planning
**Next Review:** After P3-F5/P3-F6 specs created
