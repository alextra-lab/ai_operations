# Template Management API Reference

**Version:** 1.0
**Base URL:** `/api/v1/templates`
**Authentication:** Required (Admin role only)
**Date:** October 12, 2025
**Updated:** October 18, 2025

---

> **⚠️ NOTE - October 2025:**
> Template Management API coexists with the newer Use Case Management API (`/api/v1/admin/use-cases`).
> **For new development:** Use the Use Case Management API (see [ADR-018: Use Case Owned Architecture](../development/adrs/ADR-018-Use-Case-Owned-Architecture.md))
> **This API:** Maintained for backward compatibility and specific template-only operations.

**Disambiguation:** This API is **prompt-template** CRUD (versioned prompt templates for use case configuration). Use case **authoring** (input fields, user prompt template with `{{variable}}`, output visualization) is configured via the **Use Case Management API** in each use case’s `config_json`. See [Use Case Management](use-case-management.md) for `config_json.input_fields`, `config_json.user_prompt_template`, and `config_json.output_contract` (including `template_id` for built-in or custom visualization templates). Custom **output** (visualization) templates are managed via the [Output Templates API](admin/output-templates.md) (admin).

---

## Overview

The Template Management API provides comprehensive CRUD operations, version control, and approval workflows for prompt templates used in use case configurations.

**Key Features:**

- Template CRUD operations with pagination and filtering
- Version control with automatic versioning and activation
- Approval workflow with status tracking
- Version comparison with unified diff
- Admin-only access with full audit trail

---

## Authentication

All endpoints require admin authentication. Include JWT token in Authorization header:

```bash
Authorization: Bearer <access_token>
```

**Get Admin Token:**

```bash
curl -X POST "http://localhost:8006/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin" \
  -d "password=adminpassword"
```

---

## Endpoints

### 1. List Templates

**GET** `/api/v1/templates`

List all prompt templates with optional filtering and pagination.

**Query Parameters:**

- `page` (integer, default: 1) - Page number
- `page_size` (integer, default: 50, max: 100) - Items per page
- `template_id_filter` (string, optional) - Filter by template ID
- `deployment_status` (string, optional) - Filter by status (draft/pending/approved/deployed)
- `active_only` (boolean, default: false) - Return only active versions

**Example Request:**

```bash
curl -X GET "http://localhost:8006/api/v1/templates?page=1&page_size=10&deployment_status=approved" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:** `TemplateListResponse`

```json
{
  "templates": [...],
  "total_count": 6,
  "page": 1,
  "page_size": 10
}
```

---

### 2. Get Template

**GET** `/api/v1/templates/{template_id}`

Get a specific template by ID. Returns active version by default.

**Path Parameters:**

- `template_id` (string) - Template identifier

**Query Parameters:**

- `version` (integer, optional) - Specific version number (default: active version)

**Example Request:**

```bash
curl -X GET "http://localhost:8006/api/v1/templates/general_query" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:** `TemplateResponse`

---

### 3. Create Template

**POST** `/api/v1/templates`

Create a new prompt template. First version starts at v1.

**Request Body:** `TemplateCreate`

```json
{
  "template_id": "threat_analysis",
  "prompt_type": "system",
  "template_content": "Analyze threat: {threat_description}. Context: {context}",
  "variables": ["threat_description", "context"],
  "metadata_json": {
    "category": "threat_intelligence",
    "difficulty": "medium"
  },
  "deployment_status": "draft"
}
```

**Example Request:**

```bash
curl -X POST "http://localhost:8006/api/v1/templates" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @template.json
```

**Response:** `TemplateResponse` (201 Created)

**Errors:**

- `409 Conflict` - Template ID already exists

---

### 4. Update Template

**PUT** `/api/v1/templates/{template_id}`

Update the active version of a template. For new versions, use POST to /versions endpoint.

**Path Parameters:**

- `template_id` (string) - Template identifier

**Request Body:** `TemplateUpdate`

```json
{
  "template_content": "Updated template content...",
  "deployment_status": "pending"
}
```

**Example Request:**

