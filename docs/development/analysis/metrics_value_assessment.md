# Execution Metrics - Value Assessment for SOC Users

## Executive Summary

Not all proposed metrics provide meaningful value to SOC analysts. This assessment categorizes each metric by business value and recommends which should be implemented.

---

## 🔴 HIGH VALUE - Critical for SOC Operations

### 1. Security Guard Details (content_filtered, pii_detected, toxicity_detected, jailbreak_attempt, blocked_categories)

**Value:** ⭐⭐⭐⭐⭐ **CRITICAL**

**Why It Matters:**

- **Compliance & Audit:** SOC teams MUST know if PII was detected/filtered for GDPR, HIPAA, etc.
- **Security Posture:** Jailbreak attempts indicate potential adversarial testing or misuse
- **Trust & Transparency:** Users need visibility into what security controls are active
- **Incident Response:** Blocked categories help identify if queries are hitting restricted topics

**User Benefit:**

- "Was my query sanitized?" → Direct answer
- "Did I accidentally include sensitive data?" → Immediate feedback
- Audit trail for security reviews

**Recommendation:** ✅ **IMPLEMENT - Essential for enterprise SOC deployment**

---

### 2. Cost Estimate (`cost_estimate`)

**Value:** ⭐⭐⭐⭐ **HIGH**

**Why It Matters:**

- **Budget Tracking:** Enterprise SOCs need cost visibility for AI operations
- **Query Optimization:** Users can see expensive queries and adjust behavior
- **Resource Management:** Management visibility into AI spend by use case

**User Benefit:**

- "How much does this query cost?" → Enables cost-conscious usage
- Aggregate cost reporting for ROI analysis
- Identify inefficient use patterns

**Recommendation:** ✅ **IMPLEMENT - Important for enterprise deployment**

---

## 🟡 MEDIUM VALUE - Useful for Power Users & Debugging

### 3. Retrieval/Processing Times (`retrieval_time_ms`, `processing_time_ms`)

**Value:** ⭐⭐⭐ **MEDIUM**

**Why It Matters:**

- **Performance Monitoring:** Identify slow queries or system bottlenecks
- **SLA Tracking:** Monitor if system meets performance requirements
- **User Experience:** Explain why some queries take longer

**User Benefit:**

- "Why is this slow?" → Visibility into which component is the bottleneck
- Historical performance trending

**Recommendation:** ⚠️ **NICE-TO-HAVE - Add if backend tracks these already**

- If retrieval service already measures this, expose it
- If not being tracked, deprioritize - total execution time is usually sufficient

---

### 4. Model Parameters (`temperature`, `max_tokens`)

**Value:** ⭐⭐⭐ **MEDIUM**

**Why It Matters:**

- **Transparency:** Power users want to know model configuration
- **Debugging:** Helps explain unexpected outputs (e.g., truncated responses)
- **Reproducibility:** Important for tuning and optimization

**User Benefit:**

- "Why was the response cut off?" → See max_tokens limit hit
- "Can I make responses more/less creative?" → See current temperature

**Recommendation:** ⚠️ **NICE-TO-HAVE - Add for power users**

- Useful for advanced users and administrators
- Not critical for day-to-day SOC operations
- Consider showing in "Advanced Metrics" section

---

## 🟢 LOW VALUE - Additional Information with Limited Utility

### 5. Total Documents Searched (`total_documents_searched`)

**Value:** ⭐⭐ **LOW**

**Why It Matters:**

- **System Health:** Indicates corpus size being queried
- **Context:** Shows scale of search operation

**User Benefit:**

- "How big is the knowledge base?" → Interesting but not actionable
- Minimal impact on user decision-making

**Recommendation:** ❌ **SKIP - Low actionability**

- User doesn't care about total corpus size during query execution
- More relevant as a system-level dashboard metric, not per-query
- `hits` and `top_k` already show retrieval effectiveness

---

### 6. Filtered Documents (`filtered_documents`)

**Value:** ⭐ **VERY LOW**

**Why It Matters:**

- **Debugging:** Shows how many docs were excluded by filters

**User Benefit:**

- Minimal - this is an internal implementation detail
- Only useful for debugging retrieval issues

**Recommendation:** ❌ **SKIP - Internal metric only**

- Not actionable for end users
- Belongs in logs, not user-facing metrics
- Adds clutter without value

---

### 7. Latency vs Processing Time

**Value:** ⭐ **DUPLICATE**

**Why It Matters:**

- Same metric, different units (ms vs seconds)

