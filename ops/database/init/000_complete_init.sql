-- ============================================================================
-- AI Operations Platform - Complete Database Initialization Script
-- ============================================================================
-- Version: 1.3.0
-- Date: 2025-12-10
-- PostgreSQL Version: 17+
--
-- Description:
--   Complete database schema initialization for AI Operations Platform.
--   This script creates all tables, indexes, views, functions, and RLS policies
--   required for the application to function.
--
-- NOTE: This init script includes RBAC V2 schema (ADR-060), Inference Gateway tables (migrations 029-032),
--       and additional migrations: 027 (models.is_hidden), 028 (collections preflight), 035 (query/thread columns)
--
-- For fresh installations: Use this script directly
-- For upgrading existing databases: Use migrations in ops/database/migrations/rbac_v2/
--
-- Last updated: 2025-12-10 (RBAC V2 consolidation + Gateway tables + Migrations 027, 028, 035 integration)
--
-- Prerequisites:
--   - PostgreSQL 17 or higher
--   - Database already created
--   - Sufficient privileges to create extensions, tables, and functions
--
-- Usage:
--   PGPASSWORD=$POSTGRES_PASSWORD psql-17 \
--     -h $POSTGRES_HOST -p $POSTGRES_PORT \
--     -U $POSTGRES_USER -d $POSTGRES_DB \
--     -f scripts/database/init/000_complete_init.sql
--
-- Sections:
--   1. Extensions and Schemas
--   2. Helper Functions
--   3. Enums and Types
--   4. Authentication Tables
--   5. Document Management
--   6. Use Case System
--   7. Query History and Threading
--   8. Token Tracking
--   9. Tools Platform
--   10. Model Registry
--   11. Inference Gateway
--   12. Telemetry
--   13. Pricing Management
--   14. Intent System
--   15. Audit and Security
--   16. Analytics Views
--   17. Analytics Functions
--   18. Indexes
--   19. Row-Level Security Policies
--   20. Triggers
--   21. Seed Data - Default Collection
--   22. Finalization
-- ============================================================================
BEGIN;
-- ============================================================================
-- SECTION 1: EXTENSIONS AND SCHEMAS
-- ============================================================================
-- Enable required PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- Create application schema
CREATE SCHEMA IF NOT EXISTS aio;
-- ============================================================================
-- SECTION 2: HELPER FUNCTIONS
-- ============================================================================
-- Helper to normalize session user roles into a text array
CREATE OR REPLACE FUNCTION aio.current_user_roles() RETURNS text [] LANGUAGE SQL STABLE AS $$
SELECT CASE
        WHEN current_setting('aio.user_roles', true) IS NULL
        OR current_setting('aio.user_roles', true) = '' THEN ARRAY []::text []
        ELSE regexp_split_to_array(
            trim(
                both '{}'
                FROM current_setting('aio.user_roles', true)
            ),
            '\s*,\s*'
        )
    END;
$$;
-- Helper to test if the active session contains a target role
CREATE OR REPLACE FUNCTION aio.user_has_role(target_role text) RETURNS boolean LANGUAGE SQL STABLE AS $$
SELECT target_role = ANY(aio.current_user_roles());
$$;
-- Helper to read the current session user UUID, if available
CREATE OR REPLACE FUNCTION aio.current_user_uuid() RETURNS uuid LANGUAGE SQL STABLE AS $$
SELECT CASE
        WHEN current_setting('aio.user_id', true) IS NULL
        OR current_setting('aio.user_id', true) = '' THEN NULL::uuid
        ELSE NULLIF(
            current_setting('aio.user_id', true),
            ''
        )::uuid
    END;
$$;
-- Helper to update updated_at timestamps
CREATE OR REPLACE FUNCTION aio.touch_updated_at() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN NEW.updated_at := NOW();
RETURN NEW;
END;
$$;
-- Helper for automatic updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column() RETURNS TRIGGER AS $$ BEGIN NEW.updated_at = NOW();
RETURN NEW;
END;
$$ LANGUAGE plpgsql;
COMMENT ON FUNCTION aio.user_has_role IS 'Checks whether the active session includes a given AI Operations Platform role.';
COMMENT ON FUNCTION aio.current_user_roles IS 'Returns all AI Operations Platform roles assigned to the active session as a text array.';
COMMENT ON FUNCTION aio.current_user_uuid IS 'Returns the AI Operations Platform user identifier from the active session, if set.';
-- ============================================================================
-- SECTION 3: ENUMS AND TYPES
-- ============================================================================
-- Model types
DO $$ BEGIN
    CREATE TYPE model_type_enum AS ENUM ('llm', 'embedding', 'reasoning', 'multimodal', 'vision', 'audio', 'other');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
-- Model providers
DO $$ BEGIN
    CREATE TYPE model_provider_enum AS ENUM ('openai', 'anthropic', 'local', 'other');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
