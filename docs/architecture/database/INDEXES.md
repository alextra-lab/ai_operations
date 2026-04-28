# Database Index Strategy and Performance

**Version:** 1.1.0
**Last Updated:** 2025-10-27

## Overview

The AI Operations Platform database employs a comprehensive indexing strategy with **100+ indexes** optimized for:

- **Fast lookups** - Primary key and unique constraint indexes
- **Foreign key joins** - Relationship traversal
- **Time-series queries** - Created_at, accessed_at indexes with DESC order
- **Full-text search** - GIN indexes on text columns
- **JSONB queries** - Specialized indexes on config_json fields
- **Partial indexes** - Conditional indexes for common filters

---

## Index Categories

### 1. Primary Keys and Uniqueness (29 indexes)

All tables have UUID primary keys with implicit indexes:

```sql
-- Example
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),  -- Implicit index
    username VARCHAR UNIQUE NOT NULL,              -- Implicit unique index
    email VARCHAR UNIQUE                           -- Implicit unique index (partial)
);
```

**Performance:** O(log n) lookup, clustered by default

---

### 2. Foreign Key Indexes (40+ indexes)

Every foreign key has a corresponding index for efficient joins:

```sql
-- Example: query_history → users relationship
CREATE INDEX idx_query_history_user_id ON query_history(user_id);

-- Benefits:
-- 1. Fast joins: SELECT * FROM query_history qh JOIN users u ON u.id = qh.user_id
-- 2. Cascade deletes: DELETE FROM users WHERE id = ? (fast FK check)
-- 3. User queries: SELECT * FROM query_history WHERE user_id = ?
```

**Key foreign key indexes:**
- `idx_query_history_user_id` - User's queries
- `idx_token_usage_user_id` - User's token consumption
- `idx_tool_invocations_user_id` - User's tool usage
- `idx_user_use_case_assignments_user` - User's use case access
- `idx_thread_messages_thread_id` - Thread's messages
- `idx_system_config_updated_by` - Audit queries for config changes

---

### 3. Time-Series Indexes (25+ indexes)

Optimized for chronological queries with DESC order:

```sql
-- Pattern: (timestamp_column DESC)
CREATE INDEX idx_query_history_created_at
ON query_history(created_at DESC);

CREATE INDEX idx_usage_stats_accessed_at
ON usage_stats(accessed_at DESC);

CREATE INDEX idx_audit_logs_actor_time
ON audit_logs(actor_user_id, event_time DESC);
```

**Use cases:**
- Recent queries: `WHERE created_at >= NOW() - INTERVAL '30 days' ORDER BY created_at DESC`
- User activity timeline: `WHERE user_id = ? ORDER BY created_at DESC LIMIT 100`
- Audit trail: `WHERE actor_user_id = ? ORDER BY event_time DESC`

**Performance:** DESC indexes enable fast reverse scans without sorting

---

### 4. Composite Indexes (15+ indexes)

Multi-column indexes for common query patterns:

```sql
-- Pattern: (filter_column, sort_column)
CREATE INDEX idx_use_cases_active
ON use_cases(is_active, category);

CREATE INDEX idx_token_usage_center_created
ON token_usage(center_id, created_at DESC);

CREATE INDEX idx_audit_logs_use_case_time
ON audit_logs(use_case_id, event_time DESC);
```

**Query optimization:**
```sql
-- Fully optimized by idx_use_cases_active
SELECT * FROM use_cases
WHERE is_active = TRUE
ORDER BY category;

-- Fully optimized by idx_token_usage_center_created
SELECT * FROM token_usage
WHERE center_id = 'headquarters'
ORDER BY created_at DESC
LIMIT 100;
```

**Index Selectivity:** Most selective column first, sort column second

---

### 5. GIN Indexes (9 indexes)

Generalized Inverted Indexes for complex types:

#### Array Columns (3 indexes)

```sql
-- Tags array
CREATE INDEX idx_documents_tags
ON documents USING GIN(tags);

-- Query: Find documents with specific tags
SELECT * FROM documents WHERE tags @> ARRAY['security', 'compliance'];

-- Chunk IDs array
CREATE INDEX idx_usage_stats_chunk_ids
ON usage_stats USING GIN(chunk_ids);

-- Query: Find usage stats for specific chunk
SELECT * FROM usage_stats WHERE chunk_ids @> ARRAY['uuid-here']::UUID[];
```

#### Full-Text Search (2 indexes)

```sql
-- Document title search
CREATE INDEX idx_documents_title_search
ON documents USING GIN(to_tsvector('english', title));

-- Query: Full-text search on titles
SELECT * FROM documents
WHERE to_tsvector('english', title) @@ to_tsquery('english', 'threat & analysis');

-- Query text search
CREATE INDEX idx_query_history_query_text_fts
ON query_history USING GIN(to_tsvector('english', query_text));
```

