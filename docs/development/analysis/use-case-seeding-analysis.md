# Use Case Seeding Analysis

**Date:** 2025-10-26
**Issue:** Use cases lack input_fields, making them unusable in the UI

---

## Current Seeding Architecture

### 1. **SQL Migration 007** (`007_seed_use_cases.sql`)
Seeds 5 use cases:
- `threat-analysis-basic` - Threat analysis
- `log-investigation` - Log investigation
- `ioc-lookup` - IOC lookup
- `policy-review` - Policy review
- `incident-summary` - Incident summary

**Problem:** Creates `config_json` WITHOUT `input_fields` array ❌

### 2. **SQL Migrations 008 & 009** (`008_add_use_case_input_fields.sql`, `009_add_input_fields_to_existing_use_cases.sql`)
Adds `input_fields` to specific use cases by string `use_case_id`

**Problem:** Only updates use cases that match exact `use_case_id` strings ❌
- If migration 007 didn't run, these fail silently
- If use_case_id changed, input_fields won't be added
- No validation that all published use cases have input_fields

### 3. **Python Scripts** (`seed_templates.py`, `seed_phase1.py`, `seed_users.py`)
- `seed_templates.py`: Seeds PROMPT TEMPLATES (legacy, not use cases)
- `seed_phase1.py`: Seeds ONE test use case for Phase 1
- `seed_users.py`: Seeds users and roles

**Problem:** No unified Python script to seed use cases with proper validation ❌

---

## Root Cause Analysis

### Why Use Cases Have No Input Fields

The seeding process has a **2-step anti-pattern**:

```sql
-- Step 1: Create use case WITHOUT input_fields (Migration 007)
INSERT INTO use_cases (..., config_json) VALUES (..., '{
    "models": {...},
    "rag": {...}
    -- ❌ NO input_fields!
}'::jsonb);

-- Step 2: LATER add input_fields (Migration 008)
UPDATE use_cases
SET config_json = jsonb_set(config_json, '{input_fields}', '[...]'::jsonb)
WHERE use_case_id = 'specific-id';
```

**Problems:**
1. ⏱️ **Race condition**: If 008 doesn't run, use cases are broken
2. 🎯 **Fragile matching**: Depends on exact `use_case_id` strings
3. 🔍 **No validation**: Database allows published use cases without input_fields
4. 📝 **No audit trail**: Can't tell which use cases lack input_fields

---

## Impact on User Experience

**Frontend Behavior:**
```typescript
// use-case-execution.component.ts (line 180)
private setupExecutionForm(): void {
    if (!this.useCaseConfig?.template_config?.input_fields) return;
    // ❌ Returns early if input_fields is null/undefined/empty
    // User sees: "This use case doesn't require any input parameters"
}
```

**Backend Behavior:**
```python
# use_cases.py (line 388)
"input_fields": config.get("input_fields", []),
# ❌ Returns empty array [] if not in config_json
```

**Result:**
- ❌ Use case loads but shows "no input parameters"
- ❌ Execute button is disabled (canExecute = false)
- ❌ User cannot submit query
- ❌ 500 Internal Server Error when trying to execute

---

## Recommended Solutions

### Option 1: **Create Unified Python Seeder** (Recommended)

Create `ops/bootstrap/seed_use_cases.py`:

