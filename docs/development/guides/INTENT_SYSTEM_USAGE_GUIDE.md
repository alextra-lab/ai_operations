# Dynamic Intent System - Usage Guide

**Related:** [ADR-016 Dynamic Intent System](../adrs/ADR-016-Dynamic-Intent-System.md)

This guide shows practical examples of how the dynamic intent system works from both admin and user perspectives.

---

## Quick Start

### As an Admin: Adding a New Intent

```bash
# 1. Create intent through API
curl -X POST http://localhost:8006/api/v1/admin/intents/types \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "intent_code": "MALWARE_ANALYSIS",
    "display_name": "Malware Analysis",
    "description": "Analyze malware samples and provide remediation guidance",
    "category_id": "<security-category-uuid>",
    "system_prompt_template": "You are a malware analyst with expertise in reverse engineering and threat analysis. Provide detailed analysis of samples, including behavior, IOCs, and remediation steps.",
    "recommended_model": "mistral-large",
    "default_temperature": 0.3,
    "default_max_tokens": 4096,
    "rag_top_k": 10,
    "rag_similarity_threshold": 0.8,
    "rag_required_tags": ["malware", "threat-intel"],
    "allowed_tool_ids": ["<yara-tool-uuid>", "<sandbox-tool-uuid>"],
    "icon": "bug_report",
    "color": "#E91E63"
  }'
```

### As a Developer: Creating a Use Case with New Intent

```python
# config/templates/use-cases/malware_triage.yaml

use_case_id: malware-triage-001
name: "Malware Sample Triage"
description: "Quick triage analysis of malware samples"
category: "Malware Analysis"
version: "1.0.0"

# NEW: Intent code instead of hardcoded enum
intent_code: "MALWARE_ANALYSIS"  # ← Dynamic lookup

# Use Case inherits these from intent_code unless overridden:
# - system_prompt_template
# - recommended_model
# - default_temperature
# - rag_parameters
# - allowed_tools

# Optional: Override intent defaults for this specific use case
overrides:
  temperature: 0.2  # More precise for this use case
  max_tokens: 3000

ui_config:
  input_sections:
    - section_id: "sample_info"
      title: "Malware Sample Information"
      fields:
        - field_name: "sample_hash"
          label: "File Hash (SHA256)"
          field_type: "text_input"
          required: true
        - field_name: "sample_behavior"
          label: "Observed Behavior"
          field_type: "text_area"

execution_config:
  timeout_seconds: 180
  supports_streaming: true
```

### As a User: Using the Intent

```typescript
// Frontend - User selects use case
const useCase = await useCaseService.getUseCase('malware-triage-001');

// Use case shows:
// - Icon: 🐛 (bug_report)
// - Color: Pink (#E91E63)
// - Category: Security > Malware Analysis
// - Intent: MALWARE_ANALYSIS

// User provides inputs
const execution = {
  use_case_id: 'malware-triage-001',
  inputs: {
    sample_hash: 'a1b2c3d4...',
    sample_behavior: 'Process creates suspicious registry keys...'
  }
};

// System automatically:
// 1. Loads MALWARE_ANALYSIS intent config
// 2. Uses mistral-large model
// 3. Applies temperature 0.2 (overridden)
// 4. Retrieves context with tags: ['malware', 'threat-intel']
// 5. Makes tools available: [yara, sandbox]
// 6. Generates response using intent's system prompt

const response = await executionService.executeUseCase(execution);

// Response maintains intent context for follow-ups
// All messages in conversation use same intent configuration
```

---

## Real-World Scenarios

### Scenario 1: Legal Department Needs Contract Analysis

**Problem:** Legal team wants AI assistance for contract review, but current system only has SOC intents.

**Solution:**

