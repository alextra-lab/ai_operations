# System Configuration API Reference

**Version:** 1.0
**Base URL:** `/api/v1/admin/config`
**Authentication:** Required (Admin role only)
**Date:** October 27, 2025
**Status:** Implemented

---

## Overview

The System Configuration API provides admin-only access to system-wide configuration settings stored in the `system_config` table. Configuration is organized into four sections (corpus, auth, features, system) and stored as JSONB for flexibility.

**Key Features:**

- Get all configuration sections or individual section
- Update configuration with schema validation
- Export configuration as YAML
- Import configuration from YAML with validation
- JSON schema retrieval for frontend dynamic forms
- **Health endpoint for configuration validation (NEW - Oct 27, 2025)**

**Architecture References:**
- **ADR-037:** UUID Primary Keys
- **ADR-038:** JSONB Configuration Storage
- **ADR-039:** Row-Level Security (Admin-Only Access)
- **ADR-021 Addendum 3:** Per-Collection Embedding Model Architecture

---

## Authentication

All endpoints require **admin role**. Corpus admins and other roles are denied access.

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

## Configuration Sections

### Corpus Configuration

Document and embedding settings.

**Fields:**
- `chunk_size` (512) - Document chunking size in tokens (128-8192, must not exceed embedding model context window)
- `chunk_overlap` (50) - Character overlap between chunks (0-512)
- `default_embedding_model` - Default model pre-selected in Collection Create Dialog
  - **Note:** This is a convenience default, NOT global enforcement
  - Each collection chooses its own model at creation (immutable thereafter)
  - Example: "all-MiniLM-L6-v2"
  - See ADR-021 Addendum 3 for architecture details
- `max_document_size_mb` (50) - Maximum file upload size (1-500)
- `allowed_file_types` - List of accepted extensions (pdf, txt, docx, md, csv, json, xml, html)

### Auth Configuration

Authentication and session settings.

**Fields:**
- `session_timeout_minutes` (60) - Session timeout (5-1440)
- `refresh_token_ttl_days` (30) - Refresh token TTL (1-90)
- `password_policy` - Password requirements object:
  - `min_length` (8) - Minimum password length (6-32)
  - `require_uppercase` (true) - Require uppercase letters
  - `require_lowercase` (true) - Require lowercase letters
  - `require_numbers` (true) - Require numbers
  - `require_special` (false) - Require special characters

### Feature Flags

Enable/disable system features.

**Fields:**
- `multi_collection_search` (false) - Enable multi-collection RAG search
- `export_functionality` (true) - Enable export features
- `conversation_cache` (true) - Enable conversation caching
- `telemetry_enabled` (true) - Enable telemetry collection

### System Configuration

System-level operational settings.