```python
#!/usr/bin/env python
"""Seed realistic SOC use cases with complete configuration."""

SOC_USE_CASES = [
    {
        "use_case_id": "threat-analysis-basic",
        "name": "Threat Analysis",
        "description": "Analyze security threats, IOCs, and alerts",
        "category": "security_analysis",
        "intent_type": "QUERY",
        "lifecycle_state": "published",
        "is_active": True,
        "config_json": {
            "input_fields": [  # ✅ Input fields included from the start
                {
                    "name": "query",
                    "type": "textarea",
                    "label": "Threat Analysis Query",
                    "description": "Describe the threat or paste IOCs/logs",
                    "required": True,
                    "placeholder": "Example: Analyze APT29 tactics...",
                    "default_value": ""
                }
            ],
            "models": {"llm": "foundation-sec-8b-instruct-mlx"},
            "generation_params": {
                "sampling_preset": "balanced",
                "temperature": 0.3,
                "max_tokens": 2000
            },
            "rag": {
                "enabled": True,
                "vector_collections": ["documents"],
                "top_k": 10,
                "similarity_threshold": 0.7
            },
            "output_contract": {"format": "text"},
            "policy": {
                "streaming_enabled": True,
                "streaming_default": False
            }
        },
        "metadata": {
            "prompts": {
                "system_prompt": "You are a cybersecurity threat analyst...",
                "developer_prompt": "Provide concise threat analysis..."
            }
        }
    }
    # ... more use cases
]

def seed_use_cases(session):
    """Seed use cases with validation."""
    for uc_data in SOC_USE_CASES:
        # Validate config has input_fields
        if not uc_data["config_json"].get("input_fields"):
            raise ValueError(f"Use case {uc_data['use_case_id']} missing input_fields!")

        # Check if exists
        existing = session.query(UseCase).filter(
            UseCase.use_case_id == uc_data["use_case_id"]
        ).first()

        if existing:
            print(f"Updating: {uc_data['use_case_id']}")
            for key, value in uc_data.items():
                setattr(existing, key, value)
        else:
            print(f"Creating: {uc_data['use_case_id']}")
            session.add(UseCase(**uc_data))

    session.commit()
    print(f"✓ Seeded {len(SOC_USE_CASES)} use cases")
```

**Benefits:**
- ✅ Single source of truth
- ✅ Validation at seed time
- ✅ Can be run repeatedly (idempotent)
- ✅ Easy to add new use cases
- ✅ Python type checking and IDE support

### Option 2: **Fix SQL Migrations** (Quick Fix)

Merge migrations 007, 008, 009 into one atomic migration:

```sql
-- 007_seed_use_cases_complete.sql
INSERT INTO use_cases (..., config_json) VALUES (..., '{
    "input_fields": [  -- ✅ Included in initial INSERT
        {
            "name": "query",
            "type": "textarea",
            ...
        }
    ],
    "models": {...},
    "rag": {...}
}'::jsonb);
```

**Benefits:**
- ✅ No 2-step process
- ✅ Atomic operation
- ✅ No race conditions

**Drawbacks:**
- ❌ Still SQL-based (harder to maintain)
- ❌ No validation
- ❌ Hard to add new use cases

### Option 3: **Add Database Constraint** (Safety Net)

```sql
-- Prevent published use cases without input_fields
ALTER TABLE use_cases
ADD CONSTRAINT use_cases_published_requires_input_fields
CHECK (
    lifecycle_state != 'published' OR
    (
        config_json->'input_fields' IS NOT NULL AND
        jsonb_array_length(config_json->'input_fields') > 0
    )
);
```

**Benefits:**
- ✅ Catches missing input_fields at database level
- ✅ Prevents future mistakes

**Drawbacks:**
- ❌ Requires fixing existing data first
- ❌ Doesn't help with current broken use cases

---

## Realistic SOC Use Case Examples

### 1. **Threat Intelligence Query**
```json
{
    "input_fields": [
        {
            "name": "threat_query",
            "type": "textarea",
            "label": "Threat Intelligence Query",
            "description": "Ask about threat actors, IOCs, TTPs, or campaigns",
            "required": true,
            "placeholder": "Example: What are the latest ransomware campaigns targeting healthcare?",
            "validation": {
                "min_length": 10,
                "max_length": 5000
            }
        },
        {
            "name": "timeframe",
            "type": "select",
            "label": "Timeframe",
            "required": false,
            "options": [
                {"value": "24h", "label": "Last 24 hours"},
                {"value": "7d", "label": "Last 7 days"},
                {"value": "30d", "label": "Last 30 days"},
                {"value": "all", "label": "All time"}
            ],
            "default_value": "30d"
        }
    ]
}
```

### 2. **IOC Enrichment**
```json
{
    "input_fields": [
        {
            "name": "ioc_value",
            "type": "text",
            "label": "Indicator of Compromise",
            "description": "IP address, domain, hash, or URL",
            "required": true,
            "placeholder": "192.0.2.1 or malicious.com or ab3f24...",
            "validation": {
                "pattern": "^(([0-9]{1,3}\\.){3}[0-9]{1,3}|[a-fA-F0-9]{32,64}|[a-z0-9.-]+\\.[a-z]{2,}|https?://.+)$"
            }
        },
        {
            "name": "ioc_type",
            "type": "select",
            "label": "IOC Type",
            "required": true,
            "options": [
                {"value": "ip", "label": "IP Address"},
                {"value": "domain", "label": "Domain Name"},
                {"value": "hash", "label": "File Hash (MD5/SHA256)"},
                {"value": "url", "label": "URL"}
            ]
        },
        {
            "name": "context",
            "type": "textarea",
            "label": "Additional Context (Optional)",
            "required": false,
            "placeholder": "Where did you find this IOC? Any suspicious behavior?"
        }
    ]
}
```