```bash
# 1. Admin creates LEGAL category (if not exists)
curl -X POST /api/v1/admin/intents/categories \
  -d '{
    "category_code": "LEGAL",
    "display_name": "Legal Affairs",
    "icon": "gavel",
    "color": "#9C27B0"
  }'

# 2. Admin creates CONTRACT_REVIEW intent
curl -X POST /api/v1/admin/intents/types \
  -d '{
    "intent_code": "CONTRACT_REVIEW",
    "display_name": "Contract Review",
    "category_id": "<legal-category-uuid>",
    "system_prompt_template": "You are a legal expert specializing in contract law. Analyze contracts for:\n- Key obligations and rights\n- Potential risks and liabilities\n- Compliance with regulations\n- Negotiation points\n\nProvide structured, actionable insights.",
    "recommended_model": "mistral-large",
    "default_temperature": 0.2,
    "rag_required_tags": ["legal", "contracts"],
    "icon": "description"
  }'

# 3. Grant permission to legal team
curl -X POST /api/v1/admin/intents/roles/permissions \
  -d '{
    "role_name": "legal_counsel",
    "intent_id": "<contract-review-intent-uuid>",
    "can_use": true
  }'

# 4. Developer creates use case
# config/templates/use-cases/contract_analysis.yaml
```

**Result:** Legal team now has dedicated AI assistant for contract review with appropriate model, prompts, and knowledge base access.

---

### Scenario 2: Multi-Organization SaaS Deployment

**Problem:** Deploying AI Operations Platform (AIOP) for multiple organizations with different needs:
- **Org A (Financial):** Needs fraud detection, transaction analysis
- **Org B (Healthcare):** Needs patient data analysis, HIPAA compliance
- **Org C (Government):** Needs security + compliance intents

**Solution:**

```python
# Add organization_id to intent_types table
ALTER TABLE intent_types ADD COLUMN organization_id UUID;

# Org A: Financial intents
POST /api/v1/admin/intents/types
{
  "intent_code": "FRAUD_DETECTION",
  "organization_id": "org-a-uuid",
  "category_id": "<finance-category>",
  ...
}

# Org B: Healthcare intents
POST /api/v1/admin/intents/types
{
  "intent_code": "HIPAA_COMPLIANCE_CHECK",
  "organization_id": "org-b-uuid",
  "category_id": "<compliance-category>",
  ...
}

# Org C: Use default security intents
# No custom intents needed, uses system intents
```

**Result:** Each organization sees only relevant intents, enabling true multi-tenant SaaS.

---

### Scenario 3: Intent Marketplace / Plugin System

**Problem:** Third-party wants to contribute specialized intents (e.g., "Blockchain Transaction Analysis").

**Solution:**

```python
# Intent definition as JSON/YAML plugin
# plugins/intents/blockchain_analysis.yaml
plugin:
  name: "Blockchain Analysis Intent"
  version: "1.0.0"
  author: "CryptoSec Inc"
  license: "MIT"

intent:
  intent_code: "BLOCKCHAIN_ANALYSIS"
  display_name: "Blockchain Transaction Analysis"
  description: "Analyze blockchain transactions for suspicious patterns"
  category_code: "SECURITY"

  system_prompt_template: |
    You are a blockchain forensics expert. Analyze transactions for:
    - Money laundering patterns
    - Wallet clustering
    - Entity attribution
    - Compliance risks

  recommended_model: "mistral-large"
  default_temperature: 0.3

  required_tools:
    - name: "blockchain_explorer"
      version: ">=1.0.0"

  rag_config:
    required_tags: ["blockchain", "crypto", "forensics"]
    similarity_threshold: 0.8

# Admin installs plugin
fusioncentral intent install plugins/intents/blockchain_analysis.yaml

# System automatically:
# 1. Validates plugin format
# 2. Checks tool dependencies
# 3. Creates intent in database
# 4. Adds to available intents
```

**Result:** Extensible platform where community can contribute specialized intents.

---

## Admin UI Mockup (Concept)

