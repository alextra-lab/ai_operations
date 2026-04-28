# Public Configuration API

**Base URL:** `/api/v1/config`
**Authentication:** Required (any authenticated user)
**Date:** February 2026
**Reference:** ADR-067 (Dynamic Categories, Intent Capability Profiles)

---

## Overview

Read-only endpoints for platform configuration used by the Use Case wizard and other UI components. Any authenticated user can read; no admin role required. Categories and intent types are loaded dynamically from the database (domain-neutral, deployment-configurable).

---

## Authentication

Include JWT in the Authorization header:

```bash
Authorization: Bearer <access_token>
```

---

## Endpoints

### List categories

**GET** `/api/v1/config/categories`

Returns all active intent categories for use case classification (e.g. Security, Legal, IT Ops, General). Used by the wizard to populate the category dropdown.

**Response:** `CategoriesListResponse`

```json
{
  "categories": [
    {
      "category_code": "SECURITY",
      "display_name": "Security",
      "description": "Security operations and threat analysis",
      "icon": "security",
      "color": "#1976d2",
      "sort_order": 1
    }
  ],
  "total": 4
}
```

---

### List intent types with capability profiles

**GET** `/api/v1/config/intent-types`

Returns all active intent types with capability profiles and auto-preset defaults. The wizard uses these to auto-configure sampling preset and output format when an intent is selected.

**Response:** `IntentTypesListResponse`

```json
{
  "intent_types": [
    {
      "intent_code": "EXTRACTION",
      "display_name": "Extraction",
      "description": "Structured data extraction from text",
      "category_code": "SECURITY",
      "icon": "table_chart",
      "color": "#2e7d32",
      "is_system": true,
      "default_sampling_preset": "strict",
      "default_output_format": "json",
      "recommended_capabilities": ["structured_output", "rag"],
      "sort_order": 1
    }
  ],
  "total": 12
}
```

**Auto-presets:** When the user selects an intent in the wizard, the UI may apply `default_sampling_preset` and `default_output_format` to the use case config. Values for sampling: `strict` | `balanced` | `creative`; for output: `text` | `json` | `yaml` | `structured`.

---

## Frontend usage

The wizard loads categories and intent types on init via `PlatformConfigService` (caching and fallback when the backend is unavailable). See `src/frontend-angular` for the service and models.
