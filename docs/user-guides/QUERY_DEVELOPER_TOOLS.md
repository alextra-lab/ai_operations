# Query Developer Tools - User Guide

**Version:** 1.0
**Date:** November 1, 2025
**Status:** Active
**Related:** ADR-045, P4-TOOLS-01 through P4-TOOLS-07

---

## Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Semantic Search Tab](#semantic-search-tab)
4. [RAG Q&A Tab](#rag-qa-tab)
5. [Use Case Tester Tab](#use-case-tester-tab)
6. [Parameter Configuration](#parameter-configuration)
7. [Sampling Presets](#sampling-presets)
8. [Applying Parameters to Use Cases](#applying-parameters-to-use-cases)
9. [Metrics Dashboard](#metrics-dashboard)
10. [Repeatability Testing](#repeatability-testing)
11. [Troubleshooting](#troubleshooting)

---

## Overview

### What are Query Developer Tools?

Query Developer Tools is a unified interface for testing, tuning, and optimizing query configurations before applying them to Use Cases. It consolidates three previously separate tools into a single, cohesive developer experience.

**Key Features:**

- **Semantic Search Testing** - Test vector retrieval without LLM overhead
- **RAG Q&A Testing** - Test full RAG pipeline with LLM responses
- **Use Case Tester** - Test configurations with Use Case context
- **Parameter Injection** - Apply discovered parameters to Use Cases
- **Metrics Dashboard** - Performance analytics and recommendations
- **Shared Configuration** - Seamless state management across tabs

### Who Should Use This Tool?

- **Use Case Developers** (`use_case_publisher` role) - Test and tune configurations before creating Use Cases
- **Corpus Administrators** (`corpus_admin` role) - Verify semantic search after uploading documents
- **System Administrators** (`admin` role) - Benchmark performance and evaluate model trade-offs

### Navigation

**Access:** `/dev/query-tools` or Developer Tools → Query Developer Tools

**UI Structure:**

```
┌─────────────────────────────────────────┐
│ Query Developer Tools                   │
│ Test, tune, and optimize configurations │
├─────────────────────────────────────────┤
│ [Semantic Search] [RAG Q&A] [UC Tester] │ ← Tabs
├─────────────────────────────────────────┤
│                                          │
│  Tab Content Area (scrollable)          │
│                                          │
├─────────────────────────────────────────┤
│ [Apply to Use Case ▼]  [Export Config]  │ ← Footer
└─────────────────────────────────────────┘
```

---

## Getting Started

### Quick Start (5 minutes)

1. **Navigate** to `/dev/query-tools`
2. **Select** the Semantic Search tab
3. **Choose** a collection from the dropdown
4. **Enter** a test query (e.g., "What are the key findings?")
5. **Click** Execute or press `Enter` (if enabled)
6. **Review** results and metrics
7. **Tune** parameters (top_k, threshold) for better results
8. **Apply** to a Use Case when satisfied

### First-Time Setup

No setup required! The tool works with:
- ✅ Existing document collections
- ✅ Default system embedding model
- ✅ Configured LLM models (for RAG Q&A)

### Typical Workflow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Test with    │ ──> │ Tune params  │ ──> │ Apply to UC  │
│ Semantic     │     │ iteratively  │     │ (update/     │
│ Search       │     │              │     │  clone/new)  │
└──────────────┘     └──────────────┘     └──────────────┘
       │                     │                     │
       └─────────────────────┴─────────────────────┘
                    Review Metrics
```

---

## Semantic Search Tab

### Purpose

Test **vector retrieval only** without LLM overhead. Ideal for:
- Verifying document upload quality
- Tuning `top_k` and `similarity_threshold`
- Testing collection coverage
- Evaluating chunking strategies

### Interface

```
┌─────────────────────────────────────────┐
│ Collection: [documents_v2    ▼]         │
│ Top K: [10] (slider)                   │
│ Similarity Threshold: [0.6] (slider)   │
│ Query: [What are the compliance ...]   │
├─────────────────────────────────────────┤
│ Results (5 chunks retrieved):           │
│ ┌─────────────────────────────────────┐ │
│ │ 📄 compliance_policy.pdf             │ │
│ │ Relevance: 92.5%                     │ │
│ │ Chunk 3, Page 12                     │ │
│ │ "All systems must undergo quarterly │ │
│ │  security audits..."                 │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

### Parameters

| Parameter | Range | Default | Description |
|-----------|-------|---------|-------------|
| **Collection** | Dropdown | Required | Target vector collection |
| **Top K** | 1-100 | 10 | Number of chunks to retrieve |
| **Similarity Threshold** | 0.0-1.0 | 0.6 | Minimum cosine similarity |
| **ef_search** (Advanced) | 16-512 | 128 | HNSW search quality |

### Best Practices

✅ **DO:**
- Start with default parameters (top_k=10, threshold=0.6)
- Test multiple queries to evaluate coverage
- Review similarity scores for consistency
- Use "Apply to Use Case" after validation

❌ **DON'T:**
- Set top_k > 50 (diminishing returns, increased cost)
- Set threshold < 0.5 (poor relevance)
- Test with only one query
- Skip parameter documentation

### Interpreting Results

**Similarity Score Ranges:**

- **90-100%** - Excellent match, likely exact or near-duplicate
- **75-90%** - Good match, semantically similar
- **60-75%** - Moderate match, contextually related
- **50-60%** - Weak match, may not be relevant
- **< 50%** - Poor match, likely noise

**Common Issues:**

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| All scores < 60% | Query too vague | Refine query, add keywords |
| Only 1-2 results | Collection too small | Upload more documents |
| Duplicates | Chunking too small | Review chunk size in collection |
| Missing expected docs | Wrong collection | Verify collection selection |

---

## RAG Q&A Tab

### Purpose

Test **full RAG pipeline** with LLM response generation. Ideal for:
- Validating end-to-end workflow
- Tuning LLM parameters (temperature, max_tokens)
- Testing sampling presets
- Evaluating response quality

### Interface

```
┌─────────────────────────────────────────┐
│ LLM Model: [gpt-4o            ▼]        │
│ Sampling Preset: [BALANCED    ▼]        │
│ Collection: [documents_v2     ▼]        │
│ Top K: [10] | Threshold: [0.6]          │
│ Query: [What are the key security ...]  │
├─────────────────────────────────────────┤
│ 💬 You                     1/1/25 10:00 │
│ What are the key security requirements? │
│                                          │
│ 🤖 Assistant               1/1/25 10:01 │
│ Based on the compliance policy, the key │
│ security requirements are:               │
│ 1. Quarterly security audits             │
│ 2. Multi-factor authentication...        │
│                                          │
│ 📊 Metrics                               │
│ Latency: 1.2s | Tokens: 350 | Cost: $0.01
└─────────────────────────────────────────┘
```

### Parameters

| Parameter | Range | Default | Description |
|-----------|-------|---------|-------------|
| **LLM Model** | Dropdown | gpt-4o | Language model |
| **Sampling Preset** | Dropdown | BALANCED | Temperature/top_p preset |
| **Temperature** (Custom) | 0.0-2.0 | 0.65 | Randomness (CUSTOM only) |
| **Max Tokens** | 100-8000 | 2000 | Maximum response length |
| **Top P** (Custom) | 0.0-1.0 | 0.95 | Nucleus sampling (CUSTOM only) |
| **RAG Parameters** | - | - | Same as Semantic Search |

### Sampling Presets (ADR-023)

| Preset | Temperature | Top P | Use Case |
|--------|-------------|-------|----------|
| **STRICT** | 0.15 | 0.90 | Compliance, legal, factual responses |
| **BALANCED** | 0.65 | 0.95 | General use (recommended) |
| **CREATIVE** | 0.85 | 0.98 | Brainstorming, exploratory |
| **CUSTOM** | User-defined | User-defined | Advanced tuning |

**High-Entropy Warning:**

When `temperature > 0.9` AND `top_p > 0.97`:
```
⚠️ High Entropy Detected
Temperature (1.2) and top_p (0.98) may produce inconsistent results.
Consider using BALANCED preset for production use cases.
```

### Streaming Responses

RAG Q&A uses **Server-Sent Events (SSE)** for real-time streaming:

1. Query submitted
2. Spinner appears
3. Response streams word-by-word
4. Auto-scroll follows latest content
5. Metrics displayed on completion

**Auto-Scroll Behavior:**
- ✅ Enabled by default
- 📜 Pauses if you scroll up (reading previous content)
- ▼ Resumes if you scroll back to bottom

### Best Practices

✅ **DO:**
- Start with BALANCED preset
- Test with 3-5 representative queries
- Review metrics for cost/latency trade-offs
- Use STRICT for compliance-critical Use Cases
- Export configuration before applying

❌ **DON'T:**
- Use CREATIVE preset for factual Use Cases
- Set max_tokens too high (increased cost)
- Use CUSTOM without understanding parameters
- Skip testing with edge cases

---

## Use Case Tester Tab

### Purpose

Test configurations **within Use Case context**. Coming in Phase 5.

### Planned Features

- Load existing Use Case configuration
- Override parameters for testing
- Compare results against baseline
- A/B test different configurations

**Status:** Placeholder in current release
**Timeline:** Phase 5 (Q1 2026)

---

## Parameter Configuration

### Parameter Panel

All parameters accessible in collapsible panel:

```
┌─────────────────────────────────────────┐
│ ▼ Configuration                          │
├─────────────────────────────────────────┤
│ Model Selection                          │
│  LLM Model: [gpt-4o         ▼]          │
│  Embedding: (System default)             │
│                                          │
│ Sampling                                 │
│  Preset: [BALANCED          ▼]          │
│                                          │
│ RAG Parameters                           │
│  Collections: [documents_v2  ▼]         │
│  Top K: [──●────────] 10                │
│  Threshold: [─────●───] 0.60            │
│                                          │
│ ▼ Advanced Settings                      │
│  Max Tokens: [2000]                     │
│  ef_search: [128]                       │
│  Distance Metric: [COSINE   ▼]          │
└─────────────────────────────────────────┘
```

### Parameter Groups

**1. Model Configuration** (RAG Q&A only)
- LLM model selection
- Embedding model (display only, system-wide)
- Sampling preset

**2. RAG Parameters** (Both tabs)
- Collection selection (multi-select)
- Top K (chunks to retrieve)
- Similarity threshold

**3. Advanced Settings**
- Max tokens (response length)
- ef_search (HNSW quality)
- Distance metric (COSINE recommended)

### Collapsible UI

- **Collapsed:** Saves vertical space, shows summary
- **Expanded:** Full parameter controls
- **State:** Persisted to localStorage
- **Auto-expand:** When validation errors present

---

## Sampling Presets

### Overview

Sampling presets (ADR-023) simplify LLM parameter selection:

- **Preset-based** - Choose STRICT/BALANCED/CREATIVE
- **Custom override** - Advanced users only
- **High-entropy detection** - Warns about inconsistent configs
- **Use Case inheritance** - Apply preset to Use Case

### Preset Details

#### STRICT (Temperature: 0.15, Top P: 0.90)

**Best for:**
- ✅ Compliance documentation
- ✅ Legal analysis
- ✅ Factual summaries
- ✅ Data extraction

**Characteristics:**
- Highly deterministic
- Minimal creativity
- Consistent outputs
- Lower token variance

**Example Use Cases:**
- Extract PII from documents
- Classify MITRE ATT&CK techniques
- Generate audit reports

#### BALANCED (Temperature: 0.65, Top P: 0.95)

**Best for:**
- ✅ General Q&A
- ✅ Threat intelligence summaries
- ✅ Investigation assistance
- ✅ Most SOC workflows

**Characteristics:**
- Moderate variability
- Natural language
- Good balance of accuracy/fluency
- Recommended default

**Example Use Cases:**
- Summarize security alerts
- Answer analyst questions
- Generate incident timelines

#### CREATIVE (Temperature: 0.85, Top P: 0.98)

**Best for:**
- ✅ Brainstorming
- ✅ Hypothesis generation
- ✅ Exploratory analysis
- ⚠️ NOT for compliance/legal

**Characteristics:**
- High variability
- More diverse outputs
- Less deterministic
- Higher token usage

**Example Use Cases:**
- Generate attack scenarios
- Brainstorm mitigation strategies
- Explore threat actor TTPs

### Custom Preset

**When to use:**
- Specific workflow requirements
- A/B testing different configurations
- Research and development

**Parameters:**
- Temperature: 0.0-2.0 (0.1 increments)
- Top P: 0.0-1.0 (0.01 increments)
- Max Tokens: 100-8000

**⚠️ Warning:** CUSTOM preset requires understanding of:
- Temperature effects on randomness
- Top P (nucleus sampling) behavior
- Interaction between temperature and top_p
- Cost implications of max_tokens

---

## Applying Parameters to Use Cases

### Overview

After testing and tuning, apply parameters to Use Cases via three workflows:

1. **Update Existing Draft** - Merge into your draft
2. **Clone & Apply** - Clone published UC, inject params
3. **Create New Use Case** - Start wizard with pre-filled config

### Workflow 1: Update Existing Draft

**Use Case:** You have a draft Use Case and want to update parameters

**Steps:**

1. Configure and test parameters in Query Developer Tools
2. Click **"Apply to Use Case" ▼** in footer
3. Select **"Update Existing Draft"**
4. Choose your draft from dropdown
   ```
   ┌─────────────────────────────────────┐
   │ Select Draft Use Case               │
   ├─────────────────────────────────────┤
   │ ○ TI Summary (draft)                │
   │   Owner: You | Modified: 1 day ago  │
   │                                      │
   │ ○ Alert Triage (draft)              │
   │   Owner: You | Modified: 3 days ago │
   └─────────────────────────────────────┘
   ```
5. Click **"Apply Parameters"**
6. Review success message with navigation link

**Permissions:**
- ✅ Can update own drafts
- ✅ Admin can update any draft
- ❌ Cannot update others' drafts (unless admin)

**Metadata Added:**
```json
{
  "parameter_source": "query_developer_tools",
  "tuned_by_user_id": "uuid",
  "tuned_at": "2025-11-01T10:30:00Z",
  "source_test_queries": ["query1", "query2"]
}
```

### Workflow 2: Clone & Apply

**Use Case:** You want to modify a published Use Case

**Steps:**

1. Configure and test parameters
2. Click **"Apply to Use Case" ▼**
3. Select **"Clone Published & Apply"**
4. Choose published Use Case from dropdown
   ```
   ┌─────────────────────────────────────┐
   │ Select Published Use Case           │
   ├─────────────────────────────────────┤
   │ ○ Threat Intel Summary (v2.1)       │
   │   Published: 2 weeks ago            │
   │                                      │
   │ ○ MITRE Mapper (v1.0)               │
   │   Published: 1 month ago            │
   └─────────────────────────────────────┘
   ```
5. System creates draft clone
6. Parameters injected into clone
7. Navigate to wizard to complete

**Permissions:**
- ✅ Anyone can clone published UCs
- ✅ Parameters apply to clone (not original)
- ✅ Original UC unchanged (immutable)

**Metadata Added:**
```json
{
  "cloned_from": "original_uc_id",
  "parameter_source": "query_developer_tools",
  "tuned_by_user_id": "uuid",
  "tuned_at": "2025-11-01T10:30:00Z",
  "source_test_queries": ["query1", "query2"]
}
```

### Workflow 3: Create New Use Case

**Use Case:** You want to start fresh with tested parameters

**Steps:**

1. Configure and test parameters
2. Click **"Apply to Use Case" ▼**
3. Select **"Create New Use Case"**
4. Use Case Wizard opens with pre-filled:
   - Step 1: Name/Description (empty)
   - Step 2: Pattern (optional)
   - Step 3: Prompts (example from test queries)
   - Step 4: **Configuration (pre-filled)** ✓
   - Step 5: Preview
5. Complete wizard and save

**Pre-filled Configuration:**
```yaml
LLM Model: gpt-4o
Sampling Preset: BALANCED
Collections: [documents_v2]
Top K: 10
Similarity Threshold: 0.6
Max Tokens: 2000
```

### Parameter Diff Viewer

When applying to existing draft, view what will change:

```
┌─────────────────────────────────────────┐
│ Parameter Changes                        │
├─────────────────────────────────────────┤
│ LLM Model                                │
│  - gpt-3.5-turbo                         │
│  + gpt-4o                                │
│                                          │
│ Sampling Preset                          │
│  - STRICT                                │
│  + BALANCED                              │
│                                          │
│ Top K                                    │
│  - 5                                     │
│  + 10                                    │
│                                          │
│ Collections (added)                      │
│  + documents_v2                          │
└─────────────────────────────────────────┘
```

---

## Metrics Dashboard

### Overview

View performance analytics and get recommendations based on execution metrics.

**Access:** Appears after query execution in all tabs

### Metrics Display

```
┌─────────────────────────────────────────┐
│ 📊 Execution Metrics                     │
├─────────────────────────────────────────┤
│ Retrieval:  150ms  │ Generation: 850ms  │
│ Total: 1.0s        │ Tokens: 350        │
│ Cost: $0.0105      │ Confidence: 85%    │
├─────────────────────────────────────────┤
│ Retrieval Details                        │
│  Chunks Retrieved: 5                     │
│  Avg Similarity: 82.0%                   │
│  Collections: documents_v2               │
├─────────────────────────────────────────┤
│ Guard Details                            │
│  Risk Score: 0.15 (Low)                  │
│  Checks: [toxicity, pii]                 │
└─────────────────────────────────────────┘
```

### Metrics Categories

#### Timing

- **Retrieval Time** - Vector search duration
- **Generation Time** - LLM response duration
- **Total Time** - End-to-end latency

**Performance Targets:**
- Retrieval: < 200ms (good), < 500ms (acceptable)
- Generation: < 2s (good), < 5s (acceptable)
- Total: < 3s (good), < 7s (acceptable)

#### Tokens

- **Input Tokens** - Query + context
- **Output Tokens** - Response length
- **Total Tokens** - Sum (affects cost)

**Cost Formula:**
```
Cost = (input_tokens × input_price) + (output_tokens × output_price)
```

**Example (GPT-4o):**
```
Input: 2,500 tokens × $0.005/1K = $0.0125
Output: 500 tokens × $0.015/1K = $0.0075
Total: $0.0200
```

#### Retrieval Quality

- **Chunks Retrieved** - Number of chunks (should match top_k)
- **Avg Similarity** - Mean cosine similarity
- **Collections Searched** - Collections queried

**Quality Indicators:**
- Avg Similarity > 75% - Excellent
- Avg Similarity 60-75% - Good
- Avg Similarity < 60% - Poor (tune parameters)

#### Security (LLM Guard)

- **Risk Score** - 0.0 (low) to 1.0 (high)
- **Checks Performed** - toxicity, pii, prompt_injection
- **Warnings** - Security concerns detected

### Recommendations Engine

Based on metrics, system provides actionable recommendations:

**Example Recommendations:**

```
💡 Recommendations

1. Retrieval Quality
   Avg similarity (62%) is below optimal.
   → Try increasing similarity_threshold to 0.65

2. Cost Optimization
   Average cost ($0.025/query) is above target.
   → Consider using gpt-3.5-turbo for non-critical queries

3. Latency
   Generation time (4.2s) exceeds target.
   → Reduce max_tokens from 4000 to 2000
   → Consider shorter system prompt

4. Token Usage
   Output tokens averaging 800 (high variance).
   → Add explicit length constraints to prompt
   → Use max_tokens as hard limit
```

### Export Metrics

**Formats:**
- CSV - For spreadsheet analysis
- JSON - For programmatic access

**CSV Structure:**
```csv
timestamp,query,latency_ms,tokens,cost,avg_similarity,confidence
2025-11-01 10:00:00,What are key findings?,1234,350,0.0105,0.82,0.85
2025-11-01 10:05:23,Summarize threats,1567,425,0.0127,0.78,0.81
```

**JSON Structure:**
```json
{
  "timestamp": "2025-11-01T10:00:00Z",
  "query": "What are key findings?",
  "metrics": {
    "timing": { "total_time_ms": 1234 },
    "tokens": { "total_tokens": 350 },
    "cost": { "total_cost": 0.0105 },
    "retrieval": { "avg_similarity": 0.82 },
    "confidence_score": 0.85
  }
}
```

---

## Repeatability Testing

### Purpose

Test **consistency** of responses across multiple executions with identical parameters.

### How It Works

1. Configure parameters
2. Enter test query
3. Click **"Run Repeatability Test"** (coming soon)
4. System executes query 5-10 times
5. Calculates consistency metrics:
   - Token variance
   - Response similarity (cosine)
   - Latency variance

### Consistency Metrics

**Consistency Score:**
```
Score = average_similarity_across_runs

90-100% - Highly consistent (STRICT preset)
75-90%  - Moderately consistent (BALANCED preset)
60-75%  - Variable (CREATIVE preset)
< 60%   - Inconsistent (CUSTOM high-entropy)
```

**Expected by Preset:**
- STRICT: 95-99% (minimal variance)
- BALANCED: 80-90% (moderate variance)
- CREATIVE: 65-80% (high variance)

### Use Cases

✅ **When to test:**
- Before deploying to production
- After major parameter changes
- Validating STRICT preset behavior
- Compliance-critical Use Cases

❌ **When not to test:**
- CREATIVE preset (variance expected)
- Exploratory workflows
- Brainstorming Use Cases

---

## Troubleshooting

### Common Issues

#### No Results Returned

**Symptom:** Query executes but returns 0 chunks

**Causes:**
1. Collection empty/incorrect
2. Similarity threshold too high
3. Query too specific

**Solutions:**
```
1. Verify collection has documents:
   → Go to Documents → Collections
   → Check document count

2. Lower similarity threshold:
   → Try 0.5 instead of 0.6

3. Broaden query:
   → Use keywords instead of full sentences
   → Try synonyms
```

#### High Latency

**Symptom:** Queries take > 5 seconds

**Causes:**
1. Large top_k value
2. Multiple collections
3. High max_tokens

**Solutions:**
```
1. Reduce top_k:
   → Try 10 instead of 50

2. Search fewer collections:
   → Start with one collection
   → Add more only if needed

3. Reduce max_tokens:
   → Try 1000 instead of 4000
```

#### Inconsistent Responses

**Symptom:** Same query returns different results

**Causes:**
1. High temperature
2. CREATIVE/CUSTOM preset
3. High top_p

**Solutions:**
```
1. Use STRICT preset:
   → Switch from CREATIVE to STRICT

2. Lower temperature:
   → Try 0.3 instead of 0.9

3. Lower top_p:
   → Try 0.90 instead of 0.98
```

#### "Apply to Use Case" Disabled

**Symptom:** Button is grayed out

**Causes:**
1. No LLM model selected (RAG Q&A)
2. No meaningful configuration
3. No collections selected

**Solutions:**
```
1. Select LLM model:
   → Choose from dropdown (RAG Q&A tab)

2. Configure parameters:
   → Set at least one of:
     - Sampling preset
     - Collections
     - Top K

3. Verify collection selection:
   → At least one collection required
```

#### High-Entropy Warning

**Symptom:** Orange warning banner appears

**Message:**
```
⚠️ High Entropy Detected
Temperature (1.2) and top_p (0.98) may produce
inconsistent results.
```

**Causes:**
- Temperature > 0.9 AND top_p > 0.97

**Solutions:**
```
1. Use preset (recommended):
   → Switch to BALANCED or STRICT

2. Lower temperature:
   → Try 0.7 instead of 1.2

3. Lower top_p:
   → Try 0.95 instead of 0.98

4. Understand trade-offs:
   → High entropy = high variability
   → May be acceptable for creative workflows
   → NOT recommended for compliance
```

### Error Messages

| Error | Meaning | Solution |
|-------|---------|----------|
| `Collection not found` | Selected collection doesn't exist | Refresh page, reselect collection |
| `Insufficient permissions` | User lacks role for operation | Contact admin for role assignment |
| `Model not available` | LLM model not configured | Select different model or contact admin |
| `Rate limit exceeded` | Too many requests | Wait 60 seconds, then retry |
| `Invalid parameter combination` | Conflicting settings | Review parameter values |

### Getting Help

**Internal Resources:**
- **ADR-045** - Architecture decisions
- **API Documentation** - `/docs/api/use-case-management.md`
- **Testing Guide** - `/docs/testing/TESTING_GUIDE.md`

**Support Channels:**
- System admin (`admin` role users)
- Documentation issues: Create GitHub issue
- Feature requests: Contact product team

---

## Keyboard Shortcuts

| Shortcut | Action | Context |
|----------|--------|---------|
| **Enter** | Execute query | When "Enter to Execute" enabled |
| **Shift+Enter** | New line | Query input field |
| **Ctrl+/** | Toggle "Enter to Execute" | Any tab |
| **Ctrl+E** | Export configuration | Any tab |
| **Tab** | Next tab | Tab navigation |
| **Shift+Tab** | Previous tab | Tab navigation |

---

## Best Practices Summary

### DO ✅

1. **Start Simple**
   - Use default parameters (top_k=10, threshold=0.6, BALANCED preset)
   - Test with 3-5 representative queries
   - Review metrics before applying

2. **Iterate Methodically**
   - Change ONE parameter at a time
   - Document what works
   - Export configuration

3. **Validate Before Applying**
   - Test edge cases
   - Check consistency (repeatability)
   - Review cost projections

4. **Use Presets**
   - STRICT for compliance
   - BALANCED for general use
   - CREATIVE for brainstorming

5. **Monitor Metrics**
   - Track latency trends
   - Watch cost per query
   - Validate retrieval quality

### DON'T ❌

1. **Avoid Over-Tuning**
   - Don't change multiple parameters simultaneously
   - Don't obsess over minor improvements
   - Don't skip documentation

2. **Respect Presets**
   - Don't use CREATIVE for compliance
   - Don't use STRICT for brainstorming
   - Don't use CUSTOM without understanding

3. **Watch Costs**
   - Don't set max_tokens unnecessarily high
   - Don't test with expensive models
   - Don't ignore cost metrics

4. **Maintain Quality**
   - Don't lower threshold below 0.5
   - Don't increase top_k beyond 50 without reason
   - Don't skip validation

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Nov 1, 2025 | Initial release - P4-TOOLS-08 completion |

---

**Questions or Feedback?**
Contact your system administrator or refer to ADR-045 for architectural details.
