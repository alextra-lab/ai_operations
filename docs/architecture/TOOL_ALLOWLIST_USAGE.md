# Tool Allowlist Configuration & Usage

**Status:** B4-F3 Complete ✅
**Date:** October 1, 2025
**Purpose:** Guide for configuring tool allowlists in Use Case Templates

---

## Overview

The Tool Allowlist feature provides a framework for controlling which tools can be invoked within specific use cases. This is configured directly in Use Case Templates via the `config_json` field and enforced by the orchestrator.

**Current Status:** 🔧 **Placeholder for Future MCP Integration**

The framework is fully implemented and validates tool configurations, but actual tool calling functionality awaits Model Context Protocol (MCP) integration.

---

## Configuration via Use Case Templates

### Basic Configuration

Tool allowlists are configured in the `config_json` field of use case records:

```sql
INSERT INTO use_cases (
    use_case_id,
    name,
    description,
    category,
    intent_type,
    is_active,
    lifecycle_state,
    config_json
) VALUES (
    'threat_intel_with_tools',
    'Threat Intelligence Analysis with Tools',
    'Advanced threat analysis with web search and threat intel lookup',
    'security',
    'QUERY',
    true,
    'published',
    '{
        "visibility": {
            "roles": ["admin", "analyst", "user"]
        },
        "models": {
            "llm": "gpt-4o",
            "embedding": "text-embedding-3-small"
        },
        "rag": {
            "enabled": true,
            "top_k": 10,
            "similarity_threshold": 0.6
        },
        "tools_allowlist": ["web_search", "threat_intel_lookup", "code_interpreter"],
        "policy": {
            "streaming_default": false,
            "pii_redaction": "anonymize"
        }
    }'::jsonb
);
```

### Configuration Options

#### 1. Allow All Tools (Default)

**Use Case:** Maximum flexibility, suitable for admin-only or development use cases

```json
{
    "tools_allowlist": []
}
```

**Behavior:**

- ✅ All tools are permitted (when MCP is implemented)
- 📝 Logs: `DEBUG: "No tool allowlist configured, all tools permitted"`

#### 2. Restrict to Specific Tools

**Use Case:** Production use cases with controlled tool access

```json
{
    "tools_allowlist": ["web_search", "threat_intel_lookup"]
}
```

**Behavior:**

- ✅ Only specified tools are permitted
- 📝 Logs:
  - `INFO: "Tool allowlist configured: ['web_search', 'threat_intel_lookup']"`
  - `WARNING: "Tool calling is not yet implemented. Configured tools (2) will be validated when MCP integration is available."`
- ❌ Other tools will be blocked (when MCP is implemented)

#### 3. No Tools Allowed

**Use Case:** Use cases that should never invoke external tools

```json
{
    "tools_allowlist": []  // Empty array = allow all by default
}
```

**Note:** To explicitly disallow all tools, this will be implemented when MCP is available. Currently, empty array allows all.

---

## Available Tool Categories

The system supports the following tool categories (ready for MCP integration):

| Category | Description | Example Tools |
|----------|-------------|---------------|
| `web_search` | Web search capabilities | DuckDuckGo, Google Search |
| `code_interpreter` | Code execution and analysis | Python interpreter, Jupyter |
| `data_analysis` | Data processing and analytics | Pandas operations, SQL queries |
| `threat_intel` | Threat intelligence lookups | VirusTotal, AlienVault OTX |
| `siem_query` | SIEM system queries | Splunk, Elasticsearch |
| `custom` | Custom tool implementations | Organization-specific tools |

---

## Use Case Examples

### Example 1: General Query with Web Search

```json
{
    "use_case_id": "general_query_with_search",
    "name": "General Query with Web Search",
    "description": "General queries with optional web search capability",
    "category": "general",
    "intent_type": "QUERY",
    "config_json": {
        "visibility": {"roles": ["user", "analyst", "admin"]},
        "models": {"llm": "gpt-4o"},
        "rag": {"enabled": true, "top_k": 10},
        "tools_allowlist": ["web_search"],
        "policy": {"streaming_default": false}
    }
}
```

**What this enables:**

- Users can invoke web search to augment RAG results
- Other tools are blocked
- Suitable for general-purpose queries requiring up-to-date information

### Example 2: Threat Analysis with Multiple Tools

