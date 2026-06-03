# Use Case Management API Reference

**Version:** 1.0
**Base URL:** `/api/v1/admin/use-cases`
**Authentication:** Required (Admin or Corpus Admin role)
**Date:** October 18, 2025
**Status:** Implemented

---

## Overview

The Use Case Management API provides comprehensive CRUD operations, lifecycle state management, version control, and cloning capabilities for Use Cases. This API implements the [ADR-018: Use Case Owned Architecture](../development/adrs/ADR-018-Use-Case-Owned-Architecture.md) where Use Cases are sovereign entities that own all configuration (prompts, models, RAG, tools, policies).

**Key Features:**

- Complete CRUD operations with filtering and pagination
- Lifecycle state management (draft → review → published → archived)
- Version control with snapshot-based history
- Rollback to previous versions
- Clone use case with automatic versioning
- Admin and Corpus Admin role enforcement

**Related APIs:**

- **Use Case Execution:** `/api/v1/use-cases` (public endpoint for executing use cases)
- **Template Management:** `/api/v1/templates` (legacy, backward compatibility)

---

## Authentication

All endpoints require admin or corpus_admin authentication. Include JWT token in Authorization header:

```bash
Authorization: Bearer <access_token>
```

**Get Admin Token:**

```bash
TOKEN=$(curl -s -X POST "http://localhost:8006/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin" \
  -d "password=adminpassword" | jq -r '.access_token')
```

---

## Endpoints

### 1. List Use Cases

**GET** `/api/v1/admin/use-cases`

List all use cases with optional filtering and pagination. Management endpoint returns more details than the public `/available` endpoint.

**Query Parameters:**

- `page` (integer, default: 1, min: 1) - Page number
- `page_size` (integer, default: 50, min: 1, max: 100) - Items per page
- `use_case_id_filter` (string, optional) - Filter by use_case_id (partial match)
- `category` (string, optional) - Filter by category
- `lifecycle_state` (string, optional) - Filter by state (draft, review, published, archived)
- `active_only` (boolean, default: false) - Return only active use cases

**Example Request:**

