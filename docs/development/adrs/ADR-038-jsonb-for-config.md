# ADR-002: JSONB for Dynamic Configuration

**Status:** Accepted
**Date:** 2025-10-24
**Deciders:** Database Team, Backend Team

## Context

AI Operations Platform requires flexible configuration for:

- Use case definitions (models, RAG settings, output contracts)
- LLM generation parameters (temperature, max_tokens, etc.)
- Tool capabilities and parameters
- Model API configurations
- Metadata for extensibility

**Competing Approaches:**

1. **Normalized tables** - Separate tables for each config type
2. **JSON (text)** - Plain JSON stored as text
3. **JSONB (binary)** - Binary JSON with indexing

## Decision

We will use **JSONB columns** for dynamic configuration and flexible metadata.

**Primary Use Cases:**

- `use_cases.config_json` - Use case configuration
- `tools.capabilities` - MCP tool capabilities
- `tools.parameters_schema` - Tool parameter schemas
- `models.api_config` - Model-specific API configuration
- `*.metadata` - Extensible metadata across many tables

## Rationale

### Advantages

1. **Schema Flexibility**
   - Evolve configuration without migrations
   - Different use cases can have different config structures
   - Supports future features without schema changes

2. **JSONB-Specific Benefits**
   - **Binary format** - Faster processing than JSON text
   - **Indexable** - GIN and BTREE indexes on JSON paths
   - **Queryable** - Extract values, check containment, filter

3. **Type Safety at Application Layer**
   - Pydantic schemas validate JSONB structure
   - Application enforces consistency
   - Database provides storage flexibility

4. **Readability**
   - Easy to inspect in psql/pgAdmin
   - Self-documenting configurations
   - API-friendly (direct JSON pass-through)

5. **Air-Gapped Friendly**
   - Configuration embedded in database
   - No external config servers needed
   - Portable across environments

### Trade-Offs

1. **No Database-Level Validation (By Default)**
   - Schema changes don't require migrations
   - **Mitigation:** CHECK constraints on required fields

   ```sql
   ALTER TABLE use_cases
   ADD CONSTRAINT use_cases_config_json_structure
   CHECK (
       config_json ? 'visibility' AND
       config_json ? 'models' AND
       config_json ? 'generation_params' AND
       config_json ? 'rag' AND
       config_json ? 'output_contract'
   );
   ```

2. **Query Performance**
   - JSONB path extraction slower than dedicated columns
   - **Mitigation:**
     - Index frequently queried paths
     - Cache extracted values in application
     - Consider materialized columns for hot paths

3. **Storage Overhead**
   - JSONB has metadata overhead (~10-20%)
   - **Mitigation:** TOAST compression handles large JSONB

4. **Index Limitations**
   - Can't enforce uniqueness on deep JSON paths easily
   - **Mitigation:** Extract to dedicated columns if needed

## Alternatives Considered

### 1. Normalized Tables

**Example:**

```sql
CREATE TABLE use_case_models (
    use_case_id UUID REFERENCES use_cases(id),
    llm VARCHAR,
    embedding VARCHAR
);

CREATE TABLE use_case_generation_params (
    use_case_id UUID REFERENCES use_cases(id),
    temperature DECIMAL,
    max_tokens INTEGER,
    ...
);
```

**Rejected because:**

- Dozens of tables for full config
- Schema migrations for every new parameter
- Complex queries with many joins
- Doesn't support arbitrary extension

### 2. JSON (Text)

**Rejected because:**

- No indexing support
- Slower parsing (text → JSON on every query)
- Can't query JSON structure efficiently
- No validation (not even well-formedness)

### 3. Key-Value Table

**Example:**

```sql
CREATE TABLE use_case_config (
    use_case_id UUID,
    key VARCHAR,
    value TEXT
);
```

**Rejected because:**

- Loses type information
- Can't represent nested structures
- Many rows per use case
- Complex queries (pivot/unpivot)

## Implementation Guidelines

### Pattern 1: Validated Config JSONB

```sql
CREATE TABLE use_cases (
    id UUID PRIMARY KEY,
    config_json JSONB NOT NULL,

    -- Validate required top-level keys
    CONSTRAINT config_structure_check
    CHECK (
        config_json ? 'models' AND
        config_json ? 'generation_params'
    ),

    -- Validate specific values
    CONSTRAINT config_temperature_check
    CHECK (
        (config_json->'generation_params'->>'temperature')::float >= 0.0 AND
        (config_json->'generation_params'->>'temperature')::float <= 1.0
    )
);
```

