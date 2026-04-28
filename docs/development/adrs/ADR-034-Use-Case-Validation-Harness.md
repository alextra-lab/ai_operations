# ADR-034: Use Case Validation & Test Harness

**Status:** Accepted
**Date:** 2025-10-22
**Deciders:** Architecture Team
**Tags:** validation, testing, use-cases, quality, thresholds

---

## Context

**What is the issue we're addressing?**

With stateless architecture and run manifests, we need robust validation and testing for:

- **Use Case Quality:** Validate use case configurations before deployment
- **Performance Thresholds:** Ensure use cases meet latency and accuracy requirements
- **Regression Testing:** Prevent use case changes from breaking existing functionality
- **Quality Metrics:** Measure and track use case performance over time

**Current limitations:**
- No systematic validation of use case configurations
- Missing performance thresholds and quality gates
- No automated testing for use case changes
- Limited metrics for use case effectiveness

**Forces at play:**
- Stateless architecture requires higher quality use cases (no manual intervention)
- Run manifests provide telemetry data for quality measurement
- Need for automated validation in CI/CD pipelines
- Enterprise requirements for use case governance

---

## Decision

**What did we decide?**

**Implement comprehensive use case validation and test harness:**

- **Validation Engine:** 9 validation rules for use case configuration quality
- **Test Harness:** Automated testing framework with performance thresholds
- **Quality Metrics:** Hit@K, MRR, nDCG metrics for retrieval quality
- **Thresholds-as-Code:** Configurable quality gates for use case approval
- **Integration Testing:** End-to-end use case execution with validation

**Key Implementation Details:**
- 9 validation rules: prompt quality, configuration completeness, parameter validation
- Test query execution with output validation
- Performance thresholds: latency, accuracy, conformance scores
- YAML-based test suite configuration
- Integration with run manifests for quality tracking

---

## Alternatives Considered

### Option 1: Manual Validation Only
**Description:** Human review of use case configurations
**Pros:**
- Simple implementation
- Human judgment for complex cases

**Cons:**
- Not scalable for many use cases
- Inconsistent validation criteria
- No automated quality gates
- Manual process prone to errors

**Why Rejected:** Doesn't scale and lacks consistency for enterprise deployment

### Option 2: Basic Configuration Validation
**Description:** Simple schema validation only
**Pros:**
- Quick to implement
- Catches obvious errors

**Cons:**
- Doesn't validate prompt quality
- No performance testing
- Missing quality metrics
- Insufficient for production use

**Why Rejected:** Too basic for enterprise quality requirements

### Option 3: External Testing Framework
**Description:** Use external testing tools and frameworks
**Pros:**
- Leverage existing tools
- Rich testing capabilities

**Cons:**
- External dependencies
- Integration complexity
- Not tailored to use case specifics
- Air-gapped deployment concerns

**Why Rejected:** Internal framework provides better integration and air-gapped compatibility

---

## Consequences

### Positive Consequences

**Benefits of this decision:**
- **Quality Assurance:** Systematic validation prevents poor use case configurations
- **Performance Guarantees:** Thresholds ensure use cases meet requirements
- **Regression Prevention:** Automated testing catches breaking changes
- **Quality Metrics:** Measurable use case effectiveness over time
- **CI/CD Integration:** Automated quality gates in deployment pipelines
- **Enterprise Governance:** Controlled use case quality and approval process

### Negative Consequences

**Tradeoffs and costs:**
- **Implementation Complexity:** Comprehensive validation system requires significant development
- **Testing Overhead:** Additional testing time for use case changes
- **Threshold Tuning:** Requires ongoing adjustment of quality thresholds
- **Maintenance Burden:** Validation rules need updates as use cases evolve

### Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| False positives | Medium | Tune thresholds based on production data, allow overrides |
| Performance impact | Low | Run validation asynchronously, cache results |
| Threshold drift | Medium | Regular review and adjustment of quality gates |

---

## Implementation Notes

**Key implementation details:**

**Validation Rules (9 rules):**
1. **HighEntropyDetectionRule:** Detects dangerous parameter combinations
2. **EmptySystemPromptRule:** Blocks empty/short system prompts
3. **MissingDeveloperPromptRule:** Warns for JSON without developer prompt
4. **InsufficientFewShotsRule:** Suggests 3-5 examples
5. **VagueInstructionsRule:** Detects ambiguous language
6. **MaxTokensForPatternRule:** Validates max_tokens for pattern
7. **ReActWithoutToolStepsRule:** Blocks ReAct without max_tool_steps
8. **StrictOutputWithoutSchemaRule:** Blocks STRICT without schema
9. **RAGWithoutCollectionsRule:** Blocks RAG without collections