-- ============================================================================
-- SECTION 4: AUTHENTICATION TABLES
-- ============================================================================
-- Users table (unified auth)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR UNIQUE NOT NULL,
    full_name VARCHAR,
    email VARCHAR,
    hashed_password VARCHAR NOT NULL,
    role VARCHAR NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    center_id VARCHAR(255),
    -- Organization/center identifier
    user_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ
);
-- Refresh tokens table (unified auth)
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token VARCHAR UNIQUE NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    revoked BOOLEAN DEFAULT FALSE,
    revoked_at TIMESTAMPTZ
);
-- User role membership join table
CREATE TABLE IF NOT EXISTS user_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    granted_by UUID REFERENCES users(id),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW() -- Note: No CHECK constraint on role to allow dynamic custom roles (ADR-041)
    -- Layer 2: Custom use case grouping roles (NOT system roles)
    -- Examples: threat_hunting, incident_response, compliance_monitoring, threat_intelligence
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_roles_unique ON user_roles (user_id, role);
COMMENT ON TABLE users IS 'User authentication and management table';
COMMENT ON TABLE refresh_tokens IS 'JWT refresh token storage for authentication';
COMMENT ON TABLE user_roles IS 'Multi-role membership assignments for AI Operations Platform accounts. Supports dynamic custom roles (ADR-041).';
COMMENT ON COLUMN users.center_id IS 'Organization/center identifier for aggregating usage';
COMMENT ON COLUMN user_roles.role IS 'Layer 2 custom use case grouping roles. Examples: threat_hunting, incident_response, compliance_monitoring, threat_intelligence. NOT for system roles (those are in users.role column).';
COMMENT ON COLUMN user_roles.metadata IS 'Additional context regarding role assignment (reason, ticket, etc).';
-- ============================================================================
-- SECTION 5: DOCUMENT MANAGEMENT
-- ============================================================================
-- Collections table for organizing documents with embedding model consistency
-- Related: ADR-021 Collection-Based Document Management
CREATE TABLE IF NOT EXISTS collections (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    -- Embedding model binding (immutable after creation)
    embedding_model VARCHAR(255) NOT NULL,
    embedding_provider VARCHAR(100) NOT NULL,
    embedding_dimensions INTEGER NOT NULL,
    -- Qdrant mapping
    qdrant_collection_name VARCHAR(255) UNIQUE NOT NULL,
    -- Flags
    is_default BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    is_system_managed BOOLEAN DEFAULT FALSE,
    -- Metadata
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    document_count INTEGER DEFAULT 0,
    -- Preflight configuration (Migration 028)
    preflight_sample_tokens INTEGER NOT NULL DEFAULT 10000 CHECK (
        preflight_sample_tokens BETWEEN 1000 AND 100000
    ),
    preflight_strategies TEXT [] NOT NULL DEFAULT ARRAY ['sentence_paragraph', 'fixed_token', 'sliding_token', 'heading_aware', 'table_aware'],
    auto_chunk_enabled BOOLEAN NOT NULL DEFAULT true,
    -- Constraints
    CONSTRAINT chk_name_format CHECK (name ~ '^[a-z0-9_-]+$'),
    CONSTRAINT chk_dimensions_positive CHECK (embedding_dimensions > 0),
    CONSTRAINT chk_document_count_nonnegative CHECK (document_count >= 0)
);
-- Ensure only one default collection
CREATE UNIQUE INDEX IF NOT EXISTS idx_collections_unique_default ON collections(is_default)
WHERE is_default = TRUE;
-- Index for auto chunking filtering
CREATE INDEX IF NOT EXISTS idx_collections_auto_enabled ON collections(auto_chunk_enabled)
WHERE auto_chunk_enabled = true;
-- Documents table with comprehensive metadata
CREATE TABLE IF NOT EXISTS documents (
    -- Core identification
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Document metadata
    title TEXT NOT NULL,
    source TEXT,
    author TEXT,
    created_at TIMESTAMP WITH TIME ZONE,
    -- Document creation timestamp
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    -- Ingestion timestamp
    ingested_by TEXT,
    -- User or process that ingested the document
    -- File information
    original_file_name TEXT,
    file_type TEXT,
    -- MIME/file type
    file_checksum TEXT,
    -- File hash for deduplication
    file_size INTEGER,
    -- File size in bytes
    -- Content storage (optional compressed version)
    content_compressed BYTEA,
    -- Compressed text version of the document
    -- Collection relationship (required - added in Migration 016)
    collection_id UUID NOT NULL REFERENCES collections(id) ON DELETE RESTRICT,
    -- Embedding configuration (stored at document level, must match collection)
    embedding_model TEXT,
    -- Embedding model used
    embedding_provider TEXT,
    -- Embedding provider or backend
    embedding_dimensions INTEGER,
    -- Number of embedding dimensions
    -- Chunking information (no chunk content stored)
    num_chunks INTEGER,
    -- Number of chunks created during ingestion
    avg_chunk_size_tokens INTEGER,
    -- Average chunk size in tokens (optional)
    -- Classification and organization
    tags TEXT [],
    -- Array of tags for search or categorization
    classification TEXT,
    -- Document classification/type
    -- Status tracking
    status TEXT DEFAULT 'created',
    -- Document state (created, deleted, updated)
    error_message TEXT,
    -- Error description if ingestion failed
    -- Additional metadata
    metadata JSONB DEFAULT '{}',
    -- Additional metadata as needed
    -- Timestamps
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() -- Last update timestamp
);
-- Usage statistics table for retrieval tracking
CREATE TABLE IF NOT EXISTS usage_stats (
    -- Core identification
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Document reference (nullable for tracking without document)
    document_id UUID REFERENCES documents(id) ON DELETE
    SET NULL,
        -- Chunk information (IDs only, no content)
        chunk_ids UUID [],
        -- Array of chunk IDs returned in this query (from vector DB)
        -- Access tracking
        accessed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        -- Timestamp of retrieval/access
        user_id TEXT,
        -- User or process that performed the retrieval
        -- Query information
        query_text TEXT,
        -- The query string (encrypt or redact if sensitive)
        -- Relevancy information (optional)
        relevancy_scores FLOAT [],
        -- Array of relevancy scores, parallel to chunk_ids
        -- Additional metadata
        metadata JSONB DEFAULT '{}',
        -- Additional context about the retrieval
        -- Performance metrics
        average_relevancy FLOAT,
        rag_confidence FLOAT,
        total_results_found INTEGER,
        source_document_count INTEGER,
        -- Run tracking
        run_id UUID -- For tracking specific execution runs
);
COMMENT ON TABLE collections IS 'Document collections with enforced embedding model consistency. See ADR-021.';
COMMENT ON COLUMN collections.embedding_model IS 'Embedding model identifier (immutable after creation)';
COMMENT ON COLUMN collections.embedding_provider IS 'Embedding provider: openai, local, etc.';
COMMENT ON COLUMN collections.embedding_dimensions IS 'Vector dimensions for this collection';
COMMENT ON COLUMN collections.qdrant_collection_name IS 'Qdrant collection name: fc_<name>_<model_hash>';
COMMENT ON COLUMN collections.is_default IS 'System default collection (only one allowed)';
COMMENT ON COLUMN collections.is_system_managed IS 'Protected from deletion if true';
COMMENT ON COLUMN collections.document_count IS 'Cached document count, maintained by trigger';
COMMENT ON COLUMN collections.preflight_sample_tokens IS 'Sample size in tokens for preflight analysis during auto-detection. Range: 1000-100000';
COMMENT ON COLUMN collections.preflight_strategies IS 'List of chunking strategies to test during auto-detection. Core strategies: sentence_paragraph, fixed_token, sliding_token, heading_aware, table_aware';
COMMENT ON COLUMN collections.auto_chunk_enabled IS 'Whether auto-chunking detection is enabled for this collection. If false, users must manually select chunking strategy';
COMMENT ON TABLE documents IS 'Master documents table storing all relevant metadata for each document';
COMMENT ON TABLE usage_stats IS 'Usage statistics table to record each retrieval event';
COMMENT ON COLUMN documents.id IS 'Unique document identifier';
COMMENT ON COLUMN documents.collection_id IS 'Collection this document belongs to (required)';
COMMENT ON COLUMN documents.file_checksum IS 'File hash (for deduplication)';
COMMENT ON COLUMN documents.embedding_model IS 'Embedding model used';
COMMENT ON COLUMN documents.num_chunks IS 'Number of chunks created during ingestion';
COMMENT ON COLUMN documents.status IS 'Document state (e.g. created, deleted, updated)';
COMMENT ON COLUMN usage_stats.chunk_ids IS 'Array of chunk IDs returned in this query (from the vector DB; chunk content is not stored)';
COMMENT ON COLUMN usage_stats.run_id IS 'For tracking specific execution runs';
-- ============================================================================
-- SECTION 6: USE CASE SYSTEM
-- ============================================================================
-- Use cases table
CREATE TABLE IF NOT EXISTS use_cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    use_case_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    intent_type VARCHAR(50) NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    lifecycle_state VARCHAR(20) NOT NULL DEFAULT 'draft',
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    config_json JSONB NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by_user_id UUID REFERENCES users(id),
    approved_by_user_id UUID REFERENCES users(id),
    published_by_user_id UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    approved_at TIMESTAMPTZ,
    published_at TIMESTAMPTZ,
    team_id VARCHAR(100),
    CONSTRAINT use_cases_use_case_id_unique UNIQUE (use_case_id),
    CONSTRAINT use_cases_lifecycle_state_check CHECK (
        lifecycle_state IN ('draft', 'review', 'published', 'archived')
    ),
    -- Config validation constraints
    CONSTRAINT use_cases_config_json_not_empty CHECK (
        config_json IS NOT NULL
        AND config_json != '{}'::jsonb
    ),
    CONSTRAINT use_cases_config_json_structure CHECK (
        config_json ? 'visibility'
        AND config_json ? 'models'
        AND config_json ? 'generation_params'
        AND config_json ? 'rag'
        AND config_json ? 'output_contract'
        AND config_json ? 'telemetry'
        AND config_json ? 'policy'
    ),
    CONSTRAINT use_cases_config_models_llm_not_empty CHECK (
        config_json->'models'->>'llm' IS NOT NULL
        AND config_json->'models'->>'llm' != ''
    ),
    CONSTRAINT use_cases_config_rag_top_k_positive CHECK (
        (config_json->'rag'->>'enabled')::boolean = false
        OR (config_json->'rag'->>'top_k')::integer > 0
    ),
    CONSTRAINT use_cases_config_temperature_range CHECK (
        (config_json->'generation_params'->>'temperature')::float >= 0.0
        AND (config_json->'generation_params'->>'temperature')::float <= 1.0
    ),
    CONSTRAINT use_cases_config_max_tokens_positive CHECK (
        (config_json->'generation_params'->>'max_tokens')::integer > 0
    ),
    CONSTRAINT use_cases_config_similarity_threshold_range CHECK (
        (config_json->'rag'->>'similarity_threshold')::float >= 0.0
        AND (config_json->'rag'->>'similarity_threshold')::float <= 1.0
    ),
    CONSTRAINT use_cases_config_output_format_valid CHECK (
        config_json->'output_contract'->>'format' IN ('text', 'json', 'yaml', 'structured')
    ),
    CONSTRAINT use_cases_config_pii_redaction_valid CHECK (
        config_json->'policy'->>'pii_redaction' IN ('none', 'anonymize', 'redact', 'encrypt')
    ),
    CONSTRAINT use_cases_config_validation_mode_valid CHECK (
        config_json->'output_contract'->>'validation_mode' IN ('best_effort', 'strict')
    )
);
COMMENT ON COLUMN use_cases.team_id IS 'Developer team that owns this use case. Format: team:team_name. Used to isolate draft use cases between teams. NULL for published use cases (visible to all).';
-- Prompt templates table (versioned)
CREATE TABLE IF NOT EXISTS prompt_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id VARCHAR(255) NOT NULL,
    use_case_id UUID REFERENCES use_cases(id) ON DELETE
    SET NULL,
        prompt_type VARCHAR(50) NOT NULL DEFAULT 'system',
        version_number INTEGER NOT NULL DEFAULT 1,
        template_content TEXT NOT NULL,
        variables JSONB NOT NULL DEFAULT '[]'::jsonb,
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
        is_active_version BOOLEAN NOT NULL DEFAULT FALSE,
        deployment_status VARCHAR(20) NOT NULL DEFAULT 'draft',
        created_by_user_id UUID REFERENCES users(id),
        approved_by_user_id UUID REFERENCES users(id),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        approved_at TIMESTAMPTZ,
        CONSTRAINT prompt_templates_unique_version UNIQUE (template_id, version_number)
);
-- Prompt patterns library (reusable prompt engineering patterns)
CREATE TABLE IF NOT EXISTS prompt_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    description TEXT,
    system_prompt_template TEXT,
    developer_prompt_template TEXT,
    fewshots_template JSONB NOT NULL DEFAULT '[]'::jsonb,
    variables JSONB NOT NULL DEFAULT '[]'::jsonb,
    source_url VARCHAR(500),
    tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    use_count INTEGER NOT NULL DEFAULT 0,
    -- Sampling preset recommendation (ADR-023)
    recommended_preset VARCHAR(50) DEFAULT 'balanced',
    max_tokens_override INTEGER,
    special_params JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by VARCHAR(255)
);
-- User-use-case assignments
CREATE TABLE IF NOT EXISTS user_use_case_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    use_case_id UUID NOT NULL REFERENCES use_cases(id) ON DELETE CASCADE,
    assigned_role VARCHAR(20) NOT NULL,
    assigned_by_user_id UUID REFERENCES users(id),
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT user_use_case_assignments_role_check CHECK (
        assigned_role IN ('user', 'developer', 'corpus_admin', 'admin')
    ),
    CONSTRAINT user_use_case_assignments_status_check CHECK (status IN ('active', 'revoked')),
    CONSTRAINT user_use_case_assignments_unique UNIQUE (user_id, use_case_id, assigned_role)
);
COMMENT ON TABLE use_cases IS 'Registered operational use cases available to AI Operations Platform users.';
COMMENT ON COLUMN use_cases.lifecycle_state IS 'Draft/review/published/archived lifecycle gate.';
COMMENT ON COLUMN use_cases.config_json IS 'Parameterization and routing configuration for the use case.';
COMMENT ON TABLE prompt_templates IS 'Versioned prompt templates supporting use-case orchestration.';
COMMENT ON COLUMN prompt_templates.metadata IS 'Supplemental context (inputs schema, notes, etc).';
COMMENT ON TABLE prompt_patterns IS 'Reusable prompt engineering pattern library from promptingguide.ai and custom patterns.';
COMMENT ON COLUMN prompt_patterns.pattern_id IS 'Unique identifier (e.g., chain-of-thought, rag-citations).';
COMMENT ON COLUMN prompt_patterns.fewshots_template IS 'Example input/output pairs for few-shot learning.';
COMMENT ON COLUMN prompt_patterns.variables IS 'Template variable definitions for pattern application.';
COMMENT ON COLUMN prompt_patterns.recommended_preset IS 'Recommended sampling preset (strict/balanced/creative) per ADR-023.';
COMMENT ON COLUMN prompt_patterns.use_count IS 'Analytics: number of times this pattern has been applied to use cases.';
COMMENT ON TABLE user_use_case_assignments IS 'Per-use-case role entitlements for AI Operations Platform users.';
COMMENT ON COLUMN user_use_case_assignments.metadata IS 'Notes such as ticket numbers or scope clarifications.';
-- Role-use-case assignments (ADR-041: Role-based permissions)
CREATE TABLE IF NOT EXISTS role_use_case_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_name VARCHAR(50) NOT NULL,
    use_case_id UUID NOT NULL REFERENCES use_cases(id) ON DELETE CASCADE,
    -- Audit fields
    granted_by UUID REFERENCES users(id),
    granted_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Constraints
    UNIQUE(role_name, use_case_id) -- Note: No CHECK constraint on role_name to allow dynamic custom roles
    -- Role names should match user_roles.role but not enforced at DB level
);
COMMENT ON TABLE role_use_case_assignments IS 'Assigns use cases to grouping roles (Tier 2). Users inherit execution access through role memberships. System roles (Tier 1) should NOT have use cases assigned - they grant capabilities, not resource access. See ADR-041, ADR-060.';
COMMENT ON COLUMN role_use_case_assignments.role_name IS 'Grouping role name (Tier 2). Users with this grouping role can execute assigned use cases. NOT for system roles like admin, developer, user - those grant capabilities, not execution access.';
COMMENT ON COLUMN role_use_case_assignments.is_active IS 'Allows temporary revocation without deletion. Application must check this flag.';
-- Role-collection assignments (ADR-060: RBAC V2)
CREATE TABLE IF NOT EXISTS role_collection_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_name VARCHAR(50) NOT NULL,
    collection_id UUID NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    -- Audit fields
    granted_by UUID REFERENCES users(id),
    granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    -- Constraints
    UNIQUE(role_name, collection_id) -- Note: No CHECK constraint on role_name to allow dynamic custom roles
    -- Role names should match user_roles.role but not enforced at DB level
);
COMMENT ON TABLE role_collection_assignments IS 'Assigns document collections to roles. Users inherit collection access through role memberships. Implements ADR-060 Tier 2 resource access control.';
COMMENT ON COLUMN role_collection_assignments.role_name IS 'Role name (system role or grouping role) that gets access to this collection. Examples: admin, corpus_admin, threat_hunting, incident_response, etc.';
COMMENT ON COLUMN role_collection_assignments.collection_id IS 'Document collection that this role can access.';
COMMENT ON COLUMN role_collection_assignments.is_active IS 'Allows temporary revocation without deletion. Application must check this flag.';
COMMENT ON COLUMN role_collection_assignments.expires_at IS 'Optional expiration timestamp. If NULL, assignment never expires.';
COMMENT ON COLUMN role_collection_assignments.metadata IS 'Additional context regarding assignment (reason, ticket, etc).';
-- ============================================================================
-- SECTION 7: QUERY HISTORY AND THREADING
-- ============================================================================
-- Query History Table
CREATE TABLE IF NOT EXISTS query_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id VARCHAR(255) UNIQUE NOT NULL,
    -- User context
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    center_id VARCHAR(255),
    -- Use case context
    use_case_id UUID REFERENCES use_cases(id) ON DELETE
    SET NULL,
        use_case_name VARCHAR(255),
        intent_type VARCHAR(50),
        -- Query details
        query_text TEXT NOT NULL,
        query_params JSONB,
        -- Response details
        response_text TEXT,
        response_status VARCHAR(50) NOT NULL,
        -- Metrics and metadata
        metrics JSONB,
        processing_time_ms INTEGER,
        -- Sources and citations
        sources JSONB,
        citations JSONB,
        -- Threading and forking
        parent_query_id UUID REFERENCES query_history(id) ON DELETE
    SET NULL,
        thread_id UUID,
        fork_count INTEGER DEFAULT 0,
        -- Audit and lifecycle
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        archived_at TIMESTAMPTZ,
        -- Additional context
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);
-- Context Threads Table
CREATE TABLE IF NOT EXISTS context_threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    -- Thread metadata
    title VARCHAR(500),
    description TEXT,
    -- User context
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    center_id VARCHAR(255),
    -- Thread state
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    message_count INTEGER DEFAULT 0,
    -- Additional context (Migration 035)
    discussion_id VARCHAR(255),
    use_case_id UUID,
    use_case_name VARCHAR(255),
    source VARCHAR(50) NOT NULL DEFAULT 'ui',
    context_size_tokens INTEGER NOT NULL DEFAULT 0,
    max_context_tokens INTEGER NOT NULL DEFAULT 8000,
    auto_compact BOOLEAN NOT NULL DEFAULT TRUE,
    last_activity_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- First and last messages
    first_query_id UUID REFERENCES query_history(id) ON DELETE
    SET NULL,
        last_query_id UUID REFERENCES query_history(id) ON DELETE
    SET NULL,
        -- Audit
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        archived_at TIMESTAMPTZ,
        -- Additional context
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);
-- Thread Messages Table
CREATE TABLE IF NOT EXISTS thread_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Thread association
    thread_id UUID NOT NULL REFERENCES context_threads(id) ON DELETE CASCADE,
    query_id UUID NOT NULL REFERENCES query_history(id) ON DELETE CASCADE,
    -- Message sequence
    sequence_number INTEGER NOT NULL,
    -- Message role and content
    role VARCHAR(50) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Unique constraint: one sequence number per thread
    CONSTRAINT thread_messages_thread_sequence_unique UNIQUE (thread_id, sequence_number)
);
COMMENT ON TABLE query_history IS 'Complete query execution history with metrics, results, and threading support';
COMMENT ON COLUMN query_history.run_id IS 'Unique run identifier matching orchestrator execution';
COMMENT ON COLUMN query_history.parent_query_id IS 'Reference to parent query if this is a fork or follow-up';
COMMENT ON COLUMN query_history.thread_id IS 'Thread identifier for multi-turn conversations';
COMMENT ON COLUMN query_history.metrics IS 'Complete execution metrics (retrieval, guard, model, confidence)';
COMMENT ON COLUMN query_history.processing_time_ms IS 'Total processing time in milliseconds (renamed from execution_time_ms)';
COMMENT ON TABLE context_threads IS 'Conversation threads for multi-turn interactions';
COMMENT ON COLUMN context_threads.discussion_id IS 'External discussion/ticket identifier for correlation';
COMMENT ON COLUMN context_threads.use_case_id IS 'Associated use case UUID';
COMMENT ON COLUMN context_threads.use_case_name IS 'Associated use case name (denormalized)';
COMMENT ON COLUMN context_threads.source IS 'Source of thread creation: ui, api, soar';
COMMENT ON COLUMN context_threads.context_size_tokens IS 'Current context size in tokens';
COMMENT ON COLUMN context_threads.max_context_tokens IS 'Maximum context size before compaction';
COMMENT ON COLUMN context_threads.auto_compact IS 'Whether to automatically compact context when max is reached';
COMMENT ON COLUMN context_threads.last_activity_at IS 'Timestamp of last activity in this thread';
COMMENT ON TABLE thread_messages IS 'Ordered messages within conversation threads';
-- ============================================================================
-- SECTION 8: TOKEN TRACKING
-- ============================================================================
-- Token Usage Table
CREATE TABLE IF NOT EXISTS token_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Request context
    run_id VARCHAR(255) NOT NULL,
    request_id VARCHAR(255),
    -- User and organization context
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    center_id VARCHAR(255),
    -- Use case context
    use_case_id UUID REFERENCES use_cases(id) ON DELETE
    SET NULL,
        use_case_name VARCHAR(255),
        intent_type VARCHAR(50),
        -- Model information
        model_id VARCHAR(255) NOT NULL,
        model_provider VARCHAR(100),
        model_version VARCHAR(100),
        -- Token counts
        tokens_in INTEGER NOT NULL DEFAULT 0,
        tokens_out INTEGER NOT NULL DEFAULT 0,
        total_tokens INTEGER NOT NULL DEFAULT 0,
        -- Cost tracking (optional, can be calculated)
        cost_per_1k_in NUMERIC(10, 6),
        cost_per_1k_out NUMERIC(10, 6),
        total_cost NUMERIC(10, 4),
        -- Request classification
        request_type VARCHAR(50),
        streaming_used BOOLEAN DEFAULT FALSE,
        -- Timing information
        call_duration_ms INTEGER,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        -- Additional metadata
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);
COMMENT ON TABLE token_usage IS 'Tracks all LLM token consumption for quota management and cost analysis';
COMMENT ON COLUMN token_usage.run_id IS 'Unique run identifier matching orchestrator execution';
COMMENT ON COLUMN token_usage.center_id IS 'Organization/center identifier for aggregating usage';
COMMENT ON COLUMN token_usage.total_tokens IS 'Sum of tokens_in and tokens_out';
COMMENT ON COLUMN token_usage.total_cost IS 'Calculated total cost based on per-1k token rates';
COMMENT ON COLUMN token_usage.streaming_used IS 'Whether streaming mode was used for this request';
-- ============================================================================
-- SECTION 9: TOOLS PLATFORM
-- ============================================================================
-- Tools Table
CREATE TABLE IF NOT EXISTS tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL,
    provider VARCHAR(100),
    -- DEPRECATED: Hybrid Architecture (ADR-001)
    -- Kept for backward compatibility during migration
    tool_purpose VARCHAR(50) NOT NULL,
    service_location VARCHAR(50) NOT NULL,
    -- Security Classification (ADR-057)
    data_source_type VARCHAR(20) NOT NULL DEFAULT 'internal',
    data_flow_direction VARCHAR(20) NOT NULL DEFAULT 'ingress',
    network_access_level VARCHAR(20) NOT NULL DEFAULT 'internal',
    max_data_sensitivity VARCHAR(20) NOT NULL DEFAULT 'internal',
    -- MCP Configuration
    mcp_server_type VARCHAR(50) NOT NULL,
    mcp_command TEXT,
    mcp_endpoint VARCHAR(500),
    mcp_protocol_version VARCHAR(20) DEFAULT '2024-11-05',
    -- Capabilities (from MCP server)
    capabilities JSONB,
    parameters_schema JSONB,
    -- Configuration
    requires_authentication BOOLEAN DEFAULT false,
    authentication_type VARCHAR(50),
    secret_name VARCHAR(255),
    config_options JSONB,
    -- Limits & Timeouts
    timeout_seconds INTEGER DEFAULT 30,
    rate_limit_per_minute INTEGER,
    max_concurrent_calls INTEGER DEFAULT 5,
    -- Lifecycle & Status
    is_enabled BOOLEAN DEFAULT false,
    is_healthy BOOLEAN DEFAULT false,
    last_health_check TIMESTAMPTZ,
    health_check_interval_seconds INTEGER DEFAULT 300,
    -- Metadata
    version VARCHAR(50),
    documentation_url VARCHAR(500),
    tags TEXT [],
    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id),
    CONSTRAINT valid_category CHECK (
        category IN (
            'database',
            'vector_db',
            'web_scraping',
            'reasoning',
            'documentation',
            'code_analysis',
            'threat_intel',
            'custom'
        )
    ),
    CONSTRAINT valid_tool_purpose CHECK (tool_purpose IN ('retrieval', 'orchestrator')),
    CONSTRAINT valid_service_location CHECK (
        service_location IN ('retrieval_service', 'orchestrator')
    ),
    CONSTRAINT valid_mcp_server_type CHECK (mcp_server_type IN ('stdio', 'sse', 'http')),
    -- Security classification constraints (ADR-057)
    CONSTRAINT valid_data_source_type CHECK (
        data_source_type IN ('internal', 'external', 'none', 'mixed')
    ),
    CONSTRAINT valid_data_flow_direction CHECK (
        data_flow_direction IN ('ingress', 'egress', 'bidirectional', 'none')
    ),
    CONSTRAINT valid_network_access_level CHECK (
        network_access_level IN ('isolated', 'internal', 'external')
    ),
    CONSTRAINT valid_max_data_sensitivity CHECK (
        max_data_sensitivity IN (
            'public',
            'internal',
            'confidential',
            'restricted'
        )
    )
);
-- Tool Secrets Table
CREATE TABLE IF NOT EXISTS tool_secrets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_id UUID REFERENCES tools(id) ON DELETE CASCADE,
    secret_name VARCHAR(255) UNIQUE NOT NULL,
    secret_type VARCHAR(50) NOT NULL,
    -- Encrypted values (use PostgreSQL pgcrypto)
    encrypted_value BYTEA NOT NULL,
    encryption_key_id VARCHAR(100) NOT NULL,
    -- Lifecycle
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true,
    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    last_accessed_at TIMESTAMPTZ,
    access_count INTEGER DEFAULT 0,
    CONSTRAINT valid_secret_type CHECK (
        secret_type IN (
            'api_key',
            'oauth_token',
            'oauth_refresh_token',
            'password',
            'certificate',
            'custom'
        )
    )
);
-- Tool Health Checks Table
CREATE TABLE IF NOT EXISTS tool_health_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_id UUID REFERENCES tools(id) ON DELETE CASCADE,
    -- Health check results
    status VARCHAR(50) NOT NULL,
    response_time_ms FLOAT,
    error_message TEXT,
    error_code VARCHAR(100),
    -- Details
    checked_at TIMESTAMPTZ DEFAULT NOW(),
    mcp_server_info JSONB,
    CONSTRAINT valid_status CHECK (
        status IN ('online', 'offline', 'degraded', 'unknown')
    )
);
-- Tool Permissions Table
CREATE TABLE IF NOT EXISTS tool_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_id UUID REFERENCES tools(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,
    -- Permissions
    can_view BOOLEAN DEFAULT true,
    can_use BOOLEAN DEFAULT false,
    can_configure BOOLEAN DEFAULT false,
    -- Constraints
    max_calls_per_hour INTEGER,
    max_calls_per_day INTEGER,
    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    UNIQUE(tool_id, role)
);
-- Tool Invocations Table
CREATE TABLE IF NOT EXISTS tool_invocations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_id UUID REFERENCES tools(id),
    use_case_id UUID REFERENCES use_cases(id),
    -- Request context
    run_id VARCHAR(255),
    user_id UUID REFERENCES users(id),
    center_id VARCHAR(255),
    -- Invocation details
    tool_name VARCHAR(255) NOT NULL,
    tool_parameters JSONB,
    -- Result
    status VARCHAR(50) NOT NULL,
    response_data JSONB,
    error_message TEXT,
    -- Performance
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    duration_ms FLOAT,
    -- Metadata
    mcp_protocol_version VARCHAR(20),
    cost_estimate DECIMAL(10, 4),
    CONSTRAINT valid_invocation_status CHECK (
        status IN (
            'success',
            'error',
            'timeout',
            'blocked',
            'rate_limited'
        )
    )
);
COMMENT ON TABLE tools IS 'Platform-level tool configurations for MCP integration';
COMMENT ON TABLE tool_secrets IS 'Encrypted storage for tool API keys and credentials';
COMMENT ON TABLE tool_health_checks IS 'Tool health monitoring history';
COMMENT ON TABLE tool_permissions IS 'Role-based access control for tools';
COMMENT ON TABLE tool_invocations IS 'Complete audit log of tool invocations';
COMMENT ON COLUMN tools.tool_purpose IS 'DEPRECATED (ADR-057): Use data_source_type + data_flow_direction instead';
COMMENT ON COLUMN tools.service_location IS 'DEPRECATED (ADR-057): All MCPs now run in orchestrator';
-- Security classification comments (ADR-057)
COMMENT ON COLUMN tools.data_source_type IS 'ADR-057: Trust level of data sources (internal/external/none/mixed)';
COMMENT ON COLUMN tools.data_flow_direction IS 'ADR-057: Direction of data flow (ingress/egress/bidirectional/none)';
COMMENT ON COLUMN tools.network_access_level IS 'ADR-057: Network access level (isolated/internal/external)';
COMMENT ON COLUMN tools.max_data_sensitivity IS 'ADR-057: Max data classification (public/internal/confidential/restricted)';
COMMENT ON COLUMN tools.mcp_server_type IS 'MCP communication protocol: stdio, sse, or http';
COMMENT ON COLUMN tool_secrets.encrypted_value IS 'Secret encrypted using pgcrypto with application key';
COMMENT ON COLUMN tool_invocations.run_id IS 'Links to query_history for full request context';
-- ============================================================================
-- SECTION 10: MODEL REGISTRY
-- ============================================================================
-- Models Table
CREATE TABLE IF NOT EXISTS models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Basic identification
    model_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    provider_type model_provider_enum NOT NULL,
    provider VARCHAR(255),
    model_type model_type_enum NOT NULL,
    -- Capabilities
    context_window INTEGER,
    max_input_tokens INTEGER,
    max_output_tokens INTEGER,
    embedding_dimensions INTEGER,
    supports_tools BOOLEAN DEFAULT FALSE,
    supports_vision BOOLEAN DEFAULT FALSE,
    supports_audio BOOLEAN DEFAULT FALSE,
    is_reasoning_model BOOLEAN DEFAULT FALSE,
    -- Reasoning model parameters
    reasoning_config JSONB DEFAULT '{}'::jsonb,
    -- Performance characteristics
    typical_latency_ms INTEGER,
    tokens_per_second FLOAT,
    -- Pricing (per 1M tokens)
    input_price_per_million DECIMAL(10, 6),
    output_price_per_million DECIMAL(10, 6),
    -- Additional metadata
    description TEXT,
    specialization VARCHAR(255),
    version VARCHAR(50),
    release_date DATE,
    deprecated BOOLEAN DEFAULT FALSE,
    deprecation_date DATE,
    -- Configuration
    default_temperature DECIMAL(3, 2) DEFAULT 0.7,
    temperature_range JSONB DEFAULT '{"min": 0.0, "max": 2.0}'::jsonb,
    recommended_use_cases TEXT [],
    -- API configuration
    api_endpoint VARCHAR(512),
    api_config JSONB DEFAULT '{}'::jsonb,
    -- Status tracking
    is_available BOOLEAN DEFAULT TRUE,
    last_checked_at TIMESTAMP WITH TIME ZONE,
    health_status VARCHAR(50) DEFAULT 'unknown',
    -- Audit fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(id),
    -- Metadata
    metadata_json JSONB DEFAULT '{}'::jsonb,
    -- Visibility control (Migration 027)
    is_hidden BOOLEAN DEFAULT FALSE NOT NULL,
    CONSTRAINT valid_context_window CHECK (
        context_window IS NULL
        OR context_window > 0
    ),
    CONSTRAINT valid_pricing CHECK (
        (
            input_price_per_million IS NULL
            OR input_price_per_million >= 0
        )
        AND (
            output_price_per_million IS NULL
            OR output_price_per_million >= 0
        )
    )
);
-- Model Pricing History Table (per-model, time-effective pricing records)
CREATE TABLE IF NOT EXISTS model_pricing_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id UUID NOT NULL REFERENCES models(id) ON DELETE CASCADE,
    -- Pricing (per 1M tokens, EUR)
    input_price_per_million DECIMAL(10, 6) NOT NULL,
    output_price_per_million DECIMAL(10, 6) NOT NULL,
    -- Effective window (inclusive start, exclusive end when set)
    effective_from TIMESTAMPTZ NOT NULL,
    effective_to TIMESTAMPTZ,
    -- Audit
    changed_by_user_id UUID REFERENCES users(id) ON DELETE
    SET NULL,
        change_reason TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE model_pricing_history IS 'Historical per-model pricing with effective intervals for immutable cost calculation and auditability.';