```bash
curl -X PUT "http://localhost:8006/api/v1/templates/threat_analysis" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"template_content": "Updated content..."}'
```

**Response:** `TemplateResponse`

---

### 5. Delete Template

**DELETE** `/api/v1/templates/{template_id}`

Delete all versions of a template. This is a destructive operation.

**Path Parameters:**

- `template_id` (string) - Template identifier

**Example Request:**

```bash
curl -X DELETE "http://localhost:8006/api/v1/templates/threat_analysis" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**

```json
{
  "message": "Template 'threat_analysis' deleted successfully",
  "versions_deleted": 3
}
```

---

### 6. Get Template Versions

**GET** `/api/v1/templates/{template_id}/versions`

Get all versions of a template, ordered by version number descending.

**Path Parameters:**

- `template_id` (string) - Template identifier

**Example Request:**

```bash
curl -X GET "http://localhost:8006/api/v1/templates/general_query/versions" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:** `TemplateVersionListResponse`

```json
{
  "template_id": "general_query",
  "versions": [
    {
      "id": "uuid-v2",
      "template_id": "general_query",
      "version_number": 2,
      "is_active_version": true,
      "deployment_status": "approved",
      "created_at": "2025-10-12T17:00:00Z",
      "updated_at": "2025-10-12T17:00:00Z"
    },
    {
      "id": "uuid-v1",
      "template_id": "general_query",
      "version_number": 1,
      "is_active_version": false,
      "deployment_status": "deployed",
      "created_at": "2025-10-10T15:00:00Z",
      "updated_at": "2025-10-10T15:00:00Z"
    }
  ],
  "total_versions": 2
}
```

---

### 7. Create Template Version

**POST** `/api/v1/templates/{template_id}/versions`

Create a new version of an existing template. New version becomes active automatically.

**Path Parameters:**

- `template_id` (string) - Template identifier

**Request Body:** `TemplateVersionCreate`

```json
{
  "template_content": "Version 2 content...",
  "variables": ["var1", "var2"],
  "metadata_json": {
    "performance_improvement": true
  },
  "change_notes": "Simplified template for better performance"
}
```

**Example Request:**

```bash
curl -X POST "http://localhost:8006/api/v1/templates/general_query/versions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @new-version.json
```

**Response:** `TemplateResponse` (new version, version_number incremented)

**Behavior:**

- Automatically increments version number
- Deactivates all previous versions
- New version becomes active
- Deployment status set to "draft"

---

### 8. Activate Template Version

**POST** `/api/v1/templates/{template_id}/activate`

Activate a specific version of a template. Deactivates all other versions.

**Path Parameters:**

- `template_id` (string) - Template identifier

**Request Body:** `TemplateActivationRequest`

```json
{
  "version_number": 1
}
```

**Example Request:**

```bash
curl -X POST "http://localhost:8006/api/v1/templates/general_query/activate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"version_number": 1}'
```

**Response:** `TemplateResponse` (activated version)

**Errors:**

- `404 Not Found` - Version not found

---

### 9. Compare Template Versions

**POST** `/api/v1/templates/{template_id}/diff`

Compare two versions of a template, returning unified diff and metadata changes.

**Path Parameters:**

- `template_id` (string) - Template identifier

**Request Body:** `TemplateDiffRequest`

```json
{
  "version_1": 1,
  "version_2": 2
}
```

**Example Request:**

```bash
curl -X POST "http://localhost:8006/api/v1/templates/general_query/diff" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"version_1": 1, "version_2": 2}'
```

**Response:** `TemplateDiffResponse`

```json
{
  "template_id": "general_query",
  "version_1": 1,
  "version_2": 2,
  "content_diff": "--- v1\n+++ v2\n@@ -1 +1 @@\n-Old content\n+New content",
  "variables_added": ["new_var"],
  "variables_removed": ["old_var"],
  "metadata_changes": {
    "version_1_keys": ["category"],
    "version_2_keys": ["category", "performance"]
  }
}
```

---

### 10. Approve Template

**POST** `/api/v1/templates/{template_id}/approve`

Approve the active version of a template for deployment.

