# Structured Output & Visualizations Guide

**Complete Guide to Using Structured Output Templates and Visualizations**

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Available Templates](#available-templates)
4. [Creating a Use Case with Structured Output](#creating-a-use-case-with-structured-output)
5. [Complete Working Examples](#complete-working-examples)
6. [Backend Implementation](#backend-implementation)
7. [Testing & Validation](#testing--validation)
8. [Troubleshooting](#troubleshooting)

---

## Overview

Structured output templates allow Use Cases to return formatted data that is automatically rendered with interactive visualizations:

**Available Visualizers:**
- 🎯 **Gauge** - Metrics with threshold-based coloring
- 📋 **Table** - Sortable, filterable data tables
- 📊 **Chart** - Bar, line, and pie charts
- ⏱️ **Timeline** - Chronological event displays

**Benefits:**
- Consistent visual presentation
- Interactive data exploration
- Export functionality (CSV, JSON, Excel)
- Mobile-responsive design
- WCAG 2.1 AA accessible

---

## Quick Start

### **5-Minute Test (Browser Console)**

1. Navigate to any Use Case execution page
2. Press **F12** to open DevTools Console
3. Paste this code:

```javascript
const comp = ng.getComponent(document.querySelector('app-use-case-execution'));
comp.formattedOutput = {
  template_id: 'test',
  template_name: 'Quick Test',
  rendered_sections: [{
    section_id: 'gauge1',
    title: 'Confidence Score',
    component_type: 'gauge',
    data: 0.85,
    config: {
      min: 0,
      max: 1,
      format: 'percent',
      thresholds: [
        { value: 0.5, color: '#4caf50', label: 'Low' },
        { value: 0.75, color: '#ff9800', label: 'Medium' },
        { value: 1.0, color: '#f44336', label: 'High' }
      ]
    },
    width: 'third'
  }],
  raw_output: 'Test'
};
comp['cdr'].detectChanges();
```

4. Scroll down to see the gauge visualizer!

---

## Available Templates (Structural IDs)

Templates use **structural, domain-neutral IDs** (ADR-066). Configure the output template in the Use Case wizard **Step 3: User Experience** under the Output Contract section.

| Template ID | Layout | Best for |
|-------------|--------|----------|
| `score-table-timeline` | Score/gauge + table + timeline | Assessments with scores, tabular data, and events |
| `filterable-table` | Single filterable, sortable table | Lists (e.g. IOCs, items) with filters |
| `score-timeline` | Score + timeline | Scores plus chronological events |
| `auto-table` | Single auto-formatted table | Simple tabular output |
| `bar-chart` | Bar chart | Single series or comparisons |
| `kv-summary` | Key-value summary | Summary fields (e.g. incident ID, status) |
| `multi-table` | Multiple tables | Several distinct tables |
| `comparison-grid` | Comparison grid | Side-by-side or matrix views |

**Wizard Step 3 (User Experience):** In the Output Contract section you can (1) select a **template** from the dropdown (built-in or custom), (2) edit the **output schema** (JSON Schema) with validation and format tools, (3) choose **validation mode** (strict or best_effort), (4) use **schema presets** by domain (Security, Legal, IT Ops, General), (5) run a **schema–template compatibility** check, and (6) use **Refine Schema from Output** to infer or merge schema from a past execution. The wizard has five steps; Output Contract lives in Step 3 (with Input Fields and User Prompt Template).

### Custom output templates

Custom templates are stored in the database (migration 038) and exposed via the [Output Templates API](../api/admin/output-templates.md) (admin). The frontend merges built-in and custom templates in `TemplateRegistryService`; use cases reference any template via `config_json.output_contract.template_id`.

### Vega-Lite (API consumers)

Execution responses may include an optional `visualization_spec` (Vega-Lite JSON) when the backend can derive it from the selected template and data (ADR-068). Clients that render visualizations programmatically can use this field instead of resolving the template client-side.

---

## Creating a Use Case with Structured Output

### **Step 1: Define Use Case Configuration**

Create a JSON configuration file or API payload:

**File:** `threat_analysis_uc.json`

```json
{
  "use_case_id": "threat-analysis-structured",
  "name": "Threat Analysis with Visualizations",
  "description": "Analyze security threats with structured output including threat scores, IOCs, and timeline",
  "category": "threat_analysis",
  "intent_type": "QUERY",
  "lifecycle_state": "published",
  "is_active": true,
  "config_json": {
    "input_fields": [
      {
        "name": "threat_data",
        "type": "textarea",
        "label": "Threat Data",
        "description": "Paste threat intelligence, logs, or alerts for analysis",
        "required": true,
        "placeholder": "Example: Suspicious activity from IP 192.0.2.1...",
        "default_value": ""
      }
    ],
    "output_contract": {
      "template_id": "score-table-timeline",
      "validation_mode": "best_effort"
    },
    "models": {
      "llm": "gpt-4",
      "embedding": "text-embedding-3-small"
    },
    "generation_params": {
      "sampling_preset": "balanced",
      "temperature": 0.3,
      "max_tokens": 2000,
      "top_p": 0.9
    },
    "rag": {
      "enabled": true,
      "vector_collections": ["threat_intel", "soc_runbooks"],
      "top_k": 10,
      "similarity_threshold": 0.7,
      "reranking_enabled": true
    },
    "policy": {
      "streaming_enabled": true,
      "streaming_default": false,
      "pii_redaction": "anonymize"
    }
  },
  "metadata": {
    "prompts": {
      "system_prompt": "You are an expert cybersecurity threat analyst. Analyze the provided threat data and return structured output with confidence scores, IOCs, and timeline.",
      "developer_prompt": "Return JSON with: {confidence: number, iocs: array, timeline: array}"
    },
    "tags": ["threat-analysis", "ioc-extraction", "timeline"],
    "owner": "soc-team"
  }
}
```

### **Step 2: Create the Use Case via API**

```bash
curl -X POST http://localhost:8006/api/v1/use-cases \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d @threat_analysis_uc.json
```

**Expected Response:**
```json
{
  "use_case_id": "threat-analysis-structured",
  "status": "created",
  "message": "Use Case created successfully",
  "version": 1
}
```

### **Step 3: Verify in UI**

1. Navigate to: `http://localhost:4200/use-cases`
2. Find "Threat Analysis with Visualizations"
3. Click to execute
4. You should see the input form ready

---

## Complete Working Examples

### **Example 1: Threat Triage Dashboard**

#### **Use Case Configuration**

```json
{
  "use_case_id": "uc-threat-triage-001",
  "name": "APT Threat Triage",
  "description": "Assess APT threats with confidence scoring and IOC extraction",
  "category": "threat_analysis",
  "intent_type": "QUERY",
  "config_json": {
    "input_fields": [
      {
        "name": "threat_data",
        "type": "textarea",
        "label": "Threat Intelligence",
        "required": true,
        "placeholder": "Paste threat data, IOCs, or SIEM alerts..."
      }
    ],
    "output_contract": {
      "template_id": "score-table-timeline",
      "validation_mode": "best_effort"
    },
    "models": {
      "llm": "gpt-4"
    },
    "generation_params": {
      "temperature": 0.3,
      "max_tokens": 2500
    },
    "rag": {
      "enabled": true,
      "top_k": 15
    }
  }
}
```

#### **Backend Response Format**

Your backend LLM orchestrator should return:

```json
{
  "response": "Analysis complete. Detected APT29 indicators with high confidence...",
  "structured_data": {
    "confidence": 0.87,
    "iocs": [
      {
        "type": "IP",
        "value": "192.0.2.2",
        "context": "C2 Server communicating with internal host",
        "severity": "critical",
        "first_seen": "2025-10-31T08:15:00Z"
      },
      {
        "type": "Domain",
        "value": "malicious-apt29.com",
        "context": "Known APT29 infrastructure",
        "severity": "critical",
        "first_seen": "2025-10-31T08:20:00Z"
      },
      {
        "type": "Hash",
        "value": "8a7d5f3e9b2c1d4f6e8a0b3c5d7e9f1a",
        "context": "Dropper malware - Cobalt Strike beacon",
        "severity": "high",
        "first_seen": "2025-10-31T09:00:00Z"
      },
      {
        "type": "Email",
        "value": "phishing@example.com",
        "context": "Spear phishing sender",
        "severity": "high",
        "first_seen": "2025-10-31T07:45:00Z"
      }
    ],
    "timeline": [
      {
        "timestamp": "2025-10-31T07:45:00Z",
        "description": "Spear phishing email received by finance team",
        "severity": "medium",
        "details": "Email with malicious attachment targeting CFO"
      },
      {
        "timestamp": "2025-10-31T08:15:00Z",
        "description": "User clicked malicious link, dropper executed",
        "severity": "high",
        "details": "PowerShell execution detected, attempts to download payload"
      },
      {
        "timestamp": "2025-10-31T08:20:00Z",
        "description": "C2 communication established",
        "severity": "critical",
        "details": "Beacon callback to 192.0.2.2 on port 443"
      },
      {
        "timestamp": "2025-10-31T09:00:00Z",
        "description": "Lateral movement detected",
        "severity": "critical",
        "details": "Credential dumping and SMB connections to DC01"
      },
      {
        "timestamp": "2025-10-31T09:30:00Z",
        "description": "Data exfiltration attempt",
        "severity": "critical",
        "details": "Large outbound transfer to C2 server (2.3 GB)"
      }
    ]
  },
  "sources": [...],
  "metrics": {...},
  "request_id": "req-abc123",
  "timestamp": "2025-10-31T10:00:00Z"
}
```

#### **Frontend Rendering**

The `OutputFormattingService` will process this data and create:

```json
{
  "template_id": "score-table-timeline",
  "template_name": "Threat Triage Dashboard",
  "rendered_sections": [
    {
      "section_id": "threat-score",
      "title": "Threat Confidence",
      "component_type": "gauge",
      "data": 0.87,
      "config": {
        "min": 0,
        "max": 1,
        "format": "percent",
        "thresholds": [
          { "value": 0.3, "color": "#4caf50", "label": "Low" },
          { "value": 0.6, "color": "#ff9800", "label": "Medium" },
          { "value": 0.8, "color": "#f57c00", "label": "High" },
          { "value": 1.0, "color": "#f44336", "label": "Critical" }
        ]
      },
      "width": "third"
    },
    {
      "section_id": "ioc-table",
      "title": "Indicators of Compromise",
      "component_type": "table",
      "data": [/* iocs array from above */],
      "config": {
        "columns": [
          { "field": "type", "header": "Type", "sortable": true, "width": "100px" },
          { "field": "value", "header": "Value", "copyable": true, "width": "200px" },
          { "field": "context", "header": "Context", "width": "300px" },
          { "field": "severity", "header": "Severity", "sortable": true, "width": "100px" }
        ],
        "filterable": true,
        "sortable": true,
        "paginated": true,
        "export": ["csv", "json"]
      },
      "width": "full"
    },
    {
      "section_id": "timeline",
      "title": "Attack Timeline",
      "component_type": "timeline",
      "data": [/* timeline array from above */],
      "config": {
        "time_field": "timestamp",
        "label_field": "description",
        "severity_field": "severity",
        "details_field": "details"
      },
      "width": "full"
    }
  ],
  "raw_output": "Analysis complete. Detected APT29 indicators..."
}
```

#### **Expected UI Output**

```
┌────────────────────────────────────────────────────────────┐
│                     APT Threat Triage                      │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌──────────┐                                             │
│  │   87%    │  ◄── Gauge showing High confidence (orange) │
│  │  High    │                                             │
│  └──────────┘                                             │
│                                                            │
├────────────────────────────────────────────────────────────┤
│               Indicators of Compromise                     │
│                                                            │
│  Type   │ Value              │ Context          │ Severity│
│  ────────────────────────────────────────────────────────│
│  IP     │ 192.0.2.2        │ C2 Server...     │Critical│
│  Domain │ malicious-apt29.. │ Known APT29...   │Critical│
│  Hash   │ 8a7d5f3e9b2c1d... │ Dropper malware..│High    │
│  Email  │ phishing@apt-g... │ Spear phishing...│High    │
│                                                            │
│  [🔍 Filter] [⬇ Export CSV] [⬇ Export JSON]             │
│                                                            │
├────────────────────────────────────────────────────────────┤
│                    Attack Timeline                         │
│                                                            │
│  ● 07:45  Spear phishing email received                  │
│           Email with malicious attachment targeting CFO    │
│                                                            │
│  ● 08:15  User clicked malicious link, dropper executed  │
│           PowerShell execution detected...                 │
│                                                            │
│  ● 08:20  C2 communication established                    │
│           Beacon callback to 192.0.2.2                 │
│                                                            │
│  ● 09:00  Lateral movement detected                       │
│           Credential dumping and SMB connections          │
│                                                            │
│  ● 09:30  Data exfiltration attempt                       │
│           Large outbound transfer (2.3 GB)                │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

### **Example 2: Simple IOC Extraction**

#### **Use Case Configuration**

```json
{
  "use_case_id": "uc-ioc-extractor-001",
  "name": "IOC Extractor",
  "description": "Extract and categorize IOCs from threat reports",
  "category": "ioc_extraction",
  "intent_type": "QUERY",
  "config_json": {
    "input_fields": [
      {
        "name": "report",
        "type": "textarea",
        "label": "Threat Report",
        "required": true,
        "placeholder": "Paste threat intelligence report or security alert..."
      }
    ],
    "output_contract": {
      "template_id": "filterable-table",
      "validation_mode": "best_effort"
    },
    "models": {
      "llm": "gpt-4"
    },
    "generation_params": {
      "temperature": 0.2,
      "max_tokens": 1500
    }
  }
}
```

#### **Backend Response**

```json
{
  "response": "Extracted 8 IOCs from the report",
  "structured_data": {
    "iocs": [
      {
        "type": "IP",
        "value": "192.0.2.3",
        "confidence": "high",
        "first_seen": "2025-10-31T10:00:00Z",
        "threat_type": "Command and Control",
        "tags": ["apt", "c2"]
      },
      {
        "type": "Domain",
        "value": "evil-domain.com",
        "confidence": "high",
        "first_seen": "2025-10-31T09:30:00Z",
        "threat_type": "Malicious Domain",
        "tags": ["phishing", "malware"]
      },
      {
        "type": "URL",
        "value": "http://evil-domain.com/payload.exe",
        "confidence": "critical",
        "first_seen": "2025-10-31T09:45:00Z",
        "threat_type": "Malware Distribution",
        "tags": ["malware", "executable"]
      },
      {
        "type": "Hash (MD5)",
        "value": "5d41402abc4b2a76b9719d911017c592",
        "confidence": "high",
        "first_seen": "2025-10-31T08:00:00Z",
        "threat_type": "Malware Sample",
        "tags": ["ransomware"]
      }
    ]
  },
  "sources": [],
  "metrics": {},
  "request_id": "req-ioc-001"
}
```

---

### **Example 3: Incident Summary with Metrics**

#### **Use Case Configuration**

```json
{
  "use_case_id": "uc-incident-summary-001",
  "name": "Incident Summary Dashboard",
  "description": "Generate incident summary with impact metrics",
  "category": "incident_response",
  "intent_type": "QUERY",
  "config_json": {
    "input_fields": [
      {
        "name": "incident_id",
        "type": "text",
        "label": "Incident ID",
        "required": true
      },
      {
        "name": "incident_data",
        "type": "textarea",
        "label": "Incident Details",
        "required": true
      }
    ],
    "output_contract": {
      "template_id": "kv-summary",
      "validation_mode": "best_effort"
    },
    "models": {
      "llm": "gpt-4"
    },
    "generation_params": {
      "temperature": 0.4,
      "max_tokens": 2000
    }
  }
}
```

#### **Backend Response**

```json
{
  "response": "Incident INC-2025-1031 analysis complete",
  "structured_data": {
    "severity_score": 0.82,
    "impact_score": 0.75,
    "urgency_score": 0.90,
    "affected_systems": [
      { "system": "Web Servers", "count": 12 },
      { "system": "Database Servers", "count": 3 },
      { "system": "Application Servers", "count": 8 },
      { "system": "Workstations", "count": 45 }
    ],
    "incident_type": "Ransomware Attack",
    "status": "Contained",
    "estimated_cost": "$250,000"
  }
}
```

---

## Backend Implementation

### **Python Example (FastAPI + LangChain)**

```python
from typing import Any, Dict
from pydantic import BaseModel
import json

class StructuredOutputResponse(BaseModel):
    """Response with structured data for visualization"""
    response: str
    structured_data: Dict[str, Any]
    sources: list = []
    metrics: dict = {}
    request_id: str
    timestamp: str


async def execute_threat_analysis(query: str) -> StructuredOutputResponse:
    """
    Execute threat analysis with structured output.

    Returns data formatted for threat-triage-dashboard template.
    """

    # Define structured output schema
    output_schema = {
        "type": "object",
        "required": ["confidence", "iocs", "timeline"],
        "properties": {
            "confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
                "description": "Threat confidence score (0-1)"
            },
            "iocs": {
                "type": "array",
                "description": "List of indicators of compromise",
                "items": {
                    "type": "object",
                    "required": ["type", "value", "context", "severity"],
                    "properties": {
                        "type": {"type": "string", "enum": ["IP", "Domain", "Hash", "Email", "URL"]},
                        "value": {"type": "string"},
                        "context": {"type": "string"},
                        "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]}
                    }
                }
            },
            "timeline": {
                "type": "array",
                "description": "Chronological timeline of attack events",
                "items": {
                    "type": "object",
                    "required": ["timestamp", "description", "severity"],
                    "properties": {
                        "timestamp": {"type": "string", "format": "date-time"},
                        "description": {"type": "string"},
                        "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                        "details": {"type": "string"}
                    }
                }
            }
        }
    }

    # Create LLM prompt with structured output instructions
    system_prompt = """You are a cybersecurity threat analyst.
    Analyze the provided threat data and return structured JSON output.

    Required format:
    {
      "confidence": <float 0-1>,
      "iocs": [{"type": "IP|Domain|Hash|Email|URL", "value": "...", "context": "...", "severity": "low|medium|high|critical"}],
      "timeline": [{"timestamp": "ISO8601", "description": "...", "severity": "low|medium|high|critical", "details": "..."}]
    }

    Extract all IOCs, assess confidence, and create timeline of attack progression.
    """

    # Execute LLM call (pseudo-code)
    llm_response = await call_llm_with_structured_output(
        query=query,
        system_prompt=system_prompt,
        output_schema=output_schema,
        temperature=0.3
    )

    # Parse structured data
    structured_data = json.loads(llm_response.structured_output)

    # Sort timeline chronologically
    structured_data["timeline"].sort(key=lambda x: x["timestamp"])

    return StructuredOutputResponse(
        response=llm_response.text_summary,
        structured_data=structured_data,
        sources=llm_response.sources,
        metrics=llm_response.metrics,
        request_id=llm_response.request_id,
        timestamp=datetime.utcnow().isoformat()
    )
```

### **TypeScript Example (Node.js + OpenAI)**

```typescript
import OpenAI from 'openai';

interface StructuredOutput {
  confidence: number;
  iocs: Array<{
    type: 'IP' | 'Domain' | 'Hash' | 'Email' | 'URL';
    value: string;
    context: string;
    severity: 'low' | 'medium' | 'high' | 'critical';
  }>;
  timeline: Array<{
    timestamp: string;
    description: string;
    severity: 'low' | 'medium' | 'high' | 'critical';
    details?: string;
  }>;
}

async function executeThreatAnalysis(query: string): Promise<any> {
  const openai = new OpenAI();

  const response = await openai.chat.completions.create({
    model: 'gpt-4',
    messages: [
      {
        role: 'system',
        content: `You are a cybersecurity threat analyst.
        Analyze threat data and return structured JSON with:
        - confidence: threat confidence score (0-1)
        - iocs: array of IOCs with type, value, context, severity
        - timeline: chronological attack events with timestamp, description, severity`
      },
      {
        role: 'user',
        content: query
      }
    ],
    response_format: { type: 'json_object' },
    temperature: 0.3
  });

  const structuredData: StructuredOutput = JSON.parse(
    response.choices[0].message.content || '{}'
  );

  // Sort timeline
  structuredData.timeline.sort((a, b) =>
    new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );

  return {
    response: `Threat analysis complete. Confidence: ${(structuredData.confidence * 100).toFixed(0)}%`,
    structured_data: structuredData,
    sources: [],
    metrics: {
      model: 'gpt-4',
      tokens_in: response.usage?.prompt_tokens,
      tokens_out: response.usage?.completion_tokens
    },
    request_id: response.id,
    timestamp: new Date().toISOString()
  };
}
```

---

## Testing & Validation

### **Test Checklist**

#### **1. Use Case Configuration**
- [ ] `output_format` is set to `"structured"`
- [ ] `template_id` matches an available template
- [ ] Input fields are properly defined
- [ ] LLM model is configured

#### **2. Backend Response**
- [ ] Returns `structured_data` field
- [ ] Data matches template schema
- [ ] All required fields present
- [ ] Data types are correct (numbers, strings, arrays)

#### **3. Frontend Rendering**
- [ ] Navigate to Use Case execution page
- [ ] Enter test query
- [ ] Execute Use Case
- [ ] Scroll to "Structured Output" section
- [ ] Verify visualizations render
- [ ] Test interactivity (sort, filter, export)

#### **4. Data Validation**
- [ ] Gauge: value is numeric (0-1 or 0-100)
- [ ] Table: data is array of objects
- [ ] Chart: data has label and value fields
- [ ] Timeline: events have timestamp field
- [ ] All fields match config expectations

### **Manual Testing Script**

```bash
#!/bin/bash
# test_structured_output.sh

API_URL="http://localhost:8006/api/v1"
TOKEN="your_access_token"

# Create test Use Case
curl -X POST "$API_URL/use-cases" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "use_case_id": "test-threat-triage",
    "name": "Test Threat Triage",
    "category": "threat_analysis",
    "intent_type": "QUERY",
    "lifecycle_state": "published",
    "is_active": true,
    "config_json": {
      "input_fields": [{
        "name": "query",
        "type": "textarea",
        "label": "Query",
        "required": true
      }],
      "output_contract": {
        "template_id": "score-table-timeline",
        "validation_mode": "best_effort"
      },
      "models": {"llm": "gpt-4"},
      "generation_params": {"temperature": 0.3}
    }
  }'

# Execute Use Case with test data
curl -X POST "$API_URL/use-cases/test-threat-triage/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "input_values": {
      "query": "Analyze this threat: IP 192.0.2.1 showing suspicious C2 traffic"
    }
  }' | jq .

echo "✅ Test Use Case created and executed"
echo "📊 Check UI at: http://localhost:4200/use-cases/execute/test-threat-triage"
```

### **Validation Errors**

| Error | Cause | Solution |
|-------|-------|----------|
| "No structured output" | Backend didn't return `structured_data` | Add `structured_data` field to response |
| "Invalid template" | `template_id` not found | Use valid template ID from registry |
| Gauge is blank | Data is not numeric | Ensure gauge data is `number` type |
| Table is empty | Data is not array | Ensure table data is `array` of objects |
| Chart not rendering | Data missing labels | Include `label` and `value` in data |
| Timeline out of order | Events not sorted | Sort by `timestamp` field |

---

## Troubleshooting

### **Problem: Visualizations don't appear**

**Check 1: Verify structured data is present**
```javascript
// Browser console
const comp = ng.getComponent(document.querySelector('app-use-case-execution'));
console.log('Execution Result:', comp.executionResult);
console.log('Has structured_data:', !!comp.executionResult?.structured_data);
```

**Check 2: Verify template ID**
```javascript
console.log('Template ID:', comp.useCaseConfig?.output_contract?.template_id);
```

**Check 3: Check formatted output**
```javascript
console.log('Formatted Output:', comp.formattedOutput);
console.log('Sections:', comp.formattedOutput?.rendered_sections);
```

**Solution:** Ensure backend returns proper `structured_data` field

---

### **Problem: Gauge shows error**

**Cause:** Data format mismatch

**Check:**
```javascript
const section = comp.formattedOutput?.rendered_sections.find(s => s.component_type === 'gauge');
console.log('Gauge data:', section?.data);
console.log('Gauge config:', section?.config);
```

**Requirements:**
- Data must be a `number` (not object or string)
- Config must have `thresholds` array
- Config must have `min` and `max` values

**Solution:**
```json
{
  "data": 0.75,  // ✅ Number
  "config": {
    "min": 0,
    "max": 1,
    "thresholds": [
      { "value": 0.5, "color": "#4caf50", "label": "Low" },
      { "value": 1.0, "color": "#f44336", "label": "High" }
    ]
  }
}
```

---

### **Problem: Table is empty**

**Cause:** Data is not an array or columns don't match

**Check:**
```javascript
const section = comp.formattedOutput?.rendered_sections.find(s => s.component_type === 'table');
console.log('Table data:', section?.data);
console.log('Is array:', Array.isArray(section?.data));
console.log('Columns:', section?.config?.columns);
```

**Requirements:**
- Data must be array of objects
- Column `field` names must match data object keys

**Solution:**
```json
{
  "data": [
    {"type": "IP", "value": "192.0.2.1", "severity": "high"}
  ],
  "config": {
    "columns": [
      { "field": "type", "header": "Type" },
      { "field": "value", "header": "Value" },
      { "field": "severity", "header": "Severity" }
    ]
  }
}
```

---

### **Problem: Timeline events out of order**

**Cause:** Backend not sorting by timestamp

**Solution:** Sort events chronologically in backend:

```python
# Python
structured_data["timeline"].sort(key=lambda x: x["timestamp"])
```

```typescript
// TypeScript
structuredData.timeline.sort((a, b) =>
  new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
);
```

---

## Best Practices

### **1. Data Validation**

Always validate structured output against schema:

```python
from jsonschema import validate, ValidationError

def validate_threat_triage_output(data: dict) -> bool:
    schema = {
        "type": "object",
        "required": ["confidence", "iocs", "timeline"],
        "properties": {
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "iocs": {"type": "array"},
            "timeline": {"type": "array"}
        }
    }

    try:
        validate(instance=data, schema=schema)
        return True
    except ValidationError as e:
        logger.error(f"Invalid structured output: {e.message}")
        return False
```

### **2. Graceful Degradation**

If structured output fails, fall back to text:

```python
try:
    structured_data = extract_structured_data(llm_response)
    validate_threat_triage_output(structured_data)
except Exception as e:
    logger.warning(f"Structured output failed: {e}")
    structured_data = None  # Frontend will show text-only response
```

### **3. Performance**

- Keep structured data payloads under 100KB
- Limit table rows to 100 items (use pagination)
- Lazy-load timeline events if >50 items
- Cache template configurations

### **4. Security**

- Sanitize all user-provided data
- Validate IOC formats (IPs, domains, hashes)
- Redact sensitive information in structured output
- Apply RLS (Row-Level Security) to Use Case execution

---

## Additional Resources

- **ADR-018:** Use Case Owned Architecture
- **ADR-045:** Query Developer Tools Architecture
- **P3-F5:** Output Formatting Engine Specification
- **API Documentation:** `/docs/api/use-case-management.md`
- **Frontend Models:** `/src/frontend-angular/src/app/models/output-format.model.ts`
- **Backend Schemas:** `/src/orchestrator/app/schemas/use_case_config.py`

---

## Support

For issues or questions:
1. Check browser console for errors
2. Verify backend response format
3. Review this guide's troubleshooting section
4. Contact SOC Platform team

---

**Last Updated:** October 31, 2025
**Version:** 1.0
**Status:** Production Ready