COMMENT ON COLUMN model_pricing_history.input_price_per_million IS 'EUR per 1M input tokens effective for the interval.';
COMMENT ON COLUMN model_pricing_history.output_price_per_million IS 'EUR per 1M output tokens effective for the interval.';
COMMENT ON COLUMN model_pricing_history.effective_from IS 'UTC timestamp when this price becomes active (inclusive).';
COMMENT ON COLUMN model_pricing_history.effective_to IS 'UTC timestamp when this price is no longer active (exclusive). NULL = current.';
-- Ensure query performance and uniqueness of window anchors
CREATE UNIQUE INDEX IF NOT EXISTS idx_model_pricing_history_unique_anchor ON model_pricing_history(model_id, effective_from);
CREATE INDEX IF NOT EXISTS idx_model_pricing_history_model_time ON model_pricing_history(
    model_id,
    effective_from,
    COALESCE(effective_to, 'infinity')
);
-- RLS for model_pricing_history (admin/service): admin full; service read
ALTER TABLE model_pricing_history ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS mph_admin_rw ON model_pricing_history;
CREATE POLICY mph_admin_rw ON model_pricing_history FOR ALL USING (aio.user_has_role('admin')) WITH CHECK (aio.user_has_role('admin'));
DROP POLICY IF EXISTS mph_service_read ON model_pricing_history;
CREATE POLICY mph_service_read ON model_pricing_history FOR
SELECT USING (aio.user_has_role('service'));
-- Helper: get active per-1M prices for a model at a point in time
CREATE OR REPLACE FUNCTION get_active_model_price(
        p_model_uuid UUID,
        p_as_of TIMESTAMPTZ DEFAULT NOW()
    ) RETURNS TABLE (
        input_price_per_million DECIMAL(10, 6),
        output_price_per_million DECIMAL(10, 6)
    ) AS $$ BEGIN RETURN QUERY
SELECT h.input_price_per_million,
    h.output_price_per_million
FROM model_pricing_history h
WHERE h.model_id = p_model_uuid
    AND h.effective_from <= p_as_of
    AND (
        h.effective_to IS NULL
        OR h.effective_to > p_as_of
    )
