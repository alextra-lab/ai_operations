# Structured Output Quick Start

**5-Minute Guide to Visualizations**

---

## Instant Test (Browser Console)

**Navigate to:** `http://localhost:4200/use-cases/execute/ANY_USE_CASE`

**Paste in Console (F12):**

```javascript
const comp = ng.getComponent(document.querySelector('app-use-case-execution'));
comp.formattedOutput = {
  template_id: 'demo',
  template_name: 'Quick Demo',
  rendered_sections: [
    // Gauge
    {
      section_id: 'score',
      title: 'Threat Score',
      component_type: 'gauge',
      data: 0.85,
      config: {
        min: 0,
        max: 1,
        format: 'percent',
        thresholds: [
          { value: 0.5, color: '#4caf50', label: 'Low' },
          { value: 0.75, color: '#ff9800', label: 'Med' },
          { value: 1.0, color: '#f44336', label: 'High' }
        ]
      },
      width: 'third'
    },
    // Table
    {
      section_id: 'iocs',
      title: 'IOCs',
      component_type: 'table',
      data: [
        { type: 'IP', value: '192.0.2.1', severity: 'high' },
        { type: 'Domain', value: 'evil.com', severity: 'critical' }
      ],
      config: {
        columns: [
          { field: 'type', header: 'Type', sortable: true },
          { field: 'value', header: 'Value', copyable: true },
          { field: 'severity', header: 'Severity', sortable: true }
        ],
        filterable: true,
        sortable: true
      },
      width: 'full'
    },
    // Chart
    {
      section_id: 'chart',
      title: 'Severity',
      component_type: 'chart',
      data: [
        { label: 'Low', value: 5 },
        { label: 'Med', value: 12 },
        { label: 'High', value: 8 }
      ],
      config: {
        chart_type: 'bar',
        colors: ['#4caf50', '#ff9800', '#f44336']
      },
      width: 'half'
    },
    // Timeline
    {
      section_id: 'timeline',
      title: 'Timeline',
      component_type: 'timeline',
      data: [
        {
          timestamp: '2025-10-31T10:00:00Z',
          description: 'Initial access',
          severity: 'medium'
        },
        {
          timestamp: '2025-10-31T10:30:00Z',
          description: 'Lateral movement',
          severity: 'high'
        }
      ],
      config: {
        time_field: 'timestamp',
        label_field: 'description',
        severity_field: 'severity'
      },
      width: 'full'
    }
  ],
  raw_output: 'Demo'
};
comp['cdr'].detectChanges();
console.log('✅ Scroll down to see visualizations!');
```

---

## Create Production Use Case

### **Minimal JSON**

```json
{
  "use_case_id": "threat-viz",
  "name": "Threat Visualizer",
  "category": "threat_analysis",
  "intent_type": "QUERY",
  "lifecycle_state": "published",
  "is_active": true,
  "config_json": {
    "template_config": {
      "output_format": "structured",
      "template_id": "threat-triage-dashboard",
      "input_fields": [{
        "name": "query",
        "type": "textarea",
        "label": "Threat Data",
        "required": true
      }]
    },
    "models": { "llm": "gpt-4" },
    "generation_params": { "temperature": 0.3 }
  }
}
```

### **Create via API**

```bash
curl -X POST http://localhost:8006/api/v1/use-cases \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d @use_case.json
```

---

## Backend Response Format

```json
{
  "response": "Text summary",
  "structured_data": {
    "confidence": 0.85,
    "iocs": [
      {
        "type": "IP",
        "value": "192.0.2.1",
        "context": "C2 Server",
        "severity": "high"
      }
    ],
    "timeline": [
      {
        "timestamp": "2025-10-31T10:00:00Z",
        "description": "Attack started",
        "severity": "high"
      }
    ]
  }
}
```

---

## Available Templates

| ID | Visualizers | Use Case |
|----|-------------|----------|
| `threat-triage-dashboard` | Gauge+Table+Timeline | Threat assessment |
| `ioc-extraction-table` | Table | IOC lists |
| `incident-summary-cards` | Gauges+Chart | Incident metrics |
| `metrics-dashboard` | Gauges+Chart | System metrics |

---

## Quick Troubleshooting

**No visualizations?**
```javascript
// Check in console:
const c = ng.getComponent(document.querySelector('app-use-case-execution'));
console.log('Result:', c.executionResult?.structured_data);
console.log('Output:', c.formattedOutput);
```

**Gauge blank?**
- Data must be `number` (not object)
- Need `thresholds` in config

**Table empty?**
- Data must be `array` of objects
- Column `field` must match data keys

**Timeline wrong order?**
- Sort by timestamp in backend

---

## Data Requirements

### **Gauge**
```json
{
  "data": 0.75,  // Must be number
  "config": {
    "min": 0,
    "max": 1,
    "thresholds": [...]  // Required
  }
}
```

### **Table**
```json
{
  "data": [
    {"field1": "value", "field2": "value"}  // Array of objects
  ],
  "config": {
    "columns": [
      {"field": "field1", "header": "Header"}  // field matches data keys
    ]
  }
}
```

### **Chart**
```json
{
  "data": [
    {"label": "Category", "value": 123}  // label + value required
  ],
  "config": {
    "chart_type": "bar"  // bar|line|pie
  }
}
```

### **Timeline**
```json
{
  "data": [
    {
      "timestamp": "2025-10-31T10:00:00Z",  // ISO format
      "description": "Event description",
      "severity": "high"
    }
  ],
  "config": {
    "time_field": "timestamp",
    "label_field": "description"
  }
}
```

---

## Full Documentation

📖 **Complete Guide:** `/docs/user-guides/STRUCTURED_OUTPUT_GUIDE.md`

Includes:
- Detailed examples for each template
- Backend implementation (Python/TypeScript)
- Validation strategies
- Best practices
- Troubleshooting

---

**Last Updated:** October 31, 2025