### Pattern 2: Indexed JSON Paths

```sql
-- Index for exact match on JSON field
CREATE INDEX idx_use_cases_model_llm
ON use_cases USING BTREE((config_json->'models'->>'llm'));

-- Query using indexed path
SELECT * FROM use_cases
WHERE config_json->'models'->>'llm' = 'gpt-4o';
```

### Pattern 3: GIN Index for Contains

```sql
-- GIN index for containment queries
CREATE INDEX idx_use_cases_visibility_roles
ON use_cases USING GIN((config_json->'visibility'->'roles'));

-- Query: Find use cases visible to role
SELECT * FROM use_cases
WHERE config_json->'visibility'->'roles' ? 'admin';
```

### Pattern 4: Flexible Metadata

```sql
CREATE TABLE models (
    id UUID PRIMARY KEY,
    model_id VARCHAR NOT NULL,
    -- Standard columns...
    metadata_json JSONB DEFAULT '{}'::jsonb  -- Extensible metadata
);

-- Insert with metadata
INSERT INTO models (model_id, metadata_json)
VALUES ('gpt-4o', '{"vendor_id": "openai-123", "region": "us-east-1"}');
```

## Validation Strategy

### Application Layer (Pydantic)

```python
from pydantic import BaseModel, Field

class UseCaseConfig(BaseModel):
    visibility: VisibilityConfig
    models: ModelsConfig
    generation_params: GenerationParams
    rag: RAGConfig
    output_contract: OutputContract
    telemetry: TelemetryConfig
    policy: PolicyConfig

# Validate before database insert
config = UseCaseConfig.model_validate_json(config_json)
await db.execute(
    "INSERT INTO use_cases (config_json) VALUES ($1)",
    config.model_dump_json()
)
```

### Database Layer (CHECK Constraints)

```sql
-- Catch configuration errors at database level
ALTER TABLE use_cases
ADD CONSTRAINT config_max_tokens_positive
CHECK (
    (config_json->'generation_params'->>'max_tokens')::integer > 0
);
```

## Performance Optimization

### 1. Limit JSONB Column Size

```sql
-- Add size limit to prevent abuse
ALTER TABLE use_cases
ADD CONSTRAINT config_json_size_limit
CHECK (pg_column_size(config_json) < 1048576);  -- 1 MB limit
```

### 2. Index Only Hot Paths

```sql
-- Don't index everything - only frequently queried paths
CREATE INDEX idx_use_cases_rag_enabled
ON use_cases USING BTREE((config_json->'rag'->>'enabled'));

-- Skip indexing rarely-queried nested fields
```

### 3. Consider Materialized Columns (Future)

If a JSON path becomes performance-critical:

```sql
-- PostgreSQL 12+ generated columns
ALTER TABLE use_cases
ADD COLUMN llm_model VARCHAR
GENERATED ALWAYS AS (config_json->'models'->>'llm') STORED;

CREATE INDEX idx_use_cases_llm_model ON use_cases(llm_model);
```

## Monitoring

**Key Metrics:**

- JSONB column sizes: Monitor growth
- Query performance: Track JSON path extraction latency
- Index usage: Check GIN index hit rates

**Alerts:**

- JSONB column > 1 MB (investigate data model)
- JSON path query > 100ms (consider materialized column)
- GIN index scan > 50% of queries (verify index effectiveness)

## Migration Strategy

If JSONB becomes a bottleneck:

1. **Identify hot path** (frequently queried JSON field)
2. **Add materialized column** (generated always as)
3. **Create index** on new column
4. **Update queries** to use new column
5. **Monitor performance** improvement

**Example:**

```sql
-- Before: Slow JSON path query
SELECT * FROM use_cases WHERE config_json->'models'->>'llm' = 'gpt-4o';

-- After: Fast indexed column query
ALTER TABLE use_cases
ADD COLUMN llm_model VARCHAR
GENERATED ALWAYS AS (config_json->'models'->>'llm') STORED;

CREATE INDEX idx_llm_model ON use_cases(llm_model);

SELECT * FROM use_cases WHERE llm_model = 'gpt-4o';
```

## References

- [PostgreSQL JSONB Documentation](https://www.postgresql.org/docs/17/datatype-json.html)
- [JSONB Indexing](https://www.postgresql.org/docs/17/datatype-json.html#JSON-INDEXING)
- [Generated Columns](https://www.postgresql.org/docs/17/ddl-generated-columns.html)

## Revision History

- 2025-10-24: Initial decision (JSONB for config and metadata)