**Path Parameters:**

- `template_id` (string) - Template identifier

**Request Body:** `TemplateApprovalRequest`

```json
{
  "approval_notes": "Reviewed and approved for production use"
}
```

**Example Request:**

```bash
curl -X POST "http://localhost:8006/api/v1/templates/general_query/approve" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"approval_notes": "Approved for deployment"}'
```

**Response:** `TemplateResponse`

```json
{
  "id": "uuid",
  "template_id": "general_query",
  "deployment_status": "approved",
  "approved_by_user_id": "admin-uuid",
  "approved_at": "2025-10-12T18:00:00Z",
  "metadata_json": {
    "approval_notes": "Reviewed and approved for production use"
  },
  ...
}
```

**Behavior:**

- Sets `deployment_status` to "approved"
- Records `approved_by_user_id` (current user)
- Sets `approved_at` timestamp
- Adds approval_notes to metadata if provided

---

### 11. Reject Template

**POST** `/api/v1/templates/{template_id}/reject`

Reject the active version of a template, reverting status to draft.

**Path Parameters:**

- `template_id` (string) - Template identifier

**Request Body:** `TemplateRejectionRequest`

```json
{
  "rejection_reason": "Template needs more detailed analysis steps"
}
```

**Example Request:**

```bash
curl -X POST "http://localhost:8006/api/v1/templates/general_query/reject" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"rejection_reason": "Missing security context"}'
```

**Response:** `TemplateResponse`

```json
{
  "id": "uuid",
  "template_id": "general_query",
  "deployment_status": "draft",
  "metadata_json": {
    "rejection_reason": "Missing security context",
    "rejected_by": "admin-uuid",
    "rejected_at": "2025-10-12T18:05:00Z"
  },
  ...
}
```

**Behavior:**

- Sets `deployment_status` to "draft"
- Adds rejection_reason to metadata
- Records rejected_by and rejected_at in metadata

---

## Data Models

### TemplateResponse

```typescript
interface TemplateResponse {
  id: string;                        // UUID primary key
  template_id: string;               // Unique template identifier
  prompt_type: string;               // "system", "user", or "assistant"
  template_content: string;          // Template with {variable} placeholders
  variables: string[];               // List of variable names
  metadata_json: Record<string, any>; // Additional metadata
  use_case_id?: string;              // Optional use case binding
  version_number: number;            // Version number (starts at 1)
  is_active_version: boolean;        // Whether this is the active version
  deployment_status: string;         // "draft", "pending", "approved", "deployed"
  created_by_user_id?: string;       // Creator user ID
  approved_by_user_id?: string;      // Approver user ID (if approved)
  approved_at?: string;              // Approval timestamp (ISO 8601)
  created_at: string;                // Creation timestamp (ISO 8601)
  updated_at: string;                // Last update timestamp (ISO 8601)
}
```

### Deployment Status Lifecycle

```
draft → pending → approved → deployed
  ↑                   ↓
  └─────(reject)──────┘
```

**Status Descriptions:**

- `draft` - Template is being developed, not ready for review
- `pending` - Template submitted for approval review
- `approved` - Template approved by admin, ready for deployment
- `deployed` - Template actively deployed and in use

---

## Usage Examples

### Example 1: Create and Approve a Template

```bash
# 1. Create template
curl -X POST "http://localhost:8006/api/v1/templates" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": "incident_analysis",
    "prompt_type": "system",
    "template_content": "Analyze incident: {incident_id}. Details: {details}",
    "variables": ["incident_id", "details"],
    "metadata_json": {"category": "incident_response"},
    "deployment_status": "draft"
  }'

# 2. Update status to pending
curl -X PUT "http://localhost:8006/api/v1/templates/incident_analysis" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"deployment_status": "pending"}'

# 3. Approve template
curl -X POST "http://localhost:8006/api/v1/templates/incident_analysis/approve" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"approval_notes": "Reviewed and approved"}'
```

### Example 2: Create New Version and Compare

