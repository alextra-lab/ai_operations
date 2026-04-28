-- ============================================================================
-- Migration 033: Tool Security Classification (ADR-057)
-- ============================================================================
-- Date: 2025-11-27
-- Description: Adds security classification columns to tools table for
--              risk-based access control.
--
-- New Columns:
--   - data_source_type: Trust level of data sources (internal/external/none/mixed)
--   - data_flow_direction: Data flow direction (ingress/egress/bidirectional/none)
--   - network_access_level: Network access level (isolated/internal/external)
--   - max_data_sensitivity: Max data classification (public/internal/confidential/restricted)
--
-- Usage:
--   psql-17 -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB \
--     -f ops/database/migrations/033_tool_security_classification.sql
-- ============================================================================

BEGIN;

-- =============================================================================
-- Add Security Classification Columns
-- =============================================================================

-- data_source_type: Trust level of data sources the tool accesses
ALTER TABLE tools ADD COLUMN IF NOT EXISTS data_source_type VARCHAR(20)
    NOT NULL DEFAULT 'internal'
    CHECK (data_source_type IN ('internal', 'external', 'none', 'mixed'));

COMMENT ON COLUMN tools.data_source_type IS
    'ADR-057: Trust level of data sources (internal=company-controlled, external=third-party, none=reasoning, mixed=gateway)';

-- data_flow_direction: Direction of data flow relative to the platform
ALTER TABLE tools ADD COLUMN IF NOT EXISTS data_flow_direction VARCHAR(20)
    NOT NULL DEFAULT 'ingress'
    CHECK (data_flow_direction IN ('ingress', 'egress', 'bidirectional', 'none'));

COMMENT ON COLUMN tools.data_flow_direction IS
    'ADR-057: Direction of data flow (ingress=into system, egress=out of system, bidirectional=both, none=pure reasoning)';

-- network_access_level: Network access requirements for the tool
ALTER TABLE tools ADD COLUMN IF NOT EXISTS network_access_level VARCHAR(20)
    NOT NULL DEFAULT 'internal'
    CHECK (network_access_level IN ('isolated', 'internal', 'external'));

COMMENT ON COLUMN tools.network_access_level IS
    'ADR-057: Network access requirements (isolated=no network, internal=company network only, external=internet access)';

-- max_data_sensitivity: Maximum data classification the tool can process
ALTER TABLE tools ADD COLUMN IF NOT EXISTS max_data_sensitivity VARCHAR(20)
    NOT NULL DEFAULT 'internal'
    CHECK (max_data_sensitivity IN ('public', 'internal', 'confidential', 'restricted'));

COMMENT ON COLUMN tools.max_data_sensitivity IS
    'ADR-057: Maximum data classification (public, internal, confidential, restricted=PII/PHI)';

-- =============================================================================
-- Create Index for Security Queries
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_tools_data_source_type
    ON tools(data_source_type);

CREATE INDEX IF NOT EXISTS idx_tools_security
    ON tools(data_source_type, max_data_sensitivity);

-- =============================================================================
-- Migrate Existing Tools Based on Current Classification
-- =============================================================================

-- Set sensible defaults based on existing tool_purpose and category
UPDATE tools SET
    data_source_type = CASE
        WHEN tool_purpose = 'retrieval' THEN 'internal'
        WHEN category IN ('reasoning', 'documentation') THEN 'none'
        ELSE 'external'
    END,
    data_flow_direction = CASE
        WHEN tool_purpose = 'retrieval' THEN 'ingress'
        WHEN category = 'reasoning' THEN 'none'
        ELSE 'ingress'
    END,
    network_access_level = CASE
        WHEN tool_purpose = 'retrieval' THEN 'internal'
        WHEN category = 'reasoning' THEN 'isolated'
        ELSE 'external'
    END,
    max_data_sensitivity = 'internal'  -- Conservative default
WHERE data_source_type = 'internal'
  AND data_flow_direction = 'ingress';  -- Only update if defaults are still set

-- =============================================================================
-- Add Deprecation Comments to Legacy Columns
-- =============================================================================

COMMENT ON COLUMN tools.tool_purpose IS
    'DEPRECATED (ADR-057): Use data_source_type + data_flow_direction instead. Kept for backward compatibility.';

COMMENT ON COLUMN tools.service_location IS
    'DEPRECATED (ADR-057): All MCPs now run in orchestrator. Kept for backward compatibility.';

COMMIT;

-- ============================================================================
-- Post-Migration Verification
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '✅ Migration 033: Tool Security Classification completed';
    RAISE NOTICE '   - Added: data_source_type, data_flow_direction, network_access_level, max_data_sensitivity';
    RAISE NOTICE '   - Created: idx_tools_data_source_type, idx_tools_security';
    RAISE NOTICE '   - Updated existing tools with default security values';
END $$;