#### JSONB Columns (4 indexes)

```sql
-- Use case config JSONB paths
CREATE INDEX idx_use_cases_config_visibility_roles
ON use_cases USING GIN((config_json->'visibility'->'roles'));

CREATE INDEX idx_use_cases_config_visibility_tags
ON use_cases USING GIN((config_json->'visibility'->'tags'));

-- Query: Find use cases with specific role visibility
SELECT * FROM use_cases
WHERE config_json->'visibility'->'roles' ? 'admin';

-- System configuration JSONB (whole document)
CREATE INDEX idx_system_config_config_gin
ON system_config USING GIN(config);

-- Query: Find config sections with specific values
SELECT * FROM system_config
WHERE config @> '{"chunk_size": 512}'::jsonb;

-- Query: Check if specific key exists
SELECT * FROM system_config
WHERE config ? 'default_embedding_model';
```

**GIN vs GiST:** GIN chosen for exact matches, GiST better for range queries

---

### 6. BTREE Indexes on JSONB (5 indexes)

For specific JSON path queries:

```sql
-- Extract JSON value and index it
CREATE INDEX idx_use_cases_config_models_llm
ON use_cases USING BTREE((config_json->'models'->>'llm'));

CREATE INDEX idx_use_cases_config_rag_enabled
ON use_cases USING BTREE((config_json->'rag'->>'enabled'));

-- Query: Find use cases using specific model
SELECT * FROM use_cases
WHERE config_json->'models'->>'llm' = 'gpt-4o';

-- Query: Find use cases with RAG enabled
SELECT * FROM use_cases
WHERE (config_json->'rag'->>'enabled')::boolean = TRUE;
```

**Performance:** Faster than GIN for equality checks on specific paths

---

### 7. Partial Indexes (6 indexes)

Conditional indexes for common filters:

```sql
-- Only index active users
CREATE UNIQUE INDEX ix_users_email
ON users(email)
WHERE email IS NOT NULL;

-- Only index enabled tools
CREATE INDEX idx_tools_enabled
ON tools(is_enabled)
WHERE is_enabled = TRUE;

-- Only index healthy tools
CREATE INDEX idx_tools_healthy
ON tools(is_healthy)
WHERE is_healthy = TRUE;

-- Only index non-deprecated models
CREATE INDEX idx_models_deprecated
ON models(deprecated)
WHERE deprecated = FALSE;

-- Only index active encryption keys
CREATE INDEX idx_encryption_keys_active
ON encryption_keys(key_type, is_active)
WHERE is_active = TRUE;
```

**Benefits:**
- **Smaller index size** - Only indexes relevant rows
- **Faster updates** - Inactive rows don't update index
- **Better cache hit rate** - Index fits in memory

---

## Index Maintenance

### Index Size Monitoring

```sql
-- Top 20 largest indexes
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
    idx_scan AS index_scans,
    idx_tup_read AS tuples_read,
    idx_tup_fetch AS tuples_fetched
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY pg_relation_size(indexrelid) DESC
LIMIT 20;
```

### Unused Index Detection

```sql
-- Indexes with zero scans (candidates for removal)
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
  AND idx_scan = 0
  AND indexrelid::regclass::text NOT LIKE '%_pkey'  -- Exclude PKs
ORDER BY pg_relation_size(indexrelid) DESC;
```

### Index Bloat Check

```sql
-- Estimate index bloat
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
    round(100 * (pg_relation_size(indexrelid) - pg_relation_size(indexrelid, 'main'))::numeric /
          NULLIF(pg_relation_size(indexrelid), 0), 2) AS bloat_pct
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY pg_relation_size(indexrelid) DESC
LIMIT 20;
```

### Reindex Strategy

```sql
-- Reindex specific table (online, concurrent)
REINDEX TABLE CONCURRENTLY users;

-- Reindex all tables (maintenance window)
REINDEX DATABASE aio;

-- Reindex specific index
REINDEX INDEX CONCURRENTLY idx_documents_title_search;
```

**Schedule:** Monthly REINDEX on high-write tables

---

## Query Optimization Patterns

### Pattern 1: User Activity Queries

```sql
-- Query: Recent user queries
SELECT * FROM query_history
WHERE user_id = ?
ORDER BY created_at DESC
LIMIT 100;

-- Optimized by: idx_query_history_user_id + pk_query_history (id includes created_at)
-- EXPLAIN: Index Scan using idx_query_history_user_id
```

### Pattern 2: Time-Range Analytics