```bash
curl -X GET "http://localhost:8006/api/v1/admin/use-cases?page=1&page_size=20&lifecycle_state=published&active_only=true" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**

```json
{
  "use_cases": [
    {
      "id": "ba0c6e49-2813-4887-8970-e0c1753234f7",
      "use_case_id": "threat_intelligence_query",
      "name": "Threat Intelligence Query",
      "description": "Query threat intelligence databases for IOCs",
      "category": "threat_intel",
      "intent_type": "rag_qa",
      "version": 1,
      "lifecycle_state": "published",
      "is_active": true,
      "config_json": {
        "models": {
          "llm": "mistral-large",
          "embedding": "all-minilm-l6-v2"
        },
        "rag": {
          "enabled": true,
          "vector_collections": ["threat_intel"],
          "top_k": 10,
          "similarity_threshold": 0.7
        }
      },
      "metadata_json": {
        "created_from_pattern": "rag-citations",
        "version_history": []
      },
      "prompts": {
        "system_prompt": "You are a threat intelligence analyst...",
        "developer_prompt": "Cite sources using (doc:id, page:N)...",
        "fewshots": []
      },
      "created_at": "2025-10-15T10:30:00Z",
      "updated_at": "2025-10-15T10:30:00Z",
      "created_by": "550e8400-e29b-41d4-a716-446655440000",
      "updated_by": "550e8400-e29b-41d4-a716-446655440000"
    }
  ],
  "total": 15,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

---

### 2. Create Use Case

**POST** `/api/v1/admin/use-cases`

Create a new use case with prompts and configuration.

**Request Body:**

```json
{
  "use_case_id": "malware_analysis",
  "name": "Malware Analysis Assistant",
  "description": "Analyze malware samples and provide threat assessment",
  "category": "malware",
  "intent_type": "rag_qa",
  "lifecycle_state": "draft",
  "is_active": false,
  "config_json": {
    "input_fields": [
      {
        "name": "sample_hash",
        "type": "text",
        "label": "Malware Hash",
        "description": "Enter the file hash (MD5, SHA1, or SHA256)",
        "required": true,
        "placeholder": "e.g., a3f5c8d9e2b7f1a6...",
        "default_value": ""
      },
      {
        "name": "sample_type",
        "type": "select",
        "label": "Sample Type",
        "description": "Type of malware sample",
        "required": true,
        "options": [
          {"value": "ransomware", "label": "Ransomware"},
          {"value": "trojan", "label": "Trojan"},
          {"value": "worm", "label": "Worm"},
          {"value": "unknown", "label": "Unknown"}
        ],
        "default_value": "unknown"
      },
      {
        "name": "additional_context",
        "type": "textarea",
        "label": "Additional Context",
        "description": "Any additional information about the sample",
        "required": false,
        "placeholder": "Optional: source, observed behavior, etc.",
        "default_value": ""
      }
    ],
    "models": {
      "llm": "mistral-large",
      "embedding": "all-minilm-l6-v2"
    },
    "rag": {
      "enabled": true,
      "vector_collections": ["malware_reports"],
      "top_k": 15,
      "similarity_threshold": 0.75
    },
    "generation": {
      "temperature": 0.3,
      "max_tokens": 2048
    },
    "policies": {
      "streaming_enabled": true,
      "pii_redaction": true
    }
  },
  "metadata_json": {
    "created_from_pattern": "rag-citations",
    "tags": ["malware", "analysis", "threat_intel"]
  },
  "prompts": {
    "system_prompt": "You are an expert malware analyst with deep knowledge of threat indicators and attack patterns.",
    "developer_prompt": "Always cite specific malware reports using (doc:{doc_id}, page:{page}) format. Provide confidence levels for all assessments.",
    "fewshots": [
      {
        "user": "What are the key indicators for ransomware?",
        "assistant": "Based on malware reports (doc:malware_123, page:5), key indicators include..."
      }
    ]
  }
}
```

**Response:**

```json
{
  "id": "c7d3e2a1-9876-4321-b123-456789abcdef",
  "use_case_id": "malware_analysis",
  "name": "Malware Analysis Assistant",
  "description": "Analyze malware samples and provide threat assessment",
  "category": "malware",
  "intent_type": "rag_qa",
  "version": 1,
  "lifecycle_state": "draft",
  "is_active": false,
  "config_json": { ... },
  "metadata_json": {
    "created_from_pattern": "rag-citations",
    "tags": ["malware", "analysis", "threat_intel"],
    "version_history": []
  },
  "prompts": { ... },
  "created_at": "2025-10-18T14:20:00Z",
  "updated_at": "2025-10-18T14:20:00Z",
  "created_by": "550e8400-e29b-41d4-a716-446655440000",
  "updated_by": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Status Codes:**

- `201 Created` - Use case created successfully
- `400 Bad Request` - Invalid request data
- `409 Conflict` - Use case ID already exists
- `403 Forbidden` - Insufficient permissions
- `500 Internal Server Error` - Server error

---

### 3. Get Use Case Details

**GET** `/api/v1/admin/use-cases/{use_case_id}`

Retrieve detailed information for a specific use case, including prompts and configuration.

**Path Parameters:**

- `use_case_id` (UUID) - Use case internal UUID (not use_case_id string)

**Example Request:**

```bash
curl -X GET "http://localhost:8006/api/v1/admin/use-cases/c7d3e2a1-9876-4321-b123-456789abcdef" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:** Same structure as Create Use Case response

**Status Codes:**

- `200 OK` - Use case retrieved successfully
- `404 Not Found` - Use case not found
- `403 Forbidden` - Insufficient permissions

---

### 4. Update Use Case

**PUT** `/api/v1/admin/use-cases/{use_case_id}`

Update use case details, configuration, or prompts. Creates a new version snapshot in metadata.

**Path Parameters:**

- `use_case_id` (UUID) - Use case internal UUID

**Request Body (all fields optional):**

```json
{
  "name": "Updated Use Case Name",
  "description": "Updated description",
  "category": "updated_category",
  "intent_type": "rag_qa",
  "lifecycle_state": "review",
  "is_active": true,
  "config_json": { ... },
  "metadata_json": { ... },
  "prompts": {
    "system_prompt": "Updated system prompt...",
    "developer_prompt": "Updated developer prompt...",
    "fewshots": [ ... ]
  }
}
```

**Response:** Updated UseCaseResponse with incremented version number

**Status Codes:**

- `200 OK` - Use case updated successfully
- `400 Bad Request` - Invalid update data
- `404 Not Found` - Use case not found
- `403 Forbidden` - Insufficient permissions

**Notes:**

- Each update creates a version snapshot in `metadata_json.version_history`
- Version number is automatically incremented
- `updated_at` and `updated_by` are automatically set

---

### 5. Delete Use Case

**DELETE** `/api/v1/admin/use-cases/{use_case_id}`

Delete a use case. Only use cases in `draft` state can be deleted.

**Path Parameters:**

- `use_case_id` (UUID) - Use case internal UUID

**Example Request:**

```bash
curl -X DELETE "http://localhost:8006/api/v1/admin/use-cases/c7d3e2a1-9876-4321-b123-456789abcdef" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**

```json
{
  "message": "Use case deleted successfully"
}
```

**Status Codes:**

- `200 OK` - Use case deleted successfully
- `400 Bad Request` - Cannot delete (not in draft state)
- `404 Not Found` - Use case not found
- `403 Forbidden` - Insufficient permissions

**Business Rules:**

- Only `draft` state use cases can be deleted
- Published/archived use cases should be transitioned to `archived` instead
- Deletion cascades to associated prompts and assignments

---

### 6. Clone Use Case

**POST** `/api/v1/admin/use-cases/{use_case_id}/clone`

Create a copy of an existing use case with a new use_case_id. The cloned use case starts in `draft` state with version 1.

**Path Parameters:**

- `use_case_id` (UUID) - Source use case internal UUID

**Request Body:**

```json
{
  "new_use_case_id": "malware_analysis_v2",
  "new_name": "Malware Analysis V2",
  "new_description": "Enhanced malware analysis with updated model"
}
```

**Response:** UseCaseResponse for the newly created use case

**Status Codes:**

- `201 Created` - Use case cloned successfully
- `400 Bad Request` - Invalid clone request
- `404 Not Found` - Source use case not found
- `409 Conflict` - New use_case_id already exists
- `403 Forbidden` - Insufficient permissions

**What Gets Cloned:**

- ✅ Complete `config_json` configuration
- ✅ All prompts (system, developer, fewshots)
- ✅ Category and intent_type
- ❌ Version history (starts fresh)
- ❌ Lifecycle state (starts as `draft`)
- ❌ User assignments (starts empty)

**Metadata:**

- `metadata_json.cloned_from` set to source use case ID
- `version` set to 1
- `created_at` set to current timestamp

---

### 7. Transition Lifecycle State

**POST** `/api/v1/admin/use-cases/{use_case_id}/transition`

Transition use case through lifecycle states following the state machine.

**Path Parameters:**

- `use_case_id` (UUID) - Use case internal UUID

**Request Body:**

```json
{
  "to_state": "published"
}
```

**Lifecycle State Machine:**

```
draft → review → published → archived
         ↓
       draft (if rejected)
```

**Valid Transitions:**

- `draft` → `review` (submit for review)
- `review` → `published` (approve)
- `review` → `draft` (reject)
- `published` → `archived` (archive)
- Any state → `draft` (demote/revert)

**Response:**

```json
{
  "id": "c7d3e2a1-9876-4321-b123-456789abcdef",
  "lifecycle_state": "published",
  "message": "State transition successful",
  "previous_state": "review",
  "transitioned_at": "2025-10-18T14:30:00Z"
}
```

**Status Codes:**

- `200 OK` - Transition successful
- `400 Bad Request` - Invalid state transition
- `404 Not Found` - Use case not found
- `403 Forbidden` - Insufficient permissions

**Business Rules:**

- Transitioning to `published` may require approval workflow (future)
- Only active versions can be transitioned
- State change is logged in version history

---

### 8. Get Version History

**GET** `/api/v1/admin/use-cases/{use_case_id}/versions`

Retrieve version history for a use case. Shows snapshots of configuration and prompts at each version.

**Path Parameters:**

- `use_case_id` (UUID) - Use case internal UUID

**Example Request:**

```bash
curl -X GET "http://localhost:8006/api/v1/admin/use-cases/c7d3e2a1-9876-4321-b123-456789abcdef/versions" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**

```json
{
  "use_case_id": "c7d3e2a1-9876-4321-b123-456789abcdef",
  "current_version": 3,
  "versions": [
    {
      "version": 3,
      "config_snapshot": {
        "models": { "llm": "mistral-large", "embedding": "all-minilm-l6-v2" },
        "rag": { "enabled": true, "top_k": 15 }
      },
      "prompts_snapshot": {
        "system_prompt": "Latest system prompt...",
        "developer_prompt": "Latest developer prompt...",
        "fewshots": []
      },
      "updated_at": "2025-10-18T14:00:00Z",
      "updated_by": "550e8400-e29b-41d4-a716-446655440000",
      "changes": "Increased RAG top_k from 10 to 15"
    },
    {
      "version": 2,
      "config_snapshot": { ... },
      "prompts_snapshot": { ... },
      "updated_at": "2025-10-17T12:00:00Z",
      "updated_by": "550e8400-e29b-41d4-a716-446655440000",
      "changes": "Updated developer prompt with citation format"
    },
    {
      "version": 1,
      "config_snapshot": { ... },
      "prompts_snapshot": { ... },
      "updated_at": "2025-10-15T10:30:00Z",
      "updated_by": "550e8400-e29b-41d4-a716-446655440000",
      "changes": "Initial version"
    }
  ]
}
```

**Status Codes:**

- `200 OK` - Version history retrieved
- `404 Not Found` - Use case not found
- `403 Forbidden` - Insufficient permissions

---

### 9. Rollback to Previous Version

**POST** `/api/v1/admin/use-cases/{use_case_id}/rollback`

Rollback use case to a previous version. Loads the config and prompts snapshot, creates a new version.

**Path Parameters:**

- `use_case_id` (UUID) - Use case internal UUID

**Request Body:**

```json
{
  "to_version": 2
}
```

**Response:**

```json
{
  "id": "c7d3e2a1-9876-4321-b123-456789abcdef",
  "version": 4,
  "message": "Successfully rolled back to version 2",
  "previous_version": 3,
  "restored_version": 2,
  "rolled_back_at": "2025-10-18T14:45:00Z"
}
```

**Status Codes:**

- `200 OK` - Rollback successful
- `400 Bad Request` - Invalid version number
- `404 Not Found` - Use case or version not found
- `403 Forbidden` - Insufficient permissions

**Business Rules:**

- Creates new version (doesn't actually overwrite current version)
- Loads config_snapshot and prompts_snapshot from target version
- Increments version number
- Adds rollback note to version_history

---

## Data Models

### UseCaseResponse

Complete use case details including prompts and configuration.

```typescript
interface UseCaseResponse {
  id: string;                    // UUID
  use_case_id: string;           // Unique identifier (e.g., "threat_intel_query")
  name: string;                  // Display name
  description: string | null;    // Description
  category: string;              // Category (threat_intel, malware, etc.)
  intent_type: string;           // Intent classification (rag_qa, semantic_search, etc.)
  version: number;               // Current version number
  lifecycle_state: string;       // draft, review, published, archived
  is_active: boolean;            // Active flag
  config_json: UseCaseConfig;    // Complete configuration
  metadata_json: object;         // Metadata including version_history
  prompts: UseCasePrompts;       // System, developer, fewshot prompts
  created_at: string;            // ISO 8601 timestamp
  updated_at: string;            // ISO 8601 timestamp
  created_by: string | null;     // Creator UUID
  updated_by: string | null;     // Last updater UUID
}
```

### UseCaseConfig

Configuration object structure (stored in `config_json` field):

```typescript
interface UseCaseConfig {
  // --- Authoring (wizard Step 3: User Experience) ---
  input_fields?: InputField[];   // Dynamic form fields at execution (ADR-062/064)
  user_prompt_template?: {       // Optional: {{variable}} template; if absent, legacy concat
    template: string;            // e.g. "Analyze incident {{incident_id}} with severity {{severity}}"
    fallback_mode?: "concat";    // If template invalid, fall back to key: value concat
  };
  output_contract?: {            // Output format and visualization (Phase 4/4bis)
    template_id?: string;        // Built-in (e.g. score-table-timeline, auto-table) or custom ID
    output_schema?: object;      // JSON Schema for structured output validation
    validation_mode?: "strict" | "best_effort";
  };
  // --- Engine (wizard Step 4) ---
  models: {
    llm: string;                 // LLM model ID (e.g., "mistral-large")
    embedding: string;           // Embedding model ID (e.g., "all-minilm-l6-v2")
  };
  rag: {
    enabled: boolean;            // Enable RAG for this use case
    vector_collections: string[];// Collection names to search
    top_k: number;               // Number of chunks to retrieve
    similarity_threshold: number;// Minimum similarity score (0.0-1.0)
  };
  generation?: {
    temperature?: number;        // LLM temperature (0.0-2.0)
    max_tokens?: number;         // Maximum output tokens
    top_p?: number;              // Nucleus sampling parameter
  };
  tools?: {
    allowlist: string[];         // Allowed tool IDs (future)
  };
  policies?: {
    streaming_enabled?: boolean; // Enable SSE streaming
    pii_redaction?: boolean;     // Enable PII redaction
    history_persistence?: boolean; // Save to query history
  };
}

interface InputField {
  name: string;                  // Identifier (used in user_prompt_template)
  type: "text" | "textarea" | "select" | "number" | "checkbox" | "date";
  label: string;
  description?: string;
  required: boolean;
  placeholder?: string;
  default_value?: string | number | boolean;
  options?: { value: string; label: string }[];  // For select
  validation?: { min_length?, max_length?, min_value?, max_value?, pattern?, pattern_message? };
}
```

**Built-in output template IDs** (structural names per ADR-066): `score-table-timeline`, `filterable-table`, `score-timeline`, `auto-table`, `bar-chart`, `kv-summary`, `multi-table`, `comparison-grid`. Custom templates are stored via the [Output Templates API](admin/output-templates.md).

### UseCasePrompts

Prompt structure with multi-role support:

```typescript
interface UseCasePrompts {
  system_prompt: string;         // System-level instructions
  developer_prompt: string | null; // Developer-level instructions (hidden from user)
  fewshots: FewShotExample[];    // Few-shot examples
}

interface FewShotExample {
  user: string;                  // Example user query
  assistant: string;             // Example assistant response
}
```

### Lifecycle States

```typescript
type LifecycleState =
  | "draft"       // Under development, not visible to users
  | "review"      // Submitted for review, pending approval
  | "published"   // Approved and active, visible to users
  | "archived";   // Deprecated, no longer available
```

---

## Use Case Architecture

### Use Case as Top Entity

According to [ADR-018](../development/adrs/ADR-018-Use-Case-Owned-Architecture.md), Use Cases are **sovereign entities** that own:

- ✅ **Prompts** - System, developer, and fewshot prompts
- ✅ **Model Configuration** - LLM and embedding model selection
- ✅ **RAG Configuration** - Collection selection, top_k, thresholds
- ✅ **Generation Parameters** - Temperature, max_tokens, top_p
- ✅ **Tools Allowlist** - Which tools can be used (future)
- ✅ **Output Contracts** - Expected output format (future)
- ✅ **Policies** - Streaming, PII redaction, history persistence

### Integration with Other Systems

**Collections** ([ADR-021](../development/adrs/ADR-021-Collection-Based-Document-Management.md)):

- Use Cases reference collections in `config_json.rag.vector_collections`
- All referenced collections must use the same embedding model
- Use Case's `config_json.models.embedding` must match collection embedding model

**Execution:**

- Public endpoint: `POST /api/v1/use-cases/{use_case_id}/execute`
- Requires `is_active = true` and `lifecycle_state = published`
- See Use Case Execution API for execution details

**RBAC:**

- Use case visibility controlled via `user_use_case_assignments` table
- Only assigned users can execute use cases
- Lifecycle state affects visibility (only published are available)

---

## Example Workflows

### Create and Publish Use Case

```bash
# 1. Create in draft state
USE_CASE=$(curl -s -X POST "http://localhost:8006/api/v1/admin/use-cases" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "use_case_id": "new_use_case",
    "name": "New Use Case",
    "category": "general",
    "intent_type": "rag_qa",
    "lifecycle_state": "draft",
    "config_json": {...},
    "prompts": {...}
  }' | jq -r '.id')

# 2. Test the use case (manually verify it works)

# 3. Submit for review
curl -X POST "http://localhost:8006/api/v1/admin/use-cases/$USE_CASE/transition" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"to_state": "review"}'

# 4. Approve and publish
curl -X POST "http://localhost:8006/api/v1/admin/use-cases/$USE_CASE/transition" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"to_state": "published"}'

# 5. Activate for user access
curl -X PUT "http://localhost:8006/api/v1/admin/use-cases/$USE_CASE" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_active": true}'
```

### Clone and Modify Use Case

```bash
# 1. Clone existing use case
CLONED=$(curl -s -X POST "http://localhost:8006/api/v1/admin/use-cases/$SOURCE_UUID/clone" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "new_use_case_id": "threat_intel_v2",
    "new_name": "Threat Intel Query V2",
    "new_description": "Enhanced with additional sources"
  }' | jq -r '.id')

# 2. Modify configuration
curl -X PUT "http://localhost:8006/api/v1/admin/use-cases/$CLONED" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "config_json": {
      "rag": {
        "vector_collections": ["threat_intel", "cve_database"],
        "top_k": 20
      }
    }
  }'

# 3. Review and publish (repeat workflow above)
```

### Rollback After Bad Update

```bash
# 1. Get version history
curl -X GET "http://localhost:8006/api/v1/admin/use-cases/$USE_CASE/versions" \
  -H "Authorization: Bearer $TOKEN"

# 2. Identify good version (e.g., version 2)

# 3. Rollback
curl -X POST "http://localhost:8006/api/v1/admin/use-cases/$USE_CASE/rollback" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"to_version": 2}'
```

---

## Relationship to Template API

**Historical Context:**
The Template Management API (`/api/v1/templates`) was the original approach where templates were shared entities referenced by multiple use cases.

**Current Architecture:**
[ADR-018: Use Case Owned Architecture](../development/adrs/ADR-018-Use-Case-Owned-Architecture.md) simplified this to make Use Cases sovereign entities that own their prompts and configuration directly.

**Coexistence:**
Both APIs currently coexist:

- **Template API:** Maintained for backward compatibility
- **Use Case Management API:** Recommended for new development

**Migration Path:**
Existing templates can be converted to use cases using the clone functionality.

---

## Security Considerations

### Authentication & Authorization

- ✅ Admin or Corpus Admin role required for all endpoints
- ✅ JWT token validation on every request
- ✅ User attribution for all create/update operations

### Audit Logging

- ✅ All operations logged to `audit_logs` table
- ✅ Version snapshots preserve complete change history
- ✅ Created_by and updated_by tracked

### Data Validation

- ✅ Pydantic schema validation on all requests
- ✅ Use case ID uniqueness enforced
- ✅ Lifecycle state transitions validated
- ✅ Config JSON schema validation (future)

---

## Testing

### Integration Tests

**Test Suite:** `temp_ops/test_use_case_management_ui.sh`
**Results:** 10/10 tests passing ✅

**Test Coverage:**

1. ✅ List use cases (admin access)
2. ✅ Create use case
3. ✅ Get use case details
4. ✅ Update use case
5. ✅ Clone use case
6. ✅ State transitions
7. ✅ Version history
8. ✅ Rollback functionality
9. ✅ Delete draft use case
10. ✅ Non-admin access denied

### Manual Testing

```bash
# Source test script for helper functions
source temp_ops/test_use_case_management_ui.sh

# Run individual tests
test_list_use_cases
test_create_use_case
test_clone_use_case
```

---

## Migration from Template API

If you have existing templates, migrate them to use cases:

```python
# Example migration script
import requests

# Get all templates
templates = requests.get(
    "http://localhost:8006/api/v1/templates",
    headers={"Authorization": f"Bearer {token}"}
).json()

# Convert each template to use case
for template in templates["templates"]:
    use_case = {
        "use_case_id": template["template_id"],
        "name": template["name"],
        "description": template.get("description"),
        "category": "migrated",
        "intent_type": "rag_qa",
        "lifecycle_state": "draft",
        "config_json": {
            "models": {
                "llm": "mistral-large",
                "embedding": "all-minilm-l6-v2"
            },
            "rag": {"enabled": True, "top_k": 10}
        },
        "prompts": {
            "system_prompt": template["template_content"],
            "developer_prompt": None,
            "fewshots": []
        }
    }

    requests.post(
        "http://localhost:8006/api/v1/admin/use-cases",
        headers={"Authorization": f"Bearer {token}"},
        json=use_case
    )
```

---

## Related Documentation

- **Architecture Decision:** [ADR-018: Use Case Owned Architecture](../development/adrs/ADR-018-Use-Case-Owned-Architecture.md)
- **Collection Integration:** [ADR-021: Collection-Based Document Management](../development/adrs/ADR-021-Collection-Based-Document-Management.md)
- **Implementation Plan:** [USE_CASE_MANAGEMENT_PLAN.md](../development/plans/USE_CASE_MANAGEMENT_PLAN.md)
- **Completion Report:** [P3-F2-USE-CASE-MANAGEMENT-WEEK1.md](../development/completed/tasks/P3-F2-USE-CASE-MANAGEMENT-WEEK1.md)
- **Template API (Legacy):** [template-management.md](./template-management.md)

---

**Last Updated:** October 18, 2025
**API Version:** 1.0
**Implementation Status:** Implemented