**Fields:**
- `log_level` ("INFO") - System log level (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- `max_workers` (4) - Maximum worker threads (1-32)
- `request_timeout_seconds` (30) - Request timeout (5-300)
- `enable_debug_endpoints` (false) - Enable debug API endpoints

---

## Endpoints

### 1. Get All Configuration

**GET** `/api/v1/admin/config/`

Retrieve all configuration sections.

**Example Request:**

```bash
curl -X GET "http://localhost:8006/api/v1/admin/config/" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**

```json
{
  "corpus": {
    "chunk_size": 512,
    "chunk_overlap": 50,
    "default_embedding_model": "all-MiniLM-L6-v2",
    "max_document_size_mb": 50,
    "allowed_file_types": ["pdf", "txt", "docx", "md"]
  },
  "auth": {
    "session_timeout_minutes": 60,
    "refresh_token_ttl_days": 30,
    "password_policy": {
      "min_length": 8,
      "require_uppercase": true,
      "require_lowercase": true,
      "require_numbers": true,
      "require_special": false
    }
  },
  "features": {
    "multi_collection_search": false,
    "export_functionality": true,
    "conversation_cache": true,
    "telemetry_enabled": true
  },
  "system": {
    "log_level": "INFO",
    "max_workers": 4,
    "request_timeout_seconds": 30,
    "enable_debug_endpoints": false
  }
}
```

**Status Codes:**

- `200 OK` - Configuration retrieved successfully
- `403 Forbidden` - Insufficient permissions (requires admin role)
- `500 Internal Server Error` - Server error

---

### 2. Get Configuration Section

**GET** `/api/v1/admin/config/{section}`

Retrieve a specific configuration section.

**Path Parameters:**
- `section` - Section name (corpus, auth, features, system)

**Example Request:**

```bash
curl -X GET "http://localhost:8006/api/v1/admin/config/corpus" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**

```json
{
  "section": "corpus",
  "config": {
    "chunk_size": 512,
    "chunk_overlap": 50,
    "default_embedding_model": "all-MiniLM-L6-v2",
    "max_document_size_mb": 50,
    "allowed_file_types": ["pdf", "txt", "docx", "md"]
  },
  "updated_at": "2025-10-27T18:30:00Z",
  "updated_by": "f2938a78-b70a-4749-860f-c9c580b91373",
  "restart_required": false
}
```

**Status Codes:**

- `200 OK` - Section retrieved successfully
- `404 Not Found` - Invalid section name
- `403 Forbidden` - Insufficient permissions
- `500 Internal Server Error` - Server error

---

### 3. Update Configuration Section

**PUT** `/api/v1/admin/config/{section}`

Update a configuration section with validation.

**Path Parameters:**
- `section` - Section name (corpus, auth, features, system)

**Request Body:**

```json
{
  "chunk_size": 512,
  "chunk_overlap": 50,
  "default_embedding_model": "all-MiniLM-L6-v2",
  "max_document_size_mb": 50,
  "allowed_file_types": ["pdf", "txt", "docx", "md"]
}
```

**Example Request:**

```bash
curl -X PUT "http://localhost:8006/api/v1/admin/config/corpus" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "chunk_size": 512,
    "chunk_overlap": 50,
    "default_embedding_model": "all-MiniLM-L6-v2",
    "max_document_size_mb": 50,
    "allowed_file_types": ["pdf", "txt", "docx", "md"]
  }'
```

**Response:**

```json
{
  "section": "corpus",
  "config": {
    "chunk_size": 512,
    "chunk_overlap": 50,
    "default_embedding_model": "all-MiniLM-L6-v2",
    "max_document_size_mb": 50,
    "allowed_file_types": ["pdf", "txt", "docx", "md"]
  },
  "updated_at": "2025-10-27T18:45:00Z",
  "updated_by": "f2938a78-b70a-4749-860f-c9c580b91373",
  "restart_required": true
}
```

**Status Codes:**

- `200 OK` - Configuration updated successfully
- `404 Not Found` - Invalid section name
- `422 Unprocessable Entity` - Invalid configuration data (schema validation failed)
- `403 Forbidden` - Insufficient permissions
- `500 Internal Server Error` - Server error

**Validation:**

Configuration is validated against Pydantic schemas before saving:
- `CorpusConfig` - Validates chunk sizes, file types, model names
- `AuthConfig` - Validates timeouts, password policy
- `FeatureFlags` - Validates boolean flags
- `SystemConfig` - Validates log level, worker count, timeouts

**Restart Required:**

Some configuration changes require service restart:
- `corpus` section changes → Restart required
- `system` section changes → Restart required
- `auth` and `features` → Restart not required (runtime changes)

---

### 4. Get Configuration Schema

**GET** `/api/v1/admin/config/schema/{section}`

Retrieve JSON schema for a configuration section (used for dynamic form generation).

**Path Parameters:**
- `section` - Section name (corpus, auth, features, system)

**Example Request:**

```bash
curl -X GET "http://localhost:8006/api/v1/admin/config/schema/corpus" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**

```json
{
  "$defs": {},
  "properties": {
    "chunk_size": {
      "default": 512,
      "description": "Document chunk size in tokens (must not exceed embedding model context window)",
      "maximum": 8192,
      "minimum": 128,
      "title": "Chunk Size",
      "type": "integer"
    },
    "chunk_overlap": {
      "default": 50,
      "description": "Character overlap between chunks",
      "maximum": 512,
      "minimum": 0,
      "title": "Chunk Overlap",
      "type": "integer"
    },
    "default_embedding_model": {
      "default": "text-embedding-3-small",
      "description": "Default embedding model for collections",
      "title": "Default Embedding Model",
      "type": "string"
    },
    "max_document_size_mb": {
      "default": 50,
      "description": "Maximum document size in MB",
      "maximum": 500,
      "minimum": 1,
      "title": "Max Document Size Mb",
      "type": "integer"
    },
    "allowed_file_types": {
      "default": ["pdf", "txt", "docx", "md"],
      "description": "Allowed file types for upload",
      "items": { "type": "string" },
      "title": "Allowed File Types",
      "type": "array"
    }
  },
  "required": [],
  "title": "CorpusConfig",
  "type": "object"
}
```

**Status Codes:**

- `200 OK` - Schema retrieved successfully
- `404 Not Found` - Invalid section name
- `403 Forbidden` - Insufficient permissions

**Usage:**

Frontend uses this endpoint to dynamically generate configuration forms from JSON Schema.

---

### 5. Export Configuration

**POST** `/api/v1/admin/config/export`

Export all configuration as YAML.

**Example Request:**

```bash
curl -X POST "http://localhost:8006/api/v1/admin/config/export" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**

```json
{
  "config_yaml": "corpus:\n  chunk_size: 512\n  chunk_overlap: 50\n  default_embedding_model: all-MiniLM-L6-v2\n  max_document_size_mb: 50\n  allowed_file_types:\n  - pdf\n  - txt\n  - docx\n  - md\nauth:\n  session_timeout_minutes: 60\n  refresh_token_ttl_days: 30\n  password_policy:\n    min_length: 8\n    require_uppercase: true\n    require_lowercase: true\n    require_numbers: true\n    require_special: false\nfeatures:\n  multi_collection_search: false\n  export_functionality: true\n  conversation_cache: true\n  telemetry_enabled: true\nsystem:\n  log_level: INFO\n  max_workers: 4\n  request_timeout_seconds: 30\n  enable_debug_endpoints: false\n",
  "exported_at": "2025-10-27T18:45:00.000Z"
}
```

**Status Codes:**

- `200 OK` - Configuration exported successfully
- `403 Forbidden` - Insufficient permissions
- `500 Internal Server Error` - Server error

---

### 6. Import Configuration

**POST** `/api/v1/admin/config/import`

Import configuration from YAML with validation.

**Request Body:**

```json
{
  "config_yaml": "corpus:\n  chunk_size: 512\n  ...",
  "validate_only": false
}
```

**Fields:**
- `config_yaml` - YAML configuration string
- `validate_only` (default: false) - Validate without applying

**Example Request:**

```bash
curl -X POST "http://localhost:8006/api/v1/admin/config/import" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "config_yaml": "corpus:\n  chunk_size: 512\n  chunk_overlap: 50\n  default_embedding_model: all-MiniLM-L6-v2\n  max_document_size_mb: 50\n  allowed_file_types:\n  - pdf\n  - txt\n",
    "validate_only": false
  }'
```

**Response:**

```json
{
  "success": true,
  "sections_updated": ["corpus", "auth", "features", "system"],
  "restart_required": true,
  "validation_errors": null
}
```

**Status Codes:**

- `200 OK` - Import completed or validation succeeded
- `422 Unprocessable Entity` - Invalid YAML or configuration validation failed
- `403 Forbidden` - Insufficient permissions
- `500 Internal Server Error` - Server error

---

## Health Endpoint (NEW - Oct 27, 2025)

### Configuration Health Check

**GET** `/health/config`

Check configuration health, including model availability validation.

**Example Request:**

```bash
curl -X GET "http://localhost:8006/health/config" \
  -H "Authorization: Bearer $TOKEN"
```

**Response (Healthy):**

```json
{
  "healthy": true,
  "issues": [],
  "checked_at": "2025-10-27T18:50:00.000Z",
  "status": "healthy"
}
```

**Response (Unhealthy):**

```json
{
  "healthy": false,
  "issues": [
    {
      "severity": "critical",
      "component": "corpus_config",
      "message": "Default embedding model 'text-embedding-3-small' is not available",
      "recommendation": "Update default_embedding_model in System Configuration to an available model",
      "impact": "Cannot create new collections"
    }
  ],
  "checked_at": "2025-10-27T18:50:00.000Z",
  "status": "unhealthy"
}
```

**Status Codes:**

- `200 OK` - Health check completed (healthy or unhealthy)
- `403 Forbidden` - Insufficient permissions
- `500 Internal Server Error` - Health check failed

**Health Checks Performed:**

1. **Default Embedding Model Availability:**
   - Validates `corpus.default_embedding_model` exists in Model Registry
   - Checks model has `is_available=true` and `model_type='embedding'`
   - Reports critical issue if model missing or unavailable
   - Impact: New collections cannot be created without available default

**Frontend Integration:**

- System Configuration page displays health banner when issues detected
- Auto-refreshes health status after configuration saves
- Provides clear messaging and recommendations

---

## Row-Level Security (RLS)

**Policy:** `admin_only_system_config`
**Effect:** Admin-only access for all operations

**Session Variables Required:**
- `aio.user_id` - Set by RLS middleware from JWT token
- `aio.user_role` - Set by RLS middleware from JWT token

**Implementation:**

The RLS middleware extracts user information from JWT tokens and sets PostgreSQL session variables:

```sql
SET LOCAL aio.user_id = '<user_uuid>';
SET LOCAL aio.user_role = 'admin';
```

**Policy Check:**

```sql
CREATE POLICY admin_only_system_config ON system_config
FOR ALL
USING (aio.user_has_role('admin'))
WITH CHECK (fusiencenter.user_has_role('admin'));
```

**Critical Bug Fix (Oct 27, 2025):**
- Fixed RLS middleware to extract `role` (singular) from TokenPayload
- Previous bug: middleware looked for `roles` (plural), causing empty session variable
- Result: 500 errors on save resolved

---

## Error Handling

### Common Errors

**403 Forbidden - Non-Admin User:**

```json
{
  "detail": "Access denied. Required role: admin"
}
```

**404 Not Found - Invalid Section:**

```json
{
  "detail": "Invalid section: invalid_section. Must be one of: ['corpus', 'auth', 'features', 'system']"
}
```

**422 Unprocessable Entity - Validation Failed:**

```json
{
  "detail": "Invalid configuration: chunk_size must be between 128 and 8192"
}
```

**422 Unprocessable Entity - Invalid File Type:**

```json
{
  "detail": "Invalid file type: exe. Must be one of: {'pdf', 'txt', 'docx', 'md', 'csv', 'json', 'xml', 'html'}"
}
```

---

## Best Practices

### 1. Validate Before Applying

Use `validate_only: true` when importing configuration:

```bash
curl -X POST "http://localhost:8006/api/v1/admin/config/import" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "config_yaml": "...",
    "validate_only": true
  }'
```

### 2. Check Health After Changes

Always verify configuration health after updates:

```bash
curl -X GET "http://localhost:8006/health/config" \
  -H "Authorization: Bearer $TOKEN"
```

### 3. Backup Before Import

Export current configuration before importing:

```bash
curl -X POST "http://localhost:8006/api/v1/admin/config/export" \
  -H "Authorization: Bearer $TOKEN" > config_backup_$(date +%Y%m%d).yaml
```

### 4. Embedding Model Selection

When changing `default_embedding_model`:
- Verify model exists in Model Registry
- Check model `is_available=true` with GET `/api/v1/models?model_type=embedding`
- Use built-in `all-MiniLM-L6-v2` for guaranteed availability (no API costs)
- Remote models require API keys and external connectivity

### 5. Restart Services After Config Changes

Some configuration changes require service restart:
- Corpus configuration (chunk size, embedding defaults)
- System configuration (log level, workers, timeouts)

Check `restart_required` field in response.

---

## Related Documentation

- **Backend Implementation:** `src/orchestrator/app/routers/admin_config.py`
- **Schemas:** `src/orchestrator/app/schemas/system_config.py`
- **Frontend Service:** `src/frontend-angular/src/app/pages/admin/system-config/services/system-config.service.ts`
- **Frontend Component:** `src/frontend-angular/src/app/pages/admin/system-config/system-config.component.ts`
- **Database Schema:** [SCHEMA.md](../../architecture/database/SCHEMA.md#system_config)
- **RLS Policies:** [RLS_POLICIES.md](../../architecture/database/RLS_POLICIES.md#system_config)
- **ADR-038:** JSONB Configuration Storage
- **ADR-039:** Row-Level Security
- **ADR-021 Addendum 3:** Per-Collection Embedding Model Architecture

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| Oct 27, 2025 | 1.0 | Initial documentation. Added health endpoint section. Documented per-collection embedding model architecture. Included RLS bug fix details. |

---

**Document Owner:** Alex
**Last Updated:** October 27, 2025
**Status:** Implemented
