# Database Schema Documentation

**Version:** 1.2.0
**PostgreSQL Version:** 17+
**Last Updated:** 2025-10-30

## Table of Contents

1. [Overview](#overview)
2. [Authentication & Authorization](#authentication--authorization)
3. [System Configuration](#system-configuration)
4. [Document Management](#document-management)
5. [Use Case System](#use-case-system)
6. [Query History & Threading](#query-history--threading)
7. [Token Tracking](#token-tracking)
8. [Tools Platform](#tools-platform)
9. [Model Registry](#model-registry)
10. [Telemetry](#telemetry)
11. [Pricing Management](#pricing-management)
12. [Intent System](#intent-system)
13. [Audit & Security](#audit--security)
14. [Data Types](#data-types)
15. [Table Relationships](#table-relationships)

---

## Overview

The AI Operations Platform database consists of **33 tables** organized into logical domains:

| Domain | Tables | Purpose |
|--------|--------|---------|
| **Authentication** | 3 | User management, sessions, roles |
| **System Configuration** | 1 | System-wide configuration management |
| **Documents** | 3 | Collections, document metadata, usage tracking |
| **Use Cases** | 5 | Use case definitions, templates, patterns, assignments (user & role-based) |
| **Query History** | 3 | Conversation threads, query tracking |
| **Token Tracking** | 1 | LLM token consumption tracking |
| **Tools** | 5 | MCP tool management, secrets, invocations |
| **Models** | 3 | LLM/embedding model registry |
| **Telemetry** | 1 | PII-free execution metrics |
| **Pricing** | 3 | LLMaaS pricing tiers, per-model pricing history, and audit |
| **Intents** | 3 | Dynamic intent types, categories, usage logs |
| **Security** | 2 | Encryption keys, audit logs |

**Total:** 33 tables, 14 functions, 3 views

---

## Authentication & Authorization

### `users`

Primary user authentication table with multi-role support.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() | Unique user identifier |
| `username` | VARCHAR | UNIQUE, NOT NULL | Login username |
| `full_name` | VARCHAR | | Display name |
| `email` | VARCHAR | UNIQUE | Email address |
| `hashed_password` | VARCHAR | NOT NULL | Bcrypt hashed password |
| `role` | VARCHAR | NOT NULL | Primary role (admin/developer/user) |
| `is_active` | BOOLEAN | DEFAULT TRUE | Account enabled status |
| `center_id` | VARCHAR(255) | | Organization/center identifier |
| `user_metadata` | JSONB | DEFAULT '{}' | Additional user data |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Account creation timestamp |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last modification timestamp |
| `last_login` | TIMESTAMPTZ | | Last successful login |

**Indexes:**

- `ix_users_username` (UNIQUE) - Login lookup
- `ix_users_email` (UNIQUE, partial) - Email lookup where not null
- `idx_users_center_id` - Organization queries

**Relationships:**

- → `user_roles` (1:N) - Multi-role assignments
- → `refresh_tokens` (1:N) - Active sessions
- → Many tables via `created_by_user_id` foreign keys

---

### `refresh_tokens`

JWT refresh token storage for session management.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Token record identifier |
| `token` | VARCHAR | UNIQUE, NOT NULL | Refresh token value |
| `user_id` | UUID | FK → users(id) ON DELETE CASCADE | Token owner |
| `expires_at` | TIMESTAMPTZ | NOT NULL | Expiration timestamp |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Token creation time |
| `revoked` | BOOLEAN | DEFAULT FALSE | Revocation status |
| `revoked_at` | TIMESTAMPTZ | | Revocation timestamp |

**Indexes:**

- `ix_refresh_tokens_token` (UNIQUE) - Token lookup
- `ix_refresh_tokens_user_id` - User's active tokens

---

### `user_roles`

Multi-role membership table (many-to-many: users ↔ roles).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Assignment record ID |
| `user_id` | UUID | FK → users(id) ON DELETE CASCADE | User reference |
| `role` | TEXT | NOT NULL, CHECK | Role name (admin/developer/corpus_admin/user/service) |
| `granted_at` | TIMESTAMPTZ | DEFAULT NOW() | Grant timestamp |
| `granted_by` | UUID | FK → users(id) | Granting user |
| `metadata` | JSONB | DEFAULT '{}' | Assignment context |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last update |

**Indexes:**

- `idx_user_roles_unique` (UNIQUE) - (user_id, role) pair

**Constraints:**

- `user_roles_role_check` - Role must be in predefined list

---

## System Configuration

### `system_config`

**Purpose:** Store system-wide configuration using JSONB for flexibility

**Columns:**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| `section` | TEXT | NOT NULL, UNIQUE, CHECK | Configuration section (corpus, auth, features, system) |
| `config` | JSONB | NOT NULL | Configuration data as JSON |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Record creation timestamp |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last update timestamp |
| `updated_by` | UUID | FK → users(id) ON DELETE SET NULL | User who last updated |

**Indexes:**

- `idx_system_config_section` - Section lookup (primary access pattern)
- `idx_system_config_updated_by` - Audit queries by user
- `idx_system_config_config_gin` - GIN index for JSONB queries

**Triggers:**

- `trigger_system_config_updated_at` - Auto-update `updated_at` on modification

**RLS Policies:**

- `admin_only_system_config` - Admin-only access for all operations

**Constraints:**

- `section` CHECK - Must be one of: 'corpus', 'auth', 'features', 'system'

**Default Data:**

- **corpus:**
  - `chunk_size` (512) - Document chunking size
  - `chunk_overlap` (50) - Character overlap between chunks
  - `default_embedding_model` - Default model pre-selected in Collection Create Dialog (e.g., "all-MiniLM-L6-v2")
    - **Note:** This is a convenience default, NOT a global enforcement
    - Each collection chooses its own model at creation (immutable thereafter)
    - Health indicator shown if this model becomes unavailable
    - See ADR-021 Addendum 3 for per-collection model architecture
  - `max_document_size_mb` (50) - Maximum file upload size
  - `allowed_file_types` - List of accepted file extensions (pdf, txt, docx, md)
- **auth:** session_timeout_minutes (60), refresh_token_ttl_days (30), password_policy (min_length, require_uppercase, etc.)
- **features:** multi_collection_search, export_functionality, conversation_cache, telemetry_enabled
- **system:** log_level (INFO), max_workers (4), request_timeout_seconds (30), enable_debug_endpoints

**ADR Compliance:**

- ADR-037: UUID primary keys
- ADR-038: JSONB for flexible configuration storage
- ADR-039: Row-Level Security for admin-only access

---

## Document Management

### `collections`

Document collections with embedding model bindings.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Collection ID |
| `name` | VARCHAR(255) | UNIQUE, NOT NULL, CHECK format | Collection name (lowercase, alphanumeric, hyphens, underscores) |
| `description` | TEXT | | Collection description |
| `embedding_model` | VARCHAR(255) | NOT NULL | Embedding model identifier (immutable after creation) |
| `embedding_provider` | VARCHAR(100) | NOT NULL | Provider (openai/local/etc) |
| `embedding_dimensions` | INTEGER | NOT NULL, CHECK > 0 | Vector dimensions |
| `qdrant_collection_name` | VARCHAR(255) | UNIQUE, NOT NULL | Qdrant collection mapping |
| `is_default` | BOOLEAN | DEFAULT FALSE | Default collection flag |
| `is_active` | BOOLEAN | DEFAULT TRUE | Active status |
| `is_system_managed` | BOOLEAN | DEFAULT FALSE | System-managed flag |
| `created_by` | VARCHAR(255) | NOT NULL | Creator |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Creation time |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last update |
| `document_count` | INTEGER | DEFAULT 0, CHECK >= 0 | Document count |

**Constraints:**

- `chk_name_format` CHECK - Name must match `^[a-z0-9_-]+$`
- `chk_dimensions_positive` CHECK - Embedding dimensions > 0
- `chk_document_count_nonnegative` CHECK - Document count >= 0

**Indexes:**

- `idx_collections_unique_default` (UNIQUE partial) - Only one default collection allowed

**Design Notes:**

- **Per-Collection Embedding Model (ADR-021 Addendum 3, Oct 27, 2025):**
  - Each collection chooses its embedding model at creation (immutable thereafter)
  - Built-in `all-MiniLM-L6-v2` always available (local, 384D, no API costs)
  - Remote models (OpenAI, etc.) available when configured
  - Backend validates model availability via Model Registry on creation
  - Frontend provides dropdown with available models + "BUILT-IN" badge
- **Multi-Collection Search Constraint:**
  - Use Cases can search multiple collections ONLY if they share the same embedding model
  - Frontend filters collection selection after first choice (Use Case Wizard)
  - Backend enforces constraint and returns 400 error if violated
  - Rationale: Similarity scores differ between models (no normalization in v1)
- **Vector Space Consistency:**
  - Embedding model and dimensions must remain constant for vector space integrity
  - Admin migration tool planned for Phase 5 (P5-F8) to change models with re-embedding
- **System Configuration Default:**
  - `system_config.corpus.default_embedding_model` is a convenience pre-select
  - Not enforced globally - each collection chooses independently
  - Health indicator shown if default model becomes unavailable
- **Qdrant Mapping:**
  - Each collection maps to a Qdrant collection for actual vector storage
  - Documents reference collections for vector storage coordination

---

### `documents`

Master document metadata table (no actual content stored).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Document identifier |
| `title` | TEXT | NOT NULL | Document title |
| `source` | TEXT | | Source system/uploader |
| `author` | TEXT | | Document author |
| `created_at` | TIMESTAMPTZ | | Original document creation |
| `ingested_at` | TIMESTAMPTZ | DEFAULT NOW() | Ingestion timestamp |
| `ingested_by` | TEXT | | Ingesting user/process |
| `original_file_name` | TEXT | | Original filename |
| `file_type` | TEXT | | MIME type |
| `file_checksum` | TEXT | | SHA-256 hash for deduplication |
| `file_size` | INTEGER | | Size in bytes |
| `content_compressed` | BYTEA | | Optional compressed content |
| `embedding_model` | TEXT | | Embedding model used |
| `embedding_provider` | TEXT | | Provider (openai/local/etc) |
| `embedding_dimensions` | INTEGER | | Vector dimensions |
| `num_chunks` | INTEGER | | Chunk count |
| `avg_chunk_size_tokens` | INTEGER | | Average tokens per chunk |
| `tags` | TEXT[] | | Classification tags |
| `classification` | TEXT | | Document classification |
| `status` | TEXT | DEFAULT 'created' | Processing status |
| `error_message` | TEXT | | Ingestion error details |
| `metadata` | JSONB | DEFAULT '{}' | Additional metadata |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last update |

**Indexes:**

- `idx_documents_ingested_at` - Chronological queries
- `idx_documents_status` - Status filtering
- `idx_documents_classification` - Classification queries
- `idx_documents_embedding_model` - Model filtering
- `idx_documents_file_checksum` - Deduplication
- `idx_documents_tags` (GIN) - Tag search
- `idx_documents_title_search` (GIN) - Full-text title search

**Design Notes:**

- Actual document content stored in vector database (Qdrant)
- Chunks referenced by UUID arrays in usage_stats
- File checksum enables deduplication before ingestion

---

### `usage_stats`

Retrieval analytics and usage tracking.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Stats record ID |
| `document_id` | UUID | FK → documents(id) ON DELETE SET NULL | Source document |
| `chunk_ids` | UUID[] | | Retrieved chunk UUIDs |
| `accessed_at` | TIMESTAMPTZ | DEFAULT NOW() | Access timestamp |
| `user_id` | TEXT | | Accessing user |
| `query_text` | TEXT | | User query |
| `relevancy_scores` | FLOAT[] | | Per-chunk relevancy (parallel to chunk_ids) |
| `metadata` | JSONB | DEFAULT '{}' | Additional context |
| `average_relevancy` | FLOAT | | Mean relevancy score |
| `rag_confidence` | FLOAT | | RAG confidence score |
| `total_results_found` | INTEGER | | Total search results |
| `source_document_count` | INTEGER | | Unique documents cited |
| `run_id` | UUID | | Execution run identifier |

**Indexes:**

- `idx_usage_stats_document_id` - Document access patterns
- `idx_usage_stats_accessed_at` - Time-series queries
- `idx_usage_stats_user_id` - User activity
- `idx_usage_stats_chunk_ids` (GIN) - Chunk popularity queries

**Analytics Views:**

- `hot_documents` - Most accessed docs (30 days)
- `hot_chunks` - Most retrieved chunks (30 days)

---

## Use Case System

### `use_cases`

Dynamic use case definitions with JSONB configuration.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Use case ID |
| `use_case_id` | VARCHAR(255) | UNIQUE, NOT NULL | Human-readable identifier |
| `name` | VARCHAR(255) | NOT NULL | Display name |
| `description` | TEXT | | Detailed description |
| `category` | VARCHAR(100) | | Category (security/compliance/etc) |
| `intent_type` | VARCHAR(50) | NOT NULL | Intent code (QUERY/RULE_GENERATION/etc) |
| `version` | INTEGER | DEFAULT 1 | Version number |
| `lifecycle_state` | VARCHAR(20) | CHECK | draft/review/published/archived |
| `is_active` | BOOLEAN | DEFAULT FALSE | Active status |
| `config_json` | JSONB | NOT NULL, validated | Use case configuration |
| `metadata` | JSONB | DEFAULT '{}' | Additional metadata |
| `created_by_user_id` | UUID | FK → users(id) | Creator |
| `approved_by_user_id` | UUID | FK → users(id) | Approver |
| `published_by_user_id` | UUID | FK → users(id) | Publisher |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Creation time |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last modification |
| `approved_at` | TIMESTAMPTZ | | Approval timestamp |
| `published_at` | TIMESTAMPTZ | | Publication timestamp |

**config_json Structure:**

```json
{
  "visibility": {"roles": [], "tags": []},
  "models": {"llm": "...", "embedding": "..."},
  "generation_params": {"temperature": 0.7, "max_tokens": 2000, ...},
  "rag": {"enabled": true, "top_k": 10, "similarity_threshold": 0.7, ...},
  "tools_allowlist": [],
  "output_contract": {"format": "text", "schema": null, "validation_mode": "best_effort"},
  "telemetry": {"required_metrics": [...]},
  "policy": {"streaming_enabled": true, "pii_redaction": "anonymize", ...}
}
```

**Constraints:**

- Multiple CHECK constraints validate config_json structure
- Temperature must be [0.0, 1.0]
- Max tokens must be positive
- Output format must be text/json/yaml/structured

**Indexes:**

- `idx_use_cases_active` - (is_active, category)
- `idx_use_cases_intent` - (intent_type, lifecycle_state)
- Multiple GIN/BTREE indexes on config_json fields

**RLS:** Enabled - users see only assigned use cases

---

### `prompt_templates`

Versioned prompt templates for use cases.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Template ID |
| `template_id` | VARCHAR(255) | NOT NULL | Template identifier |
| `use_case_id` | UUID | FK → use_cases(id) ON DELETE SET NULL | Associated use case |
| `prompt_type` | VARCHAR(50) | DEFAULT 'system' | Prompt type |
| `version_number` | INTEGER | DEFAULT 1 | Version number |
| `template_content` | TEXT | NOT NULL | Prompt template |
| `variables` | JSONB | DEFAULT '[]' | Template variables |
| `metadata` | JSONB | DEFAULT '{}' | Additional metadata |
| `is_active_version` | BOOLEAN | DEFAULT FALSE | Active flag |
| `deployment_status` | VARCHAR(20) | DEFAULT 'draft' | Deployment status |
| `created_by_user_id` | UUID | FK → users(id) | Creator |
| `approved_by_user_id` | UUID | FK → users(id) | Approver |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Creation time |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last update |
| `approved_at` | TIMESTAMPTZ | | Approval time |

**Constraints:**

- `prompt_templates_unique_version` - (template_id, version_number) UNIQUE

**Indexes:**

- `idx_prompt_templates_active` - (template_id, is_active_version, deployment_status)

**RLS:** Enabled - role-based access

---

### `prompt_patterns`

Reusable prompt engineering pattern library.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Pattern ID |
| `pattern_id` | VARCHAR(100) | UNIQUE, NOT NULL | Pattern identifier (e.g., chain-of-thought) |
| `name` | VARCHAR(255) | NOT NULL | Display name |
| `category` | VARCHAR(100) | | Pattern category (reasoning/rag/soc/tools/json/learning/quality/advanced) |
| `description` | TEXT | | Detailed description and use cases |
| `system_prompt_template` | TEXT | | System-level prompt template |
| `developer_prompt_template` | TEXT | | Developer/hidden instructions template |
| `fewshots_template` | JSONB | DEFAULT '[]' | Example input/output pairs |
| `variables` | JSONB | DEFAULT '[]' | Template variable definitions |
| `source_url` | VARCHAR(500) | | Source reference URL (e.g., promptingguide.ai) |
| `tags` | JSONB | DEFAULT '[]' | Tags for searchability |
| `use_count` | INTEGER | DEFAULT 0 | Pattern application count (analytics) |
| `recommended_preset` | VARCHAR(50) | DEFAULT 'balanced' | Recommended sampling preset (ADR-023) |
| `max_tokens_override` | INTEGER | | Max tokens override for specific patterns |
| `special_params` | JSONB | DEFAULT '{}' | Pattern-specific parameters |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Creation time |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last update |
| `created_by` | VARCHAR(255) | | Pattern creator (user or system) |

**Indexes:**

- `idx_prompt_patterns_category` - Category filtering
- `idx_prompt_patterns_tags` (GIN) - Tag search
- `idx_prompt_patterns_pattern_id` - Pattern lookup

**Design Notes:**

- Patterns are read-only library entries used during use case creation
- After pattern application, prompts belong to the use case (no runtime references)
- 29 patterns seeded from promptingguide.ai covering 8 categories
- See ADR-018 for use case ownership model

---

### `user_use_case_assignments`

User-to-use-case role assignments.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Assignment ID |
| `user_id` | UUID | FK → users(id) ON DELETE CASCADE | User |
| `use_case_id` | UUID | FK → use_cases(id) ON DELETE CASCADE | Use case |
| `assigned_role` | VARCHAR(20) | CHECK | user/developer/corpus_admin/admin |
| `assigned_by_user_id` | UUID | FK → users(id) | Assigner |
| `assigned_at` | TIMESTAMPTZ | DEFAULT NOW() | Assignment time |
| `expires_at` | TIMESTAMPTZ | | Expiration (optional) |
| `status` | VARCHAR(20) | CHECK, DEFAULT 'active' | active/revoked |
| `metadata` | JSONB | DEFAULT '{}' | Assignment context |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Creation time |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last update |

**Constraints:**

- `user_use_case_assignments_unique` - (user_id, use_case_id, assigned_role) UNIQUE

**Indexes:**

- `idx_user_use_case_assignments_user` - (user_id, status)
- `idx_user_use_case_assignments_use_case` - (use_case_id, assigned_role, status)

**RLS:** Enabled - users see own assignments, admins see all

---

## Query History & Threading

### `query_history`

Complete query execution history with metrics.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Query ID |
| `run_id` | VARCHAR(255) | UNIQUE, NOT NULL | Execution run ID |
| `user_id` | UUID | FK → users(id) ON DELETE CASCADE | User |
| `center_id` | VARCHAR(255) | | Organization ID |
| `use_case_id` | UUID | FK → use_cases(id) ON DELETE SET NULL | Use case |
| `use_case_name` | VARCHAR(255) | | Use case name |
| `intent_type` | VARCHAR(50) | | Intent type |
| `query_text` | TEXT | NOT NULL | User query |
| `query_params` | JSONB | | Query parameters |
| `response_text` | TEXT | | LLM response |
| `response_status` | VARCHAR(50) | NOT NULL | success/error/timeout |
| `metrics` | JSONB | | Complete execution metrics |
| `execution_time_ms` | INTEGER | | Total execution time |
| `sources` | JSONB | | Retrieved sources |
| `citations` | JSONB | | Response citations |
| `parent_query_id` | UUID | FK → query_history(id) ON DELETE SET NULL | Parent query (forking) |
| `thread_id` | UUID | | Conversation thread |
| `fork_count` | INTEGER | DEFAULT 0 | Number of forks |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Execution time |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last update |
| `archived_at` | TIMESTAMPTZ | | Archive timestamp |
| `metadata` | JSONB | DEFAULT '{}' | Additional context |

**Indexes:**

- `idx_query_history_user_id` - User queries
- `idx_query_history_center_id` - Organization queries
- `idx_query_history_use_case_id` - Use case analytics
- `idx_query_history_created_at` - Time-series
- `idx_query_history_parent_query_id` - Query forking
- `idx_query_history_thread_id` - Threading
- `idx_query_history_response_status` - Status filtering
- `idx_query_history_query_text_fts` (GIN) - Full-text search

**RLS:** Enabled - users see own queries, admins see all

**Functions:**

- `fork_query(source_query_id UUID, new_user_id UUID) → UUID` - Create forked query

---

### `context_threads`

Conversation threads for multi-turn interactions.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Thread ID |
| `thread_id` | UUID | UNIQUE, DEFAULT gen_random_uuid() | Thread identifier |
| `title` | VARCHAR(500) | | Thread title |
| `description` | TEXT | | Thread description |
| `user_id` | UUID | FK → users(id) ON DELETE CASCADE | Thread owner |
| `center_id` | VARCHAR(255) | | Organization ID |
| `is_active` | BOOLEAN | DEFAULT TRUE | Active status |
| `message_count` | INTEGER | DEFAULT 0 | Message count |
| `first_query_id` | UUID | FK → query_history(id) ON DELETE SET NULL | First message |
| `last_query_id` | UUID | FK → query_history(id) ON DELETE SET NULL | Last message |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Creation time |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last update |
| `archived_at` | TIMESTAMPTZ | | Archive time |
| `metadata` | JSONB | DEFAULT '{}' | Additional context |

**Indexes:**

- `idx_context_threads_user_id` - User threads
- `idx_context_threads_is_active` - Active threads
- `idx_context_threads_created_at` - Time-series

**RLS:** Enabled - users see own threads

---

### `thread_messages`

Ordered messages within conversation threads.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Message ID |
| `thread_id` | UUID | FK → context_threads(id) ON DELETE CASCADE | Thread |
| `query_id` | UUID | FK → query_history(id) ON DELETE CASCADE | Query reference |
| `sequence_number` | INTEGER | NOT NULL | Message order |
| `role` | VARCHAR(50) | CHECK | user/assistant/system |
| `content` | TEXT | NOT NULL | Message content |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Creation time |

**Constraints:**

- `thread_messages_thread_sequence_unique` - (thread_id, sequence_number) UNIQUE
- `role` CHECK - Must be user/assistant/system

**Indexes:**

- `idx_thread_messages_thread_id` - Thread messages
- `idx_thread_messages_query_id` - Query lookup
- `idx_thread_messages_sequence` - (thread_id, sequence_number)

**RLS:** Enabled - users see messages from own threads

---

## Token Tracking

### `token_usage`

LLM token consumption tracking for quota/cost management.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Usage record ID |
| `run_id` | VARCHAR(255) | NOT NULL | Execution run ID |
| `request_id` | VARCHAR(255) | | Request ID |
| `user_id` | UUID | FK → users(id) ON DELETE CASCADE | User |
| `center_id` | VARCHAR(255) | | Organization ID |
| `use_case_id` | UUID | FK → use_cases(id) ON DELETE SET NULL | Use case |
| `use_case_name` | VARCHAR(255) | | Use case name |
| `intent_type` | VARCHAR(50) | | Intent type |
| `model_id` | VARCHAR(255) | NOT NULL | Model identifier |
| `model_provider` | VARCHAR(100) | | Provider (openai/anthropic/etc) |
| `model_version` | VARCHAR(100) | | Model version |
| `tokens_in` | INTEGER | DEFAULT 0 | Input tokens |
| `tokens_out` | INTEGER | DEFAULT 0 | Output tokens |
| `total_tokens` | INTEGER | DEFAULT 0 | Total (auto-calculated) |
| `cost_per_1k_in` | NUMERIC(10,6) | | Input cost per 1K tokens |
| `cost_per_1k_out` | NUMERIC(10,6) | | Output cost per 1K tokens |
| `total_cost` | NUMERIC(10,4) | | Total cost (auto-calculated) |
| `request_type` | VARCHAR(50) | | Request classification |
| `streaming_used` | BOOLEAN | DEFAULT FALSE | Streaming mode used |
| `call_duration_ms` | INTEGER | | API call duration |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Creation time |
| `metadata` | JSONB | DEFAULT '{}' | Additional context |

**Triggers:**

- `token_usage_calculate_totals` - Auto-calculates total_tokens and total_cost

**Indexes:**

- `idx_token_usage_user_id` - User consumption
- `idx_token_usage_center_id` - Organization consumption
- `idx_token_usage_run_id` - Run tracking
- `idx_token_usage_use_case_id` - Use case analytics
- `idx_token_usage_model_id` - Model usage
- `idx_token_usage_created_at` - Time-series
- `idx_token_usage_center_created` - (center_id, created_at) composite
- `idx_token_usage_user_created` - (user_id, created_at) composite

**RLS:** Enabled - users see own usage, admins see all

**Functions:**

- `get_center_usage_summary(center_id, start_date, end_date)` - Center aggregates
- `get_all_centers_usage_summary(start_date, end_date)` - All centers

---

## Tools Platform

### `tools`

MCP tool registry with configuration.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Tool ID |
| `tool_id` | VARCHAR(255) | UNIQUE, NOT NULL | Tool identifier |
| `name` | VARCHAR(255) | NOT NULL | Display name |
| `description` | TEXT | | Tool description |
| `category` | VARCHAR(50) | CHECK | database/vector_db/web_scraping/etc |
| `provider` | VARCHAR(100) | | Provider name |
| `tool_purpose` | VARCHAR(50) | CHECK | retrieval/orchestrator |
| `service_location` | VARCHAR(50) | CHECK | retrieval_service/orchestrator |
| `mcp_server_type` | VARCHAR(50) | CHECK | stdio/sse/http |
| `mcp_command` | TEXT | | Command for stdio servers |
| `mcp_endpoint` | VARCHAR(500) | | Endpoint for http/sse servers |
| `mcp_protocol_version` | VARCHAR(20) | DEFAULT '2024-11-05' | MCP protocol version |
| `capabilities` | JSONB | | Server capabilities |
| `parameters_schema` | JSONB | | Expected parameters |
| `requires_authentication` | BOOLEAN | DEFAULT FALSE | Auth required |
| `authentication_type` | VARCHAR(50) | | api_key/oauth/basic/none |
| `secret_name` | VARCHAR(255) | | Reference to tool_secrets |
| `config_options` | JSONB | | Tool-specific config |
| `timeout_seconds` | INTEGER | DEFAULT 30 | Timeout |
| `rate_limit_per_minute` | INTEGER | | Rate limit |
| `max_concurrent_calls` | INTEGER | DEFAULT 5 | Concurrency limit |
| `is_enabled` | BOOLEAN | DEFAULT FALSE | Enabled status |
| `is_healthy` | BOOLEAN | DEFAULT FALSE | Health status |
| `last_health_check` | TIMESTAMPTZ | | Last health check |
| `health_check_interval_seconds` | INTEGER | DEFAULT 300 | Health check interval |
| `version` | VARCHAR(50) | | Tool version |
| `documentation_url` | VARCHAR(500) | | Documentation URL |
| `tags` | TEXT[] | | Classification tags |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Creation time |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last update |
| `created_by` | UUID | FK → users(id) | Creator |
| `updated_by` | UUID | FK → users(id) | Last updater |

**Constraints:**

- `valid_category` CHECK - Predefined categories
- `valid_tool_purpose` CHECK - retrieval or orchestrator
- `valid_service_location` CHECK - retrieval_service or orchestrator
- `valid_mcp_server_type` CHECK - stdio/sse/http

**Indexes:**

- `idx_tools_category` - Category queries
- `idx_tools_purpose` - Purpose filtering
- `idx_tools_service_location` - Service location
- `idx_tools_enabled` (partial) - Enabled tools only
- `idx_tools_healthy` (partial) - Healthy tools only
- `idx_tools_tool_id` - Tool lookup

**RLS:** Enabled - admins manage all, users view enabled tools they have permission for

---

### `tool_secrets`

Encrypted tool credentials storage.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Secret ID |
| `tool_id` | UUID | FK → tools(id) ON DELETE CASCADE | Tool |
| `secret_name` | VARCHAR(255) | UNIQUE, NOT NULL | Secret identifier |
| `secret_type` | VARCHAR(50) | CHECK | api_key/oauth_token/password/etc |
| `encrypted_value` | BYTEA | NOT NULL | Encrypted secret (pgcrypto) |
| `encryption_key_id` | VARCHAR(100) | NOT NULL | Encryption key used |
| `expires_at` | TIMESTAMPTZ | | Expiration time |
| `is_active` | BOOLEAN | DEFAULT TRUE | Active status |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Creation time |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last update |
| `created_by` | UUID | FK → users(id) | Creator |
| `last_accessed_at` | TIMESTAMPTZ | | Last access time |
| `access_count` | INTEGER | DEFAULT 0 | Access count |

**Constraints:**

- `valid_secret_type` CHECK - Predefined secret types

**Indexes:**

- `idx_tool_secrets_tool_id` - Tool secrets
- `idx_tool_secrets_active` (partial) - Active secrets only
- `idx_tool_secrets_secret_name` - Secret lookup

**RLS:** Enabled - admins only (application-level access)

**Security:**

- Values encrypted using pgcrypto
- Never logged or exposed in queries
- Access count tracked for audit

---

### `tool_health_checks`

Tool health monitoring history.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Health check ID |
| `tool_id` | UUID | FK → tools(id) ON DELETE CASCADE | Tool |
| `status` | VARCHAR(50) | CHECK | online/offline/degraded/unknown |
| `response_time_ms` | FLOAT | | Response time |
| `error_message` | TEXT | | Error details |
| `error_code` | VARCHAR(100) | | Error code |
| `checked_at` | TIMESTAMPTZ | DEFAULT NOW() | Check time |
| `mcp_server_info` | JSONB | | Server info |

**Constraints:**

- `valid_status` CHECK - online/offline/degraded/unknown

**Indexes:**

- `idx_tool_health_tool_id` - Tool health history
- `idx_tool_health_checked_at` - Time-series
- `idx_tool_health_status` - Status queries

---

### `tool_permissions`

Role-based access control for tools.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Permission ID |
| `tool_id` | UUID | FK → tools(id) ON DELETE CASCADE | Tool |
| `role` | VARCHAR(50) | NOT NULL | Role name |
| `can_view` | BOOLEAN | DEFAULT TRUE | View permission |
| `can_use` | BOOLEAN | DEFAULT FALSE | Use permission |
| `can_configure` | BOOLEAN | DEFAULT FALSE | Configure permission |
| `max_calls_per_hour` | INTEGER | | Hourly limit |
| `max_calls_per_day` | INTEGER | | Daily limit |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Creation time |
| `created_by` | UUID | FK → users(id) | Creator |

**Constraints:**

- (tool_id, role) UNIQUE

**Indexes:**

- `idx_tool_permissions_tool_id` - Tool permissions
- `idx_tool_permissions_role` - Role permissions

---

### `tool_invocations`

Complete audit log of tool invocations.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Invocation ID |
| `tool_id` | UUID | FK → tools(id) | Tool |
| `use_case_id` | UUID | FK → use_cases(id) | Use case |
| `run_id` | VARCHAR(255) | | Run identifier |
| `user_id` | UUID | FK → users(id) | User |
| `center_id` | VARCHAR(255) | | Organization ID |
| `tool_name` | VARCHAR(255) | NOT NULL | Tool name |
| `tool_parameters` | JSONB | | Input parameters |
| `status` | VARCHAR(50) | CHECK | success/error/timeout/blocked/rate_limited |
| `response_data` | JSONB | | Response data |
| `error_message` | TEXT | | Error details |
| `started_at` | TIMESTAMPTZ | DEFAULT NOW() | Start time |
| `completed_at` | TIMESTAMPTZ | | Completion time |
| `duration_ms` | FLOAT | | Duration |
| `mcp_protocol_version` | VARCHAR(20) | | MCP version |
| `cost_estimate` | DECIMAL(10,4) | | Cost estimate |

**Constraints:**

- `valid_invocation_status` CHECK - Predefined statuses

**Indexes:**

- `idx_tool_invocations_tool_id` - Tool usage
- `idx_tool_invocations_run_id` - Run tracking
- `idx_tool_invocations_user_id` - User activity
- `idx_tool_invocations_started_at` - Time-series
- `idx_tool_invocations_center_id` (partial) - Organization queries
- `idx_tool_invocations_status` - Status filtering

**RLS:** Enabled - users see own invocations, admins see all

---

## Model Registry

### `models`

LLM and embedding model registry.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Model ID |
| `model_id` | VARCHAR(255) | UNIQUE, NOT NULL | API identifier (e.g., gpt-4o-mini) |
| `name` | VARCHAR(255) | NOT NULL | Display name |
| `provider` | model_provider_enum | NOT NULL | openai/anthropic/local/other |
| `model_type` | model_type_enum | NOT NULL | llm/embedding/reasoning/etc |
| `context_window` | INTEGER | CHECK > 0 | Max context window in tokens |
| `max_input_tokens` | INTEGER | | Max input tokens |
| `max_output_tokens` | INTEGER | | Max output tokens |
| `embedding_dimensions` | INTEGER | | Vector dimensions (for embedding models) |
| `supports_tools` | BOOLEAN | DEFAULT FALSE | Tool calling support |
| `supports_vision` | BOOLEAN | DEFAULT FALSE | Vision support |
| `supports_audio` | BOOLEAN | DEFAULT FALSE | Audio support |
| `is_reasoning_model` | BOOLEAN | DEFAULT FALSE | Reasoning model flag |
| `reasoning_config` | JSONB | DEFAULT '{}' | Reasoning config |
| `typical_latency_ms` | INTEGER | | Typical latency |
| `tokens_per_second` | FLOAT | | Generation speed |
| `input_price_per_million` | DECIMAL(10,6) | CHECK >= 0 | Input price |
| `output_price_per_million` | DECIMAL(10,6) | CHECK >= 0 | Output price |
| `description` | TEXT | | Model description |
| `specialization` | VARCHAR(255) | | Specialization area |
| `version` | VARCHAR(50) | | Model version |
| `release_date` | DATE | | Release date |
| `deprecated` | BOOLEAN | DEFAULT FALSE | Deprecation status |
| `deprecation_date` | DATE | | Deprecation date |
| `default_temperature` | DECIMAL(3,2) | DEFAULT 0.7 | Default temperature |
| `temperature_range` | JSONB | DEFAULT '{"min": 0.0, "max": 2.0}' | Valid temp range |
| `recommended_use_cases` | TEXT[] | | Recommended use cases |
| `api_endpoint` | VARCHAR(512) | | API endpoint |
| `api_config` | JSONB | DEFAULT '{}' | API configuration |
| `is_available` | BOOLEAN | DEFAULT TRUE | Availability status |
| `last_checked_at` | TIMESTAMPTZ | | Last health check |
| `health_status` | VARCHAR(50) | DEFAULT 'unknown' | Health status |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Creation time |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last update |
| `created_by` | UUID | FK → users(id) | Creator |
| `metadata_json` | JSONB | DEFAULT '{}' | Additional metadata |

**Indexes:**

- `idx_models_model_id` - Model lookup
- `idx_models_provider` - Provider queries
- `idx_models_model_type` - Type filtering
- `idx_models_is_available` - Available models
- `idx_models_specialization` - Specialization queries
- `idx_models_deprecated` (partial) - Non-deprecated models

---

### `model_cache`

Caching layer for model metadata from inference server.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Cache entry ID |
| `model_id` | VARCHAR(255) | FK → models(model_id) ON DELETE CASCADE | Model |
| `cache_key` | VARCHAR(255) | NOT NULL | Cache key |
| `cache_data` | JSONB | NOT NULL | Cached data |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Creation time |
| `expires_at` | TIMESTAMPTZ | NOT NULL | Expiration time |

**Constraints:**

- (model_id, cache_key) UNIQUE

**Indexes:**

- `idx_model_cache_expires` - Expiration cleanup
- `idx_model_cache_model_id` - Model cache lookups

---

### `model_configs`

Model configurations with tokenizer settings and pricing associations.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Config ID |
| `model_id` | VARCHAR(100) | UNIQUE, NOT NULL | Model identifier |
| `model_name` | VARCHAR(200) | NOT NULL | Display name |
| `model_provider` | VARCHAR(50) | NOT NULL | Provider |
| `tokenizer_type` | VARCHAR(50) | NOT NULL | Tokenizer type |
| `tokenizer_file_path` | VARCHAR(255) | | Bundled tokenizer path |
| `encoding_name` | VARCHAR(100) | | Encoding name (e.g., cl100k_base) |
| `default_pricing_tier_id` | UUID | FK → pricing_tiers(id) | Default pricing tier |
| `supports_streaming` | BOOLEAN | DEFAULT TRUE | Streaming support |
| `max_context_tokens` | INTEGER | DEFAULT 8192 | Max context |
| `is_active` | BOOLEAN | DEFAULT TRUE | Active status |
| `is_available` | BOOLEAN | DEFAULT TRUE | Availability status |
| `description` | TEXT | | Description |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Creation time |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last update |
| `created_by` | UUID | FK → users(id) | Creator |
| `updated_by` | UUID | FK → users(id) | Last updater |

**Indexes:**

- `idx_model_configs_active` - Active configs
- `idx_model_configs_provider` - Provider queries

---

## Telemetry

### `run_manifests`

PII-free telemetry storage for stateless architecture (ADR-030).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `run_id` | UUID | PK | Run identifier |
| `ts_utc` | TIMESTAMPTZ | DEFAULT NOW() | Timestamp UTC |
| `use_case_id` | TEXT | NOT NULL | Use case ID |
| `template_ver` | TEXT | NOT NULL | Template version |
| `model_name` | TEXT | NOT NULL | Model name |
| `model_version` | TEXT | NOT NULL | Model version |
| `params_hash` | TEXT | NOT NULL | Parameters hash (idempotence) |
| `schema_valid` | BOOLEAN | NOT NULL | Schema validity |
| `conformance` | NUMERIC(4,3) | CHECK [0,1] | Conformance score 0-1 |
| `tool_chain` | TEXT[] | NOT NULL | Tools used |
| `idempotence_ok` | BOOLEAN | NOT NULL | Idempotence check |
| `latency_total_ms` | INTEGER | CHECK >= 0 | Total latency |
| `latency_llm_ms` | INTEGER | CHECK >= 0 | LLM latency |
| `latency_tools_ms` | INTEGER | CHECK >= 0 | Tools latency |
| `tokens_in` | INTEGER | CHECK >= 0 | Input tokens |
| `tokens_out` | INTEGER | CHECK >= 0 | Output tokens |
| `result_kind` | TEXT | CHECK | success/contract_violation/policy_block/error |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Creation time |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last update |

**Constraints:**

- `conformance` CHECK - [0.0, 1.0]
- `result_kind` CHECK - Predefined values

**Indexes:**

- `idx_run_manifests_use_case` - (use_case_id, ts_utc DESC)
- `idx_run_manifests_result` - (result_kind, ts_utc DESC)
- `idx_run_manifests_timestamp` - ts_utc DESC
- `idx_run_manifests_conformance` - conformance DESC

**RLS:** Enabled - users see runs for their use cases

**Design:** No PII stored - enables air-gapped telemetry analysis

---

## Pricing Management

### `pricing_tiers`

LLMaaS pricing tier definitions.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Tier ID |
| `tier_key` | VARCHAR(50) | UNIQUE, NOT NULL | Tier identifier (e.g., XS|Large) |
| `tier_name` | VARCHAR(100) | NOT NULL | Display name |
| `plan_size` | VARCHAR(10) | NOT NULL | XS/S/M/L/XL |
| `model_class` | VARCHAR(50) | NOT NULL | Large/Small/Codestral/Llama |
| `input_rate_per_1m` | DECIMAL(10,2) | NOT NULL | Input rate (KEUR per 1M tokens) |
| `output_rate_per_1m` | DECIMAL(10,2) | NOT NULL | Output rate (KEUR per 1M tokens) |
| `rate_limit_tpm` | INTEGER | NOT NULL | Tokens per minute limit |
| `is_active` | BOOLEAN | DEFAULT TRUE | Active status |
| `is_default` | BOOLEAN | DEFAULT FALSE | Default tier flag |
| `description` | TEXT | | Description |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Creation time |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last update |
| `created_by` | UUID | FK → users(id) | Creator |
| `updated_by` | UUID | FK → users(id) | Last updater |

**Constraints:**

- (plan_size, model_class) UNIQUE

**Indexes:**

- `idx_pricing_tiers_active` - Active tiers
- `idx_pricing_tiers_plan_model` - (plan_size, model_class)

---

### `model_pricing_history`

Per-model, effective-dated pricing records (ADR-046).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() | Record ID |
| `model_id` | UUID | FK → models(id) ON DELETE CASCADE | Target model |
| `input_price_per_million` | DECIMAL(10,6) | NOT NULL | EUR per 1M input tokens |
| `output_price_per_million` | DECIMAL(10,6) | NOT NULL | EUR per 1M output tokens |
| `effective_from` | TIMESTAMPTZ | NOT NULL | Start timestamp (inclusive) |
| `effective_to` | TIMESTAMPTZ | | End timestamp (exclusive, null=current) |
| `changed_by` | UUID | FK → users(id) | Admin user making change |
| `change_reason` | TEXT | | Optional reason |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Creation time |

**Indexes:**

- `idx_model_pricing_history_model_time` - (model_id, effective_from DESC)
- `idx_model_pricing_history_active` - (model_id, effective_from, effective_to)

**Notes:**

- History is immutable; new prices are appended with new `effective_from`.
- The current price is the row where `effective_from <= now()` and
  (`effective_to` is NULL or `now() < effective_to`).

---

### Function: `get_active_model_price(model_uuid UUID, p_as_of TIMESTAMPTZ)`

Returns the active per‑million input/output EUR prices for a model at a
point in time.

Signature:

```sql
RETURNS TABLE (
  input_price_per_million DECIMAL(10,6),
  output_price_per_million DECIMAL(10,6),
  effective_from TIMESTAMPTZ,
  effective_to TIMESTAMPTZ
)
```

Access Pattern:

- Used by cost estimator to compute `cost_per_1k_*` and `total_cost` at
  execution time for `token_usage` records.

---

### `pricing_tier_audit`

Audit trail for pricing tier changes.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Audit record ID |
| `pricing_tier_id` | UUID | FK → pricing_tiers(id) | Tier |
| `action` | VARCHAR(20) | NOT NULL | CREATE/UPDATE/DELETE/ACTIVATE/DEACTIVATE |
| `changed_by` | UUID | FK → users(id) | User who made change |
| `changed_at` | TIMESTAMPTZ | DEFAULT NOW() | Change timestamp |
| `old_values` | JSONB | | Values before change |
| `new_values` | JSONB | | Values after change |
| `change_reason` | TEXT | | Reason for change |

**Indexes:**

- `idx_pricing_audit_tier` - (pricing_tier_id, changed_at DESC)
- `idx_pricing_audit_action` - (action, changed_at DESC)

---

## Intent System

### `intent_categories`

Domain categories for grouping related intent types.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Category ID |
| `category_code` | VARCHAR(50) | UNIQUE, CHECK | UPPERCASE_UNDERSCORE format |
| `display_name` | VARCHAR(100) | NOT NULL | Display name |
| `description` | TEXT | | Description |
| `icon` | VARCHAR(50) | | Material icon name |
| `color` | VARCHAR(20) | | Hex color for UI |
| `is_active` | BOOLEAN | DEFAULT TRUE | Active status |
| `sort_order` | INTEGER | DEFAULT 0 | Display order |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Creation time |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last update |

**Constraints:**

- `ck_intent_categories_code_format` CHECK - Uppercase with underscores

**Indexes:**

- `idx_intent_categories_active` - Active categories
- `idx_intent_categories_sort` - Sort order

---

### `intent_types`

Dynamic intent types with minimal defaults.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Intent ID |
| `intent_code` | VARCHAR(50) | UNIQUE, CHECK | UPPERCASE_UNDERSCORE format |
| `display_name` | VARCHAR(100) | NOT NULL | Display name |
| `description` | TEXT | | Description |
| `category_id` | UUID | FK → intent_categories(id) ON DELETE CASCADE | Category |
| `recommended_model` | VARCHAR(100) | DEFAULT 'mistral-small' | Recommended model |
| `default_temperature_min` | DECIMAL(3,2) | DEFAULT 0.1, CHECK [0,2] | Min temperature |
| `default_temperature_max` | DECIMAL(3,2) | DEFAULT 0.9, CHECK [0,2] | Max temperature |
| `icon` | VARCHAR(50) | DEFAULT 'chat' | Icon name |
| `color` | VARCHAR(20) | DEFAULT '#2196F3' | Hex color |
| `is_active` | BOOLEAN | DEFAULT TRUE | Active status |
| `is_system` | BOOLEAN | DEFAULT FALSE | System intent (cannot delete) |
| `sort_order` | INTEGER | DEFAULT 0 | Display order |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Creation time |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last update |
| `created_by` | UUID | FK → users(id) | Creator |

**Constraints:**

- `ck_intent_types_code_format` CHECK - Uppercase with underscores
- `ck_intent_types_temp_min` CHECK - [0, 2]
- `ck_intent_types_temp_max` CHECK - [0, 2]
- `ck_intent_types_temp_range` CHECK - min <= max

**Indexes:**

- `idx_intent_types_category` - Category queries
- `idx_intent_types_active` - Active intents
- `idx_intent_types_system` - System intents

---

### `intent_usage_logs`

Analytics and monitoring for intent type usage.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Log ID |
| `intent_id` | UUID | FK → intent_types(id) | Intent |
| `user_id` | UUID | FK → users(id) | User |
| `thread_id` | UUID | | Conversation thread |
| `use_case_id` | UUID | FK → use_cases(id) | Use case |
| `execution_time_ms` | INTEGER | | Execution time |
| `model_used` | VARCHAR(100) | | Model used |
| `tokens_used` | INTEGER | | Tokens consumed |
| `success` | BOOLEAN | NOT NULL | Success status |
| `error_message` | TEXT | | Error message |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Creation time |

**Indexes:**

- `idx_intent_usage_intent` - Intent analytics
- `idx_intent_usage_user` - User analytics
- `idx_intent_usage_created` - Time-series
- `idx_intent_usage_success` - Success rate queries

---

## Audit & Security

### `encryption_keys`

Managed encryption keys registry.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Key ID |
| `key_id` | VARCHAR(255) | UNIQUE, NOT NULL | Key identifier |
| `user_id` | UUID | FK → users(id) | Key owner |
| `key_type` | VARCHAR(50) | DEFAULT 'conversation_data' | Key type |
| `algorithm` | VARCHAR(50) | DEFAULT 'AES-256-GCM' | Encryption algorithm |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Creation time |
| `expires_at` | TIMESTAMPTZ | | Expiration time |
| `is_active` | BOOLEAN | DEFAULT TRUE | Active status |
| `rotation_count` | INTEGER | DEFAULT 0 | Rotation count |
| `hsm_key_reference` | VARCHAR(500) | | HSM key reference |
| `metadata` | JSONB | DEFAULT '{}' | Additional metadata |
| `created_by_user_id` | UUID | FK → users(id) | Creator |

**Indexes:**

- `idx_encryption_keys_user` - (user_id, is_active)
- `idx_encryption_keys_active` (partial) - (key_type, is_active) WHERE is_active

**RLS:** Enabled - role-based access

---

### `audit_logs`

Immutable security and operational audit trail.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Log ID |
| `event_time` | TIMESTAMPTZ | DEFAULT NOW() | Event timestamp |
| `actor_user_id` | UUID | FK → users(id) | User who performed action |
| `actor_roles` | TEXT[] | DEFAULT ARRAY[] | User's roles at time of action |
| `action` | VARCHAR(100) | NOT NULL | Action performed |
| `resource_type` | VARCHAR(100) | NOT NULL | Resource type |
| `resource_id` | VARCHAR(255) | | Resource ID |
| `use_case_id` | UUID | FK → use_cases(id) | Related use case |
| `request_id` | VARCHAR(64) | | Request ID |
| `client_ip` | INET | | Client IP address |
| `user_agent` | TEXT | | User agent |
| `success` | BOOLEAN | DEFAULT TRUE | Success status |
| `details` | JSONB | DEFAULT '{}' | Additional details |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Creation time |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last update |

**Indexes:**

- `idx_audit_logs_use_case_time` - (use_case_id, event_time DESC)
- `idx_audit_logs_actor_time` - (actor_user_id, event_time DESC)

**RLS:** Enabled - role-based access (service can insert, admins/developers can read)

---

## Data Types

### Custom ENUMs

```sql
-- Model provider enum
CREATE TYPE model_provider_enum AS ENUM (
    'openai',
    'anthropic',
    'local',
    'other'
);

-- Model type enum
CREATE TYPE model_type_enum AS ENUM (
    'llm',
    'embedding',
    'reasoning',
    'multimodal',
    'vision',
    'audio',
    'other'
);
```

---

## Table Relationships

### Foreign Key Summary

```
users
├─→ refresh_tokens (user_id)
├─→ user_roles (user_id, granted_by)
├─→ use_cases (created_by_user_id, approved_by_user_id, published_by_user_id)
├─→ prompt_templates (created_by_user_id, approved_by_user_id)
├─→ user_use_case_assignments (user_id, assigned_by_user_id)
├─→ query_history (user_id)
├─→ context_threads (user_id)
├─→ token_usage (user_id)
├─→ tools (created_by, updated_by)
├─→ tool_secrets (created_by)
├─→ tool_permissions (created_by)
├─→ tool_invocations (user_id)
├─→ models (created_by)
├─→ model_configs (created_by, updated_by)
├─→ pricing_tiers (created_by, updated_by)
├─→ pricing_tier_audit (changed_by)
├─→ intent_types (created_by)
├─→ intent_usage_logs (user_id)
├─→ encryption_keys (user_id, created_by_user_id)
└─→ audit_logs (actor_user_id)

use_cases
├─→ prompt_templates (use_case_id)
├─→ user_use_case_assignments (use_case_id)
├─→ query_history (use_case_id)
├─→ token_usage (use_case_id)
├─→ tool_invocations (use_case_id)
├─→ intent_usage_logs (use_case_id)
└─→ audit_logs (use_case_id)

documents
└─→ usage_stats (document_id)

query_history
├─→ context_threads (first_query_id, last_query_id)
├─→ thread_messages (query_id)
└─→ query_history (parent_query_id) [self-reference]

context_threads
└─→ thread_messages (thread_id)

tools
├─→ tool_secrets (tool_id)
├─→ tool_health_checks (tool_id)
├─→ tool_permissions (tool_id)
└─→ tool_invocations (tool_id)

pricing_tiers
├─→ model_configs (default_pricing_tier_id)
└─→ pricing_tier_audit (pricing_tier_id)

intent_categories
└─→ intent_types (category_id)

intent_types
├─→ role_intent_permissions (intent_id)
└─→ intent_usage_logs (intent_id)
```

---

**Last Updated:** 2025-10-24
**Maintainer:** AI Operations Platform Team
