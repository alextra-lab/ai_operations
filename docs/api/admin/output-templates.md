# Output Templates API (Admin)

**Base URL:** `/api/v1/admin/output-templates`
**Authentication:** Required. List/Get: any authenticated user. Create/Update/Delete: **Admin role required**.
**Date:** February 2026
**Reference:** ADR-066 (Domain-Neutral Visualization Templates)

---

## Overview

CRUD for **custom** output visualization templates. Built-in templates (e.g. `score-table-timeline`, `auto-table`, `bar-chart`) are read-only and defined in code; custom templates are stored in the `output_templates` table and can be created, updated, or deleted by admins. The Use Case wizard merges built-in and custom templates when showing the template selector.

---

## Authentication

```bash
Authorization: Bearer <access_token>
```

Admin token required for POST, PUT, DELETE. Use the same auth endpoint as other admin APIs.

---

## Endpoints

### List output templates

**GET** `/api/v1/admin/output-templates`

List all output templates (built-in + custom) with pagination.

**Query parameters:**

| Parameter   | Type    | Default | Description        |
|------------|---------|--------|--------------------|
| `page`     | integer | 1      | Page number        |
| `page_size`| integer | 50     | Items per page (1–100) |

**Response:** `OutputTemplateListResponse`

```json
{
  "templates": [
    {
      "id": "uuid",
      "template_id": "my-custom-table",
      "name": "My Custom Table",
      "description": "Custom layout for reports",
      "is_builtin": false,
      "data_schema": {},
      "layout": {},
      "export_formats": ["csv", "json"],
      "created_by": "uuid",
      "created_at": "2026-02-07T12:00:00Z",
      "updated_at": "2026-02-07T12:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 50
}
```

---

### Get output template

**GET** `/api/v1/admin/output-templates/{template_id}`

Get a single template by `template_id` (slug). Returns 404 if not found.

**Path parameters:** `template_id` (string) — e.g. `score-table-timeline` or a custom ID.

---

### Create output template (Admin)

**POST** `/api/v1/admin/output-templates`

Create a new custom output template.

**Request body:** `OutputTemplateCreate`

```json
{
  "template_id": "my-custom-table",
  "name": "My Custom Table",
  "description": "Optional description",
  "data_schema": {},
  "layout": {},
  "export_formats": ["csv", "json"]
}
```

- `template_id`: Unique slug (used in use case `config_json.output_contract.template_id`).
- `data_schema`: JSON Schema for the expected data shape.
- `layout`: Layout configuration (sections, component types) per ADR-066.
- `export_formats`: Optional list, e.g. `["pdf", "csv", "json", "excel"]`.

**Response:** `OutputTemplateResponse` (201 Created). Conflict (409) if `template_id` already exists.

---

### Update output template (Admin)

**PUT** `/api/v1/admin/output-templates/{template_id}`

Update a custom template. Built-in templates return 403 Forbidden.

**Request body:** `OutputTemplateUpdate` (all fields optional)

```json
{
  "name": "Updated name",
  "description": "Updated description",
  "data_schema": {},
  "layout": {},
  "export_formats": ["csv", "json", "excel"]
}
```

---

### Delete output template (Admin)

**DELETE** `/api/v1/admin/output-templates/{template_id}`

Delete a custom template. Built-in templates cannot be deleted (403). Returns 204 No Content on success.

---

## Use case integration

Use cases reference a template via `config_json.output_contract.template_id`. At execution time, the backend resolves the template (built-in or custom) to render structured output. Custom templates are loaded from the database and merged with built-in definitions in the frontend `TemplateRegistryService`.