ORDER BY h.effective_from DESC
LIMIT 1;
END;
$$ LANGUAGE plpgsql STABLE;
-- Model Cache Table
CREATE TABLE IF NOT EXISTS model_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id VARCHAR(255) NOT NULL REFERENCES models(model_id) ON DELETE CASCADE,
    cache_key VARCHAR(255) NOT NULL,
    cache_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT unique_model_cache_key UNIQUE(model_id, cache_key)
);
-- Model Configs Table
CREATE TABLE IF NOT EXISTS model_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_id VARCHAR(100) UNIQUE NOT NULL,
    model_name VARCHAR(200) NOT NULL,
    model_provider VARCHAR(50) NOT NULL,
    -- Tokenizer configuration
    tokenizer_type VARCHAR(50) NOT NULL,
    tokenizer_file_path VARCHAR(255),
    encoding_name VARCHAR(100),
    -- Pricing tier association
    default_pricing_tier_id UUID,
    -- Capabilities
    supports_streaming BOOLEAN DEFAULT TRUE,
    max_context_tokens INTEGER DEFAULT 8192,
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_available BOOLEAN DEFAULT TRUE,
    -- Metadata
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id)
);
COMMENT ON TABLE models IS 'Registry of available LLM and embedding models with capabilities';
COMMENT ON COLUMN models.reasoning_config IS 'Configuration for reasoning models (e.g., {"max_thinking_tokens": 10000})';
COMMENT ON COLUMN models.api_config IS 'Provider-specific API configuration';
COMMENT ON COLUMN models.is_hidden IS 'Admin flag to hide models from default view. Hidden models can be shown via "Show Hidden" filter.';
COMMENT ON TABLE model_cache IS 'Caching layer for model metadata from inference server';
-- ============================================================================
-- SECTION 11: INFERENCE GATEWAY
-- ============================================================================
-- Gateway Provider Registry (Migration 029)
-- Create enum for provider types
DO $$ BEGIN CREATE TYPE provider_type AS ENUM (
    'openai',
    'mistral',
    'anthropic',
    'local',
    'custom'
);
EXCEPTION
WHEN duplicate_object THEN NULL;
END $$;
-- Create enum for provider status
DO $$ BEGIN CREATE TYPE provider_status AS ENUM ('active', 'disabled', 'error', 'testing');
EXCEPTION
WHEN duplicate_object THEN NULL;
END $$;
-- Create gateway_providers table
CREATE TABLE IF NOT EXISTS gateway_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) UNIQUE NOT NULL,
    provider_type provider_type NOT NULL,
    base_url TEXT NOT NULL,
    api_key_encrypted TEXT,
    -- Encrypted API key (if needed)
    is_enabled BOOLEAN NOT NULL DEFAULT true,
    status provider_status NOT NULL DEFAULT 'testing',
    priority INTEGER NOT NULL DEFAULT 100,
    -- Lower = higher priority for routing
    config_json JSONB DEFAULT '{}',
    -- Provider-specific configuration
    health_check_url TEXT,
    -- Optional health check endpoint
    last_health_check TIMESTAMPTZ,
    last_health_status BOOLEAN,
    error_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    circuit_state VARCHAR(20) DEFAULT 'CLOSED' CHECK (circuit_state IN ('CLOSED', 'OPEN', 'HALF_OPEN')),
    circuit_opened_at TIMESTAMPTZ,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_gateway_providers_enabled ON gateway_providers(is_enabled)
WHERE is_enabled = true;
CREATE INDEX IF NOT EXISTS idx_gateway_providers_status ON gateway_providers(status);
CREATE INDEX IF NOT EXISTS idx_gateway_providers_type ON gateway_providers(provider_type);
CREATE INDEX IF NOT EXISTS idx_gateway_providers_priority ON gateway_providers(priority)
WHERE is_enabled = true;
CREATE INDEX IF NOT EXISTS idx_gateway_providers_circuit ON gateway_providers(circuit_state);
-- Add trigger for updated_at
CREATE OR REPLACE TRIGGER update_gateway_providers_updated_at BEFORE
UPDATE ON gateway_providers FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
-- Add column comments
COMMENT ON TABLE gateway_providers IS 'Inference Gateway provider registry - manages LLM and embedding provider configurations';
COMMENT ON COLUMN gateway_providers.name IS 'Human-readable provider name (e.g., "OpenAI Production", "Mistral Backup")';
COMMENT ON COLUMN gateway_providers.provider_type IS 'Provider type enum: openai, mistral, anthropic, local, custom';
COMMENT ON COLUMN gateway_providers.base_url IS 'Provider base URL (e.g., https://api.openai.com/v1)';
COMMENT ON COLUMN gateway_providers.api_key_encrypted IS 'Encrypted API key using pgcrypto (decrypt with shared secret)';
COMMENT ON COLUMN gateway_providers.is_enabled IS 'Enable/disable toggle - disabled providers are not used for routing';
COMMENT ON COLUMN gateway_providers.status IS 'Current provider status: active, disabled, error, testing';
COMMENT ON COLUMN gateway_providers.priority IS 'Routing priority (lower = higher priority) for provider selection';
COMMENT ON COLUMN gateway_providers.config_json IS 'Provider-specific configuration (timeout, retries, model mappings, etc.)';
COMMENT ON COLUMN gateway_providers.health_check_url IS 'Optional URL for automated health checks';
COMMENT ON COLUMN gateway_providers.error_count IS 'Cumulative error count for circuit breaker logic';
COMMENT ON COLUMN gateway_providers.success_count IS 'Cumulative success count for health tracking';
COMMENT ON COLUMN gateway_providers.circuit_state IS 'Circuit breaker state: CLOSED (healthy), OPEN (failing), HALF_OPEN (testing)';
COMMENT ON COLUMN gateway_providers.circuit_opened_at IS 'Timestamp when circuit breaker opened (for timeout tracking)';
-- Gateway Usage Log (Migration 030)
CREATE TABLE IF NOT EXISTS gateway_usage_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id VARCHAR(255) NOT NULL,
    -- Correlation ID from X-Request-ID header
    ts_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Request metadata
    user_id UUID REFERENCES users(id),
    -- User making the request (nullable for service accounts)
    integration_id VARCHAR(255),
    -- Integration/service account identifier
    endpoint VARCHAR(100) NOT NULL,
    -- Gateway endpoint hit (e.g., /v1/chat/completions)
    -- Routing information
    provider_id UUID REFERENCES gateway_providers(id),
    -- Provider used for this request
    provider_name VARCHAR(255),
    -- Denormalized provider name for fast queries
    model_requested VARCHAR(255) NOT NULL,
    -- Model requested by client
    model_used VARCHAR(255),
    -- Actual model used (may differ if routing/mapping)
    -- Token usage
    tokens_in INTEGER NOT NULL DEFAULT 0 CHECK (tokens_in >= 0),
    tokens_out INTEGER NOT NULL DEFAULT 0 CHECK (tokens_out >= 0),
    tokens_total INTEGER GENERATED ALWAYS AS (tokens_in + tokens_out) STORED,
    -- Cost tracking
    cost_eur NUMERIC(10, 6) DEFAULT 0.00 CHECK (cost_eur >= 0),
    -- Latency metrics (milliseconds)
    latency_total_ms INTEGER NOT NULL CHECK (latency_total_ms >= 0),
    latency_gateway_ms INTEGER CHECK (latency_gateway_ms >= 0),
    -- Gateway processing overhead
    latency_provider_ms INTEGER CHECK (latency_provider_ms >= 0),
    -- Provider API call latency
    -- Request/response status
    http_status INTEGER NOT NULL,
    -- HTTP status code returned to client
    success BOOLEAN NOT NULL DEFAULT false,
    -- Whether request succeeded
    error_type VARCHAR(100),
    -- Error type if failed (timeout, rate_limit, etc.)
    error_message TEXT,
    -- Error details (sanitized, no secrets)
    -- Additional context
    stream_enabled BOOLEAN DEFAULT false,
    -- Whether streaming was used
    cache_hit BOOLEAN DEFAULT false,
    -- Cache hit (future use)
    retry_count INTEGER DEFAULT 0,
    -- Number of retries attempted
    metadata_json JSONB DEFAULT '{}',
    -- Additional request metadata
    created_at TIMESTAMPTZ DEFAULT NOW()
);
-- Create indexes for query performance
CREATE INDEX IF NOT EXISTS idx_gateway_usage_log_ts_utc ON gateway_usage_log(ts_utc DESC);
CREATE INDEX IF NOT EXISTS idx_gateway_usage_log_user_id ON gateway_usage_log(user_id, ts_utc DESC);
CREATE INDEX IF NOT EXISTS idx_gateway_usage_log_provider_id ON gateway_usage_log(provider_id, ts_utc DESC);
CREATE INDEX IF NOT EXISTS idx_gateway_usage_log_request_id ON gateway_usage_log(request_id);
CREATE INDEX IF NOT EXISTS idx_gateway_usage_log_model ON gateway_usage_log(model_requested, ts_utc DESC);
CREATE INDEX IF NOT EXISTS idx_gateway_usage_log_success ON gateway_usage_log(success, ts_utc DESC);
CREATE INDEX IF NOT EXISTS idx_gateway_usage_log_error_type ON gateway_usage_log(error_type)
WHERE error_type IS NOT NULL;
-- Composite index for analytics queries
CREATE INDEX IF NOT EXISTS idx_gateway_usage_log_analytics ON gateway_usage_log(provider_id, model_requested, ts_utc DESC) INCLUDE (tokens_total, cost_eur, latency_total_ms);
-- Add column comments
COMMENT ON TABLE gateway_usage_log IS 'Inference Gateway usage tracking - logs all requests for analytics, billing, and debugging';
COMMENT ON COLUMN gateway_usage_log.request_id IS 'Correlation ID from X-Request-ID header for distributed tracing';
COMMENT ON COLUMN gateway_usage_log.user_id IS 'User making the request (null for service account requests)';
COMMENT ON COLUMN gateway_usage_log.integration_id IS 'Service account or integration identifier (e.g., "orchestrator", "embedding-service")';
COMMENT ON COLUMN gateway_usage_log.endpoint IS 'Gateway endpoint accessed (e.g., /v1/chat/completions, /v1/embeddings)';
COMMENT ON COLUMN gateway_usage_log.provider_name IS 'Denormalized provider name for fast queries without join';
COMMENT ON COLUMN gateway_usage_log.model_requested IS 'Model requested by client in API call';
COMMENT ON COLUMN gateway_usage_log.model_used IS 'Actual model used after routing/mapping (may differ from requested)';
COMMENT ON COLUMN gateway_usage_log.cost_eur IS 'Total cost in EUR calculated from pricing history';
COMMENT ON COLUMN gateway_usage_log.latency_gateway_ms IS 'Gateway processing overhead (total - provider)';
COMMENT ON COLUMN gateway_usage_log.latency_provider_ms IS 'Provider API call latency (measured at Gateway)';
COMMENT ON COLUMN gateway_usage_log.error_type IS 'Error classification: timeout, rate_limit, auth_failed, provider_error, etc.';
COMMENT ON COLUMN gateway_usage_log.metadata_json IS 'Additional request context: headers, retry info, circuit breaker state, etc.';
-- Gateway Rate Limits (Migration 032)
-- Create enum for rate limit types
DO $$ BEGIN CREATE TYPE rate_limit_type AS ENUM ('global', 'provider', 'integration', 'use_case');
EXCEPTION
WHEN duplicate_object THEN NULL;
END $$;
-- Create gateway_rate_limits table
CREATE TABLE IF NOT EXISTS gateway_rate_limits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    limit_type rate_limit_type NOT NULL,
    identifier TEXT,
    -- NULL for global, 'openai' for provider, 'service:cortex-prod' for integration
    requests_per_minute INTEGER NOT NULL CHECK (requests_per_minute > 0),
    tokens_per_minute BIGINT CHECK (
        tokens_per_minute IS NULL
        OR tokens_per_minute > 0
    ),
    burst_size INTEGER NOT NULL DEFAULT 10 CHECK (burst_size >= 0),
    enabled BOOLEAN NOT NULL DEFAULT true,
    description TEXT,
    -- Human-readable description of this limit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