```json
{
    "use_case_id": "threat_analysis_full",
    "name": "Full Threat Analysis",
    "description": "Comprehensive threat analysis with all security tools",
    "category": "security",
    "intent_type": "ANALYSIS",
    "config_json": {
        "visibility": {"roles": ["analyst", "admin"]},
        "models": {"llm": "gpt-4o"},
        "rag": {"enabled": true, "top_k": 15},
        "tools_allowlist": [
            "web_search",
            "threat_intel_lookup",
            "siem_query",
            "code_interpreter"
        ],
        "policy": {"streaming_default": true}
    }
}
```

**What this enables:**

- Analysts can use multiple tools for comprehensive analysis
- Web search for recent threat intelligence
- Threat intel lookups against external databases
- SIEM queries for internal logs
- Code analysis for malware samples

### Example 3: Restricted Summarization

```json
{
    "use_case_id": "document_summary",
    "name": "Document Summarization",
    "description": "Summarize documents without external tools",
    "category": "general",
    "intent_type": "SUMMARIZATION",
    "config_json": {
        "visibility": {"roles": ["user", "analyst", "admin"]},
        "models": {"llm": "gpt-4o"},
        "rag": {"enabled": false},
        "tools_allowlist": [],  // No tools needed for summarization
        "policy": {"streaming_default": true}
    }
}
```

**What this enables:**

- Pure LLM-based summarization
- No external tool calls
- Fast, predictable responses

---

## Integration with Orchestrator

### How It Works

1. **Config Loading:**

   ```python
   # Orchestrator loads use case config
   use_case_config = self.load_use_case_config(intent_type)
   ```

2. **Tool Validation:**

   ```python
   # Validates tool allowlist format and logs configuration
   self._validate_tool_allowlist(use_case_config)
   ```

3. **Runtime Behavior (Future MCP):**
   - When a tool call is requested, the validator checks the allowlist
   - Only permitted tools are executed
   - Blocked tools return validation error

### Validation Rules

✅ **Valid Tool Names:**

- Non-empty strings
- No whitespace-only names
- Case-sensitive matching

❌ **Invalid Tool Names:**

```json
{
    "tools_allowlist": ["web_search", "", "  "]  // ERROR: Empty and whitespace names
}
```

**Error Message:**

```
ValueError: Tool allowlist contains invalid tool name: ''
```

---

## Logging Behavior

### Empty Allowlist

```
[DEBUG] No tool allowlist configured, all tools permitted
```

### Configured Allowlist

```
[INFO] Tool allowlist configured: ['web_search', 'threat_intel_lookup']
[WARNING] Tool calling is not yet implemented. Configured tools (2) will be validated when MCP integration is available.
```

### Invalid Tool Names

```
[ERROR] Invalid tool name in allowlist: ''
ValueError: Tool allowlist contains invalid tool name: ''
```

---

## Best Practices

### 1. **Principle of Least Privilege**

Only enable the tools that are necessary for the specific use case.

```json
// ❌ BAD: Allow all tools for production use cases
{"tools_allowlist": []}

// ✅ GOOD: Restrict to specific tools needed
{"tools_allowlist": ["web_search", "threat_intel_lookup"]}
```

### 2. **Role-Based Tool Access**

Combine tool allowlists with RBAC visibility settings:

```json
{
    "visibility": {"roles": ["admin"]},  // Only admins can use this use case
    "tools_allowlist": ["code_interpreter", "siem_query"]  // Powerful tools
}
```

### 3. **Document Tool Usage**

Include tool capabilities in use case descriptions:

```json
{
    "name": "Threat Analysis",
    "description": "Analyze threats using web search and threat intel databases. Tools: web_search, threat_intel_lookup"
}
```

### 4. **Test Tool Configurations**

Validate tool allowlists during development:

```bash
# Use the verification script
python ops/testing/verify_tool_registry.py
```

---

## Future MCP Integration

When Model Context Protocol is implemented, tool allowlists will:

### 1. **Enforce Execution**

- Block unauthorized tool calls at runtime
- Return validation errors for disallowed tools
- Log all tool invocation attempts

### 2. **Support Tool Metadata**

```json
{
    "tools_allowlist": [
        {
            "name": "web_search",
            "rate_limit": 10,  // Max 10 calls per request
            "requires_auth": true,
            "parameters_schema": {...}
        }
    ]
}
```