```typescript
// Intent Management Page
┌─────────────────────────────────────────────────────────────┐
│ Intent Management                                [+ New]     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ 📂 Security Operations (4 intents)                          │
│   ✓ QUERY - General Query                       [Edit][Del] │
│   ✓ RULE_GENERATION - Detection Rules           [Edit]      │ ← System
│   ✓ ENRICHMENT - Threat Intel                   [Edit]      │ ← System
│   ○ MALWARE_ANALYSIS - Malware Triage           [Edit][Del] │
│                                                               │
│ 📂 Legal Affairs (2 intents)                                │
│   ○ CONTRACT_REVIEW - Contract Analysis         [Edit][Del] │
│   ○ LEGAL_RESEARCH - Case Law Research          [Edit][Del] │
│                                                               │
│ 📂 Human Resources (1 intent)                               │
│   ○ POLICY_LOOKUP - HR Policy Questions         [Edit][Del] │
│                                                               │
│ [View All Categories] [Manage Permissions]                   │
└─────────────────────────────────────────────────────────────┘

// Intent Builder Wizard
┌─────────────────────────────────────────────────────────────┐
│ Create New Intent - Step 1 of 5                            │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ Basic Information                                             │
│                                                               │
│ Intent Code:     [INCIDENT_RESPONSE________]                │
│ Display Name:    [Incident Response & Remediation]          │
│ Category:        [Security Operations        ▼]             │
│ Description:     [Guide incident response workflows...    ] │
│                                                               │
│ Icon:            [🚨 emergency              ▼]              │
│ Color:           [#f44336] 🎨                                │
│                                                               │
│                                      [Cancel] [Next >]       │
└─────────────────────────────────────────────────────────────┘

// Step 2: Model Configuration
// Step 3: System Prompt Template
// Step 4: RAG Configuration
// Step 5: Tools & Permissions
```

---

## Testing New Intents

```python
# tests/integration/test_dynamic_intents.py

def test_custom_intent_workflow():
    """Test complete flow of creating and using custom intent"""

    # 1. Create category
    category = create_intent_category("CUSTOM_DOMAIN", "Custom Category")

    # 2. Create intent
    intent = create_intent_type({
        "intent_code": "CUSTOM_INTENT",
        "category_id": category.id,
        "recommended_model": "mistral-small",
        "default_temperature": 0.5
    })

    # 3. Grant role permission
    grant_permission("test_role", intent.id)

    # 4. Create use case using intent
    use_case = create_use_case({
        "intent_code": "CUSTOM_INTENT",
        "name": "Test Use Case"
    })

    # 5. Execute use case
    response = execute_use_case(use_case.id, {"query": "test"})

    # 6. Verify intent configuration applied
    assert response.model_used == "mistral-small"
    assert response.temperature == 0.5

    # 7. Verify conversation maintains intent
    thread_id = response.thread_id
    follow_up = execute_use_case(
        use_case.id,
        {"query": "follow up"},
        thread_id=thread_id
    )
    assert follow_up.intent_code == "CUSTOM_INTENT"
```

---

## Migration from Hardcoded to Dynamic

### Before (Hardcoded)
```python
# orchestrator/intent_parser.py
class RequestType(str, Enum):
    QUERY = "QUERY"
    RULE_GENERATION = "RULE_GENERATION"
    # Can't add more without code change!
```

### After (Dynamic)
```python
# orchestrator/intent_parser.py
from ..services.intent_service import IntentService

class IntentParser:
    def __init__(self, db: Session):
        self.intent_service = IntentService(db)
        # Load intents from database

    def parse_intent(self, request: IntentRequest) -> IntentResponse:
        # Lookup intent configuration dynamically
        intent_config = self.intent_service.get_intent_by_code(
            request.request_type
        )

        if not intent_config:
            raise ValueError(f"Unknown intent: {request.request_type}")

        # Use configuration from database
        return IntentResponse(
            detected_type=request.request_type,
            confidence=1.0,
            metadata={
                "model": intent_config.recommended_model,
                "temperature": intent_config.default_temperature,
                "category": intent_config.category_id
            }
        )
```

---

## API Examples

### List Available Intents for Current User
```bash
GET /api/v1/intents?category=SECURITY
Authorization: Bearer <user-token>

Response:
{
  "items": [
    {
      "intent_code": "QUERY",
      "display_name": "General Query",
      "icon": "question_answer",
      "color": "#2196F3",
      "can_use": true,
      "can_configure": false
    },
    {
      "intent_code": "RULE_GENERATION",
      "display_name": "Detection Rule Generation",
      "icon": "policy",
      "color": "#FF5722",
      "can_use": true,
      "can_configure": false
    }
  ]
}
```