-- Create unique constraint: only one limit per type+identifier combination
CREATE UNIQUE INDEX IF NOT EXISTS idx_gateway_rate_limits_unique ON gateway_rate_limits(limit_type, COALESCE(identifier, ''));
-- Create indexes for query performance
CREATE INDEX IF NOT EXISTS idx_gateway_rate_limits_type ON gateway_rate_limits(limit_type, enabled)
WHERE enabled = true;
CREATE INDEX IF NOT EXISTS idx_gateway_rate_limits_identifier ON gateway_rate_limits(identifier)
WHERE identifier IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_gateway_rate_limits_enabled ON gateway_rate_limits(enabled)
WHERE enabled = true;
-- Add trigger for updated_at
CREATE OR REPLACE TRIGGER update_gateway_rate_limits_updated_at BEFORE
UPDATE ON gateway_rate_limits FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
-- Add column comments
COMMENT ON TABLE gateway_rate_limits IS 'Inference Gateway rate limit configuration - defines request/token limits for global, provider, and integration levels';
COMMENT ON COLUMN gateway_rate_limits.limit_type IS 'Rate limit scope: global (system-wide), provider (per provider), integration (per service account), use_case (per use case)';
COMMENT ON COLUMN gateway_rate_limits.identifier IS 'Identifier for the limit scope: NULL for global, provider name (e.g., "openai"), integration ID (e.g., "service:cortex-prod"), or use_case_id';
COMMENT ON COLUMN gateway_rate_limits.requests_per_minute IS 'Maximum number of requests allowed per minute for this limit scope';
COMMENT ON COLUMN gateway_rate_limits.tokens_per_minute IS 'Maximum number of tokens (input + output) allowed per minute. NULL means no token limit (only request limit applies)';
COMMENT ON COLUMN gateway_rate_limits.burst_size IS 'Number of requests allowed to burst beyond the RPM limit (allows short spikes without rejection)';
COMMENT ON COLUMN gateway_rate_limits.enabled IS 'Enable/disable toggle - disabled limits are not enforced';
COMMENT ON COLUMN gateway_rate_limits.description IS 'Human-readable description of what this limit protects or controls';
-- ============================================================================
-- SECTION 12: TELEMETRY
-- ============================================================================
-- Run Manifests Table
CREATE TABLE IF NOT EXISTS run_manifests (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ts_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
    use_case_id TEXT NOT NULL,
    template_ver TEXT NOT NULL,
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    params_hash TEXT NOT NULL,
    schema_valid BOOLEAN NOT NULL,
    conformance NUMERIC(4, 3) NOT NULL CHECK (
        conformance >= 0
        AND conformance <= 1
    ),
    tool_chain TEXT [] NOT NULL,
    idempotence_ok BOOLEAN NOT NULL,
    latency_total_ms INTEGER NOT NULL CHECK (latency_total_ms >= 0),
    latency_llm_ms INTEGER NOT NULL CHECK (latency_llm_ms >= 0),
    latency_tools_ms INTEGER NOT NULL CHECK (latency_tools_ms >= 0),
    tokens_in INTEGER NOT NULL CHECK (tokens_in >= 0),
    tokens_out INTEGER NOT NULL CHECK (tokens_out >= 0),
    result_kind TEXT NOT NULL CHECK (
        result_kind IN (
            'success',
            'contract_violation',
            'policy_block',
            'error'
        )
    ),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    gateway_metrics JSONB DEFAULT '{}'::jsonb
);
-- Add GIN index for fast JSONB queries on gateway_metrics
CREATE INDEX IF NOT EXISTS idx_run_manifests_gateway_metrics ON run_manifests USING GIN (gateway_metrics);
COMMENT ON TABLE run_manifests IS 'PII-free telemetry storage for stateless architecture. Contains performance metrics, conformance scores, and execution metadata without conversation content.';
COMMENT ON COLUMN run_manifests.run_id IS 'Unique identifier for this execution run';
COMMENT ON COLUMN run_manifests.conformance IS 'Quality score (0-1) for output conformance to use case requirements';
COMMENT ON COLUMN run_manifests.idempotence_ok IS 'Whether this execution was idempotent (same inputs = same outputs)';
COMMENT ON COLUMN run_manifests.gateway_metrics IS 'Gateway execution metrics captured during request processing. Example structure:
{
  "provider_id": "550e8400-e29b-41d4-a716-446655440000",
  "provider_name": "OpenAI Production",
  "provider_type": "openai",
  "model_requested": "gpt-4o-mini",
  "model_used": "gpt-4o-mini",
  "gateway_latency_ms": 5,
  "provider_latency_ms": 240,
  "tokens_in": 120,
  "tokens_out": 80,
  "cost_eur": 0.00015,
  "routing_decision": "primary",
  "retry_count": 0,
  "cache_hit": false,
  "circuit_state": "CLOSED"
}
This enables correlation between use case execution and provider performance without duplicating data.';
-- ============================================================================
-- SECTION 13: PRICING MANAGEMENT
-- ============================================================================
-- Pricing Tiers Table
CREATE TABLE IF NOT EXISTS pricing_tiers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tier_key VARCHAR(50) UNIQUE NOT NULL,
    tier_name VARCHAR(100) NOT NULL,
    plan_size VARCHAR(10) NOT NULL,
    model_class VARCHAR(50) NOT NULL,
    -- Pricing (per million tokens)
    input_rate_per_1m DECIMAL(10, 2) NOT NULL,
    output_rate_per_1m DECIMAL(10, 2) NOT NULL,
    -- Rate limits
    rate_limit_tpm INTEGER NOT NULL,
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,
    -- Metadata
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id),
    CONSTRAINT unique_plan_model UNIQUE(plan_size, model_class)
);
-- Pricing Tier Audit Table
CREATE TABLE IF NOT EXISTS pricing_tier_audit (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pricing_tier_id UUID REFERENCES pricing_tiers(id),
    action VARCHAR(20) NOT NULL,
    changed_by UUID REFERENCES users(id),
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    -- Snapshot of changes
    old_values JSONB,
    new_values JSONB,
    change_reason TEXT
);
COMMENT ON TABLE pricing_tiers IS 'LLMaaS pricing tier definitions with rate limits and token pricing';
COMMENT ON COLUMN pricing_tiers.tier_key IS 'Unique identifier combining plan size and model class (e.g., XS|Large)';
COMMENT ON COLUMN pricing_tiers.input_rate_per_1m IS 'Input token rate per million tokens in KEUR';
COMMENT ON COLUMN pricing_tiers.output_rate_per_1m IS 'Output token rate per million tokens in KEUR';
COMMENT ON COLUMN pricing_tiers.rate_limit_tpm IS 'Maximum tokens per minute for this tier';
COMMENT ON TABLE pricing_tier_audit IS 'Audit trail for all pricing tier changes with user attribution';
COMMENT ON COLUMN pricing_tier_audit.action IS 'Type of change: CREATE, UPDATE, DELETE, ACTIVATE, DEACTIVATE';
-- Add foreign key for model_configs after pricing_tiers is created
ALTER TABLE model_configs
ADD CONSTRAINT fk_model_configs_pricing_tier FOREIGN KEY (default_pricing_tier_id) REFERENCES pricing_tiers(id);
-- Initialize per-model pricing history from current models table (idempotent)
DO $$ BEGIN
INSERT INTO model_pricing_history (
        model_id,
        input_price_per_million,
        output_price_per_million,
        effective_from,
        change_reason
    )
SELECT m.id,
    COALESCE(m.input_price_per_million, 0),
    COALESCE(m.output_price_per_million, 0),
    NOW(),
    'Initial import from models table during init'
FROM models m
WHERE NOT EXISTS (
        SELECT 1
        FROM model_pricing_history h
        WHERE h.model_id = m.id
    );
END $$;
-- ============================================================================
-- SECTION 14: INTENT SYSTEM
-- ============================================================================
-- Intent Categories Table
CREATE TABLE IF NOT EXISTS intent_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_code VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    icon VARCHAR(50),
    color VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    sort_order INTEGER DEFAULT 0 NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    CONSTRAINT ck_intent_categories_code_format CHECK (category_code ~ '^[A-Z_]+$')
);
-- Intent Types Table
CREATE TABLE IF NOT EXISTS intent_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    intent_code VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    category_id UUID NOT NULL REFERENCES intent_categories(id) ON DELETE CASCADE,
    -- Minimal default configuration
    recommended_model VARCHAR(100) DEFAULT 'mistral-small',
    default_temperature_min DECIMAL(3, 2) DEFAULT 0.1,
    default_temperature_max DECIMAL(3, 2) DEFAULT 0.9,
    -- UI metadata
    icon VARCHAR(50) DEFAULT 'chat',
    color VARCHAR(20) DEFAULT '#2196F3',
    -- Status
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    is_system BOOLEAN DEFAULT FALSE NOT NULL,
    sort_order INTEGER DEFAULT 0 NOT NULL,
    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    created_by UUID REFERENCES users(id),
    CONSTRAINT ck_intent_types_code_format CHECK (intent_code ~ '^[A-Z_]+$'),
    CONSTRAINT ck_intent_types_temp_min CHECK (
        default_temperature_min >= 0
        AND default_temperature_min <= 2
    ),
    CONSTRAINT ck_intent_types_temp_max CHECK (
        default_temperature_max >= 0
        AND default_temperature_max <= 2
    ),
    CONSTRAINT ck_intent_types_temp_range CHECK (
        default_temperature_min <= default_temperature_max
    )
);
-- Intent Usage Logs Table
CREATE TABLE IF NOT EXISTS intent_usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    intent_id UUID NOT NULL REFERENCES intent_types(id),
    user_id UUID NOT NULL REFERENCES users(id),
    thread_id UUID,
    use_case_id UUID REFERENCES use_cases(id),
    execution_time_ms INTEGER,
    model_used VARCHAR(100),
    tokens_used INTEGER,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);
COMMENT ON TABLE intent_categories IS 'Domain categories for grouping related intent types (e.g., SECURITY, LEGAL, HR)';
COMMENT ON TABLE intent_types IS 'Dynamic intent types with minimal defaults (sampling presets). Full configuration in use_cases.config_json. NOT a permission boundary - see ADR-041.';
COMMENT ON COLUMN intent_types.is_system IS 'System intents cannot be deleted via API';
COMMENT ON TABLE intent_usage_logs IS 'Analytics and monitoring for intent type usage';
-- ============================================================================
-- SECTION 15: AUDIT AND SECURITY
-- ============================================================================
-- Encryption Keys Registry
CREATE TABLE IF NOT EXISTS encryption_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_id VARCHAR(255) NOT NULL,
    user_id UUID REFERENCES users(id),
    key_type VARCHAR(50) NOT NULL DEFAULT 'conversation_data',
    algorithm VARCHAR(50) NOT NULL DEFAULT 'AES-256-GCM',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    rotation_count INTEGER NOT NULL DEFAULT 0,
    hsm_key_reference VARCHAR(500),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by_user_id UUID REFERENCES users(id),
    CONSTRAINT encryption_keys_key_id_unique UNIQUE (key_id)
);
-- Audit Logs Table
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor_user_id UUID REFERENCES users(id),
    actor_roles TEXT [] NOT NULL DEFAULT ARRAY []::text [],
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id VARCHAR(255),
    use_case_id UUID REFERENCES use_cases(id),
    request_id VARCHAR(64),
    client_ip INET,
    user_agent TEXT,
    success BOOLEAN NOT NULL DEFAULT TRUE,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE encryption_keys IS 'Tracks managed encryption keys and associated metadata.';
COMMENT ON TABLE audit_logs IS 'Immutable security and operational audit trail.';
-- System Configuration Table (ADR-038: JSONB for config)
CREATE TABLE IF NOT EXISTS system_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    section TEXT NOT NULL UNIQUE CHECK (
        section IN ('corpus', 'auth', 'features', 'system')
    ),
    config JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_by UUID REFERENCES users(id) ON DELETE
    SET NULL
);
-- Index for querying by section (primary access pattern)
CREATE INDEX IF NOT EXISTS idx_system_config_section ON system_config(section);
-- Index for updated_by user (audit queries)
CREATE INDEX IF NOT EXISTS idx_system_config_updated_by ON system_config(updated_by);
-- GIN index for JSONB queries
CREATE INDEX IF NOT EXISTS idx_system_config_config_gin ON system_config USING GIN(config);
-- Seed Default Configuration
INSERT INTO system_config (section, config)
VALUES (
        'corpus',
        '{
        "chunk_size": 512,
        "chunk_overlap": 50,
        "default_embedding_model": "text-embedding-3-small",
        "max_document_size_mb": 50,
        "allowed_file_types": ["pdf", "txt", "docx", "md"]
    }'::jsonb
    ),
    (
        'auth',
        '{
        "session_timeout_minutes": 60,
        "refresh_token_ttl_days": 30,
        "password_policy": {
            "min_length": 8,
            "require_uppercase": true,
            "require_lowercase": true,
            "require_numbers": true,
            "require_special": false
        }
    }'::jsonb
    ),
    (
        'features',
        '{
        "multi_collection_search": false,
        "export_functionality": true,
        "conversation_cache": true,
        "telemetry_enabled": true
    }'::jsonb
    ),
    (
        'system',
        '{
        "log_level": "INFO",
        "max_workers": 4,
        "request_timeout_seconds": 30,
        "enable_debug_endpoints": false
    }'::jsonb
    ) ON CONFLICT (section) DO NOTHING;
-- Update Trigger
CREATE OR REPLACE FUNCTION update_system_config_updated_at() RETURNS TRIGGER AS $$ BEGIN NEW.updated_at = NOW();
RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER trigger_system_config_updated_at BEFORE
UPDATE ON system_config FOR EACH ROW EXECUTE FUNCTION update_system_config_updated_at();
-- Row-Level Security (Admin-Only Access)
ALTER TABLE system_config ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS admin_only_system_config ON system_config;
CREATE POLICY admin_only_system_config ON system_config FOR ALL USING (aio.user_has_role('admin')) WITH CHECK (aio.user_has_role('admin'));
COMMENT ON TABLE system_config IS 'System-wide configuration storage with JSONB (ADR-038)';
COMMENT ON COLUMN system_config.section IS 'Configuration section: corpus, auth, features, or system';
COMMENT ON COLUMN system_config.config IS 'JSONB configuration data for the section';
COMMENT ON COLUMN system_config.updated_by IS 'User who last updated this configuration';
-- ============================================================================
-- SECTION 16: ANALYTICS VIEWS
-- ============================================================================
-- View for hot documents (most frequently accessed)
CREATE OR REPLACE VIEW hot_documents AS
SELECT d.id,
    d.title,
    d.classification,
    d.ingested_at,
    COUNT(us.id) as access_count,
    MAX(us.accessed_at) as last_accessed,
    COUNT(DISTINCT us.user_id) as unique_users
FROM documents d
    LEFT JOIN usage_stats us ON d.id = us.document_id
WHERE us.accessed_at >= NOW() - INTERVAL '30 days'
GROUP BY d.id,
    d.title,
    d.classification,
    d.ingested_at
ORDER BY access_count DESC;
COMMENT ON VIEW hot_documents IS 'View showing most frequently accessed documents in the last 30 days';
-- View for hot chunks (most frequently retrieved chunk IDs)
CREATE OR REPLACE VIEW hot_chunks AS
SELECT chunk_id,
    COUNT(*) as access_count,
    COUNT(DISTINCT us.document_id) as document_count,
    COUNT(DISTINCT us.user_id) as unique_users,
    MAX(us.accessed_at) as last_accessed,
    AVG(relevancy_score) as avg_relevancy
FROM usage_stats us,
    UNNEST(us.chunk_ids) WITH ORDINALITY AS t(chunk_id, pos)
    LEFT JOIN UNNEST(us.relevancy_scores) WITH ORDINALITY AS r(relevancy_score, pos2) ON t.pos = r.pos2
WHERE us.accessed_at >= NOW() - INTERVAL '30 days'
GROUP BY chunk_id
ORDER BY access_count DESC;
COMMENT ON VIEW hot_chunks IS 'View showing most frequently retrieved chunk IDs in the last 30 days';
-- Session context view for RLS
CREATE OR REPLACE VIEW aio.session_context AS
SELECT aio.current_user_uuid() AS user_id,
    aio.current_user_roles() AS roles;
-- ============================================================================
-- SECTION 17: ANALYTICS FUNCTIONS
-- ============================================================================
-- Function to get document access statistics
CREATE OR REPLACE FUNCTION get_document_stats(doc_id UUID, days_back INTEGER DEFAULT 30) RETURNS TABLE (
        total_accesses BIGINT,
        unique_users BIGINT,
        avg_relevancy FLOAT,
        first_access TIMESTAMP WITH TIME ZONE,
        last_access TIMESTAMP WITH TIME ZONE
    ) AS $$ BEGIN RETURN QUERY