```sql
-- Query: Token usage in last 30 days
SELECT * FROM token_usage
WHERE center_id = 'headquarters'
  AND created_at >= NOW() - INTERVAL '30 days'
ORDER BY created_at DESC;

-- Optimized by: idx_token_usage_center_created (composite index)
-- EXPLAIN: Index Scan using idx_token_usage_center_created
```

### Pattern 3: Use Case Discovery

```sql
-- Query: Active use cases for specific intent
SELECT * FROM use_cases
WHERE is_active = TRUE
  AND intent_type = 'QUERY'
ORDER BY category;

-- Optimized by: idx_use_cases_active, idx_use_cases_intent
-- EXPLAIN: Bitmap Index Scan (combines multiple indexes)
```

### Pattern 4: Full-Text Search

```sql
-- Query: Search document titles
SELECT * FROM documents
WHERE to_tsvector('english', title) @@ to_tsquery('english', 'security & policy')
ORDER BY ingested_at DESC;

-- Optimized by: idx_documents_title_search (GIN), idx_documents_ingested_at
-- EXPLAIN: Bitmap Heap Scan + GIN index scan
```

---

## Performance Benchmarks

### Expected Query Performance

| Query Type | Target Latency | Index Strategy |
|------------|----------------|----------------|
| Primary key lookup | < 1ms | PK index (BTREE) |
| User's recent queries | < 5ms | Composite (user_id, created_at DESC) |
| Full-text search | < 50ms | GIN index + LIMIT |
| Analytics aggregation | < 100ms | Composite + covering index |
| JSONB path query | < 10ms | BTREE on extracted path |
| Array containment (@>) | < 20ms | GIN index |

### Index Hit Ratio

```sql
-- Target: > 99% index hit ratio
SELECT
    sum(idx_blks_hit) / nullif(sum(idx_blks_hit + idx_blks_read), 0) * 100 AS index_hit_ratio
FROM pg_statio_user_indexes
WHERE schemaname = 'public';
```

**Acceptable:** > 95%
**Good:** > 99%
**Excellent:** > 99.9%

---

## Index Design Guidelines

### 1. Primary Keys
- **Always UUID** - Distributed, non-sequential
- **Default gen_random_uuid()** - Application-level control optional
- **Clustered** - Physical row order matches index order

### 2. Foreign Keys
- **Always indexed** - Every FK gets an index
- **Composite for common joins** - (fk_column, sort_column)

### 3. Timestamps
- **DESC order** - Most queries want recent-first
- **Composite with filters** - (filter_col, timestamp DESC)

### 4. Boolean Flags
- **Partial indexes** - WHERE flag = TRUE
- **Not standalone** - Combine with other columns

### 5. JSONB
- **GIN for contains** - @>, ?
- **BTREE for equality** - Extract path, index result
- **Minimize** - Consider normalizing hot paths

### 6. Text Search
- **GIN on tsvector** - Full-text search
- **Specify language** - 'english' for stemming
- **Limit results** - Always use LIMIT with FTS

---

## Anti-Patterns to Avoid

### ❌ Over-Indexing

```sql
-- BAD: Too many similar indexes
CREATE INDEX idx1 ON table(col_a);
CREATE INDEX idx2 ON table(col_a, col_b);
CREATE INDEX idx3 ON table(col_a, col_b, col_c);

-- GOOD: One composite index covers all
CREATE INDEX idx ON table(col_a, col_b, col_c);
```

### ❌ Indexing Low-Cardinality Columns

```sql
-- BAD: Boolean with poor selectivity
CREATE INDEX idx_users_is_active ON users(is_active);
-- Problem: Only 2 distinct values, poor selectivity

-- GOOD: Partial index for common case
CREATE INDEX idx_users_active ON users(id) WHERE is_active = TRUE;
```

### ❌ Function Indexes Without Usage

```sql
-- BAD: Creating indexes "just in case"
CREATE INDEX idx_users_lower_email ON users(LOWER(email));
-- Problem: Never used if queries don't use LOWER()

-- GOOD: Match query patterns exactly
-- If query uses: WHERE LOWER(email) = LOWER(?)
-- Then create: CREATE INDEX idx_users_lower_email ON users(LOWER(email));
```

---

## Monitoring and Alerts

### Critical Metrics

1. **Index hit ratio** - Should be > 99%
2. **Unused indexes** - Review quarterly, remove if idx_scan = 0
3. **Index bloat** - Reindex if bloat > 30%
4. **Slow query log** - Identify missing indexes

### Recommended pg_stat_statements Config

```sql
-- In postgresql.conf
shared_preload_libraries = 'pg_stat_statements'
pg_stat_statements.max = 10000
pg_stat_statements.track = all
```

---

**Last Updated:** 2025-10-24
**Maintainer:** AI Operations Platform Team