### Get Intent Configuration (for use case creation)
```bash
GET /api/v1/intents/RULE_GENERATION
Authorization: Bearer <developer-token>

Response:
{
  "intent_code": "RULE_GENERATION",
  "display_name": "Detection Rule Generation",
  "category": {
    "code": "SECURITY",
    "name": "Security Operations"
  },
  "configuration": {
    "recommended_model": "mistral-large",
    "default_temperature": 0.2,
    "default_max_tokens": 4096,
    "rag_config": {
      "top_k": 10,
      "similarity_threshold": 0.8,
      "required_tags": ["rules", "siem"]
    },
    "allowed_tools": [
      "sigma_converter",
      "kql_validator",
      "lucene_helper"
    ]
  },
  "system_prompt_template": "You are an expert in creating SIEM detection rules..."
}
```

---

## Best Practices

### 1. Intent Naming Conventions
```
✅ GOOD:
- INCIDENT_TRIAGE
- CONTRACT_REVIEW
- THREAT_HUNTING

❌ BAD:
- do_stuff
- analyze_thing
- helper_1
```

### 2. System Prompt Templates
```python
✅ GOOD:
system_prompt = """
You are a {domain} expert specializing in {specialty}.

Your responsibilities:
1. {task_1}
2. {task_2}
3. {task_3}

Output format:
{format_instructions}

Guidelines:
- {guideline_1}
- {guideline_2}
"""

❌ BAD:
system_prompt = "Help the user."
```

### 3. Temperature Settings
```python
# Precise, high-consistency tasks
temperature = 0.1 - 0.3  # Rule generation, code analysis

# Balanced creativity + accuracy
temperature = 0.4 - 0.7  # General Q&A, summarization

# Creative tasks
temperature = 0.8 - 1.0  # Brainstorming, ideation
```

### 4. Category Organization
```
Security Operations/
├── QUERY (General questions)
├── RULE_GENERATION (Detection)
├── THREAT_HUNTING (Proactive)
└── INCIDENT_RESPONSE (Reactive)

Legal Affairs/
├── CONTRACT_REVIEW
├── LEGAL_RESEARCH
└── COMPLIANCE_CHECK

NOT THIS:
Miscellaneous/
├── Everything
└── More everything
```

---

## Troubleshooting

### Intent Not Appearing in UI
```bash
# Check if intent is active
SELECT * FROM intent_types WHERE intent_code = 'YOUR_INTENT';

# Check role permissions
SELECT * FROM role_intent_permissions
WHERE role_name = 'your_role' AND intent_id = <intent-uuid>;

# Reload cache
POST /api/v1/admin/intents/reload-cache
```

### Intent Configuration Not Applied
```python
# Verify use case references correct intent
use_case = get_use_case(use_case_id)
print(f"Intent code: {use_case.intent_code}")

# Check orchestrator loading
orchestrator.intent_service.reload_cache()
```

---

## Future Enhancements

### Intent Analytics
```sql
-- Most used intents
SELECT intent_code, COUNT(*) as usage_count
FROM intent_usage_logs
GROUP BY intent_code
ORDER BY usage_count DESC;

-- Average execution time by intent
SELECT intent_code, AVG(execution_time_ms) as avg_time_ms
FROM intent_usage_logs
GROUP BY intent_code;
```

### A/B Testing Intents
```python
# Test different prompts/models for same intent
intent_variant_a = {
    "system_prompt": "Prompt A",
    "model": "mistral-small"
}

intent_variant_b = {
    "system_prompt": "Prompt B",
    "model": "mistral-large"
}

# Track which performs better
```

### Intent Recommendations
```python
# Suggest intents based on query analysis
query = "Create a Splunk rule for SSH brute force"
recommended_intent = intent_recommender.suggest(query)
# → RULE_GENERATION (95% confidence)
```

---

## References

- [ADR-015: Dynamic Intent System](../adrs/ADR-015-Dynamic-Intent-System.md)
- [Intent Service Implementation](../../src/orchestrator/app/services/intent_service.py)
- [Admin API Documentation](../../docs/api/admin-intents.md)