SELECT COUNT(us.id)::BIGINT as total_accesses,
    COUNT(DISTINCT us.user_id)::BIGINT as unique_users,
    AVG(
        (
            SELECT AVG(score)
            FROM UNNEST(us.relevancy_scores) AS score
        )
    )::FLOAT as avg_relevancy,
    MIN(us.accessed_at) as first_access,
    MAX(us.accessed_at) as last_access
FROM usage_stats us
WHERE us.document_id = doc_id
    AND us.accessed_at >= NOW() - (days_back || ' days')::INTERVAL;
END;
$$ LANGUAGE plpgsql;
COMMENT ON FUNCTION get_document_stats IS 'Get access statistics for a specific document';
-- Function to get chunk access statistics
CREATE OR REPLACE FUNCTION get_chunk_stats(
        target_chunk_id UUID,
        days_back INTEGER DEFAULT 30
    ) RETURNS TABLE (
        total_accesses BIGINT,
        unique_documents BIGINT,
        unique_users BIGINT,
        avg_relevancy FLOAT,
        first_access TIMESTAMP WITH TIME ZONE,
        last_access TIMESTAMP WITH TIME ZONE
    ) AS $$ BEGIN RETURN QUERY
SELECT COUNT(*)::BIGINT as total_accesses,
    COUNT(DISTINCT us.document_id)::BIGINT as unique_documents,
    COUNT(DISTINCT us.user_id)::BIGINT as unique_users,
    AVG(relevancy_score)::FLOAT as avg_relevancy,
    MIN(us.accessed_at) as first_access,
    MAX(us.accessed_at) as last_access
FROM usage_stats us,
    UNNEST(us.chunk_ids) WITH ORDINALITY AS t(chunk_id, pos)
    LEFT JOIN UNNEST(us.relevancy_scores) WITH ORDINALITY AS r(relevancy_score, pos2) ON t.pos = r.pos2
WHERE t.chunk_id = target_chunk_id
    AND us.accessed_at >= NOW() - (days_back || ' days')::INTERVAL;
END;
$$ LANGUAGE plpgsql;
COMMENT ON FUNCTION get_chunk_stats IS 'Get access statistics for a specific chunk ID';
-- Function: Get center usage summary for a date range
CREATE OR REPLACE FUNCTION get_center_usage_summary(
        p_center_id VARCHAR(255),
        p_start_date TIMESTAMPTZ DEFAULT NOW() - INTERVAL '30 days',
        p_end_date TIMESTAMPTZ DEFAULT NOW()
    ) RETURNS TABLE (
        center_id VARCHAR(255),
        total_requests BIGINT,
        unique_users BIGINT,
        total_tokens_in BIGINT,
        total_tokens_out BIGINT,
        total_tokens BIGINT,
        total_cost NUMERIC,
        avg_tokens_per_request NUMERIC,
        top_models JSONB
    ) LANGUAGE plpgsql SECURITY DEFINER AS $$ BEGIN RETURN QUERY
SELECT tu.center_id,
    COUNT(*)::BIGINT AS total_requests,
    COUNT(DISTINCT tu.user_id)::BIGINT AS unique_users,
    SUM(tu.tokens_in)::BIGINT AS total_tokens_in,
    SUM(tu.tokens_out)::BIGINT AS total_tokens_out,
    SUM(tu.total_tokens)::BIGINT AS total_tokens,
    SUM(tu.total_cost) AS total_cost,
    AVG(tu.total_tokens) AS avg_tokens_per_request,
    jsonb_object_agg(tu.model_id, COUNT(*)) FILTER (
        WHERE tu.model_id IS NOT NULL
    ) AS top_models
FROM token_usage tu
WHERE tu.center_id = p_center_id
    AND tu.created_at >= p_start_date
    AND tu.created_at <= p_end_date
GROUP BY tu.center_id;
END;
$$;
COMMENT ON FUNCTION get_center_usage_summary IS 'Get aggregated token usage summary for a specific center within a date range';
-- Function: Get all centers usage summary for a date range
CREATE OR REPLACE FUNCTION get_all_centers_usage_summary(
        p_start_date TIMESTAMPTZ DEFAULT NOW() - INTERVAL '30 days',
        p_end_date TIMESTAMPTZ DEFAULT NOW()
    ) RETURNS TABLE (
        center_id VARCHAR(255),
        total_requests BIGINT,
        unique_users BIGINT,
        total_tokens_in BIGINT,
        total_tokens_out BIGINT,
        total_tokens BIGINT,
        total_cost NUMERIC,
        avg_tokens_per_request NUMERIC
    ) LANGUAGE plpgsql SECURITY DEFINER AS $$ BEGIN RETURN QUERY
SELECT tu.center_id,
    COUNT(*)::BIGINT AS total_requests,
    COUNT(DISTINCT tu.user_id)::BIGINT AS unique_users,
    SUM(tu.tokens_in)::BIGINT AS total_tokens_in,
    SUM(tu.tokens_out)::BIGINT AS total_tokens_out,
    SUM(tu.total_tokens)::BIGINT AS total_tokens,
    SUM(tu.total_cost) AS total_cost,
    AVG(tu.total_tokens) AS avg_tokens_per_request
FROM token_usage tu
WHERE tu.created_at >= p_start_date
    AND tu.created_at <= p_end_date
    AND tu.center_id IS NOT NULL
GROUP BY tu.center_id
ORDER BY total_tokens DESC;
END;
$$;
COMMENT ON FUNCTION get_all_centers_usage_summary IS 'Get aggregated token usage summary for all centers within a date range';
-- Function to fork a query (create a copy with parent link)
CREATE OR REPLACE FUNCTION fork_query(source_query_id UUID, new_user_id UUID) RETURNS UUID LANGUAGE plpgsql AS $$
DECLARE new_query_id UUID;
source_query RECORD;
BEGIN -- Get source query
SELECT * INTO source_query
FROM query_history
WHERE id = source_query_id;
IF NOT FOUND THEN RAISE EXCEPTION 'Source query not found: %',
source_query_id;
END IF;
-- Create forked query
INSERT INTO query_history (
        run_id,
        user_id,
        center_id,
        use_case_id,
        use_case_name,
        intent_type,
        query_text,
        query_params,
        parent_query_id,
        response_status,
        metadata
    )
VALUES (
        'fork_' || gen_random_uuid()::text,
        new_user_id,
        source_query.center_id,
        source_query.use_case_id,
        source_query.use_case_name,
        source_query.intent_type,
        source_query.query_text,
        source_query.query_params,
        source_query_id,
        'pending',
        jsonb_build_object(
            'forked_from',
            source_query_id,
            'forked_at',
            NOW()
        )
    )
RETURNING id INTO new_query_id;
-- Increment fork count on source
UPDATE query_history
SET fork_count = fork_count + 1
WHERE id = source_query_id;
RETURN new_query_id;
END;
$$;
COMMENT ON FUNCTION fork_query IS 'Creates a forked copy of a query with parent link';
-- Trigger function to calculate total tokens
CREATE OR REPLACE FUNCTION calculate_total_tokens() RETURNS TRIGGER AS $$ BEGIN -- Calculate total tokens if not provided
    IF NEW.total_tokens = 0
    OR NEW.total_tokens IS NULL THEN NEW.total_tokens := NEW.tokens_in + NEW.tokens_out;