**Test Harness Components:**
```python
class UseCaseTestHarness:
    """Test harness for use case validation and performance testing."""

    async def validate_use_case(self, use_case: UseCase) -> ValidationReport:
        """Validate use case configuration."""
        ...

    async def execute_test_query(self, use_case: UseCase, query: str) -> TestResult:
        """Execute test query and validate output."""
        ...

    async def measure_performance(self, use_case: UseCase) -> PerformanceMetrics:
        """Measure use case performance metrics."""
        ...

    async def run_test_suite(self, test_suite: TestSuite) -> TestSuiteResult:
        """Execute full test suite with quality thresholds."""
        ...
```

**Quality Metrics:**
- **Hit@K:** Retrieval accuracy at different K values
- **MRR:** Mean Reciprocal Rank for retrieval quality
- **nDCG:** Normalized Discounted Cumulative Gain
- **Latency:** Response time percentiles (p50, p95, p99)
- **Conformance:** Schema validation and output quality scores

**Test Suite Configuration (YAML):**
```yaml
test_suite:
  name: "threat-triage-validation"
  use_case_id: "threat-triage-v1.2"
  thresholds:
    latency_p95_ms: 2500
    conformance_min: 0.95
    hit_at_5_min: 0.80
  test_queries:
    - query: "Analyze this threat..."
      expected_output_type: "threat_assessment"
      max_latency_ms: 2000
  validation_rules:
    - "high_entropy_detection"
    - "empty_system_prompt"
    - "sufficient_few_shots"
```

**Files affected:**
- `src/orchestrator/app/services/validation_engine.py`
- `src/orchestrator/app/services/test_harness.py`
- `src/orchestrator/app/schemas/validation.py`
- `src/orchestrator/app/schemas/test_suite.py`
- `src/orchestrator/app/routers/validation.py`
- `src/frontend-angular/src/app/components/validation-report/`
- `src/frontend-angular/src/app/components/use-case-test-panel/`

**Database Schema:**
```sql
CREATE TABLE test_suites (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  use_case_id TEXT NOT NULL,
  thresholds JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE test_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  test_suite_id UUID REFERENCES test_suites(id),
  query TEXT NOT NULL,
  result_kind TEXT NOT NULL,
  latency_ms INTEGER NOT NULL,
  conformance_score NUMERIC(4,3),
  metrics JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

---

## References

- [ADR-030: No Transcripts; Run Manifests Only](ADR-030-No-Transcripts-Run-Manifests.md)
- [P3-F6: Use Case Validation & Testing Spec](../features/completed/P3-F6_USE_CASE_VALIDATION_TESTING_SPEC.md)
- [Stateless Core v1 Implementation Plan](../plans/STATELESS_CORE_V1_IMPLEMENTATION_PLAN.md)

---

## Status Updates

### 2025-10-22 - Accepted
**Changed By:** Architecture Team
**Reason:** Essential for use case quality and enterprise governance in stateless architecture

### 2025-10-22 - Revised: Exemplar Storage Strategy
**Changed By:** Architecture Review
**Change:** Exemplars storage strategy simplified

**Original Design:**
- Separate `fewshot_exemplars` table in PostgreSQL
- Dedicated `ExemplarService` and `/api/v1/exemplars` endpoints
- Custom selection logic

**Revised Design:**
- **Exemplars are documents with `document_type="exemplar"`**
- Stored in regular collections (can be dedicated exemplar collections or mixed)
- Reuse existing document/collection infrastructure
- Selection via existing semantic search with `document_type` filter

**Rationale:**
- ✅ Eliminates duplicate infrastructure
- ✅ Exemplars ARE corpus content (knowledge to retrieve)
- ✅ Benefit from collection organization and access control
- ✅ Simpler architecture with less code to maintain
- ✅ Vectors naturally in Qdrant (existing pattern)

**Implementation:**
- Document upload UI: Add "Upload as Exemplar" mode with metadata fields
- Use case configuration: Reference exemplar collections
- Retrieval: Filter by `document_type="exemplar"` when selecting

**See:** ADR-021 Addendum 2 for complete exemplar-as-document pattern

---

**Template Version:** 1.0
**Based On:** [Michael Nygard's ADR pattern](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