**Recommendation:** ❌ **SKIP - Already have `processing_time`**

- Keep backend's `processing_time` (seconds), convert in frontend if needed
- No reason to have both

---

## 🎯 Final Recommendations

### MUST IMPLEMENT (Backend Changes Required)

1. **Security Guard Details** - Parse from `guard.details` dict or request structured schema
   - Priority: P0 - Critical for SOC operations
   - Impact: Security, Compliance, Trust

2. **Cost Estimate** - Add to `model.metadata` or make it a top-level field
   - Priority: P1 - High value for enterprise
   - Impact: Budget tracking, Resource management

### SHOULD IMPLEMENT (If Easy)

3. **Processing Times** - If already tracked, expose in schemas
   - Priority: P2 - Useful for performance monitoring
   - Impact: Performance optimization, SLA tracking

4. **Model Parameters** - Add to `model.metadata` or schema
   - Priority: P3 - Power user feature
   - Impact: Transparency, Debugging

### SKIP (Not Worth Implementing)

5. ❌ Total Documents Searched - System metric, not per-query value
6. ❌ Filtered Documents - Internal implementation detail
7. ❌ Latency (separate from processing_time) - Redundant

---

## Recommended Implementation Strategy

### Phase 1: Essential Security & Cost (P0-P1)

```python
# Backend: Enhance GuardMetrics
class GuardMetrics(BaseModel):
    risk_score: float
    modified: bool
    details: Dict  # Already exists
    security_flags: GuardSecurityFlags  # NEW - structured details
    processing_time_ms: Optional[float]  # NEW

class GuardSecurityFlags(BaseModel):
    content_filtered: bool
    pii_detected: bool
    toxicity_detected: bool
    jailbreak_attempt: bool
    blocked_categories: List[str]

# Backend: Enhance ModelMetrics
class ModelMetrics(BaseModel):
    model_id: str
    tokens_in: int
    tokens_out: int
    total_tokens: int
    processing_time: float
    temperature: Optional[float]  # NEW
    max_tokens: Optional[int]     # NEW
    cost_estimate: Optional[float]  # NEW
    metadata: Dict
```

### Phase 2: Performance Metrics (P2)

```python
# Backend: Enhance RetrievalMetrics
class RetrievalMetrics(BaseModel):
    top_k: int
    hits: int
    avg_similarity: float
    min_similarity: float
    max_similarity: float
    source_count: int
    retrieval_time_ms: Optional[float]  # NEW
```

### Frontend: Update TypeScript Interface

```typescript
export interface GuardMetrics {
    risk_score: number;
    modified: boolean;
    details: { [key: string]: any };
    security_flags?: GuardSecurityFlags;  // NEW
    processing_time_ms?: number;          // NEW
}

export interface GuardSecurityFlags {
    content_filtered: boolean;
    pii_detected: boolean;
    toxicity_detected: boolean;
    jailbreak_attempt: boolean;
    blocked_categories: string[];
}

export interface ModelMetrics {
    model_id: string;
    tokens_in: number;
    tokens_out: number;
    total_tokens: number;
    processing_time: number;
    temperature?: number;      // NEW
    max_tokens?: number;       // NEW
    cost_estimate?: number;    // NEW
    metadata: { [key: string]: any };
}
```

---

## User Experience Impact

### Current HTML (After Alignment)

```
✅ Documents Retrieved
✅ Avg Similarity
✅ Similarity Range
✅ Source Count
✅ Risk Score
✅ Content Modified
✅ Model ID
✅ Token Usage
✅ Processing Time
```

### Enhanced HTML (Phase 1)

```
✅ Documents Retrieved
✅ Avg Similarity
✅ Similarity Range
✅ Source Count
✅ Risk Score
✅ Content Modified
🆕 Security Analysis (PII, Toxicity, Jailbreak, Blocked Categories)
✅ Model ID
✅ Token Usage
🆕 Model Configuration (Temperature, Max Tokens)
🆕 Cost Estimate
✅ Processing Time
```

**Impact:** 4 new high-value metrics without clutter

---

## Conclusion

**Implement:** Security details and cost estimate (P0-P1)
**Consider:** Processing times and model parameters (P2-P3)
**Skip:** Document counts and filtered metrics (Low/No value)

The key is focusing on metrics that help SOC analysts:

1. **Stay secure** (security flags)
2. **Manage costs** (cost estimate)
3. **Understand results** (model parameters)
4. **Monitor performance** (processing times)

Everything else is noise that adds complexity without user benefit.