### 3. **Log Analysis**
```json
{
    "input_fields": [
        {
            "name": "log_data",
            "type": "textarea",
            "label": "Log Data",
            "description": "Paste security logs, SIEM alerts, or raw log entries",
            "required": true,
            "placeholder": "Oct 26 10:15:23 server1 sshd[12345]: Failed password for root from 192.0.2.1...",
            "validation": {
                "min_length": 50,
                "max_length": 10000
            }
        },
        {
            "name": "log_source",
            "type": "select",
            "label": "Log Source",
            "required": false,
            "options": [
                {"value": "syslog", "label": "Syslog"},
                {"value": "windows", "label": "Windows Event Log"},
                {"value": "firewall", "label": "Firewall"},
                {"value": "ids", "label": "IDS/IPS"},
                {"value": "other", "label": "Other"}
            ]
        },
        {
            "name": "analysis_focus",
            "type": "select",
            "label": "Analysis Focus",
            "required": false,
            "options": [
                {"value": "anomaly", "label": "Detect anomalies"},
                {"value": "correlation", "label": "Correlate events"},
                {"value": "timeline", "label": "Build timeline"},
                {"value": "indicators", "label": "Extract IOCs"}
            ],
            "default_value": "anomaly"
        }
    ]
}
```

### 4. **Incident Response Playbook**
```json
{
    "input_fields": [
        {
            "name": "incident_type",
            "type": "select",
            "label": "Incident Type",
            "required": true,
            "options": [
                {"value": "malware", "label": "Malware Infection"},
                {"value": "ransomware", "label": "Ransomware"},
                {"value": "phishing", "label": "Phishing Attack"},
                {"value": "data_breach", "label": "Data Breach"},
                {"value": "insider", "label": "Insider Threat"},
                {"value": "ddos", "label": "DDoS Attack"}
            ]
        },
        {
            "name": "severity",
            "type": "select",
            "label": "Severity Level",
            "required": true,
            "options": [
                {"value": "critical", "label": "Critical"},
                {"value": "high", "label": "High"},
                {"value": "medium", "label": "Medium"},
                {"value": "low", "label": "Low"}
            ]
        },
        {
            "name": "incident_details",
            "type": "textarea",
            "label": "Incident Details",
            "description": "Describe what happened, when, and what systems are affected",
            "required": true,
            "placeholder": "Ransomware detected on 5 production servers at 2AM..."
        }
    ]
}
```

---

## Recommended Action Plan

### Immediate (Fix Current State)
1. ✅ **Run migration 010** to add default input_fields to all published use cases
2. ✅ **Test in UI** - verify use cases now show input fields
3. ✅ **Verify execution** - test that use cases can be executed

### Short-term (Next Sprint)
1. 📝 **Create `seed_use_cases.py`** - Python-based seeding with validation
2. 🧪 **Add test cases** - verify seeded use cases work end-to-end
3. 🔒 **Add database constraint** - prevent future use cases without input_fields

### Long-term (Technical Debt)
1. 🗑️ **Deprecate migrations 007-009** - replace with Python seeder
2. 📚 **Document seeding process** - clear instructions for adding new use cases
3. 🎯 **Add UI validation** - warn admins if creating use case without input_fields

---

## Verification Checklist

After applying fixes, verify:

- [ ] All published use cases have `input_fields` in `config_json`
- [ ] Frontend renders input form for each use case
- [ ] Execute button is enabled when required fields filled
- [ ] Use case execution returns results (not 500 error)
- [ ] Input validation works (required fields, patterns, etc.)
- [ ] Historical use cases still work with new input_fields

---

## References

- ADR-037: UUID Primary Keys
- ADR-038: JSONB for Configuration
- P3-F1: Dynamic Form Generator
- Migration 010: `010_ensure_all_use_cases_have_input_fields.sql`