### 3. **Tool Call Metrics**

- Track tool usage per use case
- Monitor tool performance
- Audit tool invocations

### 4. **Dynamic Tool Discovery**

- Query available tools via API
- Filter by category and capabilities
- Check tool authorization

---

## API Examples

### Query Use Cases with Tool Information

```bash
GET /api/v1/use-cases/available
Authorization: Bearer <token>

Response:
{
    "use_cases": [
        {
            "use_case_id": "threat_intel_analysis",
            "name": "Threat Intelligence Analysis",
            "description": "Analyze threats with web search",
            "category": "security",
            "intent_type": "QUERY",
            "tools_available": ["web_search", "threat_intel_lookup"],
            "icon": "shield",
            "tags": ["security", "threat-intel", "tools"]
        }
    ]
}
```

### Process Request with Tool-Enabled Use Case

```bash
POST /api/v1/process
Authorization: Bearer <token>
Content-Type: application/json

{
    "query": "What are the latest ransomware trends?",
    "request_type": "QUERY",
    "use_case_id": "threat_intel_analysis"
}

Response:
{
    "request_id": "req_123",
    "response_text": "Based on recent threat intelligence...",
    "sources": [...],
    "metrics": {
        "tools_invoked": ["web_search"],  // Future MCP
        "tool_call_count": 2,             // Future MCP
        "confidence_score": 0.89
    }
}
```

---

## Troubleshooting

### Issue: Tool allowlist not being enforced

**Symptom:** All tools seem to work regardless of configuration

**Explanation:** ✅ This is expected! Tool calling is not yet implemented. The allowlist validates configuration format but doesn't enforce execution restrictions until MCP integration.

**Solution:** No action needed. The framework is ready for future MCP integration.

---

### Issue: Invalid tool name error

**Symptom:** `ValueError: Tool allowlist contains invalid tool name`

**Cause:** Empty string or whitespace-only tool name in allowlist

**Solution:**

```json
// ❌ BAD
{"tools_allowlist": ["web_search", "", "  "]}

// ✅ GOOD
{"tools_allowlist": ["web_search", "threat_intel_lookup"]}
```

---

### Issue: Tool allowlist not showing in API response

**Symptom:** Use case endpoint doesn't include tool information

**Solution:** This is a future enhancement. Currently, tool information is stored in `config_json` but not exposed via the use case menu endpoint. Will be added in a future update.

---

## Database Queries

### Find Use Cases with Specific Tools

```sql
-- Find use cases that allow web_search
SELECT
    use_case_id,
    name,
    config_json->'tools_allowlist' as tools
FROM use_cases
WHERE config_json->'tools_allowlist' @> '["web_search"]'::jsonb
  AND is_active = true;
```

### Audit Tool Allowlist Configurations

```sql
-- Get all tool configurations
SELECT
    use_case_id,
    name,
    intent_type,
    COALESCE(
        jsonb_array_length(config_json->'tools_allowlist'),
        0
    ) as tool_count,
    config_json->'tools_allowlist' as allowed_tools
FROM use_cases
WHERE is_active = true
ORDER BY tool_count DESC;
```

### Update Tool Allowlist

```sql
-- Add a tool to an existing use case
UPDATE use_cases
SET config_json = jsonb_set(
    config_json,
    '{tools_allowlist}',
    (config_json->'tools_allowlist')::jsonb || '["code_interpreter"]'::jsonb
)
WHERE use_case_id = 'threat_intel_analysis';
```

---

## Summary

Tool allowlists are **fully integrated** with Use Case Templates and provide:

✅ **Configuration:** Via `config_json.tools_allowlist` field
✅ **Validation:** Orchestrator validates tool names and format
✅ **Logging:** Comprehensive logging of tool configuration
✅ **Extensibility:** Ready for MCP integration
✅ **Security:** Framework for tool access control

**Next Steps for MCP Integration:**

1. Implement tool handlers for each category
2. Add runtime tool call routing
3. Enforce allowlist during tool execution
4. Add tool usage metrics and audit logging
5. Expose tool information via API endpoints

---

**Document Maintained By:** AI Assistant
**Last Updated:** October 1, 2025
**Related:** Use Case Configuration Schema, MCP Integration Roadmap