```bash
# 1. Create new version
curl -X POST "http://localhost:8006/api/v1/templates/incident_analysis/versions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "template_content": "Enhanced: Analyze incident {incident_id}...",
    "variables": ["incident_id"],
    "change_notes": "Simplified and improved performance"
  }'

# 2. Compare versions
curl -X POST "http://localhost:8006/api/v1/templates/incident_analysis/diff" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"version_1": 1, "version_2": 2}'

# 3. Activate version 1 (rollback)
curl -X POST "http://localhost:8006/api/v1/templates/incident_analysis/activate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"version_number": 1}'
```

### Example 3: Reject a Template

```bash
curl -X POST "http://localhost:8006/api/v1/templates/incident_analysis/reject" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"rejection_reason": "Template needs additional validation rules"}'
```

---

## Error Responses

All endpoints return standard HTTP status codes:

- `200 OK` - Successful operation
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid request data
- `401 Unauthorized` - Missing or invalid authentication
- `403 Forbidden` - User lacks required admin role
- `404 Not Found` - Template or version not found
- `409 Conflict` - Template ID already exists
- `500 Internal Server Error` - Server error

**Error Response Format:**

```json
{
  "detail": "Error message describing what went wrong"
}
```

---

## Version Control Best Practices

### When to Create New Version

- Significant template content changes
- Variable list modifications
- Major metadata updates

### When to Update Existing Version

- Minor text adjustments
- Metadata additions (not structural changes)
- Deployment status changes

### Version Activation Strategy

- Test new versions thoroughly before activation
- Keep previous approved versions available for rollback
- Use version comparison to review changes before activation

### Approval Workflow

1. Create template in `draft` status
2. Update to `pending` when ready for review
3. Admin reviews and either:
   - Approves (sets to `approved` status)
   - Rejects (reverts to `draft` with reason)
4. Deploy approved templates to production

---

## Integration with Use Cases

Templates can be bound to use cases via `use_case_id` field:

```bash
# Create template for specific use case
curl -X POST "http://localhost:8006/api/v1/templates" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": "custom_analysis",
    "use_case_id": "046ea025-50c3-4ba4-bf5c-812e8764eb4e",
    "template_content": "Analyze {query} with context {context}",
    "variables": ["query", "context"]
  }'
```

---

## Frontend Integration

### Angular Service Usage

```typescript
import { TemplateService } from '@app/api/services/template.service';

@Component({...})
export class TemplateLibraryComponent {
  templates$: Observable<TemplateListResponse>;

  constructor(private templateService: TemplateService) {}

  ngOnInit(): void {
    // List templates
    this.templates$ = this.templateService.listTemplates({
      page: 1,
      page_size: 50,
      deployment_status: 'approved'
    });
  }

  createTemplate(template: TemplateCreate): void {
    this.templateService.createTemplate(template)
      .subscribe(result => {
        console.log('Template created:', result);
      });
  }

  approveTemplate(templateId: string): void {
    this.templateService.approveTemplate(templateId, 'Approved for production')
      .subscribe(result => {
        console.log('Template approved:', result);
      });
  }
}
```

---

## Testing

Comprehensive test script available at `temp_ops/test_template_management_api.sh`.

**Run Tests:**

```bash
cd $PROJECT_ROOT
export $(grep -v '^#' config/env/env.test | xargs)
bash temp_ops/test_template_management_api.sh
```

**Test Coverage:**

- ✅ All 15 test scenarios passing
- ✅ CRUD operations tested
- ✅ Version control validated
- ✅ Approval workflow verified
- ✅ RBAC enforcement confirmed

---

## See Also

- [UI Development Plan - P3-F2](../development/plans/UI_DEVELOPMENT_PLAN.md#p3-f2-template-management-system)
- [Session Log - P3-F2 Backend](../development/sessions/2025-10-12-p3-f2-template-management-backend.md)
- [Backend Completion Summary](../development/completed/tasks/P3-F2-TEMPLATE-MANAGEMENT-BACKEND.md)
- [Database Schema](../architecture/database-schema.md)

---

**Last Updated:** October 12, 2025
**Status:** Backend Complete ✅ | Frontend Pending 🔄