END IF;
-- Calculate total cost if rates provided but cost not set
IF NEW.total_cost IS NULL
AND NEW.cost_per_1k_in IS NOT NULL
AND NEW.cost_per_1k_out IS NOT NULL THEN NEW.total_cost := (NEW.tokens_in::NUMERIC / 1000.0) * NEW.cost_per_1k_in + (NEW.tokens_out::NUMERIC / 1000.0) * NEW.cost_per_1k_out;
END IF;
RETURN NEW;
END;
$$ LANGUAGE plpgsql;
COMMENT ON FUNCTION calculate_total_tokens IS 'Automatically calculate total_tokens and total_cost before insert/update';
-- ============================================================================
-- SECTION 18: INDEXES
-- ============================================================================
-- User indexes
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username);
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email)
WHERE email IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_center_id ON users(center_id);
-- Refresh token indexes
CREATE UNIQUE INDEX IF NOT EXISTS ix_refresh_tokens_token ON refresh_tokens (token);
CREATE INDEX IF NOT EXISTS ix_refresh_tokens_user_id ON refresh_tokens (user_id);
-- Collection indexes
CREATE INDEX IF NOT EXISTS idx_collections_name ON collections(name);
CREATE INDEX IF NOT EXISTS idx_collections_active ON collections(is_active)
WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_collections_is_default ON collections(is_default);
CREATE INDEX IF NOT EXISTS idx_collections_embedding_model ON collections(embedding_model);
CREATE INDEX IF NOT EXISTS idx_collections_qdrant_name ON collections(qdrant_collection_name);
CREATE INDEX IF NOT EXISTS idx_collections_created_at ON collections(created_at DESC);
-- Document indexes
CREATE INDEX IF NOT EXISTS idx_documents_collection_id ON documents(collection_id);
CREATE INDEX IF NOT EXISTS idx_documents_ingested_at ON documents (ingested_at);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents (status);
CREATE INDEX IF NOT EXISTS idx_documents_classification ON documents (classification);
CREATE INDEX IF NOT EXISTS idx_documents_embedding_model ON documents (embedding_model);
CREATE INDEX IF NOT EXISTS idx_documents_file_checksum ON documents (file_checksum);
CREATE INDEX IF NOT EXISTS idx_documents_tags ON documents USING gin (tags);
CREATE INDEX IF NOT EXISTS idx_documents_title_search ON documents USING gin (to_tsvector('english', title));
-- Usage stats indexes
CREATE INDEX IF NOT EXISTS idx_usage_stats_document_id ON usage_stats (document_id);
CREATE INDEX IF NOT EXISTS idx_usage_stats_accessed_at ON usage_stats (accessed_at);
CREATE INDEX IF NOT EXISTS idx_usage_stats_user_id ON usage_stats (user_id);
CREATE INDEX IF NOT EXISTS idx_usage_stats_chunk_ids ON usage_stats USING gin (chunk_ids);
-- Use case indexes
CREATE INDEX IF NOT EXISTS idx_use_cases_active ON use_cases (is_active, category);
CREATE INDEX IF NOT EXISTS idx_use_cases_intent ON use_cases (intent_type, lifecycle_state);
CREATE INDEX IF NOT EXISTS idx_use_cases_team_lifecycle ON use_cases(team_id, lifecycle_state);
CREATE INDEX IF NOT EXISTS idx_use_cases_config_models_llm ON use_cases USING btree ((config_json->'models'->>'llm'));
CREATE INDEX IF NOT EXISTS idx_use_cases_config_rag_enabled ON use_cases USING btree ((config_json->'rag'->>'enabled'));
CREATE INDEX IF NOT EXISTS idx_use_cases_config_output_format ON use_cases USING btree ((config_json->'output_contract'->>'format'));
CREATE INDEX IF NOT EXISTS idx_use_cases_config_streaming_enabled ON use_cases USING btree ((config_json->'policy'->>'streaming_enabled'));
CREATE INDEX IF NOT EXISTS idx_use_cases_config_visibility_roles ON use_cases USING GIN ((config_json->'visibility'->'roles'));
CREATE INDEX IF NOT EXISTS idx_use_cases_config_visibility_tags ON use_cases USING GIN ((config_json->'visibility'->'tags'));
-- Prompt template indexes
CREATE INDEX IF NOT EXISTS idx_prompt_templates_active ON prompt_templates (
    template_id,
    is_active_version,
    deployment_status
);
-- Prompt patterns indexes
CREATE INDEX IF NOT EXISTS idx_prompt_patterns_category ON prompt_patterns(category);
CREATE INDEX IF NOT EXISTS idx_prompt_patterns_tags ON prompt_patterns USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_prompt_patterns_pattern_id ON prompt_patterns(pattern_id);
-- User use case assignment indexes
CREATE INDEX IF NOT EXISTS idx_user_use_case_assignments_user ON user_use_case_assignments (user_id, status);
CREATE INDEX IF NOT EXISTS idx_user_use_case_assignments_use_case ON user_use_case_assignments (use_case_id, assigned_role, status);
-- Role use case assignment indexes (ADR-041)
CREATE INDEX IF NOT EXISTS idx_role_use_case_assignments_role ON role_use_case_assignments(role_name, is_active);
CREATE INDEX IF NOT EXISTS idx_role_use_case_assignments_use_case ON role_use_case_assignments(use_case_id, is_active);
CREATE INDEX IF NOT EXISTS idx_role_use_case_assignments_expires ON role_use_case_assignments(expires_at)
WHERE expires_at IS NOT NULL;
-- Role collection assignment indexes (ADR-060: RBAC V2)
CREATE INDEX IF NOT EXISTS idx_role_collection_assignments_role ON role_collection_assignments(role_name, is_active);
CREATE INDEX IF NOT EXISTS idx_role_collection_assignments_collection ON role_collection_assignments(collection_id, is_active);
CREATE INDEX IF NOT EXISTS idx_role_collection_assignments_expires ON role_collection_assignments(expires_at)
WHERE expires_at IS NOT NULL;
-- Query history indexes
CREATE INDEX IF NOT EXISTS idx_query_history_user_id ON query_history(user_id);
CREATE INDEX IF NOT EXISTS idx_query_history_center_id ON query_history(center_id);
CREATE INDEX IF NOT EXISTS idx_query_history_use_case_id ON query_history(use_case_id);
CREATE INDEX IF NOT EXISTS idx_query_history_created_at ON query_history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_query_history_parent_query_id ON query_history(parent_query_id);
CREATE INDEX IF NOT EXISTS idx_query_history_thread_id ON query_history(thread_id);
CREATE INDEX IF NOT EXISTS idx_query_history_response_status ON query_history(response_status);
CREATE INDEX IF NOT EXISTS idx_query_history_query_text_fts ON query_history USING GIN(to_tsvector('english', query_text));
-- Context threads indexes
CREATE INDEX IF NOT EXISTS idx_context_threads_user_id ON context_threads(user_id);
CREATE INDEX IF NOT EXISTS idx_context_threads_is_active ON context_threads(is_active);
CREATE INDEX IF NOT EXISTS idx_context_threads_created_at ON context_threads(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_context_threads_discussion_id ON context_threads(discussion_id);
CREATE INDEX IF NOT EXISTS idx_context_threads_discussion_user ON context_threads(discussion_id, user_id);
CREATE INDEX IF NOT EXISTS idx_context_threads_last_activity_at ON context_threads(last_activity_at DESC);
CREATE INDEX IF NOT EXISTS idx_context_threads_source ON context_threads(source);
-- Thread messages indexes
CREATE INDEX IF NOT EXISTS idx_thread_messages_thread_id ON thread_messages(thread_id);
CREATE INDEX IF NOT EXISTS idx_thread_messages_query_id ON thread_messages(query_id);
CREATE INDEX IF NOT EXISTS idx_thread_messages_sequence ON thread_messages(thread_id, sequence_number);
-- Token usage indexes
CREATE INDEX IF NOT EXISTS idx_token_usage_user_id ON token_usage(user_id);
CREATE INDEX IF NOT EXISTS idx_token_usage_center_id ON token_usage(center_id);
CREATE INDEX IF NOT EXISTS idx_token_usage_run_id ON token_usage(run_id);
CREATE INDEX IF NOT EXISTS idx_token_usage_use_case_id ON token_usage(use_case_id);
CREATE INDEX IF NOT EXISTS idx_token_usage_model_id ON token_usage(model_id);
CREATE INDEX IF NOT EXISTS idx_token_usage_created_at ON token_usage(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_token_usage_center_created ON token_usage(center_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_token_usage_user_created ON token_usage(user_id, created_at DESC);
-- Tools indexes
CREATE INDEX IF NOT EXISTS idx_tools_category ON tools(category);
CREATE INDEX IF NOT EXISTS idx_tools_purpose ON tools(tool_purpose);
CREATE INDEX IF NOT EXISTS idx_tools_service_location ON tools(service_location);
CREATE INDEX IF NOT EXISTS idx_tools_enabled ON tools(is_enabled)
WHERE is_enabled = true;
CREATE INDEX IF NOT EXISTS idx_tools_healthy ON tools(is_healthy)
WHERE is_healthy = true;
CREATE INDEX IF NOT EXISTS idx_tools_tool_id ON tools(tool_id);
-- Security classification indexes (ADR-057)
CREATE INDEX IF NOT EXISTS idx_tools_data_source_type ON tools(data_source_type);
CREATE INDEX IF NOT EXISTS idx_tools_security ON tools(data_source_type, max_data_sensitivity);
-- Tool secrets indexes
CREATE INDEX IF NOT EXISTS idx_tool_secrets_tool_id ON tool_secrets(tool_id);
CREATE INDEX IF NOT EXISTS idx_tool_secrets_active ON tool_secrets(is_active)
WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_tool_secrets_secret_name ON tool_secrets(secret_name);
-- Tool health checks indexes
CREATE INDEX IF NOT EXISTS idx_tool_health_tool_id ON tool_health_checks(tool_id);
CREATE INDEX IF NOT EXISTS idx_tool_health_checked_at ON tool_health_checks(checked_at DESC);
CREATE INDEX IF NOT EXISTS idx_tool_health_status ON tool_health_checks(status);
-- Tool permissions indexes
CREATE INDEX IF NOT EXISTS idx_tool_permissions_tool_id ON tool_permissions(tool_id);
CREATE INDEX IF NOT EXISTS idx_tool_permissions_role ON tool_permissions(role);
-- Tool invocations indexes
CREATE INDEX IF NOT EXISTS idx_tool_invocations_tool_id ON tool_invocations(tool_id);
CREATE INDEX IF NOT EXISTS idx_tool_invocations_run_id ON tool_invocations(run_id);
CREATE INDEX IF NOT EXISTS idx_tool_invocations_user_id ON tool_invocations(user_id);
CREATE INDEX IF NOT EXISTS idx_tool_invocations_started_at ON tool_invocations(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_tool_invocations_center_id ON tool_invocations(center_id)
WHERE center_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_tool_invocations_status ON tool_invocations(status);
-- Models indexes
CREATE INDEX IF NOT EXISTS idx_models_model_id ON models(model_id);
CREATE INDEX IF NOT EXISTS idx_models_provider ON models(provider);
CREATE INDEX IF NOT EXISTS idx_models_model_type ON models(model_type);
CREATE INDEX IF NOT EXISTS idx_models_is_available ON models(is_available);
CREATE INDEX IF NOT EXISTS idx_models_specialization ON models(specialization);
CREATE INDEX IF NOT EXISTS idx_models_deprecated ON models(deprecated)
WHERE deprecated = false;
CREATE INDEX IF NOT EXISTS idx_models_is_hidden ON models(is_hidden);
-- Model cache indexes
CREATE INDEX IF NOT EXISTS idx_model_cache_expires ON model_cache(expires_at);
CREATE INDEX IF NOT EXISTS idx_model_cache_model_id ON model_cache(model_id);
-- Run manifests indexes
CREATE INDEX IF NOT EXISTS idx_run_manifests_use_case ON run_manifests (use_case_id, ts_utc DESC);
CREATE INDEX IF NOT EXISTS idx_run_manifests_result ON run_manifests (result_kind, ts_utc DESC);
CREATE INDEX IF NOT EXISTS idx_run_manifests_timestamp ON run_manifests (ts_utc DESC);
CREATE INDEX IF NOT EXISTS idx_run_manifests_conformance ON run_manifests (conformance DESC);
-- Pricing tiers indexes
CREATE INDEX IF NOT EXISTS idx_pricing_tiers_active ON pricing_tiers(is_active);
CREATE INDEX IF NOT EXISTS idx_pricing_tiers_plan_model ON pricing_tiers(plan_size, model_class);
-- Model configs indexes
CREATE INDEX IF NOT EXISTS idx_model_configs_active ON model_configs(is_active);
CREATE INDEX IF NOT EXISTS idx_model_configs_provider ON model_configs(model_provider);
-- Pricing tier audit indexes
CREATE INDEX IF NOT EXISTS idx_pricing_audit_tier ON pricing_tier_audit(pricing_tier_id, changed_at DESC);
CREATE INDEX IF NOT EXISTS idx_pricing_audit_action ON pricing_tier_audit(action, changed_at DESC);
-- Intent categories indexes
CREATE INDEX IF NOT EXISTS idx_intent_categories_active ON intent_categories(is_active);
CREATE INDEX IF NOT EXISTS idx_intent_categories_sort ON intent_categories(sort_order);
-- Intent types indexes
CREATE INDEX IF NOT EXISTS idx_intent_types_category ON intent_types(category_id);
CREATE INDEX IF NOT EXISTS idx_intent_types_active ON intent_types(is_active);
CREATE INDEX IF NOT EXISTS idx_intent_types_system ON intent_types(is_system);
-- Intent usage logs indexes
CREATE INDEX IF NOT EXISTS idx_intent_usage_intent ON intent_usage_logs(intent_id);
CREATE INDEX IF NOT EXISTS idx_intent_usage_user ON intent_usage_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_intent_usage_created ON intent_usage_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_intent_usage_success ON intent_usage_logs(success);
-- Encryption keys indexes
CREATE INDEX IF NOT EXISTS idx_encryption_keys_user ON encryption_keys (user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_encryption_keys_active ON encryption_keys (key_type, is_active)
WHERE is_active;
-- Audit logs indexes
CREATE INDEX IF NOT EXISTS idx_audit_logs_use_case_time ON audit_logs (use_case_id, event_time DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_actor_time ON audit_logs (actor_user_id, event_time DESC);
-- ============================================================================
-- SECTION 19: ROW-LEVEL SECURITY POLICIES
-- ============================================================================
-- Enable RLS on use_cases
ALTER TABLE use_cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE use_cases FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS use_cases_admin_manage ON use_cases;
CREATE POLICY use_cases_admin_manage ON use_cases USING (aio.user_has_role('admin')) WITH CHECK (aio.user_has_role('admin'));
DROP POLICY IF EXISTS use_cases_developer_rw ON use_cases;
CREATE POLICY use_cases_developer_rw ON use_cases FOR ALL USING (
    aio.user_has_role('developer')
    OR aio.user_has_role('corpus_admin')
    OR aio.user_has_role('service')
) WITH CHECK (
    aio.user_has_role('admin')
    OR (
        aio.user_has_role('developer')
        AND lifecycle_state <> 'published'
    )
);
DROP POLICY IF EXISTS use_cases_user_read ON use_cases;
CREATE POLICY use_cases_user_read ON use_cases FOR
SELECT USING (
        aio.user_has_role('user')
        AND EXISTS (
            SELECT 1
            FROM user_use_case_assignments a
            WHERE a.use_case_id = use_cases.id
                AND a.user_id = aio.current_user_uuid()
                AND a.status = 'active'
        )
    );
-- Enable RLS on prompt_templates
ALTER TABLE prompt_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE prompt_templates FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS prompt_templates_admin_manage ON prompt_templates;
CREATE POLICY prompt_templates_admin_manage ON prompt_templates USING (aio.user_has_role('admin')) WITH CHECK (aio.user_has_role('admin'));
DROP POLICY IF EXISTS prompt_templates_developer_rw ON prompt_templates;
CREATE POLICY prompt_templates_developer_rw ON prompt_templates FOR ALL USING (
    aio.user_has_role('developer')
    OR aio.user_has_role('service')
) WITH CHECK (
    aio.user_has_role('admin')
    OR aio.user_has_role('developer')
);
DROP POLICY IF EXISTS prompt_templates_corpus_view ON prompt_templates;
CREATE POLICY prompt_templates_corpus_view ON prompt_templates FOR
SELECT USING (aio.user_has_role('corpus_admin'));
-- Enable RLS on user_use_case_assignments
ALTER TABLE user_use_case_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_use_case_assignments FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS assignments_admin_manage ON user_use_case_assignments;
CREATE POLICY assignments_admin_manage ON user_use_case_assignments USING (aio.user_has_role('admin')) WITH CHECK (aio.user_has_role('admin'));
DROP POLICY IF EXISTS assignments_corpus_manage ON user_use_case_assignments;
CREATE POLICY assignments_corpus_manage ON user_use_case_assignments FOR ALL USING (aio.user_has_role('corpus_admin')) WITH CHECK (
    aio.user_has_role('corpus_admin')
    OR aio.user_has_role('admin')
);
DROP POLICY IF EXISTS assignments_user_read ON user_use_case_assignments;
CREATE POLICY assignments_user_read ON user_use_case_assignments FOR
SELECT USING (user_id = aio.current_user_uuid());
DROP POLICY IF EXISTS assignments_service_read ON user_use_case_assignments;
CREATE POLICY assignments_service_read ON user_use_case_assignments FOR
SELECT USING (aio.user_has_role('service'));
-- Enable RLS on role_use_case_assignments (ADR-041)
ALTER TABLE role_use_case_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE role_use_case_assignments FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS role_use_case_admin_manage ON role_use_case_assignments;
CREATE POLICY role_use_case_admin_manage ON role_use_case_assignments USING (aio.user_has_role('admin')) WITH CHECK (aio.user_has_role('admin'));
DROP POLICY IF EXISTS role_use_case_service_read ON role_use_case_assignments;
CREATE POLICY role_use_case_service_read ON role_use_case_assignments FOR
SELECT USING (aio.user_has_role('service'));
DROP POLICY IF EXISTS role_use_case_user_read ON role_use_case_assignments;
CREATE POLICY role_use_case_user_read ON role_use_case_assignments FOR
SELECT USING (
        role_name IN (
            SELECT role
            FROM user_roles
            WHERE user_id = aio.current_user_uuid()
        )
    );
DROP POLICY IF EXISTS role_use_case_corpus_admin_manage ON role_use_case_assignments;
CREATE POLICY role_use_case_corpus_admin_manage ON role_use_case_assignments FOR ALL USING (aio.user_has_role('corpus_admin')) WITH CHECK (aio.user_has_role('corpus_admin'));
-- Enable RLS on query_history
ALTER TABLE query_history ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS query_history_user_isolation_policy ON query_history;
CREATE POLICY query_history_user_isolation_policy ON query_history FOR
SELECT USING (
        user_id = aio.current_user_uuid()
        OR aio.user_has_role('admin')
    );
DROP POLICY IF EXISTS query_history_insert_policy ON query_history;
CREATE POLICY query_history_insert_policy ON query_history FOR
INSERT WITH CHECK (user_id = aio.current_user_uuid());
DROP POLICY IF EXISTS query_history_update_policy ON query_history;
CREATE POLICY query_history_update_policy ON query_history FOR
UPDATE USING (
        user_id = aio.current_user_uuid()
        OR aio.user_has_role('admin')
    );
DROP POLICY IF EXISTS query_history_delete_policy ON query_history;
CREATE POLICY query_history_delete_policy ON query_history FOR DELETE USING (aio.user_has_role('admin'));
-- Enable RLS on context_threads
ALTER TABLE context_threads ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS context_threads_user_isolation_policy ON context_threads;
CREATE POLICY context_threads_user_isolation_policy ON context_threads FOR
SELECT USING (
        user_id = aio.current_user_uuid()
        OR aio.user_has_role('admin')
    );
DROP POLICY IF EXISTS context_threads_insert_policy ON context_threads;
CREATE POLICY context_threads_insert_policy ON context_threads FOR
INSERT WITH CHECK (user_id = aio.current_user_uuid());
DROP POLICY IF EXISTS context_threads_update_policy ON context_threads;
CREATE POLICY context_threads_update_policy ON context_threads FOR
UPDATE USING (
        user_id = aio.current_user_uuid()
        OR aio.user_has_role('admin')
    );
-- Enable RLS on thread_messages
ALTER TABLE thread_messages ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS thread_messages_user_isolation_policy ON thread_messages;
CREATE POLICY thread_messages_user_isolation_policy ON thread_messages FOR
SELECT USING (
        thread_id IN (
            SELECT id
            FROM context_threads
            WHERE user_id = aio.current_user_uuid()
        )
        OR aio.user_has_role('admin')
    );
DROP POLICY IF EXISTS thread_messages_insert_policy ON thread_messages;
CREATE POLICY thread_messages_insert_policy ON thread_messages FOR
INSERT WITH CHECK (
        thread_id IN (
            SELECT id
            FROM context_threads
            WHERE user_id = aio.current_user_uuid()
        )
    );
-- Enable RLS on token_usage
ALTER TABLE token_usage ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS token_usage_admin_all_policy ON token_usage;
CREATE POLICY token_usage_admin_all_policy ON token_usage FOR ALL USING (aio.user_has_role('admin'));
DROP POLICY IF EXISTS token_usage_user_read_policy ON token_usage;
CREATE POLICY token_usage_user_read_policy ON token_usage FOR
SELECT USING (user_id = aio.current_user_uuid());
DROP POLICY IF EXISTS token_usage_service_insert_policy ON token_usage;
CREATE POLICY token_usage_service_insert_policy ON token_usage FOR
INSERT WITH CHECK (
        aio.user_has_role('service')
        OR aio.user_has_role('admin')
    );
-- Enable RLS on tools
ALTER TABLE tools ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS admin_all_tools ON tools;
CREATE POLICY admin_all_tools ON tools FOR ALL USING (
    EXISTS (
        SELECT 1
        FROM users u
        WHERE u.id = current_setting('app.user_id')::UUID
            AND u.role = 'admin'
    )
);
DROP POLICY IF EXISTS users_view_enabled_tools ON tools;
CREATE POLICY users_view_enabled_tools ON tools FOR
SELECT USING (
        is_enabled = true
        AND EXISTS (
            SELECT 1
            FROM tool_permissions tp,
                users u
            WHERE tp.tool_id = tools.id
                AND u.id = current_setting('app.user_id')::UUID
                AND tp.role = u.role
                AND tp.can_view = true
        )
    );
-- Enable RLS on tool_secrets
ALTER TABLE tool_secrets ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS secrets_admin_only ON tool_secrets;
CREATE POLICY secrets_admin_only ON tool_secrets FOR ALL USING (
    EXISTS (
        SELECT 1
        FROM users u
        WHERE u.id = current_setting('app.user_id')::UUID
            AND u.role = 'admin'
    )
);
-- Enable RLS on tool_invocations
ALTER TABLE tool_invocations ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS users_view_own_invocations ON tool_invocations;
CREATE POLICY users_view_own_invocations ON tool_invocations FOR
SELECT USING (user_id = current_setting('app.user_id')::UUID);
DROP POLICY IF EXISTS admin_view_all_invocations ON tool_invocations;
CREATE POLICY admin_view_all_invocations ON tool_invocations FOR
SELECT USING (
        EXISTS (
            SELECT 1
            FROM users u
            WHERE u.id = current_setting('app.user_id')::UUID
                AND u.role = 'admin'
        )
    );
-- Enable RLS on run_manifests
ALTER TABLE run_manifests ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS run_manifests_access_policy ON run_manifests;
CREATE POLICY run_manifests_access_policy ON run_manifests FOR ALL USING (
    use_case_id IN (
        SELECT use_case_id
        FROM use_cases
        WHERE created_by_user_id = aio.current_user_uuid()
    )
);
-- Enable RLS on encryption_keys
ALTER TABLE encryption_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE encryption_keys FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS encryption_keys_admin_manage ON encryption_keys;
CREATE POLICY encryption_keys_admin_manage ON encryption_keys USING (aio.user_has_role('admin')) WITH CHECK (aio.user_has_role('admin'));
DROP POLICY IF EXISTS encryption_keys_corpus_manage ON encryption_keys;
CREATE POLICY encryption_keys_corpus_manage ON encryption_keys FOR ALL USING (aio.user_has_role('corpus_admin')) WITH CHECK (
    aio.user_has_role('corpus_admin')
    OR aio.user_has_role('admin')
);
DROP POLICY IF EXISTS encryption_keys_developer_read ON encryption_keys;
CREATE POLICY encryption_keys_developer_read ON encryption_keys FOR
SELECT USING (aio.user_has_role('developer'));
DROP POLICY IF EXISTS encryption_keys_service_read ON encryption_keys;
CREATE POLICY encryption_keys_service_read ON encryption_keys FOR
SELECT USING (aio.user_has_role('service'));
-- Enable RLS on audit_logs
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS audit_logs_service_insert ON audit_logs;
CREATE POLICY audit_logs_service_insert ON audit_logs FOR
INSERT WITH CHECK (
        aio.user_has_role('service')
        OR aio.user_has_role('admin')
    );
DROP POLICY IF EXISTS audit_logs_admin_read ON audit_logs;
CREATE POLICY audit_logs_admin_read ON audit_logs FOR
SELECT USING (aio.user_has_role('admin'));
DROP POLICY IF EXISTS audit_logs_developer_read ON audit_logs;
CREATE POLICY audit_logs_developer_read ON audit_logs FOR
SELECT USING (aio.user_has_role('developer'));
DROP POLICY IF EXISTS audit_logs_corpus_read ON audit_logs;
CREATE POLICY audit_logs_corpus_read ON audit_logs FOR
SELECT USING (
        aio.user_has_role('corpus_admin')
        AND (
            use_case_id IS NULL
            OR EXISTS (
                SELECT 1
                FROM user_use_case_assignments a
                WHERE a.use_case_id = audit_logs.use_case_id
                    AND a.user_id = aio.current_user_uuid()
                    AND a.assigned_role = 'corpus_admin'
                    AND a.status = 'active'
            )
        )
    );
-- ============================================================================
-- SECTION 20: TRIGGERS
-- ============================================================================
-- Collections updated_at trigger
CREATE OR REPLACE FUNCTION update_collections_updated_at() RETURNS TRIGGER AS $$ BEGIN NEW.updated_at = NOW();
RETURN NEW;
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS trigger_collections_updated_at ON collections;
CREATE TRIGGER trigger_collections_updated_at BEFORE
UPDATE ON collections FOR EACH ROW EXECUTE FUNCTION update_collections_updated_at();
-- Collection document count trigger
CREATE OR REPLACE FUNCTION update_collection_document_count() RETURNS TRIGGER AS $$ BEGIN IF TG_OP = 'INSERT' THEN -- Increment count for new document's collection
UPDATE collections
SET document_count = document_count + 1
WHERE id = NEW.collection_id;
RETURN NEW;
ELSIF TG_OP = 'DELETE' THEN -- Decrement count for deleted document's collection
UPDATE collections
SET document_count = document_count - 1
WHERE id = OLD.collection_id;
RETURN OLD;
ELSIF TG_OP = 'UPDATE'
AND OLD.collection_id != NEW.collection_id THEN -- Document moved between collections
UPDATE collections
SET document_count = document_count - 1
WHERE id = OLD.collection_id;
UPDATE collections
SET document_count = document_count + 1
WHERE id = NEW.collection_id;
RETURN NEW;
END IF;
RETURN NEW;
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS trigger_update_collection_document_count ON documents;
CREATE TRIGGER trigger_update_collection_document_count
AFTER
INSERT
    OR DELETE
    OR
UPDATE OF collection_id ON documents FOR EACH ROW EXECUTE FUNCTION update_collection_document_count();
-- Use cases updated_at trigger
DROP TRIGGER IF EXISTS trg_use_cases_touch_updated ON use_cases;
CREATE TRIGGER trg_use_cases_touch_updated BEFORE
UPDATE ON use_cases FOR EACH ROW EXECUTE FUNCTION aio.touch_updated_at();
-- Prompt templates updated_at trigger
DROP TRIGGER IF EXISTS trg_prompt_templates_touch_updated ON prompt_templates;
CREATE TRIGGER trg_prompt_templates_touch_updated BEFORE
UPDATE ON prompt_templates FOR EACH ROW EXECUTE FUNCTION aio.touch_updated_at();
-- Prompt patterns updated_at trigger
DROP TRIGGER IF EXISTS trg_prompt_patterns_touch_updated ON prompt_patterns;
CREATE TRIGGER trg_prompt_patterns_touch_updated BEFORE
UPDATE ON prompt_patterns FOR EACH ROW EXECUTE FUNCTION aio.touch_updated_at();
-- Role collection assignments updated_at trigger (ADR-060: RBAC V2)
CREATE OR REPLACE FUNCTION update_role_collection_assignments_updated_at() RETURNS TRIGGER AS $$ BEGIN NEW.updated_at = NOW();
RETURN NEW;
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS trg_role_collection_assignments_updated_at ON role_collection_assignments;
CREATE TRIGGER trg_role_collection_assignments_updated_at BEFORE
UPDATE ON role_collection_assignments FOR EACH ROW EXECUTE FUNCTION update_role_collection_assignments_updated_at();
-- Query history updated_at trigger
CREATE TRIGGER update_query_history_updated_at BEFORE
UPDATE ON query_history FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
-- Context threads updated_at trigger
CREATE TRIGGER update_context_threads_updated_at BEFORE
UPDATE ON context_threads FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
-- Token usage automatic calculation trigger
CREATE TRIGGER token_usage_calculate_totals BEFORE
INSERT
    OR
UPDATE ON token_usage FOR EACH ROW EXECUTE FUNCTION calculate_total_tokens();
-- Tools updated_at trigger
CREATE TRIGGER tools_updated_at BEFORE
UPDATE ON tools FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
-- Tool secrets updated_at trigger
CREATE TRIGGER tool_secrets_updated_at BEFORE
UPDATE ON tool_secrets FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
-- Models updated_at trigger
CREATE TRIGGER update_models_updated_at BEFORE
UPDATE ON models FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
-- Run manifests updated_at trigger
CREATE OR REPLACE FUNCTION update_run_manifests_updated_at() RETURNS TRIGGER AS $$ BEGIN NEW.updated_at = now();
RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER trigger_update_run_manifests_updated_at BEFORE
UPDATE ON run_manifests FOR EACH ROW EXECUTE FUNCTION update_run_manifests_updated_at();
-- Intent categories updated_at trigger
CREATE OR REPLACE FUNCTION update_intent_types_updated_at() RETURNS TRIGGER AS $$ BEGIN NEW.updated_at = NOW();
RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER trg_intent_categories_updated_at BEFORE
UPDATE ON intent_categories FOR EACH ROW EXECUTE FUNCTION update_intent_types_updated_at();
-- Intent types updated_at trigger
CREATE TRIGGER trg_intent_types_updated_at BEFORE
UPDATE ON intent_types FOR EACH ROW EXECUTE FUNCTION update_intent_types_updated_at();
-- Role use case assignments updated_at trigger (ADR-041)
CREATE OR REPLACE FUNCTION update_role_use_case_assignments_updated_at() RETURNS TRIGGER AS $$ BEGIN NEW.updated_at = NOW();
RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER trg_role_use_case_assignments_updated_at BEFORE
UPDATE ON role_use_case_assignments FOR EACH ROW EXECUTE FUNCTION update_role_use_case_assignments_updated_at();
-- ============================================================================
-- SECTION 21: SEED DATA - DEFAULT COLLECTION
-- ============================================================================
-- Insert system default collection with safe defaults
-- This ensures at least one collection exists for document uploads
INSERT INTO collections (
        name,
        description,
        embedding_model,
        embedding_provider,
        embedding_dimensions,
        qdrant_collection_name,
        is_default,
        is_system_managed,
        is_active,
        created_by
    )
VALUES (
        'default',
        'System default collection for general-purpose documents. Created automatically during system initialization.',
        'all-MiniLM-L6-v2',
        -- Default sentence-transformers model
        'sentence-transformers',
        384,
        -- all-MiniLM-L6-v2 dimensions
        'documents_test',
        TRUE,
        -- is_default
        TRUE,
        -- is_system_managed (protected from deletion)
        TRUE,
        -- is_active
        'system'
    ) ON CONFLICT (name) DO NOTHING;
-- ============================================================================
-- SECTION 22: FINALIZATION
-- ============================================================================
COMMIT;
-- ============================================================================
-- Completion Message
-- ============================================================================
DO $$ BEGIN RAISE NOTICE '✅ AI Operations Platform Database Initialized Successfully!';
RAISE NOTICE '';
RAISE NOTICE '📊 Database Schema Summary:';
RAISE NOTICE '   - Extensions: pgcrypto, uuid-ossp';
RAISE NOTICE '   - Schemas: public, aio';
RAISE NOTICE '   - Authentication: users, refresh_tokens, user_roles';
RAISE NOTICE '   - Documents: documents, usage_stats';
RAISE NOTICE '   - Use Cases: use_cases, prompt_templates, prompt_patterns, user_use_case_assignments, role_use_case_assignments';
RAISE NOTICE '   - Query History: query_history, context_threads, thread_messages';
RAISE NOTICE '   - Token Tracking: token_usage';
RAISE NOTICE '   - Tools: tools, tool_secrets, tool_health_checks, tool_permissions, tool_invocations';
RAISE NOTICE '   - Models: models, model_cache, model_configs';
RAISE NOTICE '   - Telemetry: run_manifests';
RAISE NOTICE '   - Pricing: pricing_tiers, pricing_tier_audit';
RAISE NOTICE '   - Intents: intent_categories, intent_types, intent_usage_logs';
RAISE NOTICE '   - Security: encryption_keys, audit_logs, system_config';
RAISE NOTICE '   - Analytics: hot_documents, hot_chunks views + 6 functions';
RAISE NOTICE '';
RAISE NOTICE '🔒 Row-Level Security (RLS): Enabled on all sensitive tables';
RAISE NOTICE '📈 Indexes: Performance-optimized with GIN, BTREE, and composite indexes';
RAISE NOTICE '';
RAISE NOTICE '⏭️  Next Steps:';
RAISE NOTICE '   1. Run seed scripts from scripts/database/seed/';
RAISE NOTICE '   2. Review RLS policies for your deployment';
RAISE NOTICE '   3. Configure connection pooling';
RAISE NOTICE '   4. Set up backup schedules';
RAISE NOTICE '';
RAISE NOTICE '📚 Documentation: See scripts/database/docs/';
END $$;
-- ============================================================================
-- END OF INITIALIZATION SCRIPT
-- ============================================================================
